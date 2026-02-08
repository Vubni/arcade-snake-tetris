"""Главный файл запуска игры"""
from constants import SCREEN_WIDTH, SCREEN_HEIGHT
from menu import MainMenuView
import arcade
import warnings
warnings.filterwarnings("ignore", message=".*draw_text.*")


def main():
    """Главная функция"""
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT,
                           "Тетрис со змейкой", draw_rate=1/60.0)
    window.set_update_rate(1 / 60.0)
    menu_view = MainMenuView()
    window.show_view(menu_view)
    arcade.run()


if __name__ == "__main__":
    main()
