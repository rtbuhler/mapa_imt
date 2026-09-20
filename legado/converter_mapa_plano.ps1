param(
    [string]$Prefix = "vias_campus_imt_plano",
    [string]$OutputFile = "mapa_final_plano.xodr",
    [string]$Speed = "8.33",
    [int]$Lanes = 1
)

$params = @(
    "--shapefile-prefix", $Prefix,
    "--shapefile.street-id", "id",
    "--shapefile.use-defaults-on-failure",
    "--shapefile.guess-projection",
    "--default.speed", $Speed,
    "--default.lanenumber", $Lanes.ToString(),
    "--opendrive-output", $OutputFile
)

Write-Host "Iniciando conversao do Shapefile para OpenDRIVE..." -ForegroundColor Cyan

& netconvert @params

if ($LASTEXITCODE -eq 0 -and (Test-Path -Path $OutputFile)) {
    Write-Host "Sucesso: '$OutputFile' gerado com exito." -ForegroundColor Green
} else {
    Write-Host "Erro: Falha ao gerar o arquivo OpenDRIVE." -ForegroundColor Red
    exit 1
}