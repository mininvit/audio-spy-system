import asyncio
import json
import os
import time
from aiohttp import web

# Храним подключения
audio_sources = set()
listeners = set()

app = web.Application()

# Главная страница с РАБОЧИМ воспроизведением
async def home(request):
    return web.Response(text="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎧 Audio Streaming System</title>
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
                <h1>🎧 Audio Streaming System</h1>
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
                    <div>Buffer size: <span id="bufferSize">0</span> chunks</div>
                </div>
                
                <div class="info-panel">
                    <div class="info-row">
                        <span>Server URL:</span>
                        <span id="serverUrl">localhost:8000</span>
                    </div>
                    <div class="info-row">
                        <span>Audio Sources:</span>
                        <span id="sourcesCount">0</span>
                    </div>
                    <div class="info-row">
                        <span>WebSocket Status:</span>
                        <span id="wsStatus">Disconnected</span>
                    </div>
                    <div class="info-row">
                        <span>Audio Format:</span>
                        <span>16 kHz, mono, int16</span>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const WS_URL = 'ws://' + window.location.host + '/ws';
            let socket = null;
            let audioContext = null;
            let audioQueue = [];
            let isPlaying = false;
            let packetCount = 0;
            let audioBufferSize = 0;
            
            // Функция для правильного декодирования и воспроизведения аудио
            function processAudioData(base64Data) {
                try {
                    console.log("🎵 Processing audio data, size:", base64Data.length);
                    
                    // 1. Декодируем base64 в бинарные данные
                    const binaryStr = atob(base64Data);
                    const len = binaryStr.length;
                    
                    if (len < 100) {
                        console.warn("⚠️ Too little data:", len);
                        return null;
                    }
                    
                    // 2. Создаем ArrayBuffer и копируем данные
                    const arrayBuffer = new ArrayBuffer(len);
                    const uint8Array = new Uint8Array(arrayBuffer);
                    
                    for (let i = 0; i < len; i++) {
                        uint8Array[i] = binaryStr.charCodeAt(i);
                    }
                    
                    // 3. Создаем Int16Array из ArrayBuffer (little-endian)
                    const int16Array = new Int16Array(arrayBuffer);
                    
                    // 4. Конвертируем int16 в float32 (-1.0 до 1.0)
                    const float32Array = new Float32Array(int16Array.length);
                    for (let i = 0; i < int16Array.length; i++) {
                        // int16: -32768 до 32767 → float32: -1.0 до 1.0
                        float32Array[i] = Math.max(-1, Math.min(1, int16Array[i] / 32768.0));
                    }
                    
                    console.log("✅ Audio converted, samples:", int16Array.length);
                    return float32Array;
                    
                } catch (error) {
                    console.error('❌ Audio decoding error:', error);
                    return null;
                }
            }
            
            // Функция воспроизведения из очереди
            function playFromQueue() {
                if (!audioContext) {
                    try {
                        audioContext = new (window.AudioContext || window.webkitAudioContext)({
                            sampleRate: 16000
                        });
                        console.log("✅ AudioContext created, sample rate:", audioContext.sampleRate);
                    } catch (error) {
                        console.error("❌ Failed to create AudioContext:", error);
                        return;
                    }
                }
                
                if (audioQueue.length === 0) {
                    isPlaying = false;
                    document.getElementById('bufferSize').textContent = '0';
                    return;
                }
                
                isPlaying = true;
                document.getElementById('bufferSize').textContent = audioQueue.length;
                
                // Берем данные из очереди
                const audioData = audioQueue.shift();
                
                try {
                    // Создаем AudioBuffer
                    const audioBuffer = audioContext.createBuffer(1, audioData.length, 16000);
                    audioBuffer.copyToChannel(audioData, 0);
                    
                    // Создаем источник
                    const source = audioContext.createBufferSource();
                    source.buffer = audioBuffer;
                    
                    // Создаем GainNode для контроля громкости
                    const gainNode = audioContext.createGain();
                    gainNode.gain.value = 1.0;
                    
                    // Подключаем цепочку
                    source.connect(gainNode);
                    gainNode.connect(audioContext.destination);
                    
                    // Запускаем воспроизведение
                    source.start();
                    
                    // Когда завершится, воспроизводим следующий чанк
                    source.onended = () => {
                        setTimeout(playFromQueue, 0);
                    };
                    
                    console.log("▶️ Playing audio chunk, duration:", audioBuffer.duration.toFixed(3), "s");
                    
                } catch (error) {
                    console.error("❌ Playback error:", error);
                    setTimeout(playFromQueue, 0);
                }
            }
            
            // Функция для добавления аудио в очередь
            function addAudioToQueue(base64Data) {
                const audioData = processAudioData(base64Data);
                if (audioData) {
                    audioQueue.push(audioData);
                    
                    // Если не воспроизводится, запускаем
                    if (!isPlaying) {
                        playFromQueue();
                    }
                    
                    // Ограничиваем размер очереди
                    if (audioQueue.length > 10) {
                        audioQueue.shift();
                        console.log("⚠️ Queue overflow, removing old chunk");
                    }
                }
            }
            
            function connectWebSocket() {
                if (socket && socket.readyState === WebSocket.OPEN) return;
                
                updateStatus('Connecting...', 'disconnected');
                document.getElementById('wsStatus').textContent = 'Connecting';
                
                socket = new WebSocket(WS_URL);
                
                socket.onopen = function() {
                    updateStatus('✅ Connected to server', 'connected');
                    document.getElementById('connectBtn').disabled = true;
                    document.getElementById('disconnectBtn').disabled = false;
                    document.getElementById('wsStatus').textContent = 'Connected';
                    
                    // Register as listener
                    socket.send(JSON.stringify({
                        type: 'listener',
                        device: 'web_interface',
                        timestamp: Date.now()
                    }));
                    
                    console.log("✅ WebSocket connected");
                };
                
                socket.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        console.log("📥 Received:", data.type, "size:", data.data ? data.data.length : 0);
                        
                        if (data.type === 'status') {
                            updateStatus(data.message, 'connected');
                            document.getElementById('sourcesCount').textContent = data.sources_count || 0;
                            
                            if (data.has_source) {
                                document.getElementById('audioIndicator').classList.add('active');
                            } else {
                                document.getElementById('audioIndicator').classList.remove('active');
                            }
                        }
                        else if (data.type === 'audio') {
                            packetCount++;
                            document.getElementById('packetCount').textContent = packetCount;
                            document.getElementById('audioIndicator').classList.add('active');
                            
                            // Обрабатываем и воспроизводим аудио
                            if (data.data && data.data.length > 100) {
                                addAudioToQueue(data.data);
                            } else {
                                console.warn("⚠️ Audio packet too small:", data.data.length);
                            }
                        }
                    } catch (error) {
                        console.error('❌ Error processing message:', error);
                    }
                };
                
                socket.onclose = function() {
                    updateStatus('❌ Connection closed', 'disconnected');
                    document.getElementById('connectBtn').disabled = false;
                    document.getElementById('disconnectBtn').disabled = true;
                    document.getElementById('audioIndicator').classList.remove('active');
                    document.getElementById('wsStatus').textContent = 'Disconnected';
                    
                    console.log("🔌 WebSocket closed");
                    
                    // Auto-reconnect after 3 seconds
                    setTimeout(connectWebSocket, 3000);
                };
                
                socket.onerror = function(error) {
                    console.error('❌ WebSocket error:', error);
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
                document.getElementById('bufferSize').textContent = '0';
                
                // Очищаем очередь
                audioQueue = [];
                isPlaying = false;
                
                console.log("⏹️ WebSocket disconnected manually");
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
                console.log("🌐 Page loaded, connecting...");
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
        "service": "audio-streaming-system",
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
    print(f"🆕 New connection from {request.remote}")
    
    try:
        # Ждем первое сообщение
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    print(f"📥 Received: {data.get('type')}")
                    
                    if data.get('type') == 'spy':
                        client_type = 'spy'
                        audio_sources.add(ws)
                        print(f"🎤 Audio source connected. Total: {len(audio_sources)}")
                        
                        # Уведомляем слушателей
                        for listener in listeners:
                            try:
                                await listener.send_str(json.dumps({
                                    'type': 'status',
                                    'message': f'Audio source available ({len(audio_sources)} total)',
                                    'has_source': True,
                                    'sources_count': len(audio_sources)
                                }))
                            except:
                                pass
                        
                        # Обрабатываем аудио
                        async for audio_msg in ws:
                            if audio_msg.type == web.WSMsgType.TEXT:
                                try:
                                    audio_data = json.loads(audio_msg.data)
                                    
                                    if audio_data.get('type') == 'audio':
                                        data_len = len(audio_data.get('data', ''))
                                        print(f"🎵 Audio #{audio_data.get('packet_id', 0)}, size: {data_len}")
                                        
                                        # Пересылаем слушателям
                                        for listener in list(listeners):
                                            try:
                                                await listener.send_str(audio_msg.data)
                                            except:
                                                listeners.discard(listener)
                                        
                                except Exception as e:
                                    print(f"❌ Audio processing error: {e}")
                        
                    elif data.get('type') == 'listener':
                        client_type = 'listener'
                        listeners.add(ws)
                        print(f"🎧 Listener connected. Total: {len(listeners)}")
                        
                        # Отправляем статус
                        await ws.send_str(json.dumps({
                            'type': 'status',
                            'message': 'Ready for audio streaming' if audio_sources else 'Waiting for audio source',
                            'has_source': len(audio_sources) > 0,
                            'sources_count': len(audio_sources)
                        }))
                        
                        # Держим соединение
                        try:
                            async for _ in ws:
                                pass
                        except:
                            pass
                        
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON")
    
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    
    finally:
        # Очистка
        if client_type == 'spy':
            audio_sources.discard(ws)
            print(f"🎤 Audio source disconnected. Remaining: {len(audio_sources)}")
        elif client_type == 'listener':
            listeners.discard(ws)
            print(f"🎧 Listener disconnected. Remaining: {len(listeners)}")
    
    print(f"👋 Connection closed")
    return ws

# Routes
app.router.add_get('/', home)
app.router.add_get('/health', health)
app.router.add_get('/ws', websocket_handler)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"🚀 Audio Streaming Server started on port {port}")
    print(f"🌐 Web interface: http://localhost:{port}")
    print(f"📡 WebSocket: ws://localhost:{port}/ws")
    print(f"🔧 Waiting for connections...")
    web.run_app(app, host='0.0.0.0', port=port)