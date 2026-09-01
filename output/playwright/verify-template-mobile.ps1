$ErrorActionPreference = "Stop"
$auditRoot = Join-Path $PSScriptRoot "template-audit"
$env:LOCALAPPDATA = Join-Path $PSScriptRoot ".localappdata"
$pw = Join-Path $PSScriptRoot ".tooling\node_modules\.bin\playwright-cli.cmd"
Set-Location $auditRoot
& $pw kill-all | Out-Null
& $pw --session template-mobile open about:blank
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $pw --session template-mobile snapshot | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $pw --session template-mobile run-code --filename verify-mobile.js
$result = $LASTEXITCODE
& $pw --session template-mobile close | Out-Null
exit $result
