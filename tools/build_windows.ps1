$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$buildPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
& $buildPython tools\prepare_assets.py
if ($LASTEXITCODE -ne 0) { throw 'Asset preparation failed.' }
& $buildPython -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
& $buildPython -m PyInstaller --noconfirm packaging\RollLiveCounter.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
$candidates = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe")
$compiler = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $compiler) { throw 'Inno Setup 6 required.' }
& $compiler packaging\RollLiveCounter.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer failed.' }
$versioned = Join-Path $projectRoot 'dist\installer\RollLiveCounter-Setup-0.1.0.exe'
$generic = Join-Path $projectRoot 'dist\installer\RollLiveCounter-Setup.exe'
Copy-Item -LiteralPath $versioned -Destination $generic -Force
$hash = (Get-FileHash -LiteralPath $versioned -Algorithm SHA256).Hash.ToLowerInvariant()
@("$hash  RollLiveCounter-Setup-0.1.0.exe", "$hash  RollLiveCounter-Setup.exe") | Set-Content -LiteralPath 'dist\installer\SHA256SUMS.txt' -Encoding ascii
