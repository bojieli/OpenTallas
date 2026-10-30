#!/usr/bin/env python3
"""DIE-HBM-26 HBM-054: static macro sites for lanes8_11 and opstore_b (spec for core_macros_fix.py --static).

Instance names = yosys flatten of the HBM-CORES-KITS-24 kit RTL (elab/*.list: 24 x ot_sram_1r1w_128x256_m1_r2c2,
48 x ot_sram_1r1w_256x256_m2_r2c2).  Kit clock entries (kit_contract.clock_pin_geometry): lanes8_11 (380.184, 362.88),
opstore_b (380.184, 345.6) -> both arrays are symmetric about x = 380.16 so the entry sits in the middle vertical
channel.  y snapped to 0.012 mod 0.048 (M4 track 0.024 + n 0.048, SRAM pin centre 0.972 above origin).
"""
import json
import sys


def snap_y(y):
    n = round((y - 0.012) / 0.048)
    return round(0.012 + n * 0.048, 3)


def snap_x(x):
    return round(round(x / 0.108) * 0.108, 3)


def columns(n, w, gap, centre):
    span = n * w + (n - 1) * gap
    x0 = snap_x(centre - span / 2)
    return [round(x0 + i * (w + gap), 3) for i in range(n)]


def lanes8_11():
    W, H = 94.824, 41.064
    xs = columns(6, W, 13.176, 380.16)                       # lane_exp0 pitch 108 (13.176 channel)
    # 4 rows (bank0..3) as 2+2 with a 24.006 interior channel (lane_exp0 row channel), centred on the core
    ys0 = 362.88 - (4 * H + 2 * 0.024 + 24.006) / 2
    ys = [ys0, ys0 + H + 0.024, ys0 + 2 * H + 0.024 + 24.006, ys0 + 3 * H + 2 * 0.024 + 24.006]
    ys = [snap_y(y) for y in ys]
    rows = []
    for b in range(4):
        for r in range(6):
            rows.append(dict(name=f"u_fcore.u_core.u_bank{b}.u_data.g_read[{r}].u_m",
                             master="ot_sram_1r1w_128x256_m1_r2c2", origin_um=[xs[r], ys[b]], orient="R0"))
    return dict(outline_um=[760.32, 725.76], macros=rows,
                basis="DIE-HBM-26 static grid: 6 col x 4 row (bank b = row b, read r = col r), col pitch 108 "
                      "(13.176 channel), rows 2+2 with 24-um interior channel, centred on the clock entry channel")


def opstore_b():
    W, H = 172.824, 41.064
    xs = columns(4, W, 12.096, 380.16)                       # 4 cols, W/E core-edge channels >= 10.8
    band = 4 * H + 3 * 0.024
    ch = (682.56 - 3 * band) / 4                             # 4 equal horizontal logic channels
    rows = []
    for g, grp in enumerate(("u_group0", "u_group1", "u_output")):
        yb = 4.32 + ch + g * (band + ch)
        for c in range(4):
            for r in range(4):
                rows.append(dict(name=f"u_fcore.u_core.{grp}.g_bank[{c * 4 + r}].u_b.genblk1.genblk1.g_m11.u_m",
                                 master="ot_sram_1r1w_256x256_m2_r2c2",
                                 origin_um=[xs[c], snap_y(yb + r * (H + 0.024))], orient="R0"))
    return dict(outline_um=[760.32, 691.2], macros=rows,
                basis="DIE-HBM-26 static grid: 4 col x 12 row (3 bands u_group0/u_group1/u_output of 4 rows; bank "
                      "4c+r), col channel 12.096, ~47-um logic channels between bands, centred on the clock entry")


if __name__ == "__main__":
    spec = {"ot_hbm_su_static_pgslice_lg__lanes8_11": lanes8_11(), "ot_hgi_sfu_core_split3__opstore_b": opstore_b()}
    lists = sys.argv[1:]
    for f in lists:   # cross-check names against the elaborated instance lists
        top, names = f.rsplit("/", 1)[-1][:-5], {l.strip().split("/", 1)[1] for l in open(f) if l.strip()}
        got = {m["name"] for m in spec[top]["macros"]}
        assert got == names, (top, sorted(names - got)[:3], sorted(got - names)[:3])
    json.dump(spec, sys.stdout, indent=1)
