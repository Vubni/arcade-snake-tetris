"""Экраны меню и проигрыша"""
import arcade
import json
import os
from constants import SCREEN_WIDTH, SCREEN_HEIGHT
from record_service import fetch_record_async

HIGH_SCORE_FILE = "high_score.json"
SETTINGS_FILE = "settings.json"


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


def load_settings():
    """Загружает настройки из файла"""
    default_settings = {
        'camera_follow_snake': False
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Объединяем с настройками по умолчанию
                default_settings.update(data)
                return default_settings
        except:
            return default_settings
    return default_settings


def save_settings(settings):
    """Сохраняет настройки в файл"""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except:
        pass


class Button:
    """Кнопка для меню"""

    def __init__(self, x, y, width, height, text, color, hover_color):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False

    def contains_point(self, x, y):
        """Проверяет, находится ли точка внутри кнопки"""
        return (self.x - self.width // 2 <= x <= self.x + self.width // 2 and
                self.y - self.height // 2 <= y <= self.y + self.height // 2)

    def draw(self):
        """Отрисовка кнопки"""
        color = self.hover_color if self.is_hovered else self.color

        # Фон кнопки
        arcade.draw_lrbt_rectangle_filled(
            self.x - self.width // 2,
            self.x + self.width // 2,
            self.y - self.height // 2,
            self.y + self.height // 2,
            color
        )

        # Обводка - используем draw_lrtb_rectangle_outline
        arcade.draw_lrbt_rectangle_outline(
            self.x - self.width // 2,
            self.x + self.width // 2,
            self.y - self.height // 2,
            self.y + self.height // 2,
            arcade.color.WHITE, 3
        )

        # Текст
        arcade.draw_text(
            self.text, self.x, self.y,
            arcade.color.WHITE, 24,
            anchor_x="center", anchor_y="center",
            bold=True
        )


class MainMenuView(arcade.View):
    """Главное меню"""

    def __init__(self):
        super().__init__()
        arcade.set_background_color((20, 25, 40))

        # Загружаем рекорд
        self.high_score = load_high_score()
        self._remote_loaded = False

        # Пробуем подтянуть рекорд с сервера (не блокируя меню)
        self._try_load_remote_record()

        # Создаем кнопки выбора сложности
        button_y_start = SCREEN_HEIGHT // 2 + 40
        button_spacing = 80

        self.easy_button = Button(
            SCREEN_WIDTH // 2, button_y_start,
            250, 60,
            "ЛЕГКИЙ",
            (50, 150, 50),
            (70, 200, 70)
        )

        self.medium_button = Button(
            SCREEN_WIDTH // 2, button_y_start - button_spacing,
            250, 60,
            "СРЕДНИЙ",
            (150, 150, 50),
            (200, 200, 70)
        )

        self.hard_button = Button(
            SCREEN_WIDTH // 2, button_y_start - button_spacing * 2,
            250, 60,
            "СЛОЖНЫЙ",
            (150, 50, 50),
            (200, 70, 70)
        )

        # Кнопка настроек
        self.settings_button = Button(
            SCREEN_WIDTH // 2, button_y_start - button_spacing * 3 - 20,
            250, 60,
            "НАСТРОЙКИ",
            (100, 100, 150),
            (130, 130, 200)
        )

    def _try_load_remote_record(self):
        """Пытается получить рекорд с сервера в фоне и обновить отображение.
        Если серверный рекорд загрузился - используем его (приоритет серверу).
        Если не загрузился - используем локальный."""

        def _on_result(remote_record):
            try:
                # Проверяем, что серверный рекорд был успешно получен
                if remote_record is not None and isinstance(remote_record, int) and remote_record >= 0:
                    # Используем серверный рекорд (приоритет серверу)
                    # Это источник истины, даже если он меньше локального
                    self.high_score = remote_record
                    # Сохраняем в локальный файл как кэш
                    try:
                        with open(HIGH_SCORE_FILE, 'w', encoding='utf-8') as f:
                            json.dump({'high_score': self.high_score}, f, ensure_ascii=False)
                    except Exception:
                        pass
                self._remote_loaded = True
            except Exception:
                # Если ошибка - оставляем локальный рекорд (уже загружен в self.high_score)
                self._remote_loaded = True  # Помечаем, что попытка была сделана
                pass

        try:
            fetch_record_async(_on_result)
        except Exception:
            # Если не удалось запустить запрос - используем локальный рекорд
            self._remote_loaded = True  # Помечаем, что попытка была сделана
            pass

    def on_draw(self):
        """Отрисовка меню"""
        self.clear()

        # Заголовок
        arcade.draw_text(
            "ТЕТРИС СО ЗМЕЙКОЙ",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 150,
            arcade.color.WHITE, 36,
            anchor_x="center", anchor_y="center",
            bold=True
        )

        # Подзаголовок
        arcade.draw_text(
            "Управление: WASD",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 220,
            arcade.color.LIGHT_GRAY, 20,
            anchor_x="center", anchor_y="center"
        )

        # Подзаголовок - выбор сложности
        arcade.draw_text(
            "Выберите сложность:",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 260,
            arcade.color.LIGHT_GRAY, 18,
            anchor_x="center", anchor_y="center"
        )

        # Рекорд
        arcade.draw_text(
            f"Рекорд: {self.high_score}",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 300,
            arcade.color.GOLD, 20,
            anchor_x="center", anchor_y="center",
            bold=True
        )

        # Кнопки выбора сложности
        self.easy_button.draw()
        self.medium_button.draw()
        self.hard_button.draw()
        self.settings_button.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        """Обработка движения мыши"""
        self.easy_button.is_hovered = self.easy_button.contains_point(x, y)
        self.medium_button.is_hovered = self.medium_button.contains_point(x, y)
        self.hard_button.is_hovered = self.hard_button.contains_point(x, y)
        self.settings_button.is_hovered = self.settings_button.contains_point(
            x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        """Обработка нажатия мыши"""
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.easy_button.contains_point(x, y):
                from game import GameView
                game_view = GameView(difficulty='easy')
                self.window.show_view(game_view)
            elif self.medium_button.contains_point(x, y):
                from game import GameView
                game_view = GameView(difficulty='medium')
                self.window.show_view(game_view)
            elif self.hard_button.contains_point(x, y):
                from game import GameView
                game_view = GameView(difficulty='hard')
                self.window.show_view(game_view)
            elif self.settings_button.contains_point(x, y):
                settings_view = SettingsView()
                self.window.show_view(settings_view)


class GameOverView(arcade.View):
    """Экран проигрыша"""

    def __init__(self, score=0):
        super().__init__()
        arcade.set_background_color((40, 20, 20))
        self.score = score

        # Кнопка возврата в меню
        self.menu_button = Button(
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100,
            300, 60,
            "В ГЛАВНОЕ МЕНЮ",
            (150, 50, 50),
            (200, 70, 70)
        )

    def on_draw(self):
        """Отрисовка экрана проигрыша"""
        self.clear()

        # Заголовок
        arcade.draw_text(
            "ИГРА ОКОНЧЕНА",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 150,
            arcade.color.RED, 36,
            anchor_x="center", anchor_y="center",
            bold=True
        )

        # Результат
        arcade.draw_text(
            f"Ваш счет: {self.score}",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 250,
            arcade.color.WHITE, 32,
            anchor_x="center", anchor_y="center"
        )

        # Сообщение
        arcade.draw_text(
            "Змейка врезалась!",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 320,
            arcade.color.LIGHT_GRAY, 24,
            anchor_x="center", anchor_y="center"
        )

        # Кнопка
        self.menu_button.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        """Обработка движения мыши"""
        self.menu_button.is_hovered = self.menu_button.contains_point(x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        """Обработка нажатия мыши"""
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.menu_button.contains_point(x, y):
                menu_view = MainMenuView()
                self.window.show_view(menu_view)


class ToggleButton(Button):
    """Кнопка-переключатель для настроек"""

    def __init__(self, x, y, width, height, text, color, hover_color, active_color):
        super().__init__(x, y, width, height, text, color, hover_color)
        self.active_color = active_color
        self.is_active = False

    def draw(self):
        """Отрисовка кнопки-переключателя"""
        if self.is_active:
            color = self.active_color
        else:
            color = self.hover_color if self.is_hovered else self.color

        # Фон кнопки
        arcade.draw_lrbt_rectangle_filled(
            self.x - self.width // 2,
            self.x + self.width // 2,
            self.y - self.height // 2,
            self.y + self.height // 2,
            color
        )

        # Обводка
        arcade.draw_lrbt_rectangle_outline(
            self.x - self.width // 2,
            self.x + self.width // 2,
            self.y - self.height // 2,
            self.y + self.height // 2,
            arcade.color.WHITE, 3
        )

        # Текст с индикатором состояния
        status_text = "ВКЛ" if self.is_active else "ВЫКЛ"
        full_text = f"{self.text}: {status_text}"
        arcade.draw_text(
            full_text, self.x, self.y,
            arcade.color.WHITE, 22,
            anchor_x="center", anchor_y="center",
            bold=True
        )


class SettingsView(arcade.View):
    """Экран настроек"""

    def __init__(self):
        super().__init__()
        arcade.set_background_color((20, 25, 40))

        # Загружаем настройки
        self.settings = load_settings()

        # Кнопка камеры
        self.camera_button = ToggleButton(
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50,
            450, 60,
            "Камера следует за змейкой",
            (100, 100, 150),
            (130, 130, 200),
            (50, 200, 50)  # Зеленый когда активно
        )
        self.camera_button.is_active = self.settings.get(
            'camera_follow_snake', False)

        # Кнопка возврата в меню
        self.back_button = Button(
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100,
            300, 60,
            "НАЗАД",
            (150, 50, 50),
            (200, 70, 70)
        )

    def on_draw(self):
        """Отрисовка экрана настроек"""
        self.clear()

        # Заголовок
        arcade.draw_text(
            "НАСТРОЙКИ",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100,
            arcade.color.WHITE, 48,
            anchor_x="center", anchor_y="center",
            bold=True
        )

        # Кнопки
        self.camera_button.draw()
        self.back_button.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        """Обработка движения мыши"""
        self.camera_button.is_hovered = self.camera_button.contains_point(x, y)
        self.back_button.is_hovered = self.back_button.contains_point(x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        """Обработка нажатия мыши"""
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.camera_button.contains_point(x, y):
                # Переключаем состояние
                self.camera_button.is_active = not self.camera_button.is_active
                self.settings['camera_follow_snake'] = self.camera_button.is_active
                save_settings(self.settings)
            elif self.back_button.contains_point(x, y):
                menu_view = MainMenuView()
                self.window.show_view(menu_view)
