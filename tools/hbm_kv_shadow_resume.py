"""Resume preserved full-shape shadow synthesis remotely with equivalent SDC API."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

IMAGE='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MACRO='physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2'
NICK='hbm_kvwb_shadow_sram_full'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--source-commit',required=True)
    ap.add_argument('--peak-gb',type=float,required=True)
    ap.add_argument('--src',type=Path,required=True)
    a=ap.parse_args()
    global ROOT
    ROOT=a.src.resolve()
    if os.uname().nodename=='ip-172-31-31-69':raise SystemExit('No localhost compute')
    if (a.work/'terminal.json').exists():raise SystemExit('Terminal evidence is immutable')
    base=a.work/'results/asap7'/NICK/'base'
    if not all((base/f).is_file() for f in ['1_2_yosys.v','mem.json','1_2_yosys.sdc']):
        raise SystemExit('Pinned completed synthesis checkpoint required')
    reused={f:sha(base/f) for f in ['1_2_yosys.v','mem.json']}
    paths=sorted(p for prefix in ['rtl/common','rtl/hbm_accel/service',MACRO,'physical/hbm_kvwb_shadow_sram_20261008','tools/w18'] for p in (ROOT/prefix).rglob('*') if p.is_file())
    pins={str(p.relative_to(ROOT)):sha(p) for p in paths}
    rec=dict(schema='opentallas.hbm_accel.dskv_sram_fullhub_physical.v1',source_commit=a.source_commit,
             RTL_source_commit='bc0027ca3',SDC_compat_source_commit='6e4afafe1',reused_synthesis_sha256=reused,
             previous_immutable_failure='ot-epyc2:/srv/opentallas-data/codex/dskv-shadow-full-20261009-eb4/run-r1/terminal.json',
             image=IMAGE,host=os.uname().nodename,scope='PATHFINDING: die outline, pins and boundary clock obligations provisional',
             adoption=False,started_utc=datetime.now(timezone.utc).isoformat(),input_sha256=pins,
             admission_peak_gb=a.peak_gb,clock_period_ps=833,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
             acceptance=dict(SS_setup_ps=15,FF_hold_ps=15,DRC_errors=0),execution_caps=None)
    def container(command):
        return ['docker','run','--rm','--name','ot-dskv-'+a.work.name,'-v',str(ROOT)+':/src:ro',
                '-v',str(a.work)+':/work','-w','/OpenROAD-flow-scripts/flow',IMAGE,'bash','-lc',command]
    route=container('source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1\nmake DESIGN_CONFIG=/src/physical/hbm_kvwb_shadow_sram_20261008/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=24 finish metadata-generate')
    cmd=['/srv/opentallas-scratch/admit.sh',str(a.peak_gb),'--','/usr/bin/time','-v']+route
    rec['route_argv']=cmd;write(a.work/'launch.json',rec)
    (a.work/'status').write_text('WAIT_ADMISSION_THEN_FULL_ROUTE\n')
    with (a.work/'route.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    rec['route_returncode']=r.returncode
    rss=re.search(r'Maximum resident set size \(kbytes\): (\d+)',(a.work/'route.log').read_text())
    rec['docker_client_max_rss_kib']=int(rss[1]) if rss else None
    rec['rss_scope']='Docker client RSS excludes container memory; per-stage ORFS RSS in logs is authoritative'
    rec['reused_synthesis_unchanged']=reused=={f:sha(base/f) for f in reused}
    rec['corner_timing']={}
    if r.returncode==0 and all((base/f).is_file() for f in ['6_final.odb','6_final.sdc','6_final.spef']):
        spec=importlib.util.spec_from_file_location('corner',ROOT/'tools/w18/corner_sta.py')
        C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
        rec['final_sha256']={f:sha(base/f) for f in ['6_final.odb','6_final.sdc','6_final.spef']}
        for corner in ['ss','ff']:
            path=a.work/f'sta_{corner}.tcl'
            text=C.script(corner,f'/work/results/asap7/{NICK}/base',[MACRO])
            text+='\nputs "OT_MACRO_CENSUS_BEGIN"\nforeach inst [[ord::get_db_block] getInsts] {if {[[$inst getMaster] getName] eq "ot_sram_1r1w_128x256_m1_r2c2"} {puts [$inst getName]}}\nputs "OT_MACRO_CENSUS_END"\n'
            path.write_text(text)
            argv=['/srv/opentallas-scratch/admit.sh',str(a.peak_gb),'--']+container(f'/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/sta_{corner}.tcl')
            with (a.work/f'sta_{corner}.log').open('w') as log:q=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT)
            log=(a.work/f'sta_{corner}.log').read_text()
            def field(name):
                m=re.search(r'^'+name+r' (\S+)',log,re.M);return m[1] if m else None
            census=re.search(r'OT_MACRO_CENSUS_BEGIN\n(.*?)OT_MACRO_CENSUS_END',log,re.S)
            ws=field('OT_WS')
            rec['corner_timing'][corner]=dict(returncode=q.returncode,
                check='setup' if corner=='ss' else 'hold',worst_slack_ps=float(ws)*1e12 if ws else None,
                macro_instances=census[1].splitlines() if census else [],
                full_context_qualified=False)
    rec['input_unchanged']=pins=={str(p.relative_to(ROOT)):sha(p) for p in paths}
    rec['finished_utc']=datetime.now(timezone.utc).isoformat()
    rec['verdict']='ROUTE_COMPLETED_PATHFINDING' if r.returncode==0 else 'FAIL_ROUTE'
    if not rec['input_unchanged']:rec['verdict']='FAIL_SOURCE_CHANGED'
    write(a.work/'terminal.json',rec)
    (a.work/'status').write_text(rec['verdict']+'\n')
    print(json.dumps(rec,indent=2))
    raise SystemExit(r.returncode)
if __name__=='__main__':main()
