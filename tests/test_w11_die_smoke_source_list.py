"""W11: the die smoke tool elaborates again (source list fix) and reproduces the adopted smoke step (fast)."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "results/rtl/w11_die_smoke_source_list_fix.json"
ADOPTED = ROOT / "results/rtl/hdc_v41x_die_top_smoke.json"


def test_fix_record_reproduces_the_adopted_smoke_step():
    fix, adopted = json.loads(FIX.read_text()), json.loads(ADOPTED.read_text())
    assert fix["checks"]["smoke"] is True and fix["smoke"]["status"] == "pass"
    # lint fails on pre-existing PINMISSING warnings only (d6df92f9 / 27bea8d3), never an error
    for top in fix["lint"]["tops"].values():
        assert not top["errors"] and all("PINMISSING" in m for m in top["new_source_messages"])
    for k in ("input_token", "position", "next_token", "isa_next_token", "cycles", "logit_mismatches",
              "vm_mismatches", "kv_mismatches", "fault"):
        assert fix["smoke"]["step"][k] == adopted["smoke"]["step"][k], k
    assert fix["smoke"]["step"]["cycles"] == 449701


def test_tool_lists_every_die_dependency():
    from tools import rtl_chip_v41x_die_smoke as ds
    names = {p.stem for p in ds.DIE_DEPS}
    assert {"ot_chip_v41x_rope_su_word", "ot_hdc_v41x_idx_shard_reader", "ot_hdc_v41x_me_xbank",
            "ot_chip_v41x_window_kv_prefetch", "ot_chip_v41x_hbm_karb_local"} <= names
    assert all(p.exists() for p in ds.DIE_DEPS)
