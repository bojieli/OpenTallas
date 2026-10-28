"""bind.py: bind_latency.json reset meta must not crash when a failed bind never wrote bind_reset.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402


def test_no_wavefront_no_reset(tmp_path):
    assert bind._reset_latency_meta(tmp_path, False) == {}


def test_wavefront_missing_file_is_recorded_not_raised(tmp_path):
    m = bind._reset_latency_meta(tmp_path, True)
    assert set(m) == {"reset"} and "missing" in m["reset"]


def test_wavefront_file_is_read(tmp_path):
    W = {"parts": ["p0"], "stages": 3}
    (tmp_path / "bind_reset.json").write_text(json.dumps(W))
    assert bind._reset_latency_meta(tmp_path, True) == {"reset": W}
