#!/usr/bin/env python3
"""HBM-AGSM8 (10-20): compiler + golden vectors of the DS expert-intermediate gather TRAIN -> w2 x-load static GO.

One F20 programme a quadrant gather master (rtl/.../p2p/ot_hgi_coll_gq.sv, VM_RT 74 = the d4g bank-latency class) holds
the 7 expert-intermediate segments of one DS layer as 7 descriptor rows of ONE launch (QBG, two rings, Bs 18, F 19,
slice stride 24): row k fires at t_start(k) = k * SP.  SP = the gather master's busy span (fire -> busy clear: issue
1 + 3((K-1)>>1) + ((K-1)&1) + ND = 40 + VM_RT event-pipeline drain; the master faults a fire while busy), so the train
issues back to back without a CP record per segment.  Segment k's last landing write (bank sample) is
    W(k) = L + 3 + t_start(k) + span(F, R)          (collq_gather_1018.span, = 128 at VM_RT 74)
The w2 SM of slot k reads segment k through its x-load; its static GO (ot_hgi_coll_seg_go, armed by the same launch
broadcast) fires at L + GO_LAT + off(k) with
    off(k) = t_start(k) + span(F, R)  (+ 0: the first edge whose bank image holds every word of segment k)
Golden: hdc_golden_v41.quant_fp8 per 32-block (UE8M0) of 7 x 4 production-shape FP32 slices (576 elements each =
2304 / 4 quadrants), mixed distributions (normal / heavy-tail / floor / large / bf16 / ties).

    python3 tools/hgi_sim/agsm8_chain_vectors_1020.py OUTDIR [--vm-rt 74] [--sp N]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hgi_sim import collq_gather_1018 as CQ  # noqa: E402

NSEG, R = 7, 2
GO_LAT = 4            # ot_hgi_coll_seg_go: launch pin @L+1, counter 0 @L+2, compare @L+2+off, go reg, go pin -> L+4+off
KINDS = ["normal", "heavy", "floor", "large", "bf16", "ties"]


def busy_span(F, R_, vm_rt):
    K = (F + R_ - 1) // R_
    nd = 40 + vm_rt
    return CQ.issue_rel(K - 1) + 1 + nd          # fire edge f -> first edge a new fire is accepted


def slice_vec(rng, kind, s):
    from hdc_golden import F as FT, to_bf16
    if kind == "normal":
        x = rng.standard_normal(s)
    elif kind == "heavy":
        x = rng.standard_t(1.5, s) * 10.0 ** rng.integers(-6, 4)
    elif kind == "floor":
        x = np.zeros(s)
        x[rng.integers(0, s, 5)] = rng.standard_normal(5) * 1e-6
        x[: s // 2] = rng.standard_normal(s // 2)
    elif kind == "large":
        x = rng.standard_normal(s) * 3e4
    elif kind == "bf16":
        x = to_bf16(rng.standard_normal(s).astype(FT))
    else:
        e = rng.integers(-8, 8, s)
        x = np.ldexp(1.0 + (rng.integers(0, 16, s) * 2 + 1) / 32.0, e) * rng.choice([-1, 1], s)
    x = np.asarray(x, dtype=FT)
    if kind in ("normal", "heavy", "large"):
        x[rng.integers(0, s, 3)] = -0.0
    return x


def main():
    import hdc_golden_v41 as G
    argv = list(sys.argv[1:])
    vm_rt = 74
    sp = None
    if "--vm-rt" in argv:
        i = argv.index("--vm-rt"); vm_rt = int(argv[i + 1]); del argv[i:i + 2]
    if "--sp" in argv:
        i = argv.index("--sp"); sp = int(argv[i + 1]); del argv[i:i + 2]
    out = Path(argv[0]); out.mkdir(parents=True, exist_ok=True)
    CQ.VM_RT = vm_rt
    n = CQ.SHAPES["expert_intermediate"]
    s = n // 4
    Bs = s // 32
    Es = (Bs + 31) // 32
    F = Bs + Es
    stride = ((F + 7) // 8) * 8
    sp_min = busy_span(F, R, vm_rt)
    sp = sp_min if sp is None else sp
    rng = np.random.default_rng(20261020)
    for k in range(NSEG):
        for q in range(4):
            x = slice_vec(rng, KINDS[(k * 4 + q) % len(KINDS)], s)
            codes, ex = G.quant_fp8(x, 32)
            cb = CQ.e4m3_byte(codes).reshape(Bs, 32)
            src = ["".join("%08x" % int(v) for v in w[::-1]) for w in x.view(np.uint32).reshape(-1, 8)]
            rec = [CQ.word_hex(cb[b]) for b in range(Bs)]
            for g in range(Es):
                eb = np.zeros(32, dtype=np.uint8)
                for j in range(32):
                    if 32 * g + j < Bs:
                        eb[j] = int(ex[32 * g + j]) + 127
                rec.append(CQ.word_hex(eb))
            (out / f"seg{k}_q{q}_src.hex").write_text("\n".join(src) + "\n")
            (out / f"seg{k}_q{q}_rec.hex").write_text("\n".join(rec) + "\n")
    span = CQ.span(F, R)
    t_start = [k * sp for k in range(NSEG)]
    off = [t + span for t in t_start]
    meta = dict(nseg=NSEG, R=R, n=n, slice=s, Bs=Bs, Es=Es, F=F, stride=stride, vm_rt=vm_rt, sp=sp, sp_min=sp_min,
                span_fire_to_last_write=span, fire_from_launch=CQ.FIRE_FROM_LAUNCH, go_lat=GO_LAT, t_start=t_start,
                go_off=off, last_write_rel_launch=[CQ.FIRE_FROM_LAUNCH + t + span for t in t_start],
                go_rel_launch=[GO_LAT + o for o in off],
                train_launch_to_last_landing=CQ.FIRE_FROM_LAUNCH + t_start[-1] + span,
                separate_records_note="7 records today: each its own CP dispatch + COLL wait; the census prices 260.2 each")
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    # params file for the bench (+define lines read by the runner)
    (out / "params.txt").write_text(f"-GSP={sp} -GSPAN={span} -GVM_RT={vm_rt}\n")
    print("AGSM8_VEC", json.dumps(meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
