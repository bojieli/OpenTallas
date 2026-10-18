#!/usr/bin/env python3
"""S81-LAND landing bench driver (rtl/dsrom_sys/s81_dv/land/test/tb_s81_land.sv, iverilog).

Skew sweep: four lane geometries whose nominal forwarded-clock lag dL = (N + 1) * DH - LR sits at 0 (phase wrap),
T/2, T (one cycle of age: wrap) and 2T (16-hop lane, wrap); each is swept +-80 ps (the neighbour skew budget) by moving
the block root insertion LR.  The compiler picks ONE K per geometry from its nominal dL (window rule of
LANDING-CONTRACT.md: E = ceil((dL + 80 + margin) / T), K = E + G - R0); every sweep point must deliver the exact word
stream at the predicted compile-time latency N + 1 + E with fault 0.  A calendar slip (gate opened one edge late) must
raise fault.  Mutants: NAIVE (bounded-skew retime register without the ring: latency follows the phase) and SEL (read
slot one late) must FAIL.

  python3 tools/s81_dv/land_bench.py [--out results/arch/s81_dv_1016/landing/bench.json] [--widths 70 276]
"""
import argparse, json, math, re, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
TB = ROOT / 'rtl/dsrom_sys/s81_dv/land/test/tb_s81_land.sv'
DUT = ROOT / 'rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv'
T, D, R0, G, MARGIN, SKEW = 834, 4, 4, 6, 100, 80
GEOM = [dict(name='dL0_wrap', N=0, DH=100, LR=100), dict(name='dL_halfT', N=3, DH=135, LR=140),
        dict(name='dL_T_wrap_age1', N=6, DH=131, LR=83), dict(name='dL_2T_wrap_16hop', N=15, DH=115, LR=172)]
SWEEP = list(range(-SKEW, SKEW + 1, 20))


def pick_k(dl):
    e = math.ceil((dl + SKEW + MARGIN) / T)
    assert dl - SKEW > (e - D) * T + MARGIN, 'window too narrow for this dL spread'
    return e, e + G - R0


def run(binary, args):
    out = subprocess.run(['vvp', '-n', binary] + [f'+{k}={v}' for k, v in args.items()], capture_output=True, text=True).stdout
    m = re.search(r'OT_LAND (.*)', out)
    return {k: int(v) for k, v in (kv.split('=') for kv in m.group(1).split())} if m else {'error': out[-400:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=ROOT / 'results/arch/s81_dv_1016/landing/bench.json')
    ap.add_argument('--widths', type=int, nargs='+', default=[70, 276])
    a = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix='s81land_'))
    res = dict(schema='opentallas.s81_land.bench.v1', tb=str(TB.relative_to(ROOT)), dut=str(DUT.relative_to(ROOT)),
               T_ps=T, D=D, R0=R0, G=G, margin_ps=MARGIN, skew_sweep_ps=SWEEP, variants={})
    verdict = True
    for var, define in (('base', None), ('mut_naive', 'OT_S81_LAND_MUT_NAIVE'), ('mut_sel', 'OT_S81_LAND_MUT_SEL')):
        vr = dict(runs=[], expect='PASS' if var == 'base' else 'FAIL')
        for w in a.widths:
            b = tmp / f'{var}_{w}'
            cmd = ['iverilog', '-g2012', f'-DTB_W={w}', '-o', str(b), str(TB), str(DUT)] + ([f'-D{define}'] if define else [])
            subprocess.run(cmd, check=True)
            for g in GEOM:
                dl0 = (g['N'] + 1) * g['DH'] - g['LR']
                e, k = pick_k(dl0)
                for s in SWEEP:
                    r = run(str(b), dict(N=g['N'], DH=g['DH'], LR=g['LR'] - s, K=k, R0=R0, G=G))
                    r.update(geom=g['name'], E=e, ok=(r.get('mism', 1) == 0 and r.get('fault', 1) == 0 and r.get('meas') == r.get('pred')))
                    vr['runs'].append(r)
                r = run(str(b), dict(N=g['N'], DH=g['DH'], LR=g['LR'], K=k, R0=R0, G=G, SLIP=1))   # calendar slip
                r.update(geom=g['name'], E=e, slip_test=True, ok=(r.get('fault') == 1))
                vr['runs'].append(r)
        sweep = [r for r in vr['runs'] if not r.get('slip_test')]
        vr['sweep_pass'] = sum(r['ok'] for r in sweep); vr['sweep_runs'] = len(sweep)
        vr['slip_fault_raised'] = sum(r['ok'] for r in vr['runs'] if r.get('slip_test'))
        vr['latency_by_geom'] = {}
        for r in sweep:
            vr['latency_by_geom'].setdefault(f"{r['geom']}/w{r['w']}", set()).add(r.get('meas'))
        vr['latency_by_geom'] = {k: sorted(v) for k, v in vr['latency_by_geom'].items()}
        passed = vr['sweep_pass'] == vr['sweep_runs'] and vr['slip_fault_raised'] == len(GEOM) * len(a.widths)
        vr['verdict'] = 'PASS' if passed else 'FAIL'
        verdict &= (vr['verdict'] == vr['expect'])
        res['variants'][var] = vr
        print(var, vr['verdict'], f"sweep {vr['sweep_pass']}/{vr['sweep_runs']} slip-fault {vr['slip_fault_raised']}", vr['latency_by_geom'])
    res['verdict'] = 'PASS' if verdict else 'FAIL'
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1) + '\n')
    print('BENCH', res['verdict'], a.out)


if __name__ == '__main__':
    main()
