@'
import asyncio
import websockets
import json
import time
import base64
import sys

# Конфигурация
SERVER_URL = "wss://audio-spy-system.onrender.com/ws"

async def simulate_audio_client():
    """Тестовый клиент, имитирующий передачу аудио"""
    print("=" * 50)
    print("🎤 Audio Spy Client")
    print(f"📡 Server: {SERVER_URL}")
    print("=" * 50)
    
    try:
        async with websockets.connect(SERVER_URL) as ws:
            # Регистрируемся как источник аудио
            await ws.send(json.dumps({
                "type": "spy",
                "device": "audio_spy",
                "timestamp": time.time()
            }))
            
            print("✅ Connected to server as audio source")
            print("🎤 Simulating audio transmission...")
            print("Press Ctrl+C to stop\n")
            
            packet_count = 0
            
            try:
                while True:
                    # Имитируем аудио данные (в реальности здесь будет pyaudio)
                    simulated_audio = b"fake_audio_data_" + str(packet_count).encode()
                    encoded_audio = base64.b64encode(simulated_audio).decode('utf-8')
                    
                    # Отправляем "аудио" на сервер
                    await ws.send(json.dumps({
                        "type": "audio",
                        "data": encoded_audio,
                        "timestamp": time.time(),
                        "packet": packet_count,
                        "size": len(simulated_audio)
                    }))
                    
                    packet_count += 1
                    
                    # Показываем прогресс
                    if packet_count % 10 == 0:
                        print(f"📦 Sent {packet_count} packets...")
                    
                    # Пауза между пакетами
                    await asyncio.sleep(0.1)  # 10 пакетов в секунду
                    
            except KeyboardInterrupt:
                print("\n⏹️ Stopping...")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print(f"1. Check server URL: {SERVER_URL}")
        print("2. Make sure server is running")
        print("3. Check internet connection")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(simulate_audio_client())
    except KeyboardInterrupt:
        print("\n👋 Client stopped")
'@ | Out-File -FilePath "client.py" -Encoding UTF8