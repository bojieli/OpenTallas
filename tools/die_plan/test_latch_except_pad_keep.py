"""latch_except_hb4 (FABLE-CLOSURE-STRATEGY 11-17): the kit keeps the bit-level lockup pads dont_touch (u_hdly_lk_*) and fails
when the netlist lost them all; no pad declared or another type = no hook (byte-same)."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402

PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())


def _raw(pad=None):
    raw = copy.deepcopy(PAIR)
    cfg = {"modules": {"m": ["tap"]}, "types": ["fb"], "pipe": 1, "latch_except": {"m": ["tap[0]"]}}
    if pad is not None:
        cfg["latch_except_hb4"] = {"m": {"tap[0]": pad}}
    raw.setdefault("clock", {})["core_input_lockup"] = cfg
    for t in raw["partition_types"].values():
        for b in t.get("buses", []):
            b.pop("hold_hb4", None)
    return raw


def test_hook_only_with_a_declared_pad_for_a_listed_type():
    assert gen_phys.hold_pad_dont_touch_tcl(schema.Plan(_raw()), "fb") == ""
    assert gen_phys.hold_pad_dont_touch_tcl(schema.Plan(_raw(0)), "fb") == ""
    assert gen_phys.hold_pad_dont_touch_tcl(schema.Plan(_raw(3)), "fa") == ""
    tcl = gen_phys.hold_pad_dont_touch_tcl(schema.Plan(_raw(3)), "fb")
    assert "*u_hdly_lk_*" in tcl and "setDoNotTouch 1" in tcl and "OT_HOLDPAD_LK" in tcl and "error" in tcl


def test_all_form_of_the_lockup_key_is_a_listed_type_too():
    """the cbn plan uses {"all": true, ...} with no "types" list: the pad keep must still be emitted (an unkept pad is
    removed by remove_buffers and the tap[0] hold fix silently vanishes)."""
    raw = _raw(3)
    cfg = raw["clock"]["core_input_lockup"]
    cfg.pop("types"); cfg["all"] = True
    assert "*u_hdly_lk_*" in gen_phys.hold_pad_dont_touch_tcl(schema.Plan(raw), "fb")
    cfg["except"] = ["fb"]
    assert gen_phys.hold_pad_dont_touch_tcl(schema.Plan(raw), "fb") == ""
