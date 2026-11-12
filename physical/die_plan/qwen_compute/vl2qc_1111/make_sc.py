"""VISLAYOUT2-QC sl_sc structural fix (AMENDMENTS 3+4): the single leaf core u_core (244.56 x 514.08) sits 23 um from the E
face, and the E-face ft windows (x_fw_fe_p1/p2, x_st_a_fe, x_stm_fe, x_fe_stm_p1, ~2.4k bits at y 667-1110) are fed
up that 23-um gap (914 planned bit sites at x 604.8), so GRT routes the W->E crossings over the core on M6 (real ov
M6-dominant: slw_sc_v2 a19 914 of 1171).  Re-site: core W by DX (default 25.92 -> origin x 319.68, 8.64 lattice),
E gap 23.3 -> 49.2 um (~13 um / 600 b x 2.3k b), a straight macro-free E channel.  Plan points in the core's y span
whose x lies in the band the core moves into are shifted W by the same DX so they stay off the core.
usage: make_sc.py BASE.json OUT.json DELTA.json [DX]"""
import hashlib, json, sys
base, out, dout = sys.argv[1:4]
DX = float(sys.argv[4]) if len(sys.argv) > 4 else 25.92
G = 8.64
raw = open(base, "rb").read(); p = json.loads(raw)
edits = []


def pts(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("window_um", "outline_um", "rect_um", "origin_um", "resized_from_um", "origin_rect_um"):
                continue
            yield from pts(v, path + "." + k)
    elif isinstance(o, list):
        if len(o) == 2 and all(isinstance(x, (int, float)) for x in o):
            yield path, o
        else:
            for i, v in enumerate(o):
                yield from pts(v, f"{path}[{i}]")


for n, t in p["partition_types"].items():
    if "_sc_" not in n or len(t.get("hard_cores") or []) != 1:
        continue
    c = t["hard_cores"][0]
    (x0, y0), (w, h) = c["origin_um"], c["outline_um"]
    W = t["outline_um"][0]
    nx = round(x0 - DX, 4)
    assert abs(nx / G - round(nx / G)) < 1e-6
    lo, hi = nx - 4.32, x0 + 4.32
    moved = 0
    for pa, xy in pts(t):
        if pa.startswith(".hard_cores"):
            continue
        if lo <= xy[0] <= hi and y0 - 4.32 <= xy[1] <= y0 + h + 4.32:
            xy[0] = round(xy[0] - DX, 4); moved += 1
    edits.append(dict(type=n, core=c.get("inst") or c.get("name"), was=[x0, y0], now=[nx, y0], e_gap_um=round(W - nx - w, 2),
                      points_shifted=moved))
    c["origin_um"] = [nx, y0]
s = json.dumps(p, indent=1)
open(out, "w").write(s)
sha = hashlib.sha256(s.encode()).hexdigest()
json.dump(dict(base_sha256=hashlib.sha256(raw).hexdigest(), plan_sha256=sha, dx=DX, edits=edits), open(dout, "w"), indent=1)
for e in edits:
    print(e)
print("sha256", sha[:12])
