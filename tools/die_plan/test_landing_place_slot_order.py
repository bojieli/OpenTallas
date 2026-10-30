"""FLOW-8 10-30: ft slot ring bands follow the slot-level 'order' when in_order/out_order are absent (schema pin rule)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import landing_place as LP  # noqa: E402


class _PS:
    def __init__(self, bands, slot):
        self.types = {"t": {"buses": [], "ft_slots": [dict(slot, name="fx")],
                            "clock": {"landing_contract": {"monitor": "dataflow", "bands": bands, "pins": []}}}}


R = {"rect_um": [1, 2, 3, 4], "ring_place": "ff"}


def test_slot_order_only_applies_to_both_sides():
    t = {"ft_slots": [{"name": "fx", "order": "lsb_high"}]}
    assert LP._bus_order(t, "fx_i") == "lsb_high" and LP._bus_order(t, "fx_o") == "lsb_high"


def test_side_order_wins_over_slot_order():
    t = {"ft_slots": [{"name": "fx", "order": "lsb_high", "in_order": "lsb_low"}]}
    assert LP._bus_order(t, "fx_i") == "lsb_low" and LP._bus_order(t, "fx_o") == "lsb_high"


def test_no_order_stays_lsb_low():
    assert LP._bus_order({"ft_slots": [{"name": "fx"}]}, "fx_i") == "lsb_low"
    assert LP._bus_order({}, "x") == "lsb_low"


def test_lsb_high_slot_band_gets_reversed_ff_tag():
    tcl = LP.tcl(_PS({"fx_i": dict(R, instance="u_cland_fx_i")}, {"order": "lsb_high"}), "t")
    assert "ring:fx_i+ffr}" in tcl
    tcl = LP.tcl(_PS({"fx_i": dict(R, instance="u_cland_fx_i")}, {}), "t")
    assert "ring:fx_i+ff}" in tcl
