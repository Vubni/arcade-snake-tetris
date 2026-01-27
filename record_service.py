"""Сервис для работы с рекордами через сервер.

Требования:
- Никаких дополнительных зависимостей (используем стандартную библиотеку).
- Не блокировать игровой цикл (сетевые вызовы только в отдельных потоках).
- Быть устойчивым к отсутствию соединения/ошибкам сервера.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Optional


RECORD_GET_URL = "https://snake.vubni.com/record"
RECORD_POST_URL = "https://snake.vubni.com/new_record"

# Маленькие таймауты, чтобы даже при зависшем соединении поток быстро завершался
DEFAULT_TIMEOUT_SECONDS = 2.5


def _parse_record_response(body: bytes) -> Optional[int]:
    """Пытается вытащить рекорд из ответа сервера.

    Поддерживаем несколько форматов на всякий случай:
    - JSON: {"record": 123} / {"high_score": 123} / {"value": 123} / 123
    - plain text: "123" / "123\n"
    """
    if not body:
        return None

    # Декодируем в текст
    try:
        text = body.decode("utf-8", errors="ignore").strip()
    except Exception:
        return None

    if not text:
        return None

    # Сначала пробуем JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            # Пробуем разные ключи
            for key in ("record", "high_score", "score", "value", "result", "data"):
                value = data.get(key)
                if isinstance(value, int) and value >= 0:
                    return value
                if isinstance(value, str) and value.strip().isdigit():
                    return int(value.strip())
            # Если не нашли по ключам, пробуем взять первое числовое значение
            for value in data.values():
                if isinstance(value, int) and value >= 0:
                    return value
                if isinstance(value, str) and value.strip().isdigit():
                    return int(value.strip())
        if isinstance(data, int) and data >= 0:
            return data
        if isinstance(data, str) and data.strip().isdigit():
            val = int(data.strip())
            if val >= 0:
                return val
    except (json.JSONDecodeError, ValueError):
        pass
    except Exception:
        pass

    # Потом пробуем plain text (просто число)
    try:
        # Убираем все пробелы и переносы строк
        clean_text = text.strip().replace(" ", "").replace("\n", "").replace("\r", "")
        if clean_text.isdigit():
            val = int(clean_text)
            if val >= 0:
                return val
    except Exception:
        pass

    return None


def fetch_record(timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> Optional[int]:
    """Синхронно запрашивает рекорд с сервера. Возвращает int или None."""
    print(f"[Сервер] Запрос рекорда с {RECORD_GET_URL}...")
    try:
        req = urllib.request.Request(
            RECORD_GET_URL,
            method="GET",
            headers={
                "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
                "User-Agent": "arcade-snake-tetris",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            # Проверяем статус код
            status_code = resp.getcode()
            print(f"[Сервер] Получен ответ: статус {status_code}")
            if status_code != 200:
                print(f"[Сервер] Ошибка: неверный статус код {status_code}")
                return None
            body = resp.read()
            print(f"[Сервер] Получено {len(body)} байт данных")
        result = _parse_record_response(body)
        if result is not None:
            print(f"[Сервер] Рекорд успешно получен: {result}")
        else:
            print(f"[Сервер] Не удалось распарсить ответ сервера")
        return result
    except urllib.error.HTTPError as e:
        # HTTP ошибка (404, 500 и т.д.)
        print(f"[Сервер] HTTP ошибка при получении рекорда: {e.code} {e.reason}")
        return None
    except urllib.error.URLError as e:
        # Ошибка сети (таймаут, DNS и т.д.)
        print(f"[Сервер] Ошибка сети при получении рекорда: {e.reason}")
        return None
    except Exception as e:
        # Любая другая ошибка
        print(f"[Сервер] Неожиданная ошибка при получении рекорда: {type(e).__name__}: {e}")
        return None


def post_record(
    record: int, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
) -> bool:
    """Синхронно отправляет новый рекорд. True если запрос прошёл без исключений."""
    if not isinstance(record, int):
        print(f"[Сервер] Ошибка: неверный тип рекорда для отправки: {type(record)}")
        return False
    if record < 0:
        print(f"[Сервер] Ошибка: отрицательный рекорд для отправки: {record}")
        return False

    print(f"[Сервер] Отправка рекорда {record} на {RECORD_POST_URL}...")
    
    # Основной вариант: JSON body {"record": <int>}
    payload_json = json.dumps({"record": record}).encode("utf-8")
    req_json = urllib.request.Request(
        RECORD_POST_URL,
        data=payload_json,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
            "User-Agent": "arcade-snake-tetris",
        },
    )

    try:
        with urllib.request.urlopen(req_json, timeout=timeout_seconds) as resp:
            status_code = resp.getcode()
            body = resp.read()
            print(f"[Сервер] Рекорд отправлен успешно: статус {status_code}, ответ: {len(body)} байт")
        return True
    except urllib.error.HTTPError as e:
        print(f"[Сервер] HTTP ошибка при отправке рекорда (JSON): {e.code} {e.reason}")
        # Фолбэк: отправка как form-urlencoded "record=<int>"
        try:
            print(f"[Сервер] Попытка отправить рекорд как form-urlencoded...")
            payload_form = urllib.parse.urlencode({"record": record}).encode("utf-8")
            req_form = urllib.request.Request(
                RECORD_POST_URL,
                data=payload_form,
                method="POST",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                    "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
                    "User-Agent": "arcade-snake-tetris",
                },
            )
            with urllib.request.urlopen(req_form, timeout=timeout_seconds) as resp:
                status_code = resp.getcode()
                body = resp.read()
                print(f"[Сервер] Рекорд отправлен успешно (form): статус {status_code}, ответ: {len(body)} байт")
            return True
        except urllib.error.HTTPError as e2:
            print(f"[Сервер] HTTP ошибка при отправке рекорда (form): {e2.code} {e2.reason}")
            return False
        except urllib.error.URLError as e2:
            print(f"[Сервер] Ошибка сети при отправке рекорда (form): {e2.reason}")
            return False
        except Exception as e2:
            print(f"[Сервер] Неожиданная ошибка при отправке рекорда (form): {type(e2).__name__}: {e2}")
            return False
    except urllib.error.URLError as e:
        print(f"[Сервер] Ошибка сети при отправке рекорда (JSON): {e.reason}")
        # Фолбэк: отправка как form-urlencoded "record=<int>"
        try:
            print(f"[Сервер] Попытка отправить рекорд как form-urlencoded...")
            payload_form = urllib.parse.urlencode({"record": record}).encode("utf-8")
            req_form = urllib.request.Request(
                RECORD_POST_URL,
                data=payload_form,
                method="POST",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                    "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
                    "User-Agent": "arcade-snake-tetris",
                },
            )
            with urllib.request.urlopen(req_form, timeout=timeout_seconds) as resp:
                status_code = resp.getcode()
                body = resp.read()
                print(f"[Сервер] Рекорд отправлен успешно (form): статус {status_code}, ответ: {len(body)} байт")
            return True
        except Exception as e2:
            print(f"[Сервер] Неожиданная ошибка при отправке рекорда (form): {type(e2).__name__}: {e2}")
            return False
    except Exception as e:
        print(f"[Сервер] Неожиданная ошибка при отправке рекорда (JSON): {type(e).__name__}: {e}")
        # Фолбэк: отправка как form-urlencoded "record=<int>"
        try:
            print(f"[Сервер] Попытка отправить рекорд как form-urlencoded...")
            payload_form = urllib.parse.urlencode({"record": record}).encode("utf-8")
            req_form = urllib.request.Request(
                RECORD_POST_URL,
                data=payload_form,
                method="POST",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                    "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
                    "User-Agent": "arcade-snake-tetris",
                },
            )
            with urllib.request.urlopen(req_form, timeout=timeout_seconds) as resp:
                status_code = resp.getcode()
                body = resp.read()
                print(f"[Сервер] Рекорд отправлен успешно (form): статус {status_code}, ответ: {len(body)} байт")
            return True
        except Exception as e2:
            print(f"[Сервер] Неожиданная ошибка при отправке рекорда (form): {type(e2).__name__}: {e2}")
            return False


def fetch_record_async(
    on_result: Callable[[Optional[int]], None],
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """Запрашивает рекорд в фоне и вызывает callback с результатом (int или None)."""

    def _worker():
        result = fetch_record(timeout_seconds=timeout_seconds)
        try:
            on_result(result)
        except Exception:
            # Никогда не даём исключению из callback убить поток
            pass

    threading.Thread(target=_worker, daemon=True).start()


def post_record_async(
    record: int,
    on_done: Optional[Callable[[bool], None]] = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """Отправляет рекорд в фоне. Если указан on_done, вызовет его с True/False."""

    def _worker():
        ok = post_record(record, timeout_seconds=timeout_seconds)
        if on_done:
            try:
                on_done(ok)
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True).start()

