#!/usr/bin/env python3
"""Minimum-controller API map gate. Run remotely under measured admission."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RTL=ROOT/'rtl/dsrom_sys/engram/ot_dsrom_engram_boot_ctrl_map.sv'
TB=ROOT/'rtl/test/tb_dsrom_engram_boot_ctrl_map.sv'
OUT=ROOT/'results/rtl/engram_boot_ctrl_map_gate_20261009.json'


def main():
    if OUT.exists(): raise FileExistsError('immutable map gate record exists')
    sources=[RTL,TB,ROOT/'tools/uarch_model.py',Path(__file__),
             ROOT/'rtl/dsrom_sys/s81_ph/dsfd_ctrl.sv',ROOT/'rtl/dsrom_sys/s81_ph/ot_s81ph_ctrl_pc.sv']
    rec=dict(schema='opentallas.engram-boot-controller-api.v1',
             boundary='real dsfd_ctrl rq packing and untagged wd-to-tag mapping; controller/PHY timing, shared runtime arbitration and die integration unqualified',
             input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},cases={})
    with tempfile.TemporaryDirectory(prefix='engram-map-') as tmp:
        work=Path(tmp)
        for name,mode,mutant in [('control',0,False),('duplicate_wd',1,False),('wrong_pc_atom',0,True)]:
            text=RTL.read_text()
            if mutant:
                needle="out_addr<={6'b0,atom[launch]};"
                assert text.count(needle)==1
                text=text.replace(needle,"out_addr<={6'b0,atom[launch]}+30'd1;")
            src=work/(name+'.sv');src.write_text(text)
            exe=work/(name+'.vvp')
            build=subprocess.run(['iverilog','-g2012','-s','tb_dsrom_engram_boot_ctrl_map','-o',str(exe),str(src),str(TB)],
                                 capture_output=True,text=True)
            if build.returncode: raise RuntimeError(build.stderr)
            run=subprocess.run(['vvp',str(exe),f'+MODE={mode}'],capture_output=True,text=True)
            if mutant: ok=run.returncode!=0 and 'wrong first PC atom' in run.stdout
            else: ok=run.returncode==0 and ('ENGRAM_MAP NEG' if mode else 'ENGRAM_MAP PASS') in run.stdout
            rec['cases'][name]=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected_observed=ok)
    rec['status']='pass' if all(v['expected_observed'] for v in rec['cases'].values()) else 'fail'
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(rec,indent=1)+'\n')
    print(rec['status'])
    return 0 if rec['status']=='pass' else 1


if __name__=='__main__':raise SystemExit(main())
