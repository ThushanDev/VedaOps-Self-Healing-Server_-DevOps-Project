param(
    [string]$BaseUrl = "http://127.0.0.1:8080",
    [int]$Attempts = 10
)

$ErrorActionPreference = "Stop"
$HealthUrl = "$($BaseUrl.TrimEnd('/'))/health"

for ($Attempt = 1; $Attempt -le $Attempts; $Attempt++) {
    try {
        $Response = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 3
        if ($Response.status -eq "ok") {
            Write-Host "Smoke test passed: $HealthUrl"
            exit 0
        }
    }
    catch {
        Start-Sleep -Seconds 3
    }
}

Write-Error "Smoke test failed after $Attempts attempts: $HealthUrl"
exit 1
