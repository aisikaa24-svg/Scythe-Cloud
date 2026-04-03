# Project SCYTHE: Secret Injector
# This script reads secrets from 'local_secrets.env' and injects them into GitHub Actions.

Write-Host "--- [ Project SCYTHE: Secret Injector ] ---" -ForegroundColor Cyan

if (-not (Test-Path "local_secrets.env")) {
    Write-Host "[ERROR] 'local_secrets.env' not found! Please create it from local_secrets.env.template if it exists." -ForegroundColor Red
    exit 1
}

$secrets = @{}
Get-Content "local_secrets.env" | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $index = $line.IndexOf("=")
        $name = $line.Substring(0, $index).Trim()
        $value = $line.Substring($index + 1).Trim()
        $secrets[$name] = $value
    }
}

if ($secrets.Count -eq 0) {
    Write-Host "[WARNING] No secrets found in local_secrets.env" -ForegroundColor Yellow
    exit 0
}

foreach ($name in $secrets.Keys) {
    Write-Host "Setting secret: $name..." -NoNewline
    $value = $secrets[$name]
    # Use pipe to send value to gh CLI
    $value | gh secret set $name --repo aisikaa24-svg/Scythe-Cloud
    if ($LASTEXITCODE -eq 0) {
        Write-Host " [SUCCESS]" -ForegroundColor Green
    } else {
        Write-Host " [FAILED]" -ForegroundColor Red
    }
}

Write-Host "Mission Status: Secrets Shielded." -ForegroundColor Cyan
