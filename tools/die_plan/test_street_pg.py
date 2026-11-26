"""pytest: C-STREET-R2 opt-in PG-adjusted street sizing (street_pg, street_rule pg_loss, adv_fp_floorplan pg flag)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_fp_floorplan as F  # noqa: E402
import street_pg as SP  # noqa: E402
import street_rule as SR  # noqa: E402
from test_adv_fp_floorplan import _type  # noqa: E402


def test_loss_derived_from_band_table():
    assert abs(SP.blocked_share("M5") - 2 * 0.264 / 4.32) < 1e-9
    assert SP.blocked_share("M3") == 0.0
    assert abs(SP.street_layer_loss() - (0 + 2 * 0.264 / 4.32 + 2 * 0.48 / 8.64) / 3) < 1e-9
    for d in "VH":
        assert 0.85 < SP.pg_factor(d) < 1.0


def test_street_rule_default_off_is_identical():
    cfg = dict(SR.DEFAULTS)
    assert SR.pg_loss(cfg) == 0.0
    assert abs(SR.k_per_um(cfg) - 37.5) < 1e-9
    assert SR.need_um(1620, cfg) == 43.2


def test_street_rule_pg_widens_need():
    off, on = dict(SR.DEFAULTS), dict(SR.DEFAULTS, street_pg=1)
    assert SR.k_per_um(on) < SR.k_per_um(off)
    for pins in (1620, 3349, 9000):
        assert SR.need_um(pins, on) >= SR.need_um(pins, off)
    assert SR.need_um(3349, on) > SR.need_um(3349, off)
    assert SR.need_um(3349, dict(on, pg_track_loss=0.0)) == SR.need_um(3349, off)


def test_plan_flag_parse():
    assert SR.plan_street_cfg({}) == {}
    assert SR.plan_street_cfg({"street_sizing": {"pg": 0}}) == {}
    assert SR.plan_street_cfg({"street_sizing": {"pg": 1}}) == {"street_pg": 1}
    assert SR.plan_street_cfg({"street_sizing": {"pg": 1, "pg_track_loss": 0.2}})["pg_track_loss"] == 0.2


def test_adv_flag_flips_borderline_type_only_when_on(monkeypatch):
    monkeypatch.delenv("OT_STREET_PG", raising=False)
    t0 = _type(bits=1, gap=100.0)
    w = F.street_worst(t0)
    bits = math.floor(0.97 * w[5] / w[4])       # demand is linear in bits: stock ratio ~0.97
    t = _type(bits=bits, gap=100.0)
    w = F.street_worst(t)
    assert w and 0.9 < w[0] < 1.0
    off = F.findings({"partition_types": {"T": t}})
    on = F.findings({"partition_types": {"T": t}, "street_sizing": {"pg": 1}})
    assert not any("ADV-FP-STREET" in x for x in off)
    assert any("ADV-FP-STREET T [PG-adjusted]" in x for x in on)
    monkeypatch.setenv("OT_STREET_PG", "1")
    assert any("[PG-adjusted]" in x for x in F.findings({"partition_types": {"T": t}}))


def test_adv_default_unchanged_when_flag_absent():
    t = _type(bits=100000, gap=10.0)
    a = F.findings({"partition_types": {"T": t}})
    assert any(x.startswith("WARN ADV-FP-STREET T:") for x in a)


def _coreless(bits, x=240.0):
    st = [{"launch": "bus x", "from_um": [x, 100.0], "regs_um": [[x, 800.0]], "to_um": [x, 1500.0]}]
    return {"outline_um": [600.0, 2000.0], "hard_cores": [], "buses": [{"name": "x", "width": bits}],
            "internal_stations": st, "ft_slots": [], "cells": 10}


def test_coreless_type_blind_by_default_seen_with_flag():
    t = _coreless(3000)
    assert F.street_worst(t) is None
    assert not any("ADV-FP-STREET" in x for x in F.findings({"partition_types": {"T": t}}))
    w = F.street_worst(t, True)
    assert w and w[0] > 1.0 and w[3][0] <= 240.0 < w[3][1]
    assert any("ADV-FP-STREET T [PG-adjusted]" in x for x in F.findings({"partition_types": {"T": t}, "street_sizing": {"pg": 1}}))
    assert F.street_worst(_coreless(10), True)[0] < 1.0
