"""Regression coverage for configurable ChartRecorder chart settings."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from src.chart import render_pair
from src.config import EXPECTED_TIMEFRAMES, load_settings
from src.local_monitor import clean_local_images, parse_chart_stamp
from src.providers import DemoProvider
from src import saxo_local


ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path, **chart_changes):
    cfg = yaml.safe_load((ROOT / "setting.yaml").read_text(encoding="utf-8"))
    cfg["chart"].update(chart_changes)
    cfg["output"]["local_dir"] = str(tmp_path / "captures")
    path = tmp_path / "setting.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return path


def test_default_layout_still_has_nine_frames():
    cfg = load_settings(ROOT / "setting.yaml")
    assert cfg["chart"]["timeframes"] == list(EXPECTED_TIMEFRAMES)
    assert cfg["chart"]["columns"] == 2
    assert cfg["chart"]["ema"] == [20, 30, 40]
    assert cfg["chart"]["rci"] == [9, 14, 26]


def test_user_defined_timeframes_periods_columns_and_theme(tmp_path):
    path = _settings(
        tmp_path, timeframes=["1D", "5M", "1H"], ema=[3, 8, 13, 21],
        rci=[4, 7], columns=3, theme="light", bars=55, history_bars=110,
        figsize=[9, 9], dpi=45,
    )
    cfg = load_settings(path)
    assert cfg["chart"]["timeframes"] == ["1D", "5M", "1H"]
    assert cfg["chart"]["ema"] == [3, 8, 13, 21]
    assert cfg["chart"]["columns"] == 3
    bars = {
        tf: DemoProvider().get("FX:USDJPY", tf, cfg["chart"]["history_bars"])
        for tf in cfg["chart"]["timeframes"]
    }
    result = render_pair(
        bars, "USDJPY", tmp_path / "variable.png", cfg, "20261019_1100",
        demo=True,
    )
    assert result.is_file()
    assert result.stat().st_size > 1000


def test_one_timeframe_and_single_column(tmp_path, monkeypatch):
    from matplotlib.axes import Axes

    recorded = []
    original_text = Axes.text

    def capture_text(self, x, y, text, *args, **kwargs):
        recorded.append(str(text))
        return original_text(self, x, y, text, *args, **kwargs)

    monkeypatch.setattr(Axes, "text", capture_text)
    path = _settings(
        tmp_path, timeframes=["1H"], ema=[20], rci=[9],
        columns=1, bars=45, history_bars=100, figsize=[7, 8], dpi=40,
    )
    cfg = load_settings(path)
    bars = {"1H": DemoProvider().get("FX:USDJPY", "1H", 100)}
    assert render_pair(
        bars, "USDJPY", tmp_path / "single.png", cfg, "20261019_1200", demo=True
    ).is_file()
    assert any("TIMEFRAMES       1" in text for text in recorded)
    assert not any("8H BAR" in text for text in recorded)


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"timeframes": []}, "timeframes"),
        ({"timeframes": ["1H", "1H"]}, "duplicates"),
        ({"timeframes": ["2H"]}, "timeframes"),
        ({"columns": 0}, "columns"),
        ({"ema": []}, "ema"),
        ({"rci": [1]}, "rci"),
        ({"rci": [9, 9]}, "duplicates"),
        ({"theme": "unknown"}, "theme"),
        ({"history_bars": 50}, "history_bars"),
        ({"dpi": 0}, "dpi"),
        ({"figsize": [10, -1]}, "figsize"),
        ({"right_padding_bars": -1}, "right_padding_bars"),
    ],
)
def test_invalid_settings_fail_with_specific_field(tmp_path, changes, message):
    with pytest.raises(ValueError, match=message):
        load_settings(_settings(tmp_path, **changes))


def test_saxo_fetches_selected_frames_without_freshness_request_when_disabled(
    tmp_path, monkeypatch
):
    path = _settings(tmp_path, timeframes=["1D", "5M"], columns=1)
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg["symbols"] = cfg["symbols"][:1]
    cfg["market"]["skip_stale"] = False
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    class FakeSource:
        session = SimpleNamespace(access_token=lambda: "FAKE")

        def __init__(self):
            self.calls = []

        def get(self, pair, timeframe, count):
            self.calls.append((pair, timeframe))
            return DemoProvider().get("FX:" + pair, timeframe, count)

    provider = FakeSource()

    def fake_render(bars, pair, dest, *args, **kwargs):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"PNG")
        return dest

    monkeypatch.setattr(saxo_local, "render_pair", fake_render)
    paths = saxo_local.tick_once(
        path, now=datetime(2026, 10, 19, tzinfo=timezone.utc), provider=provider,
    )
    assert len(paths) == 1
    assert provider.calls == [("GBPAUD", "1D"), ("GBPAUD", "5M")]


def test_custom_folder_format_retention(tmp_path):
    now = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)
    fmt = "%Y-%m-%d_%H-%M"
    for dt in (now - timedelta(minutes=10), now - timedelta(minutes=5)):
        folder = tmp_path / dt.strftime(fmt)
        folder.mkdir()
        (folder / "USDJPY.png").write_bytes(b"PNG")
    unknown = tmp_path / "not_a_snapshot"
    unknown.mkdir()
    (unknown / "USDJPY.png").write_bytes(b"PNG")
    assert parse_chart_stamp("2026-10-19_09-55", "Etc/UTC", fmt) is not None
    deleted = clean_local_images(tmp_path, now, 1, "Etc/UTC", fmt)
    assert len(deleted) == 1
    assert unknown.exists()


def test_config_rejects_invalid_folder_formats(tmp_path):
    path = _settings(tmp_path)
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg["output"]["folder_format"] = "%Y%m%d"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    with pytest.raises(ValueError, match="output.folder_format"):
        load_settings(path)


def test_custom_folder_format_github_artifact_detection(tmp_path):
    from src.local_monitor import _find_artifact_batch, PNG_HEADER

    fmt = "%Y-%m-%d_%H-%M"
    batch = tmp_path / "2026-10-19_10-00"
    category = batch / "cross_jpy"
    category.mkdir(parents=True)
    path = category / "USDJPY.png"
    path.write_bytes(PNG_HEADER)
    discovered, files = _find_artifact_batch(tmp_path, ["USDJPY"], "Etc/UTC", fmt)
    assert discovered == batch
    assert files == [path]


def test_demo_8h_without_displaying_4h(tmp_path):
    from src.main import generate

    path = _settings(tmp_path, timeframes=["8H"], columns=1, bars=42,
                     history_bars=100, dpi=40, figsize=[7, 8])
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg["symbols"] = cfg["symbols"][:1]
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    files = generate(path, timestamp="20261019_1000", demo=True,
                     output_override=tmp_path / "output")
    assert len(files) == 1
    assert files[0].is_file()
