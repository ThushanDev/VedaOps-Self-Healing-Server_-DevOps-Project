param(
    [string]$ProjectName = "vedaops",
    [string]$RuntimeDirectory = ".runtime"
)

$ErrorActionPreference = "Stop"
if ($ProjectName -notmatch '^vedaops(-[a-z0-9]+)?$') {
    throw "Unsupported VedaOps Compose project name: $ProjectName"
}
if ([IO.Path]::IsPathRooted($RuntimeDirectory)) {
    throw "RuntimeDirectory must be relative to the repository root."
}

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$RuntimeRoot = Join-Path $RepositoryRoot $RuntimeDirectory
$DashboardOutputDirectory = Join-Path $RuntimeRoot "dashboards"
New-Item -ItemType Directory -Path $DashboardOutputDirectory -Force | Out-Null

$AlertRulesPath = Join-Path $RepositoryRoot "monitoring/alert.rules.yml"
$DashboardPath = Join-Path $RepositoryRoot "monitoring/grafana/dashboards/vedaops-overview.json"
$AlertRules = [IO.File]::ReadAllText($AlertRulesPath, [Text.Encoding]::UTF8)
$Dashboard = [IO.File]::ReadAllText($DashboardPath, [Text.Encoding]::UTF8)
$AlertProjectLabel = 'container_label_com_docker_compose_project="vedaops"'
$DashboardProjectLabel = 'container_label_com_docker_compose_project=\"vedaops\"'

if (-not $AlertRules.Contains($AlertProjectLabel) -or -not $Dashboard.Contains($DashboardProjectLabel)) {
    throw "The monitoring files do not contain the expected default Compose project filter."
}

$AlertRules = $AlertRules.Replace(
    $AlertProjectLabel,
    ('container_label_com_docker_compose_project="' + $ProjectName + '"')
)
$Dashboard = $Dashboard.Replace(
    $DashboardProjectLabel,
    ('container_label_com_docker_compose_project=\"' + $ProjectName + '\"')
)
$DashboardObject = $Dashboard | ConvertFrom-Json
$ExpectedDashboardFilter = 'container_label_com_docker_compose_project="' + $ProjectName + '"'
if (-not $DashboardObject.panels[1].targets[0].expr.Contains($ExpectedDashboardFilter)) {
    throw "The rendered Grafana dashboard does not filter for Compose project $ProjectName."
}

$Utf8WithoutBom = [Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllText((Join-Path $RuntimeRoot "alert.rules.yml"), $AlertRules, $Utf8WithoutBom)
[IO.File]::WriteAllText(
    (Join-Path $DashboardOutputDirectory "vedaops-overview.json"),
    $Dashboard,
    $Utf8WithoutBom
)
Write-Host "Rendered alert and dashboard filters for Compose project $ProjectName in $RuntimeRoot"
