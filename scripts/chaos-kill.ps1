param(
    [ValidateSet("vedaops-app", "vedaops-staging-app")]
    [string]$Container = "vedaops-app",
    [string]$BaseUrl = ""
)

$ErrorActionPreference = "Stop"
if (-not $BaseUrl) {
    $BaseUrl = if ($Container -eq "vedaops-staging-app") {
        "http://127.0.0.1:8081"
    }
    else {
        "http://127.0.0.1:8080"
    }
}

Write-Host "Stopping allowlisted demo/staging container $Container. Watch Grafana and healer logs."
docker kill $Container
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& "$PSScriptRoot/smoke-test.ps1" -BaseUrl $BaseUrl -Attempts 30
exit $LASTEXITCODE
