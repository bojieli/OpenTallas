#!/usr/bin/env python3
"""Minimum aggregate arithmetic fault event -> actual SU-side controller gate."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import hbm_su_cp_side as C

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    files=C.CP_SRC+['rtl/test/tb_hbm_su_fault_event.sv']
    results={}
    for name,defines in [('positive',[]),('bypass_negative',['-DOT_NEG_SU_EVENT_BYPASS'])]:
        exe=a.out/(name+'.out')
        cmd=['iverilog','-g2012','-s','tb_hbm_su_fault_event',*defines,'-o',str(exe),*files]
        built=subprocess.run(cmd,capture_output=True,text=True)
        (a.out/(name+'_compile.log')).write_text(built.stdout+built.stderr)
        built.check_returncode()
        run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
        (a.out/(name+'.log')).write_text(run.stdout+run.stderr)
        passed=(run.returncode==0 and 'PASS SU_FAULT_EVENT cases=3 checks=55' in run.stdout) if name=='positive' else (
            run.returncode!=0 and 'FAULT_EVENT event is sticky and blocks new requests within two edges' in run.stdout)
        results[name]=dict(expected_gate_pass=passed,exit_code=run.returncode,compile_command=cmd)
    record=dict(schema='opentallas.hbm.su.aggregate_fault_event.v1',
        status='PASS' if all(x['expected_gate_pass'] for x in results.values()) else 'FAIL',
        production_rtl_changed=False,model_added_cycles=0,
        scope='Actual SU-side CP controller receives injected single-edge aggregate executor fault; arithmetic producer separately qualified. Does not simulate full executor memory/publication path.',
        shape=C.SHAPE,injection_ages_after_owned=[0,32,64],registered_fault_bound_edges=2,
        observations=['fault sticky through completion and cleanup','no done after fault','new request permission suppressed within two edges','reset clears quarantine'],
        not_proved=['per-result aligned rsqrt fault metadata, which current interface does not implement','previously accepted memory writes rollback','physical timing or complete executor integration'],
        source_sha256={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files},results=results)
    (a.out/'summary.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record['results'],indent=2))
    return 0 if record['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
