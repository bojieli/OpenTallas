#!/usr/bin/env python3
"""D3: the DS softmax unit fed sink = -2^100 as DATA is bit-identical to no sink (Qwen), so `sfx_sink_off` is not
needed for exactness.

Unit semantics (rtl/hdc/v41x/ot_dsrom_su_softmax.sv header, hdc_golden_v41.attend):
    x = s * scale;  m = max_t x;  e_t = exp(x_t - m);  es = csum(e);  den = es + exp(sink - m);  o = pv / den
ARGUMENT.  (1) sink is not in the max.  (2) For |m| < 2^76, sink - m rounds to -2^100 exactly; exp clamps its
argument at EXP_MIN = -87, so exp(sink - m) = exp(-87) = 1.6458e-38 > 0 (golden exp; a correctly rounded exp gives
+0, also fine).  (3) e at the arg-max is exp(+0) = 1 exactly, every e_t >= 0, and the csum of non-negative terms
under RNE is >= its largest term, so es >= 1.  (4) For es >= 1, ulp(es)/2 >= 2^-24 >> 1.6458e-38, so
es + exp(sink - m) rounds to es.  Hence den == es bit for bit and o, e are unchanged.
CHECK.  The same through the shared library on 8 heads x T in {1, 2, 640, 641, 8192}: random scores, scores
spanning the FP32 range, all-equal rows, one dominant score, denormal-producing gaps; e, den and o compared bitwise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hgi_sim import lib as A  # noqa: E402

F = np.float32
SINK = F(-2.0 ** 100)


def main():
    rng = np.random.default_rng(100)
    scale = F(1.0 / np.sqrt(128))
    rows, worst = 0, []
    for T in (1, 2, 640, 641, 8192):
        cases = [rng.standard_normal((8, T)) * 10, rng.uniform(-3e4, 3e4, (8, T)), np.full((8, T), 7.0),
                 np.concatenate([np.full((8, 1), 500.0), rng.standard_normal((8, T - 1))], 1) if T > 1 else
                 np.full((8, 1), -900.0),
                 rng.uniform(-1e6, 1e6, (8, T))]
        for c in cases:
            s = c.astype(F)
            for h in range(8):
                e0, z0, m0 = A.softmax_e_z(s[h], scale)
                e1, z1, m1 = A.softmax_e_z(s[h], scale, sink=SINK)
                pv = rng.standard_normal(128).astype(F)
                same = (np.array_equal(e0.view(np.uint32), e1.view(np.uint32)) and
                        np.uint32(np.asarray(z0, F).view(np.uint32)) == np.uint32(np.asarray(z1, F).view(np.uint32))
                        and np.array_equal(A.div(pv, z0).view(np.uint32), A.div(pv, z1).view(np.uint32)))
                rows += 1
                if not same:
                    worst.append(dict(T=T, h=h, z0=float(z0), z1=float(z1)))
    rec = dict(schema="opentallas.hgi_sim.sink_proof.v1", status="pass" if not worst else "fail", rows=rows,
               sink=float(SINK), exp_at_clamp=float(A.exp(F(-2.0 ** 100))), mismatches=worst[:5])
    print(json.dumps(rec, indent=1))
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(rec, indent=1) + "\n")
    return 0 if not worst else 1


if __name__ == "__main__":
    raise SystemExit(main())
