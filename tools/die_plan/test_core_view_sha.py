"""KIT-OPS-6 11-14: a kit takes a hard core's signed view by sha (TYPE-HDEPC: hd_host_e on the 11-10 u_epc lib)."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_view_sha as CV  # noqa: E402


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def test_stale_lib_fails_closed_signed_lib_passes(tmp_path):
    old, new = tmp_path / "old.lib", tmp_path / "new.lib"
    old.write_bytes(b"lib old 8aad87")
    new.write_bytes(b"lib signed f663e3")
    core = {"module": "ot_s81hd_he_epc", "lib": "old.lib"}
    exp = {"ot_s81hd_he_epc": {"_tt.lib": _sha(new.read_bytes())}}
    res = lambda p: tmp_path / p  # noqa: E731
    with pytest.raises(ValueError, match="STALE-CORE-VIEW ot_s81hd_he_epc"):
        CV.gate(core, res, exp)
    CV.gate(dict(core, lib="new.lib"), res, exp)


def test_plan_declared_sha_and_default_unchanged(tmp_path):
    f = tmp_path / "c.lef"
    f.write_bytes(b"lef")
    res = lambda p: tmp_path / p  # noqa: E731
    CV.gate({"module": "m", "lef": "c.lef"}, res, None)                       # nothing declared: unchanged
    CV.gate({"module": "m", "lef": "c.lef", "lef_sha256": _sha(b"lef")}, res, {})
    with pytest.raises(ValueError):
        CV.gate({"module": "m", "lef": "c.lef", "lef_sha256": _sha(b"other")}, res, {})


def test_env_table(tmp_path, monkeypatch):
    t = tmp_path / "t.json"
    t.write_text(json.dumps({"m": {".lef": "x"}}))
    monkeypatch.setenv("OT_SIGNED_VIEW_SHA", str(t))
    assert CV.load_expected() == {"m": {".lef": "x"}}


def test_gen_phys_hooks_the_gate():
    s = (Path(__file__).resolve().parent / "gen_phys.py").read_text()
    assert "import core_view_sha" in s and "STALE-CORE-VIEW" in (Path(__file__).resolve().parent / "core_view_sha.py").read_text()
    assert "_CVS.gate(c, _CR.resolve" in s
