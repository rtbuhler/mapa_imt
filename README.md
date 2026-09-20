# Mapa do campus IMT no CARLA

Pipeline para transformar vias desenhadas no QGIS (e pontos de altitude marcados à mão) em um mapa OpenDRIVE (`.xodr`) carregado no simulador CARLA 0.9.16, com teste automático e controle manual pelo teclado.

## Estrutura de pastas

```
mapa_imt/
├── README.md                 este tutorial
├── qgis/                     dados desenhados no QGIS
│   ├── vias_campus_imt_plano.*    vias (linhas, EPSG:4326)  <- usadas pelo conversor
│   ├── pontos_cotas_campo.*       pontos de cota (campo "cota")  <- usados pelo conversor
│   ├── vias_campus_imt.*          camada original de tracado
│   └── campus_imt_tracing.qgz     projeto QGIS
├── scripts/                  todos os scripts
│   ├── converter_3d.py            gera o .xodr (com altimetria ou plano)
│   ├── carregar_xodr_3d.py        carrega o mapa 3D no CARLA + barreiras
│   ├── carregar_xodr_plano.py     carrega o mapa plano no CARLA + barreiras
│   ├── runner.py                  teste automatico (autopilot)
│   ├── controle_manual.py         dirigir pelo teclado
│   └── executar_3d.ps1            faz tudo de uma vez
├── saida/                    arquivos gerados
│   ├── mapa_final_3d.xodr
│   ├── mapa_final_plano_2vias.xodr
│   └── intermediarios/            .nod.xml / .edg.xml usados pelo netconvert
├── midia/                    videos de demonstracao
├── legado/                   tentativas antigas (nao usadas mais)
└── venv_carla/               ambiente Python do CARLA (nao mover)
```

## Dois ambientes Python (importante)

| Uso | Python | Pacotes |
|---|---|---|
| Conversor (`converter_3d.py`) | Python do **sistema** (`C:\Python313`) | `pyproj`, `eclipse-sumo` (traz o `netconvert`) |
| CARLA (carregar, runner, controle) | **`venv_carla`** (Python 3.12) | `carla`, `pygame` |

Nunca rode o conversor com a venv ativa (nao tem `pyproj`) nem os scripts do CARLA sem ela (nao tem `carla`).

Instalacao unica:

```powershell
# sistema
pip install pyproj eclipse-sumo

# venv
.\venv_carla\Scripts\Activate.ps1
python -m pip install --upgrade "setuptools<81"
python -m pip install pygame
deactivate
```

## Passo a passo

### 1. Desenhar as vias no QGIS
1. Abra `qgis/campus_imt_tracing.qgz`.
2. Edite a camada de linhas com o eixo de cada rua. Cada rua e uma linha; **uma linha que termina no meio de outra vira um cruzamento em T** (ate 3 m de tolerancia).
3. Exporte como Shapefile, SRC **EPSG:4326**, para `qgis/vias_campus_imt_plano.shp`.

### 2. Marcar as cotas (altitudes)
1. `Camada > Criar Camada > Nova Camada Shapefile`: tipo Ponto, EPSG:4326, campo `cota` (decimal).
2. Com a edicao ativa, clique em cruzamentos, pontas e mudancas de declive e digite a altitude em metros.
3. Salve em `qgis/pontos_cotas_campo.shp`.
4. Quanto mais pontos, mais fiel o relevo. Evite cotas erradas: uma cota absurda vira rampa absurda.

### 3. Gerar o mapa OpenDRIVE
Na raiz `mapa_imt/`, com a venv **desativada**:

```powershell
python scripts\converter_3d.py            # mapa 3D  -> saida\mapa_final_3d.xodr
python scripts\converter_3d.py --plano    # mapa plano -> saida\mapa_final_plano_2vias.xodr
```

O que o conversor faz: reprojeta para UTM 23S (metros), cria os cruzamentos em T, interpola a cota (IDW), suaviza a subida ao longo de cada via, deixa as pontas planas nos cruzamentos e chama o `netconvert`. Cada rua vira duas pistas (ida e volta, 3,2 m cada).

