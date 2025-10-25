from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, JobContext
from livekit.plugins import google, noise_cancellation

# Load environment variables from .env.local
load_dotenv(".env.local")


class VideoAssistant(Agent):
    """
    A voice assistant with live video input capabilities.
    Uses Gemini Live API for realtime audio and video processing.
    """
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice assistant with live video input from your user.
            You can see what the user shows you through their camera and can describe what you see.
            Be conversational, friendly, and provide detailed observations when asked about what you see.
            Keep your responses concise and natural.""",
        )


async def entrypoint(ctx: JobContext):
    """
    Main entry point for the agent.
    Sets up the agent session with video input enabled.
    """
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-2.0-flash-exp",  # Latest Gemini model with vision
            voice="Puck",  # Voice options: Puck, Charon, Kore, Fenrir, Aoede
            temperature=0.8,
        ),
    )

    await session.start(
        room=ctx.room,
        agent=VideoAssistant(),
        room_input_options=RoomInputOptions(
            # Enable video input - this is the key setting for vision!
            video_enabled=True,
            
            # Enable noise cancellation for better audio quality
            # For telephony, use: noise_cancellation.BVCTelephony()
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Generate an initial greeting
    await session.generate_reply(
        instructions="Greet the user warmly and let them know you can see their video feed and are ready to help."
    )


if __name__ == "__main__":
    # Run the agent with CLI support
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
