#!/usr/bin/env python3
"""D-S81-B2 (PATH-S81 10-26): cap the six TYPE-REDUCE-2 leaf template core LEFs (*_tpl.lef) at M5.
The tpl stubs carry OBS M1-M7, but the real leaf kits route M2-M5 (PDN M1/M2/M5), as delta_dieft_1713.cap_lefs
already assumed for the pre-reduce LEFs. With the cap, S81 die signal GRT (50 it) = 0 overflow (plan 86c5c681d3b8);
the re-kits of these cores must keep MAX_ROUTING_LAYER M5.
    delta_tplcap_1026.py ROOT [--plan PLAN]     (ROOT = tree holding physical/die_plan/s81; edits LEFs + plan in place)
"""
import argparse, json, re
from pathlib import Path

CAP = ("ot_s81sl_ve_m", "ot_s81sl_ve_s", "ot_s81sl_vn_a", "ot_s81sl_vn_b", "ot_s81sl_vs", "ot_s81sl_vq")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--plan", default="physical/die_plan/s81/die_plan.json")
    a = ap.parse_args()
    W = Path(a.root)
    pp = W / a.plan
    raw = json.loads(pp.read_text())
    paths, n = set(), 0
    for t in raw["partition_types"].values():
        for h in t.get("hard_cores") or []:
            if h.get("module") in CAP:
                if h.get("obs_max") != "M5":
                    h["obs_max"] = "M5"; n += 1
                paths.add(h["lef"])
    for rel in sorted(paths):
        p = W / rel
        txt = p.read_text()
        head, obs = txt.split("  OBS", 1)
        assert not re.search(r"LAYER\s+M[6-9]\s*;", head), f"{rel}: pins above M5"
        new = head + "  OBS" + re.sub(r"    LAYER M[6-9] ;\n(      RECT[^\n]*\n)+", "", obs)
        if new != txt:
            p.unlink(); p.write_text(new)           # unlink first: trees may be hard-link copies
    pp.unlink(); pp.write_text(json.dumps(raw, indent=1) + "\n")
    print(f"capped {len(paths)} LEFs, obs_max set on {n} hard cores")


if __name__ == "__main__":
    main()
