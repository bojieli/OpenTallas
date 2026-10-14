#!/usr/bin/env python3
"""Pin plan of the re-shaped S81 SU pin owner dsfd_su_t_pin (s81-suhc r9, die contract v17 decision D):
physical/s81su_taps/s81su_pinns_ref_io.tcl.

The closed tile (572.4 x 475.2, util 0.033) is pin-bound: 4,096 data pins on each of its W and E faces on M4 alone.
The slab's VM pins (rs_d / wq_d) enter on the slab N face on M5 and the spines run N-S, so the bus is turned twice.
Re-shape: 453.6 x 64.8 (four abreast = 1,814.4 of the 1,890-um slab width), the VM side on N, the spine side on S,
every bit a straight N-S feed-through through its two registers (pin flop, output flop):

  N (VM side)     wq_v | wq_row | wq_mask | wq_d          rs_d | rs_v | rq_v | rq_row        ck rst
  S (spine side)  up_v | up_a   | up_m    | up_d          dn_d | dn_v | c_rq_v | c_rq_row    c_rv c_rf c_uv

bit i of each S bus under bit i of the N bus above it, same layer and track, M5 / M3 alternating (4.9 b/um/layer).
Tracks, PG-stripe keep-out and corner margin as tools/s81_suhc/crr_pinplan.py (the HC plans)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import crr_pinplan as P

W, H = 453.6, 64.8
KR = KW = 4


def plan():
    b = P.bits
    P.W = W
    n_al = b("wq_v", KW) + b("wq_row", KW * 14) + b("wq_mask", KW * 16) + b("wq_d", KW * 512) \
        + b("rs_d", KR * 512) + b("rs_v", KR) + b("rq_v", KR) + b("rq_row", KR * 14)
    s_al = b("up_v", KW) + b("up_a", KW * 14) + b("up_m", KW * 16) + b("up_d", KW * 512) \
        + b("dn_d", KR * 512) + b("dn_v", KR) + b("c_rq_v", KR) + b("c_rq_row", KR * 14)
    assert len(n_al) == len(s_al)
    s_only = b("c_rv", KR) + b("c_rf", KR * 30) + b("c_uv", KW)
    cols = n_al + [None] * len(s_only)
    top = P.face_plan("N", [[f"col{i}" for i in range(len(cols))]], H, ["M5", "M3"], lo=P.MARGIN, hi=W - P.MARGIN - 1.2)
    pins = []
    for i, (_, _, L, x) in enumerate(top):
        if i < len(n_al):
            pins += [("N", n_al[i], L, x), ("S", s_al[i], L, x)]
        else:
            pins.append(("S", s_only[i - len(n_al)], L, x))
    ctl = P.tracks("M5", W - P.MARGIN - 1.1, W - P.MARGIN)
    pins += [("N", "ck", "M5", ctl[2]), ("N", "rst", "M5", ctl[10])]
    names = [p[1] for p in pins]
    assert len(names) == len(set(names)) == 2 * len(n_al) + len(s_only) + 2, len(names)
    return pins


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "physical/s81su_taps/s81su_pinns_ref_io.tcl")
    pins = plan()
    print("pinns", len(pins), P.check(pins, H, "pinns"))
    out.write_text(P.emit(pins, H, "S81 SU pin owner, N/S feed-through plan (VM side N, spine side S, bit-aligned), M5+M3")
                   .replace("crr_pinplan.py", "su_pin_ns_pinplan.py"))


if __name__ == "__main__":
    main()
