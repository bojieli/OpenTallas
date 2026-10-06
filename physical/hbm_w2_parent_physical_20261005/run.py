#!/usr/bin/env python3
import argparse,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output-root',required=True);p.add_argument('--stage',choices=['map','pnr'],default='map');a=p.parse_args()
r=Path(__file__).resolve().parents[2];o=Path(a.output_root);o.mkdir(parents=True,exist_ok=True)
c=[sys.executable,str(r/'tools/run_abi3_physical.py'),'--view','asap7','--top','ot_hbm_w2_protected_parent_context']
for s in json.loads((Path(__file__).parent/'sources.json').read_text()):c+=['--source',s]
for v in ['ENABLE=1','PROTECTED_TRANSACTION_PIPELINE=1','PROTECTED_PARENT_BOUNDARY=1']:c+=['--param',v]
c+=['--clock-port','clk_sm','--clock-period-ns','.8333333333333334','--clock-uncertainty-ns','.060','--clock-uncertainty-hold-ns','.025','--core-input-delay-min-ns','0','--core-input-delay-max-ns','.166666666666667','--output-delay-min-ns','0','--output-delay-max-ns','.166666666666667','--stages','pnr','--orfs-corner','WC','--hold-corners','WC,BC','--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited','--orfs-var','SYNTH_HDL_FRONTEND=slang','--sdc-append',str(Path(__file__).parent/'context.sdc'),'--purpose','signoff_target','--output',str(o/(a.stage+'.json')),'--keep-workdir',str(o/'work'),'--nickname-tag','w2_parent_real']
if a.stage in ['map','pnr']:
 c+=['--die-area','0','0','1814.376','1403.976','--core-area','17.28','25.92','1797.096','1386.72','--routing-layers','M2','M9','--orfs-var','MIN_CLK_ROUTING_LAYER=M8','--orfs-var','PDN_TCL=/src/physical/hbm_w2_parent_physical_20261005/pdn.tcl']
 for h,f in [('POST_PDN','regions.tcl'),('PRE_DETAIL_PLACE','pre_dpl.tcl'),('PRE_CTS','pre_dpl.tcl'),('PRE_GLOBAL_ROUTE','pre_dpl.tcl')]:c+=['--step-tcl',h+'='+str(Path(__file__).parent/f)]
if a.stage=='map':c+=['--pnr-stop-after','floorplan']
(o/(a.stage+'_argv.json')).write_text(json.dumps(c,indent=2)+'\n')
os.environ['OT_ORFS_NUM_CORES']='16';raise SystemExit(subprocess.call(c,cwd=r))
