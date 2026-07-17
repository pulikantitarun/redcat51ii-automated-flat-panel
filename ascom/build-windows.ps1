$ErrorActionPreference = 'Stop'
$venv = Join-Path $PSScriptRoot '.venv'
py -3 -m venv $venv
& "$venv\Scripts\python.exe" -m pip install --upgrade pip
& "$venv\Scripts\python.exe" -m pip install pyserial==3.5 pyinstaller==6.15.0
& "$venv\Scripts\pyinstaller.exe" --noconfirm --clean --onefile --name UniversalFlatPanelAlpaca `
  --collect-submodules serial "$PSScriptRoot\universal_flat_panel_alpaca.py"
Write-Host "Built: $PSScriptRoot\dist\UniversalFlatPanelAlpaca.exe"
