# Created: 2026-10-14 JST
"""First-run Saxo app credentials UI for the packaged Windows application.

The App Key and App Secret are *not* Saxo account login/password. They live only
in the current Windows user's Credential Manager. The Saxo account login stays
in the external browser, allowing ordinary password-manager autofill.
"""
from .saxo_auth import SaxoLoginRequired, credentials, get_keyring, save_credentials


def prompt_app_credentials(environment):
    """Return (app_key, app_secret) or None when the user cancels.

    Tk runs entirely on the dedicated login worker thread; it never shares a
    Tcl interpreter with pystray and never echoes or logs the App Secret.
    """
    import tkinter as tk
    from tkinter import messagebox, ttk

    window = tk.Tk()
    window.title("ChartRecorder - Saxo初期設定")
    window.resizable(False, False)
    window.geometry("500x260")
    result = {"credentials": None}
    key = tk.StringVar()
    secret = tk.StringVar()

    ttk.Label(
        window,
        text="Saxo OpenAPI アプリの初期設定",
        font=("", 11, "bold"),
    ).pack(anchor="w", padx=20, pady=(18, 5))
    ttk.Label(
        window,
        text=(
            f"接続環境: {environment.upper()}\n"
            "Saxo Developer PortalのApp KeyとApp Secretを入力してください。\n"
            "証券口座のログインID・パスワードではありません。"
        ),
        justify="left",
    ).pack(anchor="w", padx=20, pady=(0, 12))

    fields = ttk.Frame(window)
    fields.pack(fill="x", padx=20)
    ttk.Label(fields, text="App Key").grid(row=0, column=0, sticky="w", pady=5)
    key_entry = ttk.Entry(fields, textvariable=key, width=42)
    key_entry.grid(row=0, column=1, padx=(12, 0), pady=5)
    ttk.Label(fields, text="App Secret").grid(row=1, column=0, sticky="w", pady=5)
    secret_entry = ttk.Entry(fields, textvariable=secret, show="*", width=42)
    secret_entry.grid(row=1, column=1, padx=(12, 0), pady=5)

    ttk.Label(
        window,
        text="保存先: Windows資格情報マネージャー / ログインはブラウザで行います。",
    ).pack(anchor="w", padx=20, pady=(10, 3))

    def finish():
        app_key = key.get().strip()
        app_secret = secret.get().strip()
        if not app_key or not app_secret:
            messagebox.showwarning(
                "入力確認", "App KeyとApp Secretの両方を入力してください。",
                parent=window,
            )
            return
        result["credentials"] = (app_key, app_secret)
        secret.set("")
        window.destroy()

    def cancel():
        secret.set("")
        window.destroy()

    buttons = ttk.Frame(window)
    buttons.pack(side="bottom", anchor="e", padx=20, pady=15)
    ttk.Button(buttons, text="キャンセル", command=cancel).pack(side="left", padx=(0, 10))
    ttk.Button(buttons, text="保存してブラウザでログイン", command=finish).pack(side="left")
    window.protocol("WM_DELETE_WINDOW", cancel)
    window.after(0, key_entry.focus_set)
    window.mainloop()
    return result["credentials"]


def ensure_app_credentials(environment, vault=None, prompt=None):
    """Return True when saved credentials exist or are configured successfully.

    A canceled dialog must never launch a browser, store partial credentials,
    or write secrets into setting.yaml/GitHub/logs.
    """
    vault = vault if vault is not None else get_keyring()
    try:
        credentials(environment, vault)
        return True
    except SaxoLoginRequired:
        pass

    chooser = prompt if prompt is not None else prompt_app_credentials
    chosen = chooser(environment)
    if chosen is None:
        return False
    if not isinstance(chosen, (tuple, list)) or len(chosen) != 2:
        raise ValueError("Saxo App Key and App Secret are required")
    app_key, app_secret = chosen
    if not isinstance(app_key, str) or not isinstance(app_secret, str):
        raise ValueError("Saxo App Key and App Secret are required")
    app_key = app_key.strip()
    app_secret = app_secret.strip()
    if not app_key or not app_secret:
        raise ValueError("Saxo App Key and App Secret are required")
    save_credentials(environment, app_key, app_secret, vault)
    return True
