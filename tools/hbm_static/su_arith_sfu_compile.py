#!/usr/bin/env python3
"""Full N512 static-SU bench of the SFU-lane operations: exp, sigmoid, SiLU and the IEEE divider.

Same real grid as su_arith_compile.py (512 lanes, 3072 pinned SRAMs, fixed 64-issue calendar, one control image
per quarter per edge); differences:
  * SFU operations run on the 32 SFU lanes of each quarter only (local lanes 0..31, KIND 1/2): the compiler sets
    lvw = 5, so lanes 32..127 are not live and must NOT write.  The bench checks both: every live lane writes its 64
    outputs on the compiled edge, every dead lane writes nothing and its SRAM row keeps the previous content.
  * the issue -> receiving-pin edge count is per operation (opinfo.mem), from the lane's insertion depths
    (divider 19 at M1, exp 7M+8A+4, sigmoid/SiLU exp+A+19); the bench FAILS on any other edge, so a PASS measures
    the per-op latency the SU calendar (su_f2_spread.py DEPTHS) uses.
Golden: independent NumPy (hdc_golden exp = the algorithm ot_hdc_v41x_exp implements, checked there on all 2^32
inputs; IEEE binary32 division = NumPy float32 division, correctly rounded; canonical +0).  No DUT arithmetic here.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from su_arith_compile import pack, physical_word  # noqa: E402
from hdc_golden import add, exp, mul, neg, z  # noqa: E402

F = np.float32
SFU_EXP, SFU_SIGM, SFU_SILU = 1, 4, 5
M1_DIVB, M1_DIVIMM = 4, 5
# (name, control fields, live lanes per quarter)
OPS = [('EXP', dict(ci_sfu=SFU_EXP, cs_sfu=SFU_EXP)),
       ('EXP_SCALE_SUBB', dict(cp_m1=3, cm_m1=3, ca_ad=3, ci_sfu=SFU_EXP, cs_sfu=SFU_EXP)),   # softmax exp(s*x - max)
       ('SIGM', dict(ci_sfu=SFU_SIGM, cs_sfu=SFU_SIGM)),
       ('SILU', dict(ci_sfu=SFU_SILU, cs_sfu=SFU_SILU)),
       ('SILU_E1C_E2B', dict(ci_sfu=SFU_SILU, cs_sfu=SFU_SILU, cs_e1=1, ce_e2=1)),           # swiglu
       ('DIVB', dict(cp_m1=M1_DIVB, cm_m1=M1_DIVB)),                                          # pv_normalize, attend.norm
       ('DIVIMM', dict(cp_m1=M1_DIVIMM, cm_m1=M1_DIVIMM)),
       ('BYP_LIGHT', dict())]                                                                 # all 128 lanes, control


def depth(mods, mlat, alat):
    d_exp = 7 * mlat + 8 * alat + 4
    s = {0: 0, SFU_EXP: d_exp, SFU_SIGM: d_exp + alat + 19, SFU_SILU: d_exp + alat + 19}[mods.get('ci_sfu', 0)]
    div = (19 - mlat) if mods.get('cp_m1') in (M1_DIVB, M1_DIVIMM) else 0
    return s + div


def fdiv(a, b):
    with np.errstate(all='ignore'):
        return z(np.asarray(a, F) / np.asarray(b, F))


def main():
    out = Path(sys.argv[1])
    mlat, alat, leaf = (int(x) for x in sys.argv[2:5]) if len(sys.argv) > 4 else (3, 3, 0)
    out.mkdir(parents=True, exist_ok=True)
    lane = np.arange(512, dtype=F)
    rows = [F((lane % 31 - 15) * F(.125) + (row % 64) * F(.03125) + (row // 64) * F(.25)) for row in range(512)]
    data = np.stack(rows).astype(F)
    data[:64] += F(.0004) * ((np.arange(512) % 7) - 3).astype(F)
    b = data[64:128]
    data[64:128] = np.where(b == 0, F(0.5), b)            # divisor rows nonzero (source data only)
    (out / 'seed.mem').write_text('\n'.join(f'{x:08x}' for x in data.view(np.uint32).ravel()) + '\n')
    a, b, c, d = (data[k * 64:(k + 1) * 64] for k in range(4))
    prev = data[256:320].copy()                            # SRAM rows 256..319 hold the seed until written
    live_sfu = (np.arange(512) % 128) < 32
    gold, controls, info = [], [], []
    base_lat = 23 + 4 * (mlat - 3) + (alat - 3) + leaf
    for name, mods in OPS:
        x = a.copy()
        m = mods.get('cp_m1', 0)
        if m == 3:
            x = mul(a, F(1.25))
        if m == M1_DIVB:
            x = fdiv(a, b)
        if m == M1_DIVIMM:
            x = fdiv(a, F(1.25))
        if mods.get('ca_ad') == 3:
            x = add(x, neg(b))
        sf = mods.get('ci_sfu', 0)
        if sf == SFU_EXP:
            x = exp(x)
        elif sf in (SFU_SIGM, SFU_SILU):
            den = add(exp(neg(x)), F(1.0))
            x = fdiv(x if sf == SFU_SILU else np.full_like(x, F(1.0)), den)
        if mods.get('cs_e1') == 1:
            x = mul(x, c)
        if mods.get('ce_e2') == 1:
            x = mul(x, b)
        sfu = bool(sf) or m in (M1_DIVB, M1_DIVIMM)
        live = live_sfu if sfu else np.ones(512, bool)
        res = np.where(live[None, :], x, prev).astype(F)
        prev = res
        gold.extend(res.view(np.uint32).ravel())
        ctl = dict(no=1, ni=8192, ls=7, lvw=5 if sfu else 7, dst=1, co_dst=1,
                   cp_imm1=0x3fa00000, cm_imm1=0x3fa00000, ce_imm1=0x3fa00000,
                   ca_imm2=0x3ec00000, cs_imm2=0x3ec00000, cx_imm3=0x3f400000, **mods)
        controls.append(ctl)
        lat = base_lat + depth(mods, mlat, alat)
        info.append(dict(op=name, sfu_lanes_only=sfu, issue_to_output=lat, extra_vs_light=lat - base_lat))
    (out / 'gold.mem').write_text('\n'.join(f'{x:08x}' for x in gold) + '\n')
    (out / 'opinfo.mem').write_text(''.join(f'{i["issue_to_output"]:02x}{int(i["sfu_lanes_only"]):x}\n' for i in info))
    terms = sum((1 << k) << (24 * (s * 10 + k)) for s in range(5) for k in range(7))
    images = []
    for ctl in controls:
        for cycle in range(256):
            combined = 0
            vector = max(0, min(63, cycle - 8))
            for q in range(4):
                fields = dict(ctl, ld=int(cycle == 0), ld_c=terms, emit=int(8 <= cycle < 72), i_v=vector * 128,
                              vb=sum(physical_word(q, (s * 64 if s < 4 else 256) + vector) << (s * 24) for s in range(5)))
                combined |= pack(fields) << (q * 1742)
            images.append(combined)
    (out / 'control.mem').write_text('\n'.join(f'{x:01742x}' for x in images) + '\n')
    (out / 'programme.json').write_text(json.dumps(dict(
        qualified=False, ops=info, MLAT=mlat, ALAT=alat, LEAF=leaf, issues_per_op=64, cycles_per_op=256,
        live_outputs=sum(64 * (128 if i['sfu_lanes_only'] else 512) for i in info),
        source='independent hdc_golden exp + NumPy IEEE float32 division, canonical +0; full real N512/M128'),
        indent=2) + '\n')


if __name__ == '__main__':
    main()
