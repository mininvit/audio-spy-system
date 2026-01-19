# Создайте server-minimal.py для теста
@'
import os
from aiohttp import web

app = web.Application()

@app.get("/")
async def home(request):
    return web.Response(text='''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎧 Audio System</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; }
            .status { color: green; font-size: 24px; margin: 20px; }
            button { padding: 15px 30px; font-size: 18px; margin: 10px; }
        </style>
    </head>
    <body>
        <h1>🎧 Audio Streaming System</h1>
        <div class="status">✅ SERVER IS RUNNING</div>
        <p>WebSocket: <code id="ws-url">wss://</code></p>
        <button onclick="test()">Test WebSocket</button>
        <div id="result"></div>
        
        <script>
            document.getElementById("ws-url").textContent = "wss://" + window.location.host + "/ws";
            function test() {
                const ws = new WebSocket("wss://" + window.location.host + "/ws");
                ws.onopen = () => document.getElementById("result").innerHTML = "✅ WebSocket connected!";
                ws.onerror = () => document.getElementById("result").innerHTML = "❌ WebSocket error";
            }
        </script>
    </body>
    </html>
    ''', content_type='text/html')

@app.get("/health")
async def health(request):
    return web.json_response({"status": "ok", "service": "audio"})

@app.get("/ws")
async def websocket(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    await ws.send_str('{"status":"connected"}')
    
    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            await ws.send_str(f'{{"echo":"{msg.data}"}}')
    
    return ws

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Server started on port {port}")
    web.run_app(app, host="0.0.0.0", port=port, access_log=None)
'@ | Out-File -FilePath "server-minimal.py" -Encoding UTF8