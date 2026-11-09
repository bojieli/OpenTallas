#!/usr/bin/env python3
"""DIE-KV-94 11-08 plan event: kv3_hub_C contents 'pll' becomes a placed hard macro (reservation abstract, tools/die_plan/kv_pll_views.py),
so the bound behavioural qkd_pll_analog_model u_pll is black-boxed in the partition kit and its five delay-loop oscillators no longer reach
synthesis (kit rtl_lint: 5 combinational loops, DIE-KV-69 / Codex kv-realization).  No tie-off: the locked output and the por_n/refclk inputs
stay connected as bound, the clock outputs stay unconnected inside the partition exactly as in the RTL.

Only the contents entry 'pll' of kv3_hub_C gains lef/lib/origin_um/orient/outline_um/physical_inst/physical_master; every other byte is
preserved (asserted).  Position: east of the partition centre, next to the POR pad (local 1084, 836) in free area between kvs_ctl and ahub.

usage: pll_bb_event.py PLAN_IN PLAN_OUT [--view-root ABS_DIR]   (default lef/lib paths are repo-relative physical/kv_pll_views/...)"""
import argparse
import copy
import json
import sys
from pathlib import Path

TYPE = "kv3_hub_C"
MODULE = "qkd_pll_analog_model"
ORIGIN = [1306.8, 900.18]        # placement site / row grid
SIZE = [172.8, 172.8]


def apply(raw, view_root):
    q = copy.deepcopy(raw)
    t = q["partition_types"][TYPE]
    entry = [c for c in t["contents"] if c.get("inst") == "pll"]
    assert len(entry) == 1 and entry[0].get("module") == "qkd_pllm", entry
    assert "lef" not in entry[0] and "origin_um" not in entry[0]
    ox0, oy0, ox1, oy1 = ORIGIN[0], ORIGIN[1], ORIGIN[0] + SIZE[0], ORIGIN[1] + SIZE[1]
    for c in t.get("hard_cores", []):
        (cx, cy), (cw, ch) = c["origin_um"], c["outline_um"]
        assert ox1 <= cx or cx + cw <= ox0 or oy1 <= cy or cy + ch <= oy0, f"overlaps {c['inst']}"
    base = Path(view_root) if view_root else Path("physical/kv_pll_views/qkd_pll_analog_model")
    entry[0].update(lef=str(base / f"{MODULE}.lef"), lib=str(base / f"{MODULE}_tt.lib"), origin_um=ORIGIN, orient="R0",
                    outline_um=SIZE, physical_inst="u_bound.u_pll", physical_master=MODULE,
                    note=entry[0].get("note", "") + " | DIE-KV-94 11-08: placed reservation abstract, black box in the kit")
    return q


def check_preserved(raw, q):
    a, b = copy.deepcopy(raw), copy.deepcopy(q)
    pa = [c for c in a["partition_types"][TYPE]["contents"] if c.get("inst") == "pll"][0]
    pb = [c for c in b["partition_types"][TYPE]["contents"] if c.get("inst") == "pll"][0]
    for k in ("lef", "lib", "origin_um", "orient", "outline_um", "physical_inst", "physical_master", "note"):
        pa.pop(k, None)
        pb.pop(k, None)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True), "a key outside the event changed"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--view-root")
    a = ap.parse_args(argv)
    text = Path(a.base).read_text()
    raw = json.loads(text)
    assert json.dumps(raw, indent=1) == text.rstrip("\n"), "base plan is not in indent=1 form"
    q = apply(raw, a.view_root)
    check_preserved(raw, q)
    sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tools/die_plan") if not a.view_root else ".")
    import schema as S
    new = set(S.validate(q)) - set(S.validate(raw))
    assert not new, sorted(new)[:10]
    Path(a.out).write_text(json.dumps(q, indent=1) + "\n")
    print("wrote", a.out, "new schema errors 0")


if __name__ == "__main__":
    main()
