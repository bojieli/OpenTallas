"""The reset hook knobs reach the flow container through the generic gen_knobs mechanism (gen env -> config.mk export), default off.
reset_taps.tcl reads them as ::env(OT_...); gen_phys.gen_knobs() finds every such read, so no dedicated emitter is needed."""
from pathlib import Path

import pytest

import gen_phys as G

KNOBS = ("OT_RESET_AFFINITY_MAX_DRIVER_UM", "OT_RESET_RELAY")
SRC = (Path(__file__).parent / "reset_taps.tcl").read_text()


def test_hook_reads_the_knobs_from_env_only():
    for k in KNOBS:
        assert "::env(%s)" % k in SRC
        assert "set ::env(%s)" % k not in SRC            # a tcl `set ::env` would hide the knob from gen_knobs


@pytest.mark.parametrize("k", KNOBS)
def test_knob_is_detected(k):
    assert k in G.gen_knobs()


def test_default_off_emits_nothing(monkeypatch):
    for k in KNOBS:
        monkeypatch.delenv(k, raising=False)
    assert not [ln for ln in G.gen_knob_cfg([]) if any(k in ln for k in KNOBS)]
    assert not [k for k in G.kit_effective_env() if k in KNOBS]


def test_set_knobs_are_exported_and_audited(monkeypatch):
    monkeypatch.setenv("OT_RESET_AFFINITY_MAX_DRIVER_UM", "165")
    monkeypatch.setenv("OT_RESET_RELAY", "1")
    cfg = G.gen_knob_cfg([])
    assert "export OT_RESET_AFFINITY_MAX_DRIVER_UM = 165" in cfg and "export OT_RESET_RELAY = 1" in cfg
    eff = G.kit_effective_env()
    assert eff["OT_RESET_AFFINITY_MAX_DRIVER_UM"] == "165" and eff["OT_RESET_RELAY"] == "1"


def test_a_plan_derived_export_wins(monkeypatch):
    monkeypatch.setenv("OT_RESET_RELAY", "1")
    assert "export OT_RESET_RELAY = 1" not in G.gen_knob_cfg(["export OT_RESET_RELAY = 0"])


def test_unsafe_value_refused(monkeypatch):
    monkeypatch.setenv("OT_RESET_AFFINITY_MAX_DRIVER_UM", "165; rm")
    monkeypatch.setenv("OT_RESET_AFFINITY_MAX_DRIVER_UM", "16#5")
    with pytest.raises(ValueError):
        G.gen_knob_values()


def test_a_tcl_set_env_would_hide_the_knob():
    """why the hand-patched kit line 'set ::env(OT_RESET_AFFINITY_MAX_DRIVER_UM) 165' must never be committed to the repo tcl"""
    import re
    rd, st = set(), set()
    for t in ("set ::env(OT_RESET_RELAY) 1\n puts $::env(OT_RESET_RELAY)",):
        rd |= set(re.findall(r"::env\((OT_\w+)\)", t))
        st |= set(re.findall(r"set\s+::env\((OT_\w+)\)", t))
    assert "OT_RESET_RELAY" in rd and "OT_RESET_RELAY" in st
