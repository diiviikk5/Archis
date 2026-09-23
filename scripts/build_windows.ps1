$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
python -m pip install --upgrade pip
python -m pip install -r requirements-windows.lock
python -m pip install -e . --no-deps
python -m pytest
python -m PyInstaller ArchisOpticalTracker.spec --clean --noconfirm
$SmokeDir = Join-Path $env:TEMP "ArchisTracker-Smoke-$PID"
New-Item -ItemType Directory -Force $SmokeDir | Out-Null
$ExePath = (Resolve-Path "dist\ArchisTracker\ArchisTracker.exe").Path
try {
    Push-Location $SmokeDir
    try {
        & $ExePath validate "scenarios\schema_v2_example.json"
        if ($LASTEXITCODE -ne 0) { throw "Packaged scenario validation failed with exit code $LASTEXITCODE" }
        & $ExePath benchmark "archis_tracker\presets\nominal_leo.json" --frames 120 --output-dir "$SmokeDir\report"
        if ($LASTEXITCODE -ne 0) { throw "Packaged benchmark smoke test failed with exit code $LASTEXITCODE" }
    }
    finally {
        Pop-Location
    }
}
finally {
    Remove-Item -LiteralPath $SmokeDir -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force release | Out-Null
Compress-Archive -Path "dist\ArchisTracker\*" -DestinationPath "release\ArchisTracker-2.0.0-Portable.zip" -Force
if (Get-Command ISCC.exe -ErrorAction SilentlyContinue) {
    ISCC.exe "packaging\ArchisTracker.iss"
}
$Version = python -c "from archis_tracker import __version__; print(__version__)"
$Commit = git rev-parse HEAD
$Artifacts = Get-ChildItem release -File | ForEach-Object {
    [ordered]@{
        file = $_.Name
        bytes = $_.Length
        sha256 = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}
[ordered]@{
    application = "Archis Optical Tracker"
    version = $Version
    source_commit = $Commit
    python = (python --version)
    generated_utc = (Get-Date).ToUniversalTime().ToString("o")
    artifacts = $Artifacts
} | ConvertTo-Json -Depth 5 | Set-Content "release\release_manifest.json"
Get-ChildItem release -File | Where-Object Name -ne "SHA256SUMS.json" | Get-FileHash -Algorithm SHA256 |
    Select-Object Path, Hash | ConvertTo-Json | Set-Content "release\SHA256SUMS.json"
