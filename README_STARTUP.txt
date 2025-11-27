╔══════════════════════════════════════════════════════════════╗
║                  🧠 REMEMBAR - QUICK START                   ║
╚══════════════════════════════════════════════════════════════╝

🚀 START SERVICES (AUTOMATIC):
   ./start_services.sh

🛑 STOP SERVICES:
   ./stop_services.sh

🌐 WEB INTERFACE:
   Opens automatically, or visit:
   file:///Users/arkanfadhilkautsar/Downloads/remembar/web-test/index.html

📍 ENDPOINTS:
   • API Service:    http://localhost:8000
   • Vector Store:   http://localhost:8001

🗑️  CLEAR STORAGE:
   Option 1: Click button in web interface
   Option 2: curl -X POST http://localhost:8000/clear_storage

💾 DATA LOCATION:
   Persistent storage: vector-store/.chroma/
   (Keeps data across restarts when vector store is running)

📝 LOGS:
   • api-service/api.log
   • vector-store/vectorstore.log

📚 FULL DOCS:
   See STARTUP_GUIDE.md for detailed instructions

═══════════════════════════════════════════════════════════════


