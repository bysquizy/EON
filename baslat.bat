@echo off
chcp 65001 >nul
cd /d "%~dp0"
if /I "%~1"=="--silent" goto silent
if /I "%~1"=="--tray" goto tray
where.exe py >nul 2>&1
if errorlevel 1 goto use_python
py -3 eon.py
goto finish
:use_python
where.exe python >nul 2>&1
if errorlevel 1 goto missing_python
python eon.py
goto finish
:silent
where.exe pyw >nul 2>&1
if not errorlevel 1 goto launch_silent
where.exe pythonw >nul 2>&1
if not errorlevel 1 goto launch_pythonw
echo Sessiz başlatma için pyw veya pythonw bulunamadı; normal modda açılıyor.
goto normal
:launch_silent
pyw -3 eon.py --silent
goto finish
:launch_pythonw
pythonw eon.py --silent
goto finish
:tray
where.exe pyw >nul 2>&1
if not errorlevel 1 (
  pyw -3 eon.py --tray
  goto finish
)
where.exe pythonw >nul 2>&1
if not errorlevel 1 (
  pythonw eon.py --tray
  goto finish
)
py -3 eon.py --tray
goto finish
:normal
where.exe py >nul 2>&1
if errorlevel 1 goto use_python
py -3 eon.py
goto finish
:missing_python
echo Python bulunamadı. EON için Python 3.10 veya üzeri gereklidir.
echo Python'ı kurup bu pencereyi yeniden açın.
pause
exit /b 1
:finish
if errorlevel 1 pause
