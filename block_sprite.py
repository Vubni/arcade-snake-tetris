"""Спрайты для блоков"""
import arcade
from constants import MARGIN, CELL_SIZE


class BlockSprite(arcade.Sprite):
    """Спрайт для блока тетриса"""

    def __init__(self, x, y, color):
        """
        Создает спрайт блока
        x, y: позиция в сетке
        color: цвет блока (RGB кортеж)
        """
        super().__init__()
        self.width = CELL_SIZE - 2
        self.height = CELL_SIZE - 2

        # Создаем текстуру с цветом
        self.texture = arcade.make_soft_square_texture(
            CELL_SIZE - 2, color, outer_alpha=255
        )

        # Устанавливаем позицию в пикселях
        self.center_x = MARGIN + x * CELL_SIZE + CELL_SIZE // 2
        self.center_y = MARGIN + y * CELL_SIZE + CELL_SIZE // 2

        # Сохраняем позицию в сетке
        self.grid_x = x
        self.grid_y = y

        # Анимация появления (используем отдельную переменную, т.к. scale может быть кортежем)
        self.animation_scale = 0.0
        self.target_scale = 1.0
        self.animation_speed = 5.0
        self.scale = 0.0  # Начальный масштаб спрайта

    def update_animation(self, delta_time):
        """Обновление анимации появления"""
        if self.animation_scale < self.target_scale:
            self.animation_scale += self.animation_speed * delta_time
            if self.animation_scale > self.target_scale:
                self.animation_scale = self.target_scale
            # Применяем масштаб к спрайту
            self.scale = self.animation_scale
