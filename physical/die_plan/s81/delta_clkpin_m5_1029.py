#!/usr/bin/env python3
"""S81-028 (DIE-S81-24, 2026-10-29): GEOM-21 clock entry for the two blocked leaf cores.

Fix-only plan pin delta: the clock pin of dsfd_su_t_rxsf and ot_s81sl_vs becomes a full-size M5 edge rectangle
(0.048 x 0.48 um, centre on the kit M5 track x = 0.012 + 0.048 k), as kit_contract.clock_pin_geometry requires
(GEOM-21: the small 0.024-wide / M4 entry is the DRT-0255 class).  Nothing else moves.

  ot_s81sl_vs  (template table, all 74 instances): clk stays at x = 85.164 on the S face (same track, same face);
               the rectangle grows from M5 0.024x0.084 to 0.048x0.48 (centre y 0.042 -> 0.24).  Plan LEF edited in place.
  dsfd_su_t_rxsf (74 instances, R0/MX only): ck was M4 0.084x0.024 on the E face (140.358, 92.892).  M5 is vertical and
               no M5 track centre fits an E-face edge rectangle on the 140.4-um outline ((140.376-0.012)/0.048 = 2924.25),
               so ck moves to the nearest legal M5 edge site: N face, x = 140.124 (track 2919, 0.276 um from the E edge),
               centre y = 140.16 (rect 140.100 139.920 140.148 140.400).  R0/MX keep x, so every instance stays on track.
               Pins are only on W/E faces (M4); no M4/M5 OBS or PG shape in the N-E corner above y 138.263 (CHECKED).
               The closed view's LEF (physical/ref_tile/s81su_rxsf_ref/views/...) is NOT edited: the plan pin contract
               moves to a plan-owned copy cores/rx/lef/dsfd_su_t_rxsf.lef (identical except the ck PORT), and the plan
               hard_cores rows of dsfd_su_t_rxsf (pins_file inputs/core_pins/dsfd_su_t_rxsf.json) point to it.
Neither core is an early tap of the die clock (plan clock.core_taps 'early' lists ve_m/vsw/vn_a/vn_b only), so the die
tree (ot_clk s81_g03c2) is unchanged: the partition-local tree reaches these pins.

usage: python3 delta_clkpin_m5_1029.py [--plan PLAN.json ...]   (default: physical/die_plan/s81/die_plan.json)
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

S81 = Path(__file__).resolve().parent
REPO = S81.parents[2]
REF_LEF = "physical/ref_tile/s81su_rxsf_ref/views/dsfd_su_t_rxsf/dsfd_su_t_rxsf.lef"
NEW_LEF = "physical/die_plan/s81/cores/rx/lef/dsfd_su_t_rxsf.lef"
VS_LEF = "physical/die_plan/s81/cores/leaf/lef/ot_s81sl_vs_tpl.lef"
PIN_W, PIN_L = 0.048, 0.48
EDITS = {
    "dsfd_su_t_rxsf": dict(pins="inputs/core_pins/dsfd_su_t_rxsf.json", pin="ck", W=140.4, H=140.4,
                           old=("M4", 140.358, 92.892), new=("M5", 140.124, 140.16), lef_src=REF_LEF, lef=NEW_LEF),
    "ot_s81sl_vs": dict(pins="inputs/core_pins/ot_s81sl_vs_tpl.json", pin="clk", W=172.8, H=172.8,
                        old=("M5", 85.164, 0.042), new=("M5", 85.164, 0.24), lef_src=VS_LEF, lef=VS_LEF),
}


def pinhash(pins):
    return hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()[:12]


def rect(e):
    _, x, y = e["new"]
    if abs(y - PIN_L / 2) < 1e-6:
        y0, y1 = 0.0, PIN_L
    elif abs(y - (e["H"] - PIN_L / 2)) < 1e-6:
        y0, y1 = e["H"] - PIN_L, e["H"]
    else:
        raise SystemExit("clock pin must be an N/S edge rectangle")
    k = (x - 0.012) / 0.048
    assert abs(k - round(k)) < 1e-6, ("off M5 track", x)
    return x - PIN_W / 2, y0, x + PIN_W / 2, y1


def edit_lef(e):
    txt = (REPO / e["lef_src"]).read_text()
    x0, y0, x1, y1 = rect(e)
    pat = re.compile(r"(  PIN %s\n(?:(?!  END %s\n).)*?    PORT\n)(.*?)(    END\n  END %s\n)" % ((re.escape(e["pin"]),) * 3), re.S)
    m = pat.search(txt)
    assert m and len(pat.findall(txt)) == 1, e["pin"]
    port = f"      LAYER M5 ;\n        RECT {x0:.4f} {y0:.4f} {x1:.4f} {y1:.4f} ;\n"
    out = txt[:m.start(2)] + port + txt[m.end(2):]
    (REPO / e["lef"]).parent.mkdir(parents=True, exist_ok=True)
    (REPO / e["lef"]).write_text(out)


def edit_pins(mod, e):
    f = S81 / e["pins"]
    d = json.loads(f.read_text())
    assert d["pinhash"] == pinhash(d["pins"]), f"{f}: pinhash formula"
    q = [p for p in d["pins"] if p["name"] == e["pin"]]
    assert len(q) == 1 and (q[0]["layer"], q[0]["x"], q[0]["y"]) == e["old"], q
    q[0].update(layer=e["new"][0], x=e["new"][1], y=e["new"][2])
    d["lef"] = e["lef"]
    d["pinhash"] = pinhash(d["pins"])
    d["source"] += (f"; S81-028 DIE-S81-24 2026-10-29 (delta_clkpin_m5_1029.py): clock {e['pin']} "
                    f"{e['old'][0]}({e['old'][1]},{e['old'][2]}) -> {e['new'][0]}({e['new'][1]},{e['new'][2]}) "
                    f"{PIN_W}x{PIN_L} edge rectangle on the M5 track (GEOM-21)")
    f.write_text(json.dumps(d, indent=0) + ("\n" if f.read_text().endswith("\n") else ""))


def edit_plan(path):
    txt = Path(path).read_text()
    old = f'"module":"dsfd_su_t_rxsf","lef":"{REF_LEF}"'
    n = txt.count(old)
    if n:   # compact one-row-per-core form (main die_plan.json): textual swap keeps every other byte
        txt = txt.replace(old, f'"module":"dsfd_su_t_rxsf","lef":"{NEW_LEF}"')
        Path(path).write_text(txt)
        return n
    p = json.loads(txt)
    n = 0
    for t in p["partition_types"].values():
        for h in t.get("hard_cores", []):
            if h["module"] == "dsfd_su_t_rxsf" and h.get("pins_file") == EDITS["dsfd_su_t_rxsf"]["pins"]:
                assert h["lef"] == REF_LEF, h["lef"]
                h["lef"] = NEW_LEF
                n += 1
    Path(path).write_text(json.dumps(p, indent=1) + "\n")
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="append")
    ap.add_argument("--plans-only", action="store_true")
    a = ap.parse_args()
    if not a.plans_only:
        for mod, e in EDITS.items():
            edit_lef(e)
            edit_pins(mod, e)
            print(mod, e["pin"], e["old"], "->", e["new"], "rect", rect(e))
    for pl in a.plan or [str(S81 / "die_plan.json")]:
        print(pl, "rxsf hard_cores lef ->", NEW_LEF, edit_plan(pl))
