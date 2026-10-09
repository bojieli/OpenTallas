#!/usr/bin/env python3
"""Executable minimum Qwen r25 SU RoPE stage; tensor-full TP4 shape, P8191.

Emits the existing vec campaign's program encoding, not a hardware command
processor image. The two half-head operations avoid an unsupported arbitrary
XOR lane-offset assumption. Numerical and layout evidence is separate from
production N1024 cycle evidence; only --rtl with N1024 can supply that evidence.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import rtl_hdc_v41x_vec_campaign as C
import hdc_golden as G
import hdc_isa_v41 as I

POSITION = 8191
HEADS, HD = 10, 128  # eight Q heads and two K heads on one TP4 die
X, COS, SIN, Y = 0, 4096, 4224, 8192


def program(mutant=None):
    ops = []
    for h in range(HEADS):
        for half in range(2):
            f = C.op_defaults()
            f.update(nout=1, nin=64, abase=X+h*HD+half*64, asi=1,
                     bbase=COS+half*64, bsi=1,
                     cbase=X+h*HD+(1-half)*64, csi=1,
                     dbase=SIN+half*64, dsi=1,
                     m1=I.M1_AB, qm=I.QM_POS, ad=I.AD_Q,
                     dst=I.DST_VM, obase=Y+h*HD+half*64, osi=1)
            if mutant == 'adjacent_pair':
                f['cpair'] = 1
            ops.append(f)
    return ops


def fixture(mutant=None):
    rng = np.random.default_rng(8191)
    x = G.to_bf16(rng.standard_normal((HEADS, HD)).astype(np.float32)*3)
    # Released Qwen theta=1e6, full 128-dimensional rotate_half. Table
    # construction is a fixture, not checkpoint-provided production data.
    inv = np.power(1e6, -np.arange(0, HD, 2, dtype=np.float64)/HD)
    angles = np.float32(POSITION) * inv.astype(np.float32)
    cos = np.tile(np.cos(angles).astype(np.float32), 2)
    sin = np.tile(np.sin(angles).astype(np.float32), 2)
    signed = sin.copy(); signed[:64] = G.neg(signed[:64])
    m = C.Mem(np.zeros(1 << C.VMA, np.uint32),
              np.zeros(1 << C.KVA, np.uint32),
              np.zeros((1 << C.CRA, 2), np.uint32),
              np.zeros(1 << C.WRA, np.uint16))
    m.vm[X:X+x.size] = C.fbits(x).reshape(-1)
    m.vm[COS:COS+HD] = C.fbits(cos)
    m.vm[SIN:SIN+HD] = C.fbits(sin if mutant == 'missing_sign' else signed)
    rotated = np.concatenate((G.neg(x[:, 64:]), x[:, :64]), axis=1)
    expected = G.add(G.mul(x, cos), G.mul(rotated, sin))
    return m, expected


def check_reference(mutant=None):
    m, want = fixture(mutant)
    ops = program(mutant)
    for f in ops:
        ok, *_ = C.ref_op(f, m)
        assert ok
    got = m.vm[Y:Y+HEADS*HD].reshape(HEADS, HD)
    return int(np.count_nonzero(got != C.fbits(want)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--rtl', action='store_true')
    ap.add_argument('--exe', type=Path, help='previously source-matched c12 campaign Vtb')
    ap.add_argument('--n', type=int, default=64)
    ap.add_argument('--m', type=int, default=16)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rec = dict(schema='opentallas.qwen_r25_su_rope_stage.v1', position=POSITION,
               heads=HEADS, head_dim=HD, ops=len(program()),
               scope='SU stage only; synthetic fixture; no checkpoint quality or die-rate claim',
               reference_mismatches=check_reference(),
               negative_reference={k:check_reference(k) for k in ('adjacent_pair','missing_sign')},
               rtl=None, production_cycles=None)
    assert rec['reference_mismatches'] == 0
    assert all(v > 0 for v in rec['negative_reference'].values())
    C.write_case(a.out/'inputs', fixture()[0], program())
    if a.rtl:
        import hbm_su_c12 as S
        S.apply(C)
        # Host resource guard admits the build; no wall-time deadline.
        original_run_case = C.run_case
        C.run_case = lambda exe, d, nops, x=None: original_run_case(exe, d, nops, x, timeout=None)
        exe = a.exe or C.build(a.n,a.m,a.out/'obj',pmax=8192)[0]
        rows = {}
        for variant in (None, 'adjacent_pair', 'missing_sign'):
            mem, want = fixture(variant)
            ops = program(variant)
            compare, trace, scheduled, layouts = C.run_program(
                exe, a.out/(variant or 'positive'), mem, ops, a.n,a.m,chain=False)
            got = trace['vm']
            assert got is not None, 'No RTL memory output'
            mismatch = int(np.count_nonzero(got[Y:Y+HEADS*HD] != C.fbits(want).reshape(-1)))
            rows[variant or 'positive'] = dict(compare=compare,
                golden_mismatches=mismatch, end=trace['end'], faults=trace['faults'],
                orders=trace['orders'], acc=trace['acc'], emits=trace['emits'], rets=trace['rets'])
            assert compare['pass_'], compare
            assert (mismatch == 0) == (variant is None)
        rec['rtl'] = dict(n=a.n,m=a.m,rows=rows)
        if a.n == 1024 and a.m == 256:
            rec['production_cycles'] = rows['positive']['end'][0]
    rec['source_sha256'] = {str(p.relative_to(C.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in [Path(__file__).resolve(), *C.RTL,*C.LIB,C.TB]}
    (a.out/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps({k:v for k,v in rec.items() if k != 'source_sha256'},indent=2))

if __name__ == '__main__':
    main()
