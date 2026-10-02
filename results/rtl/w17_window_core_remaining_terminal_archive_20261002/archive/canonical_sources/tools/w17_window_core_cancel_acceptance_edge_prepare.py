#!/usr/bin/env python3
"""Added bench-only prohibited acceptance control; no compiler or simulation."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OLD='rtl/test/w17_window_core_cancel_join_r8/tb.sv'
NEW='rtl/test/w17_window_core_cancel_join_acceptance_edge/tb.sv'
MODEL='results/uarch/w17_window_core_cancel_acceptance_edge_20261002/source_model.json'
ANCHOR=' if(core.g_cancel.u_impl.qe_go_e && core.g_cancel.u_impl.qe_ready_e) begin\n'
INSERT='  if((cut=="ISSUE" || cut=="GO") && (recover || fault_pulse))\n   $fatal(1,"registered go cut accepted QE");\n'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def expected():
 old=(ROOT/OLD).read_text()
 if old.count(ANCHOR)!=1:raise ValueError('physical posedge acceptance observer not unique')
 return old.replace(ANCHOR,ANCHOR+INSERT)
def prepare():
 target=ROOT/NEW;target.parent.mkdir(parents=True,exist_ok=False);target.write_text(expected())
 oldmodel=ROOT/'results/uarch/w17_window_core_cancel_guard_feedback_repair_20261002/model.json'
 m=json.loads(oldmodel.read_text());m['status']='PREPARED_ACCEPTANCE_EDGE_UNCOMPILED';m['bench_path']=NEW;m['bench_sha256']=sha(target);m['generator_sha256']=sha(Path(__file__))
 m['acceptance_edge']={'old_bench':OLD,'old_bench_sha256':sha(ROOT/OLD),'anchor':ANCHOR,'insert':INSERT,'new_bench':NEW,'only_insertion':True,'hardware_changes':False,'old_assertions_preserved':True,'old_binary_reuse':False,'physical_QE_marker':'registered go cut accepted QE'}
 path=ROOT/MODEL;path.parent.mkdir(parents=True,exist_ok=False);path.write_text(json.dumps(m,indent=2)+'\n')
if __name__=='__main__':prepare()
