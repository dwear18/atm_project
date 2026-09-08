"""Точка входа в программу «Симуляция банкомата»."""

import os
import tkinter as tk
from tkinter import messagebox

from atm.atm_core import ATM
from atm.constants import ACCOUNTS_FILE, TRANSACTIONS_FILE
from atm.gui import ATMApp
from atm.storage import StorageError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    accounts_path = os.path.join(BASE_DIR, ACCOUNTS_FILE)
    transactions_path = os.path.join(BASE_DIR, TRANSACTIONS_FILE)

    try:
        atm = ATM(accounts_path, transactions_path)
    except StorageError as exc:
        # Показываем ошибку в отдельном окне, а не в консоли — пользователь
        # запускает GUI-приложение и может не видеть терминал.
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Ошибка запуска", str(exc))
        root.destroy()
        return

    app = ATMApp(atm)
    app.mainloop()


if __name__ == "__main__":
    main()
