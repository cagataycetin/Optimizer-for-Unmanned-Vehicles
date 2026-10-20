@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
    goto finished
)
py -3 -c "import sys; raise SystemExit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 (
    py -3 main.py
    goto finished
)
python -c "import sys; raise SystemExit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 (
    python main.py
    goto finished
)
echo Python 3.10 veya uzeri bulunamadi.
echo Python kurulumu: https://www.python.org/downloads/
echo Kurulumdan sonra bu dosyayi tekrar acin.
pause
exit /b 1
:finished
if errorlevel 1 (
    echo Uygulama baslatilamadi. Yukaridaki hata mesajini paylasabilirsiniz.
    pause
    exit /b 1
)
endlocal
