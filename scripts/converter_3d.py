"""
Gera mapa_final_3d.xodr a partir de:
  - vias_campus_imt_plano.shp  (linhas, EPSG:4326)
  - pontos_cotas_campo.shp     (pontos, EPSG:4326, campo 'cota')

Passos: reprojeta para UTM 23S (metros), interpola a cota (IDW) em cada
vertice das vias, escreve nos/arestas do SUMO com z e chama o netconvert.
Requer: pyproj e netconvert (eclipse-sumo) no Python que executar este script.
"""
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

from pyproj import Transformer

BASE = Path(__file__).resolve().parent.parent


def achar(nome):
    for pasta in (BASE / "qgis", BASE):
        if (pasta / nome).exists():
            return pasta / nome
    return BASE / "qgis" / nome


SHP_VIAS = achar("vias_campus_imt_plano.shp")
SHP_COTAS = achar("pontos_cotas_campo.shp")
DBF_COTAS = achar("pontos_cotas_campo.dbf")
CAMPO_COTA = "cota"
EPSG_METROS = "EPSG:31983"   # SIRGAS 2000 / UTM 23S
PASSO_M = 2.5                # distancia maxima entre vertices apos densificar
SUAV_SIGMA_M = 60.0         # largura (m) da suavizacao da cota ao longo da via; maior = rampa mais suave
SUAV_PASSES = 6             # repeticoes da suavizacao
PLANO_NO_M = 12.0            # comprimento (m) junto a cada no em que a via chega com inclinacao zero
TEE_M = 3.0                 # ponta a ate essa distancia do meio de outra via vira cruzamento em T
SNAP_M = 1.0                # extremos a menos que isso viram o mesmo no
IDW_K = 6                    # vizinhos usados na interpolacao
IDW_POT = 2.0
PLANO = "--plano" in sys.argv   # python converter_3d.py --plano -> mesma malha, sem altimetria
SAIDA = BASE / "saida" / ("mapa_final_plano_2vias.xodr" if PLANO else "mapa_final_3d.xodr")
PREFIXO = BASE / "saida" / "intermediarios" / ("campus_plano_2vias" if PLANO else "campus_3d")
PREFIXO.parent.mkdir(parents=True, exist_ok=True)


def ler_shapes(caminho, tipos):
    out = []
    with open(caminho, "rb") as f:
        dados = f.read()
    pos = 100
    while pos + 8 <= len(dados):
        _, tam = struct.unpack(">ii", dados[pos:pos + 8])
        c = dados[pos + 8:pos + 8 + tam * 2]
        pos += 8 + tam * 2
        if len(c) < 4:
            break
        t = struct.unpack("<i", c[:4])[0]
        if t not in tipos:
            continue
        if t in (1, 11, 21):
            out.append([struct.unpack("<2d", c[4:20])])
        else:
            n_partes, n_pts = struct.unpack("<ii", c[36:44])
            partes = list(struct.unpack(f"<{n_partes}i", c[44:44 + 4 * n_partes]))
            off = 44 + 4 * n_partes
            pts = [struct.unpack("<2d", c[off + 16 * i:off + 16 * i + 16]) for i in range(n_pts)]
            partes.append(n_pts)
            for a, b in zip(partes, partes[1:]):
                out.append(pts[a:b])
    return out


