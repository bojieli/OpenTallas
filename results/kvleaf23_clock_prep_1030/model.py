"""One fixed-master native NLDM load-bin coupon; NO native layout/ABI qualification."""
import sys,json,pickle,hashlib,statistics,math
from pathlib import Path
P=Path('/srv/opentallas-scratch2/claude/codex-kvleaf-clock-0336');D=P/'clock_candidate';O=D/'model.json'
if O.exists():raise SystemExit('Existing model result: do not repeat coupon')
look=json.loads((D/'LOOK.json').read_text());assert look['image_sha256']==hashlib.sha256((D/'geometry.png').read_bytes()).hexdigest() and look['personally_viewed']
S=P/'kernel';sys.path[:0]=[str(S/'results/core_lat_r8_1026')]
import l0r_r8_uf3 as A
L=A.U.load_libs(P/'lib');fit=json.loads((P/'uf_phys3_v1.json').read_text());graphs=pickle.loads((D/'graphs.pkl').read_bytes());records=[]
for typ,plans in graphs:
 rows=[]
 for i,plan in enumerate(plans):
  val=A.calibrated_summary(plan,L,fit['PMAX'],fit['PMIN']);depth={'root':1};todo=['root']
  while todo:
   p=todo.pop(0)
   for c in plan.kids.get(p,[]):depth[c]=depth[p]+1;todo.append(c)
  lengths=[e[2] for n in plan.nets.values() for e in n['edges']]
  rows.append({'root_index':i,'nodes':len(plan.nodes),'soft_ff':sum(len(n['sinks']) for n in plan.nodes.values() if n['kind']=='leaf'),'hard_terminals':sum(n['kind']=='macro' for n in plan.nodes.values()),'stages_min':min(depth[n] for n in plan.nodes if n not in plan.kids),'stages_max':max(depth.values()),'largest_axis_segment_um':max(lengths),'corners':val})
 records.append({'type':typ,'roots':rows,'worst_within_root_window_ps':{c:max(v['corners'][c]['window'] for v in rows) for c in ('TT','FF')},'worst_input_slew_ps':{c:max(v['corners'][c]['leaf_slew_in_max'] for v in rows) for c in ('TT','FF')},'worst_output_slew_ps':{c:max(v['corners'][c]['leaf_out_slew_max'] for v in rows) for c in ('TT','FF')},'root_relative_mean_span_ps':{c:[min(v['corners'][c]['mean'] for v in rows),max(v['corners'][c]['mean'] for v in rows)] for c in ('TT','FF')}})
result={'status':'PROPOSED_LOAD_BIN_MODEL_ONLY','kernel':'unchanged uf_phys3 v1 GRT PMAX/PMIN with native TT/FF NLDM; TT rise and FF min(rise,fall)','proposed_masters':{'root':'BUFx24_ASAP7_75t_R','branches_repeaters':'BUFx12f_ASAP7_75t_R','terminal_drivers':'BUFx8_ASAP7_75t_R'},'no_sizing_fitting_or_threshold_changes':True,'variants':records,'limits':['FF counts/cell populations/caps are measured; FF XY and grouping are proposed free-area load bins, not native placement.','Actual clock input phases/slews between 16 roots unknown; root-relative mean span is not whole-parent skew.','Child endpoint input contract proposed BUF24 Cin; child internal timing excluded. SRAM pin/cap is native, parent placement proposed.','Point-to-point branch paths are body-halo avoiding visibility routes; common physical wire sharing is not modeled, so parallel wire charge can overestimate GRT Steiner charge.','No native buffer-body/row/PG legalization; hard terminal stub enters explicit proposed pin opening not qualified by real child views.','The native594/plan597 ABI remains held; this coupon cannot qualify physical builds or full 833ps behavior.']}
O.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps([{'type':v['type'],'window':v['worst_within_root_window_ps'],'slew_in':v['worst_input_slew_ps'],'slew_out':v['worst_output_slew_ps'],'mean_spans':v['root_relative_mean_span_ps']} for v in records],indent=2))
