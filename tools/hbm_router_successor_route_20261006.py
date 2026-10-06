#!/usr/bin/env python3
"""Continue the real successor mapping once; require actual parent allocation."""
import argparse, json, shutil, socket, subprocess, sys
from pathlib import Path
import hbm_router_pipeline_route_20261006 as B
ROOT=Path(__file__).resolve().parents[1]
SUB=Path('results/asap7/carson_router_successor/base')
R=Path('results/physical/hbm_die_abstracts_20261006/compute/router_pipeline_r2')
TOP='ot_hbm_router_topk_successor'
MAKE=['make','DESIGN_CONFIG=/work/config.mk','WORK_HOME=/work','FLOW_VARIANT=base',
      'NUM_CORES=16','GPL_TIMING_DRIVEN=0','-o','/work/'+str(SUB/'1_synth.odb'),
      '-o','/work/'+str(SUB/'1_synth.sdc'),'finish','metadata-generate']

def save(p,r):p.write_text(json.dumps(r,indent=2)+'\n')

def prepare(retained,out):
    if out.exists():raise ValueError('preserve previous roots; new output required')
    r=json.loads((retained/'map.json').read_text())
    assert r['status']=='ACTUAL_NATIVE_MAP_AND_LOCAL_CONTROL_LOADS_PASS'
    gate=json.loads((ROOT/R/'gate-r2/gate.json').read_text());assert gate['passed']
    for p,h in gate['source_sha256'].items():assert B.sha(ROOT/p)==h,p
    receipt=json.loads((retained/'actual_local_controls_and_loads.json').read_text())
    assert all(v==32 for v in receipt['control_DFF_counts'].values())
    assert receipt['rank_DFF_counts']==dict(ge_q=192,valid_q=192)
    assert receipt['mapped_verilog_sha256']==r['mapped_verilog_sha256']
    assert B.sha(retained/'orfs'/SUB/'1_2_yosys.v')==r['mapped_verilog_sha256']
    out.mkdir();work=out/'orfs';work.mkdir()
    # Independent copies: no following ORFS write may mutate mapped evidence.
    for n in ['results','logs','reports','objects']:
        src=retained/'orfs'/n
        if src.exists():shutil.copytree(src,work/n,copy_function=shutil.copy2)
    for n in ['config.mk','constraint.sdc','attribute_preservation.json']:
        shutil.copy2(retained/'orfs'/n,work/n)
    cfg=(work/'config.mk').read_text()
    cfg+='\nexport TNS_END_PERCENT = 100\nexport REPORT_CLOCK_SKEW = 1\n'
    cfg+='export SLEW_MARGIN = 30\nexport HOLD_SLACK_MARGIN = 10\n'
    cfg+='export GPL_TIMING_DRIVEN = 0\nexport PLACE_DENSITY_LB_ADDON = 0.05\n'
    (work/'config.mk').write_text(cfg)
    record=dict(status='PREPARED_RETAINED_MAP_WAIT_ACTUAL_TURING_ALLOCATION',
      source_sha256=gate['source_sha256'],gate_sha256=B.sha(ROOT/R/'gate-r2/gate.json'),
      retained_map_root=str(retained),retained_map_record_sha256=B.sha(retained/'map.json'),
      mapped_control_load_record_sha256=B.sha(retained/'actual_local_controls_and_loads.json'),
      mapped_verilog_sha256=r['mapped_verilog_sha256'],sdc_sha256=r['sdc_sha256'],
      copied_synth_odb_sha256=B.sha(work/SUB/'1_synth.odb'),
      copied_synth_sdc_sha256=B.sha(work/SUB/'1_synth.sdc'),config_sha256=B.sha(work/'config.mk'),
      image=B.IMAGE,make_command=MAKE,declared_ram_gib=96,workers=16,disk_need_gib=64,
      RAM_basis='actual oldDRT31.3GiB times93309/45270=64.5GiB plus31GiB repair/extraction reserve; reservation not cap',
      synthesis_replayed=False,golden_replayed=False,RTL_changed=False,clock_or_uncertainty_relaxed=False,
      frame_binding_required=True,physical_closed=False,parent_qualified=False,adopted=False)
    save(out/'preparation.json',record)

