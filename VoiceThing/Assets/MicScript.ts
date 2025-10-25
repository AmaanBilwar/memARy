@component
export class MicScript extends BaseScriptComponent {
  @input
  statusText: Text;
  
  @input
  micButtonImage: Image;
  
  private asrModule: AsrModule = require("LensStudio:AsrModule");
  private isListening: boolean = false;
  
  onAwake() {
    print("=== Script Started ===");
    
    this.statusText.text = "Loading...";
    
    // Start listening after 1 second delay
    const delay = this.createEvent("DelayedCallbackEvent");
    delay.bind(() => {
      print("Auto-starting listening...");
      this.startContinuousListening();
    });
    delay.reset(1.0);
  }
  
  private startContinuousListening() {
    if (this.isListening) {
      print("Already listening");
      return;
    }
    
    print("=== Starting Continuous Listening ===");
    this.isListening = true;
    this.statusText.text = "🎤 Ready - speak now";
    this.setMicColor(new vec4(0, 1, 0, 1)); // Green
    
    const settings = AsrModule.AsrTranscriptionOptions.create();
    settings.mode = AsrModule.AsrMode.HighAccuracy;
    settings.silenceUntilTerminationMs = 5000; // Longer silence before stopping
    
    settings.onTranscriptionUpdateEvent.add((output) => {
      if (!output.isFinal) {
        // Interim results - still listening
        this.statusText.text = '"' + output.text + '..."';
        this.setMicColor(new vec4(1, 0, 0, 1)); // Red while hearing
      } else {
        // Final result
        print("Final: " + output.text);
        
        // Check if "memory" was said
        const lowerText = output.text.toLowerCase();
        if (lowerText.includes("memory")) {
          print("activated");
          this.statusText.text = "✅ ACTIVATED";
          this.setMicColor(new vec4(1, 1, 0, 1)); // Yellow for activation
        } else {
          this.statusText.text = '"' + output.text + '"';
        }
        
        // Show result briefly then go back to ready state
        const resetDisplay = this.createEvent("DelayedCallbackEvent");
        resetDisplay.bind(() => {
          this.statusText.text = "🎤 Ready - speak now";
          this.setMicColor(new vec4(0, 1, 0, 1)); // Green
        });
        resetDisplay.reset(1.5);
        
        // DON'T STOP - just keep listening
        // The ASR will continue waiting for next speech
      }
    });
    
    settings.onTranscriptionErrorEvent.add((error) => {
      print("Error: " + error);
      this.statusText.text = "Error - restarting...";
      this.setMicColor(new vec4(1, 1, 1, 1));
      
      // Stop and restart on error
      this.isListening = false;
      this.asrModule.stopTranscribing();
      
      const retry = this.createEvent("DelayedCallbackEvent");
      retry.bind(() => {
        this.startContinuousListening();
      });
      retry.reset(1.0);
    });
    
    this.asrModule.startTranscribing(settings);
    print("Continuous listening started - will not stop between utterances");
  }
  
  private setMicColor(color: vec4) {
    if (this.micButtonImage && this.micButtonImage.mainPass) {
      this.micButtonImage.mainPass.baseColor = color;
    }
  }
  
  public stopListening() {
    if (this.isListening) {
      print("=== Stopping Listening ===");
      this.isListening = false;
      this.asrModule.stopTranscribing();
      this.statusText.text = "Stopped";
      this.setMicColor(new vec4(1, 1, 1, 1));
    }
  }
}