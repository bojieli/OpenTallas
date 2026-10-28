"""HBM-R16 (COORD 10-27): hard_cores[] accept the HC128 overlay identity / superset-face keys used by the adopted HBM
plan D-HBM-C16 (parent_instance, cut_instance, halo_um, pin_select, unused_pins, unused_pins_policy).  Ported from
codex/hbm-plan-1351 (7e334cab5 / ee7c51747); all keys optional, so existing plans validate unchanged."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
KEYS = ("parent_instance", "cut_instance", "halo_um", "pin_select", "unused_pins", "unused_pins_policy")


def _plan(**extra):
    p = copy.deepcopy(EX)
    hc = dict(inst="u_hc0", module="m_hc", origin_um=[1.0, 1.0], outline_um=[2.0, 2.0])
    hc.update(extra)
    p["partition_types"]["src"]["hard_cores"] = [hc]
    return p


def _key_errs(p):
    return [e for e in schema.validate(p) if any(k in e for k in KEYS)]


def test_overlay_keys_accepted():
    p = _plan(parent_instance="u_hc_parent", cut_instance="u_hc_cut", halo_um=0.0,
              pin_select={"dq": "N"}, unused_pins=["dq@S"], unused_pins_policy="registered_declared")
    assert _key_errs(p) == []


def test_overlay_keys_typed():
    assert _key_errs(_plan(halo_um=-1.0))
    assert _key_errs(_plan(pin_select={"dq": 3}))
    assert _key_errs(_plan(unused_pins="dq@S"))
    assert _key_errs(_plan(parent_instance=""))


def test_example_unchanged():
    assert schema.validate(EX) == []
