"""lec_async.sh kit proof-policy options (DIE-S81-85 11-09, COORD class fix): K/lec_options.json, not the launching
shell, sets OT_LEC_SUPERSET_VEC for the kit's LEC; a differing shell value is refused.
    python3 -m pytest -q tools/die_plan/test_lec_async_kit_options.py"""
import json
import os
import subprocess
from pathlib import Path

TOOL = Path(__file__).resolve().parent / "lec_async.sh"


def _kit(tmp_path, options=None):
    k = tmp_path / "kit"
    k.mkdir()
    (k / "lec.py").write_text("")
    if options is not None:
        (k / "lec_options.json").write_text(options if isinstance(options, str) else json.dumps(options))
    return k


def _identity(k, **env):
    e = {x: v for x, v in os.environ.items() if not x.startswith("OT_LEC_")}
    e.update(env)
    return subprocess.run(["bash", str(TOOL), "identity", str(k)], env=e, capture_output=True, text=True)


def test_kit_flag_equals_shell_flag(tmp_path):
    k = _kit(tmp_path, {"superset_vec": True})
    unset = _identity(k)
    shell = _identity(k, OT_LEC_SUPERSET_VEC="1")
    assert unset.returncode == 0 and shell.returncode == 0
    assert unset.stdout == shell.stdout  # the kit, not the shell, decides: same proof identity either way


def test_shell_differing_from_kit_refused(tmp_path):
    k = _kit(tmp_path, {"superset_vec": True})
    r = _identity(k, OT_LEC_SUPERSET_VEC="0")
    assert r.returncode == 11 and "proof policy differs" in r.stderr


def test_kit_false_and_no_file_unchanged(tmp_path):
    k = _kit(tmp_path)
    assert _identity(k).returncode == 0
    assert _identity(k, OT_LEC_SUPERSET_VEC="1").returncode == 0  # no kit record: shell behaviour as before
    k2 = _kit(tmp_path / "b", {"superset_vec": False}) if (tmp_path / "b").mkdir() is None else None
    assert _identity(k2).returncode == 0
    assert _identity(k2, OT_LEC_SUPERSET_VEC="1").returncode == 11


def test_invalid_options_refused(tmp_path):
    k = _kit(tmp_path, {"superset_vec": 1, "x": True})
    r = _identity(k)
    assert r.returncode == 11 and "lec_options.json invalid" in r.stderr
