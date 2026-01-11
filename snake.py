"""Класс змейки с улучшенной графикой"""
import arcade
from constants import GRID_WIDTH, GRID_HEIGHT, MARGIN, CELL_SIZE


def get_rgb(color):
    """Преобразует цвет arcade в RGB кортеж"""
    if isinstance(color, tuple):
        return color[:3] if len(color) >= 3 else (255, 255, 255)
    try:
        return (color[0], color[1], color[2]) if hasattr(color, '__getitem__') else (255, 255, 255)
    except:
        return (255, 255, 255)


class Snake:
    """Класс для управления змейкой с красивой графикой"""

    def __init__(self, x, y):
        """
        Создает змейку
        x, y: начальная позиция головы змейки
        """
        # Тело змейки: список кортежей (x, y), первый элемент - голова
        self.body = [(x, y), (x - 1, y), (x - 2, y)]
        # Направление движения: 0=вверх, 1=вправо, 2=вниз, 3=влево
        self.direction = 1  # Изначально движется вправо
        # Следующее направление (меняется при нажатии клавиш)
        self.next_direction = 1
        # Градиентные цвета для змейки (от головы к хвосту)
        self.head_color = (100, 255, 100)  # Яркий зеленый для головы
        self.body_color = (50, 200, 50)    # Средний зеленый для тела
        self.tail_color = (20, 150, 20)    # Темный зеленый для хвоста

    def change_direction(self, new_direction):
        """
        Изменяет направление движения змейки
        new_direction: 0=вверх, 1=вправо, 2=вниз, 3=влево
        """
        # Нельзя повернуть в противоположную сторону
        if (self.direction + 2) % 4 != new_direction:
            self.next_direction = new_direction

    def move(self):
        """Перемещает змейку в текущем направлении"""
        self.direction = self.next_direction

        # Получаем текущую позицию головы
        head_x, head_y = self.body[0]

        # Вычисляем новую позицию головы в зависимости от направления
        if self.direction == 0:  # Вверх
            new_head = (head_x, head_y + 1)
        elif self.direction == 1:  # Вправо
            new_head = (head_x + 1, head_y)
        elif self.direction == 2:  # Вниз
            new_head = (head_x, head_y - 1)
        else:  # Влево
            new_head = (head_x - 1, head_y)

        # Добавляем новую голову
        self.body.insert(0, new_head)
        # Удаляем хвост
        self.body.pop()

    def get_body(self):
        """Возвращает список позиций тела змейки"""
        return self.body

    def get_head(self):
        """Возвращает позицию головы змейки"""
        return self.body[0]

    def is_valid_position(self, grid_width, grid_height):
        """Проверяет, находится ли змейка в пределах поля"""
        head_x, head_y = self.get_head()

        # Проверка границ
        if head_x < 0 or head_x >= grid_width or head_y < 0 or head_y >= grid_height:
            return False

        # Проверка столкновения с собой (проверяем, не находится ли голова на теле)
        if self.get_head() in self.body[1:]:
            return False

        return True

    def check_collision_with_position(self, x, y):
        """Проверяет, находится ли змейка в указанной позиции"""
        return (x, y) in self.body

    def draw(self):
        """Отрисовка змейки с градиентом и эффектами"""
        body_len = len(self.body)
        
        for idx, (x, y) in enumerate(self.body):
            if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
                left = MARGIN + x * CELL_SIZE + 2
                right = MARGIN + (x + 1) * CELL_SIZE - 2
                bottom = MARGIN + y * CELL_SIZE + 2
                top = MARGIN + (y + 1) * CELL_SIZE - 2
                
                if top > bottom:
                    # Градиент цвета от головы к хвосту
                    if idx == 0:  # Голова
                        color = self.head_color
                    elif idx == body_len - 1:  # Хвост
                        color = self.tail_color
                    else:  # Тело - интерполяция
                        t = idx / max(1, body_len - 1)
                        color = tuple(
                            int(self.head_color[i] * (1 - t) + self.tail_color[i] * t)
                            for i in range(3)
                        )
                    
                    # Рисуем основной блок
                    arcade.draw_lrbt_rectangle_filled(
                        left, right, bottom, top, color
                    )
                    
                    # Светлая обводка сверху и слева
                    rgb = get_rgb(color)
                    light_border = tuple(min(255, c + 60) for c in rgb)
                    arcade.draw_line(left, top, right, top, light_border, 2)
                    arcade.draw_line(left, bottom, left, top, light_border, 2)
                    
                    # Темная обводка снизу и справа (тень)
                    dark_border = tuple(max(0, c - 60) for c in rgb)
                    arcade.draw_line(left, bottom, right, bottom, dark_border, 2)
                    arcade.draw_line(right, bottom, right, top, dark_border, 2)
                    
                    # Глаза на голове
                    if idx == 0:
                        eye_size = 3
                        eye_offset = 5
                        if self.direction == 1:  # Вправо
                            eye1_x = right - eye_offset
                            eye2_x = right - eye_offset
                            eye_y1 = top - 8
                            eye_y2 = bottom + 8
                        elif self.direction == 3:  # Влево
                            eye1_x = left + eye_offset
                            eye2_x = left + eye_offset
                            eye_y1 = top - 8
                            eye_y2 = bottom + 8
                        elif self.direction == 0:  # Вверх
                            eye1_x = left + 8
                            eye2_x = right - 8
                            eye_y1 = top - eye_offset
                            eye_y2 = top - eye_offset
                        else:  # Вниз
                            eye1_x = left + 8
                            eye2_x = right - 8
                            eye_y1 = bottom + eye_offset
                            eye_y2 = bottom + eye_offset
                        
                        arcade.draw_circle_filled(eye1_x, eye_y1, eye_size, arcade.color.BLACK)
                        arcade.draw_circle_filled(eye2_x, eye_y2, eye_size, arcade.color.BLACK)
