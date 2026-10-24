#!/usr/bin/env python3
"""S81-P9-CF 10-23: crs4_bench.py for dsfd_cfifo_crs4p (LK parameter, census-safe chunked rings; compiled once per K with
-DKP=K, tb rtl/dsrom_sys/s81_dv/land/test/tb_cfifo_crs4p.sv).  Same geometries, sweep, slips, mutants and verdict rule.

S81-LAND2 bench of dsfd_cfifo_crs4 (rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv) against the CLOSED dsfd_cfifo_crs
(tb rtl/dsrom_sys/s81_dv/land/test/tb_cfifo_crs4.sv, iverilog).

The reference runs at zero lane skew with its marker epoch; the successor gets every lane on its OWN forwarded clock
with a per-lane source-synchronous lag DLk (lanes of one frame deliberately spread, incl. lanes 0 / 3 far from 1 / 2:
the dsfd_cfifo_crs gap), the hop-0 ICG opened at source edge G, and one compile-time K = E + G (E from the window rule
of LANDING-CONTRACT L5: E = ceil((max dL + 80 + margin) / T)).  Every sweep point (common lag shift -80..+80 ps) must
deliver the reference's xa / xb / cc / x2 stream EXACTLY at one constant offset (the compile-time latency difference,
= E + a constant: it follows the compile-time E, never the dL inside the window), rd identical, fault 0.  A calendar slip on lane 0 or 3 must raise fault.
Mutants: NBR (lanes 0 / 3 captured on the neighbour lane's clock = the old gap), SEL (landing read slot one late) and
NAIVE (S81-DIE7/CRS4: bounded-skew retime register instead of the ring) must FAIL.

  python3 tools/s81_dv/crs4_bench.py [--out results/arch/s81_dv_1016/landing/crs4p_bench.json]
  python3 tools/s81_dv/crs4_bench.py --variant base|mut_nbr|mut_sel|mut_naive --out RUN/x.json   (one variant; prints
      'CRS4P_BENCH PASS|FAIL <variant> ...' = that variant's OWN behavioural verdict, exit 0 PASS / 1 FAIL -- the
      hardened-view kit benches, tools/s81_dv/crs4_gate.sh)
"""
import argparse, json, math, re, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
TB = 'rtl/dsrom_sys/s81_dv/land/test/tb_cfifo_crs4p.sv'
SRC = ['rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4p.sv', 'rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv',
       'rtl/dsrom_sys/s81_dv/land/ot_s81_land_fo.sv',
       'rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_crs.sv', 'rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_ingress_hr.sv',
       'rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross_hr.sv', 'rtl/hdc/ot_hdc_cg.sv']
T, SKEW, MARGIN = 834, 80, 100
R0 = 2          # read epoch: the cfifo's rsync releases rc at source edge 2 of the tb (raw rst released after edge -1)
REF_LAT = 6     # reference dsfd_cfifo_crs: offset of its xa/xb/cc/x2 stream behind the successor's at E = 0 (measured)
GEOM = [dict(name='aligned_dL_80', dl=[80, 80, 80, 80], G=4), dict(name='halfT', dl=[450, 400, 420, 480], G=4),
        dict(name='lanes03_far_900', dl=[900, 100, 100, 900], G=4),
        dict(name='spread_16hop', dl=[1400, 1900, 2300, 2600], G=2)]
SWEEP = list(range(-SKEW, SKEW + 1, 40))
VARIANTS = (('base', None), ('mut_nbr', 'OT_CRS4_MUT_NBR'), ('mut_sel', 'OT_S81_LAND_MUT_SEL'), ('mut_naive', 'OT_S81_LAND_MUT_NAIVE'))


