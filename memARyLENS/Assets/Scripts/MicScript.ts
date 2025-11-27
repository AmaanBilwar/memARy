import Event from "SpectaclesInteractionKit.lspkg/Utils/Event";
import { BaseButton } from "SpectaclesUIKit.lspkg/Scripts/Components/Button/BaseButton";

@component
export class MicScript extends BaseScriptComponent {
  @input
  private statusText: Text;
  
  @input
  private micButton: BaseButton; // Now it's a BaseButton!
  
  @input
  private micButtonImage: Image; // Optional - for color changes
  
  private asrModule: AsrModule = require("LensStudio:AsrModule");
  private isRecording: boolean = false;
  
  public onTranscriptionEvent: Event<string> = new Event<string>();
  
  onAwake() {
    print("=== Mic Script Started ===");
    
    // Wait for button to initialize
    this.micButton.onInitialized.add(() => {
      print("Button initialized");
      this.setupButton();
    });
    
    this.updateStatus('Tap mic to speak');
    this.setMicColor(new vec4(1, 1, 1, 1));
  }
  
  private setupButton() {
    // Listen for button press
    this.micButton.onTriggerStart.add(() => {
      print("Button pressed!");
      this.handleButtonPress();
    });
    
    // Optional: Listen for button release
    this.micButton.onTriggerEnd.add(() => {
      print("Button released");
    });
    
    print("Button events registered");
  }
  
  private handleButtonPress() {
    if (this.isRecording) {
      print("Already recording");
      return;
    }
    
    this.startListening();
  }
  
  private startListening() {
    print("=== Starting to listen ===");
    this.isRecording = true;
    this.setMicColor(new vec4(1, 0, 0, 1)); // Red
    this.updateStatus('🎤 Listening...');
    
    const asrSettings = AsrModule.AsrTranscriptionOptions.create();
    asrSettings.mode = AsrModule.AsrMode.HighAccuracy;
    asrSettings.silenceUntilTerminationMs = 1500;
    
    asrSettings.onTranscriptionUpdateEvent.add((asrOutput) => {
      print("Transcription: " + asrOutput.text);
      
      if (!asrOutput.isFinal) {
        this.updateStatus('"' + asrOutput.text + '..."');
      }
      
      if (asrOutput.isFinal) {
        this.isRecording = false;
        this.setMicColor(new vec4(1, 1, 1, 1)); // White
        this.asrModule.stopTranscribing();
        
        const text = asrOutput.text;
        print("=== Final: " + text + " ===");
        
        this.updateStatus('"' + text + '"');
        this.onTranscriptionEvent.invoke(text);
        
        const reset = this.createEvent("DelayedCallbackEvent");
        reset.bind(() => {
          this.updateStatus('Tap mic to speak');
        });
        reset.reset(3.0);
      }
    });
    
    asrSettings.onTranscriptionErrorEvent.add((error) => {
      print("=== Error: " + error + " ===");
      this.isRecording = false;
      this.setMicColor(new vec4(1, 1, 1, 1));
      this.updateStatus("Error - try again");
    });
    
    print("Starting ASR...");
    this.asrModule.startTranscribing(asrSettings);
  }
  
  private setMicColor(color: vec4) {
    if (this.micButtonImage && this.micButtonImage.mainPass) {
      this.micButtonImage.mainPass.baseColor = color;
    }
  }
  
  private updateStatus(message: string) {
    if (this.statusText) {
      this.statusText.text = message;
    }
    print("Status: " + message);
  }
}