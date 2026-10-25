#!/usr/bin/env python3
"""HBM-W128 10-25: top-down pin tables + kit views for the native W128 HC hard cores (B2o Rh bank slots / q_hub).

Cores (cut exactness: results/hbm_hc128_physical_1025; multiplier reset fix .DRST(ADRST) in ot_hdc_v41x_hcp_lanes):
  ot_hbm_hc_bank128_pair_core        plain / feed / terminal bank pair master (one circuit, equiv-checked)
  ot_hbm_hc_bank128_pair_first_core  first bank pair (no sum_in)
  ot_hbm_hc_subtree32_core           qhub 32-input 5-level FP32 adder subtree (x4 per qhub)

Outline derivation (parent = B2o, codex/hbm-b2o-capacity-1025@96be80ec2, partition_types q_b0xx = 2419.2 tall, narrowest
q_b002 / q_b011 = 380.16 wide):  8 pairs stacked in the bank column: 2 x 17.28 face bands + 8 x 267.84 + 7 x 34.56 row
gaps = 2419.2 exactly; pair x = 25.92 -> 17.28 um left / 95.04 um right free channel after the 8.64 halo in the 380.16
bank (wider banks only widen the right channel).  Pair width 250.56 = 29 x 8.64, height 267.84 = 31 x 8.64.
Faces (one role per face, data flow straight through the bank row):
  W  sum_in  (partial sums from the previous bank's same pair row, M4/M6)       bit i at the same y as sum_out[i]
  E  sum_out (to the next bank, M4/M6) + fault
  N  write / read control broadcast from the row gap (write_data, addresses, enables, lane_valid, square, go, clk, rst_n)
Subtree: 220.32 x 220.32 (4 per qhub in a 2 x 2 around the 3 upper adders; qhub slot in B2o q_hub 734.4 x 734.4):
  N  data[1023:0] + valid_in + clk + rst_n (from the bank side; mirrored per quadrant)   S  sum, node_fault, valid_out
"""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDGE = 0.019
LAT = dict(M4=(0.024, 0.048), M5=(0.024, 0.048), M6=(0.032, 0.064), M7=(0.032, 0.064))


def bits(name, w):
    return [name] if w == 1 else [f"{name}[{i}]" for i in range(w)]


def face(names, f, w, h, layers, margin=8.64):
    L = h if f in "WE" else w
    n = len(names)
    used = {l: set() for l in layers}
    out = []
    for i, nm in enumerate(names):
        lay = layers[i % len(layers)]
        o, p = LAT[lay]
        t = margin + (i + 0.5) * (L - 2 * margin) / n
        k = round((t - o) / p)
        while k in used[lay]:
            k += 1
        used[lay].add(k)
        c = round(o + k * p, 3)
        assert margin * 0.5 < c < L - margin * 0.5, (nm, c)
        x, y = {"W": (EDGE, c), "E": (round(w - EDGE, 3), c), "S": (c, EDGE), "N": (c, round(h - EDGE, 3))}[f]
        out.append(dict(name=nm, layer=lay, x=x, y=y))
    return out


def pair(first):
    w, h = 250.56, 267.84
    pins = []
    if not first:
        pins += face(bits("sum_in", 512), "W", w, h, ["M4", "M6"])
    pins += face(bits("sum_out", 512) + bits("fault", 2), "E", w, h, ["M4", "M6"])
    n = (bits("write_data", 512) + bits("write_addr", 10) + bits("weight_addr", 10) + bits("x_addr", 7) +
         bits("lane_valid", 16) + bits("square", 16) + ["go", "weight_read", "weight_we0", "weight_we1", "x_read",
                                                         "x_write"])
    half = len(n) // 2
    pins += face(n[:half] + ["clk", "rst_n"] + n[half:], "N", w, h, ["M5", "M7"])
    return (w, h), pins


def subtree():
    w = h = 220.32
    d = bits("data", 1024)
    pins = face(d[:512] + ["valid_in", "clk", "rst_n"] + d[512:], "N", w, h, ["M5", "M7"])
    pins += face(bits("sum", 32) + ["valid_out"] + bits("node_fault", 31), "S", w, h, ["M5", "M7"])
    return (w, h), pins


def main():
    cores = HERE / "cores"
    cores.mkdir(exist_ok=True)
    # plan.json = B2o die_plan.json (codex/hbm-b2o-capacity-1025@96be80ec2) with partitions / types / ports / lanes /
    # census emptied: the kit generator needs only die.period_ps, clock and the layer track table from it.
    assert (HERE / "plan.json").is_file(), "w128/plan.json (stripped B2o plan) missing"
    views = []
    # placed = instances per W128 HC unit (16 banks x 8 pairs; bank 0 = first style; 4 subtrees per qhub)
    for module, (oh, pins), slot, placed in (
            ("ot_hbm_hc_bank128_pair_core", pair(False), "q_b0xx bank column rows (plain/feed/terminal banks)", 120),
            ("ot_hbm_hc_bank128_pair_first_core", pair(True), "first bank column rows", 8),
            ("ot_hbm_hc_subtree32_core", subtree(), "q_hub u_hc_Q 2x2 subtrees", 4)):
        w, h = oh
        pf = f"cores/{module}__{w:g}x{h:g}.json"
        (HERE / pf).write_text(json.dumps(pins) + "\n")
        s = hashlib.sha256((HERE / pf).read_bytes()).hexdigest()
        views.append(dict(view=f"{module}@{s[:12]}", module=module, outline_um=[w, h], pins_file=pf, pins_sha256=s,
                          pins=len(pins), family="HC128", instances=[slot], placed=placed, recipe_keys=[module], blockers=[]))
        print(module, w, h, len(pins), s[:12])
    (HERE / "views_w128.json").write_text(json.dumps(dict(schema="opentallas.hbm_arch.core_views.v1",
                                                          plan=str((HERE / "plan.json").relative_to(HERE.parent)),
                                                          view_list=views), indent=1) + "\n")


if __name__ == "__main__":
    main()
