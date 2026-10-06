#!/usr/bin/env python3
"""One source-pinned native hierarchy map and actual receiver-load check, E1 only."""
import argparse, hashlib, json, os, socket, subprocess, sys
from pathlib import Path
import hbm_router_pipeline_route_20261006 as B
import hbm_router_successor_mapcheck_20261006 as C
ROOT = Path(__file__).resolve().parents[1]
SUB = Path('results/asap7/carson_router_successor/base')
R = Path('results/physical/hbm_die_abstracts_20261006/compute/router_pipeline_r2')
TOP = 'ot_hbm_router_topk_successor'

CAPS = r'''import gzip,json,re,hashlib
from pathlib import Path
p=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM');result={};pins={}
for corner in ('SS','FF'):
 cells={}
 for path in sorted(p.glob('*_RVT_'+corner+'_*.lib*')):
  pins[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
  text=gzip.open(path,'rt').read() if path.suffix=='.gz' else path.read_text()
  assert re.search(r'capacitive_load_unit\s*\(\s*1\s*,\s*ff\s*\)',text)
  for m in re.finditer(r'cell\s*\(\s*(\w+)\s*\)\s*\{(.*?)(?=\n\s*cell\s*\(|\Z)',text,re.S):
   name,body=m.groups();row={}
   for pin,part in re.findall(r'pin\s*\(\s*(\w+)\s*\)\s*\{(.*?)(?=\n\s*pin\s*\(|\Z)',body,re.S):
    direction=re.search(r'direction\s*:\s*(\w+)',part)
    cap=re.search(r'\bcapacitance\s*:\s*([0-9.eE+-]+)',part)
    if direction and direction[1]=='input':
     assert cap,(name,pin);row[pin]=float(cap[1])
   cells[name]=row
 result[corner]=cells
Path('/work/library_input_caps_ff.json').write_text(json.dumps(result)+'\n')
Path('/work/library_sha256.json').write_text(json.dumps(pins,indent=2)+'\n')
'''

def save(p, r): p.write_text(json.dumps(r, indent=2)+'\n')

def docker(work, command, name=None):
    args = ['docker', 'run', '--cpus', '16' if name else '1']
    args += ['--name', name] if name else ['--rm']
    return args + ['-e', 'OMP_NUM_THREADS=16', '-v', str(ROOT)+':/src:ro',
                   '-v', str(work)+':/work', B.IMAGE, 'bash', '-lc', command]

