"""Основной класс игры"""
import arcade
import random
import json
import os
from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GRID_WIDTH, GRID_HEIGHT,
    MARGIN, CELL_SIZE, COLORS, TETROMINOES, DIFFICULTY_SETTINGS
)
from snake import Snake
from tetromino import Tetromino
from apple import Apple

HIGH_SCORE_FILE = "high_score.json"


def get_rgb(color):
    """Преобразует цвет arcade в RGB кортеж"""
    if isinstance(color, tuple):
        return color[:3] if len(color) >= 3 else (255, 255, 255)
    try:
        return (color[0], color[1], color[2]) if hasattr(color, '__getitem__') else (255, 255, 255)
    except:
        return (255, 255, 255)


def load_high_score():
    """Загружает рекорд из файла"""
    if os.path.exists(HIGH_SCORE_FILE):
        try:
            with open(HIGH_SCORE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('high_score', 0)
        except:
            return 0
    return 0


def save_high_score(score):
    """Сохраняет рекорд в файл"""
    try:
        with open(HIGH_SCORE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'high_score': score}, f, ensure_ascii=False)
    except:
        pass


class GameView(arcade.View):
    """Класс игрового экрана"""

    def __init__(self, difficulty='medium'):
        super().__init__()
        arcade.set_background_color((20, 25, 40))

        # Настройки сложности
        self.difficulty = difficulty
        difficulty_config = DIFFICULTY_SETTINGS.get(
            difficulty, DIFFICULTY_SETTINGS['medium'])
        self.fall_speed = difficulty_config['fall_speed']
        self.snake_speed = difficulty_config['snake_speed']

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

        # Яблоко
        self.apple = None
        self.spawn_apple()

        self.spawn_new_piece()

        # Сообщения об изменении очков (текст, x, y, время жизни, цвет)
        self.score_messages = []

        # Счетчик фигур для постепенного ускорения
        self.pieces_count = 0
        self.base_fall_speed = self.fall_speed  # Сохраняем базовую скорость

    def find_best_target_row(self):
        """Находит лучший ряд для заполнения (самый заполненный, но не полностью)"""
        best_row = -1
        max_filled = 0

        # Анализируем нижние 15 рядов (игровую зону)
        for y in range(max(0, GRID_HEIGHT - 15), GRID_HEIGHT):
            filled_count = sum(1 for x in range(GRID_WIDTH)
                               if self.grid[y][x] is not None)
            # Ищем ряд с максимальным заполнением, но не полностью заполненный
            if filled_count > max_filled and filled_count < GRID_WIDTH:
                max_filled = filled_count
                best_row = y

        return best_row, max_filled

    def find_best_position_for_piece(self, piece, target_row):
        """Находит лучшую позицию X для фигуры, чтобы заполнить пробелы в целевом ряду"""
        if target_row < 0:
            return piece.get_x()

        # Находим пробелы в целевом ряду
        gaps = []
        for x in range(GRID_WIDTH):
            if self.grid[target_row][x] is None:
                gaps.append(x)

        if not gaps:
            return piece.get_x()

        # Находим самый большой последовательный пробел
        gap_start = gaps[0]
        gap_end = gaps[0]
        best_gap_start = gaps[0]
        best_gap_length = 1

        for i in range(1, len(gaps)):
            if gaps[i] == gaps[i-1] + 1:
                gap_end = gaps[i]
            else:
                if gap_end - gap_start + 1 > best_gap_length:
                    best_gap_length = gap_end - gap_start + 1
                    best_gap_start = gap_start
                gap_start = gaps[i]
                gap_end = gaps[i]

        if gap_end - gap_start + 1 > best_gap_length:
            best_gap_length = gap_end - gap_start + 1
            best_gap_start = gap_start

        # Вычисляем реальные X координаты фигуры
        shape = piece.get_shape()
        current_x = piece.get_x()
        piece_x_positions = [current_x + dx for dx, dy in shape]
        min_piece_x = min(piece_x_positions)
        max_piece_x = max(piece_x_positions)
        piece_center_x = (min_piece_x + max_piece_x) / 2

        # Центр пробела
        gap_center = best_gap_start + best_gap_length / 2

        # Вычисляем смещение, необходимое для центрирования фигуры над пробелом
        offset = gap_center - piece_center_x
        desired_x = current_x + int(offset)

        # Ограничиваем границами поля
        desired_x = max(0, min(GRID_WIDTH - 1, desired_x))

        return desired_x

    def analyze_grid_for_spawn(self):
        """Анализирует поле и возвращает подходящую позицию X и тип фигуры"""
        best_row, max_filled = self.find_best_target_row()

        # Если нашли заполненный ряд, ищем пробелы
        if best_row >= 0 and max_filled > 0:
            gaps = []
            for x in range(GRID_WIDTH):
                if self.grid[best_row][x] is None:
                    gaps.append(x)

            if gaps:
                # Выбираем позицию X - центр самого большого пробела
                # Находим последовательные пробелы
                gap_start = gaps[0]
                gap_end = gaps[0]
                best_gap_start = gaps[0]
                best_gap_length = 1

                for i in range(1, len(gaps)):
                    if gaps[i] == gaps[i-1] + 1:
                        gap_end = gaps[i]
                    else:
                        if gap_end - gap_start + 1 > best_gap_length:
                            best_gap_length = gap_end - gap_start + 1
                            best_gap_start = gap_start
                        gap_start = gaps[i]
                        gap_end = gaps[i]

                if gap_end - gap_start + 1 > best_gap_length:
                    best_gap_length = gap_end - gap_start + 1
                    best_gap_start = gap_start

                # Выбираем центр пробела
                target_x = best_gap_start + best_gap_length // 2
                target_x = max(2, min(GRID_WIDTH - 3, target_x))

                # Выбираем фигуру по ширине пробела
                piece_types = list(TETROMINOES.keys())
                # Для широких пробелов (4+) предпочитаем широкие фигуры (I, O, T)
                if best_gap_length >= 4:
                    preferred_pieces = ['I', 'O', 'T', 'S', 'Z']
                elif best_gap_length >= 3:
                    preferred_pieces = ['L', 'J', 'T', 'S', 'Z']
                else:
                    preferred_pieces = ['O', 'T']

                # Выбираем из предпочтительных, если они есть, иначе любую
                available_preferred = [
                    p for p in preferred_pieces if p in piece_types]
                piece_type = random.choice(
                    available_preferred if available_preferred else piece_types)

                return target_x, piece_type

        # Если не нашли подходящий ряд, выбираем случайно (но ближе к заполненным рядам)
        # Находим среднюю X позицию заполненных блоков
        filled_x_positions = []
        for y in range(max(0, GRID_HEIGHT - 10), GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.grid[y][x] is not None:
                    filled_x_positions.append(x)

        if filled_x_positions:
            avg_x = sum(filled_x_positions) // len(filled_x_positions)
            target_x = max(2, min(GRID_WIDTH - 3, avg_x))
        else:
            target_x = random.randint(2, max(2, GRID_WIDTH - 3))

        piece_type = random.choice(list(TETROMINOES.keys()))
        return target_x, piece_type

    def spawn_new_piece(self):
        """Создает новую фигуру вверху поля с учетом анализа поля"""
        x, piece_type = self.analyze_grid_for_spawn()
        color = random.choice(COLORS)
        y = GRID_HEIGHT - 1

        self.current_piece = Tetromino(piece_type, color, x, y)

    def is_cell_free(self, x, y, ignore_apple=None):
        """Проверяет, свободна ли клетка (не занята блоками, фигурой, змейкой)"""
        # Проверяем границы
        if x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT:
            return False

        # Проверяем блоки
        if 0 <= y < GRID_HEIGHT and 0 <= x < GRID_WIDTH:
            if self.grid[y][x] is not None:
                return False

        # Проверяем падающую фигуру
        if self.current_piece:
            if (x, y) in self.current_piece.get_positions():
                return False

        # Проверяем змейку (игнорируем яблоко, если указано)
        if ignore_apple and (x, y) == ignore_apple:
            return True
        if self.snake.check_collision_with_position(x, y):
            return False

        return True

    def is_apple_accessible(self, apple_x, apple_y):
        """Проверяет доступность яблока для змейки с помощью BFS"""
        # Если яблоко внизу (y < 5), проверяем доступность более тщательно
        if apple_y >= 5:
            # Для яблок выше проверяем только базовую доступность
            return True

        # Используем BFS для поиска пути от головы змейки до яблока
        snake_head = self.snake.get_head()
        start = snake_head

        # Проверяем, можем ли добраться до яблока
        queue = [start]
        visited = {start}
        # Вверх, вправо, вниз, влево
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]

        found_apple = False
        while queue:
            current = queue.pop(0)

            if current == (apple_x, apple_y):
                found_apple = True
                break

            for dx, dy in directions:
                nx, ny = current[0] + dx, current[1] + dy
                neighbor = (nx, ny)

                # Проверяем, свободна ли клетка (игнорируем яблоко)
                if not self.is_cell_free(nx, ny, ignore_apple=(apple_x, apple_y)):
                    continue

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        if not found_apple:
            return False  # Не можем добраться до яблока

        # Теперь проверяем, можем ли выбраться от яблока
        # Используем BFS от яблока, чтобы найти путь к свободному пространству
        # Считаем, что яблоко доступно, если есть хотя бы 2 свободных соседних клетки
        free_neighbors = 0
        for dx, dy in directions:
            nx, ny = apple_x + dx, apple_y + dy
            if self.is_cell_free(nx, ny, ignore_apple=(apple_x, apple_y)):
                free_neighbors += 1

        # Если к яблоко ведет только 1 клетка или меньше, оно недоступно
        # (змейка не сможет выбраться после того, как съест яблоко)
        if free_neighbors < 2:
            return False

        # Дополнительная проверка: можем ли выбраться от яблока (BFS от яблока)
        # Проверяем, что от яблока можно добраться до области выше (y >= 3)
        escape_queue = [(apple_x, apple_y)]
        escape_visited = {(apple_x, apple_y)}
        can_escape = False

        while escape_queue:
            current = escape_queue.pop(0)
            cx, cy = current

            # Если достигли области выше, можем выбраться
            if cy >= 3:
                can_escape = True
                break

            for dx, dy in directions:
                nx, ny = cx + dx, cy + dy
                neighbor = (nx, ny)

                # Проверяем, свободна ли клетка
                if not self.is_cell_free(nx, ny, ignore_apple=(apple_x, apple_y)):
                    continue

                if neighbor not in escape_visited:
                    escape_visited.add(neighbor)
                    escape_queue.append(neighbor)

        return can_escape

    def spawn_apple(self):
        """Создает яблоко в случайной позиции (не на змейке, не на блоках, не на падающей фигуре, не в верхних 4 линиях, не под падающей фигурой)"""
        max_attempts = 200
        for _ in range(max_attempts):
            apple_x = random.randint(0, GRID_WIDTH - 1)
            # Не спавним в верхних 4 линиях (GRID_HEIGHT - 1, GRID_HEIGHT - 2, GRID_HEIGHT - 3, GRID_HEIGHT - 4)
            apple_y = random.randint(0, GRID_HEIGHT - 5)

            # Проверяем, что яблоко не на змейке
            if self.snake.check_collision_with_position(apple_x, apple_y):
                continue

            # Проверяем, что яблоко не на блоке
            if 0 <= apple_y < GRID_HEIGHT and 0 <= apple_x < GRID_WIDTH:
                if self.grid[apple_y][apple_x] is not None:
                    continue

            # Проверяем, что яблоко не на падающей фигуре и не под ней
            if self.current_piece:
                piece_positions = self.current_piece.get_positions()
                if (apple_x, apple_y) in piece_positions:
                    continue
                # Проверяем, не находится ли яблоко прямо под какой-то частью фигуры
                # (по той же x координате и ниже по y)
                is_under_piece = False
                for px, py in piece_positions:
                    if px == apple_x and apple_y < py:
                        is_under_piece = True
                        break
                if is_under_piece:
                    continue

            # Нашли свободное место
            self.apple = Apple(apple_x, apple_y)

            # Проверяем доступность яблока (особенно если оно внизу)
            if not self.is_apple_accessible(apple_x, apple_y):
                # Яблоко недоступно - уничтожаем без снятия очков и создаем новое
                self.apple = None
                continue

            return

        # Если не нашли место (очень маловероятно), ставим None
        self.apple = None

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
        # Проверяем, не раздавили ли яблоко падающей фигурой
        if self.apple:
            apple_pos = self.apple.get_position()
            piece_positions = self.current_piece.get_positions()
            if apple_pos in piece_positions:
                # Яблоко раздавлено
                # Отнимаем 50 очков (не меньше 0)
                apple_x, apple_y = apple_pos
                self.score = max(0, self.score - 50)
                self.add_score_message(-50, apple_x, apple_y)
                self.apple = None
                self.spawn_apple()

        for dx, dy in self.current_piece.get_shape():
            x = self.current_piece.get_x() + dx
            y = self.current_piece.get_y() + dy

            if 0 <= y < GRID_HEIGHT and 0 <= x < GRID_WIDTH:
                self.grid[y][x] = self.current_piece.get_color()

        self.clear_lines()

        # Увеличиваем счетчик фигур и постепенно ускоряем падение
        self.pieces_count += 1
        # Очень медленное ускорение: каждые 10 фигур уменьшаем fall_speed на 0.001
        # Минимальная скорость - 0.05 (максимальное ускорение)
        speed_reduction = (self.pieces_count // 10) * 0.001
        self.fall_speed = max(0.05, self.base_fall_speed - speed_reduction)

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

        # Начисляем очки за очищенные линии
        if lines_cleared > 0:
            score_gain = lines_cleared * 100
            self.score = max(0, self.score + score_gain)
            self.add_score_message(score_gain)

    def move_piece(self, dx, dy):
        """Перемещает фигуру"""
        if self.is_valid_position(self.current_piece, dx, dy):
            self.current_piece.move(dx, dy)

            # Проверяем, не раздавили ли яблоко после перемещения
            if self.apple and dy < 0:  # Проверяем только при движении вниз
                apple_pos = self.apple.get_position()
                piece_positions = self.current_piece.get_positions()
                if apple_pos in piece_positions:
                    # Яблоко раздавлено
                    apple_x, apple_y = apple_pos
                    self.score = max(0, self.score - 50)
                    self.add_score_message(-50, apple_x, apple_y)
                    self.apple = None
                    self.spawn_apple()

            return True
        return False

    def check_snake_collision(self):
        """Проверяет столкновение змейки со стеной, фигурами или с собой (проверяет все части змейки)"""
        snake_body = self.snake.get_body()

        # Проверка столкновения головы с телом (столкновение с собой)
        head = snake_body[0]
        if head in snake_body[1:]:
            return True

        # Проверяем каждую часть змейки
        for snake_x, snake_y in snake_body:
            # Проверка столкновения со стеной
            if snake_x < 0 or snake_x >= GRID_WIDTH or snake_y < 0 or snake_y >= GRID_HEIGHT:
                return True

            # Проверка столкновения с зафиксированными блоками
            if 0 <= snake_y < GRID_HEIGHT and 0 <= snake_x < GRID_WIDTH:
                if self.grid[snake_y][snake_x] is not None:
                    return True

        # Проверка столкновения с падающей фигурой (отдельно для головы и тела)
        if self.current_piece:
            piece_positions = self.current_piece.get_positions()
            head_pos = snake_body[0]

            # Если фигура касается головы - игра заканчивается
            if head_pos in piece_positions:
                return True

            # Если фигура касается тела - обрезаем тело
            for idx, (snake_x, snake_y) in enumerate(snake_body[1:], start=1):
                if (snake_x, snake_y) in piece_positions:
                    # Нашли касание тела - обрезаем начиная с этого индекса
                    removed_count = self.snake.cut_body_at_index(idx)
                    if removed_count > 0:
                        # Проверяем, что змейка не стала короче 3 клеточек
                        if len(self.snake.body) < 3:
                            # Игра заканчивается - змейка слишком короткая
                            return True
                        # Снимаем по 50 очков за каждый отрубленный кусок
                        score_loss = removed_count * 50
                        self.score = max(0, self.score - score_loss)
                        # Показываем изменение очков
                        self.add_score_message(-score_loss, snake_x, snake_y)
                    break  # Обрабатываем только первое касание

        return False

    def add_score_message(self, score_change, x=None, y=None):
        """Добавляет сообщение об изменении очков (всегда показываем сверху по центру)"""
        # Все сообщения показываем сверху по центру
        x = SCREEN_WIDTH // 2
        y = SCREEN_HEIGHT - 60

        # Формируем текст с плюсом для положительных значений
        if score_change > 0:
            text = f"+{score_change}"
            color = (0, 255, 0)  # Зеленый
        else:
            text = str(score_change)
            color = (255, 0, 0)  # Красный

        # Добавляем сообщение: (текст, x, y, время жизни, цвет)
        self.score_messages.append({
            'text': text,
            'x': x,
            'y': y,
            'life': 1.5,  # Время жизни в секундах
            'color': color
        })

    def game_over(self):
        """Завершает игру и показывает экран проигрыша"""
        # Обновляем рекорд, если текущий счёт больше
        high_score = load_high_score()
        if self.score > high_score:
            save_high_score(self.score)

        from menu import GameOverView
        game_over_view = GameOverView(self.score)
        self.window.show_view(game_over_view)

    def on_update(self, delta_time):
        """Обновление игры"""
        # Обновление сообщений об изменении очков
        for msg in self.score_messages[:]:
            msg['life'] -= delta_time
            msg['y'] += 30 * delta_time  # Движение вверх
            if msg['life'] <= 0:
                self.score_messages.remove(msg)

        # Обновление падающих фигур
        self.fall_timer += delta_time
        if self.fall_timer >= self.fall_speed:
            self.fall_timer = 0.0

            # Автоматическое позиционирование для заполнения рядов
            if self.current_piece:
                best_row, max_filled = self.find_best_target_row()
                # Если есть ряд, который заполнен хотя бы на 40%, пытаемся его заполнить
                if best_row >= 0 and max_filled >= int(GRID_WIDTH * 0.4):
                    # Находим лучшую позицию для фигуры
                    desired_x = self.find_best_position_for_piece(
                        self.current_piece, best_row)
                    current_x = self.current_piece.get_x()

                    # Плавно сдвигаем фигуру к целевой позиции (постепенно, не резко)
                    if desired_x != current_x:
                        dx = 1 if desired_x > current_x else -1
                        # Сдвигаем только если разница значительная или фигура еще высоко
                        piece_y = self.current_piece.get_y()
                        if abs(desired_x - current_x) > 0 and piece_y > GRID_HEIGHT - 10:
                            # Пытаемся сдвинуть, проверяя валидность
                            if self.is_valid_position(self.current_piece, dx, 0):
                                self.current_piece.move(dx, 0)

            if not self.move_piece(0, -1):
                # Если не можем двигаться вниз, фиксируем фигуру
                self.lock_piece()

        # Обновление змейки
        self.snake_timer += delta_time
        if self.snake_timer >= self.snake_speed:
            self.snake_timer = 0.0

            # Сохраняем хвост перед движением (для роста, если съедим яблоко)
            old_tail = self.snake.body[-1] if len(
                self.snake.body) > 1 else None

            # Двигаем змейку (направление может измениться внутри move)
            self.snake.move(grow=False)

            # Проверяем яблоко ПОСЛЕ движения, используя реальную новую позицию головы
            new_head = self.snake.get_head()
            if self.apple and new_head == self.apple.get_position():
                # Яблоко съедено - змейка должна вырасти
                # Возвращаем удаленный хвост, чтобы змейка выросла
                if old_tail:
                    self.snake.body.append(old_tail)
                apple_x, apple_y = self.apple.get_position()
                self.score += 100
                self.add_score_message(100, apple_x, apple_y)
                self.spawn_apple()

            # Проверяем столкновения
            if self.check_snake_collision():
                self.game_over()
                return

            # Проверяем доступность яблока после каждого обновления
            # (ситуация может измениться, например, упала фигура)
            if self.apple:
                apple_pos = self.apple.get_position()
                if not self.is_apple_accessible(apple_pos[0], apple_pos[1]):
                    # Яблоко стало недоступным - уничтожаем без снятия очков
                    self.apple = None
                    self.spawn_apple()

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
        if key == arcade.key.W:
            self.snake.change_direction(0)  # Вверх
        elif key == arcade.key.D:
            self.snake.change_direction(1)  # Вправо
        elif key == arcade.key.S:
            self.snake.change_direction(2)  # Вниз
        elif key == arcade.key.A:
            self.snake.change_direction(3)  # Влево

    def draw_apple(self):
        """Отрисовка яблока"""
        if self.apple:
            self.apple.draw()

    def on_draw(self):
        """Отрисовка игры"""
        self.clear()

        self.draw_grid()
        self.draw_blocks()
        self.draw_apple()
        self.snake.draw()

        score_text = f"Счет: {self.score}"
        arcade.draw_text(score_text, 10, SCREEN_HEIGHT -
                         30, arcade.color.WHITE, 16)

        # Отрисовка сообщений об изменении очков
        for msg in self.score_messages:
            arcade.draw_text(
                msg['text'],
                msg['x'],
                msg['y'],
                msg['color'],
                20,
                anchor_x='center',
                anchor_y='center',
                bold=True
            )
