$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepositoryRoot

function Assert-NativeCommandSuccess([string]$Description) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

py -3.12 -m venv .venv
Assert-NativeCommandSuccess "Creating the Python 3.12 virtual environment"
$Python = Join-Path $RepositoryRoot ".venv\Scripts\python.exe"
$Ruff = Join-Path $RepositoryRoot ".venv\Scripts\ruff.exe"
$Pytest = Join-Path $RepositoryRoot ".venv\Scripts\pytest.exe"
& $Python -m pip install --requirement app/requirements.txt --requirement healer/requirements.txt --requirement requirements-dev.txt
Assert-NativeCommandSuccess "Installing pinned Python dependencies"
& $Ruff check app healer
Assert-NativeCommandSuccess "Ruff lint"
& $Pytest
Assert-NativeCommandSuccess "Pytest"

$DockerRepositoryRoot = $RepositoryRoot -replace '\\', '/'
$MonitoringPath = "$DockerRepositoryRoot/monitoring"
$RuntimePath = "$DockerRepositoryRoot/.runtime"
docker compose config --quiet
Assert-NativeCommandSuccess "Docker Compose configuration"
docker run --rm --volume "${MonitoringPath}:/etc/prometheus:ro" --entrypoint=/bin/promtool prom/prometheus:v3.15.0 check config /etc/prometheus/prometheus.yml
Assert-NativeCommandSuccess "Prometheus configuration"
docker run --rm --volume "${MonitoringPath}:/etc/prometheus:ro" --entrypoint=/bin/promtool prom/prometheus:v3.15.0 check rules /etc/prometheus/alert.rules.yml
Assert-NativeCommandSuccess "Prometheus alert rules"
docker run --rm --volume "${MonitoringPath}:/etc/alertmanager:ro" --entrypoint=/bin/amtool prom/alertmanager:v0.34.1 check-config /etc/alertmanager/alertmanager.yml
Assert-NativeCommandSuccess "Alertmanager configuration"

foreach ($ProjectName in @("vedaops", "vedaops-staging", "vedaops-production")) {
    & (Join-Path $PSScriptRoot "render-runtime-monitoring.ps1") -ProjectName $ProjectName
    $RuntimeRules = "$RuntimePath/alert.rules.yml"
    docker run --rm --volume "${RuntimePath}:/etc/runtime:ro" --entrypoint=/bin/promtool prom/prometheus:v3.15.0 check rules /etc/runtime/alert.rules.yml
    Assert-NativeCommandSuccess "Rendered alert rules for $ProjectName"
}

docker compose build
Assert-NativeCommandSuccess "Docker image builds"
Write-Host "Python, shell, Compose, monitoring, and container build checks passed."
