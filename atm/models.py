"""Модели данных."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class Account:
    """Данные одного счёта банковской карты."""

    card_number: str
    pin_hash: str
    holder_name: str
    balance: float
    failed_attempts: int = 0
    locked: bool = False

    def to_dict(self) -> dict:
        """Преобразует счёт в словарь для сохранения в JSON."""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Account":
        """Создаёт Account из словаря, прочитанного из JSON."""
        return Account(
            card_number=data["card_number"],
            pin_hash=data["pin_hash"],
            holder_name=data["holder_name"],
            balance=float(data["balance"]),
            failed_attempts=int(data.get("failed_attempts", 0)),
            locked=bool(data.get("locked", False)),
        )

    def masked_card_number(self) -> str:
        """Возвращает номер карты со скрытой средней частью."""
        
        parts = self.card_number.split("-")
        if len(parts) <= 2:
            return self.card_number
        masked_middle = ["*" * len(p) for p in parts[1:-1]]
        return "-".join([parts[0], *masked_middle, parts[-1]])
