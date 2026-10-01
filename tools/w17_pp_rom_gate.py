#!/usr/bin/env python3
"""Exhaustive DPI PP bank/address/edge/hold gate; no full-die build."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=['rtl/test/v41_runtime/ot_rom_4096x274_m8_rt.sv','rtl/test/v41_runtime/tb_w17_pp_rom.sv','rtl/test/v41_runtime/w17_pp_rom_test.cpp','tools/w17_pp_rom_gate.py']
def main():
    a=argparse.ArgumentParser();a.add_argument('--work',type=Path,required=True);a.add_argument('--result',type=Path,required=True);a=a.parse_args()
    if a.result.exists() or a.work.exists() and any(a.work.iterdir()):raise SystemExit('Use unique paths')
    a.work.mkdir(parents=True,exist_ok=True)
    pins={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC}
    vl=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator')
    cmd=[vl,'--cc','--exe','--build','-j','2','--top-module','tb_w17_pp_rom','--Mdir',str(a.work/'obj'),*[str(ROOT/s) for s in SRC[:3]]]
    p=subprocess.run(cmd,capture_output=True,text=True);(a.work/'build.log').write_text(p.stdout+p.stderr)
    runs=[]
    if p.returncode==0:
        for kind in ('normal','bank','parity'):
            env=dict(os.environ)
            if kind!='normal':env['W17_PP_MUTANT']=kind
            else:env.pop('W17_PP_MUTANT',None)
            r=subprocess.run([str(a.work/'obj/Vtb_w17_pp_rom')],capture_output=True,text=True,env=env)
            (a.work/f'{kind}.log').write_text(r.stdout+r.stderr)
            runs.append(dict(kind=kind,returncode=r.returncode,stdout=r.stdout))
    stable=pins=={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC}
    passed=p.returncode==0 and runs[0]['returncode']==0 and 'PASS checks=' in runs[0]['stdout'] and all(r['returncode']!=0 and 'FAIL addr=' in r['stdout'] for r in runs[1:]) and stable
    rec=dict(schema='opentallas.w17.pp_dpi_gate.v1',status='pass' if passed else 'fail',build_returncode=p.returncode,runs=runs,source_sha256=pins,source_stable=stable,git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    a.result.parent.mkdir(parents=True,exist_ok=True);a.result.write_text(json.dumps(rec,indent=2)+'\n');print(rec['status']);return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
