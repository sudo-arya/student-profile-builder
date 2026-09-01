param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $CliArgs
)

$env:LOCALAPPDATA = Join-Path $PSScriptRoot ".localappdata"
$cli = Join-Path $PSScriptRoot ".tooling\node_modules\.bin\playwright-cli.cmd"
& $cli @CliArgs
exit $LASTEXITCODE
