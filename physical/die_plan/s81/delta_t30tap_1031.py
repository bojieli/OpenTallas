#!/usr/bin/env python3
"""DIE-S81-43 10-31 (COORD 12:19, GEOM-92 12:13 REVIEW): one-block tap fix (METHODOLOGY 12.20) for
slice_station__t30__cl6a190133 AUTO-GEOM clock_reach 276.58 > 220.

Root cause (CHECKED on kit-wave daaa48cc29b geom.tsv): the kit places the ft1_o relay stations of the 604-bit N->S slot
ft1 on a diagonal walk; two station rows sit mid-span, (320-480, 440-520) and (200-400, 680-760), with no plan tap
nearer than clk_t8 (502.7, 613.4) / clk_t7 (215.5, 613.4) -> worst sink (359, 480) at 276.6 um.  The plan sink model
(stations at the in-pin column) does not see these rows, so plan_geom passes (143) while AUTO-GEOM fails.

Fix (GEOM-92 option A, taps only): two explicit taps clk_t21 / clk_t22 at the legal site (schema.tap_clear strict)
nearest the centres of the two rows, plus one sink row [x, y, 1] at each row centre so the explicit validator never
sees an empty tap.  Nothing else changes (asserted): outline, pins, buses, slots, existing taps, landing pins
(forwarded clock source ports are re-taken only if the new tap is nearer -- reported), every other type.
usage (repo root): delta_t30tap_1031.py PLAN_IN PLAN_OUT REPORT.json"""
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402
import taps as TP  # noqa: E402
import plan_geom as PG  # noqa: E402
import compact_plan as CP  # noqa: E402

TN = "slice_station__t30__cl6a190133"
ROWS = [(400.0, 480.0), (290.0, 720.0)]        # ft1_o station row centres (kit geom.tsv, 40-um bins)


def main():
    src, dst, rp = sys.argv[1:4]
    text = open(src).read()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    t = raw["partition_types"][TN]
    ck = t["clock"]
    assert ck.get("tap_mode") == "explicit", ck.get("tap_mode")
    P0 = S.Plan(copy.deepcopy(raw), Path(src).resolve())
    m0 = PG.type_metrics(P0, TN)
    taken = [tuple(p["xy"]) for p in ck["taps"]]
    rep = dict(lane="DIE-S81-43", type=TN, added=[], before=dict(clock_reach=m0["clock_reach_max"],
               tap_sinks=m0.get("grid_tap_sinks_max")))
    for rx, ry in ROWS:
        q = S.tap_clear(t, rx, ry, taken, strict=True)
        q = [round(q[0], 4), round(q[1], 4)]
        name = f"clk_t{len(ck['taps'])}"
        ck["taps"].append(dict(name=name, xy=q))
        ck.setdefault("sink_sites_um", []).append([rx, ry, 1])
        taken.append(tuple(q))
        rep["added"].append(dict(name=name, xy=q, row=[rx, ry]))
    P = S.Plan(copy.deepcopy(raw), Path(src).resolve())
    fin = TP.explicit_taps(P, TN)
    rep["taps"] = [list(f) for f in fin]
    # forwarded clock out pins: report the nearest tap; keep the source port (stform2 rule only if it changes)
    from gen_phys import clock_pins
    roots = clock_pins(P, TN)
    for p in ck.get("landing_contract", {}).get("pins", []):
        if p.get("kind") == "clock" and p.get("dir") == "out" and "source_clock_port" in p:
            tap = min(roots, key=lambda r: abs(r[1] - p["xy_um"][0]) + abs(r[2] - p["xy_um"][1]))[0]
            rep.setdefault("fclk_out", []).append(dict(pin=p["name"], source=p["source_clock_port"], nearest=tap))
            assert tap == p["source_clock_port"], (p["name"], tap)
    m1 = PG.type_metrics(P, TN)
    rep["after"] = dict(clock_reach=m1["clock_reach_max"], tap_sinks=m1.get("grid_tap_sinks_max"),
                        verdict=[(r["rule"], r["status"], r["value"]) for r in PG.judge(m1, P.name)])
    # reach of the two kit rows to the nearest entry, before / after
    def reach(Pp, pt):
        G = PG.type_sites(Pp, TN)
        return round(min(abs(pt[0] - x) + abs(pt[1] - y) for _, x, y in G["entries"]), 2)
    worst = [(359.0, 480.0), (320.0, 440.0), (480.0, 520.0), (200.0, 680.0), (400.0, 760.0), (240.0, 760.0)]
    rep["kit_row_reach"] = {f"{a},{b}": [reach(P0, (a, b)), reach(P, (a, b))] for a, b in worst}
    # nothing else changed
    for tn in raw["partition_types"]:
        if tn != TN:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
    x, y = copy.deepcopy(t), copy.deepcopy(orig["partition_types"][TN])
    for z in (x, y):
        z["clock"]["taps"] = z["clock"]["taps"][:21]
        z["clock"]["sink_sites_um"] = z["clock"]["sink_sites_um"][:9]
    assert x == y
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    m = re.search(r'^  "' + re.escape(TN) + r'": ', text, re.M)
    _, j = json.JSONDecoder().raw_decode(text, m.end())
    text = text[:m.end()] + CP._d(raw["partition_types"][TN], 2) + text[j:]
    assert json.loads(text) == raw
    open(dst, "w").write(text)
    json.dump(rep, open(rp, "w"), indent=1)
    print(json.dumps(rep, indent=1)[:3000])


if __name__ == "__main__":
    main()
