"""CPL-HBM-B1 hcol S2 intent sheets + SVG (t19 ladder vs re-layout) for one type.
usage: sheet.py T19_PLAN.json CAND_PLAN.json TYPE TRACE.json REP.json OUTDIR"""
import json, sys, re, hashlib, collections

t19p, candp, tn, trf, repf, od = sys.argv[1:7]
A = json.load(open(t19p))["partition_types"][tn]; B = json.load(open(candp))["partition_types"][tn]
tr = json.load(open(trf)); rep = json.load(open(repf))
W, H = B["outline_um"]
COL = {"c0": "#4c78a8", "c1": "#f58518", "c2": "#54a24b", "c3": "#b279a2", "bank": "#9d9d9d"}


def role(i):
    m = re.search(r"r(\d)c(\d)_k(\d)h(\d)(?:__(r[ab]))?$", i)
    if m: return "c" + m.group(2), f"r{m.group(1)}c{m.group(2)}_k{m.group(3)}", ("h1" if m.group(4) == "1" else m.group(5))
    return "bank", re.sub(r".*bank128_", "", i), "bank"


def ctr(h): return (h["origin_um"][0] + h["outline_um"][0] / 2, h["origin_um"][1] + h["outline_um"][1] / 2)


def svg(T, title, x0):
    s = [f'<g transform="translate({x0},20)"><text x="0" y="-6" font-size="13" font-family="sans-serif">{title}</text>']
    sc = 0.32; Ht = H * sc
    Y = lambda y: Ht - y * sc
    s.append(f'<rect x="0" y="0" width="{W*sc:.1f}" height="{Ht:.1f}" fill="#fafafa" stroke="#333"/>')
    for b in T["buses"]:
        lo, hi = b["window_um"]; f = b["face"]; w = 4
        if f in ("E", "W"):
            x = W * sc if f == "E" else 0; s.append(f'<rect x="{x - w/2:.1f}" y="{Y(hi):.1f}" width="{w}" height="{(hi-lo)*sc:.1f}" fill="#d62728"/>')
            s.append(f'<text x="{x + (6 if f == "E" else -6):.1f}" y="{Y((lo+hi)/2):.1f}" font-size="8" text-anchor="{"start" if f == "E" else "end"}" font-family="sans-serif">{b["name"]}</text>')
        else:
            y = 0 if f == "N" else Ht; s.append(f'<rect x="{lo*sc:.1f}" y="{y - w/2:.1f}" width="{(hi-lo)*sc:.1f}" height="{w}" fill="#d62728"/>')
            s.append(f'<text x="{(lo+hi)/2*sc:.1f}" y="{y + (-6 if f == "N" else 12):.1f}" font-size="8" text-anchor="middle" font-family="sans-serif">{b["name"]}</text>')
    for f in T.get("ft_slots") or []:
        pts = " ".join(f"{p[0]*sc:.1f},{Y(p[1]):.1f}" for p in f["regs_um"])
        s.append(f'<polyline points="{pts}" fill="none" stroke="#bbb" stroke-width="0.6"/>')
    for st in T.get("internal_stations") or []:
        for p in st["regs_um"]:
            s.append(f'<rect x="{p[0]*sc-0.8:.1f}" y="{Y(p[1])-0.8:.1f}" width="1.6" height="1.6" fill="#888"/>')
    stacks = collections.defaultdict(dict)
    for h in T["hard_cores"]:
        r, st, part = role(h["inst"]); (x, y), (w, hh) = h["origin_um"], h["outline_um"]
        s.append(f'<rect x="{x*sc:.1f}" y="{Y(y+hh):.1f}" width="{w*sc:.1f}" height="{hh*sc:.1f}" fill="{COL[r]}" fill-opacity="0.55" stroke="#222" stroke-width="0.5"/>')
        lab = st.replace("_", " ") + ("" if part == "bank" else " " + part)
        s.append(f'<text x="{(x+w/2)*sc:.1f}" y="{Y(y+hh/2)+3:.1f}" font-size="6" text-anchor="middle" font-family="sans-serif">{lab}</text>')
        if r != "bank": stacks[st][part] = ctr(h)
    for st, parts in stacks.items():          # h0 -> h1 arrows (bound 33-bit direct pair)
        if "h1" in parts:
            for p in ("ra", "rb"):
                if p in parts:
                    a, b = parts[p], parts["h1"]
                    s.append(f'<line x1="{a[0]*sc:.1f}" y1="{Y(a[1]):.1f}" x2="{b[0]*sc:.1f}" y2="{Y(b[1]):.1f}" stroke="#000" stroke-width="0.9" marker-end="url(#ar)"/>')
    tap = T["clock"]["tap_um"]; s.append(f'<circle cx="{tap[0]*sc:.1f}" cy="{Y(tap[1]):.1f}" r="3" fill="none" stroke="#e377c2" stroke-width="1.2"/>')
    s.append("</g>")
    return "\n".join(s), W * sc


