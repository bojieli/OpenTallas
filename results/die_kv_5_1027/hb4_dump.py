"""DIE-KV-5 HB4 PREP probe: run the MAIN die_sta_related (no fork: same module, same args as DIE-KV-4 sta_reccal) and dump
the per-pair records the summary hides:
  * kit-contract hold per related tap pair (FF, classes intra / seam): damage = lc - ea - CPPR credit (nominal) and
    damage + clock OCV (R18 form), vs the plan kit window W;
  * seam bits per tap pair (DC.seam_pairs, nearest-tap) for the cell count.
Nothing in the gate changes; the wrapper only records arguments/locals the tool already computes.
    hb4_dump.py TOOLDIR DUMP_OUT.json -- <die_sta_related args>"""
import json, sys
tool, dump_out = sys.argv[1], sys.argv[2]
assert sys.argv[3] == "--"
sys.path.insert(0, tool)
import die_sta_related as DS

REC = {"kit": [], "seam_bits": None}
_tc, _sb = DS.time_class, DS.seam_bits


def time_class(pairs, taps, rng, reg, lat_tol, period, unc_s, unc_h, landed=False, window=None, hold_window=None, **kw):
    out = _tc(pairs, taps, rng, reg, lat_tol, period, unc_s, unc_h, landed=landed, window=window,
              hold_window=hold_window, **kw)
    if hold_window is not None and pairs:
        ocv = kw.get("ocv")
        rows = []
        for a, b, tag in pairs:
            A, B = taps[a], taps[b]
            node = DS.pair_node(A, B)
            la, ea, lc, ec = DS.arr4(A, B, node)
            cr = DS.credit(rng, node, la, ea, lc, ec)
            dmg = lc - ea - cr
            o = ocv(a, b, "hold") if ocv is not None else 0.0
            rows.append(dict(launch=a, capture=b, where=tag, launch_part=A.get("part"), capture_part=B.get("part"),
                             damage_ps=round(dmg, 2), ocv_hold_ps=round(o, 2)))
        REC["kit"].append(dict(window_ps=float(hold_window["ps"]), basis=hold_window["basis"],
                               neg_pairs_tool=out.get("kit_contract_hold", {}).get("neg_pairs"),
                               worst_bound_tool=out.get("kit_contract_hold", {}).get("worst_hold_bound_ps"),
                               pairs=rows))
    return out


def seam_bits(*a, **k):
    r = _sb(*a, **k)
    REC["seam_bits"] = [[x, y, n] for (x, y), n in r.items()]
    return r


DS.time_class, DS.seam_bits = time_class, seam_bits
rc = DS.main(sys.argv[4:])
json.dump(REC, open(dump_out, "w"))
print("DUMP", dump_out, [(r["window_ps"], r["neg_pairs_tool"], r["worst_bound_tool"], len(r["pairs"])) for r in REC["kit"]])
sys.exit(rc or 0)
