import numpy as np

# Типы клеток карты (кодирование в входном файле)
CELL_EMPTY = 0      # Свободная дорога, по которой можно перемещаться
CELL_WALL = 1       # Стена
CELL_START = 2      # Начальная позиция агента
CELL_GARAGE = 3     # Точка генерации трафика (гараж)
CELL_FINISH = 4     # Целевая точка доставки


class CityMap:
    """
    Класс для загрузки и представления городской карты в виде матрицы.

    Карта загружается из текстового файла, где каждая строка представляет строку сетки,
    а каждый символ — тип клетки (см. константы CELL_*).

    Attributes
    ----------
    matrix : np.ndarray
        Двумерная матрица карты.
    width : int
        Ширина карты (количество колонок).
    height : int
        Высота карты (количество строк).
    garages : list[tuple[int, int]]
        Координаты гаражей (источников трафика).
    starts : list[tuple[int, int]]
        Координаты стартовых позиций агентов.
    finish : tuple[int, int]
        Координаты целевой точки.
    """

    def __init__(self, file_path: str):
        """
        Загружает карту из файла и извлекает ключевые точки.

        Parameters
        ----------
        file_path : str
            Путь к текстовому файлу с описанием карты.
        """
        self.matrix = self._load_map(file_path)
        self.height, self.width = self.matrix.shape

        # Координаты гаражей и стартовых точек
        self.garages = [(int(x), int(y)) for y, x in zip(*np.where(self.matrix == CELL_GARAGE))]
        self.starts = [(int(x), int(y)) for y, x in zip(*np.where(self.matrix == CELL_START))]

        # Предполагается одна целевая точка
        res_finish = np.where(self.matrix == CELL_FINISH)
        self.finish = (int(res_finish[1][0]), int(res_finish[0][0]))

    def _load_map(self, file_path: str) -> np.ndarray:
        """
        Загружает карту из текстового файла.

        Файл может содержать метаданные в квадратных скобках, которые игнорируются.

        Parameters
        ----------
        file_path : str
            Путь к файлу.

        Returns
        -------
        np.ndarray
            Двумерный массив целых чисел, представляющий карту.
        """
        with open(file_path, 'r') as f:
            # Игнорируем пустые строки и метаданные вида [ ... ]
            lines = [
                line.strip()
                for line in f.readlines()
                if line.strip() and not line.startswith('[')
            ]

        # Преобразуем символы в целые числа
        matrix = [[int(char) for char in line] for line in lines]
        return np.array(matrix)

    def is_walkable(self, x: int, y: int) -> bool:
        """
        Проверяет, можно ли перемещаться в указанную клетку.

        Клетка считается проходимой, если:
        - находится внутри карты;
        - не является стеной.

        Parameters
        ----------
        x : int
            Координата по оси X (колонка).
        y : int
            Координата по оси Y (строка).

        Returns
        -------
        bool
            True, если клетка проходима, иначе False.
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.matrix[y, x] != CELL_WALL
        return False
