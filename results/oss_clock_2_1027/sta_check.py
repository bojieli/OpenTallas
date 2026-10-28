#!/usr/bin/env python3
"""OSS-CLOCK-2: OpenSTA arrivals vs the mscts model on a built region tree (no spice).
    sta_check.py BUILD_DIR SPEC.json  -> per corner: model vs STA tap arrival, latency skew (arrival + insertion),
    crossing nominal d (model vs STA)."""
import json
import sys
from pathlib import Path

d, specp = Path(sys.argv[1]), sys.argv[2]
tree = json.loads((d / "tree.json").read_text())
spec = json.loads(Path(specp).read_text())
ins = {s["name"]: s.get("insertion_ps", {}) for s in spec["sinks"]}
out = {}
for c in ("TT", "FF"):
    st = {}
    for ln in (d / f"sta_arr_{c}.txt").read_text().splitlines():
        p, v = ln.split()
        st[p.split("/")[0][2:]] = float(v)
    r0 = st.pop(tree["root"])
    mod = tree["model_arrival_ps"][c]
    rows = []
    for s, m in mod.items():
        n = s[2:]
        rows.append((n, m, st[s] - r0, ins[n].get(c, 0.0)))
    ratio = sum(m for _, m, _, _ in rows) / sum(a for _, _, a, _ in rows)
    dm = [m - a for _, m, a, _ in rows]
    lat = [a + i for _, _, a, i in rows]
    latm = [m + i for _, m, _, i in rows]
    sta = {n: a + i for n, _, a, i in rows}
    modl = {n: m + i for n, m, _, i in rows}
    xd = [abs((sta[x["b"]] - sta[x["a"]]) - (modl[x["b"]] - modl[x["a"]])) for x in tree["crossings"]]
    out[c] = dict(sinks=len(rows), model_over_sta=round(ratio, 4), model_minus_sta_ps=[round(min(dm), 1), round(max(dm), 1)],
                  sta_tap_arrival_ps=[round(min(a for _, _, a, _ in rows), 1), round(max(a for _, _, a, _ in rows), 1)],
                  sta_latency_skew_ps=round(max(lat) - min(lat), 1), model_latency_skew_ps=round(max(latm) - min(latm), 1),
                  crossing_d_model_vs_sta_max_ps=round(max(xd), 1) if xd else None)
print(json.dumps(dict(dir=d.name, **out)))
(d / "sta_check.json").write_text(json.dumps(out, indent=1) + "\n")
