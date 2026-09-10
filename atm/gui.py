"""Класс ATMApp — графический интерфейс банкомата на tkinter."""

import tkinter as tk
from tkinter import messagebox, ttk

from .atm_core import ATM, ATMError

FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_TEXT = ("Segoe UI", 11)
FONT_MONEY = ("Segoe UI", 22, "bold")


class ATMApp(tk.Tk):
    """Главное окно приложения и переключатель экранов."""

    def __init__(self, atm: ATM):
        super().__init__()
        self.atm = atm

        self.title("Симуляция банкомата")
        self.geometry("480x520")
        self.resizable(False, False)

        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        # Все экраны занимают одно и то же место в сетке — виден
        # только тот, что поднят наверх методом tkraise().
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames: dict[str, tk.Frame] = {}
        for FrameClass in (
            LoginScreen,
            MainMenuScreen,
            BalanceScreen,
            WithdrawScreen,
            DepositScreen,
            TransferScreen,
            HistoryScreen,
        ):
            frame = FrameClass(container, self)
            self.frames[FrameClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("LoginScreen")

    def show_frame(self, name: str) -> None:
        """Поднимает нужный экран наверх и обновляет его данные."""
        frame = self.frames[name]
        if hasattr(frame, "on_show"):
            frame.on_show()
        frame.tkraise()

    def logout(self) -> None:
        """Завершает сеанс и возвращает пользователя на экран входа."""
        self.atm.logout()
        self.show_frame("LoginScreen")


class BaseScreen(tk.Frame):
    """Общие удобства для экранов: доступ к app и atm, единый стиль."""

    def __init__(self, parent: tk.Frame, app: ATMApp):
        super().__init__(parent, padx=24, pady=24)
        self.app = app
        self.atm = app.atm

    def show_error(self, message: str) -> None:
        messagebox.showerror("Ошибка", message)

    def show_info(self, message: str) -> None:
        messagebox.showinfo("Готово", message)


class LoginScreen(BaseScreen):
    """Экран входа: номер карты + PIN-код."""

    def __init__(self, parent, app):
        super().__init__(parent, app)

        tk.Label(self, text="Вход в систему", font=FONT_TITLE).pack(pady=(0, 24))

        tk.Label(self, text="Номер карты", font=FONT_TEXT).pack(anchor="w")
        self.card_entry = tk.Entry(self, font=FONT_TEXT)
        self.card_entry.insert(0, "1234-5678-9012-3456")
        self.card_entry.pack(fill="x", pady=(0, 16))

        tk.Label(self, text="PIN-код", font=FONT_TEXT).pack(anchor="w")
        self.pin_entry = tk.Entry(self, font=FONT_TEXT, show="•")
        self.pin_entry.pack(fill="x", pady=(0, 24))
        self.pin_entry.bind("<Return>", lambda _event: self._submit())

        tk.Button(
            self, text="Войти", font=FONT_TEXT, command=self._submit
        ).pack(fill="x")

    def on_show(self) -> None:
        self.pin_entry.delete(0, tk.END)
        self.pin_entry.focus_set()

    def _submit(self) -> None:
        card_number = self.card_entry.get().strip()
        pin = self.pin_entry.get().strip()

        if not card_number or not pin:
            self.show_error("Введите номер карты и PIN-код")
            return

        try:
            self.atm.authenticate(card_number, pin)
        except ATMError as exc:
            self.show_error(str(exc))
            return

        self.app.show_frame("MainMenuScreen")


class MainMenuScreen(BaseScreen):
    """Главное меню банкомата с кнопками операций."""

    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.greeting_label = tk.Label(self, font=FONT_TITLE)
        self.greeting_label.pack(pady=(0, 24))

        buttons = (
            ("Проверить баланс", lambda: app.show_frame("BalanceScreen")),
            ("Снять наличные", lambda: app.show_frame("WithdrawScreen")),
            ("Внести наличные", lambda: app.show_frame("DepositScreen")),
            ("Перевести на другой счёт", lambda: app.show_frame("TransferScreen")),
            ("История операций", lambda: app.show_frame("HistoryScreen")),
        )
        for text, command in buttons:
            tk.Button(self, text=text, font=FONT_TEXT, command=command).pack(
                fill="x", pady=6
            )

        tk.Button(
            self,
            text="Завершить сеанс",
            font=FONT_TEXT,
            fg="white",
            bg="#c0392b",
            command=app.logout,
        ).pack(fill="x", pady=(24, 0))

    def on_show(self) -> None:
        account = self.atm.current_account
        self.greeting_label.config(
            text=f"Здравствуйте, {account.holder_name.split()[0]}!"
        )


class BalanceScreen(BaseScreen):
    """Экран проверки баланса."""

    def __init__(self, parent, app):
        super().__init__(parent, app)

        tk.Label(self, text="Баланс счёта", font=FONT_TITLE).pack(pady=(0, 24))
        self.holder_label = tk.Label(self, font=FONT_TEXT)
        self.holder_label.pack()
        self.card_label = tk.Label(self, font=FONT_TEXT)
        self.card_label.pack(pady=(0, 24))
        self.balance_label = tk.Label(self, font=FONT_MONEY)
        self.balance_label.pack()

        _back_button(self, app, "MainMenuScreen")

    def on_show(self) -> None:
        account = self.atm.current_account
        self.holder_label.config(text=account.holder_name)
        self.card_label.config(text=account.masked_card_number())
        self.balance_label.config(text=f"{account.balance:,.2f} ₽".replace(",", " "))


class WithdrawScreen(BaseScreen):
    """Экран снятия наличных."""

    def __init__(self, parent, app):
        super().__init__(parent, app)

        tk.Label(self, text="Снятие наличных", font=FONT_TITLE).pack(pady=(0, 16))
        tk.Label(
            self,
            text="Сумма от 100 до 100 000 ₽, кратная 5",
            font=FONT_TEXT,
            fg="#666666",
        ).pack(pady=(0, 8))

        self.amount_entry = tk.Entry(self, font=FONT_TEXT)
        self.amount_entry.pack(fill="x", pady=(0, 16))

        tk.Button(
            self, text="Снять", font=FONT_TEXT, command=self._submit
        ).pack(fill="x")

        _back_button(self, app, "MainMenuScreen")

    def on_show(self) -> None:
        self.amount_entry.delete(0, tk.END)

    def _submit(self) -> None:
        amount_text = self.amount_entry.get().strip()
        try:
            amount = float(amount_text)
        except ValueError:
            self.show_error("Введите корректную сумму")
            return

        try:
            breakdown = self.atm.withdraw(amount)
        except ATMError as exc:
            self.show_error(str(exc))
            return

        notes_text = "\n".join(
            f"{count} × {note} ₽" for note, count in breakdown.items()
        )
        self.show_info(f"Выдано {amount:.0f} ₽:\n{notes_text}")
        self.app.show_frame("MainMenuScreen")


class DepositScreen(BaseScreen):
    """Экран пополнения счёта."""

    def __init__(self, parent, app):
        super().__init__(parent, app)

        tk.Label(self, text="Пополнение счёта", font=FONT_TITLE).pack(pady=(0, 16))
        tk.Label(self, text="Сумма пополнения, ₽", font=FONT_TEXT).pack(anchor="w")

        self.amount_entry = tk.Entry(self, font=FONT_TEXT)
        self.amount_entry.pack(fill="x", pady=(0, 16))

        tk.Button(
            self, text="Внести", font=FONT_TEXT, command=self._submit
        ).pack(fill="x")

        _back_button(self, app, "MainMenuScreen")

    def on_show(self) -> None:
        self.amount_entry.delete(0, tk.END)

    def _submit(self) -> None:
        amount_text = self.amount_entry.get().strip()
        try:
            amount = float(amount_text)
        except ValueError:
            self.show_error("Введите корректную сумму")
            return

        try:
            self.atm.deposit(amount)
        except ATMError as exc:
            self.show_error(str(exc))
            return

        self.show_info(f"Счёт пополнен на {amount:.2f} ₽")
        self.app.show_frame("MainMenuScreen")


class TransferScreen(BaseScreen):
    """Экран перевода средств на другой счёт."""

    def __init__(self, parent, app):
        super().__init__(parent, app)

        tk.Label(self, text="Перевод средств", font=FONT_TITLE).pack(pady=(0, 16))

        tk.Label(self, text="Номер карты получателя", font=FONT_TEXT).pack(
            anchor="w"
        )
        self.recipient_entry = tk.Entry(self, font=FONT_TEXT)
        self.recipient_entry.pack(fill="x", pady=(0, 16))

        tk.Label(self, text="Сумма перевода, ₽", font=FONT_TEXT).pack(anchor="w")
        self.amount_entry = tk.Entry(self, font=FONT_TEXT)
        self.amount_entry.pack(fill="x", pady=(0, 16))

        tk.Button(
            self, text="Перевести", font=FONT_TEXT, command=self._submit
        ).pack(fill="x")

        _back_button(self, app, "MainMenuScreen")

    def on_show(self) -> None:
        self.recipient_entry.delete(0, tk.END)
        self.amount_entry.delete(0, tk.END)

    def _submit(self) -> None:
        recipient = self.recipient_entry.get().strip()
        amount_text = self.amount_entry.get().strip()
        try:
            amount = float(amount_text)
        except ValueError:
            self.show_error("Введите корректную сумму")
            return

        try:
            self.atm.transfer(recipient, amount)
        except ATMError as exc:
            self.show_error(str(exc))
            return

        self.show_info(f"Переведено {amount:.2f} ₽ на карту {recipient}")
        self.app.show_frame("MainMenuScreen")


class HistoryScreen(BaseScreen):
    """Экран истории операций."""

    def __init__(self, parent, app):
        super().__init__(parent, app)

        tk.Label(self, text="История операций", font=FONT_TITLE).pack(pady=(0, 16))

        columns = ("datetime", "type", "amount", "description")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        for col, title, width in (
            ("datetime", "Дата и время", 130),
            ("type", "Операция", 110),
            ("amount", "Сумма", 80),
            ("description", "Описание", 0),  # растянется автоматически
        ):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, stretch=(col == "description"))
        self.tree.pack(fill="both", expand=True, pady=(0, 16))

        _back_button(self, app, "MainMenuScreen")

    def on_show(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for record in self.atm.get_history():
            self.tree.insert(
                "",
                tk.END,
                values=(
                    record["datetime"],
                    record["type"],
                    f"{record['amount']:+.2f}",
                    record["description"],
                ),
            )


def _back_button(frame: tk.Frame, app: ATMApp, target: str) -> None:
    """Общая кнопка «Назад», используемая на всех операционных экранах."""
    tk.Button(
        frame, text="Назад", font=FONT_TEXT, command=lambda: app.show_frame(target)
    ).pack(fill="x", pady=(16, 0))
