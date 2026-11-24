@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "EON_MODE=%~1"

:: 1. Yerel taşınabilir Python (.python\python.exe) varsa doğrudan onu kullan
if exist "%~dp0.python\python.exe" (
  set "PY_CMD=%~dp0.python\python.exe"
  set "PYW_CMD=%~dp0.python\pythonw.exe"
  goto dispatch
)

:: 2. Sistemde kurulu Python Başlatıcısı (py.exe) var mı?
where.exe py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys;raise SystemExit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
  if not errorlevel 1 (
    set "PY_CMD=py -3"
    set "PYW_CMD=pyw -3"
    goto dispatch
  )
)

:: 3. Sistemde gerçek python.exe (Windows Store sahte kısayolu olmayan) var mı?
where.exe python >nul 2>&1
if not errorlevel 1 (
  python -c "import sys;raise SystemExit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
  if not errorlevel 1 (
    set "PY_CMD=python"
    set "PYW_CMD=pythonw"
    goto dispatch
  )
)

:: 4. Bilgisayarda Python kurulu değil: Resmi python.org Taşınabilir (Embeddable) Python'ı otomatik indir ve hazırla
echo Bilgisayarda Python bulunamadi.
echo EON, resmi python.org tasinabilir (portable) calisma ortamini (.python klasorune) indirip hazirliyor...
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$ProgressPreference='SilentlyContinue';" ^
  "$arch=if($env:PROCESSOR_ARCHITECTURE -eq 'ARM64'){'arm64'}else{'amd64'};" ^
  "$ver='3.13.2';" ^
  "$url=\"https://www.python.org/ftp/python/$ver/python-$ver-embed-$arch.zip\";" ^
  "$dest=Join-Path '%~dp0' '.python';" ^
  "$zip=Join-Path '%~dp0' '.python-embed.zip';" ^
  "New-Item -ItemType Directory -Force $dest|Out-Null;" ^
  "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13;" ^
  "Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $zip;" ^
  "Expand-Archive -Force -Path $zip -DestinationPath $dest;" ^
  "Remove-Item -Force $zip;" ^
  "$sig=Get-AuthenticodeSignature (Join-Path $dest 'python.exe');" ^
  "if($sig.Status -ne 'Valid'){Remove-Item -Recurse -Force $dest; throw 'Python dijital imzasi dogrulanamadi!'};" ^
  "Get-ChildItem -Path '%~dp0' -Recurse -File | ForEach-Object { try { Unblock-File -Path $_.FullName -ErrorAction SilentlyContinue } catch {} };" ^
  "Get-ChildItem -Path $dest -Filter 'python*._pth'|ForEach-Object{" ^
  "  $c=(Get-Content $_.FullName) -replace '#import site','import site';" ^
  "  if($c -notcontains '..'){$c+=@('..')};" ^
  "  Set-Content -Encoding ASCII $_.FullName $c" ^
  "}"
if exist "%~dp0.python\python.exe" (
  set "PY_CMD=%~dp0.python\python.exe"
  set "PYW_CMD=%~dp0.python\pythonw.exe"
  goto dispatch
)

echo Tasinabilir Python indirilemedi. Internet baglantinizi kontrol edin veya https://www.python.org adresinden Python 3.10+ kurun.
pause
exit /b 1

:dispatch
if /I "%EON_MODE%"=="--cli" goto launch_cli
if /I "%EON_MODE%"=="--console" goto launch_cli
if /I "%EON_MODE%"=="--silent" goto launch_silent
if /I "%EON_MODE%"=="--tray" goto launch_tray
goto launch_tray

:launch_cli
%PY_CMD% eon.py %EON_MODE%
goto finish

:launch_silent
if exist "%~dp0.python\pythonw.exe" (
  "%~dp0.python\pythonw.exe" eon.py --silent
  goto finish
)
where.exe pyw >nul 2>&1
if not errorlevel 1 (
  pyw -3 eon.py --silent
  goto finish
)
where.exe pythonw >nul 2>&1
if not errorlevel 1 (
  pythonw eon.py --silent
  goto finish
)
%PY_CMD% eon.py
goto finish

:launch_tray
if exist "%~dp0.python\pythonw.exe" (
  "%~dp0.python\pythonw.exe" eon.py --tray
  goto finish
)
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
%PY_CMD% eon.py --tray
goto finish

:finish
if errorlevel 1 pause
