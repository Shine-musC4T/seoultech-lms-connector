[CmdletBinding()]
param(
    [switch]$RemoveAuth
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$setupScript = Join-Path $projectRoot "scripts\setup_integrations.py"
$userProfilePath = [Environment]::GetFolderPath("UserProfile")

function Get-ClaudeDesktopConfigPath {
    $claudePackage = Get-AppxPackage -Name Claude -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($claudePackage -and $claudePackage.PackageFamilyName) {
        return Join-Path $env:LOCALAPPDATA (
            "Packages\{0}\LocalCache\Roaming\Claude\claude_desktop_config.json" -f
            $claudePackage.PackageFamilyName
        )
    }

    return Join-Path ([Environment]::GetFolderPath("ApplicationData")) "Claude\claude_desktop_config.json"
}

$claudeConfig = Get-ClaudeDesktopConfigPath

$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pythonLauncher) {
    $pythonExe = (& $pythonLauncher.Source -3.12 -c "import sys; print(sys.executable)")
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) { throw "Python was not found." }
    $pythonExe = $pythonCommand.Source
}

$removeJson = & $pythonExe $setupScript uninstall `
    --user-profile $userProfilePath `
    --claude-config $claudeConfig
if ($LASTEXITCODE -ne 0) { throw "Failed to remove integration settings." }
$removeResult = $removeJson | ConvertFrom-Json

$codexCommand = Get-Command codex -ErrorAction SilentlyContinue
if ($codexCommand) {
    & $codexCommand.Source plugin remove "seoultech-c4t@$($removeResult.marketplace_name)"
}

$claudeCommand = Get-Command claude -ErrorAction SilentlyContinue
if ($claudeCommand) {
    & $claudeCommand.Source mcp remove seoultech_c4t --scope user
}

& $pythonExe -m pip uninstall --yes seoultech-lms-connector

if ($RemoveAuth) {
    $authDirectory = Join-Path $env:LOCALAPPDATA "seoultech-lms-connector"
    $authPath = Join-Path $authDirectory "auth_state.json"
    if (Test-Path -LiteralPath $authPath) {
        Remove-Item -LiteralPath $authPath -Force
        Write-Host "Removed the saved LMS login session."
    }
}

Write-Host "Uninstall complete. The login state is removed only when -RemoveAuth is specified."
Write-Host "In Claude Desktop, remove seoultech_c4t from Settings > Extensions if it is installed."
