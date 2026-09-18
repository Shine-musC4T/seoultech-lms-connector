[CmdletBinding()]
param(
    [switch]$SkipCodex,
    [switch]$SkipClaude,
    [switch]$SkipLogin
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$desktopIni = Join-Path $projectRoot "desktop.ini"
$pluginSource = Join-Path $projectRoot "plugin\seoultech-c4t"
$setupScript = Join-Path $projectRoot "scripts\setup_integrations.py"
$buildMcpbScript = Join-Path $projectRoot "scripts\build_mcpb.py"
$userProfilePath = [Environment]::GetFolderPath("UserProfile")

function Get-ClaudeDesktopConfigPath {
    # Microsoft Store/MSIX apps see a virtualized roaming directory. Writing to
    # the normal %APPDATA% path leaves the MCP server invisible to that build.
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

# Apply the bundled icon to this distribution folder in Windows Explorer.
if (Test-Path -LiteralPath $desktopIni) {
    & attrib.exe +h +s $desktopIni
    $folderItem = Get-Item -LiteralPath $projectRoot -Force
    $folderItem.Attributes = $folderItem.Attributes -bor [System.IO.FileAttributes]::ReadOnly
}

$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pythonLauncher) {
    $pythonExe = (& $pythonLauncher.Source -3.12 -c "import sys; print(sys.executable)")
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python 3.12 is required. Install it and run this script again."
    }
    $pythonExe = (& $pythonCommand.Source -c "import sys; print(sys.executable)")
}
if (-not $pythonExe) {
    throw "Could not locate a Python 3.12 executable."
}

$pythonVersion = (& $pythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if ($pythonVersion -ne "3.12") {
    throw "Python 3.12 is required. Detected version: $pythonVersion"
}

Write-Host "[1/6] Installing the Python package."
& $pythonExe -m pip install --upgrade $projectRoot
if ($LASTEXITCODE -ne 0) { throw "Python package installation failed." }

$setupArguments = @(
    $setupScript,
    "install",
    "--plugin-source", $pluginSource,
    "--user-profile", $userProfilePath,
    "--python-executable", $pythonExe,
    "--claude-config", $claudeConfig
)
if ($SkipCodex) { $setupArguments += "--skip-codex" }
if ($SkipClaude) { $setupArguments += "--skip-claude-desktop" }
$integrationJson = & $pythonExe @setupArguments
if ($LASTEXITCODE -ne 0) { throw "Failed to create AI integration settings." }
$integrationResult = $integrationJson | ConvertFrom-Json

if (-not $SkipCodex) {
    Write-Host "[2/6] Registering the Codex plugin."
    $codexCommand = Get-Command codex -ErrorAction SilentlyContinue
    if ($codexCommand) {
        & $codexCommand.Source plugin add "seoultech-c4t@$($integrationResult.marketplace_name)"
        if ($LASTEXITCODE -ne 0) { throw "Codex plugin registration failed." }
    } else {
        Write-Warning "Codex was not found. Install Codex and run this script again to register the plugin."
    }
} else {
    Write-Host "[2/6] Skipping Codex registration."
}

if (-not $SkipClaude) {
    Write-Host "[3/6] Building the branded Claude Desktop extension."
    $manifest = Get-Content -LiteralPath (Join-Path $pluginSource ".codex-plugin\plugin.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $claudeBundleDirectory = Join-Path $env:LOCALAPPDATA "seoultech-lms-connector"
    $claudeBundle = Join-Path $claudeBundleDirectory "seoultech-c4t.mcpb"
    & $pythonExe $buildMcpbScript `
        --project-root $projectRoot `
        --output $claudeBundle `
        --python-executable $pythonExe `
        --version $manifest.version
    if ($LASTEXITCODE -ne 0) { throw "Claude Desktop extension build failed." }

    # Windows does not register .mcpb as an openable file type. Opening it with
    # Start-Process therefore shows an irrelevant "Choose an app" dialog rather
    # than Claude's extension installer. Claude intentionally requires the user
    # to select and approve the bundle from its own settings screen.
    Write-Host "[4/6] Claude Desktop extension bundle is ready."
    Write-Host "In Claude Desktop: Settings > Extensions > Advanced settings > Install Extension"
    Write-Host "Select this file, then approve the installation: $claudeBundle"

    $claudeCommand = Get-Command claude -ErrorAction SilentlyContinue
    if ($claudeCommand) {
        & $claudeCommand.Source mcp remove seoultech_c4t --scope user *> $null
        $claudeServer = @{
            type = "stdio"
            command = $pythonExe
            args = @("-m", "seoultech_lms.mcp_server")
            env = @{}
        } | ConvertTo-Json -Compress
        & $claudeCommand.Source mcp add-json seoultech_c4t $claudeServer --scope user
        if ($LASTEXITCODE -ne 0) { throw "Claude Code MCP registration failed." }
        Write-Host "[5/6] Registered the Claude Code MCP server."
    } else {
        Write-Host "[5/6] Claude Code was not found. Claude Desktop extension is ready to install."
    }
} else {
    Write-Host "[3/6] Skipping Claude Desktop extension."
    Write-Host "[4/6] Skipping Claude Desktop installation."
    Write-Host "[5/6] Skipping Claude Code registration."
}

$authPath = Join-Path $env:LOCALAPPDATA "seoultech-lms-connector\auth_state.json"
if (-not $SkipLogin -and -not (Test-Path -LiteralPath $authPath)) {
    Write-Host "[6/6] Starting the first LMS login. Sign in directly in the browser window."
    & $pythonExe -m seoultech_lms.cli login
    if ($LASTEXITCODE -ne 0) { throw "Failed to save the LMS login state." }
} elseif ($SkipLogin) {
    Write-Host "[6/6] Skipping LMS login. Run 'seoultech-lms login' later."
} else {
    Write-Host "[6/6] Keeping the existing LMS login state."
}

Write-Host "Setup complete. Fully restart Codex and Claude before use."
Write-Host "If the folder icon does not refresh immediately, press F5 in File Explorer."
