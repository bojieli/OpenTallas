#!/usr/bin/env python3
"""Explicit opt-in successor source list. Example:
python3 tools/hbm_su_div64.py campaign --ddiv 64 --quick --only random --scratch /tmp/div64 --out /tmp/div64.json
Uses unchanged c12 default parameters unless --ddiv 64 is explicitly supplied.
"""
import hbm_su_c12 as C
import os
import re
import subprocess
import shlex

def install():
    for key, values in list(C.SWAP.items()):
        if any(x in key for x in ('vec_lane.sv', 'vec_side.sv', 'v41x_sfu.sv')):
            C.SWAP[key] = ['rtl/hbm_accel/su/div64_candidate/' + p.split('/')[-1] for p in values]
    additions = ['rtl/hdc/v41/ot_hdc_fdiv64.sv', 'rtl/hdc/ot_hdc_cg.sv']
    C.C12_UNITS.extend(additions)
    C.C12_UNITS_DPI.extend(additions)
    original_apply = C.apply
    def apply(VC, dpi=False):
        original_apply(VC, dpi)
        VC.TB_SFU = C.ROOT / 'rtl/test/tb_hbm_su_div64_sfu.sv'
        VC.sfu_equivalence = lambda scratch, n=200000: sfu_equivalence(VC, scratch, n)
    C.apply = apply

def sfu_equivalence(VC, scratch, n):
    """Pass actual selected DDIV to the SFU bench; never silently test default21."""
    ddiv, fsq = C.P['ddiv'], C.P['fsq']
    obj = scratch / f"obj_sfu_m{VC.MLAT}a{VC.ALAT}_d{ddiv}_f{fsq}"
    obj.mkdir(parents=True, exist_ok=True)
    exe = obj / 'Vtb'
    if not exe.exists():
        defines = [f for f in shlex.split(os.environ.get('OT_VFLAGS', '')) if f.startswith('-D')]
        cmd = [VC.VERILATOR, '--cc', '--exe', '--build', '-O2', '-Wno-fatal', '-Wno-WIDTH',
               '-Wno-UNUSED', '-Wno-BLKSEQ', *defines, '--top-module', 'tb_hdc_v41x_vec_sfu',
               '--prefix', 'Vtb', f'-GMLAT={VC.MLAT}', f'-GALAT={VC.ALAT}',
               f'-GDDIV={ddiv}', f'-GFSQ={fsq}', '-Mdir', str(obj),
               *map(str, VC.LIB), str(VC.RTL[0]), str(VC.TB_SFU), str(VC.HARNESS), '-CFLAGS', '-O1']
        built = subprocess.run(cmd, capture_output=True, text=True)
        (obj / 'build.log').write_text(built.stdout + built.stderr)
        built.check_returncode()
    run = subprocess.run([str(exe), f'+N={n}'], capture_output=True, text=True)
    (obj / 'runtime.log').write_text(run.stdout + run.stderr)
    run.check_returncode()
    match = re.search(r"V41XSFU n=(\d+) div=(\d+) div_err=(\d+) exp=(\d+) exp_err=(\d+) rsq=(\d+) rsq_err=(\d+) "
                      r"rsq_fault_timing=(\d+) sp=(\d+) sp_err=(\d+)", run.stdout)
    if match is None:
        raise RuntimeError('SFU campaign missing terminal result')
    v = list(map(int, match.groups()))
    return dict(operands=v[0], selected_ddiv=ddiv, selected_fsq=fsq,
                fdiv_vs_ot_hdc_fdiv=dict(checked=v[1], errors=v[2]),
                exp_vs_ot_hdc_exp=dict(checked=v[3], errors=v[4]),
                rsqrt_vs_ot_hdc_rsqrt=dict(checked=v[5], errors=v[6], fault_timing_differences=v[7]),
                softplus_vs_ot_hdc_softplus=dict(checked=v[8], errors=v[9]),
                pass_=v[1] > 0 and v[3] > 0 and v[5] > 0 and v[8] > 0 and
                      v[2] == 0 and v[4] == 0 and v[6] == 0 and v[9] == 0)


if __name__ == '__main__':
    install()
    raise SystemExit(C.main())
