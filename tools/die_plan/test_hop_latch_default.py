"""COORD 11-09: HBM kits get OT_HOP_LATCH_CAPTURE_TAP = u_fl_rst_ by default; other dies stay opt-in."""
import types

import gen_phys


def _p(name):
    return types.SimpleNamespace(die={"name": name})


def test_hbm_default(monkeypatch):
    monkeypatch.delenv("OT_HOP_LATCH_CAPTURE_TAP", raising=False)
    assert gen_phys._hop_latch_capture_tap(_p("hbm_arch_B2o")) == "u_fl_rst_ u_fl_L201x"


def test_other_dies_off(monkeypatch):
    monkeypatch.delenv("OT_HOP_LATCH_CAPTURE_TAP", raising=False)
    for n in ("qwen_compute", "qwen_kvsys", "s81", "head", ""):
        assert gen_phys._hop_latch_capture_tap(_p(n)) is None


def test_env_wins(monkeypatch):
    monkeypatch.setenv("OT_HOP_LATCH_CAPTURE_TAP", "u_fl_rst_6/,u_fl_rst_36/")
    assert gen_phys._hop_latch_capture_tap(_p("qwen_compute")) == "u_fl_rst_6/ u_fl_rst_36/"
    monkeypatch.setenv("OT_HOP_LATCH_CAPTURE_TAP", "off")
    assert gen_phys._hop_latch_capture_tap(_p("hbm_arch_B2o")) is None
