# 🌐 Using Memary API from Any Device via Ngrok

Your API is now publicly accessible at: **`https://memary-chromadb.ngrok-free.app`**

Any device (phone, tablet, computer, IoT device) can call this API!

---

## 🚀 Quick Start - From Any Device

### **Base URL**
```
https://memary-chromadb.ngrok-free.app
```

---

## 📸 Store Image Memory

### **Endpoint**: `POST /store`

**From any device** (Python, curl, JavaScript, mobile app):

### **Python Example** (from phone/laptop)
```python
import requests
import base64

# Read and encode image
with open('photo.jpg', 'rb') as f:
    image_b64 = base64.b64encode(f.read()).decode('utf-8')

# Send to API
response = requests.post(
    'https://memary-chromadb.ngrok-free.app/store',
    json={
        'image_base64': image_b64,
        'session_id': 'my-phone-session'
    }
)

result = response.json()
print(f"Scene: {result['analysis']['scene']}")
print(f"Objects: {result['analysis']['objects']}")
```

### **cURL Example** (from terminal on any device)
```bash
# Encode image to base64
IMAGE_B64=$(base64 -i photo.jpg)

# Send to API
curl -X POST https://memary-chromadb.ngrok-free.app/store \
  -H "Content-Type: application/json" \
  -d "{
    \"image_base64\": \"$IMAGE_B64\",
    \"session_id\": \"terminal-session\"
  }"
```

### **JavaScript Example** (from browser/Node.js)
```javascript
// From a webpage or React Native app
async function storeImage(imageBase64) {
    const response = await fetch('https://memary-chromadb.ngrok-free.app/store', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            image_base64: imageBase64,
            session_id: 'web-session'
        })
    });
    
    const data = await response.json();
    console.log('Scene:', data.analysis.scene);
    console.log('Objects:', data.analysis.objects);
}
```

### **iOS Swift Example**
```swift
func storeImage(imageBase64: String) {
    let url = URL(string: "https://memary-chromadb.ngrok-free.app/store")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let body: [String: Any] = [
        "image_base64": imageBase64,
        "session_id": "ios-app"
    ]
    request.httpBody = try? JSONSerialization.data(withJSONObject: body)
    
    URLSession.shared.dataTask(with: request) { data, response, error in
        if let data = data {
            let json = try? JSONSerialization.jsonObject(with: data)
            print("Result:", json)
        }
    }.resume()
}
```

### **Android Kotlin Example**
```kotlin
suspend fun storeImage(imageBase64: String) = withContext(Dispatchers.IO) {
    val url = URL("https://memary-chromadb.ngrok-free.app/store")
    val json = JSONObject().apply {
        put("image_base64", imageBase64)
        put("session_id", "android-app")
    }
    
    val connection = url.openConnection() as HttpURLConnection
    connection.requestMethod = "POST"
    connection.setRequestProperty("Content-Type", "application/json")
    connection.doOutput = true
    
    connection.outputStream.write(json.toString().toByteArray())
    val response = connection.inputStream.bufferedReader().readText()
    println("Result: $response")
}
```

---

## 📝 Store Text Summary

### **Endpoint**: `POST /store_text`

```bash
curl -X POST https://memary-chromadb.ngrok-free.app/store_text \
  -H "Content-Type: application/json" \
  -d '{
    "text_summary": "I see a red mug on the desk next to my keys",
    "session_id": "text-session"
  }'
```

```python
import requests

requests.post(
    'https://memary-chromadb.ngrok-free.app/store_text',
    json={
        'text_summary': 'Blue backpack on the floor near the door',
        'session_id': 'python-session'
    }
)
```

---

## 🔍 Search Memories

### **Endpoint**: `GET /search?query=<your_query>`

```bash
# Search from any device
curl "https://memary-chromadb.ngrok-free.app/search?query=where%20are%20my%20keys"
```

```python
import requests

response = requests.get(
    'https://memary-chromadb.ngrok-free.app/search',
    params={'query': 'where are my keys'}
)
print(response.json()['answer'])
```

---

## 📊 Get All Memories

### **Endpoint**: `GET /memories`

```bash
curl https://memary-chromadb.ngrok-free.app/memories
```

