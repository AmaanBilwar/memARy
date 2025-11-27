// @input Component.Text statusText
// @input SceneObject micButton {"hint": "Required: Button to trigger recording"}

const asrModule = require('LensStudio:AsrModule');

var isRecording = false;
var waitingForKeyword = true;
var currentTranscription = "";

// Initialize
function init() {
    print("Initializing ASR Speech Recognition...");

    if (!script.micButton) {
        print("❌ ERROR: micButton is required! Please assign a button in the inspector.");
        updateStatus('ERROR: No button assigned');
        return;
    }

    updateStatus('Tap button to speak');
    setupButtonMode();
}

// Setup button-triggered recording
function setupButtonMode() {
    var interactionComponent = script.micButton.getComponent("Component.InteractionComponent");

    if (interactionComponent) {
        interactionComponent.onTap.add(function() {
            print("Button tapped - isRecording: " + isRecording);
            if (!isRecording) {
                startRecording();
            }
        });
    } else {
        print("⚠️ No InteractionComponent found on micButton!");
        print("Adding InteractionComponent...");

        // Try to add interaction component if missing
        var interaction = script.micButton.createComponent("Component.InteractionComponent");
        if (interaction) {
            interaction.onTap.add(function() {
                print("Button tapped - isRecording: " + isRecording);
                if (!isRecording) {
                    startRecording();
                }
            });
        }
    }
}

// Start recording
function startRecording() {
    if (isRecording) {
        print("⚠️ Already recording, ignoring tap");
        return;
    }

    print("🎤 Starting ASR transcription...");
    isRecording = true;
    waitingForKeyword = true;
    currentTranscription = "";
    updateStatus('🎤 Say "Memory" then your message');

    var asrSettings = AsrModule.AsrTranscriptionOptions.create();
    asrSettings.mode = AsrModule.AsrMode.HighAccuracy;
    asrSettings.silenceUntilTerminationMs = 2000; // Stop after 2s of silence

    asrSettings.onTranscriptionUpdateEvent.add(function(asrOutput) {
        var text = asrOutput.text.toLowerCase();
        print('ASR Update - isFinal: ' + asrOutput.isFinal + ', text: "' + asrOutput.text + '"');

        // Check for "memory" keyword if still waiting
        if (waitingForKeyword && text.includes("memory")) {
            print("🎯 MEMORY keyword detected!");
            waitingForKeyword = false;
            updateStatus('✓ Keyword detected! Continue...');
        }

        // Show interim results if keyword was detected
        if (!waitingForKeyword && !asrOutput.isFinal && asrOutput.text.trim() !== '') {
            currentTranscription = asrOutput.text;
            updateStatus('Recording: "' + asrOutput.text + '..."');
        }

        // Final result
        if (asrOutput.isFinal) {
            currentTranscription = asrOutput.text;

            if (!waitingForKeyword && currentTranscription.trim() !== '') {
                print('✅ Final transcription: ' + currentTranscription);
                updateStatus('You said: "' + currentTranscription + '"');
            } else {
                print('⚠️ No keyword detected or empty transcription');
                updateStatus('No "Memory" keyword heard. Try again.');
            }

            isRecording = false;
            asrModule.stopTranscribing();

            // Reset after 3 seconds
            var reset = script.createEvent("DelayedCallbackEvent");
            reset.bind(function() {
                updateStatus('Tap button to speak');
                waitingForKeyword = true;
            });
            reset.reset(3.0);
        }
    });

    asrSettings.onTranscriptionErrorEvent.add(function(error) {
        print('❌ ASR Error code: ' + error);

        var errorMsg = 'Error: ';
        if (error === 1) {
            errorMsg += 'Microphone permission denied or ASR unavailable';
        } else if (error === 2) {
            errorMsg += 'No speech detected';
        } else if (error === 3) {
            errorMsg += 'Network error';
        } else {
            errorMsg += 'Unknown error (' + error + ')';
        }

        updateStatus(errorMsg);
        isRecording = false;

        // Reset after 3 seconds
        var reset = script.createEvent("DelayedCallbackEvent");
        reset.bind(function() {
            updateStatus('Tap button to speak');
        });
        reset.reset(3.0);
    });

    asrModule.startTranscribing(asrSettings);
}

function updateStatus(message) {
    if (script.statusText) {
        script.statusText.text = message;
    }
    print("Status: " + message);
}

// Initialize
init();