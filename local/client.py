#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
АУДИО КЛИЕНТ - РАБОЧАЯ ВЕРСИЯ
"""
import asyncio
import websockets
import json
import base64
import time
import sys
import numpy as np
import sounddevice as sd

# ========== НАСТРОЙКИ ==========
SERVER_URL = "ws://localhost:8000/ws"
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
CHANNELS = 1

class AudioClient:
    def __init__(self):
        self.running = True
        self.ws = None
        self.stream = None
        self.packet_count = 0
        
    async def connect(self):
        """Подключение к серверу"""
        print(f"🔗 Подключение к {SERVER_URL}...")
        
        try:
            self.ws = await websockets.connect(SERVER_URL)
            
            await self.ws.send(json.dumps({
                "type": "spy",
                "sample_rate": SAMPLE_RATE,
                "chunk_size": CHUNK_SIZE,
                "channels": CHANNELS
            }))
            
            print("✅ Подключено к серверу")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    def setup_microphone(self):
        """Настройка микрофона"""
        print("\n🎤 Настройка микрофона...")
        
        try:
            # Тест микрофона
            print("Тест микрофона (3 секунды)...")
            recording = sd.rec(int(3 * SAMPLE_RATE), 
                             samplerate=SAMPLE_RATE, 
                             channels=CHANNELS,
                             dtype='int16')
            sd.wait()
            
            audio = recording.flatten().astype(np.float32) / 32768.0
            rms = np.sqrt(np.mean(audio**2))
            print(f"Уровень теста: {rms:.4f}")
            
            # Запуск микрофона
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                blocksize=CHUNK_SIZE,
                channels=CHANNELS,
                dtype='int16'
            )
            
            self.stream.start()
            print("✅ Микрофон запущен")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка микрофона: {e}")
            return False
    
    async def send_audio(self):
        """Отправка аудио"""
        print("\n📤 Начало передачи...")
        print("💬 ГОВОРИТЕ В МИКРОФОН!")
        print("Ctrl+C для остановки")
        print("-" * 50)
        
        start_time = time.time()
        
        while self.running and self.ws:
            try:
                # Читаем аудио
                data, overflowed = self.stream.read(CHUNK_SIZE)
                
                if overflowed:
                    print("⚠️  Buffer overflow")
                
                # Конвертируем
                audio_int16 = data.astype(np.int16)
                audio_bytes = audio_int16.tobytes()
                
                # Проверяем размер
                if len(audio_bytes) != CHUNK_SIZE * 2:
                    continue
                
                # Отправляем
                encoded = base64.b64encode(audio_bytes).decode('ascii')
                
                await self.ws.send(json.dumps({
                    "type": "audio",
                    "data": encoded,
                    "packet_id": self.packet_count,
                    "timestamp": time.time()
                }))
                
                self.packet_count += 1
                
                # Статистика
                if self.packet_count % 10 == 0:
                    audio_float = audio_int16.astype(np.float32) / 32768.0
                    rms = np.sqrt(np.mean(audio_float**2))
                    level = int(min(rms * 40, 30))
                    bars = '█' * level
                    
                    elapsed = time.time() - start_time
                    rate = self.packet_count / elapsed if elapsed > 0 else 0
                    
                    print(f"\r🔊 [{bars:30}] {rms:.3f} | Пакеты: {self.packet_count} | {rate:.1f}/сек", end="")
                
                await asyncio.sleep(0.001)
                
            except Exception as e:
                print(f"\n⚠️  Ошибка отправки: {e}")
                break
    
    async def run(self):
        """Основной цикл"""
        print("\n" + "="*60)
        print("🎧 АУДИО КЛИЕНТ")
        print("="*60)
        
        if not await self.connect():
            return
        
        if not self.setup_microphone():
            await self.cleanup()
            return
        
        try:
            await self.send_audio()
        except KeyboardInterrupt:
            print("\n\n⏹️  Остановка...")
        except Exception as e:
            print(f"\n💥 Ошибка: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Очистка"""
        self.running = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            print("\n✅ Микрофон остановлен")
        
        if self.ws:
            await self.ws.close()
            print("✅ Соединение закрыто")
        
        print(f"\n📊 Отправлено пакетов: {self.packet_count}")
        print("👋 Завершено")

def main():
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    client = AudioClient()
    
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\n👋 Остановлено")

if __name__ == "__main__":
    main()