#!/usr/bin/env python3
"""QW-XHEAD 10-19: the x CONSUMER lowering (tools/qwen_layerbench/dv_lower_xhead.py) on the 12-slice qfd_dv_slice2 die
chain (tb_qfd_dv2.sv N 12 +define+DV2_XHEAD: hr port 42, per-slice heads logs XT / CW / XL / HF), Verilator 5.050.

The x writes are the REAL producer families on their compiled edges (dv_lower_vec_bench: resid -> the x stream of
gate/up and the next qkv, attn -> o_proj, silu -> down); this bench adds the head-row words the lowering emits (the XPF
arm descriptor and the go with its ib, DV-relocated xbase 0) on dvs_W5.hr_i and checks every slice's heads:
  * no heads fault (tap range / epoch / per-element valid: a go before the last beat or an XPF after the first beat
    reads an unwritten element -> sticky FAULT, never a stale value), no slice fault (status_ok2), the family's own checks;
  * every slice's 8 column heads launch their corridor go on the lowered edge (go hr edge + hr_at + d_head), the
    corridor x lines run tiles * k * IL edges (+ read_tail);
  * every x word of the family reached every slice's tap (S<k>XT) on its lowered edge (stream reference + x_tap).
Modes:
  --calibrate   measure x_tap, d_head, read_tail (XPF early, go late) and sweep go_lag / xpf_lead (the smallest PASSING
                value; the next smaller one must FAIL) -> xhead_ages.json
  --run C       C in qkv | gu | o | down: the lowered XPF / go (measured ages) [--mutant goearly | xpflate | isaxbase]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_layerbench'))
import dv_bench2 as B2            # noqa: E402
import dv_lower as D              # noqa: E402
import dv_lower_bench as LB       # noqa: E402
import dv_lower_vec_bench as VB   # noqa: E402
import dv_lower_xhead as X        # noqa: E402

N = D.NSLICE
P_HR = 42
FAMILY = dict(qkv='resid', gu='resid', o='attn', down='silu')
STATE = {}


BUILD = {}


def build_xh(work):
    obj = BUILD['dir'] / 'obj_xh'          # ONE executable for every run of this bench (+DV2_XHEAD)
    exe = obj / 'Vtb'
    if not exe.exists():
        cmd = ['verilator', '--cc', '--exe', '--build', '-O2', '-j', '16', '-Wno-fatal', '-Wno-lint', '-Wno-style',
               '-Wno-TIMESCALEMOD', '--x-assign', '0', '--x-initial', '0', '--top-module', 'tb_qfd_dv2', '--prefix', 'Vtb',
               '+define+DV2_XHEAD', '-GMUT=0', f'-GN={N}', '-Mdir', str(obj), str(HERE / 'main2.cpp')] + \
              [str(ROOT / s) for s in B2.SRCS2]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (BUILD['dir'] / 'build_xh.log').write_text(r.stdout)
        if r.returncode:
            raise SystemExit(f'BENCH ERROR: build failed (see {BUILD["dir"]}/build_xh.log)')
    return exe


_orig_run = LB.run


def run_hook(work, name, ev, ncyc):
    log = _orig_run(work, name, ev, ncyc)
    STATE['log'] = log
    return log


def lowered_hook(ev, lw, base):
    end = _orig_lowered(ev, lw, base)
    STATE['lw'], STATE['base'] = lw, base
    plan = STATE['plan'](lw, base)
    for t, w in plan['hr']:
        ev.at(t, P_HR, w)
    STATE['hr_plan'] = plan
    return max(end, plan['end'])


_orig_lowered = VB.lowered


def heads_log(log):
    xt = {m: [c for c, _ in log.get(f'S{m}XT', [])] for m in range(N)}
    cw = {m: [(c, v) for c, v in log.get(f'S{m}CW', [])] for m in range(N)}
    xl = {m: [c for c, _ in log.get(f'S{m}XL', [])] for m in range(N)}
    hf = {m: log[f'S{m}HF'][0][0] for m in range(N) if f'S{m}HF' in log}
    return xt, cw, xl, hf


def run_family(work, consumer, plan_fn, tag, seed=1):
    """the producer family's own bench run (its checks) + the hr plan; returns (family verdict line rc, log)"""
    STATE.clear()
    STATE['plan'] = plan_fn
    VB.lowered = lowered_hook
    LB.run = run_hook
    LB.build = build_xh
    (work / tag).mkdir(parents=True, exist_ok=True)
    try:
        rc = VB.main_run(work / tag, FAMILY[consumer], None, seed, None, 'row' if FAMILY[consumer] == 'resid' else 'slice')
    finally:
        VB.lowered = _orig_lowered
        LB.run = _orig_run
    return rc, STATE


def op_fields(consumer, lw, isa_xbase=False):
    f = X.me_ops()[consumer]
    xs, ea = X.x_edges(lw['expected']['x'])
    g = X.dv_fields(f, ea)
    if isa_xbase:
        g = dict(g, me_xbase=g['isa_xbase'])
    return g


