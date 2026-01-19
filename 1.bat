@echo off
echo ========================================
echo Установка зависимостей Audio Streaming System
echo ========================================
echo.

echo Устанавливаем Python пакеты...
pip install aiohttp websockets sounddevice numpy

echo.
echo Проверяем установку...
python -c "import aiohttp; import websockets; import sounddevice; import numpy; print('✅ Все зависимости установлены!')"

echo.
echo ========================================
echo Установка завершена!
echo Запустите:
echo   1. server.py  - для запуска сервера
echo   2. client.py  - для запуска клиента
echo   3. test.py    - для тестирования
echo ========================================
pause