# Define o diretório atual do script como o diretório de trabalho
Set-Location -Path $PSScriptRoot

# 1. Verifica se o CarlaUE4 já está em execução
$carlaProcess = Get-Process CarlaUE4 -ErrorAction SilentlyContinue
if (-not $carlaProcess) {
    Write-Host "Iniciando o simulador CARLA (janela visivel)..." -ForegroundColor Cyan
    Start-Process -FilePath "C:\CARLA_0.9.16\CarlaUE4.exe"
    Write-Host "Aguardando o simulador abrir (isso pode levar ~30-60s)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
}

# 2. Localiza e ativa o ambiente virtual
$venvActivate = ".\venv_carla\Scripts\Activate.ps1"

if (-not (Test-Path $venvActivate)) {
    Write-Error "Ambiente virtual 'venv_carla' não encontrado neste diretório."
    exit 1
}

Write-Host "Ativando ambiente virtual venv_carla..." -ForegroundColor Cyan
& $venvActivate

# 3. Carrega o mapa customizado (mapa_final.xodr) no simulador
Write-Host "Carregando mapa_final.xodr..." -ForegroundColor Green
python .\carregar_xodr.py

# 4. Roda o teste automatizado (spawna um carro com autopilot e verifica a pista)
Write-Host "Executando runner.py (teste com autopilot)..." -ForegroundColor Green
python .\runner.py

# 5. Desativa o venv ao concluir
deactivate
Write-Host "Processo concluído." -ForegroundColor Cyan
