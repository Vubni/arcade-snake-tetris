"""Основной класс игры"""
import arcade
import random
from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GRID_WIDTH, GRID_HEIGHT,
    MARGIN, CELL_SIZE, FALL_SPEED, SNAKE_SPEED, COLORS, TETROMINOES
)
from snake import Snake
from tetromino import Tetromino


def get_rgb(color):
    """Преобразует цвет arcade в RGB кортеж"""
    if isinstance(color, tuple):
        return color[:3] if len(color) >= 3 else (255, 255, 255)
    try:
        return (color[0], color[1], color[2]) if hasattr(color, '__getitem__') else (255, 255, 255)
    except:
        return (255, 255, 255)


class GameView(arcade.View):
    """Класс игрового экрана"""

    def __init__(self):
        super().__init__()
        arcade.set_background_color((20, 25, 40))

        self.grid = [[None for _ in range(GRID_WIDTH)]
                     for _ in range(GRID_HEIGHT)]

        self.current_piece = None
        self.fall_timer = 0.0
        self.score = 0

        # Инициализация змейки в случайной позиции
        snake_x = random.randint(5, GRID_WIDTH - 5)
        snake_y = random.randint(5, GRID_HEIGHT - 5)
        self.snake = Snake(snake_x, snake_y)
        self.snake_timer = 0.0

        self.spawn_new_piece()

    def spawn_new_piece(self):
        """Создает новую случайную фигуру вверху поля"""
        piece_type = random.choice(list(TETROMINOES.keys()))
        color = random.choice(COLORS)
        # Случайная позиция по x (с запасом для фигуры)
        x = random.randint(2, max(2, GRID_WIDTH - 3))
        y = GRID_HEIGHT - 1

        self.current_piece = Tetromino(piece_type, color, x, y)

    def is_valid_position(self, piece, x_offset=0, y_offset=0):
        """Проверяет, может ли фигура находиться в указанной позиции"""
        for dx, dy in piece.get_shape():
            x = piece.get_x() + dx + x_offset
            y = piece.get_y() + dy + y_offset

            if x < 0 or x >= GRID_WIDTH or y < 0:
                return False

            if y < GRID_HEIGHT and self.grid[y][x] is not None:
                return False

        return True

    def lock_piece(self):
        """Фиксирует текущую фигуру на поле"""
        for dx, dy in self.current_piece.get_shape():
            x = self.current_piece.get_x() + dx
            y = self.current_piece.get_y() + dy

            if 0 <= y < GRID_HEIGHT and 0 <= x < GRID_WIDTH:
                self.grid[y][x] = self.current_piece.get_color()

        self.clear_lines()

        self.spawn_new_piece()

        if not self.is_valid_position(self.current_piece):
            # Игра окончена - поле переполнено
            self.game_over()

    def clear_lines(self):
        """Удаляет заполненные линии"""
        lines_cleared = 0
        y = GRID_HEIGHT - 1

        while y >= 0:
            if all(self.grid[y][x] is not None for x in range(GRID_WIDTH)):
                del self.grid[y]
                self.grid.append([None for _ in range(GRID_WIDTH)])
                lines_cleared += 1
            else:
                y -= 1

    def move_piece(self, dx, dy):
        """Перемещает фигуру"""
        if self.is_valid_position(self.current_piece, dx, dy):
            self.current_piece.move(dx, dy)
            return True
        return False

    def check_snake_collision(self):
        """Проверяет столкновение змейки со стеной или фигурами"""
        head_x, head_y = self.snake.get_head()

        # Проверка столкновения со стеной
        if head_x < 0 or head_x >= GRID_WIDTH or head_y < 0 or head_y >= GRID_HEIGHT:
            return True

        # Проверка столкновения с зафиксированными блоками
        if 0 <= head_y < GRID_HEIGHT and 0 <= head_x < GRID_WIDTH:
            if self.grid[head_y][head_x] is not None:
                return True

        # Проверка столкновения с падающей фигурой
        if self.current_piece:
            piece_positions = self.current_piece.get_positions()
            if (head_x, head_y) in piece_positions:
                return True

        return False

    def game_over(self):
        """Завершает игру и показывает экран проигрыша"""
        from menu import GameOverView
        game_over_view = GameOverView(self.score)
        self.window.show_view(game_over_view)

    def on_update(self, delta_time):
        """Обновление игры"""
        # Обновление падающих фигур
        self.fall_timer += delta_time
        if self.fall_timer >= FALL_SPEED:
            self.fall_timer = 0.0
            if not self.move_piece(0, -1):
                # Если не можем двигаться вниз, фиксируем фигуру
                self.lock_piece()

        # Обновление змейки
        self.snake_timer += delta_time
        if self.snake_timer >= SNAKE_SPEED:
            self.snake_timer = 0.0
            self.snake.move()

            # Проверяем столкновения
            if self.check_snake_collision():
                self.game_over()
                return

    def draw_grid(self):
        """Отрисовка сетки поля"""
        field_color = (30, 35, 50)
        arcade.draw_lrbt_rectangle_filled(
            MARGIN, MARGIN + GRID_WIDTH * CELL_SIZE,
            MARGIN, MARGIN + GRID_HEIGHT * CELL_SIZE,
            field_color
        )

        grid_color = (60, 70, 90)
        for x in range(GRID_WIDTH + 1):
            start_x = MARGIN + x * CELL_SIZE
            start_y = MARGIN
            end_x = start_x
            end_y = MARGIN + GRID_HEIGHT * CELL_SIZE
            arcade.draw_line(start_x, start_y, end_x, end_y, grid_color, 1)

        for y in range(GRID_HEIGHT + 1):
            start_x = MARGIN
            start_y = MARGIN + y * CELL_SIZE
            end_x = MARGIN + GRID_WIDTH * CELL_SIZE
            end_y = start_y
            arcade.draw_line(start_x, start_y, end_x, end_y, grid_color, 1)

    def draw_blocks(self):
        """Отрисовка всех блоков на поле"""
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.grid[y][x] is not None:
                    left = MARGIN + x * CELL_SIZE + 1
                    right = MARGIN + (x + 1) * CELL_SIZE - 1
                    bottom = MARGIN + y * CELL_SIZE + 1
                    top = MARGIN + (y + 1) * CELL_SIZE - 1
                    if top > bottom:
                        arcade.draw_lrbt_rectangle_filled(
                            left, right, bottom, top, self.grid[y][x]
                        )
                        rgb = get_rgb(self.grid[y][x])
                        border_color = tuple(min(255, c + 50) for c in rgb)
                        arcade.draw_line(left, top, right,
                                         top, border_color, 2)
                        arcade.draw_line(left, bottom, left,
                                         top, border_color, 2)
                        shadow_color = tuple(max(0, c - 50) for c in rgb)
                        arcade.draw_line(left, bottom, right,
                                         bottom, shadow_color, 2)
                        arcade.draw_line(right, bottom, right,
                                         top, shadow_color, 2)

        if self.current_piece:
            for dx, dy in self.current_piece.get_shape():
                x = self.current_piece.get_x() + dx
                y = self.current_piece.get_y() + dy

                if 0 <= y < GRID_HEIGHT:
                    left = MARGIN + x * CELL_SIZE + 1
                    right = MARGIN + (x + 1) * CELL_SIZE - 1
                    bottom = MARGIN + y * CELL_SIZE + 1
                    top = MARGIN + (y + 1) * CELL_SIZE - 1
                    if top > bottom:
                        piece_color = self.current_piece.get_color()
                        arcade.draw_lrbt_rectangle_filled(
                            left, right, bottom, top, piece_color
                        )
                        rgb = get_rgb(piece_color)
                        border_color = tuple(min(255, c + 70) for c in rgb)
                        shadow_color = tuple(max(0, c - 50) for c in rgb)
                        arcade.draw_line(left, top, right,
                                         top, border_color, 2)
                        arcade.draw_line(left, bottom, left,
                                         top, border_color, 2)
                        arcade.draw_line(left, bottom, right,
                                         bottom, shadow_color, 2)
                        arcade.draw_line(right, bottom, right,
                                         top, shadow_color, 2)

    def on_key_press(self, key, modifiers):
        """Обработка нажатий клавиш для управления змейкой"""
        if key == arcade.key.UP:
            self.snake.change_direction(0)  # Вверх
        elif key == arcade.key.RIGHT:
            self.snake.change_direction(1)  # Вправо
        elif key == arcade.key.DOWN:
            self.snake.change_direction(2)  # Вниз
        elif key == arcade.key.LEFT:
            self.snake.change_direction(3)  # Влево

    def on_draw(self):
        """Отрисовка игры"""
        self.clear()

        self.draw_grid()
        self.draw_blocks()
        self.snake.draw()

        score_text = f"Счет: {self.score}"
        arcade.draw_text(score_text, 10, SCREEN_HEIGHT -
                         30, arcade.color.WHITE, 16)
