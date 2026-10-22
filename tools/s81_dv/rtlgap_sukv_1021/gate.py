#!/usr/bin/env python3
"""RTLGAP-SUKV 10-21 (G-L2-L20-HW): exactness benches for the S81 KV leaf's opt-in CN / IK (CNIK=1) and compressor pool
(CP=1), and for eng.knorm on the existing ot_s81sl_eg, against the LAYERBENCH-S81 golden fixtures of the 1M token
(tools/s81_dv/dv_layer_fixtures.py: L2 / L14 ratio 2, L20 ratio 1; HDC_V41_ARITH=chunk8).

  python3 tools/s81_dv/rtlgap_sukv_1021/gate.py --fx <fixtures dir with L2 L14 L20> --out <run dir>

Fleet only (Verilator 5.050 from hc_gate).  Positives: L2 (CP->CN->IK), L14 (CP->CN->IK + KV regression), L20 (CN->IK),
a synthetic pool stress case (ties, exp clamp, signs), each at VM latency 4 (and L2 at 1); eng.knorm on L14.  Negatives
(must FAIL): CP_MUT 1..5, CNIK_MUT 1..2, knorm wrong reduction order / swapped operands.  Writes result.json.
"""
import argparse, json, os, subprocess, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/s81_suhc')]
os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
import hdc_golden_v41 as V
import su_gate as S
import hc_gate as H
import dsrom_su_norm as NM
F = np.float32
POS = 1048575
EPS = F(1e-20)
FY = V.rope_freqs(64, 65536, 160000, 16, 32, 1)          # freqs_yarn (rope_head_dim 64, compress_rope_theta)


def u32(a):
    return np.asarray(a, F).view(np.uint32)


def same(a, b):
    return np.array_equal(u32(a), u32(b))


def put(vm, base, rows):
    for i, row in enumerate(rows):
        for q in range(4):
            vm[base + 4 * i + q] = (int(row) >> (128 * q)) & ((1 << 128) - 1)


def wmem(path, vals, w):
    Path(path).write_text(''.join(f'{int(v):0{w}x}\n' for v in vals))


def desc(out, nb=0, eps=EPS):
    return S.pack([out, 0, nb, int(u32([eps])[0])] + [0] * 12, 32)


def gk_image(w):
    vm = [0] * 1024
    put(vm, 528, [desc(0)])
    put(vm, 896, S.rows_of(np.asarray(w, F)))
    return vm


def bfw(p):
    return (np.fromfile(p, dtype='<u2').astype(np.uint32) << 16).view(F)


def case_from_fixture(fx, L):
    d = Path(fx) / L
    ld = lambda p: np.fromfile(d / p, dtype=F)
    r = 2 if L in ('L2', 'L14') else 1
    wkv = ld('ops/attn.cmp.wkv.bin')
    c = dict(name=L, ratio=r, wn=bfw(d / 'weights/compressor.norm.bin'), wk=ld('ops/attn.cmp.wk.bin'),
             kw=bfw(d / 'weights/indexer.k_norm.bin'), cs=V.rope_cs(FY, POS + 1 - r),
             fx=dict(norm=ld('ops/attn.cmp.norm.scale.bin'), row=ld('ops/attn.cmp.row_qdq.bin'),
                     knorm=ld('ops/attn.cmp.k_norm.scale.bin'), ik=ld('ops/attn.cmp.k_rope_qdq.bin')))
    if r == 2:
        sl = np.fromfile(d / f'state/kv.slots{L[1:]}.bin', dtype=F).reshape(-1, 2, 512)
        c.update(kv=np.stack([sl[0, 0], wkv[:512]]), sc=np.stack([sl[0, 1], wkv[512:]]), fx_pool=ld('ops/attn.cmp.pool.bin'))
    else:
        c.update(x=wkv)
    return c


def synthetic_pool(base):
    """stress: ties, large gaps (exp clamp at -87), sign mixes, zero kv, tiny / huge magnitudes (CN / IK operands,
    gains and RoPE of `base`)."""
    rng = np.random.default_rng(1021_2)
    s0 = rng.standard_normal(512).astype(F) * F(4)
    s1 = rng.standard_normal(512).astype(F) * F(4)
    s1[:16] = s0[:16]                                   # ties
    s1[16:32] = s0[16:32] - F(120)                      # e1 underflows through the clamp
    s0[32:48] = s1[32:48] - F(95)
    s1[48:56] = -s0[48:56]
    kv0 = rng.standard_normal(512).astype(F) * F(3)
    kv1 = rng.standard_normal(512).astype(F) * F(3)
    kv0[56:64] = 0; kv1[64:72] = -kv0[64:72]
    kv0[72:80] *= F(1e15); kv1[80:88] *= F(1e-30)
    return dict(name='SYN', ratio=2, kv=np.stack([kv0, kv1]), sc=np.stack([s0, s1]), wn=base['wn'], wk=base['wk'],
                kw=base['kw'], cs=base['cs'])


