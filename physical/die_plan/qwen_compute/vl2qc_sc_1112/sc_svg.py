"""VL2QC-SC intent SVG: one type, before (left) and after (right): outline, hard core, landing bands, ft station
register columns (bit sites) and centre-line chains.  usage: sc_svg.py BEFORE.json AFTER.json TYPE OUT.svg"""
import json, sys
b, a, tn, out = sys.argv[1:5]
P = [json.load(open(b))["partition_types"][tn], json.load(open(a))["partition_types"][tn]]
S = 0.5; GAP = 60
W, H = P[0]["outline_um"]
COL = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf", "#ff7f0e"]
o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{2*W*S+3*GAP}" height="{H*S+2*GAP}" font-family="sans-serif" font-size="10">',
     '<rect width="100%" height="100%" fill="white"/>']
for k, t in enumerate(P):
    ox = GAP + k * (W * S + GAP); oy = GAP
    X = lambda x: ox + x * S; Y = lambda y: oy + (H - y) * S
    o.append(f'<text x="{ox}" y="{oy-20}" font-size="13">{tn} {"BEFORE s25" if k == 0 else "AFTER VL2QC-SC"}</text>')
    o.append(f'<rect x="{X(0)}" y="{Y(H)}" width="{W*S}" height="{H*S}" fill="none" stroke="black"/>')
    for c in t.get("hard_cores") or []:
        (x, y), (w, h) = c["origin_um"], c["outline_um"]
        o.append(f'<rect x="{X(x)}" y="{Y(y+h)}" width="{w*S}" height="{h*S}" fill="#ccc" stroke="#555"/>'
                 f'<text x="{X(x)+4}" y="{Y(y+h)+12}">{c["inst"].split(".")[-1]} {c["module"]}</text>')
    for bn, bd in ((t.get("clock") or {}).get("landing_contract") or {}).get("bands", {}).items():
        x0, y0, x1, y1 = bd["rect_um"]
        o.append(f'<rect x="{X(x0)}" y="{Y(y1)}" width="{(x1-x0)*S}" height="{(y1-y0)*S}" fill="#ffd70080" stroke="#b8860b"/>')
    for i, f in enumerate(t.get("ft_slots") or []):
        col = COL[i % len(COL)]
        r = f.get("regs_um") or []
        pts = " ".join(f"{X(p[0]):.1f},{Y(p[1]):.1f}" for p in r)
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.2"/>')
        for st in f.get("bit_sites_um") or []:
            for p in st[::8]:
                o.append(f'<circle cx="{X(p[0]):.1f}" cy="{Y(p[1]):.1f}" r="0.7" fill="{col}"/>')
        if r:
            o.append(f'<text x="{X(r[-1][0])+2:.1f}" y="{Y(r[-1][1])-2:.1f}" fill="{col}" font-size="8">{f["name"]}</text>')
o.append("</svg>")
open(out, "w").write("\n".join(o))
print("wrote", out)
