"""Система частиц для эффектов"""
import arcade
import random
import math
from constants import MARGIN, CELL_SIZE


class Particle:
    """Одна частица"""

    def __init__(self, x, y, color, velocity_x=0, velocity_y=0, lifetime=1.0, size=5):
        self.x = x
        self.y = y
        self.color = color
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = size
        self.alpha = 255

    def update(self, delta_time):
        """Обновление частицы"""
        self.x += self.velocity_x * delta_time
        self.y += self.velocity_y * delta_time
        self.lifetime -= delta_time
        # Уменьшаем альфа-канал со временем
        self.alpha = int(255 * (self.lifetime / self.max_lifetime))
        # Гравитация
        self.velocity_y -= 200 * delta_time

    def is_alive(self):
        """Проверяет, жива ли частица"""
        return self.lifetime > 0 and self.alpha > 0

    def draw(self):
        """Отрисовка частицы"""
        if self.alpha > 0:
            color_with_alpha = (*self.color[:3], self.alpha)
            arcade.draw_circle_filled(
                self.x, self.y, self.size, color_with_alpha
            )


class ParticleSystem:
    """Система частиц"""

    def __init__(self):
        self.particles = []

    def add_explosion(self, x, y, color, count=20):
        """Добавляет взрыв частиц"""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 200)
            velocity_x = math.cos(angle) * speed
            velocity_y = math.sin(angle) * speed
            lifetime = random.uniform(0.5, 1.5)
            size = random.randint(3, 8)
            particle = Particle(x, y, color, velocity_x,
                                velocity_y, lifetime, size)
            self.particles.append(particle)

    def add_line_clear_particles(self, x, y, color, count=15):
        """Добавляет частицы при очистке линии"""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(30, 100)
            velocity_x = math.cos(angle) * speed
            velocity_y = math.sin(angle) * speed
            lifetime = random.uniform(0.3, 0.8)
            size = random.randint(2, 6)
            particle = Particle(x, y, color, velocity_x,
                                velocity_y, lifetime, size)
            self.particles.append(particle)

    def add_apple_particles(self, x, y, count=10):
        """Добавляет частицы при съедании яблока"""
        color = (255, 50, 50)  # Красный
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(40, 120)
            velocity_x = math.cos(angle) * speed
            velocity_y = math.sin(angle) * speed
            lifetime = random.uniform(0.4, 1.0)
            size = random.randint(2, 5)
            particle = Particle(x, y, color, velocity_x,
                                velocity_y, lifetime, size)
            self.particles.append(particle)

    def update(self, delta_time):
        """Обновление всех частиц"""
        for particle in self.particles[:]:
            particle.update(delta_time)
            if not particle.is_alive():
                self.particles.remove(particle)

    def draw(self):
        """Отрисовка всех частиц"""
        for particle in self.particles:
            particle.draw()

    def clear(self):
        """Очищает все частицы"""
        self.particles.clear()