# ------------------------------------------------------------------------------------------------ calibrate
def calibrate(work):
    work.mkdir(parents=True, exist_ok=True)
    hr_at = X.bench_hr_arrival()
    res = {}

    def plan_free(consumer, go_lag=None, xpf_lead=None, x_tap=None):
        def fn(lw, base):
            f = op_fields(consumer, lw)
            xs, _ = X.x_edges(lw['expected']['x'], shift=base)
            if go_lag is None:                 # timing probe: XPF well before the stream, go well after it
                xpf = min(min(v) for v in xs.values()) - 40
                go = max(max(v) for v in xs.values()) + 60
            else:
                xt = {m: [e + x_tap for e in v] for m, v in xs.items()}
                go = max(max(v) + go_lag - hr_at[m] for m, v in xt.items())
                xpf = min(min(v) - xpf_lead - hr_at[m] for m, v in xt.items())
            hr = [(xpf, X.hr_word(xpf72=X.pack_xpf72(f))), (go, X.hr_word(go=1, ib=X.pack_ib(f)))]
            return dict(hr=hr, xpf=xpf, go=go, xs=xs, f=f, end=go + X.read_span(f) + 200)
        return fn

    def verdict(consumer, st, rc):
        xt, cw, xl, hf = heads_log(st['log'])
        errs = B2.status_ok2(st['log'])
        return dict(rc=rc, hf=hf, slice_faults=errs, cw=cw, xt=xt, xl=xl,
                    ok=(rc == 0 and not hf and not errs and all(cw[m] for m in range(N))))

    consumer = 'gu'
    rc, st = run_family(work, consumer, plan_free(consumer), 'cal_probe')
    v = verdict(consumer, st, rc)
    p = st['hr_plan']
    xs = p['xs']
    # x_tap: every slice's XT edges vs the stream reference edges
    taps = set()
    for m in range(N):
        if len(v['xt'][m]) != len(xs[m]):
            raise SystemExit(f'CALIBRATE: slice {m} saw {len(v["xt"][m])} x writes, the family streams {len(xs[m])}')
        taps |= {a - b for a, b in zip(v['xt'][m], xs[m])}
    if len(taps) != 1:
        raise SystemExit(f'CALIBRATE: x_tap not constant {sorted(taps)}')
    x_tap = taps.pop()
    d_head = {cw[0][0] - (p['go'] + hr_at[m]) for m, cw in v['cw'].items() if cw}
    if len(d_head) != 1 or not v['ok']:
        raise SystemExit(f'CALIBRATE: probe run not clean (d_head {d_head}, hf {v["hf"]}, faults {v["slice_faults"]}, '
                         f'rc {v["rc"]})')
    d_head = d_head.pop()
    rs = X.read_span(p['f'])
    tails = {max(v['xl'][m]) - (p['go'] + hr_at[m] + d_head + rs) for m in range(N)}
    read_tail = max(tails)
    res['probe'] = dict(xpf=p['xpf'], go=p['go'], x_tap=x_tap, d_head=d_head, read_tail=sorted(tails),
                        cw_edges={m: v['cw'][m][:2] for m in range(3)}, xl_edges=len(v['xl'][0]))
    # sweeps: the smallest passing go_lag (with a generous XPF lead) and xpf_lead (with a generous go lag)
    sweep = dict(go_lag={}, xpf_lead={})
    for g in range(-2, 7):
        rc, st = run_family(work, consumer, plan_free(consumer, g, 12, x_tap), f'cal_go{g}')
        sweep['go_lag'][g] = verdict(consumer, st, rc)['ok']
    for L in range(-2, 7):
        rc, st = run_family(work, consumer, plan_free(consumer, 20, L, x_tap), f'cal_xpf{L}')
        sweep['xpf_lead'][L] = verdict(consumer, st, rc)['ok']

    def smallest(d):
        ks = sorted(d)
        for k in ks:
            if d[k] and all(d[j] for j in ks if j >= k):
                return k
        return None
    go_lag, xpf_lead = smallest(sweep['go_lag']), smallest(sweep['xpf_lead'])
    if go_lag is None or xpf_lead is None or go_lag == min(sweep['go_lag']) or xpf_lead == min(sweep['xpf_lead']):
        raise SystemExit(f'CALIBRATE: sweep has no PASS/FAIL edge {sweep}')
    ages = dict(schema='opentallas.qwen.dv-xhead-ages.v1', x_tap=x_tap, xpf_lead=xpf_lead, go_lag=go_lag,
                d_head=d_head, read_tail=read_tail, il=X.IL, sweep=sweep, probe=res['probe'],
                bench='rtl/test/qwen_dv/xhead_bench.py --calibrate (tb_qfd_dv2 N 12 +DV2_XHEAD, real resid x stream, '
                      'consumer gate/up k 32 S 128)',
                rule='x_tap: stream reference edge (dv_lower_xhead.x_edges) -> S<k>XT; d_head: go at the slice hr pin '
                     '(W5 hr event + hr_at) -> S<k>CW; read_tail: last S<k>XL - (head go + tiles k IL); go_lag / xpf_lead: '
                     'smallest passing value of the sweep (value - 1 FAILS)',
                verilator=subprocess.run(['verilator', '--version'], stdout=subprocess.PIPE, text=True).stdout.strip())
    (work / 'xhead_ages.json').write_text(json.dumps(ages, indent=1) + '\n')
    print('XHEAD_CALIBRATE', json.dumps({k: ages[k] for k in ('x_tap', 'xpf_lead', 'go_lag', 'd_head', 'read_tail')}),
          json.dumps(sweep))
    return 0


