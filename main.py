"""Главный файл запуска игры"""
import warnings
# Подавляем предупреждение о медленном draw_text
warnings.filterwarnings("ignore", message=".*draw_text.*")

import arcade
# Примечание: Ошибка "Unable to load version number via VERSION" при запуске .exe
# не критична и не влияет на работу игры. Она возникает из-за особенностей
# работы PyInstaller с ресурсами arcade, но игра функционирует нормально.
from menu import MainMenuView
from constants import SCREEN_WIDTH, SCREEN_HEIGHT


def main():
    """Главная функция"""
    # Ограничиваем частоту отрисовки до 60 FPS для предотвращения лагов при перетаскивании окна
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT,
                           "Тетрис со змейкой", draw_rate=1/60.0)
    # Ограничиваем частоту обновления до 60 FPS для стабильной производительности
    window.set_update_rate(1 / 60.0)
    menu_view = MainMenuView()
    window.show_view(menu_view)
    arcade.run()


if __name__ == "__main__":
    main()
