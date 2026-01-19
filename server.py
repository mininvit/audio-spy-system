# server-minimal.py - минимальная рабочая версия
import os
from aiohttp import web

app = web.Application()

@app.get('/')
async def home(request):
    return web.Response(text='''
    <html><body>
    <h1>✅ Audio System Works!</h1>
    <p>Server is running on Render</p>
    <script>
        const ws = new WebSocket('wss://' + window.location.host + '/ws');
        ws.onopen = () => console.log('✅ WebSocket connected');
        ws.onerror = (e) => console.log('❌ WebSocket error:', e);
    </script>
    </body></html>
    ''', content_type='text/html')

@app.get('/health')
async def health(request):
    return web.json_response({'status': 'ok', 'service': 'audio'})

@app.get('/ws')
async def websocket(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    await ws.send_str('{"status":"connected"}')
    
    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            await ws.send_str(f'{{"echo":"{msg.data}"}}')
    
    return ws

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f'🚀 Server started on port {port}')
    web.run_app(app, host='0.0.0.0', port=port)