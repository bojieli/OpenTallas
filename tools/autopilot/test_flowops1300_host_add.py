"""FLOW-OPS-1300 / FABLE-FLOW-1900: kit_wave_edit refuses a gen host add until the input-closure probe of that host is empty."""
import os, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_wave_edit as E  # noqa: E402

OLD = {"dies": {"s81": {"gen_host": "epyc8", "gen_hosts": ["epyc2", "epyc7"]}, "hbm": {"gen_host": "epyc10", "gen_hosts": ["epyc2"]}}}


def test_added_gen_hosts():
    new = E.apply_patch(OLD, [{"op": "add", "path": "/dies/s81/gen_hosts/-", "value": "intel2"}])
    assert E.added_gen_hosts(OLD, new) == {"s81": ["intel2"]}
    new = E.apply_patch(OLD, [{"op": "remove", "path": "/dies/s81/gen_hosts/0"}])
    assert E.added_gen_hosts(OLD, new) == {}


def test_probe_scope_and_refusal(monkeypatch):
    monkeypatch.delenv("OT_HOST_ADD_FORCE", raising=False)
    new = E.apply_patch(OLD, [{"op": "add", "path": "/dies/s81/gen_hosts/-", "value": "intel2"}])
    seen = {}

    def probe(cfg):
        seen.update(cfg=cfg)
        return {"intel2": {"s81": "/srv/opentallas-scratch2/claude/kw45/s81bind_x/rtl/bind_cells.sv missing"}}
    errs = E.host_add_problems(new, E.added_gen_hosts(OLD, new), probe)
    assert errs and "s81 intel2" in errs[0] and "bind_cells.sv missing" in errs[0]
    assert seen["cfg"]["dies"]["s81"]["gen_hosts"] == ["intel2"] and seen["cfg"]["dies"]["hbm"]["src_probe"] is False
    assert E.host_add_problems(new, E.added_gen_hosts(OLD, new), lambda c: {}) == []
    monkeypatch.setenv("OT_HOST_ADD_FORCE", "1")
    assert E.host_add_problems(new, E.added_gen_hosts(OLD, new), probe) == []


def test_edit_once_refuses_incomplete_host(monkeypatch, tmp_path):
    import json, subprocess
    monkeypatch.delenv("OT_HOST_ADD_FORCE", raising=False)
    c = tmp_path / "coord"
    (c / "autopilot").mkdir(parents=True)
    (c / E.REL).write_text(E.dump(OLD))
    for a in (["init", "-q"], ["add", E.REL], ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "x"]):
        subprocess.run(["git", "-C", str(c)] + a, check=True, capture_output=True)
    monkeypatch.setattr(E, "HOST_ADD_PROBE", lambda cfg: {"intel2": {"s81": "macros missing"}})
    with pytest.raises(SystemExit) as ex:
        E.edit(c, [{"op": "add", "path": "/dies/s81/gen_hosts/-", "value": "intel2"}], "t", commit_cmd=lambda m, r: "x")
    assert "HOST-ADD refused" in str(ex.value)
    assert json.loads((c / E.REL).read_text()) == OLD
