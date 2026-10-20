# =====================================================================
#  CARICA.ps1 - carica il codice nel repo GitHub (e apre il deploy)
#
#  Uso:  .\CARICA.ps1
#  (oppure: .\CARICA.ps1 -Token "ghp_xxxx")
# =====================================================================
param(
    [string]$Utente = "enzatoro1-afk",
    [string]$NomeRepo = "canzoni-tiktok",
    [string]$Token = ""
)

$ErrorActionPreference = "Continue"
$cartella = $PSScriptRoot
$env:Path += ";C:\Program Files\Git\cmd"

function Write-Step($n, $m) { Write-Host ""; Write-Host "[$n] $m" -ForegroundColor Cyan }
function Write-Ok($m) { Write-Host "    OK: $m" -ForegroundColor Green }
function Write-Err($m) { Write-Host "    ERRORE: $m" -ForegroundColor Red }

Write-Step 1 "Controllo Git"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Err "Git non trovato. Rilancia INSTALLA.ps1 che lo installa."
    Start-Sleep 10; exit 1
}
Write-Ok (git --version)

Write-Step 2 "Token GitHub"
if ([string]::IsNullOrWhiteSpace($Token)) {
    $url = "https://github.com/settings/tokens/new?scopes=repo&description=Assistente%20canzoni%20pentecostali&name=app-canzoni"
    Write-Host "    Ti apro la pagina del token gia' pronta." -ForegroundColor Yellow
    Write-Host "    -> spunta la casella 'repo' -> Generate new token -> copia il token" -ForegroundColor Yellow
    Write-Host "    (incolla qui il token che inizia con ghp_)" -ForegroundColor Yellow
    Start-Process $url
    Start-Sleep 2
    $Token = (Read-Host "    Token").Trim()
}
if ([string]::IsNullOrWhiteSpace($Token)) { Write-Err "Token mancante."; Start-Sleep 10; exit 1 }
try {
    $me = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers @{
        "Authorization" = "Bearer $Token"; "User-Agent" = "AssistenteCanzoni"
    } -TimeoutSec 30
    Write-Ok ("Token valido per: " + $me.login)
    $Utente = $me.login
} catch {
    Write-Err "Token non valido: $($_.Exception.Message)"
    Start-Sleep 10; exit 1
}

Write-Step 3 "Carico il codice"
Push-Location $cartella
try {
    if (-not (Test-Path ".git")) { git init -q 2>&1 | Out-Null; git branch -M main 2>&1 | Out-Null }
    git config user.name  $Utente
    git config user.email "$Utente@users.noreply.github.com"
    git add -A 2>&1 | Out-Null
    git commit -q -m "Assistente Canzoni Pentecostali per TikTok - codice completo" 2>&1 | Out-Null

    # creo il repo se manca
    try {
        Invoke-RestMethod -Uri "https://api.github.com/repos/$Utente/$NomeRepo" -Headers @{
            "Authorization" = "Bearer $Token"; "User-Agent" = "AssistenteCanzoni"
        } -TimeoutSec 30 | Out-Null
        Write-Ok "Repository gia' esistente"
    } catch {
        $corpo = @{
            name = $NomeRepo; description = "Assistente Canzoni Pentecostali per TikTok (Streamlit)"
            private = $false; auto_init = $false
        } | ConvertTo-Json
        Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method POST `
            -Headers @{ "Authorization" = "Bearer $Token"; "User-Agent" = "AssistenteCanzoni" } `
            -Body $corpo -ContentType "application/json" -TimeoutSec 60 | Out-Null
        Write-Ok "Repository creato"
    }

    $urlConToken = "https://$Utente`:$Token@github.com/$Utente/$NomeRepo.git"
    $out = git -c "remote.origin.url=$urlConToken" push -u origin main 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host ($out | Select-Object -Last 6 | ForEach-Object { "    $_" })
        Write-Err "Push non riuscito."
    } else {
        Write-Ok "Codice caricato su https://github.com/$Utente/$NomeRepo"
        Write-Ok "IL TOKEN NON E' RIMASTO IN ALCUN FILE"
    }
    # remote pulito, senza token
    git remote remove origin 2>&1 | Out-Null
    git remote add origin "https://github.com/$Utente/$NomeRepo.git" 2>&1 | Out-Null
} finally {
    Pop-Location
}

Write-Step 4 "Apro la pagina di deploy"
$deploy = "https://share.streamlit.io/deploy?url=https://github.com/$Utente/$NomeRepo"
Start-Process $deploy
Write-Host ""
Write-Host "    NELLA PAGINA CHE SI APRE, IMPOSTA COSI' :" -ForegroundColor Yellow
Write-Host "      Repository       : $Utente/$NomeRepo      (gia' giusto)" -ForegroundColor Yellow
Write-Host "      Branch           : main                    (gia' giusto)" -ForegroundColor Yellow
Write-Host "      Main file path   : app.py                  <-- CAMBIA QUESTO" -ForegroundColor Yellow
Write-Host "      App URL          : un sottodominio LIBERO  <-- CAMBIA QUESTO" -ForegroundColor Yellow
Write-Host ""
Write-Host "    Se 'canzoni-evangeliche-tiktok' e' gia' preso, prova con:" -ForegroundColor Yellow
Write-Host "      canzoni-pentecostali-enzo" -ForegroundColor Yellow
Write-Host "      enzo-lode-tiktok" -ForegroundColor Yellow
Write-Host "      lode-evangelica-enzo" -ForegroundColor Yellow
Write-Host ""
Write-Host "    Poi clicca DEPLOY. Quando e' online, torna qui e rilancia:" -ForegroundColor Green
Write-Host "      .\INVIA_EMAIL.ps1 -Link ""https://<il-tuo-sottodominio>.streamlit.app""" -ForegroundColor Green
Start-Sleep 20
