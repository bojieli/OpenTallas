#!/usr/bin/env python3
"""FILL-9 (2026-10-10) HGI VM ECC 0 macro placements: 32 x ot_sram_1r1w_1024x256_m2 (174.744 x 70.488 um), one per bank
(u_core.g_bank[k].u_lo), in the 1399.656 x 1080 hfd_hgi_vm low spine slot.  Every macro gap >= 16 um (no slivers).
  a: bottom field, 7 columns x 5 rows (banks row-major), logic + client stations above, under the top cq/cr pins.
  b: side columns, banks 0-15 in 2 columns on the left face, 16-31 on the right face (the wq DMA lanes enter on the
     left / right faces), logic + stations in the 600-um centre channel."""
import sys
MW, MH, W, H = 174.744, 70.488, 1399.656, 1080.0
sx = lambda x: round(round(x / 0.054) * 0.054, 3)
sy = lambda y: round(round(y / 0.27) * 0.27, 3)
def a():
    m = 16.2; s = (W - 2 * m - 7 * MW) / 6; out = []
    for k in range(32):
        r, c = divmod(k, 7)
        out.append((k, sx(m + c * (MW + s)), sy(16.2 + r * (MH + 16.2))))
    return out
def b():
    y0 = sy((H - 8 * MH - 7 * 24.0) / 2); out = []
    xs = [16.2, 16.2 + MW + 16.2, W - 16.2 - MW, W - 16.2 - 2 * MW - 16.2]
    for k in range(32):
        side, i = divmod(k, 16); col, row = divmod(i, 8)
        out.append((k, sx(xs[2 * side + col]), sy(y0 + row * (MH + 24.0))))
    return out
v = sys.argv[1]
print(f"# FILL-9 hgi_vm ECC 0 placement variant {v} (gen_place.py {v})")
for k, x, y in {'a': a, 'b': b}[v]():
    print(f"place_macro -macro_name {{u_core.g_bank\\[{k}\\].u_lo}} -location {{{x} {y}}} -orientation R0")
