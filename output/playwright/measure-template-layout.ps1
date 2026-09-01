$ErrorActionPreference = "Stop"
$env:LOCALAPPDATA = Join-Path $PSScriptRoot ".localappdata"
$pw = Join-Path $PSScriptRoot ".tooling\node_modules\.bin\playwright-cli.cmd"
$auditRoot = Join-Path $PSScriptRoot "template-audit"
New-Item -ItemType Directory -Force (Join-Path $auditRoot "focused") | Out-Null
Set-Location $auditRoot
& $pw kill-all | Out-Null
& $pw --session template-layout open about:blank
if ($LASTEXITCODE -ne 0) { throw "Unable to open Playwright session" }
& $pw --session template-layout snapshot
if ($LASTEXITCODE -ne 0) { throw "Unable to snapshot Playwright session" }
& $pw --session template-layout run-code --filename measure-layout.js
if ($LASTEXITCODE -ne 0) { throw "Unable to measure template layouts" }
& $pw --session template-layout close
