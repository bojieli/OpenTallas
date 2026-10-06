#!/usr/bin/env python3
"""Route the full P2 element with actual enclosing IO timing and all SRAM corners.

Invoke in a clean pinned owner worktree through unchanged host admit.sh. Existing
objects are retained in --work; this recipe never restarts another pinned job.
Parent SDC is supplied by the enclosing source owner, not guessed here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
RTL=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
     'rtl/hbm_accel/service/ot_hbm_accel_r5a_ecc_pkg.sv',
     'rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo_p2.sv',
     'rtl/hbm_accel/service/ot_hbm_accel_expert_stream_pc_p2.sv',
     'rtl/hbm_accel/service/ot_hbm_accel_expert_fetch_p2.sv']
MACRO='ot_sram_1r1w_512x128_m4_r2c2'
BASE='physical/asap7_memory_macros_v2/'+MACRO

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--exact',type=Path,required=True)
    p.add_argument('--parent-sdc',type=Path,required=True)
    p.add_argument('--allocation',type=Path,required=True,help='existing Turing finite dieplan allocation record')
    p.add_argument('--stack-context',action='store_true',help='route actual defaultOFF stack caller/codec/SM receiver, requiring its own exact gate')
    p.add_argument('--cores',type=int,choices=range(16,25),default=16)
    a=p.parse_args()
    rtl=RTL+(['rtl/hbm_accel/service/ot_hbm_accel_expert_stack_p2.sv'] if a.stack_context else [])
    clock_file='physical/hbm_accel/r5a_stack_p2_clocks.sdc' if a.stack_context else 'physical/hbm_accel/r5a_p2_clocks.sdc'
    top='ot_hbm_accel_expert_stack_p2' if a.stack_context else 'ot_hbm_accel_expert_fetch_p2'
    exact=json.loads(a.exact.read_text())
    if a.stack_context and exact['variant']!='stack_p2':raise SystemExit('actual stack codec/capture gate required')
    if exact['exact']['verdict']!='PASS' or not exact['protection_pass']:
        raise SystemExit('changed-source fullshape exact/protection gate not passed')
    for f in rtl:
        if exact['input_sha256'][f]!=sha(ROOT/f):raise SystemExit('different exact RTL source: '+f)
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True):
        raise SystemExit('physical source worktree must be clean')
    # Refuse synthetic boundary exceptions; async clocks live in the fixed
    # clock file, and the actual falling/rising macro arcs remain timed.
    parent=a.parent_sdc.read_text()
    forbidden=('set_false_path','set_multicycle_path','create_clock','remove_clock_uncertainty')
    if any(x in parent for x in forbidden):raise SystemExit('parent SDC changes fixed timing relations')
    if 'set_input_delay' not in parent or 'set_output_delay' not in parent:
        raise SystemExit('actual enclosing launch/capture IO timing missing')
    work=a.work.resolve();work.mkdir(parents=True,exist_ok=False)
    helpers=['physical/hbm_accel/r5a_p2_physical.py','physical/hbm_accel/r5a_p2_macro_local.tcl',
             clock_file,'physical/common/ot_macro_track_snap.tcl',
             'tools/run_abi3_physical.py','tools/orfs_allcorner_spef.py']
    inputs=rtl+helpers+[BASE+'/'+MACRO+s for s in ('_bb.v','.lef','_ss.lib','_ff.lib','.json')]
    receipt=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                 exact_source_commit=exact['source_commit'],input_sha256={f:sha(ROOT/f) for f in inputs},
                 exact_sha256=sha(a.exact),parent_sdc_sha256=sha(a.parent_sdc),
                 allocation_sha256=sha(a.allocation),cores=a.cores,
                 clk_ps=833.333333333,hclk_ps=1024,SS_setup_ps=60,FF_hold_ps=25,
                 falsepath_IO=False,context_qualification='requires actual enclosing source pins and corner loads')
    cmd=[sys.executable,str(ROOT/'tools/run_abi3_physical.py'),'--view','asap7',
         '--top',top,'--param','ENABLE=1','--clock-port',('stream_clk' if a.stack_context else 'clk'),
         '--clock-period-ns','0.833333333333',
         '--clock-uncertainty-ns','0.060','--clock-uncertainty-hold-ns','0.025',
         '--stages','pnr','--orfs-corner','WC','--hold-corners','WC,BC',
         '--macro-view',MACRO+'='+BASE,'--macro-place-halo','3','3',
         '--die-area','0','0','2000.16','2000.16',
         '--core-area','19.44','19.44','1980.72','1980.72',
         '--sdc-append',clock_file,'--sdc-append',str(a.parent_sdc.resolve()),
         '--step-tcl','POST_MACRO_PLACE=physical/hbm_accel/r5a_p2_macro_local.tcl',
         '--orfs-var','SYNTH_HDL_FRONTEND=slang',
         '--orfs-var','SYNTH_SLANG_ARGS=--unroll-limit 65536','--orfs-var','NUM_CORES='+str(a.cores),
         '--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited',
         '--nickname-tag','r5a_p2','--keep-heavy-artifacts','--keep-workdir',str(work/'flow'),
         '--output',str(work/'physical.json'),'--purpose','signoff_target']
    for f in rtl+[BASE+'/'+MACRO+'_bb.v']:cmd+=['--source',f]
    if not a.stack_context:cmd+=['--param','NPC=32','--param','NSM=8','--param','DEPTH=512']
    receipt['connected_stack_context']=a.stack_context
    receipt['command']=cmd;receipt['load_at_execution']=os.getloadavg()
    (work/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if os.uname().nodename.startswith('ot-epyc2') and os.getloadavg()[0]>=128:
        raise SystemExit('EPYC2 load >=128 at execution; no physical launch')
    with (work/'run.log').open('w') as log:r=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    (work/'exit').write_text(str(r.returncode)+'\n')
    raise SystemExit(r.returncode)

if __name__=='__main__':main()