def pool(kvs, scs):
    mx = np.max(scs, axis=0)
    e = V.exp(V.add(scs, V.neg(mx)))
    p = V.div(e, V.seqsum(list(e))[None, :])
    return V.seqsum([V.mul(kvs[i], p[i]) for i in range(2)])


def prep(c, d, kv_regress=False):
    d.mkdir(parents=True, exist_ok=True)
    checks = {}
    if c['ratio'] == 2:
        y32 = pool(c['kv'], c['sc'])
        if 'fx_pool' in c:
            checks['pool_vs_fixture'] = same(y32, c['fx_pool'])
        x = V.to_bf16(y32)
        wmem(d / 'exp_cp32.mem', u32(y32), 8)
        wmem(d / 'exp_cp.mem', S.rows_of(x), 128)
    else:
        x = c['x']
    co, si = c['cs']
    # CN / IK expectations from the hub SU gate's own CN / IK row model (su_gate.Run.cn / .ik)
    r = S.Run(S.SHAPES['full'])
    b = r.cn(x, c['wn'], EPS, co, si)
    cn_rows = [r.exp[b['qdq_base'] + i] for i in range(16)] + [r.exp[b['raw_base'] + i] for i in range(16)] + \
              [r.exp[b['norm_base'] + i] for i in range(16)]
    lat = V.rmsnorm_bf16(x, c['wn'], EPS)
    k = V.rmsnorm_bf16(c['wk'], c['kw'], EPS)
    if 'fx' in c:
        checks['norm_vs_fixture'] = same(lat, c['fx']['norm'])
        checks['row_qdq_vs_fixture'] = same(V.qdq_fp4_e4m3(V.rope_tail(lat, c['cs']), 16), c['fx']['row'])
        checks['knorm_vs_fixture'] = same(k, c['fx']['knorm'])
        checks['k_rope_qdq_vs_fixture'] = same(V.qdq_fp4_e8m0(V.rope_tail(k, c['cs'])), c['fx']['ik'])
        qd = H.bf16bits(V.qdq_fp4_e4m3(V.rope_tail(lat, c['cs']), 16))
        checks['cn_qdq_rows_eq_fixture'] = all(cn_rows[i] == S.pack(qd[32 * i:32 * i + 32], 16) for i in range(16))
    r2 = S.Run(S.SHAPES['full'])
    b2 = r2.ik(c['wk'], c['kw'], EPS, co, si)
    ik_rows = [r2.exp[b2['qdq_base'] + i] for i in range(4)] + [r2.exp[b2['raw_base'] + i] for i in range(4)]
    wmem(d / 'exp_cn.mem', cn_rows, 128)
    wmem(d / 'exp_ik.mem', ik_rows, 128)
    wmem(d / 'img_gk3.mem', gk_image(c['wn']), 32)
    wmem(d / 'img_gk0.mem', gk_image(np.concatenate([np.zeros(384, F), c['kw']])), 32)
    vm = [0] * 1024
    put(vm, 672, [desc(168, 200)] + S.rows_of(np.concatenate([co, si])))
    if c['ratio'] == 2:
        for s in range(2):
            put(vm, 256 * s, S.rows_of(c['kv'][s]))
            put(vm, 256 * s + 128, S.rows_of(c['sc'][s]))
    else:
        put(vm, 692, S.rows_of(x))
    wmem(d / 'img_main.mem', vm, 32)
    vm = [0] * 1024
    put(vm, 672, [desc(168)] + S.rows_of(np.concatenate([co, si])))
    put(vm, 692, S.rows_of(np.concatenate([np.zeros(384, F), c['wk']])))
    wmem(d / 'img_ik.mem', vm, 32)
    if kv_regress:                                       # codex gate.py's KV case, on this layout
        rng = np.random.default_rng(1021512)
        xk = rng.standard_normal(512).astype(F); xk = H.f32(H.u32(xk) & np.uint32(0xffff0000))
        w = rng.uniform(.25, 1.75, 512).astype(F); w = H.f32(H.u32(w) & np.uint32(0xffff0000))
        ang = rng.uniform(-2, 2, 32); kc = np.cos(ang).astype(F); ks = np.sin(ang).astype(F); e6 = F(1e-6)
        _, ro = NM.golden_row('kv', xk, np.zeros(4, F), w, e6, (kc, ks))
        q = S.aq(ro); tmp = S.Run(S.SHAPES['full']); codes, exps = tmp.aq_rows(q, 512)
        exp = codes[0] + [exps[0]] + [H.pack(bb[2], 16) for bb in q]
        assert len(exp) == 25
        wmem(d / 'exp_kv.mem', exp, 128)
        wmem(d / 'img_kvg.mem', gk_image(w), 32)
        vm = [0] * 1024
        put(vm, 672, [168 | (int(H.u32([e6])[0]) << 96)] + S.rows_of(np.concatenate([kc, ks])))
        put(vm, 692, S.rows_of(xk))
        wmem(d / 'img_kv.mem', vm, 32)
    return checks


