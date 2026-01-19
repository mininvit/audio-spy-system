# test_audio_no_numpy.py - тестовый тон без numpy
import asyncio
import websockets
import json
import base64
import math
import time
import sys

SERVER_URL = "wss://audio-spy-system.onrender.com/ws"

async def send_test_tone_no_numpy():
    """Тестовый тон без numpy"""
    print("🎵 Audio Test (no numpy)")
    
    async with websockets.connect(SERVER_URL) as ws:
        await ws.send(json.dumps({
            "type": "spy",
            "device": "test_tone"
        }))
        
        print("✅ Connected, sending test beeps...")
        
        sample_rate = 44100
        frequency = 440
        duration = 0.1
        samples = int(sample_rate * duration)
        
        packet_count = 0
        
        try:
            while True:
                # Генерируем синусоиду без numpy
                audio_bytes = bytearray()
                for i in range(samples):
                    # Синусоида 440 Гц
                    sample = math.sin(2 * math.pi * frequency * i / sample_rate)
                    # Конвертируем в int16
                    int_sample = int(sample * 32767)
                    # Разбиваем на 2 байта (little-endian)
                    audio_bytes.append(int_sample & 0xFF)
                    audio_bytes.append((int_sample >> 8) & 0xFF)
                
                # Отправляем
                await ws.send(json.dumps({
                    "type": "audio",
                    "data": base64.b64encode(audio_bytes).decode('utf-8'),
                    "timestamp": time.time(),
                    "packet": packet_count
                }))
                
                packet_count += 1
                if packet_count % 10 == 0:
                    print(f"📦 Packets sent: {packet_count}")
                
                await asyncio.sleep(duration)
                
        except KeyboardInterrupt:
            print("\n⏹️ Stopped")

if __name__ == "__main__":
    asyncio.run(send_test_tone_no_numpy())