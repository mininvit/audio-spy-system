import os
from aiohttp import web

app = web.Application()

# Главная страница - ПРАВИЛЬНЫЙ синтаксис
async def home(request):
    return web.Response(text="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>✅ Audio System</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; }
            .success { color: green; font-size: 24px; margin: 20px; }
            button { padding: 15px 30px; font-size: 18px; margin: 10px; }
        </style>
    </head>
    <body>
        <h1>🎧 Audio Streaming System</h1>
        <div class="success">✅ SERVER IS RUNNING</div>
        <p>WebSocket endpoint: <code>wss://<span id="host"></span>/ws</code></p>
        <button onclick="test()">Test WebSocket</button>
        <div id="result"></div>
        
        <script>
            document.getElementById("host").textContent = window.location.host;
            function test() {
                const ws = new WebSocket("wss://" + window.location.host + "/ws");
                ws.onopen = () => document.getElementById("result").innerHTML = "✅ WebSocket connected!";
                ws.onerror = () => document.getElementById("result").innerHTML = "❌ WebSocket error";
            }
        </script>
    </body>
    </html>
    """, content_type="text/html")

# Health check
async def health(request):
    return web.json_response({"status": "ok", "service": "audio"})

# WebSocket handler
async def websocket(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    await ws.send_str('{"status":"connected"}')
    
    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            await ws.send_str(f'{{"echo":"{msg.data}"}}')
    
    return ws

# Настройка маршрутов - ПРАВИЛЬНО!
app.router.add_get("/", home)
app.router.add_get("/health", health)
app.router.add_get("/ws", websocket)

# Запуск сервера
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Server started on port {port}")
    print(f"🌐 Open: https://audio-spy-system.onrender.com")
    web.run_app(app, host="0.0.0.0", port=port)