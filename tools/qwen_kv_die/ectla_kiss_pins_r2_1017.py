#!/usr/bin/env python3
"""ECTLA-2 2026-10-17: exact pin plan of the RE-ASPECTED fused ECTL A + static K issuer tile (coordinator 0co (1)).

The k1 tile (254.88 x 129.6, ectla_kiss_pins_1017.py) was rejected at review: W landing face 1,100 pins at 8.5 /um,
SRAMs off the 43.2 lattice in x, two std-cell bands (above / below the SRAMs), 350 ps TT clock insertion from one
far N-face root.  This plan re-aspects the outline inside the KV die's ECTL slot (k3: 172.8 x 194.4; k2 216 x 216 was measured
TritonCTS 388 ps / spread 123 ps at 6 % std density) with both SRAMs stacked in one column on the lattice (k3 x 43.2,
y 43.2 / 129.6), their pin edge (W) facing ONE contiguous std-cell band that holds the landing capture, the issuer and the ECTL body:

  W  landing K request / response (1,100 b) over 2.2..213.8 on M4 + M6 alternating (M6 off the M6 PG stripes):
     5.2 pins/um (<= 6), bit-ascending in y; the rc variant leaves 106.2..110.2 for ck_k (issuer region root, M4).
  E  rs_o / x_i: the ECTL A grant's exact y (B abuts bottom-aligned; B is 129.6 tall), x moved to the new E face.
  S  cfg / rst_n / kgo / epoch / layer / fault at the k1 x (6..21); t0_row over 23..212 (bit-ascending, M5), ~2.7 /um.
  N  t1_row as t0_row; ck (ECTL body root, M5) at x 108 in a 4-um gap of the row bus (tile centre: SRAM gap + bands).

  python3 tools/qwen_kv_die/ectla_kiss_pins_r2_1017.py [--rc] [--out results/arch/qwen_kv_static_ectla2_1017]
"""
import argparse
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ectl_pin_grant_1016 as G  # noqa: E402

ROOT = G.ROOT
SRC = "results/arch/qwen_kv_static_kvjd_1017/qkd_static_ectla_kiss.tcl"     # k1 plan (E / S control pins from the grant)
W_OLD = 254.88
GEOM = {   # name: (W, H, W landing span, ck_k window on W, ck window on N, row span, ck x, ck_k y)
    "k2": (216.0, 216.0, (2.2, 213.8), (106.2, 110.2), (106.0, 110.0), (23.0, 212.0), 108.0, 108.2),
    "k3": (172.8, 194.4, (2.2, 192.2), (95.2, 99.2), (84.4, 88.4), (23.0, 170.0), 86.4, 97.2),
}
TILE_W, TILE_H = 216.0, 216.0
W_SPAN, CKK_GAP, CK_GAP, ROW_SPAN, CK_X, CKK_Y = (2.2, 213.8), (106.2, 110.2), (106.0, 110.0), (23.0, 212.0), 108.0, 108.2
W_BUS = [("req_valid", 1), ("req_t", 14), ("req_v", 1), ("req_epoch", 16), ("req_layer", 6),
         ("rsp_valid", 1), ("rsp_data", 1024), ("rsp_t", 14), ("rsp_v", 1), ("rsp_epoch", 16), ("rsp_layer", 6)]


def names(bus):
    return [n if w == 1 else f"{n}[{i}]" for n, w in bus for i in range(w)]


def spread_gap(n, lo, hi, layer, gap, allowed=None):
    """n track-aligned centres over [lo, hi] minus the open window gap, bit-ascending"""
    ok = (lambda t: not (gap[0] <= t <= gap[1]) and (allowed is None or allowed(t))) if gap else allowed
    return G.spread(n, lo, hi, layer, ok)


