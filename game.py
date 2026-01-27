"""Основной класс игры"""
import arcade
import random
import json
import os
import pymunk
import copy
from record_service import fetch_record_async, post_record_async
from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GRID_WIDTH, GRID_HEIGHT,
    MARGIN, CELL_SIZE, COLORS, TETROMINOES, DIFFICULTY_SETTINGS,
    PIECE_SPAWN_DELAY, PIECE_SPAWN_DELAY_CYCLES, COLUMN_CLEAR_THRESHOLD,
    ROW_CLEAR_HEIGHT_THRESHOLD, POINTS_PER_LINE
)
from snake import Snake
from tetromino import Tetromino
from apple import Apple
from menu import load_settings
from particles import ParticleSystem
from block_sprite import BlockSprite

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

        # Загружаем настройки
        settings = load_settings()
        self.camera_follow_snake = settings.get('camera_follow_snake', False)

        # Настройки сложности
        self.difficulty = difficulty
        difficulty_config = DIFFICULTY_SETTINGS.get(
            difficulty, DIFFICULTY_SETTINGS['medium'])
        self.fall_speed = difficulty_config['fall_speed']
        self.snake_speed = difficulty_config['snake_speed']
        self.spawn_delay = difficulty_config.get('spawn_delay', PIECE_SPAWN_DELAY)

        self.grid = [[None for _ in range(GRID_WIDTH)]
                     for _ in range(GRID_HEIGHT)]

        self.current_piece = None
        self.fall_timer = 0.0
        self.piece_spawn_delay_timer = 0.0
        self.piece_spawn_delay_cycles = 0
        self.piece_spawn_delay_applied = False  # Флаг, что задержка уже применена
        self.score = 0
        self.max_score = 0  # Максимальный счёт за игру (для рекорда)
        self.high_score = load_high_score()  # Загружаем текущий рекорд
        self._last_posted_record = 0  # чтобы не спамить сервер одинаковыми значениями

        # Пробуем получить рекорд с сервера (не блокируя игру)
        self._try_load_remote_record()

        # Инициализация змейки в безопасной позиции
        snake_x, snake_y = self._find_safe_snake_spawn()
        self.snake = Snake(snake_x, snake_y)
        self.snake_timer = 0.0

        # Яблоко (теперь спрайт)
        self.apple = None
        self.apple_sprite_list = arcade.SpriteList()
        # Защита от частых пересозданий яблока
        self.apple_spawn_timer = 0.0
        self.apple_spawn_cooldown = 0.5  # Минимальный интервал между пересозданиями (0.5 секунды)
        self.apple_spawn_attempts = 0  # Счетчик попыток пересоздания
        self.apple_spawn_max_attempts = 5  # Максимум попыток подряд без проверки доступности
        self.apple_last_spawn_time = 0.0  # Время последнего спавна
        self.spawn_apple()

        self.spawn_new_piece()

        # Сообщения об изменении очков (текст, x, y, время жизни, цвет)
        self.score_messages = []

        # Счетчик фигур для постепенного ускорения
        self.pieces_count = 0
        self.base_fall_speed = self.fall_speed  # Сохраняем базовую скорость

        # Система частиц
        self.particle_system = ParticleSystem()

        # Спрайты для блоков (для использования методов collide)
        self.block_sprites = arcade.SpriteList()

        # Физический движок (pymunk)
        self.space = pymunk.Space()
        self.space.gravity = (0, -981)  # Гравитация вниз

        # Звуки
        self.sound_eat_apple = None
        self.sound_line_clear = None
        self.sound_game_over = None
        self.sound_background = None
        self.background_music_player = None
        self.load_sounds()

        # Запускаем фоновую музыку
        if self.sound_background:
            self.background_music_player = self.sound_background.play(
                volume=0.3, loop=True)

        # Настройки камеры
        # Увеличение при следовании за змейкой (меньше = больше область видимости)
        self.camera_zoom = 1.2
        # Инициализируем камеру начальной позицией змейки
        snake_head = self.snake.get_head()
        self.camera_x = MARGIN + snake_head[0] * CELL_SIZE + CELL_SIZE // 2
        self.camera_y = MARGIN + snake_head[1] * CELL_SIZE + CELL_SIZE // 2
        # Создаем камеру для игрового поля
        self._camera = arcade.Camera2D()
        # Создаем камеру по умолчанию для UI
        self._ui_camera = arcade.Camera2D()

        # Анимация для фигур
        self.piece_animation_timer = 0.0

    def _try_load_remote_record(self):
        """Пытается подтянуть рекорд с сервера в фоне.
        Если серверный рекорд загрузился - используем его (приоритет серверу).
        Если не загрузился - используем локальный."""

        def _on_result(remote_record):
            try:
                # Проверяем, что серверный рекорд был успешно получен
                if remote_record is not None and isinstance(remote_record, int) and remote_record >= 0:
                    print(f"[Игра] Получен рекорд с сервера: {remote_record}, текущий локальный: {self.high_score}")
                    # Используем серверный рекорд (приоритет серверу)
                    # Это источник истины, даже если он меньше локального
                    self.high_score = remote_record
                    # Обновляем последний отправленный рекорд, чтобы не отправлять меньшие значения
                    self._last_posted_record = remote_record
                    # Сохраняем в локальный файл как кэш
                    save_high_score(self.high_score)
                    print(f"[Игра] Рекорд обновлён: {self.high_score}")
                else:
                    print(f"[Игра] Не удалось получить рекорд с сервера (получено: {remote_record}), используем локальный: {self.high_score}")
            except Exception as e:
                # Если ошибка - оставляем локальный рекорд (уже загружен в self.high_score)
                print(f"[Игра] Ошибка при обработке рекорда с сервера: {type(e).__name__}: {e}")

        try:
            print(f"[Игра] Запрос рекорда с сервера...")
            fetch_record_async(_on_result)
        except Exception as e:
            # Если не удалось запустить запрос - используем локальный рекорд
            print(f"[Игра] Ошибка при запуске запроса рекорда: {type(e).__name__}: {e}")

    def _try_post_record(self, record: int):
        """Отправляет рекорд на сервер в фоне (с защитой от повторов).
        Отправляет только если рекорд больше текущего рекорда с сервера."""
        try:
            if not isinstance(record, int):
                print(f"[Игра] Ошибка: неверный тип рекорда для отправки: {type(record)}")
                return
            if record <= 0:
                print(f"[Игра] Пропуск отправки: рекорд <= 0: {record}")
                return
            # Отправляем только если рекорд больше последнего полученного с сервера
            # (self.high_score содержит рекорд с сервера после загрузки)
            if record <= self.high_score:
                print(f"[Игра] Пропуск отправки: рекорд {record} не больше текущего рекорда {self.high_score}")
                return
            # Не отправляем повторно, если уже отправляли этот рекорд
            if record <= self._last_posted_record:
                print(f"[Игра] Пропуск отправки: рекорд {record} уже был отправлен (последний отправленный: {self._last_posted_record})")
                return
            # Обновляем последний отправленный рекорд
            self._last_posted_record = record
            print(f"[Игра] Отправка рекорда {record} на сервер...")
            
            def on_post_done(success: bool):
                if success:
                    print(f"[Игра] Рекорд {record} успешно отправлен на сервер")
                    # Обновляем high_score, чтобы не пытаться отправить снова
                    if record > self.high_score:
                        self.high_score = record
                        save_high_score(self.high_score)
                else:
                    print(f"[Игра] Не удалось отправить рекорд {record} на сервер")
            
            post_record_async(record, on_done=on_post_done)
        except Exception as e:
            print(f"[Игра] Ошибка при попытке отправить рекорд: {type(e).__name__}: {e}")

    def load_sounds(self):
        """Загружает звуки игры"""
        try:
            # Пытаемся загрузить звуки из встроенных ресурсов arcade
            sound_paths = {
                'eat_apple': [
                    ":resources:sounds/coin1.wav",
                    ":resources:sounds/coin2.wav",
                    ":resources:sounds/coin3.wav",
                    ":resources:sounds/coin4.wav",
                    ":resources:sounds/coin5.wav",
                ],
                'line_clear': [
                    ":resources:sounds/upgrade1.wav",
                    ":resources:sounds/upgrade2.wav",
                    ":resources:sounds/upgrade3.wav",
                    ":resources:sounds/upgrade4.wav",
                    ":resources:sounds/upgrade5.wav",
                ],
                'game_over': [
                    ":resources:sounds/gameover1.wav",
                    ":resources:sounds/gameover2.wav",
                    ":resources:sounds/gameover3.wav",
                    ":resources:sounds/gameover4.wav",
                    ":resources:sounds/gameover5.wav",
                ],
                'background': [
                    ":resources:music/funkyrobot.mp3",
                    ":resources:music/1918.mp3",
                ]
            }

            for sound_name, paths in sound_paths.items():
                for path in paths:
                    try:
                        if sound_name == 'eat_apple':
                            self.sound_eat_apple = arcade.load_sound(path)
                        elif sound_name == 'line_clear':
                            self.sound_line_clear = arcade.load_sound(path)
                        elif sound_name == 'game_over':
                            self.sound_game_over = arcade.load_sound(path)
                        elif sound_name == 'background':
                            self.sound_background = arcade.load_sound(path)
                        break
                    except:
                        continue
        except:
            pass  # Если звуки не загрузились, продолжаем без них

    def _find_safe_snake_spawn(self):
        """Находит безопасную позицию для спавна змейки
        Проверяет, что змейка не спавнится:
        - слишком близко к стенам в направлении движения (вправо)
        - под падающим блоком или перед ним
        - в области с блоками на сетке
        """
        # Змейка изначально движется вправо (direction = 1)
        # Минимальные отступы от стен для безопасности
        min_distance_from_right = 6  # От правой стены (направление движения)
        min_distance_from_left = 3   # От левой стены
        min_distance_from_top = 4    # От верхней стены
        min_distance_from_bottom = 3  # От нижней стены
        
        # Змейка имеет длину 3, поэтому нужно учесть это
        snake_length = 3
        
        max_attempts = 500
        for attempt in range(max_attempts):
            # Генерируем случайную позицию с учетом минимальных отступов
            snake_x = random.randint(
                min_distance_from_left,
                GRID_WIDTH - min_distance_from_right - snake_length
            )
            snake_y = random.randint(
                min_distance_from_bottom,
                GRID_HEIGHT - min_distance_from_top
            )
            
            # Проверяем, что позиция безопасна
            if self._is_safe_spawn_position(snake_x, snake_y):
                return snake_x, snake_y
        
        # Если не нашли безопасную позицию после всех попыток,
        # возвращаем позицию по умолчанию (центр поля с отступами)
        default_x = max(min_distance_from_left, 
                       min(GRID_WIDTH - min_distance_from_right - snake_length,
                           GRID_WIDTH // 2 - snake_length // 2))
        default_y = max(min_distance_from_bottom,
                       min(GRID_HEIGHT - min_distance_from_top,
                           GRID_HEIGHT // 2))
        return default_x, default_y

    def _is_safe_spawn_position(self, snake_x, snake_y):
        """Проверяет, является ли позиция безопасной для спавна змейки"""
        # Змейка имеет длину 3 и движется вправо
        # Тело змейки: [(x, y), (x-1, y), (x-2, y)]
        snake_body = [(snake_x, snake_y), (snake_x - 1, snake_y), (snake_x - 2, snake_y)]
        
        # Проверяем каждую часть тела змейки
        for x, y in snake_body:
            # Проверяем границы
            if x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT:
                return False
            
            # Проверяем, что нет блоков на сетке
            if 0 <= y < GRID_HEIGHT and 0 <= x < GRID_WIDTH:
                if self.grid[y][x] is not None:
                    return False
        
        # Проверяем, что в направлении движения (вправо) есть достаточно места
        # Проверяем следующие 5 клеток вправо от головы
        safe_distance_ahead = 5
        for i in range(1, safe_distance_ahead + 1):
            check_x = snake_x + i
            check_y = snake_y
            
            # Если вышли за границы - это плохо (слишком близко к стене)
            if check_x >= GRID_WIDTH:
                return False
            
            # Проверяем, что впереди нет блоков
            if 0 <= check_y < GRID_HEIGHT and 0 <= check_x < GRID_WIDTH:
                if self.grid[check_y][check_x] is not None:
                    return False
        
        # Проверяем, что нет падающей фигуры в опасной близости
        # (хотя при инициализации current_piece еще None, но на всякий случай)
        if self.current_piece:
            piece_positions = self.current_piece.get_positions()
            # Проверяем, не пересекается ли змейка с падающей фигурой
            for snake_x_pos, snake_y_pos in snake_body:
                if (snake_x_pos, snake_y_pos) in piece_positions:
                    return False
            
            # Проверяем, не находится ли падающая фигура прямо над змейкой
            # или в опасной близости впереди
            piece_min_y = min(py for px, py in piece_positions)
            piece_max_x = max(px for px, py in piece_positions)
            piece_min_x = min(px for px, py in piece_positions)
            
            # Если фигура находится над змейкой (по Y) и может упасть на нее
            if piece_min_y > snake_y:
                # Проверяем, не находится ли фигура в опасной близости по X
                if not (piece_max_x < snake_x - 2 or piece_min_x > snake_x + safe_distance_ahead):
                    return False
        
        # Проверяем, что есть место для маневра вверх и вниз
        # (чтобы игрок мог повернуть, если нужно)
        if snake_y + 2 >= GRID_HEIGHT or snake_y - 2 < 0:
            return False
        
        # Проверяем, что сверху и снизу нет блоков в опасной близости
        for offset_y in [-2, -1, 1, 2]:
            check_y = snake_y + offset_y
            if 0 <= check_y < GRID_HEIGHT:
                # Проверяем позиции тела змейки по X
                for offset_x in [0, -1, -2]:
                    check_x = snake_x + offset_x
                    if 0 <= check_x < GRID_WIDTH:
                        if self.grid[check_y][check_x] is not None:
                            # Блок слишком близко - небезопасно
                            return False
        
        return True

    def _is_piece_safe_from_snake(self, piece):
        """Проверяет, не находится ли фигура в опасной позиции относительно змейки
        Фигура считается опасной, если она:
        - находится прямо над змейкой или в опасной близости
        - может упасть на змейку слишком быстро
        """
        if not hasattr(self, 'snake') or not self.snake:
            return True  # Если змейки еще нет, позиция безопасна
        
        piece_positions = piece.get_positions()
        snake_body = self.snake.get_body()
        snake_head = self.snake.get_head()
        snake_x, snake_y = snake_head
        
        # Находим границы фигуры
        piece_min_x = min(px for px, py in piece_positions)
        piece_max_x = max(px for px, py in piece_positions)
        piece_min_y = min(py for px, py in piece_positions)
        piece_max_y = max(py for px, py in piece_positions)
        
        # Находим границы змейки
        snake_min_x = min(sx for sx, sy in snake_body)
        snake_max_x = max(sx for sx, sy in snake_body)
        snake_min_y = min(sy for sx, sy in snake_body)
        snake_max_y = max(sy for sx, sy in snake_body)
        
        # Проверяем, не находится ли фигура прямо над змейкой
        # (по X координате пересекается с змейкой)
        x_overlap = not (piece_max_x < snake_min_x - 1 or piece_min_x > snake_max_x + 1)
        
        if x_overlap:
            # Если есть пересечение по X, проверяем расстояние по Y
            # Фигура находится вверху (y = GRID_HEIGHT - 1), змейка ниже
            # Вычисляем минимальное расстояние по Y между фигурой и змейкой
            # (фигура выше змейки, поэтому piece_min_y > snake_max_y)
            vertical_distance = piece_min_y - snake_max_y
            
            # Если расстояние слишком маленькое (меньше 8 клеток), это опасно
            # Игрок должен иметь время среагировать
            if vertical_distance < 8:
                return False
        
        # Проверяем, не находится ли фигура в опасной близости впереди змейки
        # (змейка движется вправо, поэтому проверяем справа от змейки)
        # Если фигура находится справа от змейки и может упасть на ее путь
        if piece_min_x >= snake_max_x:
            # Фигура справа от змейки
            horizontal_distance = piece_min_x - snake_max_x
            # Если фигура слишком близко (меньше 3 клеток) и может упасть на путь змейки
            if horizontal_distance < 3 and x_overlap:
                return False
        
        # Проверяем, не находится ли фигура слишком близко по диагонали
        # (может упасть на змейку при движении)
        if x_overlap:
            # Если фигура находится в опасной зоне (может упасть на змейку быстро)
            # Проверяем, что есть достаточно времени для реакции
            min_safe_distance = 6  # Минимальное безопасное расстояние
            if vertical_distance < min_safe_distance:
                return False
        
        return True

    def find_best_target_row(self):
        """Находит лучший ряд для заполнения (приоритет рядам, близким к завершению)"""
        best_row = -1
        best_score = -1
        max_filled = 0

        # Анализируем нижние 15 рядов (игровую зону)
        for y in range(max(0, GRID_HEIGHT - 15), GRID_HEIGHT):
            filled_count = sum(1 for x in range(GRID_WIDTH)
                               if self.grid[y][x] is not None)

            # Пропускаем полностью заполненные ряды
            if filled_count >= GRID_WIDTH:
                continue

            # Вычисляем "ценность" ряда: чем больше заполнен и чем ниже, тем лучше
            fill_ratio = filled_count / GRID_WIDTH
            height_bonus = (GRID_HEIGHT - y) / \
                GRID_HEIGHT  # Нижние ряды важнее

            # Улучшенная оценка: приоритет рядам с заполнением 20-95%
            # Снижаем порог с 30% до 20% для более агрессивного заполнения
            if fill_ratio >= 0.2:
                score = fill_ratio * 150 + height_bonus * 40  # Увеличиваем веса
                # Большой бонус за ряды, близкие к завершению
                if fill_ratio >= 0.9:
                    score += 80  # Почти готовый ряд - максимальный приоритет
                elif fill_ratio >= 0.8:
                    score += 60
                elif fill_ratio >= 0.7:
                    score += 45
                elif fill_ratio >= 0.6:
                    score += 30
                elif fill_ratio >= 0.5:
                    score += 20
                elif fill_ratio >= 0.4:
                    score += 10

                # Дополнительный бонус за последовательные заполненные клетки
                consecutive_bonus = 0
                max_consecutive = 0
                current_consecutive = 0
                for x in range(GRID_WIDTH):
                    if self.grid[y][x] is not None:
                        current_consecutive += 1
                        max_consecutive = max(
                            max_consecutive, current_consecutive)
                    else:
                        current_consecutive = 0
                consecutive_bonus = max_consecutive * 3  # Увеличиваем бонус
                score += consecutive_bonus
                
                # Бонус за компактность пробелов (меньше маленьких пробелов = лучше)
                gap_count = GRID_WIDTH - filled_count
                if gap_count > 0:
                    # Подсчитываем количество отдельных пробелов
                    separate_gaps = 0
                    prev_filled = True
                    for x in range(GRID_WIDTH):
                        is_filled = self.grid[y][x] is not None
                        if not is_filled and prev_filled:
                            separate_gaps += 1
                        prev_filled = is_filled
                    # Меньше отдельных пробелов = лучше
                    score += (GRID_WIDTH - separate_gaps) * 2

                if score > best_score:
                    best_score = score
                    best_row = y
                    max_filled = filled_count
            elif filled_count > 0:
                # Для рядов с меньшим заполнением используем меньший приоритет
                score = fill_ratio * 50 + height_bonus * 20
                if score > best_score and best_row == -1:
                    best_score = score
                    best_row = y
                    max_filled = filled_count

        return best_row, max_filled if best_row >= 0 else 0

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

        # Анализируем форму фигуры
        shape = piece.get_shape()
        current_x = piece.get_x()

        # Находим ширину фигуры по X
        piece_x_positions = [current_x + dx for dx, dy in shape]
        min_piece_x = min(piece_x_positions)
        max_piece_x = max(piece_x_positions)
        piece_width = max_piece_x - min_piece_x + 1
        piece_center_x = (min_piece_x + max_piece_x) / 2

        # Находим все последовательные пробелы и выбираем лучший
        gap_segments = []
        if gaps:
            gap_start = gaps[0]
            gap_end = gaps[0]

            for i in range(1, len(gaps)):
                if gaps[i] == gaps[i-1] + 1:
                    gap_end = gaps[i]
                else:
                    gap_segments.append((gap_start, gap_end))
                    gap_start = gaps[i]
                    gap_end = gaps[i]
            gap_segments.append((gap_start, gap_end))

        if not gap_segments:
            return piece.get_x()

        # Выбираем пробел, который лучше всего подходит для фигуры
        best_position = current_x
        best_score = -1

        for gap_start, gap_end in gap_segments:
            gap_length = gap_end - gap_start + 1
            gap_center = gap_start + gap_length / 2

            # Оценка: предпочитаем пробелы, которые точно вмещают фигуру или немного больше
            if gap_length >= piece_width:
                # Пробел подходит по размеру
                # Чем точнее, тем лучше
                score = 100 - abs(gap_length - piece_width)
                # Бонус за центрирование
                position_x = gap_center - piece_center_x + current_x
                if 0 <= position_x <= GRID_WIDTH - piece_width:
                    score += 20
                    if score > best_score:
                        best_score = score
                        best_position = int(position_x)
            elif gap_length >= piece_width - 1:
                # Почти подходит - можно попробовать
                score = 50
                position_x = gap_center - piece_center_x + current_x
                if 0 <= position_x <= GRID_WIDTH - piece_width:
                    if score > best_score:
                        best_score = score
                        best_position = int(position_x)

        # Ограничиваем границами поля
        best_position = max(0, min(GRID_WIDTH - 1, best_position))

        # Проверяем, что фигура не выходит за границы
        test_piece_x = best_position
        piece_x_positions_test = [test_piece_x + dx for dx, dy in shape]
        if min(piece_x_positions_test) < 0:
            best_position = -min(piece_x_positions_test)
        if max(piece_x_positions_test) >= GRID_WIDTH:
            best_position = GRID_WIDTH - 1 - \
                max(piece_x_positions_test) + current_x

        return max(0, min(GRID_WIDTH - 1, best_position))

    def analyze_grid_for_spawn(self):
        """Анализирует поле и возвращает подходящую позицию X и тип фигуры
        Избегает столбцов с высокой башней, чтобы блоки не падали только в одно место"""
        # Сначала вычисляем высоту каждого столбца
        column_heights = []
        for x in range(GRID_WIDTH):
            # Находим самый верхний блок в столбце
            top_block_y = -1
            for y in range(GRID_HEIGHT - 1, -1, -1):  # Идём сверху вниз
                if self.grid[y][x] is not None:
                    top_block_y = y
                    break
            # Высота столбца = индекс самого верхнего блока + 1 (или 0, если пустой)
            column_height = top_block_y + 1 if top_block_y >= 0 else 0
            column_heights.append(column_height)
        
        # Находим максимальную высоту столбца
        max_column_height = max(column_heights) if column_heights else 0
        
        # Определяем порог "высокой башни" - если столбец выше 60% от максимальной высоты
        # или выше GRID_HEIGHT - 8, считаем его высокой башней
        high_tower_threshold = max(
            int(max_column_height * 0.6) if max_column_height > 0 else 0,
            GRID_HEIGHT - 8
        )
        
        best_row, max_filled = self.find_best_target_row()

        # Если нашли заполненный ряд, ищем пробелы
        if best_row >= 0 and max_filled > 0:
            gaps = []
            for x in range(GRID_WIDTH):
                if self.grid[best_row][x] is None:
                    # Исключаем столбцы с высокой башней
                    if column_heights[x] < high_tower_threshold:
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

        # Если не нашли подходящий ряд, выбираем случайно, но избегая столбцов с высокой башней
        # Находим столбцы с низкой высотой (предпочитаем их)
        low_height_columns = [x for x in range(GRID_WIDTH) 
                              if column_heights[x] < high_tower_threshold]
        
        if low_height_columns:
            # Если есть столбцы с низкой высотой, выбираем из них
            # Предпочитаем столбцы с минимальной высотой
            min_height = min(column_heights[x] for x in low_height_columns)
            best_columns = [x for x in low_height_columns 
                           if column_heights[x] == min_height]
            target_x = random.choice(best_columns)
        else:
            # Если все столбцы высокие, выбираем столбец с минимальной высотой
            min_height = min(column_heights)
            best_columns = [x for x in range(GRID_WIDTH) 
                           if column_heights[x] == min_height]
            target_x = random.choice(best_columns)
        
        # Ограничиваем границами поля
        target_x = max(2, min(GRID_WIDTH - 3, target_x))

        piece_type = random.choice(list(TETROMINOES.keys()))
        return target_x, piece_type

    def spawn_new_piece(self):
        """Создает новую фигуру вверху поля с учетом анализа поля"""
        x, piece_type = self.analyze_grid_for_spawn()
        color = random.choice(COLORS)
        y = GRID_HEIGHT - 1

        self.current_piece = Tetromino(piece_type, color, x, y)

        # Случайный поворот фигуры перед появлением (0, 90, 180 или 270 градусов)
        rotations = random.randint(0, 3)
        for _ in range(rotations):
            self.current_piece.rotate()

        # Проверяем, не находится ли фигура в опасной позиции относительно змейки
        # Если да, пытаемся найти безопасную позицию
        if not self._is_piece_safe_from_snake(self.current_piece):
            # Пытаемся найти безопасную позицию
            safe_found = False
            for attempt in range(50):  # Максимум 50 попыток
                # Пробуем разные X позиции
                test_x = random.randint(2, GRID_WIDTH - 3)
                self.current_piece.x = test_x
                self.current_piece.y = GRID_HEIGHT - 1
                
                # Пробуем разные повороты
                test_rotations = random.randint(0, 3)
                # Сбрасываем поворот
                self.current_piece.shape = copy.deepcopy(TETROMINOES[piece_type])
                for _ in range(test_rotations):
                    self.current_piece.rotate()
                
                if self._is_piece_safe_from_snake(self.current_piece):
                    safe_found = True
                    break
            
            # Если не нашли безопасную позицию, оставляем как есть
            # (лучше чем ничего, и задержка спавна даст время игроку)

        # Сбрасываем таймер задержки после появления
        self.piece_spawn_delay_timer = 0.0
        self.piece_spawn_delay_cycles = 0
        self.piece_spawn_delay_applied = False  # Сбрасываем флаг задержки

    def is_cell_free(self, x, y, ignore_apple=None, ignore_snake=False):
        """Проверяет, свободна ли клетка (не занята блоками, фигурой, змейкой)
        ignore_snake: если True, не учитывает змейку как препятствие"""
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
        if not ignore_snake and self.snake.check_collision_with_position(x, y):
            return False

        return True

    def is_apple_accessible(self, apple_x, apple_y):
        """Проверяет доступность яблока для змейки:
        1. Находит кратчайший путь от змейки до яблока (не учитывая змейку как препятствие)
        2. Если путь найден, занимает пространство размером змейки от яблока
        3. Проверяет путь от яблока до центра/пустого места для возврата"""
        snake_head = self.snake.get_head()
        snake_length = len(self.snake.get_body())
        # Вверх, вправо, вниз, влево
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]

        # Шаг 1: Находим кратчайший путь от змейки до яблока
        # НЕ учитываем змейку как препятствие (только блоки тетриса)
        start = snake_head
        queue = [(start, [start])]  # (позиция, путь)
        visited = {start}
        path_to_apple = None

        while queue:
            current, path = queue.pop(0)

            if current == (apple_x, apple_y):
                path_to_apple = path
                break

            for dx, dy in directions:
                nx, ny = current[0] + dx, current[1] + dy
                neighbor = (nx, ny)

                # Проверяем границы
                if nx < 0 or nx >= GRID_WIDTH or ny < 0 or ny >= GRID_HEIGHT:
                    continue

                # Проверяем, свободна ли клетка (игнорируем яблоко и змейку)
                if not self.is_cell_free(nx, ny, ignore_apple=(apple_x, apple_y), ignore_snake=True):
                    continue

                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = path + [neighbor]
                    queue.append((neighbor, new_path))

        if not path_to_apple:
            return False  # Не можем добраться до яблока

        # Шаг 2: Занимаем пространство размером змейки от яблока
        # Берем последние snake_length клеток пути от яблока
        occupied_cells = set()
        if len(path_to_apple) >= snake_length:
            # Берем последние snake_length клеток пути (включая яблоко)
            for i in range(len(path_to_apple) - snake_length, len(path_to_apple)):
                occupied_cells.add(path_to_apple[i])
        else:
            # Если путь короче длины змейки, занимаем весь путь
            occupied_cells = set(path_to_apple)

        # Шаг 3: Проверяем путь от яблока до центра/пустого места
        # Ищем центр поля или ближайшее пустое место
        center_x = GRID_WIDTH // 2
        center_y = GRID_HEIGHT // 2

        # Ищем ближайшее пустое место к центру
        target_positions = []
        for y in range(max(0, center_y - 5), min(GRID_HEIGHT, center_y + 6)):
            for x in range(max(0, center_x - 5), min(GRID_WIDTH, center_x + 6)):
                if self.is_cell_free(x, y, ignore_apple=(apple_x, apple_y), ignore_snake=True):
                    target_positions.append((x, y))

        # Если не нашли пустых мест около центра, ищем любое пустое место выше
        if not target_positions:
            for y in range(GRID_HEIGHT // 2, GRID_HEIGHT):
                for x in range(GRID_WIDTH):
                    if self.is_cell_free(x, y, ignore_apple=(apple_x, apple_y), ignore_snake=True):
                        target_positions.append((x, y))
                        if len(target_positions) >= 5:
                            break
                if len(target_positions) >= 5:
                    break

        if not target_positions:
            return False  # Нет пустых мест для возврата

        # Проверяем путь от яблока до любого из целевых мест
        # При этом учитываем занятые клетки (пространство змейки)
        escape_found = False
        # Проверяем первые 3 целевых места
        for target_x, target_y in target_positions[:3]:
            escape_queue = [(apple_x, apple_y)]
            escape_visited = {(apple_x, apple_y)}

            while escape_queue:
                current = escape_queue.pop(0)
                cx, cy = current

                if current == (target_x, target_y):
                    escape_found = True
                    break

                for dx, dy in directions:
                    nx, ny = cx + dx, cy + dy
                    neighbor = (nx, ny)

                    # Проверяем границы
                    if nx < 0 or nx >= GRID_WIDTH or ny < 0 or ny >= GRID_HEIGHT:
                        continue

                    # Проверяем, свободна ли клетка (игнорируем яблоко, змейку, но учитываем занятые клетки)
                    if neighbor in occupied_cells:
                        continue  # Клетка занята пространством змейки

                    if not self.is_cell_free(nx, ny, ignore_apple=(apple_x, apple_y), ignore_snake=True):
                        continue

                    if neighbor not in escape_visited:
                        escape_visited.add(neighbor)
                        escape_queue.append(neighbor)

            if escape_found:
                break

        return escape_found

    def _safe_spawn_apple(self, delta_time):
        """Защищенный метод для спавна яблока с ограничением частоты вызовов"""
        # Проверяем, прошло ли достаточно времени с последнего спавна
        if self.apple_spawn_timer < self.apple_spawn_cooldown:
            return  # Слишком рано для нового спавна
        
        # Если превышен лимит попыток, пропускаем проверку доступности
        skip_accessibility_check = (self.apple_spawn_attempts >= self.apple_spawn_max_attempts)
        
        # Вызываем обычный spawn_apple с флагом пропуска проверки доступности
        self.spawn_apple(skip_accessibility_check=skip_accessibility_check)
        
        # Сбрасываем таймер и обновляем счетчики
        self.apple_spawn_timer = 0.0
        self.apple_last_spawn_time = 0.0
        
        # Если яблоко успешно создано и осталось, сбрасываем счетчик попыток
        if self.apple:
            self.apple_spawn_attempts = 0
        else:
            # Если яблоко не создано, увеличиваем счетчик попыток
            self.apple_spawn_attempts += 1

    def spawn_apple(self, skip_accessibility_check=False):
        """Создает яблоко в случайной позиции (не на змейке, не на блоках, не на падающей фигуре, не в верхних 4 линиях, не под падающей фигурой)"""
        try:
            max_attempts = 200
            for attempt in range(max_attempts):
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

                # Нашли свободное место - создаем спрайт яблока
                try:
                    self.apple = Apple(apple_x, apple_y)
                    self.apple_sprite_list.clear()
                    self.apple_sprite_list.append(self.apple)

                    # Проверяем доступность яблока (особенно если оно внизу)
                    # Пропускаем проверку, если было слишком много неудачных попыток
                    if not skip_accessibility_check:
                        if not self.is_apple_accessible(apple_x, apple_y):
                            # Яблоко недоступно - уничтожаем без снятия очков и создаем новое
                            self.apple = None
                            self.apple_sprite_list.clear()
                            continue

                    # Яблоко успешно создано
                    return
                except Exception as e:
                    # Если ошибка при создании яблока, пробуем следующую позицию
                    self.apple = None
                    self.apple_sprite_list.clear()
                    continue

            # Если не нашли место после всех попыток, пробуем с ослабленными требованиями
            # (только проверяем, что не на змейке и не на блоке, игнорируем фигуру и доступность)
            for attempt in range(500):
                apple_x = random.randint(0, GRID_WIDTH - 1)
                apple_y = random.randint(0, GRID_HEIGHT - 5)

                # Проверяем только базовые условия
                if self.snake.check_collision_with_position(apple_x, apple_y):
                    continue

                if 0 <= apple_y < GRID_HEIGHT and 0 <= apple_x < GRID_WIDTH:
                    if self.grid[apple_y][apple_x] is not None:
                        continue

                # Пробуем создать яблоко даже если оно может быть под фигурой
                try:
                    self.apple = Apple(apple_x, apple_y)
                    self.apple_sprite_list.clear()
                    self.apple_sprite_list.append(self.apple)
                    # Яблоко успешно создано
                    return
                except Exception:
                    continue

            # Если всё ещё не получилось, создаём яблоко в любой свободной клетке
            for y in range(GRID_HEIGHT - 5, -1, -1):
                for x in range(GRID_WIDTH):
                    if not self.snake.check_collision_with_position(x, y):
                        if 0 <= y < GRID_HEIGHT and 0 <= x < GRID_WIDTH:
                            if self.grid[y][x] is None:
                                try:
                                    self.apple = Apple(x, y)
                                    self.apple_sprite_list.clear()
                                    self.apple_sprite_list.append(self.apple)
                                    # Яблоко успешно создано - сбрасываем счетчик попыток
                                    self.apple_spawn_attempts = 0
                                    return
                                except Exception:
                                    continue
        except Exception:
            # В случае любой ошибки пытаемся создать яблоко в безопасном месте
            try:
                safe_x = GRID_WIDTH // 2
                safe_y = GRID_HEIGHT // 2
                if not self.snake.check_collision_with_position(safe_x, safe_y):
                    if 0 <= safe_y < GRID_HEIGHT and 0 <= safe_x < GRID_WIDTH:
                        if self.grid[safe_y][safe_x] is None:
                            self.apple = Apple(safe_x, safe_y)
                            self.apple_sprite_list.clear()
                            self.apple_sprite_list.append(self.apple)
                            # Яблоко успешно создано - сбрасываем счетчик попыток
                            self.apple_spawn_attempts = 0
                            return
            except Exception:
                pass

        # Если всё ещё не получилось, ставим None (но это не должно произойти)
        self.apple = None
        self.apple_sprite_list.clear()

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
        # Проверяем, не раздавили ли яблоко падающей фигурой (используя collide)
        if self.apple:
            try:
                apple_pos = self.apple.get_position()
                piece_positions = self.current_piece.get_positions()
                if apple_pos in piece_positions:
                    # Яблоко раздавлено
                    # Отнимаем 50 очков (не меньше 0)
                    apple_x, apple_y = apple_pos
                    self.score = max(0, self.score - 50)
                    self.max_score = max(self.max_score, self.score)  # Обновляем максимальный счёт
                    self.check_and_update_high_score()  # Проверяем и обновляем рекорд
                    self.add_score_message(-50, apple_x, apple_y)
                    # Частицы при раздавливании яблока
                    try:
                        pixel_x = MARGIN + apple_x * CELL_SIZE + CELL_SIZE // 2
                        pixel_y = MARGIN + apple_y * CELL_SIZE + CELL_SIZE // 2
                        self.particle_system.add_explosion(
                            pixel_x, pixel_y, (255, 0, 0), count=15)
                    except Exception:
                        pass
                    self.apple = None
                    self.apple_sprite_list.clear()
                    self.spawn_apple()
            except Exception:
                # Если ошибка при проверке яблока, пересоздаём его
                self.apple = None
                self.apple_sprite_list.clear()
                self.spawn_apple()

        # Создаем спрайты для блоков и добавляем в список для collide
        for dx, dy in self.current_piece.get_shape():
            x = self.current_piece.get_x() + dx
            y = self.current_piece.get_y() + dy

            if 0 <= y < GRID_HEIGHT and 0 <= x < GRID_WIDTH:
                self.grid[y][x] = self.current_piece.get_color()
                # Создаем спрайт блока
                block_sprite = BlockSprite(
                    x, y, self.current_piece.get_color())
                self.block_sprites.append(block_sprite)
                # Анимация появления
                pixel_x = MARGIN + x * CELL_SIZE + CELL_SIZE // 2
                pixel_y = MARGIN + y * CELL_SIZE + CELL_SIZE // 2
                self.particle_system.add_explosion(
                    pixel_x, pixel_y, self.current_piece.get_color(), count=5)

        self.clear_lines()
        self.clear_columns()

        # Увеличиваем счетчик фигур и постепенно ускоряем падение
        self.pieces_count += 1
        # Очень медленное ускорение: каждые 10 фигур уменьшаем fall_speed на 0.001
        # Минимальная скорость - 0.05 (максимальное ускорение)
        speed_reduction = (self.pieces_count // 10) * 0.001
        self.fall_speed = max(0.03, self.base_fall_speed - speed_reduction)

        self.spawn_new_piece()

        if not self.is_valid_position(self.current_piece):
            # Игра окончена - поле переполнено
            self.game_over()

    def clear_lines(self):
        """Удаляет заполненные линии и применяет физику падения блоков"""
        lines_cleared = 0
        y = GRID_HEIGHT - 1
        cleared_rows = []

        # Сначала находим все заполненные линии
        while y >= 0:
            if all(self.grid[y][x] is not None for x in range(GRID_WIDTH)):
                # Собираем цвет для частиц
                line_color = self.grid[y][0] if self.grid[y][0] else (
                    255, 255, 255)
                cleared_rows.append((y, line_color))
                lines_cleared += 1
            y -= 1

        # Если есть линии для удаления
        if lines_cleared > 0:
            # Удаляем заполненные линии и сдвигаем блоки вниз
            cleared_row_indices = []
            y = GRID_HEIGHT - 1
            while y >= 0:
                if all(self.grid[y][x] is not None for x in range(GRID_WIDTH)):
                    # Собираем цвет для частиц
                    line_color = self.grid[y][0] if self.grid[y][0] else (
                        255, 255, 255)

                    # Удаляем спрайты блоков этой линии
                    sprites_to_remove = []
                    for sprite in self.block_sprites:
                        if sprite.grid_y == y:
                            # Частицы при удалении блока
                            pixel_x = sprite.center_x
                            pixel_y = sprite.center_y
                            self.particle_system.add_line_clear_particles(
                                pixel_x, pixel_y, line_color, count=3
                            )
                            sprites_to_remove.append(sprite)

                    for sprite in sprites_to_remove:
                        self.block_sprites.remove(sprite)

                    # Удаляем строку из сетки
                    cleared_row_indices.append(y)
                    del self.grid[y]
                    self.grid.append([None for _ in range(GRID_WIDTH)])
                else:
                    y -= 1

            # Применяем физику: сдвигаем все блоки выше удаленных линий вниз
            # Для каждой удаленной линии, все блоки выше сдвигаются вниз на 1
            for cleared_y in sorted(cleared_row_indices, reverse=True):
                # Обновляем позиции спрайтов: все спрайты выше удаленной линии сдвигаются вниз
                for sprite in self.block_sprites:
                    if sprite.grid_y > cleared_y:
                        sprite.grid_y -= 1
                        sprite.center_y = MARGIN + sprite.grid_y * CELL_SIZE + CELL_SIZE // 2

            # Начисляем очки за очищенные линии
            score_gain = lines_cleared * POINTS_PER_LINE
            self.score = max(0, self.score + score_gain)
            self.max_score = max(self.max_score, self.score)  # Обновляем максимальный счёт
            self.check_and_update_high_score()  # Проверяем и обновляем рекорд
            self.add_score_message(score_gain)

            # Звук очистки линии
            if self.sound_line_clear:
                arcade.play_sound(self.sound_line_clear, volume=0.5)

            # Частицы для каждой очищенной линии
            for row_y, color in cleared_rows:
                center_x = SCREEN_WIDTH // 2
                center_y = MARGIN + row_y * CELL_SIZE + CELL_SIZE // 2
                self.particle_system.add_line_clear_particles(
                    center_x, center_y, color, count=20)

    def clear_columns(self):
        """Удаляет столбцы, если они достигают высоты ROW_CLEAR_HEIGHT_THRESHOLD (чтобы не заполнять всё поле)
        После удаления применяет физику падения для соседних блоков"""
        columns_cleared = 0
        cleared_columns = []

        # Проверяем каждый столбец
        for x in range(GRID_WIDTH):
            # Находим самый верхний блок в столбце
            top_block_y = -1
            for y in range(GRID_HEIGHT - 1, -1, -1):  # Идём сверху вниз
                if self.grid[y][x] is not None:
                    top_block_y = y
                    break
            
            # Если столбец достиг высоты ROW_CLEAR_HEIGHT_THRESHOLD или выше, уничтожаем его
            # ROW_CLEAR_HEIGHT_THRESHOLD означает, что осталось только 4 свободных клетки сверху
            if top_block_y >= ROW_CLEAR_HEIGHT_THRESHOLD:
                # Считаем количество блоков в столбце (снизу до самого верхнего)
                blocks_count = 0
                for y in range(GRID_HEIGHT):
                    if self.grid[y][x] is not None:
                        blocks_count += 1
                    else:
                        # Если встретили пустую клетку, прерываем подсчёт
                        break
                
                # Если столбец не пустой, очищаем его
                if blocks_count > 0:
                    cleared_columns.append((x, blocks_count))
                    columns_cleared += 1

                    # Собираем цвет для частиц (берём цвет первого блока снизу)
                    column_color = self.grid[0][x] if self.grid[0][x] else (255, 255, 255)

                    # Удаляем спрайты блоков, которые находятся в удаляемых позициях (первые blocks_count снизу)
                    sprites_to_remove = []
                    for sprite in self.block_sprites:
                        if sprite.grid_x == x and sprite.grid_y < blocks_count:
                            # Частицы при удалении блока
                            pixel_x = sprite.center_x
                            pixel_y = sprite.center_y
                            self.particle_system.add_line_clear_particles(
                                pixel_x, pixel_y, column_color, count=3
                            )
                            sprites_to_remove.append(sprite)

                    for sprite in sprites_to_remove:
                        self.block_sprites.remove(sprite)

                    # Удаляем блоки из столбца (снизу вверх, blocks_count штук)
                    for y in range(blocks_count):
                        if y < GRID_HEIGHT:
                            self.grid[y][x] = None

                    # Сдвигаем все блоки выше удалённых вниз
                    # Создаём временный список для столбца
                    column_blocks = []
                    for y in range(blocks_count, GRID_HEIGHT):
                        column_blocks.append(self.grid[y][x])
                        self.grid[y][x] = None

                    # Вставляем блоки обратно, начиная снизу
                    for i, block in enumerate(column_blocks):
                        if block is not None:
                            self.grid[i][x] = block

                    # Обновляем позиции спрайтов в этом столбце (только тех, что выше удалённых)
                    for sprite in self.block_sprites:
                        if sprite.grid_x == x and sprite.grid_y >= blocks_count:
                            sprite.grid_y = sprite.grid_y - blocks_count
                            sprite.center_y = MARGIN + sprite.grid_y * CELL_SIZE + CELL_SIZE // 2

        # После удаления всех столбцов применяем физику падения только для соседних столбцов
        if columns_cleared > 0:
            # Собираем X координаты удалённых столбцов
            cleared_x_positions = [x for x, _ in cleared_columns]
            
            # Находим соседние столбцы (слева и справа от каждого удалённого)
            columns_to_update = set()
            for cleared_x in cleared_x_positions:
                # Левый сосед
                if cleared_x - 1 >= 0:
                    columns_to_update.add(cleared_x - 1)
                # Правый сосед
                if cleared_x + 1 < GRID_WIDTH:
                    columns_to_update.add(cleared_x + 1)
            
            # Применяем физику падения только к соседним столбцам
            for x in columns_to_update:
                # Собираем все блоки в столбце (снизу вверх)
                column_blocks = []
                for y in range(GRID_HEIGHT):
                    if self.grid[y][x] is not None:
                        column_blocks.append(self.grid[y][x])
                        self.grid[y][x] = None
                
                # Размещаем блоки обратно снизу вверх (блоки падают вниз)
                for i, block in enumerate(column_blocks):
                    self.grid[i][x] = block
                
                # Обновляем позиции спрайтов в этом столбце
                # Собираем все спрайты в этом столбце
                sprites_in_column = [s for s in self.block_sprites if s.grid_x == x]
                # Сортируем спрайты по старой позиции Y (снизу вверх)
                sprites_in_column.sort(key=lambda s: s.grid_y)
                
                # Обновляем позиции спрайтов согласно новым позициям блоков
                sprite_index = 0
                for y in range(GRID_HEIGHT):
                    if self.grid[y][x] is not None and sprite_index < len(sprites_in_column):
                        sprite = sprites_in_column[sprite_index]
                        sprite.grid_y = y
                        sprite.center_y = MARGIN + sprite.grid_y * CELL_SIZE + CELL_SIZE // 2
                        sprite_index += 1

            # Начисляем очки за очищенные столбцы
            score_gain = columns_cleared * 150  # Больше очков за столбцы, чем за линии
            self.score = max(0, self.score + score_gain)
            self.max_score = max(self.max_score, self.score)  # Обновляем максимальный счёт
            self.check_and_update_high_score()  # Проверяем и обновляем рекорд
            self.add_score_message(score_gain)

            # Звук очистки столбца
            if self.sound_line_clear:
                arcade.play_sound(self.sound_line_clear, volume=0.5)

            # Частицы для каждого очищенного столбца
            for col_x, _ in cleared_columns:
                center_x = MARGIN + col_x * CELL_SIZE + CELL_SIZE // 2
                center_y = MARGIN + (COLUMN_CLEAR_THRESHOLD // 2) * CELL_SIZE + CELL_SIZE // 2
                column_color = (255, 200, 0)  # Золотистый цвет для столбцов
                self.particle_system.add_line_clear_particles(
                    center_x, center_y, column_color, count=30)

    def move_piece(self, dx, dy):
        """Перемещает фигуру"""
        if self.is_valid_position(self.current_piece, dx, dy):
            self.current_piece.move(dx, dy)

            # Проверяем, не раздавили ли яблоко после перемещения
            if self.apple and dy < 0:  # Проверяем только при движении вниз
                try:
                    apple_pos = self.apple.get_position()
                    piece_positions = self.current_piece.get_positions()
                    if apple_pos in piece_positions:
                        # Яблоко раздавлено
                        apple_x, apple_y = apple_pos
                        self.score = max(0, self.score - 50)
                        self.max_score = max(self.max_score, self.score)  # Обновляем максимальный счёт
                        self.check_and_update_high_score()  # Проверяем и обновляем рекорд
                        self.add_score_message(-50, apple_x, apple_y)
                        self.apple = None
                        self.apple_sprite_list.clear()
                        self.spawn_apple()
                except Exception:
                    # Если ошибка при проверке яблока, пересоздаём его
                    self.apple = None
                    self.apple_sprite_list.clear()
                    self.spawn_apple()

            return True
        return False

    def check_snake_collision(self):
        """Проверяет столкновение змейки со стеной, фигурами или с собой (использует методы collide)"""
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

            # Проверка столкновения с зафиксированными блоками (используя collide)
            if 0 <= snake_y < GRID_HEIGHT and 0 <= snake_x < GRID_WIDTH:
                if self.grid[snake_y][snake_x] is not None:
                    # Создаем временный спрайт для проверки столкновения
                    temp_sprite = arcade.Sprite()
                    temp_sprite.center_x = MARGIN + snake_x * CELL_SIZE + CELL_SIZE // 2
                    temp_sprite.center_y = MARGIN + snake_y * CELL_SIZE + CELL_SIZE // 2
                    temp_sprite.width = CELL_SIZE
                    temp_sprite.height = CELL_SIZE

                    # Проверяем столкновение со спрайтами блоков
                    hit_list = arcade.check_for_collision_with_list(
                        temp_sprite, self.block_sprites)
                    if hit_list:
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
                        # Снимаем по 25 очков за каждый отрубленный кусок
                        score_loss = removed_count * 25
                        self.score = max(0, self.score - score_loss)
                        self.max_score = max(self.max_score, self.score)  # Обновляем максимальный счёт
                        self.check_and_update_high_score()  # Проверяем и обновляем рекорд
                        # Показываем изменение очков
                        self.add_score_message(-score_loss, snake_x, snake_y)
                        # Частицы при обрезании
                        pixel_x = MARGIN + snake_x * CELL_SIZE + CELL_SIZE // 2
                        pixel_y = MARGIN + snake_y * CELL_SIZE + CELL_SIZE // 2
                        self.particle_system.add_explosion(
                            pixel_x, pixel_y, (255, 100, 0), count=10)
                    break  # Обрабатываем только первое касание

        return False

    def check_and_update_high_score(self):
        """Проверяет и обновляет рекорд, если текущий максимальный счёт больше"""
        if self.max_score > self.high_score:
            self.high_score = self.max_score
            save_high_score(self.high_score)
            # Отправляем новый рекорд на сервер (в фоне)
            self._try_post_record(self.high_score)

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
        # Останавливаем фоновую музыку
        if self.background_music_player:
            arcade.stop_sound(self.background_music_player)

        # Звук окончания игры
        if self.sound_game_over:
            arcade.play_sound(self.sound_game_over, volume=0.8)

        # Обновляем рекорд, если максимальный счёт за игру больше
        # (используем max_score, а не финальный score)
        if self.max_score > self.high_score:
            self.high_score = self.max_score
            save_high_score(self.high_score)
            self._try_post_record(self.high_score)
        else:
            # Даже если локальный рекорд не обновили, всё равно попробуем отправить
            # максимальный счёт за игру (сервер может иметь меньший рекорд).
            self._try_post_record(self.max_score)

        from menu import GameOverView
        game_over_view = GameOverView(self.score)
        self.window.show_view(game_over_view)

    def on_update(self, delta_time):
        """Обновление игры"""
        # Обновление физического движка
        self.space.step(delta_time)

        # Обновление анимаций
        self.piece_animation_timer += delta_time

        # Обновление анимации яблока (с обработкой ошибок)
        if self.apple:
            try:
                self.apple.update_animation(delta_time)
            except Exception:
                # Если ошибка при обновлении анимации, пересоздаём яблоко
                try:
                    apple_pos = self.apple.get_position()
                    self.apple = None
                    self.apple_sprite_list.clear()
                    # Используем защищенный спавн
                    self._safe_spawn_apple(delta_time)
                except Exception:
                    self.apple = None
                    self.apple_sprite_list.clear()
                    # Используем защищенный спавн
                    self._safe_spawn_apple(delta_time)
        
        # Обновляем таймер спавна яблока
        self.apple_spawn_timer += delta_time
        self.apple_last_spawn_time += delta_time
        
        # Постоянная проверка наличия яблока - если его нет, спавним (с защитой)
        if self.apple is None:
            self._safe_spawn_apple(delta_time)

        # Обновление анимаций спрайтов блоков
        for sprite in self.block_sprites:
            if hasattr(sprite, 'update_animation'):
                sprite.update_animation(delta_time)

        # Обновление системы частиц
        self.particle_system.update(delta_time)

        # Обновление камеры (следует за змейкой)
        if self.camera_follow_snake:
            snake_head = self.snake.get_head()
            # Преобразуем координаты змейки в пиксели
            target_x = MARGIN + snake_head[0] * CELL_SIZE + CELL_SIZE // 2
            target_y = MARGIN + snake_head[1] * CELL_SIZE + CELL_SIZE // 2

            # Плавное следование камеры (интерполяция)
            lerp_speed = 5.0  # Скорость следования
            self.camera_x += (target_x - self.camera_x) * \
                lerp_speed * delta_time
            self.camera_y += (target_y - self.camera_y) * \
                lerp_speed * delta_time

        # Обновление сообщений об изменении очков
        for msg in self.score_messages[:]:
            msg['life'] -= delta_time
            msg['y'] += 30 * delta_time  # Движение вверх
            if msg['life'] <= 0:
                self.score_messages.remove(msg)

        # Обновление падающих фигур
        self.fall_timer += delta_time

        # Проверяем задержку после появления фигуры (только один раз в самом верху)
        piece_can_fall = True
        if self.current_piece and not self.piece_spawn_delay_applied:
            piece_y = self.current_piece.get_y()
            # Задержка применяется только если фигура в самом верху (y >= GRID_HEIGHT - 1)
            if piece_y >= GRID_HEIGHT - 1:
                if PIECE_SPAWN_DELAY_CYCLES > 0:
                    # Используем задержку в циклах
                    if self.piece_spawn_delay_cycles < PIECE_SPAWN_DELAY_CYCLES:
                        self.piece_spawn_delay_cycles += 1
                        piece_can_fall = False  # Пропускаем обновление падения фигуры
                    else:
                        self.piece_spawn_delay_cycles = 0
                        self.piece_spawn_delay_applied = True  # Задержка применена
                else:
                    # Используем задержку по времени (из настроек сложности)
                    if self.piece_spawn_delay_timer < self.spawn_delay:
                        self.piece_spawn_delay_timer += delta_time
                        piece_can_fall = False  # Пропускаем обновление падения фигуры
                    else:
                        self.piece_spawn_delay_timer = 0.0
                        self.piece_spawn_delay_applied = True  # Задержка применена

        if piece_can_fall and self.fall_timer >= self.fall_speed:
            self.fall_timer = 0.0

            # Фигуры падают только вниз, без автоматического позиционирования по X
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

            # Проверяем яблоко ПОСЛЕ движения - проверяем точное совпадение координат сетки
            new_head = self.snake.get_head()
            if self.apple:
                try:
                    apple_pos = self.apple.get_position()
                    # Проверяем точное совпадение координат сетки (не спрайтов)
                    if new_head == apple_pos:
                        # Яблоко съедено - змейка должна вырасти
                        # Возвращаем удаленный хвост, чтобы змейка выросла
                        if old_tail:
                            self.snake.body.append(old_tail)
                        apple_x, apple_y = self.apple.get_position()
                        self.score += 100
                        self.max_score = max(self.max_score, self.score)  # Обновляем максимальный счёт
                        self.check_and_update_high_score()  # Проверяем и обновляем рекорд
                        self.add_score_message(100, apple_x, apple_y)

                        # Звук съедания яблока
                        if self.sound_eat_apple:
                            try:
                                arcade.play_sound(self.sound_eat_apple, volume=0.7)
                            except Exception:
                                pass

                        # Частицы при съедании яблока
                        try:
                            pixel_x = self.apple.center_x
                            pixel_y = self.apple.center_y
                            self.particle_system.add_apple_particles(
                                pixel_x, pixel_y, count=15)
                        except Exception:
                            pass

                        # Анимация вращения яблока перед исчезновением
                        try:
                            self.apple.start_rotation()
                        except Exception:
                            pass

                        self.apple = None
                        self.apple_sprite_list.clear()
                        # Используем защищенный спавн
                        self._safe_spawn_apple(delta_time)
                except Exception:
                    # Если ошибка при работе с яблоком, пересоздаём его
                    self.apple = None
                    self.apple_sprite_list.clear()
                    # Используем защищенный спавн
                    self._safe_spawn_apple(delta_time)

            # Проверяем столкновения
            if self.check_snake_collision():
                self.game_over()
                return

            # Проверяем доступность яблока после каждого обновления
            # (ситуация может измениться, например, упала фигура)
            # Но только если прошло достаточно времени с последнего спавна
            if self.apple and self.apple_last_spawn_time >= 0.3:  # Минимум 0.3 секунды после спавна
                try:
                    apple_pos = self.apple.get_position()
                    if not self.is_apple_accessible(apple_pos[0], apple_pos[1]):
                        # Яблоко стало недоступным - уничтожаем без снятия очков
                        self.apple = None
                        self.apple_sprite_list.clear()
                        # Используем защищенный спавн
                        self._safe_spawn_apple(delta_time)
                except Exception:
                    # Если ошибка при проверке доступности, пересоздаём яблоко
                    self.apple = None
                    self.apple_sprite_list.clear()
                    # Используем защищенный спавн
                    self._safe_spawn_apple(delta_time)

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
        if key == arcade.key.W or key == arcade.key.UP:
            self.snake.change_direction(0)  # Вверх
        elif key == arcade.key.D or key == arcade.key.RIGHT:
            self.snake.change_direction(1)  # Вправо
        elif key == arcade.key.S or key == arcade.key.DOWN:
            self.snake.change_direction(2)  # Вниз
        elif key == arcade.key.A or key == arcade.key.LEFT:
            self.snake.change_direction(3)  # Влево

    def draw_apple(self):
        """Отрисовка яблока (спрайт)"""
        if self.apple:
            try:
                self.apple_sprite_list.draw()
            except Exception:
                # Если ошибка при отрисовке, пересоздаём яблоко
                self.apple = None
                self.apple_sprite_list.clear()
                self.spawn_apple()

    def on_draw(self):
        """Отрисовка игры"""
        self.clear()

        # Применяем камеру, если включено следование за змейкой
        if self.camera_follow_snake:
            # Устанавливаем позицию камеры (центрируем на змейке)
            # В arcade Camera2D позиция камеры - это точка в мировых координатах,
            # которая будет отображаться в центре экрана
            # camera_x и camera_y уже содержат позицию змейки в пикселях
            # Просто устанавливаем позицию камеры равной позиции змейки
            self._camera.position = (self.camera_x, self.camera_y)
            self._camera.zoom = self.camera_zoom

            # Активируем камеру
            self._camera.use()

        self.draw_grid()
        self.draw_blocks()
        # Отрисовка спрайтов блоков
        self.block_sprites.draw()
        self.draw_apple()
        self.snake.draw()

        # Отрисовка системы частиц
        self.particle_system.draw()

        # Отключаем камеру для UI элементов - используем камеру по умолчанию
        if self.camera_follow_snake:
            # Возвращаемся к обычному виду через UI камеру
            self._ui_camera.use()

        # UI элементы отрисовываются без трансформации камеры
        score_text = f"Счет: {self.score}"
        arcade.draw_text(score_text, 10, SCREEN_HEIGHT -
                         30, arcade.color.WHITE, 16)
        
        # Отображаем рекорд справа от счёта жёлтым цветом
        high_score_text = f"Рекорд: {self.high_score}"
        # Вычисляем позицию справа от счёта (примерная ширина текста счёта + отступ)
        score_text_width = len(score_text) * 10  # Примерная ширина символа
        high_score_x = 10 + score_text_width + 30  # Отступ 30 пикселей
        arcade.draw_text(high_score_text, high_score_x, SCREEN_HEIGHT -
                         30, arcade.color.YELLOW, 16)

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
