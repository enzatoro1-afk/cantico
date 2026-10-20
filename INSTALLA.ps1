# =====================================================================
#  INSTALLA.ps1 - pubblica l'app online con il minimo sforzo
#
#  Fa da solo:
#    1. installa Git se manca (con winget)
#    2. crea il repository su GitHub (via API, col tuo token)
#    3. carica tutto il codice
#    4. apre la pagina di deploy su Streamlit Cloud
#    5. quando l'app e' online, ti manda l'email col link definitivo
#
#  Uso:  .\INSTALLA.ps1
#        .\INSTALLA.ps1 -Utente "tuo-username" -Token "ghp_xxx"
# =====================================================================
param(
    [string]$Utente = "",
    [string]$Token = "",
    [string]$NomeRepo = "canzoni-tiktok",
    [switch]$SoloPreparazione
)

$ErrorActionPreference = "Continue"
$cartella = $PSScriptRoot

function Write-Step($n, $m) { Write-Host ""; Write-Host "[$n] $m" -ForegroundColor Cyan }
function Write-Ok($m) { Write-Host "    OK: $m" -ForegroundColor Green }
function Write-Warn($m) { Write-Host "    ATTENZIONE: $m" -ForegroundColor Yellow }
function Write-Err($m) { Write-Host "    ERRORE: $m" -ForegroundColor Red }

# ---------------------------------------------------------------
Write-Step 1 "Preparazione dell'ambiente"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "    Git non e' installato: lo installo (puo' durare 1-2 minuti)..." -ForegroundColor Yellow
    try {
        winget install --id Git.Git -e --silent --source winget `
            --accept-source-agreements --accept-package-agreements | Out-Null
    } catch {
        Write-Err "Installazione di Git fallita: $_"
    }
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Err "Git non disponibile. Riavvia il PC e rilancia questo script."
        Start-Sleep 15; exit 1
    }
}
Write-Ok ("Git " + (git --version))

# ---------------------------------------------------------------
Write-Step 2 "Account GitHub"
if ([string]::IsNullOrWhiteSpace($Utente)) {
    Write-Host "    Non serve un account nuovo: se ne hai gia' uno, scrivi qui lo username." -ForegroundColor Yellow
    Write-Host "    (se non ce l'hai, aprilo: https://github.com/join  e registrati in 2 minuti)" -ForegroundColor Yellow
    $Utente = (Read-Host "    Username GitHub").Trim()
}
if ([string]::IsNullOrWhiteSpace($Utente)) { Write-Err "Username mancante."; Start-Sleep 10; exit 1 }
Write-Ok "Username: $Utente"

if ([string]::IsNullOrWhiteSpace($Token)) {
    $urlToken = "https://github.com/settings/tokens/new?scopes=repo&description=Assistente%20canzoni%20pentecostali&name=app-canzoni"
    Write-Host ""
    Write-Host "    Adesso serve il TOKEN (e' l'unica cosa che devi fare tu)." -ForegroundColor Yellow
    Write-Host "    1) ti apro la pagina gia' pronta: prema 'Generate token'" -ForegroundColor Yellow
    Write-Host "    2) scegli 'Generate new token (classic)' -> spunta 'repo' -> Generate" -ForegroundColor Yellow
    Write-Host "    3) copia il token (inizia con ghp_) e incollalo qui" -ForegroundColor Yellow
    Start-Process $urlToken
    Start-Sleep 2
    $Token = (Read-Host "    Incolla qui il token").Trim()
}
if ([string]::IsNullOrWhiteSpace($Token)) { Write-Err "Token mancante."; Start-Sleep 10; exit 1 }

# controllo che il token sia valido
try {
    $verifica = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers @{
        "Authorization" = "Bearer $Token"
        "User-Agent"    = "AssistenteCanzoni"
    } -TimeoutSec 30
    Write-Ok ("Token valido. Account: " + $verifica.login)
} catch {
    Write-Err "Token non valido o senza internet: $($_.Exception.Message)"
    Start-Sleep 15; exit 1
}

# ---------------------------------------------------------------
Write-Step 3 "Creo il repository su GitHub"
$esiste = $false
try {
    Invoke-RestMethod -Uri "https://api.github.com/repos/$Utente/$NomeRepo" -Headers @{
        "Authorization" = "Bearer $Token"; "User-Agent" = "AssistenteCanzoni"
    } -TimeoutSec 30 | Out-Null
    $esiste = $true
} catch { $esiste = $false }

if ($esiste) {
    Write-Ok "Il repository $NomeRepo esiste gia': lo uso."
} else {
    try {
        $corpo = @{
            name        = $NomeRepo
            description = "Assistente Canzoni Pentecostali per TikTok (Streamlit)"
            private     = $false
            auto_init   = $true
        } | ConvertTo-Json
        Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method POST `
            -Headers @{ "Authorization" = "Bearer $Token"; "User-Agent" = "AssistenteCanzoni" } `
            -Body $corpo -ContentType "application/json" -TimeoutSec 60 | Out-Null
        Write-Ok "Repository creato: https://github.com/$Utente/$NomeRepo"
    } catch {
        Write-Err "Creazione repository fallita: $($_.Exception.Message)"
        Start-Sleep 15; exit 1
    }
}

if ($SoloPreparazione) {
    Write-Host ""
    Write-Host "    Tutto pronto. Rilancia senza -SoloPreparazione per caricare il codice." -ForegroundColor Green
    Start-Sleep 10; exit 0
}

# ---------------------------------------------------------------
Write-Step 4 "Carico il codice su GitHub"
Push-Location $cartella
try {
    if (-not (Test-Path ".git")) {
        git init -q 2>&1 | Out-Null
        git branch -M main 2>&1 | Out-Null
    }
    git config user.name  $Utente
    git config user.email "$Utente@users.noreply.github.com"
    git add -A 2>&1 | Out-Null
    git commit -q -m "Assistente Canzoni Pentecostali per TikTok" 2>&1 | Out-Null

    $urlConToken = "https://$Utente`:$Token@github.com/$Utente/$NomeRepo.git"
    git -c "remote.origin.url=$urlConToken" push -u origin main 2>&1 |
        Select-Object -Last 4 | ForEach-Object { Write-Host "    $_" }
    git remote remove origin 2>&1 | Out-Null
    git remote add origin "https://github.com/$Utente/$NomeRepo.git" 2>&1 | Out-Null
    Write-Ok "Codice caricato (il token NON e' rimasto in nessun file)"
} catch {
    Write-Err "Caricamento fallito: $($_.Exception.Message)"
} finally {
    Pop-Location
}

