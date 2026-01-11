"""Класс для яблок"""
import arcade
from constants import GRID_WIDTH, GRID_HEIGHT, MARGIN, CELL_SIZE


class Apple:
    """Класс для яблока с текстурой"""

    def __init__(self, x, y):
        """
        Создает яблоко
        x, y: позиция яблока в сетке
        """
        self.x = x
        self.y = y
        # Загружаем текстуру яблока из встроенных ресурсов arcade
        self.texture = None
        texture_paths = [
            ":resources:images/items/fruit/apple.png",
            ":resources:images/items/apple.png",
        ]

        for path in texture_paths:
            try:
                self.texture = arcade.load_texture(path)
                break
            except:
                continue

    def get_position(self):
        """Возвращает позицию яблока"""
        return (self.x, self.y)

    def draw(self):
        """Отрисовка яблока"""
        left = MARGIN + self.x * CELL_SIZE + 2
        right = MARGIN + (self.x + 1) * CELL_SIZE - 2
        bottom = MARGIN + self.y * CELL_SIZE + 2
        top = MARGIN + (self.y + 1) * CELL_SIZE - 2

        if top > bottom:
            if self.texture:
                # Рисуем текстуру
                arcade.draw_texture_rectangle(
                    (left + right) / 2,
                    (bottom + top) / 2,
                    right - left,
                    top - bottom,
                    self.texture
                )
            else:
                # Fallback: рисуем красное яблоко (как раньше)
                apple_color = (255, 50, 50)
                arcade.draw_lrbt_rectangle_filled(
                    left, right, bottom, top, apple_color)
                arcade.draw_lrbt_rectangle_outline(
                    left, right, bottom, top, (255, 150, 150), 2)
