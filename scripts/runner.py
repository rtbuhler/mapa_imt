"""
Runner de teste do mapa mapa_final.xodr no CARLA.

Assume que carregar_xodr.py ja foi executado (mundo OpenDRIVE gerado).
Spawna um veiculo, liga o autopilot via Traffic Manager, deixa rodar
por alguns segundos e verifica se o veiculo realmente se moveu e
permaneceu sem colisao grave.
"""
import time
import sys
import carla


def main():
    client = carla.Client('localhost', 2000)
    client.set_timeout(60.0)

    world = client.get_world()
    bp_lib = world.get_blueprint_library()
    spawn_points = world.get_map().get_spawn_points()

    if not spawn_points:
        print("FALHA: nenhum spawn point encontrado no mapa. "
              "Verifique se o mapa_final.xodr foi carregado corretamente.")
        sys.exit(1)

    vehicle_bp = bp_lib.filter('vehicle.*')[0]
    vehicle = None
    collision_events = []

    for sp in spawn_points:
        vehicle = world.try_spawn_actor(vehicle_bp, sp)
        if vehicle is not None:
            break

    if vehicle is None:
        print("FALHA: nao foi possivel spawnar nenhum veiculo em nenhum "
              f"dos {len(spawn_points)} spawn points.")
        sys.exit(1)

    print(f"Veiculo '{vehicle.type_id}' spawnado em {vehicle.get_location()}.")

    collision_bp = bp_lib.find('sensor.other.collision')
    collision_sensor = world.spawn_actor(
        collision_bp, carla.Transform(), attach_to=vehicle
    )
    collision_sensor.listen(lambda event: collision_events.append(event))

    try:
        tm = client.get_trafficmanager()
        tm_port = tm.get_port()
        vehicle.set_autopilot(True, tm_port)

        # Velocidade relativa ao limite de velocidade da via (%).
        # Negativo = mais rapido que o limite, positivo = mais devagar.
        # Ex.: -50 -> 50% mais rapido; 30 -> 30% mais devagar.
        speed_diff_percent = -100
        tm.vehicle_percentage_speed_difference(vehicle, speed_diff_percent)

        start_location = vehicle.get_location()
        duration_s = 60
        print(f"Rodando teste com autopilot por {duration_s}s...")

        t0 = time.time()
        while time.time() - t0 < duration_s:
            world.tick() if world.get_settings().synchronous_mode else time.sleep(0.5)

        end_location = vehicle.get_location()
        distance = start_location.distance(end_location)

        print(f"Posicao inicial: {start_location}")
        print(f"Posicao final:   {end_location}")
        print(f"Distancia percorrida: {distance:.2f} m")
        print(f"Colisoes detectadas: {len(collision_events)}")

        ok = distance > 1.0 and len(collision_events) == 0

        if ok:
            print("RESULTADO: SUCESSO - o veiculo trafegou pelo mapa sem colisoes.")
        else:
            if distance <= 1.0:
                print("RESULTADO: FALHA - o veiculo praticamente nao se moveu "
                      "(possivel problema de conectividade/topologia das vias).")
            if collision_events:
                print("RESULTADO: FALHA - colisao detectada durante o teste.")
            sys.exit(1)

    finally:
        collision_sensor.destroy()
        vehicle.destroy()


if __name__ == '__main__':
    main()