# ---------------------------------------------------------------
Write-Step 5 "Deploy su Streamlit Cloud (1 clic)"
$deploy = "https://share.streamlit.io/deploy?url=https://github.com/$Utente/$NomeRepo"
Write-Host ""
Write-Host "    Ti apro la pagina di deploy gia' compilata." -ForegroundColor Yellow
Write-Host "    1) clicca 'Authorize with GitHub' (accedi con lo stesso account)" -ForegroundColor Yellow
Write-Host "    2) clicca 'Deploy'" -ForegroundColor Yellow
Write-Host "    3) aspetta 1-2 minuti" -ForegroundColor Yellow
Start-Process $deploy
Start-Sleep 3
Write-Host ""
$premuto = Read-Host "    Quando l'app e' online (o vuoi procedere), premi INVIO"
if ([string]::IsNullOrWhiteSpace($premuto)) { $premuto = "invio" }

# ---------------------------------------------------------------
Write-Step 6 "Mando l'email con il link definitivo"
$possibili = @(
    "https://$NomeRepo.streamlit.app",
    "https://$Utente-$NomeRepo.streamlit.app"
)
Write-Host "    Se ricordi l'indirizzo esatto dell'app scrivilo (invio = prova automatico):" -ForegroundColor Yellow
$urlScelto = (Read-Host "    Indirizzo").Trim()
if ([string]::IsNullOrWhiteSpace($urlScelto)) {
    foreach ($p in $possibili) {
        try {
            $r = Invoke-WebRequest -Uri "$p/_stcore/health" -UseBasicParsing -TimeoutSec 12
            if ($r.Content -eq "ok") { $urlScelto = $p; Write-Ok "Trovata online: $p"; break }
        } catch { }
    }
}
if ([string]::IsNullOrWhiteSpace($urlScelto)) {
    Write-Warn "Non riesco a rilevare l'URL. Apri l'app su share.streamlit.io e copia l'indirizzo."
    $urlScelto = (Read-Host "    Indirizzo (o INVIO per annullare)").Trim()
}
if ([string]::IsNullOrWhiteSpace($urlScelto)) { Write-Warn "Operazione conclusa."; Start-Sleep 10; exit 0 }

# salvo il link per gli invii futuri
Set-Content -Path (Join-Path $cartella "link.txt") -Value $urlScelto -Encoding UTF8
Write-Ok "Link salvato in link.txt"

Write-Host ""
& (Join-Path $cartella "INVIA_EMAIL.ps1") -Link $urlScelto -A "enzatoro1@gmail.com"

Write-Host ""
Write-Host "    FATTO! Controlla la posta (enzatoro1@gmail.com): apri l'email, tocca" -ForegroundColor Green
Write-Host "    il link e poi 'Aggiungi alla schermata Home' sul telefono." -ForegroundColor Green
Start-Sleep 15
