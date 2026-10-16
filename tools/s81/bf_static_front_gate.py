#!/usr/bin/env python3
"""Actual dsfd_bf_front_static public-pin programme/boundary gate.

Two physical roots are tied at a fixed phase for this functional check. The
source calendar is fixed before simulation; only public packed master pins are
observed. This is not a BF numerical column or production-CFG7 qualification.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
MASTER = 'rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_static.sv'
FRONT = 'rtl/s81/ot_s81_bf_front.sv'
CORE = 'rtl/v41rom/ot_v41_bf_front_core.sv'
FILES = ['tests/s81/tb_bf_static_front.sv', MASTER, FRONT,
         'rtl/s81/ot_s81_bf_seam.sv', CORE,
         'rtl/v41rom/ot_v41_rom_elem_w10.sv', 'rtl/v41rom/ot_v41_kreg.sv',
         'rtl/common/ot_prefix.sv', 'rtl/hdc/ot_hdc_cg.sv']
MUTANTS = {
    'programme_register_bypass': ('define', 'BF_PROG_MUTANT_CORE_BYPASS', ''),
    'control_latch_go_lost': ('define', 'BF_CTL_LAT_MUTANT_GO', ''),
    'read_pointer_copy_stall': ('define', 'BF_FRD_MUTANT_COPY', ''),
    'cpin_register_bypass': (MASTER, '.CPIN(1)', '.CPIN(0)'),
    'address_check_removed': (CORE, 'prog_addr_pin != a_ctr ||', "1'b0 ||"),
    'pinlat_payload_lsb_loss': ('define', 'PINLAT_MUTANT_B0', ''),
    'seam_issue_slot_inversion': ('define', 'BF_SEAM_MUTANT_SLOT', ''),
}

def main():
    import sys
    # --mutant NAME: run ONLY that mutant as a plain bench (exit = the tb's exit; a closure-loop expect=fail bench)
    only = sys.argv[sys.argv.index('--mutant')+1] if '--mutant' in sys.argv else None
    sources = {f:(ROOT/f).read_text() for f in FILES}
    # Packed die-pin ABI differs from the internal CPIN concat ordering.
    for n, name in [(0,'issue'),(15,'i1_v')]:
        assert f'assign c0[{n}] = w_c0_{name};' in sources[MASTER]
        assert f'assign c1[{n}] = w_c1_{name};' in sources[MASTER]
    for n in range(14):
        assert f'assign c0[{n+1}] = w_c0_a_ctr[{n}];' in sources[MASTER]
    for n in range(17):
        assert f'assign c0[{n+18}] = w_c0_i1_t[{n}];' in sources[MASTER]
    results = {}
    with tempfile.TemporaryDirectory(prefix='bf-static-front-') as td:
        td=Path(td)
        for name in ([only] if only else ['positive', *MUTANTS]):
            files = dict(sources)
            defines=[]
            if name != 'positive':
                path,before,after=MUTANTS[name]
                if path == 'define':
                    defines=['-D'+before]
                else:
                    assert files[path].count(before)==1, (name,before)
                    files[path]=files[path].replace(before,after)
            paths=[]
            for i,(path,data) in enumerate(files.items()):
                p=td/f'{i}.sv';p.write_text(data);paths.append(str(p))
            binary=td/'sim.vvp'
            build=subprocess.run(['iverilog','-g2012','-s','tb_bf_static_front',*defines,'-o',str(binary),*paths],capture_output=True,text=True)
            if build.returncode: raise RuntimeError(build.stderr)
            run=subprocess.run(['vvp',str(binary)],capture_output=True,text=True)
            if only:
                print(run.stdout + run.stderr)
                code = 1 if (run.returncode != 0 or 'FATAL' in run.stdout) else 0
                print(f'MUTANT {only} ' + ('FAIL (detected)' if code else 'PASS (NOT detected)'))
                raise SystemExit(code)
            if name=='positive':
                assert run.returncode==0 and 'PASS actual BF static die front' in run.stdout,run.stdout+run.stderr
            else:
                assert run.returncode!=0 and 'FATAL' in run.stdout,(name,run.stdout,run.stderr)
            results[name]={'exit':run.returncode,'output':run.stdout.strip()}
    print(json.dumps({'scope':'Actual die-front control and payload boundary component; not BF numerical columns, CFG7 workload, production throughput or physical skew qualification',
                      'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES},
                      'pin_age_edges':{'issue':2,'i1_valid_and_tag':3,'operand_q0':4},
                      'compiled_slots':64,'clock_roots':'ck and io_clk: two physical roots of one die clock (tied at the die); every io_clk->ck crossing register->lockup latch->register; tied in the functional bench',
                      'results':results},indent=2))

if __name__=='__main__':main()
