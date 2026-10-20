#!/usr/bin/env python3
"""QW-CB16FULL (10-19): the FULL 16-region landed CB16 parent (4 x 4 A0, one clock region per A0) as hard children only.

Source of truth for the function = the soft fabric qfd_c_b16_dv_fabric.sv (qc_gen.py, MUT 0) + its top qfd_c_b16_dv.sv.
This generator rewrites that netlist mechanically, so every path keeps EXACTLY the fabric's edge count (no re-pricing):
  * soft qfd_c_land_w / qfd_c_land_r (D 4, K 2) -> the CLOSED hard halves qfd_c_land_{w,r}{257,258}_narrow (lo + hi bit
    halves; writer on the source root, reader on the destination root, same D 4 / K 2 static ring, no credit)
  * soft 514-b re-alignment pads (15 triples, 3-deep delay lines):
        variant 'ring' (kit qfd_c_b16_full):  one same-clock hard ring pair per triple (w257/r257 x 2, K 2 = 3 edges)
        variant 'stn'  (kit qfd_c_b16_fullb): three CLOSED qfd_c_stn514 relays per triple (fallback)
  * soft qfd_c_xstn / qfd_c_xstnw -> CLOSED qfd_c_xstn_safe / qfd_c_xstnw_safe; qfd_c_stn514 / 516 = CLOSED views
  * A0 = the diagnostic STAND-IN (qfd_c_b16_dv_diag/a0_standin, 457.92 x 1166.4): NO qualified A0 view exists.  The
    floorplan is A0-shape parametric (A0 LEF read here) and must be regenerated on the qualified A0 LEF.
  * the 1-bit reset trees stay soft (registered stages; sites from the diag tsv, mapped onto the new geometry).
Floorplan: the diag column structure L | c0 MY | A | c1 R0 | T | c2 MY | B | c3 R0 | R kept; corridors and row gaps are
widened until every hard child fits (21.6-um clearance, origins on the 43.2 lattice), children are legalised by
Manhattan spiral search around their mapped diag sites, and every single-cycle wire is checked PER BIT on the real LEF
pins (<= 405 um); landed bank windows (multicycle setup 2 / hold 3) are reported separately (<= ~650 um).
Usage: python3 tools/qwen_cluster/qc_full_kit.py [--check]   (--check: geometry/reach report only, writes nothing)
"""
import json, re, sys, math, collections
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
U = 43.2
CELL = 21.6                     # occupancy grid = clearance quantum
RT = "physical/ref_tile"
FAB = "rtl/physical/qcluster/qfd_c_b16_dv_fabric.sv"
TOPSRC = "rtl/physical/qcluster/qfd_c_b16_dv.sv"
DIAG = "tools/ref_tile/specs_qcluster/qfd_c_b16_dv_diag16rt.json"
DIAG_SDC = "physical/qcluster/qfd_c_b16_dv_quadrants.sdc"
DIAG_SITES = "physical/qcluster/qfd_c_b16_dv_sites.tsv"
KITS = {"soft": "qfd_c_b16_full", "softb": "qfd_c_b16_fullb", "ring": "qfd_c_b16_fullh", "stn": "qfd_c_b16_fullhb"}
KIT_VARIANTS = ("soft", "softb")      # written as kits; "ring" / "stn" (all-hard landing halves) = area study, plan only
HARD = ("ring", "stn")
OUT_RTL = "rtl/physical/qcluster/qfd_c_b16_full.sv"
OUT_SDC = {v: f"physical/qcluster/{k}_regions.sdc" for v, k in KITS.items()}
OUT_SITES = {v: f"physical/qcluster/{k}_sites.tsv" for v, k in KITS.items()}
PLAN = "results/arch/qwen_cluster_1017/q_cluster16/full"
REACH = 405.0
A0_STANDIN = f"{RT}/qfd_c_b16_dv_diag/a0_standin"
VIEW = {
    "qfd_c_stn514": f"{RT}/qfd_c_stn514/views/qfd_c_stn514",
    "qfd_c_stn516": f"{RT}/qfd_c_stn516/views/qfd_c_stn516",
    "qfd_c_xstn_safe": f"{RT}/qfd_c_xstn_safe/views/qfd_c_xstn_safe",
    "qfd_c_xstnw_safe": f"{RT}/qfd_c_xstnw_safe/views/qfd_c_xstnw_safe",
    "qfd_tile_nk_rp2_romleaf_rr": f"{A0_STANDIN}/qfd_tile_nk_rp2_romleaf_rr",
    "qfd_tile_nl_rp2_romleaf_rr": f"{A0_STANDIN}/qfd_tile_nl_rp2_romleaf_rr",
}
for _h in (257, 258):
    for _s in "wr":
        VIEW[f"qfd_c_land_{_s}{_h}_narrow"] = f"{RT}/qfd_c_land_{_s}{_h}_narrow/views/qfd_c_land_{_s}{_h}_narrow"
SOURCES = ["physical/ref_tile/qfd_c_b16_dv_diag/a0_standin/a0_rr_bb.v", "rtl/physical/qcluster/qfd_c_stn.sv",
           "rtl/physical/qcluster/qfd_c_xstn_safe.sv", "rtl/physical/qcluster/qfd_c_land_safe.sv",
           "rtl/physical/qcluster/qfd_q3h_stn.sv", OUT_RTL]

# ---------------------------------------------------------------------------------------------------------------- LEF
def lef(view):
    t = next((ROOT / view).glob("*.lef")).read_text()
    w, h = map(float, re.search(r"SIZE ([\d.]+) BY ([\d.]+)", t).groups())
    pins = {}
    for n, b in re.findall(r"\n\s*PIN (\S+)(.*?)END \1", t, re.S):
        m = re.search(r"RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)", b)
        if m:
            pins[n] = ((float(m[1]) + float(m[3])) / 2, (float(m[2]) + float(m[4])) / 2)
    return w, h, pins

LEFS = {k: lef(v) for k, v in VIEW.items()}

# ------------------------------------------------------------------------------------------------- netlist rewrite
INST_RE = re.compile(r"^(?P<pre>\s*(?:wire\s+(?:\[\d+:0\]\s+)?\w+;\s*)?)(?P<mod>qfd_\w+)(?:\s+#\((?P<par>.*?)\))?\s+(?P<inst>u_\w+)\s+\((?P<ports>.*)\);(?P<cmt>\s*//.*)?$")
PORT_RE = re.compile(r"\.(\w+)\(([^()]*)\)")
CMT_RE = re.compile(r"//\s*\(([\d.]+),\s*([\d.]+)\)\s+(c\dr\d)")

def parse_fabric():
    lines = (ROOT / FAB).read_text().splitlines()
    recs = []
    for i, l in enumerate(lines):
        m = INST_RE.match(l)
        if not m:
            continue
        par = dict(PORT_RE.findall(m["par"] or ""))
        c = CMT_RE.search(m["cmt"] or "")
        recs.append(dict(line=i, mod=m["mod"], par=par, inst=m["inst"], ports=dict(PORT_RE.findall(m["ports"])),
                         pre=m["pre"], cmt=(m["cmt"] or "").strip(), at=(float(c[1]), float(c[2])) if c else None,
                         reg=c[3] if c else None))
    return lines, recs

