# =====================================================================
#  INVIA_EMAIL.ps1 - manda l'app via email dal PC
#
#  Uso:
#     .\INVIA_EMAIL.ps1                     # usa link.txt (o il link locale)
#     .\INVIA_EMAIL.ps1 -Link "https://canzoni-tiktok.streamlit.app"
#     .\INVIA_EMAIL.ps1 -A "altra@email.it" # altro destinatario
#     .\INVIA_EMAIL.ps1 -Prova              # non invia: mostra com'e' (prova)
#     .\INVIA_EMAIL.ps1 -SoloLink           # solo link, niente ZIP
# =====================================================================
param(
    [string]$Link = "",
    [string]$A = "enzatoro1@gmail.com",
    [string]$Cartella = $PSScriptRoot,
    [switch]$Prova,
    [switch]$SoloLink
)

$ErrorActionPreference = "Continue"

function Write-Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }

# ---------- 1. Quale link usare ----------
if ([string]::IsNullOrWhiteSpace($Link)) {
    $fileLink = Join-Path $Cartella "link.txt"
    if (Test-Path $fileLink) {
        $Link = (Get-Content $fileLink -Encoding UTF8 -Raw).Trim()
        # ignora le righe di commento del file di esempio
        $candidate = ($Link -split "`n" | Where-Object { $_ -match "^https?://" } | Select-Object -First 1)
        if ($candidate) { $Link = $candidate.Trim() }
    }
}

if ([string]::IsNullOrWhiteSpace($Link) -or $Link -notmatch "^https?://") {
    # nessun link cloud: uso l'indirizzo di questa rete (funziona in casa)
    $ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
           Where-Object { $_.IPAddress -notlike "127.*" -and
                          $_.IPAddress -notlike "169.254*" -and
                          $_.InterfaceAlias -notlike "*WARP*" } |
           Select-Object -First 1).IPAddress
    if ($ip) {
        $Link = "http://${ip}:8501"
        Write-Host "Nessun link cloud in link.txt: uso quello locale." -ForegroundColor Yellow
        Write-Host "Per il link definitivo (funziona OVUNQUE) rilancia dopo il deploy:" -ForegroundColor Yellow
        Write-Host "   .\INVIA_EMAIL.ps1 -Link `"https://canzoni-tiktok.streamlit.app`"" -ForegroundColor Yellow
    }
}

if ([string]::IsNullOrWhiteSpace($Link)) {
    Write-Host "Nessun link: operazione annullata." -ForegroundColor Red
    Start-Sleep 10
    exit 1
}
Write-Step "Link: $Link"

# ---------- 2. Corpo dell'email ----------
$fileTesto = Join-Path $Cartella "email_testo.txt"
if (Test-Path $fileTesto) {
    $corpo = Get-Content $fileTesto -Encoding UTF8 -Raw
} else {
    $corpo = "Ciao!`r`n`r`nEcco l'app:`r`n`r`n__LINK__`r`n`r`nBuon lavoro!"
}
$corpo = $corpo.Replace("__LINK__", $Link)
$corpo = $corpo.Replace("__DATA__", (Get-Date -Format "dd/MM/yyyy HH:mm"))

$oggetto = "La tua app Canzoni Pentecostali per TikTok (pronta per il telefono)"

