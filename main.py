import arcade
import random
import copy

CELL_SIZE = 30
GRID_WIDTH = 20  # Ширина поля в клетках (большое поле)
GRID_HEIGHT = 30  # Высота поля в клетках (большое поле)
MARGIN = 50  # Отступы от краев окна

SCREEN_WIDTH = GRID_WIDTH * CELL_SIZE + MARGIN * 2
SCREEN_HEIGHT = GRID_HEIGHT * CELL_SIZE + MARGIN * 2

COLORS = [
    (0, 255, 255),      # Яркий циан для I
    (0, 100, 255),      # Яркий синий для J
    (255, 140, 0),      # Яркий оранжевый для L
    (255, 255, 0),      # Яркий желтый для O
    (50, 205, 50),      # Яркий зеленый для S
    (186, 85, 211),     # Яркий фиолетовый для T
    (255, 50, 50),      # Яркий красный для Z
]


def get_rgb(color):
    """Преобразует цвет arcade в RGB кортеж"""
    if isinstance(color, tuple):
        return color[:3] if len(color) >= 3 else (255, 255, 255)
    try:
        return (color[0], color[1], color[2]) if hasattr(color, '__getitem__') else (255, 255, 255)
    except:
        return (255, 255, 255)


TETROMINOES = {
    'I': [(-1, 0), (0, 0), (1, 0), (2, 0)],
    'J': [(-1, -1), (-1, 0), (0, 0), (1, 0)],
    'L': [(1, -1), (-1, 0), (0, 0), (1, 0)],
    'O': [(0, 0), (1, 0), (0, 1), (1, 1)],
    'S': [(-1, 0), (0, 0), (0, 1), (1, 1)],
    'T': [(0, -1), (-1, 0), (0, 0), (1, 0)],
    'Z': [(-1, 1), (0, 1), (0, 0), (1, 0)],
}


class TetrisGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, "Тетрис")
        arcade.set_background_color((20, 25, 40))

        self.grid = [[None for _ in range(GRID_WIDTH)]
                     for _ in range(GRID_HEIGHT)]

        self.current_piece = None
        self.current_piece_type = None
        self.current_piece_color = None
        self.current_piece_x = 0
        self.current_piece_y = 0

        self.fall_timer = 0.0
        self.fall_speed = 0.5  # секунд до следующего падения

        self.score = 0

        self.spawn_new_piece()

    def spawn_new_piece(self):
        """Создает новую случайную фигуру вверху поля"""
        piece_type = random.choice(list(TETROMINOES.keys()))
        self.current_piece_type = piece_type
        self.current_piece = copy.deepcopy(TETROMINOES[piece_type])
        self.current_piece_color = random.choice(COLORS)

        self.current_piece_x = GRID_WIDTH // 2
        self.current_piece_y = GRID_HEIGHT - 1

    def get_absolute_positions(self):
        """Возвращает абсолютные позиции текущей фигуры на поле"""
        positions = []
        for dx, dy in self.current_piece:
            x = self.current_piece_x + dx
            y = self.current_piece_y + dy
            positions.append((x, y))
        return positions

    def is_valid_position(self, x_offset=0, y_offset=0):
        """Проверяет, может ли фигура находиться в текущей позиции"""
        for dx, dy in self.current_piece:
            x = self.current_piece_x + dx + x_offset
            y = self.current_piece_y + dy + y_offset

            if x < 0 or x >= GRID_WIDTH or y < 0:
                return False

            if y < GRID_HEIGHT and self.grid[y][x] is not None:
                return False

        return True

    def lock_piece(self):
        """Фиксирует текущую фигуру на поле"""
        for dx, dy in self.current_piece:
            x = self.current_piece_x + dx
            y = self.current_piece_y + dy

            if 0 <= y < GRID_HEIGHT and 0 <= x < GRID_WIDTH:
                self.grid[y][x] = self.current_piece_color

        self.clear_lines()

        self.spawn_new_piece()

        if not self.is_valid_position():
            print("Игра окончена! Счет:", self.score)

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

        if lines_cleared > 0:
            self.score += lines_cleared * 100 * lines_cleared

    def rotate_piece(self):
        """Поворачивает фигуру на 90 градусов по часовой стрелке"""
        if self.current_piece_type == 'O':
            return

        rotated = [(-dy, dx) for dx, dy in self.current_piece]
        old_piece = self.current_piece
        self.current_piece = rotated

        if not self.is_valid_position():
            self.current_piece = old_piece

    def move_piece(self, dx, dy):
        """Перемещает фигуру"""
        if self.is_valid_position(dx, dy):
            self.current_piece_x += dx
            self.current_piece_y += dy
            return True
        return False

    def update(self, delta_time):
        """Обновление игры"""
        self.fall_timer += delta_time

        if self.fall_timer >= self.fall_speed:
            self.fall_timer = 0.0

            if not self.move_piece(0, -1):
                self.lock_piece()

    def on_key_press(self, key, modifiers):
        """Обработка нажатий клавиш"""
        if key == arcade.key.LEFT:
            self.move_piece(-1, 0)
        elif key == arcade.key.RIGHT:
            self.move_piece(1, 0)
        elif key == arcade.key.DOWN:
            if not self.move_piece(0, -1):
                self.lock_piece()
        elif key == arcade.key.UP:
            self.rotate_piece()
        elif key == arcade.key.SPACE:
            while self.move_piece(0, -1):
                pass
            self.lock_piece()

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
            arcade.draw_line(start_x, start_y, end_x,
                             end_y, grid_color, 1)

        for y in range(GRID_HEIGHT + 1):
            start_x = MARGIN
            start_y = MARGIN + y * CELL_SIZE
            end_x = MARGIN + GRID_WIDTH * CELL_SIZE
            end_y = start_y
            arcade.draw_line(start_x, start_y, end_x,
                             end_y, grid_color, 1)

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
            for dx, dy in self.current_piece:
                x = self.current_piece_x + dx
                y = self.current_piece_y + dy

                if 0 <= y < GRID_HEIGHT:
                    left = MARGIN + x * CELL_SIZE + 1
                    right = MARGIN + (x + 1) * CELL_SIZE - 1
                    bottom = MARGIN + y * CELL_SIZE + 1
                    top = MARGIN + (y + 1) * CELL_SIZE - 1
                    if top > bottom:
                        arcade.draw_lrbt_rectangle_filled(
                            left, right, bottom, top, self.current_piece_color
                        )
                        rgb = get_rgb(self.current_piece_color)
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

    def on_draw(self):
        """Отрисовка игры"""
        self.clear()

        self.draw_grid()
        self.draw_blocks()

        score_text = f"Счет: {self.score}"
        arcade.draw_text(score_text, 10, SCREEN_HEIGHT -
                         30, arcade.color.WHITE, 16)

        instructions = [
            "← → : Движение",
            "↑ : Поворот",
            "↓ : Ускорить",
            "Пробел : Уронить"
        ]
        y_offset = SCREEN_HEIGHT - 60
        for instruction in instructions:
            arcade.draw_text(instruction, SCREEN_WIDTH - 200, y_offset,
                             arcade.color.WHITE, 12)
            y_offset -= 20


def main():
    """Главная функция"""
    game = TetrisGame()
    arcade.run()


if __name__ == "__main__":
    main()
