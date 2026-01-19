# -*- coding: utf-8 -*-
"""
АУДИО КЛИЕНТ БЕЗ ТРЕСКОВ И ШУМОВ
"""
import asyncio
import websockets
import json
import base64
import time
import sys
import numpy as np
import sounddevice as sd
from queue import Queue
import threading

# ========== НАСТРОЙКИ ==========
SERVER_URL = "wss://audio-spy-system.onrender.com/ws"
SAMPLE_RATE = 44100  # Стандартная частота 44.1 кГц
CHUNK_SIZE = 1024    # Размер чанка
DEVICE_ID = None     # Устройство по умолчанию

class CleanAudioClient:
    def __init__(self):
        self.running = True
        self.ws = None
        self.audio_queue = Queue(maxsize=10)  # Маленький буфер
        self.packet_count = 0
        self.stream = None
        self.last_time = time.time()
        
    async def connect(self):
        """Подключение к серверу"""
        print("🔗 Подключение...")
        try:
            self.ws = await websockets.connect(SERVER_URL)
            
            # Отправляем конфигурацию
            await self.ws.send(json.dumps({
                "type": "spy",
                "sample_rate": SAMPLE_RATE,
                "channels": 1,
                "format": "int16"
            }))
            
            print("✅ Подключено!")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    def setup_audio(self):
        """Настройка аудио устройства"""
        try:
            print("🎤 Настройка микрофона...")
            
            # Показываем устройства
            devices = sd.query_devices()
            print(f"Найдено устройств: {len(devices)}")
            
            # Используем устройство по умолчанию
            default_device = sd.default.device[0]
            print(f"Используется устройство: {default_device}")
            
            return True
        except Exception as e:
            print(f"⚠️  Ошибка настройки: {e}")
            return True
    
    def audio_callback(self, indata, frames, time_info, status):
        """
        КОЛБЕК ДЛЯ ЗАХВАТА АУДИО
        Правильная конвертация float32 -> int16
        """
        if status:
            print(f"Статус аудио: {status}")
        
        try:
            # Копируем данные
            audio_data = indata.copy().flatten()
            
            # 1. Убираем DC offset (постоянную составляющую)
            audio_data = audio_data - np.mean(audio_data)
            
            # 2. Мягкое ограничение для предотвращения клиппинга
            max_val = np.max(np.abs(audio_data))
            if max_val > 0.9:
                audio_data = audio_data * 0.9 / max_val
            
            # 3. Конвертация в int16 (ПРАВИЛЬНО!)
            audio_int16 = np.zeros(len(audio_data), dtype=np.int16)
            
            for i in range(len(audio_data)):
                sample = audio_data[i] * 32767
                # Ограничиваем диапазон
                if sample > 32767:
                    sample = 32767
                elif sample < -32768:
                    sample = -32768
                audio_int16[i] = int(sample)
            
            # 4. Добавляем в очередь
            if not self.audio_queue.full():
                self.audio_queue.put(audio_int16.tobytes())
            
            # 5. Показываем уровень звука
            rms = np.sqrt(np.mean(audio_data**2))
            if rms > 0.01:
                level = int(rms * 30)
                print(f"\r🔊 Уровень: [{'█' * level}{' ' * (30-level)}] {rms:.4f}", end="")
                
        except Exception as e:
            print(f"\nОшибка в колбеке: {e}")
    
    def start_capture(self):
        """Запуск захвата звука"""
        print("🎤 Запуск микрофона...")
        
        try:
            self.stream = sd.InputStream(
                callback=self.audio_callback,
                channels=1,
                samplerate=SAMPLE_RATE,
                blocksize=CHUNK_SIZE,
                dtype='float32',
                device=DEVICE_ID
            )
            self.stream.start()
            
            print("✅ Микрофон готов")
            print("💬 Говорите сейчас...")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка запуска микрофона: {e}")
            return False
    
    async def send_audio(self):
        """Отправка аудио данных"""
        print("\n📤 Отправка аудио...")
        
        target_interval = CHUNK_SIZE / SAMPLE_RATE  # Время одного чанка
        
        while self.running and self.ws:
            try:
                current_time = time.time()
                
                # Синхронизация по времени
                if current_time - self.last_time < target_interval * 0.9:
                    await asyncio.sleep(0.001)
                    continue
                
                # Получаем данные
                try:
                    audio_bytes = self.audio_queue.get_nowait()
                except:
                    # Если нет данных, отправляем тишину
                    audio_bytes = bytes(CHUNK_SIZE * 2)
                
                # Создаем пакет
                packet = {
                    "type": "audio",
                    "data": base64.b64encode(audio_bytes).decode(),
                    "timestamp": time.time(),
                    "packet_id": self.packet_count,
                    "sample_rate": SAMPLE_RATE,
                    "chunk_size": len(audio_bytes)
                }
                
                # Отправляем
                await self.ws.send(json.dumps(packet))
                
                self.packet_count += 1
                self.last_time = current_time
                
                if self.packet_count % 50 == 0:
                    print(f"\n📦 Отправлено пакетов: {self.packet_count}")
                
            except Exception as e:
                print(f"\n⚠️  Ошибка отправки: {e}")
                break
        
        print("⏹️  Отправка остановлена")
    
    async def run(self):
        """Основной цикл"""
        print("\n" + "="*50)
        print("🎧 АУДИО КЛИЕНТ - ЧИСТЫЙ ЗВУК")
        print("="*50)
        
        # Настройка
        self.setup_audio()
        
        # Подключение
        if not await self.connect():
            return
        
        # Запуск микрофона
        if not self.start_capture():
            return
        
        print("\n" + "="*50)
        print("🚀 ТРАНСЛЯЦИЯ НАЧАТА")
        print("Нажмите Ctrl+C для остановки")
        print("="*50 + "\n")
        
        # Запуск отправки
        try:
            await self.send_audio()
        except KeyboardInterrupt:
            print("\n\n⏹️  Остановлено")
        except Exception as e:
            print(f"\n💥 Ошибка: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Очистка"""
        self.running = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
        
        if self.ws:
            asyncio.create_task(self.ws.close())
        
        print(f"\n📊 Итог: {self.packet_count} пакетов")
        print("👋 Завершено")

def main():
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    client = CleanAudioClient()
    
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\n👋 Остановлено")
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")

if __name__ == "__main__":
    main()