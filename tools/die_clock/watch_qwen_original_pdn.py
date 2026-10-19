#!/usr/bin/env python3
"""Collect this lane's original-PDN job and fleet final audits; never run timing.

The controller reserves no fleet memory while waiting. PID identity and the
native completion receipt guard dispatch; final audits only read the immutable
generated ODB. Each audit has its own ot-run admission and log.
"""
import argparse,json,shlex,subprocess,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def main(a):
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    def remote(code,*args):
        command=shlex.join(['python3','-c',code,*map(str,args)])
        return subprocess.check_output(['ssh','-o','ConnectTimeout=10',a.host,command],text=True)
    probe='''import json,pathlib,sys
p=pathlib.Path(sys.argv[1]);pid=sys.argv[2]
try:r=json.loads((p/'original_pdn_v1/out/record.json').read_text())
except (OSError,ValueError):r={}
try:c=pathlib.Path('/proc/'+pid+'/cmdline').read_bytes();alive=b'/original_pdn_v1/qwen_clock_pre_pdn.py' in c
except OSError:alive=False
print(json.dumps(dict(alive=alive,power_checks_pass=r.get('actual_contacts_stack_shorts_native_continuity_pass',False),generated_sha=r.get('generated_odb_sha256'),manifest_sha=r.get('manifest_sha256'),gen_source=r.get('gen_source'))))'''
    while True:
        try:state=json.loads(remote(probe,a.lane,a.pid))
        except (subprocess.SubprocessError,ValueError):time.sleep(30);continue
        if not state['alive'] or state['power_checks_pass']:break
        time.sleep(30)
    print('NATIVE_PDN_TERMINAL '+json.dumps(state),flush=True)
    if not state['generated_sha']:
        (out/'combined.json').write_text(json.dumps(dict(native_state=state,physical_checks_pass=False,
            error='native PDN ended before a generated ODB receipt',timing_qualified=False,production_admitted=False),indent=1)+'\n')
        return 1
    def audit(kind):
        if kind=='geometry':
            args=['--tool-source',a.tool_source];tool='qwen_spine_geometry_proof.py'
        else:
            args=['--policy','/phase/original_pdn_v1/die_tie_rows.tcl'];tool='qwen_clock_pg_audit.py'
        native=['openroad','-python','-no_init','-exit','/phase/tools/die_clock/'+tool,
                '--odb','/phase/original_pdn_v1/out/generated_pdn.odb',
                '--manifest','/phase/full_pg/geometry_manifest.json',*args,
                '--out','/phase/original_pdn_v1/final_'+kind+'.json']
        script='source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; '+shlex.join(native)
        command=['docker','run','--rm','--cpus=2','--memory=22g','-v',a.lane+':/phase',
                 'openroad/orfs:asap7lock','bash','-lc',script]
        with (out/(kind+'.log')).open('w') as log:
            return subprocess.call(['/home/ubuntu/bin/ot-run','--mem','24','--threads','2','--dir',a.lane,
                                    '--',*command],stdout=log,stderr=subprocess.STDOUT)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results=dict(zip(('geometry','pg'),executor.map(audit,('geometry','pg'))))
    fetch='''import json,pathlib,sys
p=pathlib.Path(sys.argv[1]);out={}
for k in ('geometry','pg'):
 try:out[k]=json.loads((p/('original_pdn_v1/final_'+k+'.json')).read_text())
 except (OSError,ValueError):out[k]={}
print(json.dumps(out))'''
    receipts=json.loads(remote(fetch,a.lane));g=receipts['geometry'];pg=receipts['pg']
    passed=bool(state['power_checks_pass'] and results=={'geometry':0,'pg':0} and g.get('geometry_pass')
                and g.get('odb_sha256')==pg.get('odb_sha256')==state['generated_sha']
                and g.get('manifest_sha256')==pg.get('manifest_sha256')==state['manifest_sha']
                and pg.get('unconnected_clock_pg_pins')==0 and pg.get('canonical_m8_phase_conflict_pins')==0
                and pg.get('macro_halo_conflict_cells')==0)
    combined=dict(schema='opentallas.qwen.clock_physical_collection.v1',native_state=state,
                  audit_exit_codes=results,physical_checks_pass=passed,
                  geometry_receipt=g,pg_receipt=pg,timing_qualified=False,production_admitted=False)
    payload=json.dumps(combined,indent=1)+'\n';(out/'combined.json').write_text(payload)
    writer='import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.stdin.read())'
    subprocess.run(['ssh',a.host,shlex.join(['python3','-c',writer,a.lane+'/original_pdn_v1/physical_collection.json'])],
                   input=payload,text=True,check=True)
    print('FINAL_PHYSICAL_COLLECTION '+json.dumps(dict(physical_checks_pass=passed,exits=results)),flush=True)
    return 0 if passed else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('host','lane','pid','tool-source','out'):p.add_argument('--'+name,required=True)
    raise SystemExit(main(p.parse_args()))
