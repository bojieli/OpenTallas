#!/usr/bin/env python3
"""RTLGAP-SO (10-21): image maker for tb_so_golden.sv -- the L0 normalised SO (attn.normalize / attn.normalize.unrope) on
the 16 REAL per-slice SM shares ot_s81_su_sms (the share every dsdv_svc_rs instantiates, -DSU_SMU_T), driven with:
  * the SE job the compiler emits today (lower_svc Job SMJ kind 4 frame: params row0 / sinks row1) + the SE operand rows
    the REAL 16-slice svc RTL produced (tb_svc_lower ALLQ se_dump: the score-exchange SE assembler rows, bit-exact there);
  * the SO programme of lower_svc.so_frames (SMJ kind 5 + 16 operand frames, 534 q words) whose operand payload is the
    REAL ALLQ P.V words of the same run (tb_svc_lower pv_dump: E entry tiles 0..7, W entry tiles 8..15), transposed here
    by a pure bit permutation -- the stand-in of the PVSO ingress (codex/s81-pv-so-assembly-1021 dsdv_pv_so_ingress),
    no arithmetic, never the fixture attn.pv.
Every slice decodes the SMJ q words exactly as dsdv_svc_att (sm_st = hdr[0], kind [4:1], jid [12:5]; payload rows
sm_rv = !hdr[13] || hdr[14 + tile], sm_rp = !hdr[13], sm_rj = payload index).  Expected: SE e rows = fixture attn.exp (FP32
bits), SO o rows = fixture attn.normalize.unrope (BF16 bits), addresses / masks per ot_s81_su_smq.

  so_bench.py --fixtures FX --dump IMGDIR/base [--seed 1] --out OUT     (writes OUT/{base,cs_swap,hm_shift}/)
"""
import argparse, hashlib, json, os, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parents[1])); sys.path.insert(0, str(HERE.parents[2]))
os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
import lower_svc as L  # noqa: E402

E_SE_OBASE = 0x0000          # the SE job's obase (lower_svc row0 [13:0] = 0)


def verify_reference_sources(fx):
    """Restore the fixture's existing numerical contract before making coefficients."""
    import hdc_golden_v41 as V
    import hdc_golden as G
    root = HERE.parents[3]
    paths = {
        'tools/hdc_golden_v41.py': Path(V.__file__),
        'tools/hdc_golden.py': Path(G.__file__),
        'compiler/models/deepseek-v4.1-flash/inference_config.json':
            root / 'compiler/models/deepseek-v4.1-flash/inference_config.json',
    }
    expected = json.loads((Path(fx) / 'meta.json').read_text())['sources']
    checked = {}
    for name, path in paths.items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected[name]:
            raise ValueError(f'fixture reference source mismatch: {name}: '
                             f'{actual} != {expected[name]}')
        checked[name] = actual
    return checked


def read_pv_dump(path):
    """{entry sid: [(cycle, 513-b word)]} -> pv u32 [16, 512] (decode as tb_svc_lower ALLQ)"""
    seq = {5: [], 11: []}
    for ln in Path(path).read_text().splitlines():
        s, c, w = ln.split()
        seq[int(s)].append((int(c), int(w, 16)))
    pv = np.zeros((16, 512), dtype=np.uint64)
    seen = np.zeros((16, 512), dtype=bool)
    for s, words in seq.items():
        assert len(words) == 320, (s, len(words))
        t0 = 0 if s == 11 else 8
        pc = 0
        for n, (c, w) in enumerate(words):
            t, wi = t0 + n // 40, n % 5
            if wi == 0:
                assert (w >> 512) & 1, 'header marker'
                pc = (w >> 64) & 255
            else:
                d = 32 * t + 8 * (wi - 1) + pc
                for h in range(16):
                    pv[h, d] = (w >> (32 * h)) & 0xFFFFFFFF
                assert not seen[:, d].any(), d
                seen[:, d] = True
    assert seen.all(), 'P.V dims missing'
    return pv.astype(np.uint32)


def read_se_dump(path):
    """slice -> [512-b SE operand rows] in arrival order (8 a slice at T 128)"""
    se = {s: [] for s in range(16)}
    for ln in Path(path).read_text().splitlines():
        s, c, w = ln.split()
        se[int(s)].append(int(w, 16))
    return se


