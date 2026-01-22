import pygame
from src.core import CityMap, CELL_WALL, CELL_START, CELL_FINISH, CELL_GARAGE
from src.engine import SimulationEngine


# Цветовая схема интерфейса и карты
COLORS = {
    'bg': (245, 247, 250),          # Основной фон
    'road': (230, 233, 237),        # Дороги / пустые клетки
    'wall': (52, 73, 94),           # Стены (глубокий сине-серый)
    'start': (46, 204, 113),        # Старт (зелёный)
    'finish': (231, 76, 60),        # Финиш (красный)
    'garage': (52, 152, 219),       # Гараж (синий)
    'agent': (142, 68, 173),        # Агент (фиолетовый)
    'npc': (243, 156, 18),          # Трафик / NPC (оранжево-жёлтый)
    'ui_bg': (220, 223, 228),       # Фон панели управления
    'btn_active': (41, 128, 185),   # Активная кнопка
    'btn_inactive': (189, 195, 199),# Неактивная кнопка
    'text': (44, 62, 80)            # Текст
}



class SimulationGUI:
    """
    Графический интерфейс управления симуляцией доставки.
    """

    def __init__(self, map_path):
        """
        Parameters
        ----------
        map_path : str
            Путь к файлу карты города.
        """
        self.map_path = map_path
        self.city_map = CityMap(map_path)

        # Параметры, изменяемые пользователем в UI
        self.ui_num_agents = 2
        self.ui_traffic_prob = 0.02

        # Параметры, с которыми запущен текущий движок
        self.running_num_agents = 0
        self.running_traffic_prob = 0

        pygame.init()

        self.cell_size = 20
        self.sidebar_width = 300
        self.map_display_width = self.city_map.width * self.cell_size

        self.screen = pygame.display.set_mode(
            (self.map_display_width + self.sidebar_width,
             self.city_map.height * self.cell_size)
        )
        pygame.display.set_caption("Реализация многоагентной среды с помощью многопроцессных вычислений")

        self.font = pygame.font.SysFont('Segoe UI', 14, bold=True)
        self.clock = pygame.time.Clock()

        self.engine = None
        self.reset_engine()

    def reset_engine(self):
        """
        Перезапускает симуляцию с текущими параметрами UI.
        """
        if self.engine:
            self.engine.shutdown()

        # Фиксируем параметры, с которыми работает движок
        self.running_num_agents = self.ui_num_agents
        self.running_traffic_prob = self.ui_traffic_prob

        self.engine = SimulationEngine(
            self.city_map,
            self.running_num_agents,
            self.running_traffic_prob
        )
        self.engine.start()

    def is_restart_allowed(self):
        """
        Определяет, активна ли кнопка перезапуска.

        Перезапуск разрешён, если:
        - параметры UI изменились,
        - либо все агенты завершили работу.
        """
        params_changed = (
            self.ui_num_agents != self.running_num_agents or
            abs(self.ui_traffic_prob - self.running_traffic_prob) > 1e-4
        )
        all_done = self.engine.all_finished()
        return params_changed or all_done

    def draw_ui(self):
        """
        Отрисовывает боковую панель управления.
        """
        ui_x = self.map_display_width
        pygame.draw.rect(
            self.screen,
            COLORS['ui_bg'],
            (ui_x, 0, self.sidebar_width, self.screen.get_height())
        )

        # Информационный блок
        y = 30
        info_lines = [
            f"Агентов: {self.ui_num_agents}",
            f"Шанс появления трафика: {self.ui_traffic_prob:.3f}",
            f"Активно на карте: {len([v for v in self.engine.active_agents.values() if v is not None])}",
            f"В очереди: {len(self.engine.spawn_queue)}",
            "",
            "УПРАВЛЕНИЕ:",
            "[+ / -]  Кол-во агентов",
            "[↑ / ↓]  Шанс трафика"
        ]

        for line in info_lines:
            img = self.font.render(line, True, COLORS['text'])
            self.screen.blit(img, (ui_x + 15, y))
            y += 30

        # Кнопка перезапуска
        is_active = self.is_restart_allowed()
        self.btn_rect = pygame.Rect(ui_x + 20, y + 20, 180, 45)

        btn_color = COLORS['btn_active'] if is_active else COLORS['btn_inactive']
        pygame.draw.rect(self.screen, btn_color, self.btn_rect, border_radius=8)

        btn_img = self.font.render("RESTART", True, (255, 255, 255))
        self.screen.blit(
            btn_img,
            (
                self.btn_rect.centerx - btn_img.get_width() // 2,
                self.btn_rect.centery - btn_img.get_height() // 2
            )
        )

    def run(self):
        """
        Главный цикл приложения.
        """
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.engine.shutdown()
                    pygame.quit()
                    return

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.ui_traffic_prob = min(0.3, self.ui_traffic_prob + 0.005)
                    elif event.key == pygame.K_DOWN:
                        self.ui_traffic_prob = max(0.0, self.ui_traffic_prob - 0.005)
                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                        self.ui_num_agents = min(6, self.ui_num_agents + 1)
                    elif event.key == pygame.K_MINUS:
                        self.ui_num_agents = max(1, self.ui_num_agents - 1)
                    elif event.key == pygame.K_r and self.is_restart_allowed():
                        self.reset_engine()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.btn_rect.collidepoint(event.pos) and self.is_restart_allowed():
                        self.reset_engine()

            # Шаг симуляции
            self.engine.step()

            # ===== Отрисовка карты =====
            self.screen.fill(COLORS['bg'])

            for y in range(self.city_map.height):
                for x in range(self.city_map.width):
                    rect = (
                        x * self.cell_size,
                        y * self.cell_size,
                        self.cell_size,
                        self.cell_size
                    )
                    cell = self.city_map.matrix[y, x]

                    if cell == CELL_WALL:
                        pygame.draw.rect(self.screen, COLORS['wall'], rect)
                    elif cell == CELL_START:
                        pygame.draw.rect(self.screen, COLORS['start'], rect)
                    elif cell == CELL_FINISH:
                        pygame.draw.rect(self.screen, COLORS['finish'], rect)
                    elif cell == CELL_GARAGE:
                        pygame.draw.rect(self.screen, COLORS['garage'], rect)
                    else:
                        pygame.draw.rect(self.screen, COLORS['road'], rect, 1)

            # ===== Отрисовка агентов и NPC =====
            for pos, oid in dict(self.engine.shared_positions).items():
                color = COLORS['agent'] if str(oid).startswith('A') else COLORS['npc']
                pygame.draw.circle(
                    self.screen,
                    color,
                    (
                        pos[0] * self.cell_size + self.cell_size // 2,
                        pos[1] * self.cell_size + self.cell_size // 2
                    ),
                    7
                )

            self.draw_ui()
            pygame.display.flip()
            self.clock.tick(15)


if __name__ == "__main__":
    SimulationGUI('data/citymap.txt').run()
