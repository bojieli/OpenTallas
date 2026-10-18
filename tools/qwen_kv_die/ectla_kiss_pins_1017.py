#!/usr/bin/env python3
"""KVJ-D 2026-10-17: exact pin plan of the fused ECTL A + static K issuer tile qkd_static_ectla_kiss.

Starts from the KV die lead's ECTL A grant (results/arch/qwen_split_1014/ectl_pin_grant_1016/qkd_ectl_a_tp8_epoch_direct.tcl):
every pin of the granted leaf that the fused tile still has (cfg, rst_n, ck, t0_row / t1_row over their SRAMs, x_i,
rs_o) is copied byte-exact.  rq / rs become internal nets.  The W face carries the landing segment's K request
(req_*, 38 b) and response (rsp_*, 1,062 b) over the WHOLE face on M4 + M6 (alternating, M6 off the M6 PG stripes,
same layer grant as rs), bit-ascending in y; the issuer's control inputs and fault (kgo, epoch, layer, fault, 24 b) sit
on S next to cfg / rst_n on M5.

  python3 tools/qwen_kv_die/ectla_kiss_pins_1017.py [--out results/arch/qwen_kv_static_kvjd_1017]
"""
import argparse, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ectl_pin_grant_1016 as G  # noqa: E402

ROOT = G.ROOT
SRC = "results/arch/qwen_split_1014/ectl_pin_grant_1016/qkd_ectl_a_tp8_epoch_direct.tcl"
CELL = "qkd_static_ectla_kiss"
W_SPAN = (2.2, 127.4)
W_BUS = [("req_valid", 1), ("req_t", 14), ("req_v", 1), ("req_epoch", 16), ("req_layer", 6),
         ("rsp_valid", 1), ("rsp_data", 1024), ("rsp_t", 14), ("rsp_v", 1), ("rsp_epoch", 16), ("rsp_layer", 6)]
S_BUS = [("kgo", 1), ("epoch", 16), ("layer", 6), ("fault", 1)]
S_SPAN = (12.0, 21.0)


def names(bus):
    return [n if w == 1 else f"{n}[{i}]" for n, w in bus for i in range(w)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/arch/qwen_kv_static_kvjd_1017")
    a = ap.parse_args()
    pins = {}
    for ln in (ROOT / SRC).read_text().splitlines():
        m = re.match(r"place_pin -pin_name \{(\S+)\} -layer (\S+) -location \{(\S+) (\S+)\} -pin_size \{(\S+) (\S+)\}", ln)
        if not m or re.match(r"(rq|rs)\[", m.group(1)):
            continue
        n, l, x, y, w, h = m.groups()
        pins[n] = dict(layer=l, x=float(x), y=float(y), w=float(w), h=float(h), src="ectl_a_grant_1016")
    wn = names(W_BUS)
    even = G.spread((len(wn) + 1) // 2, *W_SPAN, "M4")
    odd = G.spread(len(wn) // 2, *W_SPAN, "M6", G.off_pg6)
    for b, n in enumerate(wn):
        layer, y = ("M4", even[b // 2]) if b % 2 == 0 else ("M6", odd[b // 2])
        w, h = G.SIZE[layer]
        pins[n] = dict(layer=layer, x=round(w / 2, 4), y=y, w=w, h=h, src="kvjd_w")
    sn = names(S_BUS)
    for n, x in zip(sn, G.spread(len(sn), *S_SPAN, "M5")):
        w, h = G.SIZE["M5"]
        pins[n] = dict(layer="M5", x=x, y=round(h / 2, 4), w=w, h=h, src="kvjd_s")
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    lines = [f"# {CELL}: exact pin plan, KVJ-D 2026-10-17 (tools/qwen_kv_die/ectla_kiss_pins_1017.py) from {SRC}. Do not edit; regenerate."]
    for n in sorted(pins):
        p = pins[n]
        lines.append(f"place_pin -pin_name {{{n}}} -layer {p['layer']} -location {{{p['x']:.4f} {p['y']:.4f}}} "
                     f"-pin_size {{{p['w']:.3f} {p['h']:.3f}}} -force_to_die_boundary")
    (out / f"{CELL}.tcl").write_text("\n".join(lines) + "\n")
    face = lambda p: "W" if p["x"] < 0.2 else ("E" if p["x"] > G.LEAF_W - 0.2 else ("S" if p["y"] < 0.2 else "N"))
    rep = {}
    for n, p in pins.items():
        f = face(p)
        r = rep.setdefault(f, dict(pins=0, layers={}))
        r["pins"] += 1
        r["layers"][p["layer"]] = r["layers"].get(p["layer"], 0) + 1
    L = dict(W=G.LEAF_H, E=G.LEAF_H, N=G.LEAF_W, S=G.LEAF_W)
    for f, r in rep.items():
        r["pins_per_um_face"] = round(r["pins"] / L[f], 2)
    print(json.dumps(dict(cell=CELL, pins=len(pins), faces=rep), indent=1))


if __name__ == "__main__":
    main()
