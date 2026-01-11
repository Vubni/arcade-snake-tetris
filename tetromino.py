"""Класс тетромино"""
import copy
from constants import TETROMINOES


def get_rgb(color):
    """Преобразует цвет arcade в RGB кортеж"""
    if isinstance(color, tuple):
        return color[:3] if len(color) >= 3 else (255, 255, 255)
    try:
        return (color[0], color[1], color[2]) if hasattr(color, '__getitem__') else (255, 255, 255)
    except:
        return (255, 255, 255)


class Tetromino:
    """Класс для управления тетромино (фигурой)"""

    def __init__(self, piece_type, color, x, y):
        """
        Создает новую фигуру
        piece_type: тип фигуры ('I', 'J', 'L', 'O', 'S', 'T', 'Z')
        color: цвет фигуры (RGB кортеж)
        x, y: начальная позиция фигуры
        """
        self.piece_type = piece_type
        self.color = color
        self.x = x
        self.y = y
        self.shape = copy.deepcopy(TETROMINOES[piece_type])

    def get_positions(self):
        """Возвращает список абсолютных позиций блоков фигуры"""
        positions = []
        for dx, dy in self.shape:
            positions.append((self.x + dx, self.y + dy))
        return positions

    def move(self, dx, dy):
        """Перемещает фигуру на указанное смещение"""
        self.x += dx
        self.y += dy

    def rotate(self):
        """Поворачивает фигуру на 90 градусов по часовой стрелке"""
        if self.piece_type == 'O':  # Квадрат не поворачивается
            return

        # Поворот: (x, y) -> (y, -x)
        self.shape = [(-dy, dx) for dx, dy in self.shape]

    def get_shape(self):
        """Возвращает форму фигуры (относительные координаты)"""
        return self.shape

    def get_color(self):
        """Возвращает цвет фигуры"""
        return self.color

    def get_type(self):
        """Возвращает тип фигуры"""
        return self.piece_type

    def get_x(self):
        """Возвращает x координату"""
        return self.x

    def get_y(self):
        """Возвращает y координату"""
        return self.y