def pad_triples(recs):
    """the 514-b soft re-alignment pads: chains u_pad_<tag>_0 -> .. -> _(n-1) on one clock, n = 3 or 6 (3-deep groups)."""
    pads = [r for r in recs if r["mod"] == "qfd_q3h_stn" and r["par"].get("W", "1") != "1"]
    by = collections.defaultdict(dict)
    for r in pads:
        m = re.match(r"u_pad_(\w+)_(\d)$", r["inst"]); assert m, r["inst"]
        by[m[1]][int(m[2])] = r
    for tag, d in by.items():
        n = len(d)
        assert sorted(d) == list(range(n)) and n % 3 == 0, (tag, sorted(d))
        assert all(d[k]["ports"]["d"] == f"pad_{tag}_{k - 1}" for k in range(1, n)), tag
        assert all(x["par"]["W"] == "514" and x["ports"]["ck"] == d[0]["ports"]["ck"] for x in d.values()), tag
    return by

def half_insts(name, w, kind):
    h = w // 2
    return [(f"u_{name}_{kind}lo", f"qfd_c_land_{kind}{h}_narrow", 0, h), (f"u_{name}_{kind}hi", f"qfd_c_land_{kind}{h}_narrow", h, h)]

def rewrite(variant):
    """returns (fabric module text, crossings, rings): crossings = [(name, W, src clock, dst clock)], rings likewise."""
    lines, recs = parse_fabric()
    out = list(lines)
    drop_decl = set()
    crossings, rings = [], []
    for r in recs:
        mod, p, inst = r["mod"], r["ports"], r["inst"]
        if mod in ("qfd_c_xstn", "qfd_c_xstnw"):
            out[r["line"]] = lines[r["line"]].replace(f"{mod} {inst}", f"{mod}_safe {inst}", 1)
        elif mod in ("qfd_c_land_w", "qfd_c_land_r") and variant in HARD:
            w = int(r["par"]["W"]); assert w in (514, 516) and r["par"].get("D", "4") == "4", r["inst"]
            name = inst[2:-2]; kind = inst[-1]; assert kind in "wr"
            drop_decl |= {f"{name}_bank", f"{name}_epo", f"{name}_vld"}
            L = [f"    // {inst} -> hard halves (lo / hi bits) {r['cmt']}"]
            if kind == "w":
                L.append(f"    wire [{w - 1}:0] {name}_i = {p['i']};")
                for (hn, hm, lsb, hw) in half_insts(name, w, "w"):
                    s = hn[-2:]
                    L.append(f"    wire [{2 * hw - 1}:0] {name}_{s}_bw, {name}_{s}_be;  wire [43:0] {name}_{s}_v;")
                    L.append(f"    {hm} {hn} (.ck({p['ck']}), .rsi({p['rsi']}), .i({name}_i[{lsb + hw - 1}:{lsb}]), "
                             f".bank_w({name}_{s}_bw), .bank_e({name}_{s}_be), .vld({name}_{s}_v));")
                crossings.append(dict(name=name, w=w, src=p["ck"], at_w=r["at"], reg_w=r["reg"]))
            else:
                o = p["o"]; assert re.fullmatch(r"\w+", o), o
                hs = half_insts(name, w, "r")
                for (hn, hm, lsb, hw) in hs:
                    s = hn[-2:]
                    L.append(f"    wire [{hw - 1}:0] {name}_{s}_o;")
                    L.append(f"    {hm} {hn} (.ck({p['ck']}), .rsi({p['rsi']}), .o({name}_{s}_o), "
                             f".bank_w({name}_{s}_bw), .bank_e({name}_{s}_be), .vld({name}_{s}_v));")
                L.append(f"    assign {o} = {{{name}_hi_o, {name}_lo_o}};")
                x = next(c for c in crossings if c["name"] == name)
                x.update(dst=p["ck"], at_r=r["at"], reg_r=r["reg"])
            out[r["line"]] = "\n".join(L)
    for tag, d in pad_triples(recs).items():
        ck = d[0]["ports"]["ck"]; reg = ck[3:]
        if variant in ("stn", "softb"):
            for k in range(len(d)):
                l = lines[d[k]["line"]]
                out[d[k]["line"]] = l.replace("qfd_q3h_stn #(.W(514), .N(1))", "qfd_c_stn514", 1)
        elif variant == "soft":
            col, row = reg[1], reg[3]
            rsi = f"trst_{col}_{row}"
            for j in range(len(d) // 3):
                name = f"land_pad_{tag}_{j}"
                src = d[0]["ports"]["d"] if j == 0 else f"pad_{tag}_{3 * j - 1}"
                L = [f"    // pads u_pad_{tag}_{3 * j}..{3 * j + 2} (3-deep 514-b delay) -> same-clock soft landing ring (qfd_c_land D 4 / K 2 = 3 edges, checklist 5)",
                     f"    wire [513:0] pad_{tag}_{3 * j + 2};",
                     f"    wire [2055:0] {name}_bank;  wire [11:0] {name}_epo;  wire [3:0] {name}_vld;",
                     f"    qfd_c_land_w #(.W(514), .D(4)) u_{name}_w (.ck({ck}), .rsi({rsi}), .i({src}), .bank({name}_bank), .epo({name}_epo), .vld({name}_vld));",
                     f"    qfd_c_land_r #(.W(514), .D(4), .K(2)) u_{name}_r (.ck({ck}), .rsi({rsi}), .bank({name}_bank), .epo({name}_epo), .vld({name}_vld), .o(pad_{tag}_{3 * j + 2}));"]
                out[d[3 * j]["line"]] = "\n".join(L); out[d[3 * j + 1]["line"]] = ""; out[d[3 * j + 2]["line"]] = ""
                rings.append(dict(name=name, w=514, src=ck, dst=ck, at_w=d[3 * j]["at"], at_r=d[3 * j]["at"], reg_w=reg, reg_r=reg,
                                  pads=[f"u_pad_{tag}_{3 * j + k}" for k in range(3)]))
        else:
            col, row = reg[1], reg[3]
            rsi = f"trst_{col}_{row}"           # the region's A0 reset leaf (same epoch as the A0 that feeds / reads it)
            n = len(d)
            for j in range(n // 3):
                name = f"ring_{tag}_{j}"
                src = d[0]["ports"]["d"] if j == 0 else f"pad_{tag}_{3 * j - 1}"
                L = [f"    // pads u_pad_{tag}_{3 * j}..{3 * j + 2} (3-deep 514-b delay) -> same-clock hard ring pair (D 4 / K 2 = 3 edges, checklist 5)",
                     f"    wire [513:0] pad_{tag}_{3 * j + 2};", f"    wire [513:0] {name}_i = {src};"]
                for (hn, hm, lsb, hw) in half_insts(name, 514, "w"):
                    s = hn[-2:]
                    L.append(f"    wire [513:0] {name}_{s}_bw, {name}_{s}_be;  wire [43:0] {name}_{s}_v;  wire [256:0] {name}_{s}_o;")
                    L.append(f"    {hm} {hn} (.ck({ck}), .rsi({rsi}), .i({name}_i[{lsb + hw - 1}:{lsb}]), .bank_w({name}_{s}_bw), "
                             f".bank_e({name}_{s}_be), .vld({name}_{s}_v));")
                for (hn, hm, lsb, hw) in half_insts(name, 514, "r"):
                    s = hn[-2:]
                    L.append(f"    {hm} {hn} (.ck({ck}), .rsi({rsi}), .o({name}_{s}_o), .bank_w({name}_{s}_bw), "
                             f".bank_e({name}_{s}_be), .vld({name}_{s}_v));")
                L.append(f"    assign pad_{tag}_{3 * j + 2} = {{{name}_hi_o, {name}_lo_o}};")
                out[d[3 * j]["line"]] = "\n".join(L); out[d[3 * j + 1]["line"]] = ""; out[d[3 * j + 2]["line"]] = ""
                at = d[3 * j]["at"]
                rings.append(dict(name=name, w=514, src=ck, dst=ck, at_w=at, at_r=at, reg_w=reg, reg_r=reg))
    txt = "\n".join(out)
    for n in drop_decl:
        txt, k = re.subn(rf"\n\s*wire\s+\[\d+:0\]\s+{n};", "", txt)
        txt = re.sub(rf"wire\s+\[\d+:0\]\s+{n};\s*", "", txt)
        assert not re.search(rf"\b{n}\b", txt), n
    return txt, crossings, rings

def fabric_rtl(variant):
    txt, X, R = rewrite(variant)
    top = KITS[variant]
    txt = txt.replace("module qfd_c_b16_dv_fabric", f"module {top}_fabric", 1)
    hdr = (f"// GENERATED by tools/qwen_cluster/qc_full_kit.py from {FAB} (MUT 0 path) -- do not edit.  QW-CB16FULL variant '{variant}':\n"
           "// landings: " + ("CLOSED hard halves" if variant in HARD else "soft qfd_c_land rings (unchanged)") + "; 3-deep pads -> " +
           {"ring": "hard ring pair", "stn": "3 hard stn514", "soft": "soft same-clock landing ring", "softb": "3 hard stn514"}[variant] +
           "; xstn -> xstn_safe.  Edge counts identical to the fabric.\n")
    t = (ROOT / TOPSRC).read_text()
    t = t.replace("module qfd_c_b16_dv (", f"module {top} (", 1).replace("qfd_c_b16_dv_fabric u_fab", f"{top}_fabric u_fab", 1)
    t = re.sub(r"`timescale[^\n]*\n", "", t)
    return hdr + txt.replace("`timescale 1ns/1ps\n", "") + "\n" + t, X, R

# ---------------------------------------------------------------------------------------------------------- geometry
OLD_X = [("L", 0.0, 86.4), ("c0", 86.4, 544.32), ("A", 544.32, 691.2), ("c1", 691.2, 1149.12), ("T", 1149.12, 1296.0),
         ("c2", 1296.0, 1753.92), ("B", 1753.92, 1900.8), ("c3", 1900.8, 2358.72), ("R", 2358.72, 2445.12)]
OLD_Y = [("m0", 0.0, 86.4), ("r0", 86.4, 1252.8), ("g0", 1252.8, 1382.4), ("r1", 1382.4, 2548.8), ("g1", 2548.8, 2678.4),
         ("r2", 2678.4, 3844.8), ("g2", 3844.8, 3974.4), ("r3", 3974.4, 5140.8), ("m1", 5140.8, 5227.2)]

def axis(old, neww):
    new, a = [], 0.0
    for (k, lo, hi) in old:
        w = neww.get(k, hi - lo); new.append((k, lo, hi, a, a + w)); a += w
    return new, a

def mapv(v, ax):
    for (k, lo, hi, nlo, nhi) in ax:
        if lo - 1e-6 <= v <= hi + 1e-6:
            return nlo + (v - lo) * (nhi - nlo) / (hi - lo)
    return ax[-1][4] if v > ax[-1][2] else 0.0

GEOM = {  # widened channels (um); tile bands keep their width.  Sized by fit (plan.json records the fit).
    # soft-landing variants: L / R / T widened only for the CLOSED xstn(w)_safe (90.72 x 129.6, was 56.16 x 86.4 stand-in);
    # A0 origins stay on the 43.2 lattice (L / R multiples of 43.2, A / T / B = 146.88 + k 43.2)
    "soft": dict(L=172.8, A=276.48, T=276.48, B=190.08, R=172.8, m0=129.6, g0=172.8, g1=172.8, g2=172.8, m1=129.6),   # A / B and row gaps +43.2: two station lanes at 21.6 clearance
    "softb": dict(L=172.8, A=319.68, T=276.48, B=276.48, R=172.8, m0=129.6, g0=172.8, g1=172.8, g2=172.8, m1=129.6),   # + room in A / B for the 45 pad stn514
    "ring": dict(L=280.8, A=496.8, T=453.6, B=496.8, R=280.8, m0=172.8, g0=388.8, g1=388.8, g2=388.8, m1=172.8),
    "stn":  dict(L=280.8, A=453.6, T=453.6, B=453.6, R=280.8, m0=172.8, g0=345.6, g1=345.6, g2=345.6, m1=172.8),
}

def orient_xy(kind, orient, x, y):
    w, h, _ = LEFS[kind]
    if orient == "MX": return x, h - y
    if orient == "MY": return w - x, y
    if orient == "R180": return w - x, h - y
    return x, y

class Floor:
    def __init__(self, W, H, cell=CELL):
        self.W, self.H, self.cell = W, H, cell
        self.nx, self.ny = int(math.ceil(W / cell)), int(math.ceil(H / cell))
        self.occ = np.zeros((self.nx, self.ny), dtype=bool)
    def cells(self, x, y, w, h, pad=1):
        C = self.cell
        return (max(0, int(math.floor(x / C + 1e-6)) - pad), min(self.nx, int(math.ceil((x + w) / C - 1e-6)) + pad),
                max(0, int(math.floor(y / C + 1e-6)) - pad), min(self.ny, int(math.ceil((y + h) / C - 1e-6)) + pad))
    def free(self, x, y, w, h, edge=CELL):
        if x < edge - 1e-6 or y < edge - 1e-6 or x + w > self.W - edge + 1e-6 or y + h > self.H - edge + 1e-6:
            return False
        a, b, c, d = self.cells(x, y, w, h, pad=0)
        return not self.occ[a:b, c:d].any()
    def take(self, x, y, w, h, pad=None):
        a, b, c, d = self.cells(x, y, w, h, pad=self.pad if pad is None else pad)
        self.occ[a:b, c:d] = True

SPIRAL = sorted(((dx, dy) for dx in range(-60, 61) for dy in range(-60, 61)), key=lambda t: (abs(t[0]) + abs(t[1]), abs(t[1]), t))

def legalise(F, w, h, cx, cy, lat=U, edge=CELL):
    """origin on the lattice `lat` nearest (cx, cy) = target CENTRE, Manhattan spiral."""
    x0, y0 = round((cx - w / 2) / lat), round((cy - h / 2) / lat)
    for dx, dy in SPIRAL:
        x, y = (x0 + dx) * lat, (y0 + dy) * lat
        if F.free(x, y, w, h, edge):
            F.take(x, y, w, h)
            return x, y
    raise SystemExit(f"no site for {w}x{h} near ({cx:.0f}, {cy:.0f})")

def placement(variant, X, R):
    diag = json.loads((ROOT / DIAG).read_text())
    ax, W = axis(OLD_X, GEOM[variant]); ay, H = axis(OLD_Y, GEOM[variant])
    W = round(math.ceil(W / U) * U, 3); H = round(math.ceil(H / U) * U, 3)
    soft = variant not in HARD
    F = Floor(W, H, cell=4.32 if soft else CELL)
    F.pad = 5 if soft else 1            # soft variants: 21.6-um clearance between hard children (ref_tile channel rule >= 20 um)
    P = {}
    def put(inst, kind, x, y, orient, reg=None):
        P[inst] = dict(kind=kind, x=round(x, 3), y=round(y, 3), orient=orient, reg=reg)
    kids = {c["inst"]: c for c in diag["children"]}
    _, recs = parse_fabric()
    rec = {f"u_fab.{r['inst']}": r for r in recs}
    # 1. A0 tiles: tile bands are not widened, so an A0 origin maps exactly (snapped to the lattice)
    for n, c in kids.items():
        if not n.startswith("u_t_"):
            continue
        kind = c["view"].split("/")[-1]; w, h, _ = LEFS[kind]
        x = round(mapv(c["at"][0] + 1.0, ax) / U) * U if False else mapv(c["at"][0], ax)
        y = mapv(c["at"][1], ay)
        x, y = round(x / U) * U, round(y / U) * U
        assert F.free(x, y, w, h), n
        F.take(x, y, w, h, pad=5 if soft else 1); put(n, kind, x, y, c["orient"], f"c{n[4]}r{n[6]}")
    # 2. xstn (tap face next to its A0's tap face), then landing / ring stacks, then the relay stations
    items = []
    for n, c in kids.items():
        if n.startswith("u_t_"):
            continue
        r = rec[n]; kind = {"qfd_c_xstn": "qfd_c_xstn_safe", "qfd_c_xstnw": "qfd_c_xstnw_safe"}.get(r["mod"], r["mod"])
        if kind == "qfd_q3h_stn":
            continue
        w, h, _ = LEFS[kind]
        cx, cy = mapv(c["at"][0] + w / 2, ax), mapv(c["at"][1] + h / 2, ay)
        items.append((0 if "xstn" in kind else 2, n, kind, w, h, cx, cy, c["orient"], r["reg"]))
    for X1 in (X + R if variant in HARD else []):
        hk = 257 if X1["w"] == 514 else 258
        aw, ar = X1["at_w"], X1["at_r"]
        flow_up = ar[1] >= aw[1]
        cx, cy = mapv((aw[0] + ar[0]) / 2, ax), mapv((aw[1] + ar[1]) / 2, ay)
        items.append((1, X1["name"], ("stack", hk, flow_up), 194.4, 302.4, cx, cy, None, (X1["reg_w"], X1["reg_r"])))
    if variant in ("stn", "softb"):
        for r in recs:
            if r["mod"] == "qfd_q3h_stn" and r["par"].get("W") == "514":
                w, h, _ = LEFS["qfd_c_stn514"]
                items.append((3, f"u_fab.{r['inst']}", "qfd_c_stn514", w, h, mapv(r["at"][0], ax), mapv(r["at"][1], ay), "R0", r["reg"]))
    if soft:      # corridor lanes: stations snap to the nearest lane (lo + 21.6 + k (w + 21.6)) so the corridor holds two+ lanes
        lanes = {k: (nlo, nhi) for (k, lo, hi, nlo, nhi) in ax if not k.startswith("c")}
        def lane(cx, w):
            for (lo, hi) in lanes.values():
                if lo - 1 <= cx <= hi + 1:
                    xs = [lo + 21.6 + j * (w + 21.6) for j in range(10) if lo + 21.6 + j * (w + 21.6) + w <= hi - 21.6 + 1e-6]
                    if xs:
                        return min(xs, key=lambda x: abs(x + w / 2 - cx)) + w / 2
            return cx
        items = [(pr, n, k, w, h, lane(cx, w) if "stn5" in str(k) else cx, cy, o, r) for (pr, n, k, w, h, cx, cy, o, r) in items]
    items.sort(key=lambda t: (t[0], -t[3] * t[4], t[1]))
    for (pri, n, kind, w, h, cx, cy, orient, reg) in items:
        x, y = legalise(F, w, h, cx, cy, lat=(4.32 if soft and "stn5" in str(kind) else U), edge=30.24 if soft else CELL)
        if isinstance(kind, tuple):
            _, hk, up = kind
            for s, dx in (("lo", 0.0), ("hi", 129.6)):
                if up:
                    put(f"u_fab.u_{n}_w{s}", f"qfd_c_land_w{hk}_narrow", x + dx, y, "MX", reg[0])
                    put(f"u_fab.u_{n}_r{s}", f"qfd_c_land_r{hk}_narrow", x + dx, y + 172.8, "R0", reg[1])
                else:
                    put(f"u_fab.u_{n}_w{s}", f"qfd_c_land_w{hk}_narrow", x + dx, y + 172.8, "R0", reg[0])
                    put(f"u_fab.u_{n}_r{s}", f"qfd_c_land_r{hk}_narrow", x + dx, y, "MX", reg[1])
        else:
            put(n, kind, x, y, orient or "R0", reg)
    return dict(W=W, H=H, ax=ax, ay=ay), P

# ------------------------------------------------------------------------------------------------ bit-level reach
DIR_OUT = {"q", "o", "a_d", "tap_d", "bank_w", "bank_e", "vld", "t_out", "n_y", "tie_hi", "tie_lo"}

def split_expr(e):
    e = e.strip()
    if e.startswith("{"):
        parts, depth, cur = [], 0, ""
        for ch in e[1:-1]:
            if ch == "," and depth == 0:
                parts.append(cur); cur = ""
            else:
                depth += ch in "[{"; depth -= ch in "]}"; cur += ch
        parts.append(cur)
        bits = []
        for p in reversed(parts):          # LSB first
            bits += split_expr(p)
        return bits
    m = re.fullmatch(r"(\w+)\[(\d+):(\d+)\]", e)
    if m:
        return [(m[1], k) for k in range(int(m[3]), int(m[2]) + 1)]
    m = re.fullmatch(r"(\w+)\[(\d+)\]", e)
    if m:
        return [(m[1], int(m[2]))]
    if re.fullmatch(r"\w+", e):
        return [(e, None)]                 # whole net, width resolved later
    return [("?" + e, None)]

def netlist(txt):
    """bit-level driver map over the (flattened by name) top + fabric text: hard child pins only."""
    widths = {}
    for m in re.finditer(r"\b(?:wire|input\s+wire|output\s+wire|input|output)\s+\[(\d+):0\]\s+([\w\s,]+?)(?:;|=|,\s*$|\)|\n)", txt):
        for n in m[2].split(","):
            n = n.strip()
            if re.fullmatch(r"\w+", n): widths[n] = int(m[1]) + 1
    for m in re.finditer(r"\b(?:wire|input\s+wire|output\s+wire)\s+(\w+)\s*[;,=\n]", txt):
        widths.setdefault(m[1], 1)
    alias = {}
    def bits_of(e):
        out = []
        for (n, k) in split_expr(e):
            if k is None:
                out += [(n, j) for j in range(widths.get(n, 1))]
            else:
                out.append((n, k))
        return out
    for m in re.finditer(r"assign\s+(\w+(?:\[\d+(?::\d+)?\])?)\s*=\s*(.+?);", txt):
        rhs = m[2].strip()
        t = re.fullmatch(r"\(MUT == \d+ \? (\w+) : (\w+)\)", rhs)
        if t: rhs = t[2]
        for a, b in zip(bits_of(m[1]), bits_of(rhs)):
            alias[a] = b
    for m in re.finditer(r"wire\s+(?:\[\d+:0\]\s+)?(\w+)\s*=\s*(.+?);", txt):
        rhs = m[2].strip()
        t = re.fullmatch(r"\(MUT == \d+\) \? .* : (\w+)", rhs)
        if t: rhs = t[1]
        if rhs.startswith("~"): continue
        for a, b in zip(bits_of(m[1]), bits_of(rhs)):
            alias[a] = b
    drv, sinks = {}, []
    inst_re = re.compile(r"\b(qfd_\w+)\s+(?:#\((?:[^()]|\([^()]*\))*\)\s+)?(u_\w+)\s+\(((?:[^;])*?)\);", re.S)
    for m in inst_re.finditer(txt):
        mod, inst, ports = m[1], m[2], dict(PORT_RE.findall(m[3]))
        if mod == "qfd_q3h_run":            # MUT 0: D = 0 -> wire
            for a, b in zip(bits_of(ports["q"]), bits_of(ports["d"])):
                alias[a] = b
            continue
        if mod not in LEFS:
            continue
        full = inst if inst.startswith("u_t_") else f"u_fab.{inst}"
        for pin, e in ports.items():
            if pin.startswith("ck") or pin in ("rst_n", "rsi", "sidx", "tile_id", "tie_hi", "tie_lo"):
                continue
            for k, b in enumerate(bits_of(e)):
                if pin in DIR_OUT and not (mod.startswith("qfd_c_land_r") and pin in ("bank_w", "bank_e", "vld")):
                    drv[b] = (full, pin, k)
                else:
                    sinks.append(((full, pin, k), b))
    def resolve(b):
        seen = 0
        while b not in drv and b in alias and seen < 64:
            b = alias[b]; seen += 1
        return drv.get(b), b
    return drv, sinks, resolve, widths

def pin_at(P, inst, pin, k):
    p = P[inst]; w, h, pins = LEFS[p["kind"]]
    n = f"{pin}[{k}]"
    x, y = pins[n] if n in pins else pins[pin]
    x, y = orient_xy(p["kind"], p["orient"], x, y)
    return p["x"] + x, p["y"] + y

def port_xy(env, ranges, faces, port, k, nbits):
    face = next(f for f, l in faces.items() if port in l)
    a, b = ranges[port]
    t = a + (b - a) * (k + 0.5) / max(1, nbits)
    return {"S": (t, 0.0), "N": (t, env["H"]), "W": (0.0, t), "E": (env["W"], t)}[face]

def reach(variant, txt, env, P, ranges, faces):
    drv, sinks, resolve, widths = netlist(txt)
    rows = collections.defaultdict(lambda: [0.0, 0, None, None])
    unresolved = collections.Counter()
    pairs = []
    for (dst, b) in sinks:
        d, base = resolve(b)
        if d is None:
            if base[0] in ranges:      # boundary input port
                s_xy = port_xy(env, ranges, faces, base[0], base[1], widths.get(base[0], 1)); src = ("PORT", base[0])
                pairs.append((("PORT", s_xy), dst))
            else:
                unresolved[base[0]] += 1; continue
        else:
            s_xy = pin_at(P, *d); src = (d[0], d[1])
        t_xy = pin_at(P, *dst)
        if d is not None and d[1] not in ("bank_w", "bank_e", "vld"):
            pairs.append((d, dst))
        dist = abs(s_xy[0] - t_xy[0]) + abs(s_xy[1] - t_xy[1])
        key = (src, (dst[0], dst[1]))
        r = rows[key]; r[1] += 1
        if dist > r[0]: r[0] = dist
    # boundary outputs (bco*, rs, rs_o)
    for port in [p for p in ranges if re.fullmatch(r"bco\d|rs|rs_o", p)]:
        for k in range(widths.get(port, 1)):
            d, base = resolve((port, k))
            if d is None:
                unresolved[port] += 1; continue
            s_xy = pin_at(P, *d); t_xy = port_xy(env, ranges, faces, port, k, widths[port])
            pairs.append((d, ("PORT", s_xy and t_xy)))
            dist = abs(s_xy[0] - t_xy[0]) + abs(s_xy[1] - t_xy[1])
            r = rows[((d[0], d[1]), ("PORT", port))]; r[1] += 1; r[0] = max(r[0], dist)
    out = []
    for (src, dst), (wst, n, _, _) in rows.items():
        bank = src[1] in ("bank_w", "bank_e", "vld")
        out.append(dict(src=".".join(src), dst=".".join(dst), bits=n, worst_um=round(wst, 1),
                        cls="bank window (multicycle setup 2 / hold 3)" if bank else "single-cycle"))
    return out, dict(unresolved), pairs

# --------------------------------------------------------------------------------------------------------- pins
def pins(variant, env):
    diag = json.loads((ROOT / DIAG).read_text())
    ax, ay = env["ax"], env["ay"]
    faces = diag["pins"]; R = {}
    for p, (a, b) in diag["pin_ranges"].items():
        face = next(f for f, l in faces.items() if p in l)
        m = (lambda v: mapv(v, ax)) if face in "NS" else (lambda v: mapv(v, ay))
        if b - a > 2.0:     # bus: keep the width, move the centre
            c = m((a + b) / 2); R[p] = [c - (b - a) / 2, c + (b - a) / 2]
        else:
            c = m(a); R[p] = [c, c + (b - a)]
    # route.pin_balance needs DISJOINT per-port ranges on a face: buses first (slide right if they overlap), then the
    # narrow ports slide out of the bus ranges (qc_reg_kit.py rule)
    for face, ports_ in faces.items():
        lim = env["W"] if face in "NS" else env["H"]
        taken = []
        for p in sorted([p for p in ports_ if R[p][1] - R[p][0] > 2.0], key=lambda p: R[p][0]):
            a, b = R[p]; w = b - a
            while any(not (a + w + 1.0 <= x0 or a >= x1 + 1.0) for (x0, x1) in taken):
                a += 1.0
            assert a + w < lim - 4, (p, a)
            R[p] = [a, a + w]; taken.append((a, a + w))
        for p in [p for p in ports_ if R[p][1] - R[p][0] <= 2.0]:
            a, b = R[p]; w = b - a
            for step in range(0, 20000):
                ok = None
                for sgn in (1, -1):
                    a2 = a + sgn * step * 0.5
                    if a2 < 6 or a2 + w > lim - 6:
                        continue
                    if all(a2 + w + 0.5 <= x0 or a2 >= x1 + 0.5 for (x0, x1) in taken):
                        ok = a2; break
                if ok is not None:
                    break
            R[p] = [ok, ok + w]; taken.append((ok, ok + w))
        for p in ports_:
            R[p] = [round(R[p][0], 3), round(R[p][1], 3)]
    return R, faces, diag

# ---------------------------------------------------------------------------------------------------------------- SDC
def sdc(Xall, variant):
    t = (ROOT / DIAG_SDC).read_text()
    a = t.index("# Q-CLUSTER-LANDALL"); b = t.index('puts "OT_QC_LAND_SDC'); b = t.index("\n", b) + 1
    hdr = f"# GENERATED by tools/qwen_cluster/qc_full_kit.py ({KITS[variant]}) from {DIAG_SDC}; DO NOT EDIT.\n"
    if variant not in HARD:     # soft rings: the diag block, list extended by the same-clock pad rings (land_pad_*)
        m = re.search(r"set ot_qc_lands \{([^}]*)\}", t)
        names = m[1].split() + [x["name"][5:] for x in Xall]
        t2 = t[:m.start()] + "set ot_qc_lands {" + " ".join(names) + "}" + t[m.end():]
        return hdr + t2
    names = sorted({x["name"] for x in Xall})
    blk = ["# QW-CB16FULL: every landed crossing / same-clock ring = hard writer half -> hard reader half (lo, hi); LANDING-CONTRACT L5",
           "# multicycle -setup 2 -hold 3 on the bank / vld paths (window (2 - 4) T + t_hold < dL < 2 T - t_cq - t_setup)",
           "set ot_qc_lands {" + " ".join(names) + "}", "set ot_qc_land_n 0",
           "foreach ot_ln $ot_qc_lands {", "  foreach ot_h {lo hi} {",
           "    set ot_lf [get_cells -quiet u_fab.u_${ot_ln}_w${ot_h}]", "    set ot_lt [get_cells -quiet u_fab.u_${ot_ln}_r${ot_h}]",
           "    if {[llength $ot_lf] == 0 || [llength $ot_lt] == 0} { continue }",
           "    set_multicycle_path -setup 2 -from $ot_lf -to $ot_lt", "    set_multicycle_path -hold 3 -from $ot_lf -to $ot_lt",
           "    incr ot_qc_land_n", "  }", "}",
           'puts "OT_QC_LAND_SDC $ot_qc_land_n of [expr {2 * [llength $ot_qc_lands]}] landed half pairs constrained"', ""]
    return hdr + t[:a] + "\n".join(blk) + t[b:]

# ------------------------------------------------------------------------------------------------------- reset sites
def soft_anchor(txt, P):
    """soft landing halves: writer beside the hard pin that drives its i, reader beside the hard pin its o feeds."""
    drv, sinks, resolve, widths = netlist(txt)
    by_net = collections.defaultdict(list)
    for (dst, b) in sinks:
        by_net[resolve(b)[1][0]].append(dst)
    A = {}
    for m in re.finditer(r"qfd_c_land_([wr]) #\([^;]*?\)\s+(u_\w+)\s+\(([^;]*?)\);", txt):
        side, inst, ports = m[1], m[2], dict(PORT_RE.findall(m[3]))
        if side == "w":
            d, _ = resolve(split_expr(ports["i"])[0][:1] + (0,) if split_expr(ports["i"])[0][1] is None else split_expr(ports["i"])[0])
            if d: A[f"u_fab.{inst}"] = pin_at(P, d[0], d[1], d[2])
        else:
            o = ports["o"]
            ds = by_net.get(o) or []
            if not ds:          # o feeds a soft pad ring / alias: follow one alias step
                ds = [dst for (dst, b) in sinks if resolve(b)[1][0] == o]
            if ds: A[f"u_fab.{inst}"] = pin_at(P, *ds[0])
    return A

def sites(variant, env, P, R=(), anchor=None):
    anchor = anchor or {}
    """the soft reset stages keep their diag sites, mapped onto the widened geometry and pushed out of hard children."""
    ax, ay = env["ax"], env["ay"]
    rects = [(p["x"], p["y"], p["x"] + LEFS[p["kind"]][0], p["y"] + LEFS[p["kind"]][1]) for p in P.values()]
    L = ["# prefix\tx\ty\txlo\txhi  (qc_full_kit.py; fabric_sites_place.tcl)"]
    ring_of = {pd: x["name"] for x in R for pd in x.get("pads", [])}
    for l in (ROOT / DIAG_SITES).read_text().splitlines():
        if l.startswith("#") or not l.strip():
            continue
        p, x, y, xlo, xhi = l.split("\t")
        short = p.split(".", 1)[1]
        if short.startswith("u_pad_"):
            if short not in ring_of or not short.endswith(("_0", "_3")):
                continue
            # one site per soft ring half (ring w and read r both at the pad group's first site)
            for side in ("w", "r"):
                nx, ny = mapv(float(x), env["ax"]), mapv(float(y), env["ay"]) + (6.0 if side == "r" else -6.0)
                L.append(f"u_fab.u_{ring_of[short]}_{side}\t{nx:.3f}\t{ny:.3f}\t{max(0.0, nx - 40):.3f}\t{min(env['W'], nx + 40):.3f}")
            continue
        nx, ny = mapv(float(x), ax), mapv(float(y), ay)
        if p in anchor:          # pulled to its hard neighbour pin, at most 100 um away from it
            axp, ayp = anchor[p]; dd = abs(nx - axp) + abs(ny - ayp)
            if dd > 100:
                f = 100 / dd; nx, ny = axp + (nx - axp) * f, ayp + (ny - ayp) * f
        w = max(30.0, float(xhi) - float(xlo))
        for (a, b, c, d) in rects:      # inside a hard child -> nearest free side
            if a - 4 < nx < c + 4 and b - 4 < ny < d + 4:
                cand = [(abs(nx - (a - 12)), a - 12, ny), (abs(c + 12 - nx), c + 12, ny), (abs(ny - (b - 6)), nx, b - 6), (abs(d + 6 - ny), nx, d + 6)]
                _, nx, ny = min(cand)
        nx = min(max(nx, 8.0), env["W"] - 8.0); ny = min(max(ny, 8.0), env["H"] - 8.0)
        L.append(f"{p}\t{nx:.3f}\t{ny:.3f}\t{max(0.0, nx - w / 2):.3f}\t{min(env['W'], nx + w / 2):.3f}")
    return "\n".join(L) + "\n"

# ---------------------------------------------------------------------------------------------------- spec / plan
def spec(variant, env, P, ranges, faces, diag):
    name = KITS[variant]
    kids = [dict(view=VIEW[p["kind"]], count=1, inst=n, at=[p["x"], p["y"]], orient=p["orient"], at_exact=True) for n, p in P.items()]
    s = {k: v for k, v in diag.items() if k not in ("children", "pin_ranges", "pins", "relay_sites", "abut_plan", "job")}
    src = SOURCES if variant in HARD else SOURCES[:-1] + ["rtl/physical/qcluster/qfd_c_land.sv", SOURCES[-1]]
    s.update(name=name, top=name, diagnostic=True, sources=src, sdc_extra=[OUT_SDC[variant]],
             outline=dict(w=env["W"], h=env["H"], exact=True), child_lattice_um=4.32 if variant not in HARD else 21.6, children=kids, macros=[],
             pins=faces, pin_ranges=ranges, pin_layers=diag.get("pin_layers", {}),
             orfs_vars={"PRE_GLOBAL_PLACE_TCL": "physical/qcluster/fabric_sites_place.tcl",
                        "PRE_DETAIL_PLACE_TCL": "physical/qcluster/fabric_sites_release.tcl",
                        "OT_QC_SITES": OUT_SITES[variant], "GPL_TIMING_DRIVEN": "0", "GPL_ROUTABILITY_DRIVEN": "0"},
             route=dict(pd=0.5, threads=16, peak_ram_gb=192, pin_v="M5", pin_h="M4 M6", macro_halo_um=5.4,
                        io_hold_margin_ns=0.03, hold_margin_ns=0.03, pin_balance=dict(group_max=1, h="M4 M6", v="M5")),
             fill_reason=dict(pin_bound="A0 stand-ins + pin-bound hard stations (1,028-1,032 pins on 51.84 um) + closed xstn_safe; "
                              "soft logic = landing rings + reset stages; channels = the qc_gen corridor plan (cut <= 0.90) widened "
                              "only where the closed xstn_safe needs it; no pocket off the link paths (QW-CB16FULL fill decision)"),
             structural_change="QW-CB16FULL: FULL 16-region landed CB16 parent, one clock region per A0, every seam crossing = "
                               + ("CLOSED hard landing halves qfd_c_land_{w,r}{257,258}_narrow" if variant in HARD else
                                  "a soft qfd_c_land ring (writer on the source root, reader on the destination root)")
                               + " (static D4/K2 ring, no credit), 3-deep pads = "
                               + {"ring": "same-clock hard ring pairs", "stn": "3 CLOSED stn514 relays", "soft": "same-clock soft landing rings",
                                  "softb": "3 CLOSED stn514 relays"}[variant]
                               + ", xstn = CLOSED xstn(w)_safe, relays = CLOSED stn514/516; netlist = the qc_gen fabric MUT 0 with "
                               "identical edge counts; A0 = diagnostic STAND-IN (no qualified A0 view).",
             job=dict(owner="Claude:QW-CB16FULL", branch="claude/qw-cluster3-cb16-1019", tag=KITS[variant][10:],
                      purpose="FULL CB16 landed parent (critical prefix qfd_c_b16: gate + coordinator review only, no submit)",
                      submit=False, hold_merge="QW-CB16FULL diagnostic: A0 STAND-IN", extra_paths=[PLAN],
                      no_bench_reason="critical-prefix PHYSICAL gate only; function = the qc_gen fabric MUT 0 (lockstep bench owed "
                                      "against qfd_c_b16_dv: same edge counts by construction)"))
    s["pin_regs"] = dict(enable=False, reason=diag["pin_regs"]["reason"] + "; landing halves land rsi in 2 stages; every data pin "
                         "lands in a hard station / half register (flop-first / flop-last)")
    s["reset_landing"] = dict(enable=False, reason="RTL lands every rst_<q> in its rpin register + equal-depth soft tree (qc_gen)")
    return s

def _xy(P, t):
    return t[1] if t[0] == "PORT" else pin_at(P, *t)

def improve(env, P, pairs, passes=14):
    """local repair: a relay station on an over-reach single-cycle wire moves (on the 8.64 grid / 4.32 lattice, keeping
    21.6 to every hard child) to the free site that minimises its worst incident wire."""
    # per wire keep its end bits and the middle bit (pins are linear ramps on a face, so the worst bit is an end bit)
    grp = collections.defaultdict(list)
    for (a, b) in pairs:
        grp[(a[0], a[1] if a[0] != "PORT" else None, b[0], b[1])].append((a, b))
    pairs = [x for g_ in grp.values() for x in (g_[0], g_[len(g_) // 2], g_[-1])]
    inc = collections.defaultdict(list)
    for (a, b) in pairs:
        inc[a[0]].append((a, b)); inc[b[0]].append((a, b))
    def worst(n):
        return max((abs(_xy(P, a)[0] - _xy(P, b)[0]) + abs(_xy(P, a)[1] - _xy(P, b)[1]) for (a, b) in inc[n]), default=0.0)
    def occ_except(n):
        F = Floor(env["W"], env["H"], cell=4.32); F.pad = 5
        for m, p in P.items():
            if m == n: continue
            w, h, _ = LEFS[p["kind"]]
            F.take(p["x"], p["y"], w, h, pad=5)
        return F
    moved = []
    for _ in range(passes):
        bad = sorted({n for (a, b) in pairs for n in (a[0], b[0]) if n != "PORT" and "stn5" in P[n]["kind"]
                      and abs(_xy(P, a)[0] - _xy(P, b)[0]) + abs(_xy(P, a)[1] - _xy(P, b)[1]) > REACH})
        if not bad:
            break
        nb = set(bad)
        for n in bad:       # the chain neighbours may move too (a station boxed in by its own predecessor / successor)
            for (a, b) in inc[n]:
                for m in (a[0], b[0]):
                    if m != "PORT" and "stn5" in P[m]["kind"]:
                        nb.add(m)
        for n in sorted(nb, key=lambda m: -worst(m)):
            F = occ_except(n); p = P[n]; w, h, _ = LEFS[p["kind"]]
            best = (worst(n), p["x"], p["y"]); x0, y0 = p["x"], p["y"]
            for dx, dy in SPIRAL[:4000]:
                x, y = round(x0 / 4.32 + dx * 2) * 4.32, round(y0 / 4.32 + dy * 2) * 4.32
                if not F.free(x, y, w, h, 30.24): continue
                p["x"], p["y"] = round(x, 3), round(y, 3)
                wv = worst(n)
                if wv < best[0] - 1e-6: best = (wv, p["x"], p["y"])
            p["x"], p["y"] = best[1], best[2]
            if (best[1], best[2]) != (x0, y0):
                moved.append(dict(inst=n, frm=[x0, y0], to=[best[1], best[2]], worst_um=round(best[0], 1)))
    # joint move of the two relay stations of a remaining over-reach wire (each keeps its other wires <= REACH)
    def dist(a, b):
        return abs(_xy(P, a)[0] - _xy(P, b)[0]) + abs(_xy(P, a)[1] - _xy(P, b)[1])
    for (a, b) in [(a, b) for (a, b) in pairs if a[0] != "PORT" and b[0] != "PORT" and dist(a, b) > REACH
                   and "stn5" in P[a[0]]["kind"] and "stn5" in P[b[0]]["kind"]]:
        if dist(a, b) <= REACH:
            continue
        na, nb_ = a[0], b[0]
        F = occ_except(na)
        pb = P[nb_]; wb, hb, _ = LEFS[pb["kind"]]
        a2, b2 = P[na]["x"], P[na]["y"]
        F2 = Floor(env["W"], env["H"], cell=4.32); F2.pad = 5
        for m, p in P.items():
            if m in (na, nb_): continue
            w, h, _ = LEFS[p["kind"]]; F2.take(p["x"], p["y"], w, h, pad=5)
        def cands(n):
            p = P[n]; w, h, _ = LEFS[p["kind"]]; x0, y0 = p["x"], p["y"]; out = []
            for dx, dy in SPIRAL[:3000]:
                x, y = round(x0 / 4.32 + dx * 2) * 4.32, round(y0 / 4.32 + dy * 2) * 4.32
                if not F2.free(x, y, w, h, 30.24): continue
                p["x"], p["y"] = x, y
                other = max((dist(u, v) for (u, v) in inc[n] if (u, v) != (a, b)), default=0.0)
                if other <= REACH: out.append((x, y))
            p["x"], p["y"] = x0, y0
            return out
        ca, cb = cands(na), cands(nb_)
        best = None
        sa, sb = (P[na]["x"], P[na]["y"]), (P[nb_]["x"], P[nb_]["y"])
        for (xa, ya) in ca:
            P[na]["x"], P[na]["y"] = xa, ya
            for (xb, yb) in cb:
                if abs(xa - xb) < 51.84 + 21.6 and abs(ya - yb) < 51.84 + 21.6: continue
                P[nb_]["x"], P[nb_]["y"] = xb, yb
                dd = dist(a, b)
                if best is None or dd < best[0]: best = (dd, xa, ya, xb, yb)
        if best and best[0] <= REACH:
            P[na]["x"], P[na]["y"], P[nb_]["x"], P[nb_]["y"] = round(best[1], 3), round(best[2], 3), round(best[3], 3), round(best[4], 3)
            moved.append(dict(inst=[na, nb_], frm=[sa, sb], to=[best[1:3], best[3:5]], worst_um=round(best[0], 1), joint=True))
        else:
            P[na]["x"], P[na]["y"] = sa; P[nb_]["x"], P[nb_]["y"] = sb
    return moved

def run(write=True):
    res = {}
    plan = {}
    body = {}
    for v in ("soft", "softb", "ring", "stn"):
        txt, X, R = fabric_rtl(v)
        body[v] = txt
        env, P = placement(v, X, R)
        ranges, faces, diag = pins(v, env)
        rows, unres, pairs = reach(v, txt, env, P, ranges, faces)
        if v not in HARD:
            moved = improve(env, P, pairs)
            rows, unres, pairs = reach(v, txt, env, P, ranges, faces)
        else:
            moved = []
        sc = [r for r in rows if r["cls"] == "single-cycle"]; bk = [r for r in rows if r["cls"] != "single-cycle"]
        kinds = collections.Counter(p["kind"] for p in P.values())
        a0 = sum(LEFS[p["kind"]][0] * LEFS[p["kind"]][1] for p in P.values() if "tile" in p["kind"])
        hard = sum(LEFS[p["kind"]][0] * LEFS[p["kind"]][1] for p in P.values())
        plan[KITS[v]] = dict(
            outline_um=[env["W"], env["H"]], area_mm2=round(env["W"] * env["H"] / 1e6, 3),
            area_vs_diag=round(env["W"] * env["H"] / (2445.12 * 5227.2), 3), channel_widths_um=GEOM[v],
            children=len(P), child_kinds=dict(sorted(kinds.items())), crossings=len(X), rings=len(R),
            hard_fill=round(hard / (env["W"] * env["H"]), 3), a0_fill=round(a0 / (env["W"] * env["H"]), 3),
            single_cycle_max_um=max([r["worst_um"] for r in sc] or [0.0]), single_cycle_over_405=sorted([r for r in sc if r["worst_um"] > REACH], key=lambda r: -r["worst_um"]),
            bank_window_max_um=max([r["worst_um"] for r in bk] or [0.0]), bank_over_650=[r for r in bk if r["worst_um"] > 650],
            unresolved_sink_bits=unres, edges=len(rows), reach_moves=moved)
        res[v] = (env, P, ranges, faces, diag, X, R)
    if write:
        (ROOT / OUT_RTL).write_text("`timescale 1ns/1ps\n" + body["soft"] + "\n" + body["softb"])
        for v in KIT_VARIANTS:
            env, P, ranges, faces, diag, X, R = res[v]
            (ROOT / OUT_SDC[v]).write_text(sdc(X + R, v))
            (ROOT / OUT_SITES[v]).write_text(sites(v, env, P, R, soft_anchor(body[v], P)))
            p = ROOT / "tools/ref_tile/specs_qcluster" / f"{KITS[v]}.json"
            p.write_text(json.dumps(spec(v, env, P, ranges, faces, diag), indent=1) + "\n")
        d = ROOT / PLAN; d.mkdir(parents=True, exist_ok=True)
        (d / "plan.json").write_text(json.dumps(plan, indent=1) + "\n")
        preview({v: res[v] for v in res}, d)
    return plan

def preview(res, d):
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    except Exception:
        return
    for v, (env, P, *_r) in res.items():
        fig, ax = plt.subplots(figsize=(7, 7 * env["H"] / env["W"]))
        ax.add_patch(plt.Rectangle((0, 0), env["W"], env["H"], fill=False, lw=1))
        col = {"tile": "#8fb3d9", "stn": "#e0a040", "xstn": "#50a050", "land_w": "#d05050", "land_r": "#a050c0"}
        for n, p in P.items():
            w, h, _ = LEFS[p["kind"]]
            k = next((c for c in ("xstn", "tile", "land_w", "land_r", "stn") if c in p["kind"]), "stn")
            ax.add_patch(plt.Rectangle((p["x"], p["y"]), w, h, color=col[k], lw=0))
        ax.set_xlim(0, env["W"]); ax.set_ylim(0, env["H"]); ax.set_aspect("equal"); ax.set_title(f"{KITS[v]} {env['W']:.0f} x {env['H']:.0f} um (A0 STAND-IN)")
        fig.savefig(d / f"plan_preview_{v}.png", dpi=110, bbox_inches="tight"); plt.close(fig)

if __name__ == "__main__":
    plan = run(write="--check" not in sys.argv)
    for k, v in plan.items():
        print(k, v["outline_um"], v["area_mm2"], "x", v["area_vs_diag"], "children", v["children"], "single>405:", len(v["single_cycle_over_405"]),
              "max", v["single_cycle_max_um"], "bank max", v["bank_window_max_um"], "unres", v["unresolved_sink_bits"])
        for r in v["single_cycle_over_405"][:12]:
            print("   ", r["src"], "->", r["dst"], r["worst_um"])
