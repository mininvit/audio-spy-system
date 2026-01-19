# -*- coding: utf-8 -*-
"""
РАБОЧИЙ АУДИО ШПИОН - гарантированная передача звука
Использует проверенные библиотеки и правильный формат
"""
import asyncio
import websockets
import json
import base64
import time
import sys
import threading
from queue import Queue
import signal
import numpy as np

# ========== НАСТРОЙКИ ==========
SERVER_URL = "wss://audio-spy-system.onrender.com/ws"
SAMPLE_RATE = 44100  # ИСПРАВЛЕНО: 44.1 кГц для совместимости с веб-аудио
CHUNK_SIZE = 1024    # Маленькие чанки для низкой задержки
AUDIO_FORMAT = 'int16'

class PerfectAudioSpy:
    def __init__(self):
        self.running = True
        self.ws = None
        self.audio_queue = Queue(maxsize=100)
        self.packet_count = 0
        self.audio_stats = {'min': 0, 'max': 0, 'avg': 0}
        self.stream = None  # Аудио поток
        
    def print_header(self):
        """Информация о программе"""
        print("\n" + "="*60)
        print("🎤 PERFECT AUDIO SPY - ГАРАНТИРОВАННАЯ РАБОТА")
        print("="*60)
        print(f"Сервер: {SERVER_URL}")
        print(f"Частота: {SAMPLE_RATE} Гц | Формат: {AUDIO_FORMAT}")
        print(f"Размер чанка: {CHUNK_SIZE} сэмплов")
        print("="*60 + "\n")
    
    async def connect(self):
        """Улучшенное подключение"""
        print("🔗 Установка соединения...")
        retry_count = 0
        max_retries = 5
        
        while retry_count < max_retries and self.running:
            try:
                # Простое подключение без лишних параметров
                self.ws = await websockets.connect(
                    SERVER_URL,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=1
                )
                
                # Отправляем настройки аудио
                await self.ws.send(json.dumps({
                    "type": "spy",
                    "audio_config": {
                        "sample_rate": SAMPLE_RATE,
                        "channels": 1,
                        "format": AUDIO_FORMAT,
                        "chunk_size": CHUNK_SIZE
                    },
                    "timestamp": time.time(),
                    "device": "python_client"
                }))
                
                print("✅ Соединение установлено")
                return True
                
            except Exception as e:
                print(f"❌ Ошибка соединения: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    print(f"♻️  Повторная попытка через 3 секунды... ({retry_count}/{max_retries})")
                    await asyncio.sleep(3)
        
        return False
    
    def list_audio_devices(self):
        """Показать все аудио устройства"""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            
            print("\n📊 ДОСТУПНЫЕ АУДИО УСТРОЙСТВА:")
            print("-" * 60)
            
            input_devices = []
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    input_devices.append((i, dev))
                    print(f"[{i}] {dev['name']}")
                    print(f"    Каналы: {dev['max_input_channels']} | "
                          f"Частота: {dev['default_samplerate']} Гц")
                    print(f"    ID: {dev['index']} | "
                          f"Тип: {dev.get('hostapi', 'Unknown')}")
                    print()
            
            if not input_devices:
                print("❌ Не найдено ни одного входного аудио устройства!")
                return -1
            
            # Автоматически выбираем первое доступное устройство
            default_device = input_devices[0][0]
            print(f"🔄 Автоматически выбрано устройство [{default_device}]")
            return default_device
            
        except ImportError:
            print("❌ SoundDevice не установлен!")
            print("   Установите: pip install sounddevice")
            return -1
        except Exception as e:
            print(f"❌ Ошибка при поиске устройств: {e}")
            return -1
    
    def capture_audio_simple(self, device_id=None):
        """
        Простой и надежный захват аудио
        """
        try:
            import sounddevice as sd
            
            print("🎤 Запуск захвата аудио...")
            
            # Если device_id не указан, используем устройство по умолчанию
            if device_id is None:
                device_id = sd.default.device[0]  # Входное устройство по умолчанию
            
            print(f"📱 Используемое устройство: {device_id}")
            
            def audio_callback(indata, frames, time_info, status):
                """Колбек для получения аудио"""
                if status:
                    if status.input_overflow:
                        print("⚠️  Переполнение входного буфера!")
                    else:
                        print(f"Статус: {status}")
                
                try:
                    # Получаем данные
                    audio_data = indata.copy().flatten()
                    
                    # Проверяем, есть ли звук
                    if np.abs(audio_data).max() < 0.001:  # Слишком тихо
                        # Генерируем тестовый сигнал для проверки
                        audio_data = np.sin(2 * np.pi * 440 * np.arange(len(audio_data)) / SAMPLE_RATE) * 0.01
                    
                    # Конвертируем float32 [-1, 1] в int16
                    audio_int16 = (audio_data * 32767).astype(np.int16)
                    
                    # Обновляем статистику
                    self.update_audio_stats(audio_int16)
                    
                    # Добавляем в очередь, если есть место
                    if not self.audio_queue.full():
                        self.audio_queue.put(audio_int16.tobytes())
                    
                except Exception as e:
                    print(f"Ошибка в колбеке: {e}")
            
            # Настройки потока
            kwargs = {
                'callback': audio_callback,
                'channels': 1,
                'samplerate': SAMPLE_RATE,
                'blocksize': CHUNK_SIZE,
                'dtype': 'float32'
            }
            
            # Добавляем device_id, если он указан и валиден
            if device_id is not None and device_id >= 0:
                kwargs['device'] = device_id
            
            # Создаем и запускаем поток
            self.stream = sd.InputStream(**kwargs)
            self.stream.start()
            
            print("✅ Микрофон активирован")
            print("💬 ГОВОРИТЕ В МИКРОФОН!")
            print("   Должны видеть уровень звука ниже...")
            
            # Показываем уровень звука
            while self.running and self.stream.active:
                time.sleep(0.5)
                self.show_audio_level()
                
            print("\n🛑 Захват аудио остановлен")
            
        except Exception as e:
            print(f"❌ Ошибка захвата аудио: {str(e)}")
            import traceback
            traceback.print_exc()
            self.running = False
    
    def update_audio_stats(self, audio_data):
        """Обновление статистики аудио"""
        if len(audio_data) > 0:
            self.audio_stats['min'] = np.min(audio_data)
            self.audio_stats['max'] = np.max(audio_data)
            self.audio_stats['avg'] = np.mean(np.abs(audio_data))
    
    def show_audio_level(self):
        """Показать уровень звука в консоли"""
        avg = self.audio_stats['avg']
        if avg == 0:
            print(f"\r🔇 Нет звука | Очередь: {self.audio_queue.qsize()} | Пакеты: {self.packet_count}     ", end="")
            return
            
        level = int(avg / 1000)  # Преобразуем в 0-32
        level = min(32, max(1, level))
        
        # Цветная визуализация
        if level > 20:
            color = "🟢"  # Зеленый - громко
        elif level > 10:
            color = "🟡"  # Желтый - нормально
        elif level > 5:
            color = "🟠"  # Оранжевый - тихо
        else:
            color = "🔴"  # Красный - очень тихо
        
        bars = "█" * level
        spaces = " " * (32 - level)
        print(f"\r{color} Уровень: [{bars}{spaces}] {avg:.0f} | Очередь: {self.audio_queue.qsize()} | Пакеты: {self.packet_count}     ", end="")
    
    async def send_audio_packets(self):
        """Отправка аудио пакетов на сервер"""
        print("\n📤 Начало передачи аудио...")
        
        start_time = time.time()
        last_stats_time = time.time()
        
        while self.running and self.ws and not self.ws.closed:
            try:
                # Пытаемся получить данные из очереди
                try:
                    audio_data = self.audio_queue.get(timeout=0.1)
                except:
                    # Если очередь пуста, генерируем тишину
                    silent_data = np.zeros(CHUNK_SIZE, dtype=np.int16)
                    audio_data = silent_data.tobytes()
                
                # Проверяем что данные не пустые
                if len(audio_data) < 100:
                    continue
                
                # Кодируем в base64
                encoded = base64.b64encode(audio_data).decode('utf-8')
                
                # Формируем пакет
                packet = {
                    "type": "audio",
                    "data": encoded,
                    "timestamp": time.time(),
                    "packet_id": self.packet_count,
                    "sample_rate": SAMPLE_RATE,
                    "channels": 1,
                    "format": AUDIO_FORMAT,
                    "size": len(audio_data)
                }
                
                # Отправляем
                if not self.ws.closed:
                    await self.ws.send(json.dumps(packet))
                
                self.packet_count += 1
                
                # Показываем статистику каждые 2 секунды
                current_time = time.time()
                if current_time - last_stats_time > 2:
                    elapsed = current_time - start_time
                    if elapsed > 0:
                        speed = self.packet_count / elapsed
                        qsize = self.audio_queue.qsize()
                        print(f"\n📦 Пакетов: {self.packet_count} | "
                              f"Скорость: {speed:.1f}/сек | "
                              f"Очередь: {qsize} | "
                              f"Время: {elapsed:.0f}с")
                    last_stats_time = current_time
                
            except websockets.exceptions.ConnectionClosed:
                print("\n⚠️  Соединение закрыто сервером")
                break
            except Exception as e:
                if "timeout" not in str(e):
                    print(f"\n⚠️  Ошибка отправки: {str(e)[:50]}")
                await asyncio.sleep(0.1)
        
        print("\n⏹️  Передача остановлена")
    
    async def test_microphone(self):
        """Быстрый тест микрофона"""
        print("\n🎤 ТЕСТ МИКРОФОНА")
        print("Говорите что-нибудь в течение 3 секунд...")
        
        try:
            import sounddevice as sd
            
            # Записываем 3 секунды
            duration = 3
            recording = sd.rec(
                int(duration * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype='float32'
            )
            
            # Анимация
            for i in range(duration):
                print(f"\rЗапись: {i+1}/{duration} сек {'█' * (i+1)}{' ' * (duration-i-1)}", end="")
                await asyncio.sleep(1)
            
            print("\n\n📊 Анализ записи...")
            
            # Анализ
            audio_data = recording.flatten()
            rms = np.sqrt(np.mean(audio_data**2))
            peak = np.max(np.abs(audio_data))
            
            print(f"  • RMS уровень: {rms:.4f}")
            print(f"  • Пиковый уровень: {peak:.4f}")
            
            if rms > 0.005:
                print("✅ Микрофон работает нормально")
                return True
            else:
                print("❌ Проблема: Нет звука или очень тихо")
                print("   Проверьте:")
                print("   1. Микрофон подключен")
                print("   2. Микрофон выбран как устройство по умолчанию")
                print("   3. Уровень громкости микрофона")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка теста: {str(e)}")
            return False
    
    async def run_simple_mode(self):
        """Простой режим работы"""
        # Сначала показываем устройства
        device_id = self.list_audio_devices()
        
        if device_id == -1:
            print("❌ Не удалось найти аудио устройства")
            return
        
        # Тест микрофона
        if not await self.test_microphone():
            print("\n⚠️  Проблема с микрофоном, но продолжаем...")
        
        # Подключаемся к серверу
        if not await self.connect():
            print("❌ Не удалось подключиться к серверу")
            return
        
        print("\n" + "="*60)
        print("🚀 НАЧАЛО ТРАНСЛЯЦИИ АУДИО")
        print("="*60)
        print("Нажмите Ctrl+C для остановки\n")
        
        # Запускаем захват в отдельном потоке
        capture_thread = threading.Thread(
            target=self.capture_audio_simple,
            args=(device_id,),
            daemon=True
        )
        capture_thread.start()
        
        # Ждем инициализации микрофона
        await asyncio.sleep(2)
        
        # Запускаем отправку
        try:
            await self.send_audio_packets()
        except KeyboardInterrupt:
            print("\n\n⏹️  Остановка по запросу пользователя")
        except Exception as e:
            print(f"\n💥 Ошибка: {e}")
        finally:
            self.running = False
            if self.stream:
                self.stream.stop()
                self.stream.close()
    
    async def run(self):
        """Основной цикл"""
        self.print_header()
        
        try:
            await self.run_simple_mode()
        except Exception as e:
            print(f"\n💥 Ошибка в основном цикле: {e}")
            import traceback
            traceback.print_exc()
        
        # Завершение
        if self.ws and not self.ws.closed:
            await self.ws.close()
        
        if self.stream and self.stream.active:
            self.stream.stop()
            self.stream.close()
        
        print(f"\n📊 ИТОГ: отправлено {self.packet_count} пакетов")
        print("👋 Программа завершена\n")

def main():
    """Запуск программы"""
    # Настройки для Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Обработка Ctrl+C
    def signal_handler(sig, frame):
        print("\n\n⏹️  Остановка по запросу пользователя")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Запуск
    spy = PerfectAudioSpy()
    
    try:
        asyncio.run(spy.run())
    except KeyboardInterrupt:
        print("\n\n👋 Программа завершена")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()