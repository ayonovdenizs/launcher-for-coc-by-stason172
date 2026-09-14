# Лаунчер для сборки S.T.A.L.K.E.R. Call Of Chernobyl от stason172

### проект заморожен

Современный лаунчер на **Python 3 + PySide6 (Qt 6)**: тёмная тема, аккуратный
интерфейс, проверка файлов перед запуском и логирование.

Скачать игру: [Официальная группа в ВК](https://vk.com/scoc174)

## Возможности

- Запуск игры в обычном режиме и в режиме отладки (`-dbg`)
- Фаст-запуск для слабых ПК (`2coreCPU`)
- Запуск менеджера модов от stason172 и настроек игры
- Проверка наличия файлов перед запуском и понятные сообщения об ошибках
- Лог работы в `launcher.log`

## Установка

1. Установите [Python 3.10+](https://www.python.org/downloads/)
   (при установке отметьте *Add Python to PATH*).
2. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

3. Перенесите `launcher_coc.py` в корневую папку игры.
4. Запустите:

   ```bash
   python launcher_coc.py
   ```

## Сборка в .exe (по желанию)

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name Launcher-CoC launcher_coc.py
```

Готовый файл появится в папке `dist/` — перенесите его в корень игры.
