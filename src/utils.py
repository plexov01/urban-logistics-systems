import heapq


def get_distance(p1, p2):
    """
    Манхэттенское расстояние между двумя точками.

    Используется как эвристика для A* на прямоугольной сетке
    с перемещением только по четырём направлениям.

    Parameters
    ----------
    p1, p2 : tuple[int, int]
        Координаты точек.

    Returns
    -------
    int
        Манхэттенское расстояние.
    """
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def a_star(start, goal, city_map, shared_positions):
    """
    Поиск кратчайшего пути от start до goal с учётом динамических препятствий.

    Алгоритм учитывает:
    - статические препятствия (стены карты),
    - динамические препятствия (другие агенты и NPC),
    - возможность входа в целевую клетку даже если она занята.

    Parameters
    ----------
    start : tuple[int, int]
        Начальная позиция агента.
    goal : tuple[int, int]
        Целевая позиция.
    city_map : CityMap
        Объект карты города.
    shared_positions : dict
        Словарь занятых клеток {(x, y): entity_id}.

    Returns
    -------
    list[tuple[int, int]] | None
        Список координат пути (без стартовой клетки) или None,
        если путь не найден.
    """
    # Возможные смещения (вверх, вниз, вправо, влево)
    neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    closed_set = set()        # Уже обработанные клетки
    came_from = {}            # Для восстановления пути

    gscore = {start: 0}       # Стоимость пути от старта
    fscore = {start: get_distance(start, goal)}  # g + эвристика

    open_heap = []
    heapq.heappush(open_heap, (fscore[start], start))

    while open_heap:
        current = heapq.heappop(open_heap)[1]

        # Цель достигнута — восстанавливаем путь
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            return path[::-1]

        closed_set.add(current)

        for dx, dy in neighbors:
            neighbor = (current[0] + dx, current[1] + dy)

            # Непроходимая клетка (стена или выход за карту)
            if not city_map.is_walkable(neighbor[0], neighbor[1]):
                continue

            # Динамическое препятствие:
            # в занятые клетки нельзя, кроме целевой
            if neighbor in shared_positions and neighbor != goal:
                continue

            tentative_g_score = gscore[current] + 1

            # Если уже обрабатывали с меньшей стоимостью — пропускаем
            if neighbor in closed_set and tentative_g_score >= gscore.get(neighbor, float('inf')):
                continue

            # Новый или более короткий путь
            if tentative_g_score < gscore.get(neighbor, float('inf')):
                came_from[neighbor] = current
                gscore[neighbor] = tentative_g_score
                fscore[neighbor] = tentative_g_score + get_distance(neighbor, goal)
                heapq.heappush(open_heap, (fscore[neighbor], neighbor))

    # Путь не найден (пробка, тупик или полная блокировка)
    return None
