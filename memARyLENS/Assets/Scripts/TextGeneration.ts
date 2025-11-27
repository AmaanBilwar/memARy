@component
export class TypeScript extends BaseScriptComponent {
    @input
    myText: Text3D;

    onAwake() {
        this.myText.text = "Hello from script!";
        
        // Example: Update text continuously
        this.createEvent("UpdateEvent").bind((eventData) => {
            // You can update text dynamically
            var currentTime = Math.floor(getTime());
            this.myText.text = "Time: " + currentTime;
        });
    }
}