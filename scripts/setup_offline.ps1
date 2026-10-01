param([Parameter(Mandatory=$true)][string]$Wheelhouse)
$ErrorActionPreference = 'Stop'
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --no-index --find-links $Wheelhouse -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Offline installation failed; check wheel versions and platform compatibility.' }
Write-Output 'Core installed. Install requirements-models.txt from the same wheelhouse for the model demo.'