def ler_dbf_campo(caminho, campo):
    d = open(caminho, "rb").read()
    n = struct.unpack("<I", d[4:8])[0]
    hl, rl = struct.unpack("<HH", d[8:12])
    campos, off = [], 1
    for i in range((hl - 33) // 32):
        h = d[32 + i * 32:64 + i * 32]
        nome = h[:11].split(b"\0")[0].decode("latin-1")
        campos.append((nome, off, h[16]))
        off += h[16]
    ini, tam = next((o, t) for nm, o, t in campos if nm.lower() == campo.lower())
    return [float(d[hl + i * rl + ini:hl + i * rl + ini + tam].decode("latin-1").strip())
            for i in range(n)]


def main():
    for arq in (SHP_VIAS, SHP_COTAS, DBF_COTAS):
        if not os.path.exists(arq):
            sys.exit(f"Erro: {arq} nao encontrado no diretorio atual.")

    tr = Transformer.from_crs("EPSG:4326", EPSG_METROS, always_xy=True)

    linhas_ll = [l for l in ler_shapes(SHP_VIAS, (3, 13, 23)) if len(l) >= 2]
    pts_ll = [p[0] for p in ler_shapes(SHP_COTAS, (1, 11, 21))]
    cotas = ler_dbf_campo(DBF_COTAS, CAMPO_COTA)
    if len(pts_ll) != len(cotas):
        sys.exit("Erro: numero de pontos difere do numero de cotas no .dbf.")

    linhas = [[tr.transform(x, y) for x, y in l] for l in linhas_ll]
    cot_xy = [tr.transform(x, y) for x, y in pts_ll]

    ox = min(x for l in linhas for x, _ in l)
    oy = min(y for l in linhas for _, y in l)
    z0 = min(cotas)
    print(f"Vias: {len(linhas)} | Cotas: {len(cotas)} ({min(cotas):.2f} a {max(cotas):.2f} m)")
    print(f"Origem UTM removida: x={ox:.2f} y={oy:.2f} | Z de referencia: {z0:.2f}")

    linhas = [[(x - ox, y - oy) for x, y in l] for l in linhas]
    cot_xy = [(x - ox, y - oy) for x, y in cot_xy]

    def proj_seg(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        n2 = dx * dx + dy * dy
        t = 0.0 if n2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n2))
        q = (a[0] + t * dx, a[1] + t * dy)
        return math.hypot(p[0] - q[0], p[1] - q[1]), q, t

    def dividir_em_T(linhas):
        """Pontas que encostam no meio de outra via viram um no: a outra via e dividida ali."""
        linhas = [list(l) for l in linhas]
        cortes = {j: [] for j in range(len(linhas))}  # j -> [(seg, t, ponto)]
        for i, l in enumerate(linhas):
            for fim in (0, -1):
                p = l[fim]
                melhor, perto_de_no = None, False
                for j, m in enumerate(linhas):
                    if j == i:
                        continue
                    if min(math.hypot(p[0] - m[0][0], p[1] - m[0][1]),
                           math.hypot(p[0] - m[-1][0], p[1] - m[-1][1])) <= SNAP_M:
                        perto_de_no = True
                        break
                    for k, (a, b) in enumerate(zip(m, m[1:])):
                        d, q, t = proj_seg(p, a, b)
                        if d <= TEE_M and (melhor is None or d < melhor[0]):
                            melhor = (d, j, k, t, q)
                if perto_de_no or melhor is None:
                    continue
                _, j, k, t, q = melhor
                for _, _, q2 in cortes[j]:
                    if math.hypot(q[0] - q2[0], q[1] - q2[1]) <= SNAP_M:
                        q = q2
                        break
                else:
                    cortes[j].append((k, t, q))
                l[fim] = q
        saida = []
        for j, m in enumerate(linhas):
            cs = sorted(cortes[j], key=lambda c: (c[0], c[1]))
            if not cs:
                saida.append(m)
                continue
            novo, marcas = [], []
            for idx, pt in enumerate(m):
                novo.append(pt)
                for k, _, q in cs:
                    if k == idx:
                        marcas.append(len(novo))
                        novo.append(q)
            ini = 0
            for mk in marcas:
                saida.append(novo[ini:mk + 1])
                ini = mk
            saida.append(novo[ini:])
        n_antes = len(linhas)
        print(f"Cruzamentos em T criados: {len(saida) - n_antes} divisoes")
        return [l for l in saida if len(l) >= 2]

    linhas = dividir_em_T(linhas)

    def z_em(x, y):
        if PLANO:
            return 0.0
        viz =sorted(((math.hypot(x - px, y - py), c) for (px, py), c in zip(cot_xy, cotas)))[:IDW_K]
        if viz[0][0] < 0.01:
            return viz[0][1] - z0
        w = [1.0 / d ** IDW_POT for d, _ in viz]
        return sum(wi * c for wi, (_, c) in zip(w, viz)) / sum(w) - z0

    def densificar(pts):
        res = [pts[0]]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = max(1, int(math.ceil(math.hypot(x1 - x0, y1 - y0) / PASSO_M)))
            for k in range(1, n + 1):
                res.append((x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n))
        return res

    nos = []  # [x, y]

    def no_para(p):
        for i, (nx, ny) in enumerate(nos):
            if math.hypot(p[0] - nx, p[1] - ny) <= SNAP_M:
                return i
        nos.append([p[0], p[1]])
        return len(nos) - 1

    arestas = []
    for pts in linhas:
        pts = densificar(pts)
        a, b = no_para(pts[0]), no_para(pts[-1])
        if a == b:
            continue
        arestas.append((a, b, pts))

    nos_xml = ['<?xml version="1.0" encoding="UTF-8"?>', "<nodes>"]
    for i, (x, y) in enumerate(nos):
        nos_xml.append(f'  <node id="n{i}" x="{x:.3f}" y="{y:.3f}" z="{z_em(x, y):.3f}"/>')
    # (z dos nos = z_em; as pontas das arestas sao fixadas nesse mesmo valor abaixo)
    nos_xml.append("</nodes>")

    z_nos = [z_em(x, y) for x, y in nos]

    def suavizar(pts, zs):
        s = [0.0]
        for p, q in zip(pts, pts[1:]):
            s.append(s[-1] + math.hypot(q[0] - p[0], q[1] - p[1]))
        for _ in range(SUAV_PASSES):
            novo = zs[:]
            for i in range(len(zs)):
                ws = [(math.exp(-0.5 * ((s[j] - s[i]) / SUAV_SIGMA_M) ** 2), zs[j])
                      for j in range(len(zs)) if abs(s[j] - s[i]) <= 3 * SUAV_SIGMA_M]
                novo[i] = sum(w * z for w, z in ws) / sum(w for w, _ in ws)
            zs = novo
        return zs

    def shape(pts, zs):
        return " ".join(f"{x:.3f},{y:.3f},{z:.3f}" for (x, y), z in zip(pts, zs))

    arestas_xml = ['<?xml version="1.0" encoding="UTF-8"?>', "<edges>"]
    for i, (a, b, pts) in enumerate(arestas):
        pts = [(nos[a][0], nos[a][1])] + pts[1:-1] + [(nos[b][0], nos[b][1])]
        zs = [z_em(x, y) for x, y in pts]
        zs = suavizar(pts, zs)
        # correcao linear para as pontas coincidirem com a cota dos nos, sem degrau
        comp = [0.0]
        for p, q in zip(pts, pts[1:]):
            comp.append(comp[-1] + math.hypot(q[0] - p[0], q[1] - p[1]))
        da, db = z_nos[a] - zs[0], z_nos[b] - zs[-1]
        zs = [z + da * (1 - s / comp[-1]) + db * (s / comp[-1]) for z, s in zip(zs, comp)]
        # pontas com inclinacao zero (emenda suave entre vias no cruzamento)
        lf = min(PLANO_NO_M, comp[-1] / 2.5)
        def ease(u):
            u = max(0.0, min(1.0, u))
            return u * u * (3 - 2 * u)
        zs = [z_nos[a] * (1 - ease(s / lf)) + z * ease(s / lf) if s < lf else z
              for z, s in zip(zs, comp)]
        zs = [z_nos[b] * (1 - ease((comp[-1] - s) / lf)) + z * ease((comp[-1] - s) / lf)
              if comp[-1] - s < lf else z for z, s in zip(zs, comp)]
        arestas_xml.append(f'  <edge id="e{i}_f" from="n{a}" to="n{b}" numLanes="1" speed="8.33" '
                           f'shape="{shape(pts, zs)}"/>')
        arestas_xml.append(f'  <edge id="e{i}_b" from="n{b}" to="n{a}" numLanes="1" speed="8.33" '
                           f'shape="{shape(pts[::-1], zs[::-1])}"/>')
    arestas_xml.append("</edges>")

    open(f"{PREFIXO}.nod.xml", "w", encoding="utf-8").write("\n".join(nos_xml))
    open(f"{PREFIXO}.edg.xml", "w", encoding="utf-8").write("\n".join(arestas_xml))
    print(f"Nos: {len(nos)} | Arestas (cada uma ida+volta): {len(arestas)}")

    cmd = ["netconvert", f"--node-files={PREFIXO}.nod.xml", f"--edge-files={PREFIXO}.edg.xml",
           f"--opendrive-output={SAIDA}", "--junctions.scurve-stretch=1.0"]
    print("Executando:", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    if not os.path.exists(SAIDA):
        sys.exit(f"Falha ao gerar {SAIDA}.")

    xodr = open(SAIDA, encoding="utf-8").read()
    elev = re.findall(r'<elevation [^>]*a="([-\d.eE+]+)"[^>]*b="([-\d.eE+]+)"', xodr)
    nao_zero = sum(1 for a, b in elev if abs(float(a)) > 1e-6 or abs(float(b)) > 1e-6)
    print(f"{SAIDA}: {os.path.getsize(SAIDA) / 1024:.1f} KB | "
          f"elevacoes: {len(elev)} | com valor != 0: {nao_zero}")
    if nao_zero == 0 and not PLANO:
        print("AVISO: nenhuma elevacao gravada; o netconvert ignorou o Z.")


if __name__ == "__main__":
    main()