ga, wa = svg(A, f"{tn} t19 ladder c18 (6391dea6)", 10)
gb, wb = svg(B, f"{tn} CPL-HBM-B1 hcol S2", 10 + wa + 80)
doc = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(wa + wb + 110)}" height="{int(H*0.32 + 60)}">'
       '<defs><marker id="ar" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L6,3 L0,6 z"/></marker></defs>'
       '<rect width="100%" height="100%" fill="white"/>' + ga + gb +
       f'<text x="10" y="{int(H*0.32 + 50)}" font-size="9" font-family="sans-serif">blue c0 / orange c1 / green c2 / purple c3 idx stacks (h0 ra, rb -> h1 arrows = bound 33-bit direct pairs), grey banks; red face windows; '
       'grey lines ft-slot register chains; grey squares plan-station registers; pink ring clock tap</text></svg>')
open(f"{od}/{tn}.svg", "w").write(doc)
# intent sheet
lay = {h["inst"]: [h["origin_um"][0], h["origin_um"][1], h.get("orient") or "R0"] for h in B["hard_cores"]}
roles = collections.defaultdict(list)
for i in lay:
    r, st, part = role(i)
    if r != "bank": roles[r].append(st)
links = collections.Counter()
for l in tr["links"]:
    a, b = l["src"], l["dst"]
    if a.startswith("bus:") == b.startswith("bus:"): continue
    m = re.search(r"r(\d)c(\d)_k\dh(\d)", a + b)
    if m: links[("c" + m.group(2), ("h1" if m.group(3) == "1" else "h0"), (a if a.startswith("bus:") else b)[4:], "in" if a.startswith("bus:") else "out", l["regs_min"])] += 1
sheet = dict(
    type=tn, base_plan="t19 6391dea6a0b38710e0da6365e279d9bd3e89ab50f3777cc94c8765546ee06b71", outline_um=W and [W, H],
    layout=lay,
    chain_roles={r: sorted(set(v)) for r, v in roles.items()},
    window_links=[dict(chain=k[0], half=k[1], bus=k[2], dir=k[3], regs=k[4], n=v) for k, v in sorted(links.items())],
    critical_pairs=dict(h0_h1="bound 33-bit direct (0 regs) h0 ra->rb->h1 per stack: centre <= 405 um (stscan missing>405 gate)",
                        one_reg_face_links="window <-> core with 1 relay register: L1 <= 810 um", h0h1_max_um=rep["h0h1_max"],
                        reach_violations_after=rep["reach_viol"]),
    re_sited=dict(ft_slots=[r for r in rep["ft_changes"]], plan_stations=len(rep["st_changes"]), plan_station_regs=sum(r.get("moved", 0) for r in rep["st_changes"])),
    rationale=("Ladder c18 shelf-packed each idx stack's h0 halves and h1 on different shelves (h0->h1 centre up to 2.4 mm, stscan missing>405). "
               "Here each stack is one frame (h1 + ra + rb, 4.32/6.05 um apart, h0->h1 centre <= 331 um). Banks keep their ladder sites "
               "(q_b011 pair7 and the q_b010__physical_v1 bank rows 1 and 3 move to open frame slots), so plan-station counts stay as bound; "
               "frames are placed where their soft relay counts reach their windows (1-reg links <= 810 um, 3-reg <= 1620 um), "
               "frame rows sit between the 250-um die cut lines (or put a line through the 4.32-um h1/h0 gap) so no partition "
               "cut-segment ratio rises above max(0.6, t19), "
               "the clock tap stays in a street, and ft-slot / plan-station register sites covered by a frame are re-sited on free "
               "sites with the same count (hops <= 405 um, first/last hop measured to the far end of the window)."))
open(f"{od}/{tn}.json", "w").write(json.dumps(sheet, indent=1))
print(tn, "sheet ok", len(lay))