# ---------- 3. ZIP del codice ----------
# ATTENZIONE: nello ZIP NON devono finire le chiavi del proprietario
# (secrets.toml, SEGRETS-CLOUD.txt, i file .chiave_* e il cookie Suno).
# Chi riceve l'app deve usare le PROPRIE chiavi.
$zip = $null
if (-not $SoloLink) {
    Write-Step "Preparo lo ZIP del codice..."
    $zip = Join-Path ([System.IO.Path]::GetTempPath()) "Assistente-Canzone-TikTok.zip"
    if (Test-Path $zip) { Remove-Item $zip -Force }

    # cartella di appoggio: ci copio il codice PULITO (senza chiavi)
    $stage = Join-Path ([System.IO.Path]::GetTempPath()) ("cantico_zip_" + [guid]::NewGuid().ToString("N").Substring(0,8))
    New-Item -ItemType Directory -Path $stage -Force | Out-Null

    $esclusi = @(".venv", "venv", "__pycache__", ".git", "SEGRETS-CLOUD.txt",
                 ".chiave_gemini_server.json", ".chiave_treblo_server.json",
                 ".chiave_hf_server.json", ".suno_cookie.txt", "link.txt")
    $da_escludere = @("secrets.toml")

    Get-ChildItem -Path $Cartella -Force | Where-Object {
        $_.Name -notin $esclusi -and $_.Extension -ne ".zip" -and
        # i TUOI post salvati e i video di prova: dati personali del
        # proprietario, non viaggiano con l'app
        $_.Name -notlike "archivio_*.json" -and
        $_.Name -notlike "PROVA_*"
    } | ForEach-Object {
        if ($_.PSIsContainer) {
            # dentro .streamlit prendo SOLO config.toml (mai secrets.toml)
            if ($_.Name -eq ".streamlit") {
                $dest = Join-Path $stage ".streamlit"
                New-Item -ItemType Directory -Path $dest -Force | Out-Null
                Get-ChildItem -Path $_.FullName -Force -File | Where-Object {
                    $_.Name -notin $da_escludere
                } | ForEach-Object { Copy-Item $_.FullName $dest -Force }
            } else {
                Copy-Item $_.FullName $stage -Recurse -Force
            }
        } else {
            Copy-Item $_.FullName $stage -Force
        }
    }

    try {
        Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zip -Force
        Write-Step "ZIP pronto: $zip"
    } catch {
        Write-Host "Non sono riuscito a creare lo ZIP (procedo senza)." -ForegroundColor Yellow
        $zip = $null
    } finally {
        Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# ---------- 4. Anteprima (modalita' prova) ----------
if ($Prova) {
    Write-Host ""
    Write-Host "---------------- ANTEPRIMA ----------------" -ForegroundColor Magenta
    Write-Host ("A: $A")
    Write-Host ("Oggetto: $oggetto")
    Write-Host "----------------------------------------"
    Write-Host $corpo
    Write-Host "----------------------------------------"
    Write-Host ("Allegato: " + $(if ($zip) { $zip } else { "nessuno" }))
    Write-Host "MODALITA' PROVA: nessuna email inviata." -ForegroundColor Magenta
    Start-Sleep 10
    exit 0
}

# ---------- 5. Invio ----------
$inviato = $false

# 5a) Outlook
try {
    $outlook = New-Object -ComObject Outlook.Application
    $mail = $outlook.CreateItem(0)
    $mail.To = $A
    $mail.Subject = $oggetto
    $mail.Body = $corpo
    if ($zip -and (Test-Path $zip)) { $mail.Attachments.Add($zip) | Out-Null }
    $mail.Save()
    $mail.Send()
    $inviato = $true
    Write-Host "Email inviata con Outlook a $A" -ForegroundColor Green
} catch {
    Write-Host "Outlook non disponibile: apro il tuo programma email." -ForegroundColor Yellow
}

# 5b) programma email predefinito
if (-not $inviato) {
    $corpoBreve = @"
Ciao!

Ecco l'app "Assistente Canzoni Pentecostali per TikTok":

$Link

Come installarla sul telefono:
1) Tocca il link (si apre nel browser).
2) Menu del browser -> "Aggiungi alla schermata Home".
3) Da lì si apre come un'app, a schermo intero, con la sua icona.

Buon lavoro!
"@
    $mailto = "mailto:$A?subject=$([System.Uri]::EscapeDataString($oggetto))&body=$([System.Uri]::EscapeDataString($corpoBreve))"
    try {
        Start-Process $mailto
        Write-Host "Aperto il tuo programma email con il messaggio gia' pronto." -ForegroundColor Green
        Write-Host "Premi INVIO per inviare a $A" -ForegroundColor Yellow
        if ($zip) {
            Write-Host "Allega anche lo ZIP: $zip" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "Non riesco ad aprire il programma email." -ForegroundColor Red
        Write-Host "Copia e incolla questo link: $Link" -ForegroundColor Yellow
    }
}

Write-Step "Fatto. Sul telefono: apri l'email, tocca il link, poi 'Aggiungi alla schermata Home'."
