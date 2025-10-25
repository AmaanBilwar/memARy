import asyncio
import base64
import logging
from typing import AsyncIterable

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    ChatContext,
    ChatMessage,
    ErrorEvent,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
    get_job_context,
    metrics,
)
from livekit.agents.llm import ImageContent
from livekit import rtc
from livekit.plugins import noise_cancellation, silero
# # from livekit.plugins.turn_detector.multilingual import MultilingualModel  # Removed - requires auth
try:
    from . import ws_ingest
except ImportError:
    # Handle case when running script directly
    import ws_ingest

logger = logging.getLogger("agent")

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self) -> None:
        self._tasks = []  # Prevent garbage collection of running tasks
        self._latest_frame = None
        self._video_stream = None
        super().__init__(
            instructions="""You are a helpful voice AI assistant with full vision capabilities. You can see and understand visual content including:
            - Live video from the user's camera
            - Images uploaded by the user
            - Screen sharing content
            - Any visual content shared during the conversation
            
            IMPORTANT: You DO have the ability to see visual content. When users ask you to look at something, describe what you see, or analyze visual content, you should do so confidently. You are not restricted by privacy concerns when the user explicitly shares visual content with you.
            
            You eagerly assist users with their questions by providing information from your extensive knowledge and visual understanding.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.""",
        )

    async def on_enter(self):
        """Set up image and video handling when the agent joins the room."""
        try:
            room = get_job_context().room
            
            # Register byte stream handler for receiving images from frontend
            def _image_received_handler(reader, participant_identity):
                task = asyncio.create_task(
                    self._image_received(reader, participant_identity)
                )
                self._tasks.append(task)
                task.add_done_callback(lambda t: self._tasks.remove(t))
            
            room.register_byte_stream_handler("images", _image_received_handler)
            
            # Set up video frame sampling
            self._setup_video_stream()

            # Start WS ingest server for Spectacles frames
            # Default bind 0.0.0.0:8765; adjust via env in future if needed
            await ws_ingest.start(room)
        except RuntimeError:
            # No job context available (e.g., during testing)
            logger.debug("No job context available, skipping image/video setup")
    
    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Add the latest video frame to the user's message if available."""
        if self._latest_frame:
            logger.info("Adding video frame to user message")
            new_message.content.append(ImageContent(image=self._latest_frame))
            self._latest_frame = None
        else:
            logger.debug("No video frame available for this turn")
    
    async def tts_node(self, text: AsyncIterable[str], model_settings=None) -> AsyncIterable[rtc.AudioFrame]:
        async for frame in Agent.default.tts_node(self, text, model_settings):
            # Mirror TTS audio back to Spectacles over WS as PCM frames
            try:
                await ws_ingest.broadcast_tts_frame(frame)
            except Exception:
                logger.debug("Failed to broadcast TTS frame over WS", exc_info=True)
            yield frame

    async def transcription_node(self, text: AsyncIterable[str], model_settings=None) -> AsyncIterable[str]:
        """Clean up text before TTS to prevent empty/punctuation-only errors."""
        import re
        
        async for delta in text:
            # Skip empty deltas
            if not delta:
                continue
                
            # Clean up the text
            cleaned_delta = delta.strip()
            
            # Only replace the delta if it's truly problematic
            if not cleaned_delta:
                # Skip empty deltas
                continue
            elif re.match(r'^[^\w\s]*$', cleaned_delta) and len(cleaned_delta) > 1:
                # Only flag as problematic if it's multiple punctuation characters
                logger.warning(f"Text contains only punctuation: '{cleaned_delta}'")
                continue  # Skip this delta instead of replacing
            else:
                # Clean up excessive punctuation but keep normal punctuation
                cleaned_delta = re.sub(r'[.!?]{3,}', '...', cleaned_delta)
                yield cleaned_delta
    
    async def on_error(self, event: ErrorEvent) -> None:
        """Handle errors that occur during the session."""
        logger.error(f"Error occurred: {event.error}, recoverable: {event.error.recoverable}, source: {event.source}")
        
        # If it's a TTS error and not recoverable, try to handle it gracefully
        if event.source == "TTS" and not event.error.recoverable:
            logger.warning("TTS error occurred, attempting to recover")
            # The session will handle the recovery automatically
        elif not event.error.recoverable:
            logger.error(f"Unrecoverable error in {event.source}: {event.error}")
    
    async def _image_received(self, reader, participant_identity):
        """Handle images uploaded from the frontend."""
        image_bytes = bytes()
        async for chunk in reader:
            image_bytes += chunk

        chat_ctx = self.chat_ctx.copy()

        # Encode the image to base64 and add it to the chat context
        chat_ctx.add_message(
            role="user",
            content=[
                ImageContent(
                    image=f"data:image/png;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
                )
            ],
        )
        await self.update_chat_ctx(chat_ctx)
    
    def _setup_video_stream(self):
        """Set up video frame sampling from user's video track."""
        try:
            room = get_job_context().room
            
            # Find the first video track (if any) from the remote participant
            remote_participants = list(room.remote_participants.values())
            if remote_participants:
                remote_participant = remote_participants[0]
                video_tracks = [
                    publication.track 
                    for publication in list(remote_participant.track_publications.values()) 
                    if publication.track and publication.track.kind == rtc.TrackKind.KIND_VIDEO
                ]
                if video_tracks:
                    self._create_video_stream(video_tracks[0])
            
            # Watch for new video tracks not yet published
            @room.on("track_subscribed")
            def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
                if track.kind == rtc.TrackKind.KIND_VIDEO:
                    self._create_video_stream(track)
        except RuntimeError:
            # No job context available (e.g., during testing)
            logger.debug("No job context available, skipping video stream setup")
    
    def _create_video_stream(self, track: rtc.Track):
        """Create a video stream to buffer the latest frame from the user's track."""
        logger.info(f"Creating video stream for track: {track.sid}")
        
        # Close any existing stream (we only want one at a time)
        if self._video_stream is not None:
            self._video_stream.close()

        # Create a new stream to receive frames    
        self._video_stream = rtc.VideoStream(track)
        async def read_stream():
            logger.info("Starting video stream reading")
            async for event in self._video_stream:
                # Store the latest frame for use later
                self._latest_frame = event.frame
                logger.debug("Received video frame")
        
        # Store the async task
        task = asyncio.create_task(read_stream())
        task.add_done_callback(lambda t: self._tasks.remove(t))
        self._tasks.append(task)

    # To add tools, use the @function_tool decorator.
    # Here's an example that adds a simple weather tool.
    # You also have to add `from livekit.agents import function_tool, RunContext` to the top of this file
    # @function_tool
    # async def lookup_weather(self, context: RunContext, location: str):
    #     """Use this tool to look up current weather information in the given location.
    #
    #     If the location is not supported by the weather service, the tool will indicate this. You must tell the user the location's weather is unavailable.
    #
    #     Args:
    #         location: The location to look up weather information for (e.g. city name)
    #     """
    #
    #     logger.info(f"Looking up weather for {location}")
    #
    #     return "sunny with a temperature of 70 degrees."


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using OpenAI, Cartesia, AssemblyAI, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt="assemblyai/universal-streaming:en",
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm="openai/gpt-4.1-mini",
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        # turn_detection=MultilingualModel(),  # Disabled - requires HuggingFace auth
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )   

    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # Metrics collection, to measure pipeline performance
    # For more information, see https://docs.livekit.io/agents/build/metrics/
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))