# UsageMonitor.exe にコード署名する。
#
# 使い方:
#   # 1) 本番: PFX ファイルで署名 (SignPath / 購入証明書などで入手した .pfx)
#   powershell -File sign.ps1 -PfxPath cert.pfx -PfxPassword "***"
#
#   # 2) 本番: 証明書ストアの拇印で署名 (HSM/トークン系)
#   powershell -File sign.ps1 -Thumbprint ABCD1234...
#
#   # 3) テスト: 自己署名でパイプライン確認 (★他人のPCでは警告は消えません)
#   powershell -File sign.ps1 -SelfSignedTest
#
# 署名後は必ず RFC3161 タイムスタンプを付与するので、証明書失効後も署名は有効なまま。
param(
    [string]$Exe = "$PSScriptRoot\dist\UsageMonitor.exe",
    [string]$PfxPath,
    [string]$PfxPassword,
    [string]$Thumbprint,
    [switch]$SelfSignedTest,
    [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"

# signtool を探す
$signtool = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
if (-not $signtool) { throw "signtool.exe が見つかりません。Windows SDK をインストールしてください。" }
if (-not (Test-Path $Exe)) { throw "署名対象が見つかりません: $Exe" }

$stArgs = @("sign", "/fd", "SHA256", "/tr", $TimestampUrl, "/td", "SHA256", "/v")

if ($SelfSignedTest) {
    Write-Host "[テスト] 自己署名証明書を作成します (他人のPCでは SmartScreen 警告は消えません)" -ForegroundColor Yellow
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=UsageMonitor Test" `
        -CertStoreLocation Cert:\CurrentUser\My -KeyUsage DigitalSignature `
        -HashAlgorithm SHA256 -NotAfter (Get-Date).AddYears(3)
    $stArgs += @("/sha1", $cert.Thumbprint)
}
elseif ($Thumbprint) {
    $stArgs += @("/sha1", $Thumbprint)
}
elseif ($PfxPath) {
    if (-not (Test-Path $PfxPath)) { throw "PFX が見つかりません: $PfxPath" }
    $stArgs += @("/f", $PfxPath)
    if ($PfxPassword) { $stArgs += @("/p", $PfxPassword) }
}
else {
    throw "証明書の指定が必要です: -PfxPath / -Thumbprint / -SelfSignedTest のいずれか"
}

$stArgs += $Exe
Write-Host "署名中: $Exe" -ForegroundColor Cyan
& $signtool @stArgs
if ($LASTEXITCODE -ne 0) { throw "署名に失敗しました (exit $LASTEXITCODE)" }

Write-Host "`n=== 署名の検証 ===" -ForegroundColor Cyan
& $signtool verify /pa /v $Exe