def run(b, args):
    out = subprocess.run(['vvp', '-n', b] + [f'+{k}={v}' for k, v in args.items()], capture_output=True, text=True).stdout
    m = re.search(r'OT_CRS4 (.*)', out)
    if not m:
        return dict(error=out[-300:])
    return {k: (v if ',' in v else int(v)) for k, v in (kv.split('=') for kv in m.group(1).split())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=ROOT / 'results/arch/s81_dv_1016/landing/crs4p_bench.json')
    ap.add_argument('--variant', choices=[v for v, _ in VARIANTS])
    ap.add_argument('-j', '--jobs', type=int, default=4)
    a = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix='crs4p_'))
    res = dict(schema='opentallas.s81_land.crs4_bench.v1', tb=TB, sources=SRC, T_ps=T, skew_sweep_ps=SWEEP, margin_ps=MARGIN,
               rule='E = ceil((max dL + 80 + margin)/T); K = E + G - R0; one K for the 4 lanes; predicted offset = E - REF_LAT', R0=R0, REF_LAT=REF_LAT, variants={})
    verdict = True
    for var, dfn in VARIANTS:
        if a.variant and var != a.variant:
            continue
        def comp(k):
            b = str(tmp / f'{var}_k{k}')
            if not Path(b).exists():
                subprocess.run(['iverilog', '-g2012', f'-DKP={k}', '-o', b, str(ROOT / TB)] + [str(ROOT / s) for s in SRC] + ([f'-D{dfn}'] if dfn else []), check=True)
            return b
        vr = dict(expect='PASS' if var == 'base' else 'FAIL', runs=[])
        jobs = []                                       # (geom, E, K, b, args, tag): all runs in parallel (-j)
        for g in GEOM:
            e = math.ceil((max(g['dl']) + SKEW + MARGIN) / T)
            assert min(g['dl']) - SKEW > (e - 4) * T + MARGIN
            k = e + g['G'] - R0
            b = comp(k)
            for s in SWEEP:
                dl = [d + s for d in g['dl']]
                jobs.append((g, e, k, b, dict(DL0=dl[0], DL1=dl[1], DL2=dl[2], DL3=dl[3], K=k, G=g['G'], SEED=3 + s), dict(shift=s)))
            for sl in ('SLIP0', 'SLIP3'):
                jobs.append((g, e, k, b, dict(DL0=g['dl'][0], DL1=g['dl'][1], DL2=g['dl'][2], DL3=g['dl'][3], K=k, G=g['G'], **{sl: 1}),
                             dict(slip_test=sl)))
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            outs = list(ex.map(lambda jb: run(jb[3], jb[4]), jobs))
        offs = {}
        for (g, e, k, b, args, tag), r in zip(jobs, outs):
            r.update(geom=g['name'], E=e, **tag)
            if 'slip_test' in tag:
                r['ok'] = r.get('fault') == 1
            else:
                r['ok'] = r.get('dmism', 1) == 0 and r.get('rmism', 1) == 0 and r.get('fault', 1) == 0 and r.get('nz', 0) > 100
                offs.setdefault(g['name'], set()).add(r.get('off'))
            vr['runs'].append(r)
            vr.setdefault('offset_by_geom', {})[g['name']] = dict(K=k, G=g['G'], E=e, offsets=sorted(o for o in offs.get(g['name'], ()) if o is not None))
        sw = [r for r in vr['runs'] if 'slip_test' not in r]
        vr['sweep_pass'] = sum(r['ok'] for r in sw); vr['sweep_runs'] = len(sw)
        vr['slip_fault_raised'] = sum(r['ok'] for r in vr['runs'] if 'slip_test' in r)
        # compile-time latency: offset vs the reference = E + one constant over every geometry and sweep point
        cst = {o - vv['E'] for vv in vr['offset_by_geom'].values() for o in vv['offsets']}
        vr['offset_minus_E'] = sorted(cst)
        ok = vr['sweep_pass'] == vr['sweep_runs'] and vr['slip_fault_raised'] == 2 * len(GEOM) and cst == {-REF_LAT}
        vr['verdict'] = 'PASS' if ok else 'FAIL'
        verdict &= vr['verdict'] == vr['expect']
        res['variants'][var] = vr
        print(var, vr['verdict'], f"sweep {vr['sweep_pass']}/{vr['sweep_runs']} slip-fault {vr['slip_fault_raised']}/{2 * len(GEOM)}",
              json.dumps(vr['offset_by_geom']), 'off-E', vr['offset_minus_E'])
    res['verdict'] = 'PASS' if verdict else 'FAIL'
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1) + '\n')
    if a.variant:
        vr = res['variants'][a.variant]
        print('CRS4P_BENCH', vr['verdict'], a.variant, f"sweep {vr['sweep_pass']}/{vr['sweep_runs']}",
              f"slip-fault {vr['slip_fault_raised']}/{2 * len(GEOM)}", 'off-E', vr['offset_minus_E'], a.out)
        raise SystemExit(0 if vr['verdict'] == 'PASS' else 1)
    print('BENCH', res['verdict'], a.out)


if __name__ == '__main__':
    main()
