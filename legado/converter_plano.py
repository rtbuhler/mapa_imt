import struct
import subprocess
import os
import sys

shp_name = "vias_campus_imt_plano.shp"

if not os.path.exists(shp_name):
    print(f"Erro: {shp_name} nao encontrado no diretorio atual.")
    sys.exit(1)

def ler_linhas_shapefile(caminho):
    linhas = []
    with open(caminho, "rb") as f:
        header = f.read(100)
        tamanho_arquivo = struct.unpack(">i", header[24:28])[0] * 2
        while f.tell() < tamanho_arquivo:
            reg_header = f.read(8)
            if len(reg_header) < 8:
                break
            _, comp_conteudo = struct.unpack(">ii", reg_header)
            conteudo = f.read(comp_conteudo * 2)
            if len(conteudo) < 4:
                break
            tipo_shape = struct.unpack("<i", conteudo[0:4])[0]
            
            # Tipos de linha: 3 (PolyLine), 13 (PolyLineZ), 23 (PolyLineM)
            if tipo_shape in (3, 13, 23):
                num_partes, num_pontos = struct.unpack("<ii", conteudo[36:44])
                offset = 44 + (num_partes * 4)
                pts = []
                for _ in range(num_pontos):
                    x, y = struct.unpack("<dd", conteudo[offset:offset+16])
                    pts.append((x, y))
                    offset += 16
                linhas.append(pts)
    return linhas

print(f"Lendo feicoes de {shp_name}...")
linhas = ler_linhas_shapefile(shp_name)
print(f"Total de segmentos carregados: {len(linhas)}")

nodes_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<nodes>\n'
edges_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<edges>\n'

for i, pts in enumerate(linhas):
    if len(pts) < 2:
        continue
    
    p_ini = pts[0]
    p_fim = pts[-1]
    
    # Se inicio e fim forem identicos, ajusta 1cm para evitar erro de no unico
    if (p_ini[0] - p_fim[0])**2 + (p_ini[1] - p_fim[1])**2 < 0.001:
        p_fim = (p_fim[0] + 0.01, p_fim[1] + 0.01)
        pts[-1] = p_fim

    n_from = f"no_{i}_ini"
    n_to = f"no_{i}_fim"

    nodes_xml += f'  <node id="{n_from}" x="{p_ini[0]:.3f}" y="{p_ini[1]:.3f}"/>\n'
    nodes_xml += f'  <node id="{n_to}" x="{p_fim[0]:.3f}" y="{p_fim[1]:.3f}"/>\n'

    shape_str = " ".join([f"{p[0]:.3f},{p[1]:.3f}" for p in pts])
    # Cria sentido duplo (ida e volta)
    edges_xml += f'  <edge id="edge_{i}_fwd" from="{n_from}" to="{n_to}" numLanes="1" speed="8.33" shape="{shape_str}"/>\n'
    edges_xml += f'  <edge id="edge_{i}_bwd" from="{n_to}" to="{n_from}" numLanes="1" speed="8.33" shape="{shape_str}"/>\n'

nodes_xml += '</nodes>'
edges_xml += '</edges>'

with open("campus_plano.nod.xml", "w", encoding="utf-8") as f:
    f.write(nodes_xml)

with open("campus_plano.edg.xml", "w", encoding="utf-8") as f:
    f.write(edges_xml)

print("Arquivos XML intermediarios gerados. Chamando netconvert...")

cmd = [
    "netconvert",
    "--node-files=campus_plano.nod.xml",
    "--edge-files=campus_plano.edg.xml",
    "--geometry.remove",
    "--junctions.join",
    "--junctions.join-dist=2.0",
    "--opendrive-output=mapa_final_plano.xodr"
]

res = subprocess.run(cmd, capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print(res.stderr)

if os.path.exists("mapa_final_plano.xodr"):
    tam_kb = os.path.getsize("mapa_final_plano.xodr") / 1024
    print(f"Sucesso: mapa_final_plano.xodr gerado com {tam_kb:.1f} KB.")
else:
    print("Falha ao gerar mapa_final_plano.xodr.")