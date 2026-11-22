"""F1 (FLOW-OPS-R2 11-22, FABLE-FLOW-0000): the cause cap is keyed on the type stem, so clone variants share one count."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def fail(item, block="b1", reason="kit_topology: ValueError: packed exact bank 7 vs face register"):
    return {"item": item, "attempt": 1, "status": "FAIL", "stage": "kit_topology", "q_class": "FLOW", "class": "FLOW",
            "reason": reason, "q_reason": reason, "block_sha": block, "updated": time.time()}


def test_type_stem():
    assert KW.type_stem("kv3_pc_v1__cl23f6a148") == "kv3_pc_v1"
    assert KW.type_stem("col_h9_r2__t1__clb8d86cd5__pv6a2b031b") == "col_h9_r2__t1"
    assert KW.type_stem("seqhost__t1") == "seqhost__t1"


def test_variants_share_one_count_and_plan_change_releases():
    cfg, st = {"dies": {"qwen_kvsys": {}}}, {}
    assert KW.cause_cap_held(cfg, st, "qwen_kvsys", fail("kv3_pc_v1__cl23f6a148", "b1")) == ""        # one automatic relaunch
    held = KW.cause_cap_held(cfg, st, "qwen_kvsys", fail("kv3_pc_v1__cl4ea58a5c", "b2"))              # a sibling: same cause, held
    assert held.startswith("CAUSE-CAP") and "type kv3_pc_v1" in held and "kv3_pc_v1__cl23f6a148" in held
    assert KW.cause_cap_held(cfg, st, "qwen_kvsys", fail("kv3_pc_v1__cl7f648944", "b3")).startswith("CAUSE-CAP")
    assert KW.cause_cap_held(cfg, st, "qwen_kvsys", fail("kv3_hub_C", "b9")) == ""                     # another type: own count
    assert KW.cause_cap_held(cfg, st, "qwen_kvsys", fail("kv3_pc_v1__cl23f6a148", "b1-new")) == ""     # its plan block changed: released