Ao final ele mostra quantas elevacoes foram gravadas. Avisos do `netconvert` sobre declividade alta (> 20%) indicam cotas suspeitas ou trechos muito curtos.

### 4. Abrir o CARLA
```powershell
C:\CARLA_0.9.16\CarlaUE4.exe
```
Aguarde 30 a 60 s. Sem janela (servidor apenas): adicione `-RenderOffScreen`. Para mais FPS: `-quality-level=Low`.

### 5. Carregar o mapa no CARLA
```powershell
.\venv_carla\Scripts\Activate.ps1
python scripts\carregar_xodr_3d.py        # ou carregar_xodr_plano.py
```
O script gera o mundo e coloca barreiras (`static.prop.streetbarrier`) **apenas nas bordas externas** das vias.

### 6. Testar
**Automatico** (carro com autopilot por 60 s; passa se andar sem colidir):
```powershell
python scripts\runner.py
```

**Manual pelo teclado** (mantenha a janelinha do pygame em foco):
```powershell
python scripts\controle_manual.py
```

| Tecla | Acao |
|---|---|
| W / seta cima | Acelerar |
| S / seta baixo | Frear |
| A, D / setas | Direcao |
| Q | Alterna re |
| Espaco | Freio de mao |
| R | Volta ao ponto inicial |
| Esc | Sair |

### Atalho: tudo de uma vez
Com o CARLA aberto e a venv desativada:
```powershell
.\scripts\executar_3d.ps1          # 3D
.\scripts\executar_3d.ps1 -Plano   # plano
```

## Ajustes

| O que | Onde | Valor |
|---|---|---|
| Suavidade da subida | `converter_3d.py` -> `SUAV_SIGMA_M`, `SUAV_PASSES` | 60 m, 6 (maior = mais suave) |
| Comprimento plano junto aos cruzamentos | `converter_3d.py` -> `PLANO_NO_M` | 12 m |
| Tolerancia de cruzamento em T | `converter_3d.py` -> `TEE_M` | 3 m |
| Distancia entre vertices | `converter_3d.py` -> `PASSO_M` | 2,5 m |
| Malha da pista no CARLA | `carregar_*.py` -> `vertex_distance` | 0,5 m (1,0 se ficar lento) |
| Espacamento das barreiras | `carregar_*.py` -> `PASSO_BARREIRA` | 1,5 m |
| Velocidade do autopilot | `runner.py` -> `speed_diff_percent` | negativo = mais rapido que o limite, positivo = mais lento |
| Aceleracao (manual) | `controle_manual.py` -> `controle.throttle` | 0,45 |
| Esterco (manual) | `controle_manual.py` -> `max_esterco` | menor em alta velocidade |

## Problemas comuns

| Sintoma | Causa / solucao |
|---|---|
| `No module named 'carla'` | Voce esta fora da venv. Ative `venv_carla` |
| `No module named 'pyproj'` | Voce esta com a venv ativa. Rode `deactivate` e use o Python do sistema |
| `pkgutil has no attribute 'ImpImporter'` (pygame) | `python -m pip install --upgrade "setuptools<81"` na venv |
| `time-out ... waiting for the simulator` | CARLA nao esta aberto ou ainda carregando |
| Vias mais estreitas no plano | Use `converter_3d.py --plano` (gera ida e volta) |
| Degrau ou desnivel entre ruas | Cruzamento sem no compartilhado. Confira se a rua lateral termina a menos de 3 m da principal |
| Parede no meio da pista | Nao use `wall_height` do CARLA (cria parede entre as pistas). Ja esta em 0, as barreiras sao criadas pelo script |
| Carro trepida | Reduza a velocidade, aumente o FPS (`-quality-level=Low`), suba `vertex_distance` para 1,0 |
| Carro sai da pista em cruzamento | Curva muito fechada no tracado; suavize o desenho no QGIS |
| Declive de 30%+ | Cotas suspeitas ou via curta; revise os pontos no QGIS |

## Legado

`legado/` guarda o fluxo antigo (`netconvert --shapefile-prefix`, `converter_plano.py`, mapas gerados por ele, README anterior). Ele gerava vias de sentido unico e sem altimetria. Nao e mais usado.
