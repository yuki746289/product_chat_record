# Created: 2026-10-14 JST
"""Packaged-first-run Saxo credential tests without Internet or real secrets."""
import threading
from types import SimpleNamespace
from unittest.mock import Mock

from src import saxo_first_run, tray_app
from src.saxo_auth import credentials, SaxoLoginRequired


class FakeVault:
    def __init__(self):
        self.data = {}
        self.writes = []

    def get_password(self, service, name):
        return self.data.get((service, name))

    def set_password(self, service, name, value):
        self.writes.append((service, name))
        self.data[(service, name)] = value


def test_fresh_pc_prompts_app_key_secret_and_saves_only_to_vault():
    vault = FakeVault()
    asked = []
    assert saxo_first_run.ensure_app_credentials(
        "sim", vault=vault,
        prompt=lambda env: asked.append(env) or ("MY_APP_KEY", "TEST_ONLY_SECRET"),
    )
    assert asked == ["sim"]
    assert credentials("sim", vault) == ("MY_APP_KEY", "TEST_ONLY_SECRET")
    assert len(vault.writes) == 2
    assert all(service == "ChartRecorder.SaxoOpenAPI.sim" for service, _ in vault.writes)


def test_existing_credentials_skip_gui_and_keep_original_credentials():
    vault = FakeVault()
    vault.set_password("ChartRecorder.SaxoOpenAPI.sim", "app_key", "SAVED_KEY")
    vault.set_password("ChartRecorder.SaxoOpenAPI.sim", "app_secret", "SAVED_SECRET")
    prompts = Mock(side_effect=AssertionError("must not prompt existing user"))
    assert saxo_first_run.ensure_app_credentials("sim", vault=vault, prompt=prompts)
    assert vault.data[("ChartRecorder.SaxoOpenAPI.sim", "app_secret")] == "SAVED_SECRET"
    assert len(vault.writes) == 2
    prompts.assert_not_called()


def test_cancel_never_saves_partial_vault_data():
    vault = FakeVault()
    assert not saxo_first_run.ensure_app_credentials("sim", vault=vault, prompt=lambda _: None)
    assert vault.writes == []
    assert vault.data == {}


def test_blank_or_invalid_credentials_never_saved():
    for given in [("", "secret"), ("key", ""), ([],), ("key", None), (None, "secret")]:
        vault = FakeVault()
        try:
            saxo_first_run.ensure_app_credentials("sim", vault=vault, prompt=lambda _: given)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid app credentials must be rejected")
        assert vault.writes == []


def make_login_controller():
    app = tray_app.TrayController.__new__(tray_app.TrayController)
    app.config_path = "unused.yaml"
    app.logger = Mock()
    app.icon = None
    app.status = "起動中"
    app.paused = True
    app.login_required = True
    app.login_in_progress = True
    app.auth_notice_sent = True
    app.wake = threading.Event()
    app.mode = "saxo_local"
    return app


def test_first_run_sets_up_vault_before_browser_and_resumes(monkeypatch):
    events = []
    app = make_login_controller()
    monkeypatch.setattr(tray_app, "load_settings", lambda _: {"saxo": {"environment": "sim"}})
    monkeypatch.setattr(tray_app, "ensure_app_credentials", lambda env: events.append(("vault", env)) or True)
    monkeypatch.setattr(tray_app, "SaxoSession", lambda cfg: SimpleNamespace(
        sign_in_interactively=lambda: events.append(("browser", cfg["saxo"]["environment"]))
    ))
    app._run_saxo_login()
    assert events == [("vault", "sim"), ("browser", "sim")]
    assert app.status.startswith("Saxo認証完了")
    assert not app.login_required
    assert not app.login_in_progress
    assert not app.paused
    assert app.wake.is_set()


def test_canceled_first_run_keeps_login_required_without_opening_browser(monkeypatch):
    app = make_login_controller()
    monkeypatch.setattr(tray_app, "load_settings", lambda _: {"saxo": {"environment": "sim"}})
    monkeypatch.setattr(tray_app, "ensure_app_credentials", lambda env: False)
    session = Mock(side_effect=AssertionError("browser must not open after cancel"))
    monkeypatch.setattr(tray_app, "SaxoSession", session)
    app._run_saxo_login()
    assert app.login_required
    assert not app.login_in_progress
    assert app.wake.is_set()
    assert "キャンセル" in app.status
    session.assert_not_called()


def test_environment_vaults_are_isolated():
    vault = FakeVault()
    assert saxo_first_run.ensure_app_credentials(
        "sim", vault=vault, prompt=lambda _: ("SIM_KEY", "SIM_SECRET")
    )
    with __import__("pytest").raises(SaxoLoginRequired):
        credentials("live", vault)


def test_new_packaged_pc_triggers_first_run_from_tray(monkeypatch):
    app = make_login_controller()
    app.login_in_progress = False
    app.stopping = threading.Event()
    calls = []
    app.start_saxo_login = lambda icon, item: calls.append("first-run-dialog")
    monkeypatch.setattr(tray_app, "load_settings", lambda _: {"saxo": {"environment": "sim"}})
    monkeypatch.setattr(tray_app, "credentials", Mock(side_effect=SaxoLoginRequired("missing")))
    app._prompt_initial_saxo_setup()
    assert calls == ["first-run-dialog"]


def test_existing_saxo_app_credentials_do_not_trigger_initial_dialog(monkeypatch):
    app = make_login_controller()
    app.login_in_progress = False
    app.stopping = threading.Event()
    app.start_saxo_login = Mock()
    monkeypatch.setattr(tray_app, "load_settings", lambda _: {"saxo": {"environment": "sim"}})
    monkeypatch.setattr(tray_app, "credentials", Mock(return_value=("EXISTING_KEY", "EXISTING_SECRET")))
    app._prompt_initial_saxo_setup()
    app.start_saxo_login.assert_not_called()


def test_first_run_does_not_popup_during_shutdown(monkeypatch):
    app = make_login_controller()
    app.login_in_progress = False
    app.stopping = threading.Event()
    app.stopping.set()
    app.start_saxo_login = Mock()
    monkeypatch.setattr(tray_app, "load_settings", Mock(side_effect=AssertionError("should not load")))
    app._prompt_initial_saxo_setup()
    app.start_saxo_login.assert_not_called()
