"""HBM-STREETS-2 street event (what-if + apply): spread hard cores inside listed partition types so every gap between
two facing cores is either 0 (abutted) or >= T (a street); grows nothing, reports types whose cores leave the outline."""
import json, sys, copy

def spread_type(t, T=17.28, eps=1e-6, only=None, axes=(0, 1)):
    hcs = [c for c in t.get("hard_cores", []) if (only is None or c["module"] in only)]
    moved = {}
    for ax in axes:
        o = 1 - ax
        # cumulative shift: process cores in order of origin along ax
        order = sorted(hcs, key=lambda c: c["origin_um"][ax])
        shift = {id(c): 0.0 for c in hcs}
        for c in order:
            lo = c["origin_um"][ax]
            need = 0.0
            for d in hcs:
                if d is c:
                    continue
                d_hi = d["origin_um"][ax] + d["outline_um"][ax]
                ov = min(c["origin_um"][o] + c["outline_um"][o], d["origin_um"][o] + d["outline_um"][o]) - max(c["origin_um"][o], d["origin_um"][o])
                gap = lo - d_hi
                if ov > eps and -eps < gap < T - eps:
                    need = max(need, shift[id(d)] + (T - gap))
                elif ov > eps and gap >= T - eps:
                    need = max(need, shift[id(d)] - (gap - T))   # keep at least T after d moved
            shift[id(c)] = max(0.0, need)
        for c in hcs:
            if shift[id(c)] > eps:
                c["origin_um"][ax] = round(c["origin_um"][ax] + shift[id(c)], 4)
                moved.setdefault(c["inst"], [0.0, 0.0])[ax] = round(shift[id(c)], 4)
    W, H = t["outline_um"]
    over = [c["inst"] for c in t.get("hard_cores", []) if c["origin_um"][0] + c["outline_um"][0] > W + eps or c["origin_um"][1] + c["outline_um"][1] > H + eps]
    return moved, over

if __name__ == "__main__":
    raw = json.load(open(sys.argv[1]))
    for tn in sys.argv[2].split(","):
        m, over = spread_type(raw["partition_types"][tn])
        print(tn, "moved", len(m), "outside outline", over)
