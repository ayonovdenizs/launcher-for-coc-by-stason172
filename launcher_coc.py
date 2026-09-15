"""Лаунчер сборки S.T.A.L.K.E.R. Call of Chernobyl от stason172.

Перенесите файл в корневую папку игры — рядом со ``Stalker-CoC.exe`` — и
запустите:

    python launcher_coc.py

Логика лаунчера живёт в пакете :mod:`launcher`, здесь только точка входа.
"""

from __future__ import annotations

import sys

from launcher import app

if __name__ == "__main__":
    sys.exit(app.main())
