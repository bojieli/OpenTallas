#!/usr/bin/env python3
"""fe-push-hgi-1010 (2026-10-10): gate of the registered MX1 MTP collar of the CP die (ot_hgi_cp_mtp_pinreg; ot_hgi_cp_die
MTP=2 MTP_PINREG=1).  iverilog, run off localhost (ot-heavy).

Cases:
  P_system_positive          tb_hgi_cp_mtp_pinreg_system: real native 40-layer controller hgi_mtp_native (PRL 4) <-> shell
                             <-> typed operation backend; two drained-reset jobs, 4 tokens each in order -> must PASS
  (MUT=1, native done not held behind the emit FIFO, does not discriminate in this system bench: the MX1 gate checks it in its pin bench)
  P_mutant_hostdone_not_held MUT=2 (host done overtakes the host-record FIFO)   -> must FAIL
  P_mutant_prl2              PRL=2 (controller ignores the +2 provider loop)    -> must FAIL
  C_cpdie_elab_pinreg        ot_hgi_cp_die MTP=2 MTP_PINREG=1 elaborates (and MTP_PINREG=0, MTP=1 unchanged)
Usage: python3 tools/hgi_cp_mtp_pinreg_gate.py --work DIR [--single CASE]   (--single: exit rc = the case's sim rc)
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_mx1_regb_gate as MX  # noqa: E402  (source lists of the MX1 REGB gate)

SHELL = 'rtl/hbm_accel/generic/ot_hgi_cp_mtp_pinreg.sv'
RELAY = 'rtl/lib/ot_rst_relay.sv'
TB = 'rtl/hbm_accel/generic/tb/tb_hgi_cp_mtp_pinreg_system.sv'
SYS = MX.NATIVE + MX.FACADE + MX.TOP + [MX.CMDPROC20, MX.BACKEND, RELAY, SHELL, TB]
CPDIE = ['rtl/hbm_accel/generic/ot_hgi_cp_die.sv', 'rtl/hbm_accel/generic/ot_hgi_cp.sv', 'rtl/hbm_accel/generic/ot_hgi_cfg.sv',
         'rtl/hbm_accel/generic/ot_hgi_seq.sv', 'rtl/hbm_accel/generic/ot_hgi_mtp_xlate.sv',
         'physical/hbm_cp_mtp_native/rtl/hfd_cmdproc_s_mtp_native_mx1.sv', 'rtl/common/ot_sc_pfifo.sv',
         'rtl/hbm_accel/control/ot_hbm_native_mtp_transaction_cp_join_mx1.sv',
         'rtl/hbm_accel/control/ot_hbm_native_mtp_emit_queue_mx1.sv', RELAY, SHELL]
CASES = {'P_system_positive': ('pass', ()),
         'P_mutant_hostdone_not_held': ('fail', ('MUT=2',)), 'P_mutant_prl2': ('fail', ('PRL=2',))}


def sim(work, name, params):
    top = 'tb_hgi_cp_mtp_pinreg_system'
    exe = work / f'{name}.vvp'
    b = subprocess.run(['iverilog', '-g2012', '-s', top, *[f'-P{top}.{p}' for p in params], '-o', str(exe),
                        *[str(ROOT / s) for s in SYS]], capture_output=True, text=True)
    if b.returncode:
        return {'case': name, 'phase': 'compile', 'returncode': b.returncode, 'output': b.stdout + b.stderr}
    r = subprocess.run(['vvp', '-n', str(exe)], capture_output=True, text=True, cwd=work)
    out = r.stdout + r.stderr
    rc = r.returncode if r.returncode else (0 if 'PASS HGI_CP_MTP_PINREG' in out else 1)
    return {'case': name, 'phase': 'sim', 'returncode': rc, 'output': out[-3000:]}


def elab(work):
    res = []
    for tag, params in (('pinreg', ('MTP=2', 'MTP_PINREG=1')), ('direct', ('MTP=2', 'MTP_PINREG=0')), ('mtp1', ('MTP=1',))):
        files = list(CPDIE)
        files += [s for s in ('rtl/hbm_accel/generic/ot_hgi_cp_ring.sv',) if (ROOT / s).exists()]
        b = subprocess.run(['iverilog', '-g2012', '-s', 'ot_hgi_cp_die', '-Pot_hgi_cp_die.USE_MACRO=0',
                            *[f'-Pot_hgi_cp_die.{p}' for p in params], '-o', str(work / f'cpdie_{tag}.vvp'),
                            '-y', str(ROOT / 'rtl/hbm_accel/generic'), '-y', str(ROOT / 'rtl/common'), '-y', str(ROOT / 'rtl/lib'),
                            '-Y', '.sv', '-I', str(ROOT / 'rtl/hbm_accel/generic'), *[str(ROOT / s) for s in files]], capture_output=True, text=True)
        res.append({'case': f'C_cpdie_elab_{tag}', 'phase': 'compile', 'returncode': b.returncode, 'output': (b.stdout + b.stderr)[-2000:]})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--single')
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    if a.single:
        if a.single == 'C_cpdie_elab':
            r = elab(a.work)
            for c in r:
                print(c['case'], 'rc', c['returncode'], c['output'][-400:])
            print('HGI_CP_MTP_PINREG_ELAB', 'PASS' if all(c['returncode'] == 0 for c in r) else 'FAIL')
            raise SystemExit(max(c['returncode'] for c in r))
        c = sim(a.work, a.single, CASES[a.single][1])
        print(c['output'][-1500:])
        if c['phase'] == 'compile':
            raise SystemExit('compile error (not a functional failure)')
        print(f"HGI_CP_MTP_PINREG_CASE {a.single} rc={c['returncode']}")
        raise SystemExit(c['returncode'])
    out, ok = [], True
    for name, (exp, params) in CASES.items():
        c = sim(a.work, name, params)
        c['expect'] = exp
        c['ok'] = c['phase'] == 'sim' and ((c['returncode'] == 0) == (exp == 'pass'))
        ok &= c['ok']
        out.append(c)
        print(name, exp, 'rc', c['returncode'], 'OK' if c['ok'] else 'BAD')
    for c in elab(a.work):
        c['expect'] = 'pass'; c['ok'] = c['returncode'] == 0; ok &= c['ok']; out.append(c)
        print(c['case'], 'rc', c['returncode'], 'OK' if c['ok'] else 'BAD')
    (a.work / 'gate.json').write_text(json.dumps({'ok': ok, 'cases': out}, indent=1) + '\n')
    print('HGI_CP_MTP_PINREG_GATE', 'PASS' if ok else 'FAIL')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
