# =====================================================================
#  AVVIA.ps1 - avvia l'app in locale (dal PC e/o dal telefono)
#  Uso:  .\AVVIA.ps1
# =====================================================================
$ErrorActionPreference = "Continue"
$cartella = $PSScriptRoot
$porta = 8501

# ---------- 1. Python 3.13 a 64 bit ----------
$candidati = @(
    "C:\Users\toroe\AppData\Local\Programs\Python\Python313\python.exe",
    "$cartella\.venv\Scripts\python.exe"
)
$python = $null
foreach ($c in $candidati) {
    if (Test-Path $c) { $python = $c; break }
}
if (-not $python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $python = $cmd.Source } else {
        Write-Host "Python non trovato. Installa Python 3.11+ da python.org" -ForegroundColor Red
        Start-Sleep 10; exit 1
    }
}
Write-Host "Python usato : $python" -ForegroundColor Cyan

# ---------- 2. Libera la porta se gia' occupata ----------
$occupata = Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue
if ($occupata) {
    Write-Host "Porta $porta occupata: chiudo il vecchio avvio..." -ForegroundColor Yellow
    foreach ($c in $occupata) {
        try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop } catch {}
    }
    Start-Sleep -Seconds 2
}

# ---------- 3. Dipendenze ----------
& $python -c "import streamlit" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installo le dipendenze (solo la prima volta, 1-2 minuti)..." -ForegroundColor Yellow
    & $python -m pip install --quiet -r "$cartella\requirements.txt"
}

# ---------- 4. Indirizzo IP del PC ----------
$ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
       Where-Object { $_.IPAddress -notlike "127.*" -and
                      $_.IPAddress -notlike "169.254*" -and
                      $_.InterfaceAlias -notlike "*WARP*" } |
       Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "  ==============================================" -ForegroundColor Green
Write-Host "   APP PRONTA" -ForegroundColor Green
Write-Host "  ==============================================" -ForegroundColor Green
Write-Host "   Computer : http://localhost:$porta"
if ($ip) {
    Write-Host "   Telefono : http://${ip}:$porta" -ForegroundColor Yellow
    Write-Host "               (stesso Wi-Fi del PC)" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "   1) Apri l'indirizzo del Telefono nel browser"
Write-Host "   2) Menu browser > Aggiungi alla schermata Home"
Write-Host "   3) Lascia questa finestra aperta"
Write-Host ""
Write-Host "   Per fermare: Ctrl+C" -ForegroundColor DarkGray
Write-Host "  ==============================================" -ForegroundColor Green
Write-Host ""

# ---------- 5. Avvio ----------
& $python -m streamlit run "$cartella\app.py" --server.address 0.0.0.0 --server.port $porta
