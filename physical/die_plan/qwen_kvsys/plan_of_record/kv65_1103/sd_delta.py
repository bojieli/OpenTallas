#!/usr/bin/env python3
"""DIE-KV-65 11-03: kv3_sys_SD/_v1 rim clock taps + die clock.ring_hold; span edit of plan_c.json and eW_sidecar.json.

Measured class (kv3_sys_SD_v1 event28w_c attempt_4 4_cts.odb): all taps sit on the south rim (tap_edge_y_um 21.6) and
the PHY macro fills the tile, so the few flops up the E/W rims stretch the sink bbox of clk_t4 / clk to 627 / 734 um
tall. TritonCTS centres the H-tree on that bbox: its legs run up the rim and come back down to the south sinks
(clk_t4 24 levels, 84 % of sinks at y < 200). Rim taps at the reset local tap sites take the rim flops off them.

    sd_delta.py PLAN SIDECAR [--sender-ps N]
"""
import json, sys
from pathlib import Path
sys.path.insert(0, "tools/die_plan")
import schema as S
import reset_tree as RT
import taps

TYPES = ("kv3_sys_SD", "kv3_sys_SD_v1")
RIM = [[1879.2, 326.16], [1874.88, 749.52], [8.64, 332.64], [8.64, 734.4]]
D = json.JSONDecoder()


def span(txt, start, key):
    i = txt.index(f'"{key}":', start) + len(key) + 3
    while txt[i] in " \n": i += 1
    _, e = D.raw_decode(txt, i)
    return i, e


def dump(o, ind):
    s = json.dumps(o, indent=1)
    return s.replace("\n", "\n" + " " * ind)


def main():
    plan, side = Path(sys.argv[1]), Path(sys.argv[2])
    sender = float(sys.argv[sys.argv.index("--sender-ps") + 1]) if "--sender-ps" in sys.argv else None
    raw = json.loads(plan.read_text())
    txt = plan.read_text()
    trees = {}
    for tn in TYPES:
        ck = raw["partition_types"][tn]["clock"]
        assert "tap_mode" not in ck and "added_taps" not in ck, tn
        n = S.Plan(raw) and len(S._grid_taps(S.Plan(raw), tn))
        ck["tap_mode"] = "grid+explicit"
        ck["added_taps"] = [dict(name=f"clk_t{n + i}", xy=xy) for i, xy in enumerate(RIM)]
    P = S.Plan(raw)
    for tn in TYPES:
        for row in taps.grid_explicit_taps(P, tn):
            print(tn, "TAP", row)
        old = raw["partition_types"][tn]["clock"]["landing_contract"]["collector_tree"]
        new = json.loads(json.dumps(RT.for_type(P, tn), sort_keys=False))
        print(tn, "tree", {k: (old.get(k), new.get(k)) for k in ("root", "depth", "own_depth", "entry", "n_clock_taps", "n_reset_consumers", "start_in")},
              "relays", len(old["relays"]), len(new["relays"]))
        trees[tn] = new
    # plan text: type-local spans, last type first so offsets stay valid
    order = sorted(TYPES, key=lambda t: -txt.index(f'"{t}": {{'))
    for tn in order:
        at = txt.index(f'"{tn}": {{')
        ci, ce = span(txt, at, "clock")
        ck_txt = txt[ci:ce]
        ti, te = span(ck_txt, ck_txt.index('"collector_tree"') - 1, "collector_tree")
        line = ck_txt.rfind("\n", 0, ck_txt.index('"collector_tree"')) + 1
        ind = ck_txt.index('"collector_tree"') - line
        ck_txt = ck_txt[:ti] + dump(trees[tn], ind) + ck_txt[te:]
        add = raw["partition_types"][tn]["clock"]["added_taps"]
        first = ck_txt.index('"', 1)
        line = ck_txt.rfind("\n", 0, first) + 1
        ind = first - line
        ins = '"tap_mode": "grid+explicit",\n' + " " * ind + '"added_taps": ' + dump(add, ind) + ",\n" + " " * ind
        ck_txt = ck_txt[:first] + ins + ck_txt[first:]
        txt = txt[:ci] + ck_txt + txt[ce:]
    if sender is not None:
        at = txt.index('"clock": {', txt.index('"lanes":'))
        first = txt.index('"', at + 10)
        line = txt.rfind("\n", 0, first) + 1
        ind = first - line
        txt = txt[:first] + '"ring_hold": ' + json.dumps({"sender_ps": sender}) + ",\n" + " " * ind + txt[first:]
    plan.write_text(txt)
    s = side.read_text()
    sd = json.loads(s)
    for tn in TYPES:
        at = s.index(f'"{tn}": {{', s.index('"types"', s.index('"collector"')))
        ti, te = span(s, at, "tree")
        line = s.rfind("\n", 0, s.index('"tree"', at)) + 1
        s = s[:ti] + dump(trees[tn], s.index('"tree"', at) - line) + s[te:]
    side.write_text(s)
    a = json.loads(plan.read_text()); b = json.loads(side.read_text())
    for tn in TYPES:
        assert a["partition_types"][tn]["clock"]["landing_contract"]["collector_tree"] == trees[tn]
        assert b["collector"]["types"][tn]["tree"] == trees[tn]
    print("OK ring_hold", a["clock"].get("ring_hold"))


main()
