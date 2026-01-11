import arcade
import random
import copy

# Константы игры
CELL_SIZE = 30  # Размер одной клетки в пикселях
GRID_WIDTH = 20  # Ширина поля в клетках (большое поле)
GRID_HEIGHT = 30  # Высота поля в клетках (большое поле)
MARGIN = 50  # Отступы от краев окна

SCREEN_WIDTH = GRID_WIDTH * CELL_SIZE + MARGIN * 2
SCREEN_HEIGHT = GRID_HEIGHT * CELL_SIZE + MARGIN * 2

# Цвета для фигур
COLORS = [
    arcade.color.CYAN,      # I
    arcade.color.BLUE,      # J
    arcade.color.ORANGE,    # L
    arcade.color.YELLOW,    # O
    arcade.color.GREEN,     # S
    arcade.color.PURPLE,    # T
    arcade.color.RED,       # Z
]

# Формы тетромино (относительно центра)
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
        arcade.set_background_color(arcade.color.BLACK)

        # Игровое поле (None = пусто, число = цвет)
        self.grid = [[None for _ in range(GRID_WIDTH)]
                     for _ in range(GRID_HEIGHT)]

        # Текущая падающая фигура
        self.current_piece = None
        self.current_piece_type = None
        self.current_piece_color = None
        self.current_piece_x = 0
        self.current_piece_y = 0

        # Таймер для падения
        self.fall_timer = 0.0
        self.fall_speed = 0.5  # секунд до следующего падения

        # Счетчик очков
        self.score = 0

        # Создаем первую фигуру
        self.spawn_new_piece()

    def spawn_new_piece(self):
        """Создает новую случайную фигуру вверху поля"""
        piece_type = random.choice(list(TETROMINOES.keys()))
        self.current_piece_type = piece_type
        self.current_piece = copy.deepcopy(TETROMINOES[piece_type])
        self.current_piece_color = random.choice(COLORS)

        # Размещаем фигуру в центре верхней части поля
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

            # Проверка границ
            if x < 0 or x >= GRID_WIDTH or y < 0:
                return False

            # Проверка столкновения с уже установленными блоками
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

        # Проверяем заполненные линии
        self.clear_lines()

        # Создаем новую фигуру
        self.spawn_new_piece()

        # Проверяем, не закончилась ли игра
        if not self.is_valid_position():
            print("Игра окончена! Счет:", self.score)

    def clear_lines(self):
        """Удаляет заполненные линии"""
        lines_cleared = 0
        y = GRID_HEIGHT - 1

        while y >= 0:
            if all(self.grid[y][x] is not None for x in range(GRID_WIDTH)):
                # Удаляем линию
                del self.grid[y]
                # Добавляем пустую линию сверху
                self.grid.append([None for _ in range(GRID_WIDTH)])
                lines_cleared += 1
            else:
                y -= 1

        # Начисляем очки
        if lines_cleared > 0:
            self.score += lines_cleared * 100 * lines_cleared  # Бонус за несколько линий

    def rotate_piece(self):
        """Поворачивает фигуру на 90 градусов по часовой стрелке"""
        if self.current_piece_type == 'O':  # Квадрат не нужно поворачивать
            return

        # Поворот: (x, y) -> (y, -x)
        rotated = [(-dy, dx) for dx, dy in self.current_piece]
        old_piece = self.current_piece
        self.current_piece = rotated

        # Проверяем, можно ли повернуть
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

            # Пытаемся опустить фигуру
            if not self.move_piece(0, -1):
                # Если не получилось, фиксируем фигуру
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
            # Мгновенное падение
            while self.move_piece(0, -1):
                pass
            self.lock_piece()

    def draw_grid(self):
        """Отрисовка сетки поля"""
        # Вертикальные линии
        for x in range(GRID_WIDTH + 1):
            start_x = MARGIN + x * CELL_SIZE
            start_y = MARGIN
            end_x = start_x
            end_y = MARGIN + GRID_HEIGHT * CELL_SIZE
            arcade.draw_line(start_x, start_y, end_x,
                             end_y, arcade.color.GRAY, 1)

        # Горизонтальные линии
        for y in range(GRID_HEIGHT + 1):
            start_x = MARGIN
            start_y = MARGIN + y * CELL_SIZE
            end_x = MARGIN + GRID_WIDTH * CELL_SIZE
            end_y = start_y
            arcade.draw_line(start_x, start_y, end_x,
                             end_y, arcade.color.GRAY, 1)

    def draw_blocks(self):
        """Отрисовка всех блоков на поле"""
        # Установленные блоки
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.grid[y][x] is not None:
                    left = MARGIN + x * CELL_SIZE + 1
                    right = MARGIN + (x + 1) * CELL_SIZE - 1
                    # В arcade координаты идут снизу вверх
                    # y=0 - нижняя строка, y=GRID_HEIGHT-1 - верхняя строка
                    bottom = MARGIN + y * CELL_SIZE + 1
                    top = MARGIN + (y + 1) * CELL_SIZE - 1
                    # Убеждаемся, что top > bottom
                    if top > bottom:
                        arcade.draw_lrbt_rectangle_filled(
                            left, right, bottom, top, self.grid[y][x]
                        )

        # Текущая падающая фигура
        if self.current_piece:
            for dx, dy in self.current_piece:
                x = self.current_piece_x + dx
                y = self.current_piece_y + dy

                if 0 <= y < GRID_HEIGHT:
                    left = MARGIN + x * CELL_SIZE + 1
                    right = MARGIN + (x + 1) * CELL_SIZE - 1
                    bottom = MARGIN + y * CELL_SIZE + 1
                    top = MARGIN + (y + 1) * CELL_SIZE - 1
                    # Убеждаемся, что top > bottom
                    if top > bottom:
                        arcade.draw_lrbt_rectangle_filled(
                            left, right, bottom, top, self.current_piece_color
                        )

    def on_draw(self):
        """Отрисовка игры"""
        self.clear()

        self.draw_grid()
        self.draw_blocks()

        # Отображение счета
        score_text = f"Счет: {self.score}"
        arcade.draw_text(score_text, 10, SCREEN_HEIGHT -
                         30, arcade.color.WHITE, 16)

        # Инструкции
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
