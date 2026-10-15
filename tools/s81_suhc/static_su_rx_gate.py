#!/usr/bin/env python3
"""Native 384-score router component: mapped calendar, controller, pin owner, RX.

Run through ot-run for admission. This is not native VM/full-SU/layer release
qualification. External operand rows are declared test stimuli. All on-chip
control storage and arithmetic are actual RTL/mapped macro models.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_suhc'))
import su_gate
NEW=['rtl/dsrom_sys/s81_suhc/hier/'+p for p in (
    'ot_s81_su_calendar_ctl.sv','ot_s81_su_calendar_store.sv','ot_s81_su_moe_sum_static.sv',
    'dsfd_sp_su_static.sv','dsfd_sp_su_static_programmed.sv')]
TB='rtl/dsrom_sys/s81_suhc/test/tb_s81_su_static_rx.sv'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--mutant',type=int,choices=[0,2],default=0)
    ap.add_argument('--drop-response',action='store_true')
    a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    sources=list(dict.fromkeys(su_gate.H.FP['rtl']+su_gate.RTL+su_gate.HIER+NEW+[TB]))
    pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
    obj=out/'obj';cache=obj/'sources.json'
    if not cache.exists() or json.loads(cache.read_text())!={'sources':pins,'mutant':a.mutant}:
        cmd=['verilator','--binary','--timing','-O1','-Wno-fatal','-Wno-WIDTH',
             '--top-module','tb_s81_su_static_rx','-Mdir',str(obj),'-j','8',
             f'-GMUT={a.mutant}',*[str(ROOT/p) for p in sources]]
        with (out/'build.log').open('w') as log:
            r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
        if r.returncode: raise SystemExit(r.returncode)
        if pins!={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}:
            raise SystemExit('source changed during build')
        cache.write_text(json.dumps(dict(sources=pins,mutant=a.mutant),indent=2)+'\n')
    cmd=[str(obj/'Vtb_s81_su_static_rx')]+(['+DROP_RESPONSE'] if a.drop_response else [])
    with (out/'run.log').open('w') as log:
        r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
    receipt=dict(schema='opentallas.s81.static-su-rx-component.v1',qualified=False,
        scope='384 scores /24rows /actual mapped calendar+pin owner+RX arithmetic; externalVM stimulus',
        returncode=r.returncode,mutant=a.mutant,drop_response=a.drop_response,
        source_sha256=pins,stdout_sha256=hashlib.sha256((out/'run.log').read_bytes()).hexdigest())
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print((out/'run.log').read_text())
    raise SystemExit(r.returncode)
if __name__=='__main__':main()
