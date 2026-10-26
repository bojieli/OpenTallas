#!/usr/bin/env python3
"""KVJ-E: run the compiled landing-calendar boot words (target 4) on the actual qkd_kv_landing_cal RTL.

    run_kv_static_programme_lcal.py COMPILE_DIR OUT [--T 77 4097 8192] [--groups all|WS_0,...]

COMPILE_DIR is a kv_static_programme.py output (report.json).  For each group and context T this writes a
tb_qkd_kv_landing_cal case file carrying the COMPILED constants (XU, H0, RC, LD, K / V pacing, the die PH0) and the
independent golden streams (tools/qwen_static_kv/landing_cal_golden.py: kv_calendar K / PV16 V sectors and put
offsets), and runs the existing bench (iverilog).  The bench checks every r_put / l_put edge and sector of the leaf
against its own integer arithmetic from those constants, so a PASS means the boot image drives the real leaf to the
kv_calendar streams.  Exit 0 iff every case passes.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools.qwen_static_kv import landing_cal_golden as G      # noqa: E402
from tools.qwen_static_schedule import kv_calendar as K        # noqa: E402
from tools.qwen_kv_die import static_kv_calendar as S         # noqa: E402

SRC = ['rtl/test/qwen_static_kv/tb_qkd_kv_landing_cal.sv', 'rtl/qwen_sys/static_kv_20261014/qkd_kv_landing_cal.sv']
STACKS = ('WS', 'WN', 'ES', 'EN')


def case_text(grp, s, e, T, ph0, ld, rc, kgo, vgo, leaf='landing', pr=None):
    """sectors: the independent golden (landing_cal_golden / kv_calendar); put offsets: the leaf law of the compiled
    (P0, GAP), which kv_static_programme.law_check proved feasible at every checked T.  Without an RD shape (component
    profile) the law must also equal kv_calendar's own per-T schedule (the bench golden)."""
    P = G.P
    ks = K.k_streams(T, P)
    vs = K.pv16_v_streams(T)
    pc = S.physical_pc(s, e, 0)
    kst, vst = ks.get(pc, []), vs.get(pc, [])
    k, v = grp['K'], grp['V']

    def offs(n, p0, gap):
        return [i + (gap * (1 + (i - p0) // 8) if i >= p0 else 0) for i in range(n)]
    ko, vo = offs(len(kst), k['P0'], k['GAP']), offs(len(vst), v['P0'], v['GAP'])
    if not pr.get('rd_shape'):
        kp = K.pc_schedule(kst, P, 0)['put'] if kst else []
        vp = K.pc_schedule_paced(vst, P, K._layer_pc_paced(vst, P)[0])['put'] if vst else []
        if [x - kp[0] for x in kp] != ko or [x - vp[0] for x in vp] != vo:
            raise SystemExit(f'compiled pacing of group {s}{e} does not give the kv_calendar put offsets at T={T}')
    ksec = [x for x, _, _ in kst]
    vsc = [G.vsec(t) for _, _, t in vst]
    return (f'{s} {e} {T} {ph0} {grp["XU"]} {grp["H0_landing" if leaf == "landing" else "H0_front"]} {rc} {ld} {kgo} {vgo} {len(ksec)} {len(vsc)} '
            f'{k["P0"]} {k["GAP"]} {v["P0"]} {v["GAP"]}\n'
            + ' '.join(map(str, ksec + [0])) + '\n' + ' '.join(map(str, ko + ko[:1])) + '\n'
            + ' '.join(map(str, vsc + [0])) + '\n' + ' '.join(map(str, vo + vo[:1])) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('compile_dir', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--T', type=int, nargs='+', default=[77, 4097, 8192])
    ap.add_argument('--groups', default='all')
    ap.add_argument('--leaf', choices=('landing', 'front'), default='landing', help='front: target-5 words on qkd_kv_front_cal')
    a = ap.parse_args()
    rep = json.loads((a.compile_dir / 'report.json').read_text())
    groups = rep['groups']
    names = list(groups) if a.groups == 'all' else a.groups.split(',')
    ph0 = (rep['profile'].get('phase') or {}).get('PH0', 0)
    ld, rc = rep['profile']['ld'], rep['profile']['rc']
    kgo = 40
    vgo = kgo + rep['leads']['vgo_minus_kgo']
    a.out.mkdir(parents=True, exist_ok=True)
    tb = 'tb_qkd_kv_landing_cal' if a.leaf == 'landing' else 'tb_qkd_kv_front_cal'
    src = SRC if a.leaf == 'landing' else ['rtl/test/qwen_static_kv/tb_qkd_kv_front_cal.sv', 'rtl/qwen_sys/static_kv_20261014/qkd_kv_front_cal.sv']
    binary = a.out / f'{a.leaf}_p{ph0}.vvp'
    b = subprocess.run(['iverilog', '-g2012'] + (['-P', f'{tb}.PH0={ph0}'] if a.leaf == 'landing' else []) + ['-o', str(binary)] + [str(ROOT / f) for f in src],
                       capture_output=True, text=True)
    if b.returncode:
        raise SystemExit(b.stderr)
    results, bad = [], 0
    for n in names:
        st, g = n.split('_')
        s, e = STACKS.index(st), int(g)
        for T in a.T:
            cf = a.out / f'c_{T}_{s}_{e}.txt'
            cf.write_text(case_text(groups[n], s, e, T, ph0, ld, rc, kgo, vgo, a.leaf, rep['profile']))
            r = subprocess.run(['vvp', '-n', str(binary), f'+CASE={cf}'], capture_output=True, text=True, timeout=600)
            line = next((l for l in r.stdout.splitlines()[::-1] if l.startswith(('PASS landing_cal', 'FAIL landing_cal', 'PASS front_cal', 'FAIL front_cal'))), 'NORESULT')
            ok = line.startswith('PASS')
            bad += not ok
            results.append(dict(group=n, T=T, result=line))
    receipt = dict(schema='opentallas.qwen_kv_static.programme_lcal_rtl.v1', compile_profile=rep['profile']['kind'],
                   programme_sha256=rep['programme_sha256'], cases=len(results), failed=bad, results=results,
                   scope='compiled target-4 constants on the actual qkd_kv_landing_cal leaf (tb_qkd_kv_landing_cal); '
                         'not the joined subsystem, not physical')
    receipt['leaf'] = a.leaf
    (a.out / 'receipt.json').write_text(json.dumps(receipt, indent=1) + '\n')
    print(f'RESULT {"OK" if not bad else "FAIL"} {a.leaf}_cal compiled cases={len(results)} failed={bad}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
