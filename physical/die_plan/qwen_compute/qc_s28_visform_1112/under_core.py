"""every plan point / rect of the sc types under the u_core footprint (+halo), by key path (excl. hard_cores)"""
import json, sys, re, collections
p = json.load(open(sys.argv[1])); m = float(sys.argv[2]) if len(sys.argv) > 2 else 2.16
def walk(o, path):
    if isinstance(o, dict):
        for k, v in o.items(): yield from walk(v, path + [k])
    elif isinstance(o, list):
        if len(o) in (2, 4) and all(isinstance(a, (int, float)) and not isinstance(a, bool) for a in o): yield path, o; return
        for i, v in enumerate(o): yield from walk(v, path + [i])
for tn, t in sorted(p["partition_types"].items()):
    if not re.match(r"^(sle|slw)_sc_", tn): continue
    h = t["hard_cores"][0]; (ox, oy), (w, hh) = h["origin_um"], h["outline_um"]; R = (ox - m, oy - m, ox + w + m, oy + hh + m)
    c = collections.Counter()
    for path, v in walk(t, []):
        if path[0] in ("hard_cores", "buses") or path[-1] in ("window_um", "out_window_um", "outline_um", "bit_site_cell_um", "resized_from_um"): continue
        key = "/".join(str(x) for x in path if isinstance(x, str))
        if len(v) == 2:
            if R[0] < v[0] < R[2] and R[1] < v[1] < R[3]: c[key] += 1
        else:
            if v[0] < R[2] and v[2] > R[0] and v[1] < R[3] and v[3] > R[1]: c[key + "[rect]"] += 1
    print(tn, dict(c))
