#!/usr/bin/env python3
"""DIE-S81-47 11-01: one-block plan fix (METHODOLOGY 12.20) for the latent grid+explicit tap violation on
col_h10_r0_p1__t1__cl574cc59d / __cl911743eb, which is exposed in strict bind by 8a92ae7e4 (taps.report now validates
frozen explicit taps): added tap clk_t28 load 413/1500, radius 219.173 > tap_radius 200 um.  The same violation
is present on the event2 plan; it is not a regression of the svc branch.

Fix: clk_t28 moves 25.92 um south, (1126.44, 980.6) -> (1126.44, 954.68), and its four reset relays sited at the tap
(u_rrl_31..34, tap 28) move with it.  Result: radius 194.603 <= 200 and load 396; the relay hop to u_rrl_35 is 401.92
<= reach 405 (collector_tree.reach_um); the parent hop from u_rrl_22 is 333.25.  The 8.6-um grid search found only
(959.0: r 198.9 / hop 397.6) and (954.68: r 194.6 / hop 401.9) legal under both limits, and this one keeps more
radius margin.  Every other key and type is unchanged (asserted).  The landed sidecar collector tree copy is
updated the same way.
usage (repo root): delta_t28tap_1101.py PLAN_IN PLAN_OUT SIDECAR_IN SIDECAR_OUT REPORT.json"""
import copy, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tools" / "die_plan"))
import schema as S  # noqa: E402
import taps as TP  # noqa: E402
import compact_plan as CP  # noqa: E402

TYPES = ["col_h10_r0_p1__t1__cl574cc59d", "col_h10_r0_p1__t1__cl911743eb"]
OLD, NEW = [1126.44, 980.6], [1126.44, 954.68]
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def move(ct):
    mv = [r for r in ct["relays"] if r["tap"] == 28]
    assert [r["name"] for r in mv] == ["u_rrl_31", "u_rrl_32", "u_rrl_33", "u_rrl_34"] and all(r["xy"] == OLD for r in mv), mv
    for r in mv:
        r["xy"] = list(NEW)
    Q = {r["q"]: r for r in ct["relays"]}
    hops = [L1(Q[r["d"]]["xy"], r["xy"]) for r in ct["relays"] if r["d"] in Q]
    mh = round(max(hops), 1)
    assert mh <= ct["reach_um"] + 1e-6, mh
    old = ct["max_hop_um"]
    ct["max_hop_um"] = max(old, mh)
    return old, ct["max_hop_um"], round(max(L1(Q[r["d"]]["xy"], r["xy"]) for r in ct["relays"] if r["d"] in Q and (r["tap"] == 28 or Q[r["d"]]["tap"] == 28)), 3)


def main():
    pin, pout, sin, sout, rp = sys.argv[1:6]
    text = Path(pin).read_text(); raw = json.loads(text); orig = copy.deepcopy(raw)
    stext = Path(sin).read_text(); side = json.loads(stext); sorig = copy.deepcopy(side)
    rep = dict(types={}, old_xy=OLD, new_xy=NEW)
    P0 = S.Plan(copy.deepcopy(orig))
    for tn in TYPES:
        ck = raw["partition_types"][tn]["clock"]
        k = [p["name"] for p in ck["added_taps"]].index("clk_t28")
        assert ck["added_taps"][k]["xy"] == OLD
        ck["added_taps"][k]["xy"] = list(NEW)
        hop = move(ck["landing_contract"]["collector_tree"])
        st = side["collector"]["types"][tn]["tree"]
        assert st == orig["partition_types"][tn]["clock"]["landing_contract"]["collector_tree"], tn
        move(st)
        assert st == ck["landing_contract"]["collector_tree"]
        try:
            TP.grid_explicit_taps(P0, tn); before = "PASS"
        except ValueError as e:
            before = str(e)
        r = TP.grid_explicit_taps(S.Plan(raw), tn)
        q = r[[a[0] for a in r].index("clk_t28")]
        rep["types"][tn] = dict(before=before, after=dict(load=q[3], radius_um=round(q[4], 3)),
                                max_hop_um=hop[:2], tap28_hop_max_um=hop[2])
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn in raw["partition_types"]:
        if tn not in TYPES:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
    for tn in TYPES:
        mm = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, mm.end())
        text = text[:mm.end()] + CP._d(raw["partition_types"][tn], 2) + text[j:]
    assert json.loads(text) == raw
    Path(pout).write_text(text)
    # sidecar: same minimal re-serialization as the earlier band deltas (compact single line file)
    def strip(d):
        d = copy.deepcopy(d)
        for tn in TYPES:
            d["collector"]["types"][tn]["tree"] = None
        return d
    assert strip(side) == strip(sorig)
    sep = (",", ":") if "\n" not in stext.strip() else None
    out = json.dumps(side, separators=sep) if sep else json.dumps(side, indent=1)
    Path(sout).write_text(out + ("\n" if stext.endswith("\n") else ""))
    assert json.loads(Path(sout).read_text()) == side
    Path(rp).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