# ------------------------------------------------------------------------------------------------ run
def run(work, consumer, ages_path, mutant=None):
    ages = json.loads(Path(ages_path).read_text())
    hr_at = X.bench_hr_arrival()

    def fn(lw, base):
        f = op_fields(consumer, lw, isa_xbase=(mutant == 'isaxbase'))
        xs, _ = X.x_edges(lw['expected']['x'], shift=base)
        c = X.lower_consumer(consumer, f, xs, ages, hr_at)
        xpf, go = c['xpf_w5'], c['go_w5']
        if mutant == 'goearly':
            go -= 1
        if mutant == 'xpflate':
            xpf += 1
        hr = [(xpf, X.hr_word(xpf72=X.pack_xpf72(f))), (go, X.hr_word(go=1, ib=X.pack_ib(f)))]
        return dict(hr=hr, low=c, xs=xs, f=f, end=go + c['read_span'] + 200)
    tag = f'{consumer}_{mutant or "m0"}'
    rc, st = run_family(work, consumer, fn, tag)
    p = st['hr_plan']
    c = p['low']
    xt, cw, xl, hf = heads_log(st['log'])
    errs = B2.status_ok2(st['log'])
    if rc:
        errs.append(f'producer family bench rc {rc}')
    if hf:
        errs.append(f'heads FAULT on slices {sorted(hf)} (first edge {min(hf.values())})')
    for m in range(N):
        want = [e + ages['x_tap'] for e in p['xs'][m]]
        if xt[m] != want:
            errs.append(f'slice {m}: x writes {xt[m][:3]}.. != lowered {want[:3]}..')
        g = [e for e, v in cw[m]]
        if g[:1] != [c['head_go'][m]]:
            errs.append(f'slice {m}: corridor go {g[:2]} != lowered {c["head_go"][m]}')
        if cw[m] and cw[m][0][1] != 0xFF:
            errs.append(f'slice {m}: {cw[m][0][1]:08b} of the 8 column heads launched')
        if xl[m] and max(xl[m]) > c['read_end'][m]:
            errs.append(f'slice {m}: last x line {max(xl[m])} after the lowered read end {c["read_end"][m]}')
    verdict = 'PASS' if not errs else 'FAIL'
    out = dict(consumer=consumer, mutant=mutant, verdict=verdict, errors=errs[:20], xpf_w5=p['hr'][0][0],
               go_w5=p['hr'][1][0], base=st['base'], lowered=dict(go_min=c['go_min'], xpf_window=c['xpf_window'],
               head_go=c['head_go'], read_end=c['read_end'], read_span=c['read_span']),
               measured=dict(first_cw={m: cw[m][0][0] if cw[m] else None for m in range(N)},
                             last_xl={m: max(xl[m]) if xl[m] else None for m in range(N)},
                             xl_edges={m: len(xl[m]) for m in range(N)}),
               span_x_to_last_line=max(v for v in (max(xl[m]) if xl[m] else 0 for m in range(N))) -
               min(min(v) for v in xt.values() if v) if any(xl.values()) else None)
    (work / f'xhead_{tag}.json').write_text(json.dumps(out, indent=1) + '\n')
    print(f'XHEAD {consumer} {verdict} mutant={mutant or 0} xpf_w5={out["xpf_w5"]} go_w5={out["go_w5"]} '
          f'go_slack_min={min(c["slack_go"].values())} xpf_slack_min={min(c["slack_xpf"].values())} '
          f'read_span={c["read_span"]}')
    for e in errs[:8]:
        print('   ', e)
    return 0 if verdict == 'PASS' else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True)
    ap.add_argument('--calibrate', action='store_true')
    ap.add_argument('--run', choices=tuple(FAMILY))
    ap.add_argument('--ages')
    ap.add_argument('--mutant', choices=('goearly', 'xpflate', 'isaxbase'))
    ap.add_argument('--build-dir', help='where obj_xh lives (shared by every run; default --work)')
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    BUILD['dir'] = Path(a.build_dir) if a.build_dir else work
    if a.calibrate:
        return calibrate(work)
    return run(work, a.run, a.ages or work / 'xhead_ages.json', a.mutant)


if __name__ == '__main__':
    raise SystemExit(main())
