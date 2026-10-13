#!/usr/bin/env python3
"""el1013-idx-tiles gate (d): exhaustive identity of the six-stage ordinal divide of ot_hgi_idxw_keep against
floor(q / 3) and q mod 3 for every q < 2^15, with the exact register widths of the RTL stages, and against the
reference's two-stage form (ot_hgi_idx_index_w k1 / k2 / k3).  MUT 11 (K4 without + q) is counted as a negative control.
"""
import json, sys
M = lambda w: (1 << w) - 1
def tiled(q, mut11=False):
    q5 = (q + (q << 2)) & M(18)                    # K1  q5 = q + 4 q            (18-bit register)
    p85 = (q5 + (q5 << 4)) & M(22)                 # K2  p85 = q5 + 16 q5        (22-bit)
    s = ((p85 << 1) + (p85 << 9)) & M(32)          # K3  s = 2 p85 + 512 p85     (32-bit)
    s4 = s if mut11 else (s + q) & M(32)           # K4  ord = (s + q) >> 17     (bits 30:17, 14-bit)
    ord_ = (s4 >> 17) & M(14)
    t = (ord_ + (ord_ << 1)) & M(15)               # K5  t = 3 ord (two low bits kept), ord < 1368
    r2 = ((q & 3) - (t & 3)) & 3                   # K6  q - t (2 bits)
    return ord_, r2, ord_ < 1368
def reference(q):
    kq5 = (q + (q << 2)) & M(18); k1_p = (kq5 + (kq5 << 4)) & M(22)
    kq3 = ((k1_p << 1) + (k1_p << 9) + q) & M(32); k2_ord = (kq3 >> 17) & M(14)
    r2 = (q - ((k2_ord + (k2_ord << 1)) & M(15))) & 3
    return k2_ord, r2, k2_ord < 1368
bad = badref = mut = 0
for q in range(1 << 15):
    o, r, lt = tiled(q)
    if o != q // 3 or r != q % 3 or lt != (q // 3 < 1368): bad += 1
    if (o, r, lt) != reference(q): badref += 1
    if tiled(q, True)[:2] != (q // 3, q % 3): mut += 1
out = {"range": "0 <= q < 32768", "mismatch_vs_floor_div3_and_mod3": bad, "mismatch_vs_reference_stages": badref,
       "mut11_wrong_values": mut, "verdict": "PASS" if bad == 0 and badref == 0 and mut > 0 else "FAIL"}
print(json.dumps(out)); sys.exit(0 if out["verdict"] == "PASS" else 1)
