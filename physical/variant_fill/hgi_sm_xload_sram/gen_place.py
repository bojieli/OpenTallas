#!/usr/bin/env python3
"""FILL-9 (2026-10-10) ot_hgi_sm_xload SRAM placements: 32 x ot_sram_1r1w_128x256_m1 (94.824 x 41.064 um, pins on the
left edge in R0 / the right edge in MY), instance g_t[t].g_q[q].u_m.  Row gaps 12.96 um (>= 12: no slivers); every
macro's pin edge faces a logic channel.
  a: die 600 x 900: two 16-high columns, left MY / right R0 (pins facing the 378-um centre logic channel);
     t 0-3 left, t 4-7 right, quarter-major in each column (fe-push-hgi-1010: the 4 macros of one OR-4 group
     (half, q) are adjacent; rw ORs the two columns' groups).
  b: die 760 x 480: four 8-high columns [MY | ch 40 | R0]  centre logic  [MY | ch 40 | R0]; quarters q 0-1 left,
     q 2-3 right, t = row (an OR-4 group = rows 0-3 / 4-7 of one column)."""
import sys
MW, MH, G = 94.824, 41.064, 12.96
sx = lambda x: round(round(x / 0.054) * 0.054, 3)
sy = lambda y: round(round(y / 0.27) * 0.27, 3)
DIE = {'a': (600.0, 900.0), 'b': (760.0, 480.0)}
def a():
    W, H = DIE['a']; y0 = (H - 16 * MH - 15 * G) / 2; out = []
    for t in range(8):
        for q in range(4):
            i = q * 4 + (t % 4); left = t < 4
            out.append((t, q, sx(16.2 if left else W - 16.2 - MW), sy(y0 + i * (MH + G)), 'MY' if left else 'R0'))
    return out
def b():
    W, H = DIE['b']; y0 = (H - 8 * MH - 7 * G) / 2; out = []
    xs = [16.2, 16.2 + MW + 40, W - 16.2 - 2 * MW - 40, W - 16.2 - MW]
    for t in range(8):
        for q in range(4):
            out.append((t, q, sx(xs[q]), sy(y0 + t * (MH + G)), 'MY' if q % 2 == 0 else 'R0'))
    return out
v = sys.argv[1]
print(f"# FILL-9 ot_hgi_sm_xload SRAM placement variant {v}, die {DIE[v][0]} x {DIE[v][1]} (gen_place.py {v})")
for t, q, x, y, o in {'a': a, 'b': b}[v]():
    print(f"place_macro -macro_name {{g_t\\[{t}\\].g_q\\[{q}\\].u_m}} -location {{{x} {y}}} -orientation {o}")