def build(fx, dump, out, seed=1):
    fx = Path(fx)
    reference_sources = verify_reference_sources(fx)
    job = L.Job(fx, tag=0, allq=True)
    pv = read_pv_dump(Path(dump) / f'pv_dump_s{seed}.hex')
    se = read_se_dump(Path(dump) / f'se_dump_s{seed}.hex')
    cos, sin = L.rope_cs_u32(fx)
    ops = json.loads((fx / 'ops.json').read_text())
    ld = lambda n: np.fromfile(fx / f'ops/{n}.bin', dtype=np.dtype(ops[n]['dtype'])).reshape(ops[n]['shape'])
    h0 = job.h0
    unrope = ld('attn.normalize.unrope')[h0:h0 + 16]
    ub = (np.asarray(unrope, np.float32).view(np.uint32) >> 16).astype(np.uint32)     # BF16 bits
    assert np.array_equal(np.asarray(unrope, np.float32).view(np.uint32) & 0xFFFF, np.zeros_like(ub)), 'unrope not BF16'
    expv = np.asarray(ld('attn.exp')[h0:h0 + 16], np.float32).view(np.uint32)       # [16, T]
    T = job.T
    nv = -(-T // 16)
    se_frame = [w for name, ws in job.frames if name == 'SMJ' for w in ws]            # SE header + row0 + row1
    recs = {}
    for mut in (None, 'cs_swap', 'hm_shift'):
        so = L.so_frames(0, cos, sin, pv, mutant=mut)
        # cycles at the share pins (tb drives at c, the decoder registers like dsdv_svc_att: +1)
        t_se = 20
        q = [(t_se + k, w) for k, w in enumerate(se_frame)]                          # SE SMJ frame
        t_rows = t_se + len(se_frame) + 4
        se_rows = [(t_rows + r, r) for r in range(nv)]                                # SE operand rows, every slice
        sch = L.so_schedule(t_rows + nv - 1, nv)
        t = sch['start']
        for name, ws in so:
            if name == 'SMJ_OP0':
                t = max(t, sch['first_op'] - 1)                                       # header one edge before row 0
            for w in ws:
                q.append((t, w)); t += 1
        d = Path(out) / (mut or 'base')
        d.mkdir(parents=True, exist_ok=True)
        hx = lambda xs, bits: ''.join(f'{x:0{-(-bits // 4)}x}\n' for x in xs)
        (d / 'qcyc.hex').write_text(hx([c for c, _ in q], 32))
        (d / 'qwd.hex').write_text(hx([w for _, w in q], 512))
        (d / 'secyc.hex').write_text(hx([c for c, _ in se_rows], 32))
        tile = {sd: L.tile_of(sd) for sd in range(16)}
        sew = []
        for g in range(16):
            sd = [k for k, v in tile.items() if v == g][0]
            assert len(se[sd]) == nv, (sd, len(se[sd]))
            sew += se[sd]
        (d / 'serow.hex').write_text(hx(sew, 512))                                   # [g * nv + r]
        oe = [sum(int(ub[g, 16 * k + i]) << (16 * i) for i in range(16)) for g in range(16) for k in range(32)]
        (d / 'oexp.hex').write_text(hx(oe, 256))                                     # [g * 32 + k]
        ee = [sum(int(expv[g, 16 * r + i]) << (32 * i) for i in range(16) if 16 * r + i < T) for g in range(16) for r in range(nv)]
        (d / 'eexp.hex').write_text(hx(ee, 512))
        meta = [len(q), nv, L.SO_OBASE, E_SE_OBASE, sch['first_op'], sch['den'], 0, 0]
        (d / 'meta.hex').write_text(hx(meta + [0] * (16 - len(meta)), 32))
        recs[mut or 'base'] = dict(q_words=len(q), so_words=sum(len(ws) for _, ws in so), sched=sch, mutant=mut,
                                   reference_sources=reference_sources,
                                   pv_source=str(Path(dump) / f'pv_dump_s{seed}.hex'), se_source=str(Path(dump) / f'se_dump_s{seed}.hex'))
    (Path(out) / 'so_images.json').write_text(json.dumps(recs, indent=1) + '\n')
    return recs


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixtures', required=True); ap.add_argument('--dump', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()
    print(json.dumps(build(a.fixtures, a.dump, a.out, a.seed), indent=1))