def allocation(path,work,r):
    # Turing supplies this normalization from actual pinned allocation/bindings;
    # Carson never populates producer/receiver/clock fields from generic IO.
    a=json.loads(path.read_text())
    model=json.loads((ROOT/R/'before_rtl.json').read_text());f=model['finite_candidate_frame']
    assert a['owner']=='Turing' and a['macro_master']==TOP
    rtl=next(h for p,h in r['source_sha256'].items() if p.endswith('ot_hbm_router_topk_successor.sv'))
    assert a['leaf_source_sha256']==rtl
    assert a['mapped_verilog_sha256']==r['mapped_verilog_sha256']
    assert a['die_area_um']==[0,0,f['die_side_um'],f['die_side_um']]
    assert a['core_area_um']==f['core_lower_um']+f['core_upper_um']
    assert a['timing_contract_sdc_sha256']==r['sdc_sha256']
    for k in ['actual_parent_instance','producer_port_binding','receiver_port_binding','clock_reset_binding','corridor_reservation']:
        assert a[k],('actual allocation/binding missing',k)
    assert a['allocation_reserved'] is True
    shutil.copy2(path,work.parent/'actual_parent_allocation.json')
    return B.sha(path)

def run(out,alloc,admitted):
    if socket.gethostname()!='ot-epyc1tb':raise ValueError('E1 only; no E2 duplicate')
    if not Path('/srv/opentallas-scratch/admit.sh').is_file():raise ValueError('unchanged remote guard required')
    if (out/'route.json').exists():raise ValueError('immutable retained attempt exists')
    r=json.loads((out/'preparation.json').read_text());work=out/'orfs'
    for p,h in r['source_sha256'].items():assert B.sha(ROOT/p)==h,p
    assert B.sha(work/SUB/'1_2_yosys.v')==r['mapped_verilog_sha256']
    assert B.sha(work/SUB/'1_synth.odb')==r['copied_synth_odb_sha256']
    assert B.sha(work/SUB/'1_synth.sdc')==r['copied_synth_sdc_sha256']
    assert B.sha(work/'constraint.sdc')==r['sdc_sha256']
    assert B.sha(work/'config.mk')==r['config_sha256']
    r['actual_parent_allocation_sha256']=allocation(alloc,work,r)
    if not B.capacity(out,'post_guard' if admitted else 'pre_guard')['fits']:return 75
    if shutil.disk_usage(out).free<64*1024**3:return 75
    if not admitted:return subprocess.call(['/srv/opentallas-scratch/admit.sh','96','--',sys.executable,
      str(Path(__file__).resolve()),'--out',str(out),'--allocation-record',str(alloc),'--admitted'])
    command='python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && cd /OpenROAD-flow-scripts/flow && '+' '.join(MAKE)
    cmd=['docker','run','--name','carson-router-successor-route-r2','--cpus','16','-e','OMP_NUM_THREADS=16',
      '-v',str(ROOT)+':/src:ro','-v',str(work)+':/work',B.IMAGE,'bash','-lc',command]
    r.update(status='RUNNING_ONE_CHANGED_SUCCESSOR_RETAINED_MAP_ROUTE',command=cmd)
    save(out/'route.json',r)
    with (out/'route.log').open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
    r.update(flow_returncode=rc,status='FLOW_FAIL_RETAINED' if rc else 'ROUTE_TERMINAL_NEEDS_REVIEW')
    if not rc:r['corners']=B.corners(out,work)
    r['post_capacity']=B.capacity(out,'terminal');save(out/'route.json',r);return rc

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--retained-map',type=Path);p.add_argument('--prepare',action='store_true')
    p.add_argument('--allocation-record',type=Path);p.add_argument('--admitted',action='store_true');a=p.parse_args()
    if a.prepare:
        if not a.retained_map:p.error('actual retained mapping required')
        prepare(a.retained_map.resolve(),a.out.resolve())
    else:
        if not a.allocation_record:p.error('actual source-bound Turing allocation required; no generic IO fallback')
        sys.exit(run(a.out.resolve(),a.allocation_record.resolve(),a.admitted))
