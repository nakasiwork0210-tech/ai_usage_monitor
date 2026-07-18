# Usage Monitor インストーラ (brew cask 相当)
#   インストール:   powershell -ExecutionPolicy Bypass -File install.ps1
#   自動起動つき:   powershell -ExecutionPolicy Bypass -File install.ps1 -AutoStart
#   アンインストール: powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall
param(
    [switch]$AutoStart,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$installDir = Join-Path $env:LOCALAPPDATA "Programs\UsageMonitor"
$exePath = Join-Path $installDir "UsageMonitor.exe"
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Usage Monitor.lnk"
$startupVbs = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\usage_monitor.vbs"
$srcExe = Join-Path $PSScriptRoot "dist\UsageMonitor.exe"

# 既存プロセスを停止
Get-Process UsageMonitor -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 500

if ($Uninstall) {
    foreach ($f in @($startMenu, $startupVbs)) {
        if (Test-Path $f) { Remove-Item $f -Force }
    }
    if (Test-Path $installDir) { Remove-Item $installDir -Recurse -Force }
    Write-Host "アンインストールしました。(~/.claude や ~/.codex の認証情報には触れていません)"
    exit 0
}

if (-not (Test-Path $srcExe)) {
    Write-Host "dist\UsageMonitor.exe が見つかりません。先にビルドしてください:"
    Write-Host "  pip install pyinstaller"
    Write-Host "  pyinstaller --onefile --windowed --name UsageMonitor usage_monitor.py"
    exit 1
}

New-Item -ItemType Directory -Force $installDir | Out-Null
Copy-Item $srcExe $exePath -Force

# スタートメニューにショートカット
$sh = New-Object -ComObject WScript.Shell
$lnk = $sh.CreateShortcut($startMenu)
$lnk.TargetPath = $exePath
$lnk.WorkingDirectory = $installDir
$lnk.Description = "Claude / Codex usage monitor"
$lnk.Save()

if ($AutoStart) {
    Set-Content -Path $startupVbs -Encoding utf8 -Value ('CreateObject("WScript.Shell").Run """' + $exePath + '""", 0, False')
    Write-Host "自動起動: ON"
}

Start-Process $exePath -WorkingDirectory $installDir
Write-Host "インストール完了: $exePath"
Write-Host "タスクトレイに常駐しています。スタートメニューの「Usage Monitor」からも起動できます。"
