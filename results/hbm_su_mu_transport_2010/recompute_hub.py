import json,sys,math
from pathlib import Path
root=Path('/srv/opentallas-scratch2/claude/wt/path-hbm-r13-1026')
sys.path[:0]=[str(root/'tools/throughput'),str(root/'tools')]
import accepted_cost as A
p=Path('/srv/opentallas-scratch2/claude/path-hbm-r13-1026/price')
out={}
for wl,model in A.DESIGNS['r25gq']['workloads'].items():
 run,counts=A.hbm_schedule(model)
 base=run(); expected={'ds_ar':576702.4,'qwen_ar':1269120.1}[wl]
 if abs(base-expected)>0.11:raise RuntimeError(('incomplete model source',wl,base,expected))
 for tag in ['F','S2']:
  lane=json.load(open(p/(tag+'_lane.json'))); cc=json.load(open(p/(tag+'_cc.json')))['ops']
  terms={mode:[] for mode in ['lower','mid_sm_serial','upper']}
  for opname in counts:
   r=next((r for r in lane['op_deltas'] if A.op_match(opname,r['op'])),None)
   if not r:continue
   c=cc[r['op']]
   values={'lower':0 if r['parallel'] else r['delta_cycles']+c['lower'],
           'mid_sm_serial':r['delta_cycles']+c['lower'],
           'upper':r['delta_cycles']+c['upper']}
   for mode,cycles in values.items():
    if cycles:terms[mode].append((opname,None,float(cycles)))
  entry={'baseline_cycles':base,'scope':'hub incremental latency relative to t_banks; bank k4 service and per-link serialization bandwidth unqualified'}
  for mode,extra in terms.items():
   cycles=run(extra=tuple(extra));entry[mode]={'cycles':round(cycles,1),'tok_s':round(1.2e9/cycles,2),'loss_pct':round((1-base/cycles)*100,3)}
  out.setdefault(tag,{})[wl]=entry
Path('/srv/opentallas-scratch2/claude/codex-hbm-2001/mu_r13/price_recomputed.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
