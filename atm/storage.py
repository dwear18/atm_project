"""Работа с файлами хранения данных (accounts.json, transactions.json)."""

import json
import os

from .models import Account


class StorageError(Exception):
    """Ошибка чтения/записи данных — используется, чтобы GUI мог
    показать пользователю понятное сообщение вместо трассировки."""


def load_accounts(path: str) -> list[Account]:
    """
    Загружает список счетов из JSON-файла.

    Если файл отсутствует или повреждён — поднимаем StorageError,
    а не даём программе упасть с необработанным исключением
    """
    if not os.path.exists(path):
        raise StorageError(f"Файл данных клиентов не найден: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        raise StorageError(f"Файл {path} повреждён и не может быть прочитан") from exc

    try:
        accounts = []

        for item in raw:
            account = Account.from_dict(item)
            accounts.append(account)
            
        return accounts
    
    except (KeyError, TypeError, ValueError) as exc:
        raise StorageError(f"Файл {path} имеет неверную структуру") from exc


def save_accounts(path: str, accounts: list[Account]) -> None:
    """Сохраняет список счетов в JSON-файл."""
    data = []

    for account in accounts:
        data.append(account.to_dict())
        
    _atomic_write(path, data)


def load_transactions(path: str) -> list[dict]:
    """Загружает журнал операций."""

    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise StorageError(f"Файл {path} повреждён и не может быть прочитан") from exc


def save_transactions(path: str, transactions: list[dict]) -> None:
    """Сохраняет журнал операций в JSON-файл."""
    _atomic_write(path, transactions)


def _atomic_write(path: str, data) -> None:
    """Записывает JSON через временный файл + os.replace."""
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)