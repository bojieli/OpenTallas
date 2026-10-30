"""DIE-S81-36: rank every existing final leaf hard_cores arrangement (same bus face) for each KV leaf type on the
generator's leaf ranking key (faces away, lanes behind, reach excess, station cycles) in the KV type's own buses/ft."""
import json, sys, os, copy
sys.path.insert(0, "physical/die_plan/s81/cores/leaf")
sys.argv_save = sys.argv
import search as S
G = S.G
plan = json.load(open(sys.argv[1]))
pt = plan["partition_types"]
res = {}
for k in (1, 2, 3, 4, 5):
    tn = "ot_s81sl_kv_leaf__t%d" % k
    t = pt[tn]
    w, h = t["outline_um"]
    T = S.Type(dict(type=tn, w=w, h=h, buses=t["buses"], ftsl=t["ft_slots"]))
    face = {b["face"] for b in t["buses"]}
    rows = []
    for ln, L in pt.items():
        if not ln.startswith("ot_s81sl_leaf__") or {b["face"] for b in L["buses"]} != face:
            continue
        o = copy.deepcopy(L["hard_cores"])
        try:
            lg = S.legal(T, [c for c in o if c["inst"] in S.CORES])
            fa = G.core_faces_away(S.K, o, w, h, T.buses)
            rx = S.reach_excess(T, o)
            ents, icyc = G.core_internal_stations(S.K, o, w, h, T.buses)
            ft = sum(max(0, G.ft_stations_macro(s, o, w, h, smax=S.SMAX) - T.k0[i]) for i, s in enumerate(T.ftsl))
            bits = sum(len(e["regs_um"]) * e["bits"] for e in ents)
            lb, lbu = G.core_lanes_behind(S.K, o)
            key = (fa, lb, rx, round(icyc + ft + bits / G.STATION_BITS_PER_CYCLE, 2))
            rows.append((key, ln, dict(legal=lg, ft_add=ft, int_cycles=icyc, station_bits=bits)))
        except Exception as e:
            rows.append(((9e9,), ln, dict(err=repr(e)[:200])))
    rows.sort(key=lambda r: r[0])
    res[tn] = rows[:6]
    print(tn, face, len(rows))
    for r in rows[:6]:
        print("   ", r)
json.dump(res, open(sys.argv[2], "w"), indent=1, default=str)
