"""Класс для яблок"""
import arcade
from constants import GRID_WIDTH, GRID_HEIGHT, MARGIN, CELL_SIZE


class Apple(arcade.Sprite):
    """Класс для яблока с использованием спрайта"""

    def __init__(self, x, y):
        """
        Создает яблоко
        x, y: позиция яблока в сетке
        """
        # Загружаем текстуру яблока (сначала из локального файла, потом из встроенных ресурсов)
        texture_paths = [
            "sprites/apple.png",  # Локальный файл в папке проекта
            ":resources:images/items/fruit/apple.png",
            ":resources:images/items/apple.png",
        ]

        texture = None
        for path in texture_paths:
            try:
                texture = arcade.load_texture(path)
                break
            except:
                continue

        # Если текстура не загрузилась, создаем цветной спрайт
        if not texture:
            texture = arcade.make_soft_square_texture(
                CELL_SIZE, (255, 50, 50), outer_alpha=255
            )

        # Создаем спрайт с загруженной текстурой
        super().__init__()
        self.texture = texture

        # Вычисляем и устанавливаем масштаб, чтобы спрайт заполнял всю клетку
        if texture and hasattr(texture, 'width') and hasattr(texture, 'height') and texture.width > 0 and texture.height > 0:
            # Вычисляем масштаб для заполнения всей клетки
            # Используем масштаб, чтобы большая сторона спрайта равнялась CELL_SIZE
            scale_x = CELL_SIZE / texture.width
            scale_y = CELL_SIZE / texture.height
            # Используем максимальный масштаб для заполнения всей клетки
            self.scale = max(scale_x, scale_y)
        else:
            # Если текстуры нет или нет размеров, устанавливаем размер напрямую
            self.width = CELL_SIZE
            self.height = CELL_SIZE

        # Устанавливаем позицию в пикселях
        self.center_x = MARGIN + x * CELL_SIZE + CELL_SIZE // 2
        self.center_y = MARGIN + y * CELL_SIZE + CELL_SIZE // 2

        # Сохраняем позицию в сетке
        self.grid_x = x
        self.grid_y = y

        # Анимация вращения
        self.rotation_speed = 0.0
        self.angle = 0.0

    def get_position(self):
        """Возвращает позицию яблока в сетке"""
        return (self.grid_x, self.grid_y)

    def update_animation(self, delta_time):
        """Обновление анимации вращения"""
        self.angle += self.rotation_speed * delta_time
        if self.rotation_speed > 0:
            self.rotation_speed -= 50 * delta_time  # Замедление
            if self.rotation_speed < 0:
                self.rotation_speed = 0

    def start_rotation(self):
        """Запускает анимацию вращения"""
        self.rotation_speed = 180.0  # Градусов в секунду
