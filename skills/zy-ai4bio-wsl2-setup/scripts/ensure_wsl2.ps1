param(
    [switch]$Apply,
    [string]$Distribution = "Ubuntu"
)

function Write-Result {
    param(
        [string]$Status,
        [string]$Distro,
        [string]$Message
    )
    [pscustomobject]@{
        status = $Status
        distro = $Distro
        message = $Message
    } | ConvertTo-Json -Compress
}

if ($env:OS -ne "Windows_NT") {
    Write-Result "unsupported_host" "" "Run this script in native Windows PowerShell, not inside Linux or WSL."
    exit 2
}

if ([Environment]::OSVersion.Version.Build -lt 19041) {
    Write-Result "unsupported_windows" "" "This Windows build is too old for the standard wsl --install workflow."
    exit 2
}

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    Write-Result "wsl_command_missing" "" "wsl.exe is unavailable; update Windows before continuing."
    exit 2
}

function Get-WslDistributions {
    $lines = & wsl.exe --list --verbose 2>$null
    $script:WslProbeFailed = $LASTEXITCODE -ne 0
    if ($script:WslProbeFailed) {
        $lines = @()
    }

    $found = @()
    foreach ($raw in $lines) {
        $line = (([string]$raw) -replace '\x00', '').Trim()
        if ($line -match '^\*?\s*(\S+)\s+.+\s+([12])\s*$') {
            $found += [pscustomobject]@{
                Name = $Matches[1]
                Version = [int]$Matches[2]
            }
        }
    }
    if ($found.Count -eq 0) {
        # A registry fallback prevents a localized or malformed CLI listing from creating a duplicate distro.
        $registryPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss'
        if (Test-Path $registryPath) {
            foreach ($key in Get-ChildItem $registryPath) {
                $entry = Get-ItemProperty $key.PSPath
                if ($entry.DistributionName) {
                    if ($entry.Version -in @(1, 2)) {
                        $found += [pscustomobject]@{
                            Name = [string]$entry.DistributionName
                            Version = [int]$entry.Version
                        }
                    } else {
                        $script:UnparsedRegistration = $true
                    }
                }
            }
        }
    }
    return $found
}

$distros = @(Get-WslDistributions)
if ($script:UnparsedRegistration -and $distros.Count -eq 0) {
    Write-Result "inspection_required" "" "A WSL distribution is registered but its version could not be read. No new distribution will be installed."
    exit 2
}
if ($script:WslProbeFailed -and $distros.Count -gt 0) {
    Write-Result "wsl_unavailable" "" "A distribution is registered but wsl.exe cannot list it. Repair WSL before attempting another installation."
    exit 2
}
$ready = @($distros | Where-Object { $_.Version -eq 2 -and $_.Name -eq $Distribution })
if ($ready.Count -eq 0) {
    $ready = @($distros | Where-Object { $_.Version -eq 2 })
}
if ($ready.Count -gt 0) {
    Write-Result "ready" $ready[0].Name "Existing WSL2 distribution will be reused; no new distribution was created."
    exit 0
}

$legacy = @($distros | Where-Object { $_.Version -eq 1 -and $_.Name -eq $Distribution })
if ($legacy.Count -eq 0) {
    $legacy = @($distros | Where-Object { $_.Version -eq 1 })
}

if (-not $Apply) {
    if ($legacy.Count -gt 0) {
        Write-Result "conversion_needed" $legacy[0].Name "An existing WSL1 distribution can be converted to WSL2 with -Apply. Its data will not be reset."
    } else {
        Write-Result "installation_needed" $Distribution "No WSL distribution was found. Use -Apply in elevated PowerShell to install Ubuntu WSL2."
    }
    exit 0
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Result "administrator_required" "" "Rerun with -Apply in an elevated PowerShell window."
    exit 2
}

if ($legacy.Count -gt 0) {
    $selected = $legacy[0].Name
    & wsl.exe --set-version $selected 2
    if ($LASTEXITCODE -ne 0) {
        Write-Result "conversion_failed" $selected "WSL conversion failed; inspect the preceding wsl.exe error."
        exit 1
    }
    $after = @(Get-WslDistributions | Where-Object { $_.Name -eq $selected -and $_.Version -eq 2 })
    if ($after.Count -gt 0) {
        Write-Result "ready" $selected "Existing distribution was converted to WSL2 without reinstalling it."
    } else {
        Write-Result "pending" $selected "Conversion command completed; rerun this script after checking wsl --list --verbose."
    }
    exit 0
}

& wsl.exe --install -d $Distribution
if ($LASTEXITCODE -ne 0) {
    Write-Result "installation_failed" $Distribution "WSL installation failed; inspect the preceding wsl.exe error."
    exit 1
}
Write-Result "pending" $Distribution "Restart Windows if requested, open the distribution to create a Linux user, then rerun this script."
