#!/usr/bin/env python3
"""DIE-S81-34/KVT2 10-30 -- larger local slot for S81 kv_leaf__t2 (OWNER 10-29 23:56: larger slot = first closure
option; CANDIDATE, not adopted).

E-only growth: s_3N_L0 (ot_s81sl_kv_leaf__t2, R0, origin 14532.48,16053.12) 1442.88 -> 1814.40 wide (+371.52 um east,
43 x 8.64); its E neighbour s_4N_L0 (ot_s81sl_leaf__t42, MY) narrows 1442.88 -> 1071.36 with its E (die) edge fixed:
origin x 15975.36 -> 16346.88.  Under MY a type-local point x maps to die x = origin + W - x, so every t42 local ft /
bus / landing window / band (all at local x <= 977.05) keeps its die position; t2 (R0) grows at local x > 1442.88
where it has no windows.  The strip die-x 15975.36..16346.88 carries no ft corridor in either type.

t2: outline only (no hard cores; its 183 native SRAM macros are placed by the kit; packer: 183/183 at 1814.40, bus-first).
t42: the 27 leaf hard cores are re-placed by cores/leaf/search.py (+ landing bands as obstacles, HC_GAP 13.8) at
1071.36 x 1226.88 (run s44: faces_away 0, lanes_behind 0, reach_excess 50.3 um, int_cycles 19, ft_add 0); orient
MY <-> search view 'xm' on the existing TYPE-REDUCE-2 template views (lef / pins_file unchanged); internal_stations
recomputed (gen_plan_v4.core_internal_stations); early core clock taps moved with their cores (clk pin transformed);
collector_tree of both types recomputed with reset_tree.for_type on the new outlines / cores.
All 183 SRAM macros, 16 write enables, RTL and site rules unchanged.

usage: python3 physical/die_plan/s81/delta_kvt2_slot_1030.py PLAN_IN PLAN_OUT     (run from the repo root)
"""
import copy, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "tools/die_plan"), HERE, os.path.join(HERE, "cores/leaf")]

T2, T42 = "ot_s81sl_kv_leaf__t2", "ot_s81sl_leaf__t42"
P2, P42 = "s_3N_L0", "s_4N_L0"
H = 1226.88
OLD = {T2: [1442.88, H], T42: [1442.88, H]}
NEW = {T2: [1814.40, H], T42: [1071.36, H]}
OLD_ORG = {P2: [14532.48, 16053.12], P42: [15975.36, 16053.12]}
NEW_ORG = {P2: [14532.48, 16053.12], P42: [16346.88, 16053.12]}
TOFF = {"R0": [0.108, 0.012], "MY": [0.132, 0.012]}
TAG = "DIE-S81-34/KVT2 1030"
# cores/leaf/search.py result (seed 44, 120k iters, landing bands as obstacles): search frame = the type frame
PLACE = json.load(open(os.path.join(HERE, "cores/leaf/kvt2_t42_narrow_1030.json")))


