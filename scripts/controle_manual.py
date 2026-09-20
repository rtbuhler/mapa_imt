"""
Controle manual do carro pelo teclado no CARLA.
Requer: pip install pygame (na venv_carla).
Mantenha a janelinha do pygame em foco para o teclado funcionar.

Teclas: W/Seta cima = acelerar | S/Seta baixo = freio
        A/D ou setas esq/dir = direcao | Q = alterna re | ESPACO = freio de mao
        R = reposiciona o carro no spawn inicial | ESC = sair
"""
import math
import pygame
import carla

client = carla.Client('localhost', 2000)
client.set_timeout(60.0)
world = client.get_world()
bp_lib = world.get_blueprint_library()
spawn_points = world.get_map().get_spawn_points()

vehicle_bp = bp_lib.filter('vehicle.*')[0]
spawn = None
vehicle = None
for sp in spawn_points:
    vehicle = world.try_spawn_actor(vehicle_bp, sp)
    if vehicle:
        spawn = sp
        break
if vehicle is None:
    raise SystemExit("Nao foi possivel spawnar o veiculo.")

spectator = world.get_spectator()
pygame.init()
tela = pygame.display.set_mode((420, 90))
pygame.display.set_caption("Controle CARLA - mantenha esta janela em foco")
fonte = pygame.font.SysFont(None, 26)
relogio = pygame.time.Clock()

def seguir_camera(snapshot):
    # roda a cada quadro do servidor, com a posicao exata daquele quadro (sem tremulacao)
    atual = snapshot.find(vehicle.id)
    if atual is None:
        return
    t = atual.get_transform()
    yaw = math.radians(t.rotation.yaw)
    spectator.set_transform(carla.Transform(
        t.location + carla.Location(x=-8 * math.cos(yaw), y=-8 * math.sin(yaw), z=4),
        carla.Rotation(pitch=-15, yaw=t.rotation.yaw)))


config_original = world.get_settings()
config = world.get_settings()
config.fixed_delta_seconds = 0.02  # passo de fisica constante, independe do FPS
world.apply_settings(config)
callback_id = world.on_tick(seguir_camera)

controle = carla.VehicleControl()
re = False
rodando = True
try:
    while rodando:
        relogio.tick(30)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                rodando = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    rodando = False
                elif e.key == pygame.K_q:
                    re = not re
                elif e.key == pygame.K_r:
                    vehicle.set_transform(spawn)
                    vehicle.set_target_velocity(carla.Vector3D(0, 0, 0))

        k = pygame.key.get_pressed()
        acel = k[pygame.K_w] or k[pygame.K_UP]
        freio = k[pygame.K_s] or k[pygame.K_DOWN]
        esq = k[pygame.K_a] or k[pygame.K_LEFT]
        dir_ = k[pygame.K_d] or k[pygame.K_RIGHT]

        controle.throttle = 0.45 if acel else 0.0
        controle.brake = 1.0 if freio else 0.0
        controle.hand_brake = bool(k[pygame.K_SPACE])
        controle.reverse = re
        v0 = vehicle.get_velocity()
        kmh0 = 3.6 * math.sqrt(v0.x ** 2 + v0.y ** 2 + v0.z ** 2)
        max_esterco = max(0.12, 0.3 - kmh0 / 120.0)  # menos esterco em alta velocidade
        alvo = -max_esterco if esq else (max_esterco if dir_ else 0.0)
        controle.steer += (alvo - controle.steer) * 0.3
        vehicle.apply_control(controle)

        v = vehicle.get_velocity()
        kmh = 3.6 * math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2)
        tela.fill((30, 30, 30))
        tela.blit(fonte.render(f"{kmh:5.1f} km/h   {'RE' if re else 'FRENTE'}", True, (255, 255, 255)), (10, 10))
        tela.blit(fonte.render("WASD/setas | Q re | ESPACO freio | R reset | ESC", True, (180, 180, 180)), (10, 50))
        pygame.display.flip()
finally:
    world.remove_on_tick(callback_id)
    world.apply_settings(config_original)
    vehicle.destroy()
    pygame.quit()
