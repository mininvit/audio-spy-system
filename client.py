import asyncio
import websockets
import json
import base64
import numpy as np
import time
import sys

SERVER_URL = "wss://audio-spy-system.onrender.com/ws"

async def send_test_tone():
    """Отправляет тестовый тон 440 Гц для проверки"""
    print("🎵 Audio Test Client")
    print(f"📡 Connecting to: {SERVER_URL}")
    
    try:
        async with websockets.connect(SERVER_URL) as ws:
            # Регистрация
            await ws.send(json.dumps({
                "type": "spy",
                "device": "test_tone_generator",
                "rate": 44100,
                "channels": 1
            }))
            
            print("✅ Connected to server")
            print("🎶 Sending 440 Hz sine wave...")
            print("Press Ctrl+C to stop\n")
            
            sample_rate = 44100
            frequency = 440  # Hz
            duration = 0.1  # 100ms per chunk
            samples_per_chunk = int(sample_rate * duration)
            
            t = 0
            packet_count = 0
            
            try:
                while True:
                    # Генерируем синусоиду
                    time_points = np.linspace(t, t + duration, samples_per_chunk, endpoint=False)
                    sine_wave = np.sin(2 * np.pi * frequency * time_points)
                    
                    # Конвертируем в int16
                    audio_int16 = (sine_wave * 32767).astype(np.int16)
                    audio_bytes = audio_int16.tobytes()
                    
                    # Отправляем
                    await ws.send(json.dumps({
                        "type": "audio",
                        "data": base64.b64encode(audio_bytes).decode('utf-8'),
                        "timestamp": time.time(),
                        "packet": packet_count,
                        "rate": sample_rate
                    }))
                    
                    packet_count += 1
                    
                    if packet_count % 10 == 0:
                        print(f"📦 Sent {packet_count} packets")
                    
                    t += duration
                    await asyncio.sleep(duration)
                    
            except KeyboardInterrupt:
                print("\n⏹️ Stopping test tone...")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(send_test_tone())
    except KeyboardInterrupt:
        print("\n👋 Test stopped")