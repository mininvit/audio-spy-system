# Создайте файл server.py
@'
import os
from aiohttp import web

# Создаем приложение
app = web.Application()

# Главная страница
@app.get("/")
async def home(request):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎧 Аудио Система</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; }
            .success { color: green; font-size: 24px; }
            button { padding: 15px 30px; font-size: 18px; margin: 10px; }
        </style>
    </head>
    <body>
        <h1>🎧 Аудио Система</h1>
        <div class="success">✅ СЕРВЕР РАБОТАЕТ!</div>
        <p>WebSocket: <code>wss://<span id="host"></span>/ws</code></p>
        <button onclick="test()">Тест WebSocket</button>
        <div id="result"></div>
        <script>
            document.getElementById('host').textContent = window.location.host;
            function test() {
                const ws = new WebSocket('wss://' + window.location.host + '/ws');
                ws.onopen = () => document.getElementById('result').innerHTML = '✅ WebSocket работает!';
                ws.onerror = () => document.getElementById('result').innerHTML = '❌ WebSocket ошибка';
            }
        </script>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

# Health check для Railway
@app.get("/health")
async def health(request):
    return web.json_response({
        "status": "ok",
        "service": "audio-server",
        "port": os.environ.get("PORT", "not set")
    })

# WebSocket endpoint
@app.get("/ws")
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    await ws.send_str('{"status":"connected","type":"audio-server"}')
    
    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            # Эхо-ответ
            await ws.send_str(f'{{"echo":"{msg.data}"}}')
    
    return ws

# Запуск сервера
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Сервер запущен на порту {port}")
    print(f"🌐 Откройте: http://localhost:{port}")
    print(f"📡 WebSocket: ws://localhost:{port}/ws")
    web.run_app(app, host="0.0.0.0", port=port)
'@ | Set-Content -Path "server.py" -Encoding UTF8