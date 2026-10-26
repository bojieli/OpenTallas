"""manifest_paths gate (TOK-SCHED 10-25): in-repo bind manifests must be repository-relative."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest_paths as M  # noqa: E402

REPO = M.REPO
# the operational bind manifests of record (one per die path); each must stay repository-relative.  HBM's
# hbm/bind/asbuilt.json still reads scratch (273 paths) and joins this list when TOK-HBM regenerates it.
OPERATIONAL = [
    "physical/die_plan/s81/bind/asbuilt_b178_coll.json",
    "physical/die_plan/qwen_compute/bind/asbuilt.json",
    "physical/die_plan/qwen_kvsys/bind/asbuilt.json",
]


def _write(tmp, rel, obj):
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))
    return p


def test_relative_inside_passes(tmp_path):
    (tmp_path / "rtl").mkdir()
    p = _write(tmp_path, "physical/d/bind/m.json",
               {"base": "../../..", "files": ["rtl/a.sv"], "netlist": ["physical/d/bind/n.v"], "map_file": "map.json"})
    assert M.check(json.loads(p.read_text()), p.parent, tmp_path) == []


def test_absolute_fails(tmp_path):
    p = _write(tmp_path, "b/m.json", {"files": ["/srv/frozen/wt/rtl/a.sv"], "map_file": "/srv/x/map.json"})
    errs = M.check(json.loads(p.read_text()), p.parent, tmp_path)
    assert len(errs) == 2 and all("absolute" in e for e in errs)


def test_escape_fails(tmp_path):
    p = _write(tmp_path, "b/m.json", {"base": "../..", "prefer": ["../../outside.sv"], "rtl_roots": ["rtl"]})
    errs = M.check(json.loads(p.read_text()), p.parent, tmp_path)
    assert any("base" in e for e in errs) and any("prefer" in e for e in errs)


def test_absolute_base_fails(tmp_path):
    p = _write(tmp_path, "b/m.json", {"base": "/srv/opentallas-scratch2/claude/wt/tok-ds-bind178", "files": ["rtl/a.sv"]})
    errs = M.check(json.loads(p.read_text()), p.parent, tmp_path)
    assert any(e.startswith("base: absolute") for e in errs)


def test_in_plan_section_checked(tmp_path):
    p = _write(tmp_path, "d/die_plan.json", {"asbuilt": {"netlist": ["/home/ubuntu/scratch/die.v"]}})
    assert any("netlist" in e for e in M.check_file(p, tmp_path))


def test_cli_exit(tmp_path, capsys):
    bad = _write(tmp_path, "m.json", {"files": ["/abs.sv"]})
    assert M.main([str(bad)]) == 1
    assert "FAIL" in capsys.readouterr().out


@pytest.mark.parametrize("rel", OPERATIONAL)
def test_operational_manifests_repo_relative(rel):
    p = REPO / rel
    if not p.exists():
        pytest.skip(f"{rel} not in this (sparse) checkout")
    assert M.check_file(p) == []


def test_bind_load_plan_gates_in_repo_manifest(tmp_path, monkeypatch):
    import bind
    m = REPO / "physical/die_plan/_manifest_paths_gate_probe.json"
    m.parent.mkdir(parents=True, exist_ok=True)
    plan = tmp_path / "die_plan.json"
    plan.write_text("{}")
    try:
        m.write_text(json.dumps({"files": ["/srv/frozen/rtl/a.sv"]}))
        monkeypatch.setitem(bind._AB_OVERRIDE, "path", str(m))
        monkeypatch.setitem(bind._AB_OVERRIDE, "allow_external_paths", False)
        with pytest.raises(bind.BindError, match="out-of-repository"):
            bind.load_plan(str(plan))
        monkeypatch.setitem(bind._AB_OVERRIDE, "allow_external_paths", True)
        assert bind.load_plan(str(plan))["asbuilt"]["files"] == ["/srv/frozen/rtl/a.sv"]
        # a scratch manifest outside the repository is not gated
        s = tmp_path / "scratch.json"
        s.write_text(json.dumps({"files": ["/srv/frozen/rtl/a.sv"]}))
        monkeypatch.setitem(bind._AB_OVERRIDE, "path", str(s))
        monkeypatch.setitem(bind._AB_OVERRIDE, "allow_external_paths", False)
        assert bind.load_plan(str(plan))["asbuilt"]["files"] == ["/srv/frozen/rtl/a.sv"]
    finally:
        m.unlink(missing_ok=True)


def test_generic_lec_token_manifest(tmp_path):
    good = _write(tmp_path, "r/lec_cfg.json", {"kit": "physical/die_plan/s81/kits/x", "hints": ["a.json"], "n": "1/2"})
    assert M.check_file(good, tmp_path, kind="lec") == []
    bad = _write(tmp_path, "r/tok.json", {"images": ["/srv/opentallas-scratch2/claude/x/kv.hex"],
                                          "nested": {"src": "../../../elsewhere/rtl/a.sv"}, "home": "~/coord/x"})
    errs = M.check_file(bad, tmp_path, kind="token")
    assert len(errs) == 3
    # auto: a JSON with bind keys is checked as a bind section
    b = _write(tmp_path, "r/m.json", {"files": ["/abs.sv"]})
    assert M.check_file(b, tmp_path) and "files" in M.check_file(b, tmp_path)[0]


def test_result_requires_commit(tmp_path):
    assert M.check_result({"verdict": "EQUIVALENT"}, tmp_path)
    assert M.check_result({"provenance": {"commit": "9a59376bb9", "dirty": False}}, tmp_path) == []
    assert M.check_result({"source_commit": "9a59376bb988365caa7c5df84829dd767405979b"}, tmp_path) == []
    assert M.check_result({"provenance": {"commit": "9a59376bb9", "dirty": True}}, tmp_path)
    assert M.check_result({"provenance": {"commit": "9a59376bb9", "inputs": ["/srv/x/m.json"]}}, tmp_path)


def test_provenance_from_cohort(tmp_path):
    (tmp_path / "cohort.json").write_text(json.dumps({"source_commit": "441e2fb399fa5f617bad638cc50417513a102e55"}))
    p = M.provenance(tmp_path)
    assert p["commit"].startswith("441e2fb399") and p["source"] == "cohort.json"
    assert M.provenance(tmp_path / "nothing")["commit"] is None


def test_bind_writes_provenance(tmp_path):
    import argparse
    import bind
    a = argparse.Namespace(plan=str(tmp_path / "die_plan.json"), asbuilt=None, out=str(tmp_path / "out"))
    bind._write_provenance(a, "bind")
    rec = json.loads((tmp_path / "out" / "provenance_bind.json").read_text())
    assert rec["provenance"]["step"] == "bind" and "commit" in rec["provenance"]
