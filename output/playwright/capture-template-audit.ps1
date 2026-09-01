$ErrorActionPreference = "Stop"
$auditRoot = Join-Path $PSScriptRoot "template-audit"
$env:LOCALAPPDATA = Join-Path $PSScriptRoot ".localappdata"
$pw = Join-Path $PSScriptRoot ".tooling\node_modules\.bin\playwright-cli.cmd"
$screenshots = Join-Path $auditRoot "screenshots"
New-Item -ItemType Directory -Force $screenshots | Out-Null
Set-Location $auditRoot

function Invoke-Pw {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]] $Arguments)
    & $pw --session template-audit @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Playwright command failed: $($Arguments -join ' ')" }
}

$pairs = @(
    @{ Name = "arya"; Source = "http://127.0.0.1:8899/TA%20designs/Arya%20Singh/index.html"; Generated = "http://127.0.0.1:8899/output/playwright/template-audit/ta-arya-editorial/index.html" },
    @{ Name = "balaji"; Source = "http://127.0.0.1:8899/TA%20designs/Athinagaram%20Shree%20Balaji/Student%20website%20static%20sample.html"; Generated = "http://127.0.0.1:8899/output/playwright/template-audit/ta-balaji-tailwind/index.html" },
    @{ Name = "krishna"; Source = "http://127.0.0.1:8899/TA%20designs/Krishna%20Bisht/student.html"; Generated = "http://127.0.0.1:8899/output/playwright/template-audit/ta-krishna-sidebar/index.html" },
    @{ Name = "yamini"; Source = "http://127.0.0.1:8899/TA%20designs/Yamini%20Chandana/dist/index.html"; Generated = "http://127.0.0.1:8899/output/playwright/template-audit/ta-yamini-research/index.html" }
)

& $pw kill-all | Out-Null
Invoke-Pw open about:blank

Invoke-Pw run-code --filename capture.js
Invoke-Pw close
