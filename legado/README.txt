Instale o QGIS:
    QGIS-OSGeo4W-3.44.14-1.msi

Desenhe o mapa e exporte a camada nas opções:
    Formato: Shapefile
    SRC: EPSG:4326
    Demais opções no padrão

Converter mapa para formato .xodr:
Instale netconverter (terminal): 
    pip install eclipse-sumo

cd até o diretório onde está o mapa e executar a conversão:
    netconvert --shapefile-prefix vias_campus_imt --shapefile.street-id id --shapefile.use-defaults-on-failure true --shapefile.guess-projection true --default.speed 8.33 --default.lanenumber 1 --opendrive-output mapa_final.xodr

Instale o Carla:
    CARLA_0.9.16.zip
    pip install carla

Execute o Carla:
    C:\CarlaUE4.exe

Carregue o mapa no Carla:
    python carregar_xodr.py

Carregue a simulação do veículo (runner):
    python runner.py

Para adicionar a elevação ao mapa:
    

Criar pontos cotados de controle e interpolar (Recomendado para malhas maiores)
Se as vias tiverem muitos vértices, é inviável digitar nó a nó. 
O ideal é marcar apenas os pontos conhecidos (início, cruzamentos, lombadas, fim de via) e deixar o QGIS calcular o gradiente suave entre eles.

Criar uma camada de pontos cotados:
1. No menu superior, vá em Camada > Criar Camada > Nova Camada Shapefile...
2. Defina o nome (ex: pontos_cotas_campo.shp)
3. Tipo de geometria: Ponto
4. Projeção: o mesmo SRC das suas vias (ex: SIRGAS 2000 / UTM zone 23S)
5. Na seção Novo Campo:
Nome: cota
Tipo: Número decimal (real)
Clique em Adicionar à Lista de Campos
6. Clique em OK.

Adicionar os pontos com as altitudes conhecidas (QGIS)
1. Ative a edição na camada pontos_cotas_campo (ícone do lápis)
2. Selecione Adicionar Ponto e clique sobre as interseções e pontos de referência das vias
3. Para cada clique, uma janela abrirá pedindo o atributo cota: digite o valor medido em campo (ex: 762.45)
4. Salve e encerre a edição da camada.




netconvert --shapefile-prefix vias_campus_3d --shapefile.street-id id --shapefile.use-defaults-on-failure --shapefile.guess-projection --junctions.join --default.speed 8.33 --default.lanenumber 1 --verbose --opendrive-output mapa_final_3d.xodr


netconvert --shapefile-prefix vias_campus_3d --shapefile.street-id id --shapefile.use-defaults-on-failure --shapefile.traditional-axis-mapping --proj "+proj=utm +zone=23 +south +ellps=GRS80 +units=m +no_defs" --default.speed 8.33 --default.lanenumber 1 --opendrive-output mapa_final_3d.xodr


netconvert --shapefile-prefix vias_campus_3d_single --shapefile.street-id id --shapefile.use-defaults-on-failure --shapefile.guess-projection --shapefile.all-bidi --junctions.join --default.speed 8.33 --default.lanenumber 1 --verbose --opendrive-output mapa_final_3d.xodr


