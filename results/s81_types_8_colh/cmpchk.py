# S81-TYPES-8-COLH: per col_h type, base vs new plan: tap rule, grid taps equal, reset solve identity equal
import sys, json
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import schema, taps, reset_tree as RT
def load(p): return schema.Plan(schema.load(p))
B, N = load(sys.argv[2]), load(sys.argv[3])
only = sys.argv[4].split(",") if len(sys.argv) > 4 else None
def ident(t):
    t = json.loads(json.dumps(t))
    for c in (t or {}).get("core_resets") or []: c.pop("physical_inst", None)
    return json.dumps(t, sort_keys=True)
def tapok(P, tn):
    mode = (P.types[tn].get("clock") or {}).get("tap_mode")
    try:
        g = [tuple(x) for x in schema._grid_taps(P, tn)] if mode != "explicit" else []
        if mode == "grid+explicit": taps.grid_explicit_sites(P, tn); taps.grid_explicit_taps(P, tn)
        elif mode == "explicit": taps.explicit_tap_sites(P, tn)
        return True, g, ""
    except Exception as e: return False, None, str(e)[:120]
out = {}
for tn in N.types:
    if not tn.startswith(("col_h9", "col_h10")): continue
    if only and tn not in only: continue
    if json.dumps(B.types[tn], sort_keys=True) == json.dumps(N.types[tn], sort_keys=True):
        print("SAME", tn); continue
    ok, g1, e = tapok(N, tn); _, g0, _ = tapok(B, tn)
    try: r = ident(RT.for_type(B, tn)) == ident(RT.for_type(N, tn))
    except Exception as ex: r = "ERR " + str(ex)[:100]
    print("CHK", tn, "taps_ok", ok, "grid_same", g0 == g1, "reset_same", r, e, flush=True)
