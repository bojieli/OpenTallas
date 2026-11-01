#!/usr/bin/env python3
"""DIE-KV-57 10-31 (GEOM-93 14:25 FAIL PLAN, METHODOLOGY 12.20 one-block fix per type, 12.13 clock follows data):
kv3_io_ft / kv3_io_ft_v1 / kv3_hroot had every die-clock entry on the S edge (CLOCK-KV-R8 tap_edge_y_um [21.6]) while
their ft bands, landing banks and N-row stations sit on the W/E faces and the N row: plan_geom clock_reach 849.7 /
849.8 / 834.8, tap sinks 2261 / 2258 / 5362 (AUTO-GEOM kit: 849.6 / 833, 2290 / 6814).

Fix (taps only, existing DIE-S81-39 clock.tap_mode "grid+explicit"): the R4/edge grid stays EXACTLY as it is (same
names, xy, order: clk..clk_t3 / clk..clk_t4 on y 21.6) and clock.added_taps are appended where plan sinks (planned
sinks, landing ring-read bands, landed out-face registers, reset relays) were beyond ~170 um of every entry, legalised
by schema.tap_clear(strict) clear of the reset.local_taps_um sites; hroot gets two more on the i_kvs_ctl_o_hroot_Q
ring-read band to split its load.  Tap sites are recorded in added_taps.json (computed by the DIE-KV-57 cover search
on the plan sink model, validated by taps.grid_explicit_taps: every added tap non-empty, <= tap_max_sinks, within
tap_radius_um).  Nothing else changes (asserted): outline, pins, buses, slots, existing grid taps, every other type.
usage (repo root): delta_geom93_taps.py PLAN_IN PLAN_OUT REPORT.json"""
import copy, json, re, sys
from pathlib import Path
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import schema as S  # noqa: E402
import taps as TP  # noqa: E402
import plan_geom as PG  # noqa: E402

ADDED = json.load(open(Path(__file__).resolve().parent / "added_taps.json"))


def _fmt(x):
    """the KV plan file format (json indent=1) for a type entry at depth 2"""
    return json.dumps(x, indent=1).replace("\n", "\n  ")


def metrics(P, tn):
    m = PG.type_metrics(P, tn)
    return dict(clock_reach=m["clock_reach_max"], far=m["clock_reach_far"], tap_sinks=m.get("grid_tap_sinks_max"),
                verdict=[(r["rule"], r["status"], r["value"]) for r in PG.judge(m, P.name)])


def main():
    src, dst, rp = sys.argv[1:4]
    text = open(src).read()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    P0 = S.Plan(copy.deepcopy(raw), Path(src).resolve())
    rep = dict(lane="DIE-KV-57", rule="GEOM-93 FAIL PLAN, 12.20 one-block taps", types={})
    for tn, add in ADDED.items():
        ck = raw["partition_types"][tn]["clock"]
        assert ck.get("tap_mode") is None and ck.get("tap_edge_y_um") == [21.6], (tn, ck.get("tap_mode"))
        ck["tap_mode"] = "grid+explicit"
        ck["added_taps"] = copy.deepcopy(add)
        rep["types"][tn] = dict(before=metrics(P0, tn), grid=[list(g) for g in S._grid_taps(P0, tn)], added=add)
    P = S.Plan(copy.deepcopy(raw), Path(src).resolve())
    for tn in ADDED:
        assert [list(g) for g in S._grid_taps(P, tn)] == rep["types"][tn]["grid"], tn   # grid unchanged
        fin = TP.grid_explicit_taps(P, tn)
        rep["types"][tn]["taps"] = [[n, x, y, k, round(r, 1)] for n, x, y, k, r in fin]
        rep["types"][tn]["after"] = metrics(P, tn)
    for tn in raw["partition_types"]:
        if tn not in ADDED:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
        else:
            x, y = copy.deepcopy(raw["partition_types"][tn]), copy.deepcopy(orig["partition_types"][tn])
            for k in ("tap_mode", "added_taps"):
                x["clock"].pop(k)
            assert x == y, tn
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn in ADDED:
        m = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, m.end())
        text = text[:m.end()] + _fmt(raw["partition_types"][tn]) + text[j:]
    assert json.loads(text) == raw
    open(dst, "w").write(text)
    json.dump(rep, open(rp, "w"), indent=1)
    for tn, r in rep["types"].items():
        print(tn, "before", r["before"]["clock_reach"], r["before"]["tap_sinks"], "after", r["after"]["clock_reach"],
              r["after"]["tap_sinks"], "added", len(r["added"]))


if __name__ == "__main__":
    main()
