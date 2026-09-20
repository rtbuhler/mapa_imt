import carla

# 1. Conectar ao servidor do CARLA
client = carla.Client('localhost', 2000)
client.set_timeout(60.0)

# 2. Ler o conteúdo do arquivo OpenDRIVE
xodr_path = 'mapa_final.xodr'
with open(xodr_path, 'r', encoding='utf-8') as f:
    xodr_content = f.read()

# 3. Parâmetros com a assinatura exata do CARLA 0.9.16
params = carla.OpendriveGenerationParameters(
    vertex_distance=2.0,
    max_road_length=50.0,
    wall_height=0.0,
    additional_width=0.6,
    smooth_junctions=True,
    enable_mesh_visibility=True,
    enable_pedestrian_navigation=True
)

# 4. Gerar o mundo procedural
world = client.generate_opendrive_world(xodr_content, params)

print("Mapa OpenDRIVE carregado com sucesso no CARLA.")