def main():
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True)
    a.add_argument('--admitted',action='store_true');q=a.parse_args()
    if not Path('/srv/opentallas-scratch/admit.sh').is_file():a.error('unchanged remote guard required')
    if socket.gethostname()!='ot-epyc1tb':a.error('E1 only; preserve E2 progressing jobs')
    out=q.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'map.json').exists() or (out/'orfs').exists():a.error('retained attempt exists; no replay')
    if not B.capacity(out,'post_guard' if q.admitted else 'pre_guard')['fits']:return 75
    if not q.admitted:
        return subprocess.call(['/srv/opentallas-scratch/admit.sh','32','--',sys.executable,
                                str(Path(__file__).resolve()),'--out',str(out),'--admitted'])
    gate=json.loads((ROOT/R/'gate-r2/gate.json').read_text());assert gate['passed']
    for p,h in gate['source_sha256'].items():assert B.sha(ROOT/p)==h,p
    assert B.sha(ROOT/R/'before_rtl.json')==gate['model_sha256']
    model=json.loads((ROOT/R/'before_rtl.json').read_text());frame=model['finite_candidate_frame']
    work=out/'orfs';work.mkdir();side=frame['die_side_um']
    lo=frame['core_lower_um'];hi=frame['core_upper_um']
    # Same actual retained finite min/maxIO/load/reset/833-60-25, top rename only.
    src=ROOT/'physical/hbm_die_abstracts_20261006/compute/router_pipeline_r1/constraint.sdc'
    sdc=src.read_text();assert sdc.count('current_design ot_hbm_router_topk_pipeline')==1
    (work/'constraint.sdc').write_text(sdc.replace('current_design ot_hbm_router_topk_pipeline','current_design '+TOP))
    files=[p for p in gate['source_sha256'] if not p.endswith('tb_router_successor.sv')]
    config=['export DESIGN_NICKNAME = carson_router_successor','export DESIGN_NAME = '+TOP,
     'export PLATFORM = asap7','export VERILOG_FILES = '+' '.join('/src/'+p for p in files),
     'export VERILOG_TOP_PARAMS = ENABLE 1','export VERILOG_DEFINES = -DSYNTHESIS',
     'export SDC_FILE = /work/constraint.sdc','export DIE_AREA = 0 0 '+str(side)+' '+str(side),
     'export CORE_AREA = '+' '.join(map(str,lo+hi)),'export PLACE_DENSITY = 0.575',
     'export SYNTH_REPEATABLE_BUILD = 1','export SYNTH_HIERARCHICAL = 1',
     'export SYNTH_KEEP_MODULES = ot_hbm_router_lane_local','export SYNTH_MEMORY_MAX_BITS = 65536',
     'export LEC_CHECK = 0','export CORNER = WC','export CORNERS = WC BC',
     'export WC_LIB_FILES = $(WC_NLDM_LIB_FILES)','export BC_LIB_FILES = $(BC_NLDM_LIB_FILES)',
     'export ADDER_MAP_FILE =','export ASAP7_USE_VT = RVT']
    (work/'config.mk').write_text('\n'.join(config)+'\n')
    (work/'preserve_attributes.py').write_text(B.BOOTSTRAP)
    r=dict(status='RUNNING_ONE_NATIVE_SUCCESSOR_MAP',source_sha256=gate['source_sha256'],
      gate_sha256=B.sha(ROOT/R/'gate-r2/gate.json'),model_sha256=gate['model_sha256'],
      sdc_sha256=B.sha(work/'constraint.sdc'),config_sha256=B.sha(work/'config.mk'),image=B.IMAGE,
      declared_ram_gib=32,workers=16,ram_basis='retained9GiB flowpeak times99238/45270=19.73GiB plus12GiB reserve; no address-space cap',
      native_flags=dict(SYNTH_HIERARCHICAL=1,SYNTH_KEEP_MODULES='ot_hbm_router_lane_local'),
      physical_closed=False,parent_qualified=False,place_or_route_launched=False,
      frame_allocation='modeled finite frame for synthesis context only; actual Turing parent allocation/receiver pending')
    command='python3 /work/preserve_attributes.py && cd /OpenROAD-flow-scripts/flow && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 synth'
    cmd=docker(work,command,'carson-router-successor-map-r2');r['command']=cmd;save(out/'map.json',r)
    with (out/'native_map.log').open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
    r['native_map_returncode']=rc
    if rc:
        r['status']='NATIVE_MAP_FAIL_RETAINED';save(out/'map.json',r);return rc
    mapped=work/SUB/'1_2_yosys.v';r['mapped_verilog_sha256']=B.sha(mapped)
    # Physical-cell flatten ONLY in analysis copy, with no optimisation pass.
    ys='read_verilog /work/'+str(mapped.relative_to(work))+'\nhierarchy -top '+TOP+'\nsetattr -mod -unset keep_hierarchy\nsetattr -unset keep_hierarchy\nflatten\nwrite_json /work/mapped.json\n'
    (work/'analysis_flatten.ys').write_text(ys);(work/'extract_caps.py').write_text(CAPS)
    command='source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -T -s /work/analysis_flatten.ys && python3 /work/extract_caps.py'
    with (out/'mapped_analysis.log').open('w') as f:rc=subprocess.call(docker(work,command),stdout=f,stderr=subprocess.STDOUT)
    r['analysis_returncode']=rc
    if not rc:
        try:
            receipt=C.check(work/'mapped.json',work/'library_input_caps_ff.json',mapped)
            save(out/'actual_local_controls_and_loads.json',receipt)
            r['status']='ACTUAL_NATIVE_MAP_AND_LOCAL_CONTROL_LOADS_PASS'
        except Exception as e:
            r.update(status='ACTUAL_MAPPED_RETENTION_LOAD_FAIL_RETAINED',failure=repr(e));rc=1
    else:r['status']='MAPPED_ANALYSIS_FAIL_RETAINED'
    r['post_capacity']=B.capacity(out,'terminal');save(out/'map.json',r);return rc

if __name__=='__main__':sys.exit(main())
