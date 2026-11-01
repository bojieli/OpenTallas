#!/usr/bin/env python3
"""DIE-S81-45 10-31: early-tap clock entries for 3 S81 hard cores (COORD 19:0x (4), S81-CORES-KITS-12/etap ASK 18:47).

12.20 one-block clock-entry fix after 2 failed kit variants (ck10/ck12A-B regional, ck12T full TritonCTS miss the
250/202.5 frame by late capture).  Measured pin-register insertion (TCTS full tree, 4_cts placement RC,
s81ck12/gate_*_T/g_{TT,FF}.log), written as the plan's early core taps (partition_types[T].clock.taps[] kind core,
CORELAT-SQ-1 form; core_taps 'early' already set on every carrying type):
  dsdv_bksel_c   TT 359.1 / FF 293.1  (bk_sel__t2 u_bk_sel.u_sel.u_c.ck[0]: was 367.2 / 302.2)
  dsdv_gunit_l3  TT 303.2 / FF 245.5  (gunit__t1 u_gunit.u_l3.clk: NEW core tap at the clk pin, MY placement)
  ot_s81sl_xrt1  TT 370.7 / FF 305.5  (14 dsdv_slice_*_C types u_c.u_xr.clk: was 433.6 / 355.5)
Only the touched partition types are rewritten in the plan text (their own text style).
usage: delta_etap_1031.py PLAN_IN PLAN_OUT [REPORT.json]"""
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools/die_plan"))
import compact_plan as CP  # noqa: E402

SRC = "S81-CORES-KITS-12/etap measured TCTS pin-register insertion (s81ck12/gate_*_T/g_{TT,FF}.log), COORD 19:0x (4)"
VALUES = {"dsdv_bksel_c": (359.1, 293.1), "dsdv_gunit_l3": (303.2, 245.5), "ot_s81sl_xrt1": (370.7, 305.5)}
CLK_PIN = {"dsdv_bksel_c": "ck[0]", "dsdv_gunit_l3": "clk", "ot_s81sl_xrt1": "clk"}


def pin_xy(plan_dir, hc, pin):
    pins = json.loads((plan_dir / hc["pins_file"]).read_text())["pins"]
    p = next(x for x in pins if x["name"] == pin)
    (ox, oy), (w, h), o = hc["origin_um"], hc["outline_um"], hc.get("orient", "R0")
    tx, ty = hc.get("track_offset_um", [0.0, 0.0])
    x = {"R0": p["x"], "MX": p["x"], "MY": w - p["x"], "R180": w - p["x"]}[o]
    y = {"R0": p["y"], "MY": p["y"], "MX": h - p["y"], "R180": h - p["y"]}[o]
    return [round(ox + x + tx, 3), round(oy + y + ty, 3)]


def main():
    pin, pout = sys.argv[1:3]
    rep_p = sys.argv[3] if len(sys.argv) > 3 else None
    text = open(pin).read()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    plan_dir = Path(pin).resolve().parent
    rep = []
    for tn, t in raw["partition_types"].items():
        for hc in t.get("hard_cores", []):
            if hc.get("module") not in VALUES:
                continue
            tt, ff = VALUES[hc["module"]]
            ck = t["clock"]
            assert ck.get("core_taps") == "early", tn
            name = f'{hc["inst"]}.{CLK_PIN[hc["module"]]}'
            xy = pin_xy(plan_dir, hc, CLK_PIN[hc["module"]])
            taps = ck.setdefault("taps", [])
            tap = next((x for x in taps if x["name"] == name), None)
            if tap is None:
                tap = dict(name=name, kind="core", xy=xy)
                taps.append(tap)
                was = None
            else:
                assert tap["kind"] == "core" and abs(tap["xy"][0] - xy[0]) < 0.2 and abs(tap["xy"][1] - xy[1]) < 0.2, (tn, tap, xy)
                was = [tap.get("insertion_ps"), tap.get("insertion_ff_ps")]
            tap["insertion_ps"], tap["insertion_ff_ps"] = tt, ff
            tap["budget_owner"] = f"parent_budget early tap {round(tt - 250.0, 1)} ps TT: {SRC}"
            tap["note"] = "CORELAT-SQ-1: early core tap (12.3 v5.0) at the core clock pin; ETAP-1031 measured kit frame"
            rep.append(dict(type=tn, tap=name, xy=tap["xy"], was=was, now=[tt, ff]))
    for tn in sorted({r["type"] for r in rep}):
        m = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        old, j = json.JSONDecoder().raw_decode(text, m.end())
        assert CP._d(old, 2) == text[m.end():j], f"{tn}: text style differs from compact_plan._d"
        text = text[:m.end()] + CP._d(raw["partition_types"][tn], 2) + text[j:]
    assert json.loads(text) == raw
    for tn in raw["partition_types"]:
        if tn not in {r["type"] for r in rep}:
            assert raw["partition_types"][tn] == orig["partition_types"][tn]
    open(pout, "w").write(text)
    if rep_p:
        open(rep_p, "w").write(json.dumps(rep, indent=1) + "\n")
    for r in rep:
        print(r)
    print(len(rep), "taps in", len({r["type"] for r in rep}), "types")


if __name__ == "__main__":
    main()
