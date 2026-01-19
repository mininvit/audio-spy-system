# -*- coding: utf-8 -*-
"""
АУДИО КЛИЕНТ С ЧИСТЫМ ЗВУКОМ
Без треска и искажений
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
import struct

# ========== НАСТРОЙКИ ==========
SERVER_URL = "wss://audio-spy-system.onrender.com/ws"
SAMPLE_RATE = 16000  # 16 kHz - оптимально для голоса
CHUNK_SIZE = 1024    # Размер чанка
BUFFER_SIZE = 50     # Размер буфера
DEVICE_ID = None     # None = устройство по умолчанию

class CleanAudioClient:
    def __init__(self):
        self.running = True
        self.ws = None
        self.audio_queue = Queue(maxsize=BUFFER_SIZE)
        self.packet_count = 0
        self.stream = None
        self.lock = threading.Lock()
        
    def print_info(self):
        """Информация о программе"""
        print("\n" + "="*60)
        print("🎤 AUDIO STREAM CLIENT - ЧИСТЫЙ ЗВУК")
        print("="*60)
        print(f"Сервер: {SERVER_URL}")
        print(f"Частота: {SAMPLE_RATE} Hz")
        print(f"Чанк: {CHUNK_SIZE} samples")
        print("="*60)
    
    async def connect_to_server(self):
        """Подключение к WebSocket серверу"""
        print("🔗 Подключение к серверу...")
        
        try:
            self.ws = await websockets.connect(
                SERVER_URL,
                ping_interval=None,
                ping_timeout=None,
                max_size=None
            )
            
            # Отправляем конфигурацию
            await self.ws.send(json.dumps({
                "type": "spy",
                "sample_rate": SAMPLE_RATE,
                "channels": 1,
                "chunk": CHUNK_SIZE
            }))
            
            print("✅ Подключено!")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    def setup_audio_device(self):
        """Настройка и выбор аудио устройства"""
        try:
            print("\n📊 Поиск аудио устройств...")
            devices = sd.query_devices()
            
            # Ищем устройства ввода
            input_devices = []
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    input_devices.append((i, dev['name']))
            
            if not input_devices:
                print("❌ Не найдены микрофоны!")
                return False
            
            print("Доступные микрофоны:")
            for idx, name in input_devices:
                print(f"  [{idx}] {name}")
            
            # Используем устройство по умолчанию
            default_idx = sd.default.device[0]
            print(f"\n🔄 Используется устройство по умолчанию: [{default_idx}]")
            
            return True
            
        except Exception as e:
            print(f"⚠️  Ошибка поиска устройств: {e}")
            return True  # Продолжаем с устройством по умолчанию
    
    def audio_callback(self, indata, frames, time_info, status):
        """
        Callback для захвата аудио
        ВАЖНО: Эта функция вызывается в отдельном потоке от аудио драйвера!
        """
        if status:
            print(f"Audio status: {status}")
        
        try:
            # Берем данные
            audio_float32 = indata.copy().flatten()
            
            # Фильтр для удаления шума (простой high-pass)
            # Убираем постоянную составляющую
            audio_float32 = audio_float32 - np.mean(audio_float32)
            
            # Нормализация (предотвращение клиппинга)
            max_val = np.max(np.abs(audio_float32))
            if max_val > 0.9:  # Если близко к клиппингу
                audio_float32 = audio_float32 * 0.9 / max_val
            
            # Конвертация float32 -> int16
            audio_int16 = np.clip(audio_float32 * 32767, -32768, 32767).astype(np.int16)
            
            # Статистика для отладки
            rms = np.sqrt(np.mean(audio_float32**2))
            if rms > 0.01:  # Есть звук
                level = int(rms * 50)
                level = min(30, level)
                bars = '█' * level
                print(f"\r🔊 Уровень: [{bars:30}] {rms:.4f}", end="")
            
            # Добавляем в очередь если есть место
            if not self.audio_queue.full():
                audio_bytes = audio_int16.tobytes()
                self.audio_queue.put(audio_bytes)
                
        except Exception as e:
            print(f"\nОшибка в audio_callback: {e}")
    
    def start_audio_stream(self):
        """Запуск потока захвата аудио"""
        print("\n🎤 Запуск захвата звука...")
        
        try:
            # Параметры потока
            stream_params = {
                'callback': self.audio_callback,
                'channels': 1,
                'samplerate': SAMPLE_RATE,
                'blocksize': CHUNK_SIZE,
                'dtype': 'float32',
                'latency': 'low'
            }
            
            # Если указано конкретное устройство
            if DEVICE_ID is not None:
                stream_params['device'] = DEVICE_ID
            
            # Создаем и запускаем поток
            self.stream = sd.InputStream(**stream_params)
            self.stream.start()
            
            print("✅ Микрофон активирован")
            print("💬 Говорите теперь...")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка запуска микрофона: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def send_audio_data(self):
        """Отправка аудио данных на сервер"""
        print("\n📤 Начало передачи...")
        
        send_interval = CHUNK_SIZE / SAMPLE_RATE  # Интервал между отправками
        last_send_time = time.time()
        
        while self.running:
            try:
                # Проверяем время для синхронизации
                current_time = time.time()
                elapsed = current_time - last_send_time
                
                if elapsed < send_interval * 0.8:  # Не отправляем слишком часто
                    await asyncio.sleep(0.001)
                    continue
                
                # Получаем данные из очереди
                try:
                    audio_bytes = self.audio_queue.get_nowait()
                except:
                    # Очередь пуста - отправляем тишину
                    audio_bytes = bytes(CHUNK_SIZE * 2)  # 2 байта на сэмпл (int16)
                
                # Создаем пакет
                encoded_audio = base64.b64encode(audio_bytes).decode('ascii')
                
                packet = {
                    "type": "audio",
                    "data": encoded_audio,
                    "timestamp": time.time(),
                    "packet_id": self.packet_count,
                    "sample_rate": SAMPLE_RATE
                }
                
                # Отправляем пакет
                await self.ws.send(json.dumps(packet))
                
                self.packet_count += 1
                last_send_time = current_time
                
                # Показываем прогресс
                if self.packet_count % 50 == 0:
                    qsize = self.audio_queue.qsize()
                    print(f"\n📦 Пакетов: {self.packet_count} | Очередь: {qsize}")
                
            except websockets.exceptions.ConnectionClosed:
                print("\n⚠️  Соединение разорвано")
                break
            except Exception as e:
                print(f"\n⚠️  Ошибка отправки: {e}")
                await asyncio.sleep(0.1)
    
    async def monitor_connection(self):
        """Мониторинг соединения"""
        while self.running:
            await asyncio.sleep(5)
            if self.ws:
                try:
                    # Просто проверяем что соединение живо
                    await self.ws.ping()
                except:
                    print("⚠️  Потеряно соединение с сервером")
                    self.running = False
    
    async def run(self):
        """Основной цикл"""
        self.print_info()
        
        # Настройка аудио
        if not self.setup_audio_device():
            return
        
        # Подключение к серверу
        if not await self.connect_to_server():
            return
        
        # Запуск захвата звука
        if not self.start_audio_stream():
            return
        
        print("\n" + "="*60)
        print("🚀 ТРАНСЛЯЦИЯ НАЧАТА")
        print("Нажмите Ctrl+C для остановки")
        print("="*60 + "\n")
        
        try:
            # Запускаем задачи
            send_task = asyncio.create_task(self.send_audio_data())
            monitor_task = asyncio.create_task(self.monitor_connection())
            
            # Ждем завершения
            await asyncio.gather(send_task, monitor_task)
            
        except KeyboardInterrupt:
            print("\n\n⏹️  Остановка...")
        except Exception as e:
            print(f"\n💥 Ошибка: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Очистка ресурсов"""
        print("\n🧹 Очистка ресурсов...")
        self.running = False
        
        # Останавливаем аудио поток
        if self.stream:
            self.stream.stop()
            self.stream.close()
            print("✅ Аудио поток остановлен")
        
        # Закрываем WebSocket
        if self.ws:
            asyncio.create_task(self.ws.close())
            print("✅ WebSocket закрыт")
        
        print(f"📊 Итог: отправлено {self.packet_count} пакетов")
        print("👋 Завершено\n")

def main():
    """Точка входа"""
    # Настройки для Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Запуск клиента
    client = CleanAudioClient()
    
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\n👋 Остановлено пользователем")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()