$ErrorActionPreference = "Stop"
$env:LOCALAPPDATA = Join-Path $PSScriptRoot ".localappdata"
$pw = Join-Path $PSScriptRoot ".tooling\node_modules\.bin\playwright-cli.cmd"
$auditRoot = Join-Path $PSScriptRoot "template-audit"
New-Item -ItemType Directory -Force (Join-Path $auditRoot "arya") | Out-Null
Set-Location $auditRoot
& $pw kill-all | Out-Null
& $pw --session arya-audit open about:blank
if ($LASTEXITCODE -ne 0) { throw "Unable to open Playwright session" }
& $pw --session arya-audit snapshot | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Unable to snapshot Playwright session" }
& $pw --session arya-audit run-code --filename audit-arya.js
if ($LASTEXITCODE -ne 0) { throw "Unable to audit Arya template" }
& $pw --session arya-audit close | Out-Null
