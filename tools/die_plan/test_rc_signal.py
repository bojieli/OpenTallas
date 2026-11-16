"""r222/r228: per-die signal-net RC table scale (rc_signal_scales.json) -> config.mk lines; hooks in the gate and the TT repair."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("OT_RC_SIGNAL", raising=False)
    monkeypatch.delenv("OT_RC_SIGNAL_SCALE", raising=False)


def test_validated_dies_get_their_scale():
    assert gen_phys.rc_signal_cfg("s81")[1:] == ["export OT_RC_SIGNAL = 1", "export OT_RC_SIGNAL_SCALE = 1", "export OT_TT_SETUP_DESIGN = 1"]
    assert gen_phys.rc_signal_cfg("qwen_compute")[2] == "export OT_RC_SIGNAL_SCALE = 1.25"
    assert gen_phys.rc_signal_cfg("s81_head")[2] == "export OT_RC_SIGNAL_SCALE = 1"
    assert gen_phys.rc_signal_cfg("qwen_kvsys")[2] == "export OT_RC_SIGNAL_SCALE = 1.1"
    assert gen_phys.rc_signal_cfg("anything", flow="core")[2] == "export OT_RC_SIGNAL_SCALE = 1.1"


@pytest.mark.parametrize("die", ["hbm", "nope"])
def test_unvalidated_dies_stay_byte_equal(die):
    assert gen_phys.rc_signal_cfg(die) == []


def test_off_switch_and_override(monkeypatch):
    monkeypatch.setenv("OT_RC_SIGNAL", "0")
    assert gen_phys.rc_signal_cfg("s81") == []
    monkeypatch.delenv("OT_RC_SIGNAL")
    monkeypatch.setenv("OT_RC_SIGNAL_SCALE", "1.4")
    assert gen_phys.rc_signal_cfg("s81_head")[2] == "export OT_RC_SIGNAL_SCALE = 1.4"
    monkeypatch.setenv("OT_RC_SIGNAL_SCALE", "x;rm")
    with pytest.raises(SystemExit):
        gen_phys.rc_signal_cfg("s81")


def test_table_file_is_sane():
    t = json.loads((HERE / "rc_signal_scales.json").read_text())
    assert t["schema"] == "opentallas.rc_signal_scales.v1"
    assert all(0.5 <= v <= 2.0 for v in list(t["type"].values()) + [t["core"]])


def test_hooks_read_config_and_repair_design():
    for f in ("postcts_gate.tcl", "tt_setup_repair.tcl"):
        txt = (HERE / f).read_text()
        assert "OT_RC_SIGNAL|OT_RC_SIGNAL_SCALE" in txt and "ot_rc_signal_table" in txt
    assert "OT_TT_SETUP_DESIGN" in (HERE / "tt_setup_repair.tcl").read_text() and "repair_design" in (HERE / "tt_setup_repair.tcl").read_text()
    assert "proc ot_rc_signal_table" in (HERE / "rc_signal_adjust.tcl").read_text()
    assert '"rc_signal_adjust.tcl"' in (HERE / "gen_phys.py").read_text()