def main(pin, pout):
    raw = json.load(open(pin))
    ty = raw["partition_types"]
    parts = {p["name"]: p for p in raw["partitions"]}
    # ---- exact old forms (refuse a second run) ----
    for tn in (T2, T42):
        assert ty[tn]["outline_um"] == OLD[tn], f"{tn}: outline {ty[tn]['outline_um']} != {OLD[tn]} (already applied?)"
    for pn in (P2, P42):
        assert parts[pn]["origin_um"] == OLD_ORG[pn], f"{pn}: origin {parts[pn]['origin_um']} (already applied?)"
    assert parts[P2]["type"] == T2 and parts[P2]["orient"] == "R0"
    assert parts[P42]["type"] == T42 and parts[P42]["orient"] == "MY"
    assert sum(1 for p in raw["partitions"] if p["type"] in (T2, T42)) == 2, "t2/t42 must have one instance each"
    assert "hard_cores" not in ty[T2]
    t = ty[T42]
    assert len(t["hard_cores"]) == 27 and len(t["internal_stations"]) == 117
    assert any(c["inst"] == "u_lf.u_vn.u_a" and c["origin_um"] == [760.32, 699.84] and c["orient"] == "MY"
               for c in t["hard_cores"]), "t42 u_vn.u_a old form"
    for tn in (T2, T42):
        tt = ty[tn]
        for s in tt.get("ft_slots", []):
            for f, w in ((s["in_face"], s["in_window_um"]), (s["out_face"], s["out_window_um"])):
                assert f in "NS" and w[1] <= NEW[tn][0], f"{tn}: ft window {w} outside new outline"
        for b in tt["buses"]:
            assert b["face"] in "NS" and b["window_um"][1] <= NEW[tn][0], f"{tn}: bus {b['name']}"
        for b in tt["clock"]["landing_contract"]["bands"].values():
            assert b["rect_um"][2] <= NEW[tn][0]
        for e in tt["clock"]["edge_clocks"]:
            assert e["tap_um"][0] <= NEW[tn][0]
    # ---- t2 / t42 outlines + s_4N_L0 origin ----
    for tn in (T2, T42):
        ty[tn]["outline_um"] = list(NEW[tn])
    parts[P42]["origin_um"] = list(NEW_ORG[P42])
    # ---- t42 hard cores ----
    import search as S
    plan_cores = {c["inst"]: c for c in t["hard_cores"]}
    pins = {}
    for c in t["hard_cores"]:
        pf = os.path.join(HERE, c["pins_file"])
        pins[c["inst"]] = {p["name"]: p for p in json.load(open(pf))["pins"]}
    old = copy.deepcopy(plan_cores)
    P, V = S.expand(PLACE["place"], PLACE.get("views", {}))
    for inst, c in plan_cores.items():
        xy = P[inst]
        orient = "MY" if (inst in S.VIEWABLE and V.get(inst)) else "R0"
        if inst not in S.VIEWABLE:
            assert c["orient"] == "R0"
        c["origin_um"] = [round(xy[0], 4), round(xy[1], 4)]
        c["orient"] = orient
        c["track_offset_um"] = list(TOFF[orient])
        if "_tpl" in c.get("pins_file", ""):
            c["note"] = f"{TAG}: re-placed (cores/leaf/search.py s44, 1071.36 wide) | TYPE-REDUCE-2: template table " \
                        f"{c['pins_file']} (orient R0->{orient})"
        else:
            c["note"] = (c.get("note", "") + f" | {TAG}: re-placed (search.py s44)").lstrip(" |")

    def pin_xy(inst, name, c):
        p = pins[inst][name]
        w = c["outline_um"][0]
        px = (w - p["x"]) if c["orient"] == "MY" else p["x"]
        return c["origin_um"][0] + c["track_offset_um"][0] + px

    for tp in t["clock"].get("taps", []):
        if tp.get("kind") != "core":
            continue
        inst = tp["name"].rsplit(".", 1)[0]
        c, o = plan_cores[inst], old[inst]
        tp["xy"] = [round(pin_xy(inst, "clk", c), 4), round(tp["xy"][1] - o["origin_um"][1] + c["origin_um"][1], 4)]
        tp["note"] = tp.get("note", "") + f" | {TAG}: moved with its core"
    # internal stations on the new arrangement (search's own model = gen_plan_v4.core_internal_stations)
    T = S.Type(dict(type=T42, key="leaf", w=NEW[T42][0], h=H, buses=t["buses"], ftsl=t["ft_slots"]))
    o = T.cores(P, V)
    assert not S.legal(T, o), "illegal core arrangement"
    ents, icyc = S.G.core_internal_stations(S.K, o, T.w, T.h, T.buses)
    t["internal_stations"] = ents
    # ---- collector trees on the new outlines / cores ----
    import schema, reset_tree as RT
    Pn = schema.Plan(raw, pin)
    for tn in (T2, T42):
        lc = ty[tn]["clock"]["landing_contract"]
        lc["collector_tree"] = RT.for_type(Pn, tn)
    raw.setdefault("note", "")
    json.dump(raw, open(pout, "w"), indent=1)
    print(f"{TAG}: t2 {OLD[T2]} -> {NEW[T2]}; t42 {OLD[T42]} -> {NEW[T42]}, {P42} origin -> {NEW_ORG[P42]}; "
          f"27 cores re-placed, {len(ents)} internal stations ({icyc} cycles), collector trees recomputed")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