def plan(rc):
    pins = {}
    for ln in (ROOT / SRC).read_text().splitlines():
        m = re.match(r"place_pin -pin_name \{(\S+)\} -layer (\S+) -location \{(\S+) (\S+)\} -pin_size \{(\S+) (\S+)\}", ln)
        if not m:
            continue
        n, l, x, y, w, h = m.group(1), m.group(2), *map(float, m.groups()[2:])
        base = n.split("[")[0]
        if base in ("rs_o", "x_i"):                                   # E face: same y, new E edge
            pins[n] = dict(layer=l, x=round(TILE_W - (W_OLD - x), 4), y=y, w=w, h=h, src="grant_e_y")
        elif base in ("cfg", "rst_n", "kgo", "epoch", "layer", "fault"):   # S control: same x
            pins[n] = dict(layer=l, x=x, y=y, w=w, h=h, src="k1_s")
    wn = names(W_BUS)
    gap = CKK_GAP if rc else None
    even = spread_gap((len(wn) + 1) // 2, *W_SPAN, "M4", gap)
    odd = spread_gap(len(wn) // 2, *W_SPAN, "M6", gap, G.off_pg6)
    for b, n in enumerate(wn):
        layer, y = ("M4", even[b // 2]) if b % 2 == 0 else ("M6", odd[b // 2])
        w, h = G.SIZE[layer]
        pins[n] = dict(layer=layer, x=round(w / 2, 4), y=y, w=w, h=h, src="r2_w")
    xs = spread_gap(512, *ROW_SPAN, "M5", CK_GAP)
    for bus, face in (("t0_row", "S"), ("t1_row", "N")):
        w, h = G.SIZE["M5"]
        for b, x in enumerate(xs):
            pins[f"{bus}[{b}]"] = dict(layer="M5", x=x, y=round(h / 2 if face == "S" else TILE_H - h / 2, 4), w=w, h=h,
                                       src="r2_rows")
    w, h = G.SIZE["M5"]
    pins["ck"] = dict(layer="M5", x=G.snap(CK_X, "M5"), y=round(TILE_H - h / 2, 4), w=w, h=h, src="r2_ck")
    if rc:
        w, h = G.SIZE["M4"]
        pins["ck_k"] = dict(layer="M4", x=round(w / 2, 4), y=G.snap(CKK_Y, "M4"), w=w, h=h, src="r2_ckk")
        w, h = G.SIZE["M5"]
        pins["rst_k"] = dict(layer="M5", x=G.snap(3.27, "M5"), y=round(h / 2, 4), w=w, h=h, src="r2_rstk")   # issuer regional reset
    return pins


def face(p):
    return "W" if p["x"] < 0.2 else ("E" if p["x"] > TILE_W - 0.2 else ("S" if p["y"] < 0.2 else "N"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rc", action="store_true", help="two regional clock roots (ck body, ck_k issuer)")
    ap.add_argument("--geom", default="k3", choices=sorted(GEOM))
    ap.add_argument("--out", default="results/arch/qwen_kv_static_ectla2_1017")
    a = ap.parse_args()
    global TILE_W, TILE_H, W_SPAN, CKK_GAP, CK_GAP, ROW_SPAN, CK_X, CKK_Y
    TILE_W, TILE_H, W_SPAN, CKK_GAP, CK_GAP, ROW_SPAN, CK_X, CKK_Y = GEOM[a.geom]
    cell = f"qkd_static_ectla_{a.geom}" + ("rc" if a.rc else "")
    pins = plan(a.rc)
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    lines = [f"# {cell}: exact pin plan, ECTLA-2 2026-10-17 (tools/qwen_kv_die/ectla_kiss_pins_r2_1017.py"
             f"{' --rc' if a.rc else ''}) from {SRC}. Do not edit; regenerate."]
    for n in sorted(pins):
        p = pins[n]
        lines.append(f"place_pin -pin_name {{{n}}} -layer {p['layer']} -location {{{p['x']:.4f} {p['y']:.4f}}} "
                     f"-pin_size {{{p['w']:.3f} {p['h']:.3f}}} -force_to_die_boundary")
    (out / f"{cell}.tcl").write_text("\n".join(lines) + "\n")
    rep, rng = {}, {}
    for n, p in pins.items():
        f = face(p)
        r = rep.setdefault(f, dict(pins=0, layers={}))
        r["pins"] += 1
        r["layers"][p["layer"]] = r["layers"].get(p["layer"], 0) + 1
        c = p["y"] if f in "WE" else p["x"]
        b = n.split("[")[0]
        lo, hi = rng.get(b, (c, c))
        rng[b] = (min(lo, c), max(hi, c))
    L = dict(W=TILE_H, E=TILE_H, N=TILE_W, S=TILE_W)
    for f, r in rep.items():
        r["pins_per_um_face"] = round(r["pins"] / L[f], 2)
    W = [p["y"] for p in pins.values() if face(p) == "W"]
    rep["W"]["pins_per_um_span"] = round(len(W) / (max(W) - min(W)), 2)
    ranges = {b: [round(max(0.0, lo - 0.3), 2), round(hi + 0.3, 2)] for b, (lo, hi) in sorted(rng.items())}
    (out / f"{cell}_pin_ranges.json").write_text(json.dumps(ranges, indent=1) + "\n")
    print(json.dumps(dict(cell=cell, pins=len(pins), faces=rep), indent=1))


if __name__ == "__main__":
    main()
