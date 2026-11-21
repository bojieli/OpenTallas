import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import lef_override as L


def setup(tmp_path, monkeypatch, base="BASE\n", new="NEW\n"):
    d = tmp_path / "ov"; d.mkdir()
    (d / "m.lef").write_text(new)
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
    (d / "map.json").write_text(json.dumps({"m.lef": dict(base_sha256=sha(base), sha256=sha(new), md5=hashlib.md5(new.encode()).hexdigest())}))
    monkeypatch.setattr(L, "DIR", d); monkeypatch.setattr(L, "_map", None); monkeypatch.setattr(L, "APPLIED", {})
    p = tmp_path / "v"; p.mkdir(); (p / "m.lef").write_text(base)
    return d, p / "m.lef"


def test_no_map_is_a_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "DIR", tmp_path / "none"); monkeypatch.setattr(L, "_map", None)
    assert L.select("a/m.lef", Path) == "a/m.lef"


def test_base_match_takes_corrected_same_name(tmp_path, monkeypatch):
    d, p = setup(tmp_path, monkeypatch)
    got = L.select(str(p), Path)
    assert got == str(d / "m.lef") and Path(got).name == "m.lef"


def test_type_macros_uses_design_root_for_override_and_cache(tmp_path, monkeypatch):
    import gen_phys

    corrected, base = setup(tmp_path, monkeypatch)
    other_root = tmp_path / "other"
    (other_root / "v").mkdir(parents=True)
    relative_lef = str(base.relative_to(tmp_path))
    (other_root / relative_lef).write_text("DIFFERENT VIEW\n")
    monkeypatch.setattr(gen_phys, "_VIEW_LEF", {})
    monkeypatch.delenv("OT_SIGNED_VIEW_SHA", raising=False)
    core = {"inst": "u_m", "module": "m", "lef": relative_lef, "origin_um": [0, 0]}
    plan = SimpleNamespace(types={"t": {"hard_cores": [core]}})

    assert gen_phys.type_macros(plan, "t", other_root)[0][2] == relative_lef
    assert gen_phys.type_macros(plan, "t", tmp_path)[0][2] == str(corrected / "m.lef")


def test_other_view_of_the_module_is_left_alone(tmp_path, monkeypatch):
    _, p = setup(tmp_path, monkeypatch)
    p.write_text("A DIFFERENT VIEW\n")
    assert L.select(str(p), Path) == str(p) and not L.APPLIED


def test_md5_mismatch_stops(tmp_path, monkeypatch):
    d, p = setup(tmp_path, monkeypatch)
    (d / "m.lef").write_text("TAMPERED\n")
    with pytest.raises(ValueError, match="md5"):
        L.select(str(p), Path)


def test_hard_landing_view_refused(tmp_path, monkeypatch):
    _, p = setup(tmp_path, monkeypatch)
    (p.parent / "landing_evidence").mkdir()
    with pytest.raises(ValueError, match="landing"):
        L.select(str(p), Path)


def test_receipt_only_when_used(tmp_path, monkeypatch):
    d, p = setup(tmp_path, monkeypatch)
    kd = tmp_path / "kit"; kd.mkdir()
    L.write_receipt(kd, [("i", "m", str(p), None, 0, 0, "R0")])
    assert not (kd / "lef_override.json").exists()
    f = L.select(str(p), Path)
    L.write_receipt(kd, [("i", "m", f, None, 0, 0, "R0")])
    r = json.loads((kd / "lef_override.json").read_text())
    assert r["rows"][0]["lef"] == "m.lef" and r["rows"][0]["md5"]