def prep_knorm(fx, d, mode='ok'):
    d.mkdir(parents=True, exist_ok=True)
    L = Path(fx) / 'L14'
    h = np.fromfile(L / 'io/h_in.bin', dtype=F).reshape(4, 5120)
    key = np.fromfile(L / 'ops/eng.wkv.bin', dtype=F)[:4 * 5120].reshape(4, 5120)
    exp = np.fromfile(L / 'ops/eng.knorm.bin', dtype=F)
    rows, gold = [], []
    for j in range(4):
        hh = V.reduce_sum_c(V.mul(h[j], h[j])); kk = V.reduce_sum_c(V.mul(key[j], key[j]))
        gold += [V.rsqrt(V.add(V.div(hh, F(5120)), EPS)), V.rsqrt(V.add(V.div(kk, F(5120)), EPS))]
        if mode == 'seqsum':                              # negative: plain sequential sum, not the csum chunk8 order
            hh = V.seqsum(list(V.mul(h[j], h[j]))); kk = V.seqsum(list(V.mul(key[j], key[j])))
        if mode == 'swap':                                # negative: h and k totals exchanged
            hh, kk = kk, hh
        rows.append((int(u32([F(0)])[0]) << 64) | (int(u32([kk])[0]) << 32) | int(u32([hh])[0]))
    assert same(np.asarray(gold, F), exp), 'eng.knorm golden != fixture'
    wmem(d / 'knorm.mem', rows, 24)
    wmem(d / 'exp_knorm.mem', u32(exp), 8)
    wmem(d / 'eps.mem', u32([EPS]), 8)


SRC_COMMON = ['rtl/dsrom_sys/s81_dv/slice/ot_s81sl_kv_bank.sv', 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_kv_leaf.sv',
              'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cmp_pool.sv',
              'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v']
TB = 'rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_kv_leaf_sukv.sv'
TBK = 'rtl/dsrom_sys/s81_dv/eng/test/tb_s81sl_eg_knorm.sv'


def build(out, tag, top, srcs, gparams):
    obj = out / f'obj_{tag}'
    cmd = [H.VERILATOR, '--binary', '--timing', '-O1', '-fno-dfg', '--unroll-count', '4', '-Wno-fatal', '-Wno-WIDTH',
           '--top-module', top, '-Mdir', str(obj), '-j', '8'] + [f'-G{k}={v}' for k, v in gparams.items()] + \
          [str(ROOT / s) for s in srcs] + ['-CFLAGS', '-O1']
    b = subprocess.run(cmd, capture_output=True, text=True)
    (out / f'build_{tag}.log').write_text(' '.join(cmd) + '\n' + b.stdout + b.stderr)
    if b.returncode:
        raise RuntimeError(f'build failed {out}/build_{tag}.log')
    return obj / f'V{top}'