```python
import requests

memories = requests.get('https://memary-chromadb.ngrok-free.app/memories').json()
print(f"Total memories: {memories['total']}")
for memory in memories['memories']:
    print(f"- {memory['scene']}")
```

---

## 🎯 Find Specific Item

### **Endpoint**: `GET /item/{item_name}`

```bash
# Find all mentions of "mug"
curl https://memary-chromadb.ngrok-free.app/item/mug

# Ask specific question
curl "https://memary-chromadb.ngrok-free.app/item/mug?question=what%20color%20is%20it"
```

---

## 📈 Get Statistics

### **Endpoint**: `GET /statistics`

```bash
curl https://memary-chromadb.ngrok-free.app/statistics
```

---

## 🧹 Clear Storage

### **Endpoint**: `POST /clear_storage`

```bash
curl -X POST https://memary-chromadb.ngrok-free.app/clear_storage
```

---

## 📱 Mobile App Integration

### **React Native Example**
```javascript
import axios from 'axios';
import { launchCamera } from 'react-native-image-picker';
import RNFS from 'react-native-fs';

async function captureAndStore() {
    // Take photo
    const result = await launchCamera({ mediaType: 'photo' });
    
    // Convert to base64
    const imageBase64 = await RNFS.readFile(result.assets[0].uri, 'base64');
    
    // Send to API
    const response = await axios.post(
        'https://memary-chromadb.ngrok-free.app/store',
        {
            image_base64: imageBase64,
            session_id: 'react-native-app'
        }
    );
    
    console.log('Stored:', response.data);
}
```

### **Flutter Example**
```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

Future<void> captureAndStore() async {
  final picker = ImagePicker();
  final image = await picker.pickImage(source: ImageSource.camera);
  
  if (image != null) {
    final bytes = await image.readAsBytes();
    final base64Image = base64Encode(bytes);
    
    final response = await http.post(
      Uri.parse('https://memary-chromadb.ngrok-free.app/store'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'image_base64': base64Image,
        'session_id': 'flutter-app'
      }),
    );
    
    print('Result: ${response.body}');
  }
}
```

---

## 🌍 Access from Different Devices

### **Same WiFi Network**
All devices on your WiFi can access: `https://memary-chromadb.ngrok-free.app`

### **Different Networks (Internet)**
Anyone with the URL can access it (ngrok makes it public)

### **From IoT Devices**
```python
# Raspberry Pi, Arduino with WiFi, ESP32, etc.
import urequests  # for MicroPython
import ubinascii

def send_to_memary(image_bytes):
    b64 = ubinascii.b2a_base64(image_bytes).decode('ascii')
    
    response = urequests.post(
        'https://memary-chromadb.ngrok-free.app/store',
        json={'image_base64': b64, 'session_id': 'iot-device'}
    )
    return response.json()
```

---

## ⚠️ Important Notes

1. **Ngrok Free Tier**: First-time visitors see an interstitial page
   - Solution: Visit the URL in browser once and click "Visit Site"
   
2. **CORS**: Already enabled for all origins (`*`)

3. **Rate Limits**: Ngrok free has bandwidth limits
   - For production: Upgrade ngrok or deploy to cloud (Railway, Heroku)

4. **Session IDs**: Use unique session IDs per device/user to organize memories

5. **Security**: Consider adding authentication for production use

---

## 🧪 Test Your Pipeline

```bash
# 1. Store an image
curl -X POST https://memary-chromadb.ngrok-free.app/store_text \
  -H "Content-Type: application/json" \
  -d '{"text_summary": "Red mug on desk", "session_id": "test"}'

# 2. Search for it
curl "https://memary-chromadb.ngrok-free.app/search?query=red%20mug"

# 3. Get statistics
curl https://memary-chromadb.ngrok-free.app/statistics
```

---

## 📊 Monitor API Usage

Visit: **`http://localhost:4040`** (on your server machine)

See real-time:
- API requests from all devices
- Response times
- Request/response bodies
- Error rates

---

## 🎯 Use Cases

- **📱 Mobile app** - Store photos from phone
- **🖥️ Desktop app** - Process screenshots
- **🤖 IoT device** - ESP32 camera uploads
- **🌐 Web app** - Browser-based image analysis
- **🔬 Research** - Collect data from multiple devices
- **👥 Team collaboration** - Share memory database

**Your API is live and accessible from anywhere!** 🌍

