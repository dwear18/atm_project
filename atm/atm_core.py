import hashlib
from datetime import datetime

from .constants import (
    BANKNOTES,
    MAX_PIN_ATTEMPTS,
    MAX_WITHDRAW_AMOUNT,
    MIN_WITHDRAW_AMOUNT,
)
from .models import Account
from .storage import (
    load_accounts,
    load_transactions,
    save_accounts,
    save_transactions,
)


class ATMError(Exception):
    """
    Ожидаемая, "штатная" ошибка операции банкомата (неверный PIN,
    недостаточно средств и т. п.).

    Отдельный класс исключения позволяет GUI отличать "пользователь
    ввёл что-то не то" (нужно показать messagebox) от настоящих багов
    программы (нужно упасть с трассировкой при разработке).
    """


def hash_pin(pin: str) -> str:
    """Возвращает SHA-256 хеш PIN-кода."""

    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


class ATM:
    """Логика операций банкомата: авторизация, снятие, внесение, перевод."""

    def __init__(self, accounts_path: str, transactions_path: str):
        # Загружаем счета и историю операций из JSON-файлов.
        self.accounts_path = accounts_path
        self.transactions_path = transactions_path
        self.accounts: list[Account] = load_accounts(accounts_path)
        self.transactions: list[dict] = load_transactions(transactions_path)
        self.current_account: Account | None = None

    # Авторизация

    def find_account(self, card_number: str) -> Account | None:
        for account in self.accounts:
            if account.card_number == card_number:
                return account

        return None

    def authenticate(self, card_number: str, pin: str) -> Account:
        """
        Проверяет номер карты и PIN-код.

        Если PIN правильный — выполняет вход и сохраняет текущий счёт.
        Если PIN неправильный — увеличивает счётчик ошибок.
        После MAX_PIN_ATTEMPTS карта блокируется.
        """
        account = self.find_account(card_number)
        if account is None:
            raise ATMError("Карта с таким номером не найдена")

        if account.locked:
            raise ATMError("Карта заблокирована. Обратитесь в банк")

        if account.pin_hash != hash_pin(pin):
            account.failed_attempts += 1

            if account.failed_attempts >= MAX_PIN_ATTEMPTS:
                account.locked = True
                message = (
                    "Неверный PIN-код. Карта заблокирована после "
                    f"{MAX_PIN_ATTEMPTS} неверных попыток"
                )
            else:
                remaining = MAX_PIN_ATTEMPTS - account.failed_attempts
                message = f"Неверный PIN-код. Осталось попыток: {remaining}"

            self._save_accounts()
            raise ATMError(message)

        account.failed_attempts = 0
        self._save_accounts()
        self.current_account = account
        return account

    def logout(self) -> None:
        """Завершает сеанс текущего пользователя (кнопка «Завершить сеанс»)."""
        self.current_account = None

    # Операции со счётом

    def get_balance(self) -> float:
        """Возвращает баланс текущего авторизованного счёта."""
        account = self._require_current_account()
        return account.balance

    def withdraw(self, amount: float) -> dict[int, int]:
        """
        Снимает наличные с текущего счёта.
        """
        account = self._require_current_account()
        self._validate_withdraw_amount(amount, account.balance)

        # Определяем, какими купюрами банкомат сможет выдать сумму.
        breakdown = self._banknote_breakdown(int(amount))
        if breakdown is None:
            raise ATMError(
                "Сумму невозможно выдать доступными купюрами номиналом "
                + ", ".join(f"{b} ₽" for b in BANKNOTES)
            )

        account.balance -= amount
        self._save_accounts()
        self._log_transaction(
            account.card_number,
            "Снятие наличных",
            -amount,
            f"Снятие {amount:.2f} ₽",
        )
        return breakdown

    def deposit(self, amount: float) -> None:
        """Вносит наличные на текущий счёт."""
        account = self._require_current_account()
        if amount <= 0:
            raise ATMError("Сумма пополнения должна быть положительным числом")

        account.balance += amount
        self._save_accounts()
        self._log_transaction(
            account.card_number,
            "Пополнение счёта",
            amount,
            f"Пополнение на {amount:.2f} ₽",
        )

    def transfer(self, recipient_card_number: str, amount: float) -> None:
        """Переводит деньги между двумя существующими счетами."""
        account = self._require_current_account()

        if amount <= 0:
            raise ATMError("Сумма перевода должна быть положительным числом")

        if recipient_card_number == account.card_number:
            raise ATMError("Нельзя перевести средства самому себе")

        recipient = self.find_account(recipient_card_number)
        if recipient is None:
            raise ATMError("Карта получателя не найдена")

        if amount > account.balance:
            raise ATMError("Недостаточно средств на счёте")

        account.balance -= amount
        recipient.balance += amount
        self._save_accounts()

        self._log_transaction(
            account.card_number,
            "Перевод (исходящий)",
            -amount,
            f"Перевод на карту {recipient.masked_card_number()}: {amount:.2f} ₽",
        )
        self._log_transaction(
            recipient.card_number,
            "Перевод (входящий)",
            amount,
            f"Перевод от карты {account.masked_card_number()}: {amount:.2f} ₽",
        )

    def get_history(self) -> list[dict]:
        """Возвращает историю операций текущего пользователя, новые сверху."""
        account = self._require_current_account()
        own_transactions = []

        for transaction in self.transactions:
            if transaction["card_number"] == account.card_number:
                own_transactions.append(transaction)

        own_transactions.reverse()
        return own_transactions

    # Внутренние вспомогательные методы

    def _require_current_account(self) -> Account:
        """Проверяет, что пользователь авторизован, и возвращает его счёт."""
        if self.current_account is None:
            raise ATMError("Нет активной сессии. Пройдите авторизацию")
        return self.current_account

    @staticmethod
    def _validate_withdraw_amount(amount: float, balance: float) -> None:
        # Сумма должна быть целым числом рублей — банкомат не выдаёт копейки
        if amount != int(amount):
            raise ATMError("Сумма снятия должна быть целым числом рублей")

        if amount < MIN_WITHDRAW_AMOUNT:
            raise ATMError(f"Минимальная сумма снятия — {MIN_WITHDRAW_AMOUNT} ₽")

        if amount > MAX_WITHDRAW_AMOUNT:
            raise ATMError(
                f"Максимальная сумма снятия за одну операцию — "
                f"{MAX_WITHDRAW_AMOUNT} ₽"
            )

        if amount > balance:
            raise ATMError("Недостаточно средств на счёте")

    @staticmethod
    def _banknote_breakdown(amount: int) -> dict[int, int] | None:
        """
        Раскладывает сумму на доступные номиналы купюр.

        Перебирает купюры от большего номинала к меньшему и
        берёт максимально возможное количество каждой купюры.
        Возвращает None, если сумму нельзя выдать без остатка.
        """
        remaining = amount
        breakdown: dict[int, int] = {}
        for note in BANKNOTES:
            count, remaining = divmod(remaining, note)
            if count:
                breakdown[note] = count
        if remaining != 0:
            return None
        return breakdown

    def _log_transaction(
        self, card_number: str, operation_type: str, amount: float, description: str
    ) -> None:
        """Добавляет запись об операции в историю и сохраняет её в файл."""
        transaction = {
            "card_number": card_number,
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": operation_type,
            "amount": round(amount, 2),
            "description": description,
        }

        self.transactions.append(transaction)
        self._save_transactions()

    def _save_accounts(self) -> None:
        save_accounts(self.accounts_path, self.accounts)

    def _save_transactions(self) -> None:
        save_transactions(self.transactions_path, self.transactions)