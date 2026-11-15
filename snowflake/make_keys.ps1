# Creates the three Snowflake key pairs (airbyte, transform, reader) and a ready-to-paste copy of
# setup.sql with the PUBLIC keys filled in.
#
#   - Private keys (*_key.p8) are written to $KeyDir, which is OUTSIDE the repository, and are
#     never printed or copied anywhere else.
#   - The filled SQL (setup_filled.sql) contains public keys only. It is also placed on your
#     clipboard (unless -NoClipboard) so you can paste it straight into a Snowflake worksheet.
#   - It refuses to overwrite existing keys.
#
# Run from the project root in PowerShell:   .\snowflake\make_keys.ps1
param(
    [string]$KeyDir = (Join-Path $HOME '.snowflake'),
    [switch]$NoClipboard
)

$ErrorActionPreference = 'Stop'

$ssl = 'C:\Program Files\Git\usr\bin\openssl.exe'
if (-not (Test-Path $ssl)) {
    $found = Get-Command openssl -ErrorAction SilentlyContinue
    if (-not $found) { throw 'OpenSSL was not found (it comes with Git for Windows).' }
    $ssl = $found.Source
}

function Invoke-Ssl {
    # Run openssl quietly and stop if it fails (its progress text goes to stderr).
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $ssl @args *> $null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    if ($code -ne 0) { throw "openssl failed (exit code $code): openssl $($args -join ' ')" }
}

$names = 'airbyte', 'transform', 'reader'
New-Item -ItemType Directory -Force -Path $KeyDir | Out-Null

foreach ($n in $names) {
    if (Test-Path (Join-Path $KeyDir "${n}_key.p8")) {
        throw "A key for '$n' already exists in $KeyDir. This script never overwrites keys. Move or delete the old files first."
    }
}

$sql = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'setup.sql'))

foreach ($n in $names) {
    $tmp = Join-Path $KeyDir "${n}_tmp.pem"
    $p8  = Join-Path $KeyDir "${n}_key.p8"     # private key, PKCS#8, unencrypted
    $pub = Join-Path $KeyDir "${n}_key.pub"    # public key

    Invoke-Ssl genrsa -out $tmp 2048
    Invoke-Ssl pkcs8 -topk8 -inform PEM -in $tmp -out $p8 -nocrypt
    Remove-Item $tmp -Force
    Invoke-Ssl rsa -in $p8 -pubout -out $pub
    Invoke-Ssl pkey -in $p8 -noout    # sanity check: the private key loads

    # only this user may read the private key
    icacls $p8 /inheritance:r /grant:r "$($env:USERNAME):(R,W)" *> $null

    # public key body: the base64 text without the BEGIN/END lines, on one line
    $body = ((Get-Content $pub) | Where-Object { $_ -notmatch '^-----' }) -join ''
    if ($body.Length -lt 300) { throw "Public key for '$n' looks too short." }
    $sql = $sql.Replace("<$($n.ToUpper())_PUBLIC_KEY>", $body)
}

if ($sql -match '<[A-Z]+_PUBLIC_KEY>') { throw 'A public-key placeholder is still in the SQL.' }

$out = Join-Path $KeyDir 'setup_filled.sql'
[IO.File]::WriteAllText($out, $sql, (New-Object Text.UTF8Encoding($false)))
if (-not $NoClipboard) { Set-Clipboard -Value $sql }

Write-Host ''
Write-Host 'Done. Private keys were NOT printed.'
Write-Host "Keys folder (outside the repo): $KeyDir"
foreach ($n in $names) { Write-Host "  - ${n}_key.p8 (private, keep secret)   ${n}_key.pub (public)" }
Write-Host "Filled SQL: $out"
if (-not $NoClipboard) { Write-Host 'The filled SQL (public keys only) is on your clipboard: paste it into the Snowflake worksheet.' }
Write-Host ''
Write-Host 'Add these lines to your local .env later (paths only, forward slashes):'
$fwd = $KeyDir.Replace('\', '/')
Write-Host "  SNOWFLAKE_DBT_PRIVATE_KEY_PATH=$fwd/transform_key.p8"
Write-Host "  SNOWFLAKE_READER_PRIVATE_KEY_PATH=$fwd/reader_key.p8"
