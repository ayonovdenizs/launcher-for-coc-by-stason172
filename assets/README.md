# Графика лаунчера

| Файл | Назначение | Размер |
| --- | --- | --- |
| `background.jpg` | фон окна лаунчера (затемняется градиентом поверх) | ~115 КБ |
| `icon.png` | иконка окна в обычном запуске | ~0.4 МБ |
| `icon.ico` | иконка для `.exe` и панели задач (16…256 px) | ~150 КБ |
| `background.png` | исходник фонового арта (в сборку не попадает) | 2 МБ |
| `icon_source.png` | исходник иконки (в сборку не попадает) | 1.9 МБ |

Рабочие файлы (`background.jpg`, `icon.png`, `icon.ico`) собираются из исходников:

```bash
pip install Pillow
python tools/make_assets.py
```

Лаунчер загружает `assets/background.jpg` через `launcher.paths.resource_path()`,
поэтому в onefile-сборке PyInstaller файлы попадают внутрь `.exe`
(см. блок `datas` в `launcher.spec`).

## Обновление арта

1. Положите новый исходник (`background.png` — вертикальный, `icon_source.png` — квадратный).
2. Запустите `python tools/make_assets.py`.
3. Проверьте, как выглядит окно: `python tools/preview_ui.py --out build/ui-preview.png --hover 2`.
