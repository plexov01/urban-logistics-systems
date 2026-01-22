import multiprocessing
import random
import time
import threading


def delivery_agent_worker(
    agent_id,
    goal_pos,
    city_map,
    shared_positions,
    active_agents,
    barrier,
    stop_event,
    stats
):
    """
    Рабочий процесс агента доставки.

    Агент действует в дискретных тактах, синхронизированных через Barrier:
    1. Планирование маршрута
    2. Перемещение
    3. Завершение такта

    Parameters
    ----------
    agent_id : int
        Уникальный идентификатор агента.
    goal_pos : tuple[int, int]
        Координаты целевой точки доставки.
    city_map : CityMap
        Карта города.
    shared_positions : multiprocessing.Manager().dict
        Общий словарь занятых клеток {(x, y): entity_id}.
    active_agents : multiprocessing.Manager().dict
        Состояние агентов {agent_id: позиция или None}.
    barrier : multiprocessing.Barrier
        Барьер синхронизации агентов и координатора.
    stop_event : multiprocessing.Event
        Сигнал завершения симуляции.
    stats : multiprocessing.Manager().list
        Статистика агентов (шаги, тики).
    """
    goal_pos = (int(goal_pos[0]), int(goal_pos[1]))

    finished = False
    steps_taken = 0
    ticks_total = 0

    try:
        while not stop_event.is_set():
            if not finished:
                ticks_total += 1

            # ===== ФАЗА 1: ПЛАНИРОВАНИЕ =====
            barrier.wait()

            my_pos = active_agents.get(agent_id)
            next_step = None

            if my_pos and not finished:
                from src.utils import a_star
                path = a_star(my_pos, goal_pos, city_map, shared_positions)

                # Берем только следующий шаг маршрута
                if path:
                    next_step = (int(path[0][0]), int(path[0][1]))

            # ===== ФАЗА 2: ДВИЖЕНИЕ =====
            barrier.wait()

            if my_pos and not finished and next_step:
                # Можно двигаться, если клетка свободна или это цель
                if next_step not in shared_positions or next_step == goal_pos:
                    # Освобождаем предыдущую позицию
                    if shared_positions.get(my_pos) == f"A{agent_id}":
                        del shared_positions[my_pos]

                    steps_taken += 1

                    if next_step == goal_pos:
                        # Агент завершил доставку
                        finished = True
                        active_agents[agent_id] = None
                        stats[agent_id] = (steps_taken, ticks_total)

                        print(
                            f"[Agent {agent_id}] Финишировал! "
                            f"Шаги: {steps_taken}, Тики: {ticks_total}"
                        )
                    else:
                        active_agents[agent_id] = next_step
                        shared_positions[next_step] = f"A{agent_id}"

            # ===== ФАЗА 3: КОНЕЦ ТАКТА =====
            barrier.wait()

            # Завершивший агент продолжает участвовать в барьере
            if finished and stop_event.is_set():
                break

    except (threading.BrokenBarrierError, Exception):
        # При аварийной остановке симуляции
        pass

    finally:
        # Освобождаем занятую клетку при выходе
        my_pos = active_agents.get(agent_id)
        if my_pos and my_pos in shared_positions:
            try:
                del shared_positions[my_pos]
            except KeyError:
                pass


