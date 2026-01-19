import asyncio
import json
import os
from aiohttp import web
import base64

# Храним подключения
audio_sources = set()  # Python клиенты (микрофоны)
listeners = set()      # Веб-клиенты (слушатели)

app = web.Application()

# Главная страница
async def home(request):
    return web.Response(text="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎧 Audio Spy System</title>
        <meta charset="UTF-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                width: 100%;
                max-width: 800px;
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                font-size: 2.5rem;
                margin-bottom: 10px;
            }
            .content {
                padding: 40px;
            }
            .status-card {
                background: #f8f9fa;
                border-radius: 15px;
                padding: 25px;
                margin-bottom: 30px;
                border-left: 5px solid #dc3545;
                transition: all 0.3s ease;
            }
            .status-card.connected {
                border-left-color: #28a745;
                background: #d4edda;
            }
            .controls {
                display: flex;
                gap: 20px;
                justify-content: center;
                margin-bottom: 30px;
            }
            .btn {
                padding: 15px 35px;
                font-size: 1.1rem;
                border: none;
                border-radius: 50px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s ease;
                min-width: 200px;
            }
            .btn-primary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .btn-primary:hover:not(:disabled) {
                transform: translateY(-3px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }
            .btn-primary:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            .btn-danger {
                background: linear-gradient(135deg, #f5365c 0%, #f56036 100%);
                color: white;
            }
            .btn-danger:hover:not(:disabled) {
                transform: translateY(-3px);
                box-shadow: 0 10px 20px rgba(245, 54, 92, 0.4);
            }
            .info-panel {
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin-top: 20px;
            }
            .info-row {
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #dee2e6;
            }
            .info-row:last-child {
                border-bottom: none;
            }
            .audio-indicator {
                text-align: center;
                margin: 20px 0;
                padding: 15px;
                background: #1a1a2e;
                color: white;
                border-radius: 10px;
                display: none;
            }
            .audio-indicator.active {
                display: block;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.7; }
                100% { opacity: 1; }
            }
            @media (max-width: 768px) {
                .content { padding: 20px; }
                .controls { flex-direction: column; align-items: center; }
                .btn { width: 100%; max-width: 300px; }
                .header h1 { font-size: 2rem; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎧 Audio Spy System</h1>
                <p>Real-time audio streaming from microphone to browser</p>
            </div>
            
            <div class="content">
                <div id="statusCard" class="status-card">
                    <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 10px;">
                        <span id="statusIcon">🔴</span>
                        <span id="statusTitle">Connection Status</span>
                    </div>
                    <div id="statusMessage">❌ Not connected to server</div>
                </div>
                
                <div class="controls">
                    <button id="connectBtn" class="btn btn-primary" onclick="connectWebSocket()">
                        🔗 Start Listening
                    </button>
                    <button id="disconnectBtn" class="btn btn-danger" onclick="disconnectWebSocket()" disabled>
                        ⏹️ Stop Listening
                    </button>
                </div>
                
                <div id="audioIndicator" class="audio-indicator">
                    <div style="font-size: 1.3rem;">🔊 Live Audio Streaming...</div>
                    <div style="margin-top: 10px;">Packets received: <span id="packetCount">0</span></div>
                </div>
                
                <div class="info-panel">
                    <div class="info-row">
                        <span>Server URL:</span>
                        <span id="serverUrl">audio-spy-system.onrender.com</span>
                    </div>
                    <div class="info-row">
                        <span>Audio Sources Active:</span>
                        <span id="sourcesCount">0</span>
                    </div>
                    <div class="info-row">
                        <span>WebSocket Status:</span>
                        <span id="wsStatus">Disconnected</span>
                    </div>
                    <div class="info-row">
                        <span>Connection URL:</span>
                        <span>wss://<span id="wsUrl">audio-spy-system.onrender.com</span>/ws</span>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const WS_URL = 'wss://' + window.location.host + '/ws';
            let socket = null;
            let audioContext = null;
            let packetCount = 0;
            
            function connectWebSocket() {
                if (socket && socket.readyState === WebSocket.OPEN) return;
                
                updateStatus('Connecting...', 'disconnected');
                document.getElementById('wsStatus').textContent = 'Connecting...';
                
                socket = new WebSocket(WS_URL);
                
                socket.onopen = function() {
                    updateStatus('✅ Connected to server', 'connected');
                    document.getElementById('connectBtn').disabled = true;
                    document.getElementById('disconnectBtn').disabled = false;
                    document.getElementById('wsStatus').textContent = 'Connected';
                    document.getElementById('wsUrl').textContent = window.location.host;
                    
                    // Register as listener
                    socket.send(JSON.stringify({
                        type: 'listener',
                        device: 'web_interface'
                    }));
                };
                
                socket.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        
                        if (data.type === 'status') {
                            updateStatus(data.message, 'connected');
                            document.getElementById('sourcesCount').textContent = data.sources_count || 0;
                            
                            if (data.has_source) {
                                document.getElementById('audioIndicator').classList.add('active');
                            }
                        }
                        else if (data.type === 'audio') {
                            packetCount++;
                            document.getElementById('packetCount').textContent = packetCount;
                            document.getElementById('audioIndicator').classList.add('active');
                            
                            // Play audio if data exists
                            if (data.data) {
                                playAudio(data.data);
                            }
                        }
                    } catch (error) {
                        console.error('Error:', error);
                    }
                };
                
                socket.onclose = function() {
                    updateStatus('❌ Connection closed', 'disconnected');
                    document.getElementById('connectBtn').disabled = false;
                    document.getElementById('disconnectBtn').disabled = true;
                    document.getElementById('audioIndicator').classList.remove('active');
                    document.getElementById('wsStatus').textContent = 'Disconnected';
                    
                    // Auto-reconnect after 3 seconds
                    setTimeout(connectWebSocket, 3000);
                };
                
                socket.onerror = function(error) {
                    updateStatus('❌ Connection error', 'disconnected');
                    document.getElementById('wsStatus').textContent = 'Error';
                };
            }
            
            function disconnectWebSocket() {
                if (socket) {
                    socket.close();
                }
                updateStatus('Disconnected', 'disconnected');
                document.getElementById('connectBtn').disabled = false;
                document.getElementById('disconnectBtn').disabled = true;
                document.getElementById('audioIndicator').classList.remove('active');
                document.getElementById('wsStatus').textContent = 'Disconnected';
                packetCount = 0;
                document.getElementById('packetCount').textContent = '0';
                document.getElementById('sourcesCount').textContent = '0';
            }
            
            function playAudio(base64Data) {
                if (!audioContext) {
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                }
                
                try {
                    const binaryString = atob(base64Data);
                    const bytes = new Uint8Array(binaryString.length);
                    for (let i = 0; i < binaryString.length; i++) {
                        bytes[i] = binaryString.charCodeAt(i);
                    }
                    
                    audioContext.decodeAudioData(bytes.buffer, function(buffer) {
                        const source = audioContext.createBufferSource();
                        source.buffer = buffer;
                        source.connect(audioContext.destination);
                        source.start();
                    });
                } catch (error) {
                    console.error('Audio error:', error);
                }
            }
            
            function updateStatus(message, type) {
                document.getElementById('statusMessage').textContent = message;
                const card = document.getElementById('statusCard');
                card.className = 'status-card';
                if (type === 'connected') {
                    card.classList.add('connected');
                    document.getElementById('statusIcon').textContent = '🟢';
                    document.getElementById('statusTitle').textContent = 'Connected';
                } else {
                    document.getElementById('statusIcon').textContent = '🔴';
                    document.getElementById('statusTitle').textContent = 'Disconnected';
                }
            }
            
            // Auto-connect on page load
            window.onload = function() {
                document.getElementById('serverUrl').textContent = window.location.host;
                document.getElementById('wsUrl').textContent = window.location.host;
                setTimeout(connectWebSocket, 1000);
            };
        </script>
    </body>
    </html>
    """, content_type="text/html")

# Health check
async def health(request):
    return web.json_response({
        "status": "ok", 
        "service": "audio-spy-system",
        "stats": {
            "audio_sources": len(audio_sources),
            "listeners": len(listeners)
        }
    })

# WebSocket handler
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    client_type = None
    
    try:
        # Wait for first message to identify client
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                
                if data.get('type') == 'spy':
                    # Python client (audio source)
                    client_type = 'spy'
                    audio_sources.add(ws)
                    print(f"🎤 Audio source connected. Total sources: {len(audio_sources)}")
                    
                    # Notify all listeners
                    for listener in listeners:
                        if not listener.closed:
                            await listener.send_str(json.dumps({
                                'type': 'status',
                                'message': f'Audio source available (total: {len(audio_sources)})',
                                'has_source': True,
                                'sources_count': len(audio_sources)
                            }))
                    
                    # Forward audio to listeners
                    async for audio_msg in ws:
                        if audio_msg.type == web.WSMsgType.TEXT:
                            # Forward to all listeners
                            for listener in listeners:
                                if not listener.closed:
                                    await listener.send_str(audio_msg.data)
                    break
                    
                elif data.get('type') == 'listener':
                    # Web client (listener)
                    client_type = 'listener'
                    listeners.add(ws)
                    print(f"🎧 Listener connected. Total listeners: {len(listeners)}")
                    
                    # Send current status
                    await ws.send_str(json.dumps({
                        'type': 'status',
                        'message': 'Ready for audio streaming' if audio_sources else 'Waiting for audio source',
                        'has_source': len(audio_sources) > 0,
                        'sources_count': len(audio_sources)
                    }))
                    
                    # Keep connection alive
                    async for _ in ws:
                        pass
                    break
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    
    finally:
        # Cleanup
        if client_type == 'spy' and ws in audio_sources:
            audio_sources.remove(ws)
            print(f"🎤 Audio source disconnected. Remaining: {len(audio_sources)}")
            
            # Notify listeners if no sources left
            if not audio_sources:
                for listener in listeners:
                    if not listener.closed:
                        await listener.send_str(json.dumps({
                            'type': 'status',
                            'message': 'No audio sources available',
                            'has_source': False,
                            'sources_count': 0
                        }))
                        
        elif client_type == 'listener' and ws in listeners:
            listeners.remove(ws)
            print(f"🎧 Listener disconnected. Remaining: {len(listeners)}")
    
    return ws

# Setup routes
app.router.add_get('/', home)
app.router.add_get('/health', health)
app.router.add_get('/ws', websocket_handler)

# Start server
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"🚀 Audio Spy Server started on port {port}")
    print(f"🌐 Web interface: https://audio-spy-system.onrender.com")
    print(f"📡 WebSocket: wss://audio-spy-system.onrender.com/ws")
    print(f"🔧 Waiting for connections...")
    web.run_app(app, host='0.0.0.0', port=port)