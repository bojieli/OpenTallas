"""KW-FIX-45 PLACE-FANOUT: gen_phys.place_max_fanout + install_gp_noconverge_gate export."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402


def test_off_without_rflow(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_PLACE_MAX_FANOUT", raising=False)
    monkeypatch.setenv("OT_RFLOW", "0")
    cfg = gen_phys.install_gp_noconverge_gate(tmp_path, [])
    assert not any("OT_PLACE_MAX_FANOUT" in c for c in cfg)
    assert any(c.startswith("export PRE_RESIZE_TCL") for c in cfg)


def test_rflow_default_32(tmp_path, monkeypatch):
    # R-FLOW 11-13 (RULEBOOK-1113): the place fanout limit is on for every kit; the gen env value still wins
    monkeypatch.delenv("OT_PLACE_MAX_FANOUT", raising=False)
    monkeypatch.delenv("OT_RFLOW", raising=False)
    assert "export OT_PLACE_MAX_FANOUT = 32" in gen_phys.install_gp_noconverge_gate(tmp_path, [])


def test_export_when_set(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_PLACE_MAX_FANOUT", "32")
    cfg = gen_phys.install_gp_noconverge_gate(tmp_path, [])
    assert "export OT_PLACE_MAX_FANOUT = 32" in cfg
    tcl = (tmp_path / "gp_noconverge_gate.tcl").read_text()
    assert "set_max_fanout $::env(OT_PLACE_MAX_FANOUT)" in tcl
    assert tcl.index("PLACE-FANOUT") < tcl.index("set gpnc_dir")


def test_own_hook_kept(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_PLACE_MAX_FANOUT", "32")
    assert gen_phys.install_gp_noconverge_gate(tmp_path, ["export PRE_RESIZE_TCL = /work/x.tcl"]) == []


@pytest.mark.parametrize("bad", ["0", "1", "x", "-4", "3.5"])
def test_bad_values(monkeypatch, bad):
    monkeypatch.setenv("OT_PLACE_MAX_FANOUT", bad)
    with pytest.raises(ValueError):
        gen_phys.place_max_fanout()
