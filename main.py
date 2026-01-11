"""Главный файл запуска игры"""
import arcade
from menu import MainMenuView
from constants import SCREEN_WIDTH, SCREEN_HEIGHT


def main():
    """Главная функция"""
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, "Тетрис со змейкой")
    menu_view = MainMenuView()
    window.show_view(menu_view)
    arcade.run()


if __name__ == "__main__":
    main()