class SimulationEngine:
    """
    Координатор многопроцессной симуляции доставки.

    Отвечает за:
    - синхронизацию тактов,
    - генерацию и движение NPC,
    - выпуск агентов,
    - завершение симуляции.
    """

    def __init__(self, city_map, num_agents=2, traffic_prob=0.02):
        """
        Parameters
        ----------
        city_map : CityMap
            Карта города.
        num_agents : int
            Количество агентов доставки.
        traffic_prob : float
            Вероятность генерации NPC в гараже на такт.
        """
        self.map = city_map
        self.num_agents = num_agents
        self.traffic_prob = traffic_prob

        self.manager = multiprocessing.Manager()

        # Общие структуры для синхронизации процессов
        self.shared_positions = self.manager.dict()
        self.active_agents = self.manager.dict()
        self.stats = self.manager.list([None] * num_agents)

        self.stop_event = multiprocessing.Event()

        # Очередь агентов, ожидающих выезда
        self.spawn_queue = list(range(num_agents))

        # Барьер: все агенты + координатор
        self.barrier = multiprocessing.Barrier(num_agents + 1)

        self.processes = []
        self.npc_list = []

    def _try_spawn_agents(self):
        """Пытается выпустить агентов на свободные стартовые точки."""
        for start_pos in self.map.starts:
            if not self.spawn_queue:
                break

            s_pos = (int(start_pos[0]), int(start_pos[1]))

            if s_pos not in self.shared_positions:
                agent_id = self.spawn_queue.pop(0)
                self.active_agents[agent_id] = s_pos
                self.shared_positions[s_pos] = f"A{agent_id}"

                print(f"[Engine] Агент {agent_id} выехал из {s_pos}")

    def _move_npcs(self):
        """Перемещает NPC согласно простой стохастической модели."""
        new_npc_list = []

        for npc in self.npc_list:
            if npc['ttl'] <= 0:
                if npc['pos'] in self.shared_positions:
                    del self.shared_positions[npc['pos']]
                continue

            x, y = npc['pos']
            possible_dirs = []

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                if self.map.is_walkable(x + dx, y + dy):
                    possible_dirs.append((dx, dy))

            if not possible_dirs:
                new_npc_list.append(npc)
                continue

            # С вероятностью 0.7 продолжаем движение в прежнем направлении
            move = (
                npc['dir']
                if npc['dir'] in possible_dirs and random.random() < 0.7
                else random.choice(possible_dirs)
            )

            new_pos = (int(x + move[0]), int(y + move[1]))

            if new_pos not in self.shared_positions:
                if npc['pos'] in self.shared_positions:
                    del self.shared_positions[npc['pos']]

                npc['pos'] = new_pos
                npc['dir'] = move
                self.shared_positions[new_pos] = npc['id']

            npc['ttl'] -= 1
            new_npc_list.append(npc)

        self.npc_list = new_npc_list

    def _spawn_npc(self):
        """Генерирует NPC в гаражах согласно вероятности."""
        for garage in self.map.garages:
            if random.random() < self.traffic_prob:
                g_pos = (int(garage[0]), int(garage[1]))

                if g_pos not in self.shared_positions:
                    npc_id = f"N{time.time()}"
                    self.npc_list.append({
                        'id': npc_id,
                        'pos': g_pos,
                        'ttl': random.randint(15, 150),
                        'dir': random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
                    })
                    self.shared_positions[g_pos] = npc_id

    def start(self):
        """Запускает процессы агентов."""
        for i in range(self.num_agents):
            self.active_agents[i] = None

            p = multiprocessing.Process(
                target=delivery_agent_worker,
                args=(
                    i,
                    self.map.finish,
                    self.map,
                    self.shared_positions,
                    self.active_agents,
                    self.barrier,
                    self.stop_event,
                    self.stats
                )
            )
            p.start()
            self.processes.append(p)

    def step(self):
        """Выполняет один такт симуляции."""
        self.barrier.wait()   # Фаза планирования
        self._try_spawn_agents()
        self._move_npcs()
        self._spawn_npc()
        self.barrier.wait()   # Фаза движения
        self.barrier.wait()   # Конец такта

    def all_finished(self):
        """Проверяет, завершили ли работу все агенты."""
        on_map = [v for v in self.active_agents.values() if v is not None]
        return not self.spawn_queue and not on_map

    def shutdown(self):
        """Корректно завершает симуляцию."""
        self.stop_event.set()
        try:
            self.barrier.abort()
        except Exception:
            pass

        for p in self.processes:
            p.join(0.1)
            if p.is_alive():
                p.terminate()
