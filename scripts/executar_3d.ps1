# Uso (a partir de qualquer pasta, com a venv DESATIVADA):
#   .\scripts\executar_3d.ps1           -> mapa 3D (com altimetria)
#   .\scripts\executar_3d.ps1 -Plano    -> mapa plano (ida e volta, sem altimetria)
param([switch]$Plano)

$raiz = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $raiz "venv_carla\Scripts\python.exe"

# Etapa 1: gerar o .xodr (Python do sistema: precisa de pyproj e netconvert)
# Requer: pip install pyproj eclipse-sumo
if ($Plano) {
    Write-Host "Gerando mapa_final_plano_2vias.xodr..." -ForegroundColor Cyan
    python (Join-Path $PSScriptRoot "converter_3d.py") --plano
    $carregador = "carregar_xodr_plano.py"
} else {
    Write-Host "Gerando mapa_final_3d.xodr..." -ForegroundColor Cyan
    python (Join-Path $PSScriptRoot "converter_3d.py")
    $carregador = "carregar_xodr_3d.py"
}
if ($LASTEXITCODE -ne 0) { Write-Error "Falha na conversao."; exit 1 }

# Etapa 2: com o CARLA aberto, carregar o mapa e rodar o runner (venv com o pacote carla)
if (-not (Get-Process CarlaUE4 -ErrorAction SilentlyContinue)) {
    Write-Warning "CarlaUE4.exe nao esta em execucao. Abra C:\CARLA_0.9.16\CarlaUE4.exe e rode este script novamente."
    exit 1
}

& $venvPython (Join-Path $PSScriptRoot $carregador)
& $venvPython (Join-Path $PSScriptRoot "runner.py")