def run(exe, d, args, log):
    r = subprocess.run([str(exe)] + args, cwd=d, capture_output=True, text=True)
    (d / log).write_text(r.stdout + r.stderr)
    return r.returncode, r.stdout + r.stderr


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fx', required=True); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    srcs = list(dict.fromkeys(H.FP['rtl'] + S.RTL + S.HIER + SRC_COMMON))
    egsrc = [l.strip() for l in (ROOT / 'rtl/dsrom_sys/s81_dv/eng/test/eg.f').read_text().split() if l.strip()]
    pins = {s: H.sha(ROOT / s) for s in srcs + egsrc + [TB, TBK, 'tools/s81_dv/rtlgap_sukv_1021/gate.py']}
    rec = dict(schema='opentallas.s81_rtlgap_sukv.gate.v1', simulator=subprocess.run([H.VERILATOR, '--version'],
               capture_output=True, text=True).stdout.strip(), fixtures=str(a.fx), golden_checks={}, positive={},
               negative={})
    cases = [case_from_fixture(a.fx, L) for L in ('L2', 'L14', 'L20')]
    cases.append(synthetic_pool(cases[0]))
    for c in cases:
        rec['golden_checks'][c['name']] = prep(c, a.out / c['name'], kv_regress=(c['name'] == 'L14'))
    from concurrent.futures import ThreadPoolExecutor
    MUTS = [('CP_MUT', 1), ('CP_MUT', 2), ('CP_MUT', 3), ('CP_MUT', 4), ('CP_MUT', 5), ('CNIK_MUT', 1), ('CNIK_MUT', 2)]
    jobs = {f'pos_v{vl}': ('tb_s81sl_kv_leaf_sukv', srcs + [TB], dict(VLAT=vl)) for vl in (4, 1)}
    jobs.update({f'{k}{v}': ('tb_s81sl_kv_leaf_sukv', srcs + [TB], {k: v, 'VLAT': 4}) for k, v in MUTS})
    jobs['knorm'] = ('tb_s81sl_eg_knorm', egsrc + [TBK], {})
    with ThreadPoolExecutor(max_workers=int(os.environ.get('SUKV_PAR', '3'))) as ex:
        fut = {t: ex.submit(build, a.out, t, *j) for t, j in jobs.items()}
        built = {t: f.result() for t, f in fut.items()}
    exe = {4: built['pos_v4'], 1: built['pos_v1']}
    for c in cases:
        args = (['+CP'] if c['ratio'] == 2 else []) + (['+KV'] if c['name'] == 'L14' else [])
        for vl in ((4, 1) if c['name'] == 'L2' else (4,)):
            rc, o = run(exe[vl], a.out / c['name'], args, f'run_v{vl}.log')
            rec['positive'][f"{c['name']}_v{vl}"] = dict(ok=rc == 0 and 'SUKV PASS' in o,
                                                       jobs=[l for l in o.splitlines() if l.startswith('SUKV')])
    # negatives on L2 (CP -> CN -> IK)
    for k, v in MUTS:
        e = built[f'{k}{v}']
        rc, o = run(e, a.out / 'L2', ['+CP'], f'run_{k}{v}.log')
        rec['negative'][f'{k}{v}'] = dict(failed=rc != 0 and 'SUKV FAIL' in o,
                                          lines=[l for l in o.splitlines() if 'SUKV' in l][:6])
    # eng.knorm
    ek = built['knorm']
    for mode in ('ok', 'seqsum', 'swap'):
        d = a.out / f'knorm_{mode}'
        prep_knorm(a.fx, d, mode)
        rc, o = run(ek, d, [], 'run.log')
        ok = rc == 0 and 'KNORM PASS' in o
        if mode == 'ok':
            rec['positive']['L14_eng_knorm'] = dict(ok=ok, lines=[l for l in o.splitlines() if 'KNORM' in l])
        else:
            rec['negative'][f'knorm_{mode}'] = dict(failed=not ok, lines=[l for l in o.splitlines() if 'KNORM' in l][:6])
    if pins != {s: H.sha(ROOT / s) for s in pins}:
        raise RuntimeError('source changed during the run')
    rec['source_sha256'] = pins
    gc_ok = all(all(v.values()) for v in rec['golden_checks'].values())
    rec['status'] = 'PASS' if gc_ok and all(v['ok'] for v in rec['positive'].values()) and \
        all(v['failed'] for v in rec['negative'].values()) else 'FAIL'
    (a.out / 'result.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ('status', 'golden_checks')}, indent=1))
    for k, v in rec['positive'].items():
        print('POS', k, v['ok'])
    for k, v in rec['negative'].items():
        print('NEG', k, v['failed'])
    return int(rec['status'] != 'PASS')


if __name__ == '__main__':
    sys.exit(main())
