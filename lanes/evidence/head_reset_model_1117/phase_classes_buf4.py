from pathlib import Path
import json,math,collections
L=Path('/srv/opentallas-scratch2/claude/head-die-r');O=L/'reset_feasibility_r4_1117';R=json.load((O/'feasibility.json').open())
# Fresh 26-cell chain, 1 fF tail, ideal wires: min FF among slew0..300; max TT bounded at30ps.
C=json.load((L/'control_hold_coupon/bufchar_r2/result.json').open())['rows']
def samples(corner,slew,field):
 return {r['n']:r[field] for r in C if r['cell']=='BUFx4_ASAP7_75t_R' and r['pitch_um']==1.35 and r['corner']==corner and r['input_slew_ps']==slew}
a=samples('FF',10,'min_ps');b=samples('TT',100,'max_ps');ff_step=(a[100]-a[26])/74;ff_base=a[26]-26*ff_step;tt_step=(b[100]-b[26])/74;tt_base=b[26]-26*tt_step
area=.10206;hold_margin=10.;wire_tt=20.
by=collections.defaultdict(list)
for r in R['rows']:by[(r['dst_type'],r['dst'])].append(r)
inst=[]
for (tn,dst),rows in sorted(by.items()):
 need=max(0.,max(-x['ff_hold'] for x in rows));budget=min(x['tt_setup']+42 for x in rows)
 lo=0 if need==0 else max(26,math.ceil((need+hold_margin-ff_base)/ff_step));hi=min(100,math.floor((budget-wire_tt-tt_base)/tt_step))
 if need==0 and budget>=0:hi=max(0,hi)
 if 0<hi<26:hi=0
 inst.append(dict(type=tn,part=dst,pins=[r['dst_cell'] for r in rows],need_ff_ps=need,budget_tt_ps=budget,n_min=lo,n_max=hi,status='PROVISIONAL_BUF4_COUNT_INTERVAL' if hi>=lo else 'NO_CHARACTERIZED_COMMON_COUNT'))
classes=[];fails=[]
for tn in sorted({x['type'] for x in inst}):
 pending=[x for x in inst if x['type']==tn and x['n_max']>=x['n_min']];fails.extend(x for x in inst if x['type']==tn and x['n_max']<x['n_min'])
 while pending:
  n=min(x['n_max'] for x in pending);cover=[x for x in pending if x['n_min']<=n<=x['n_max']];pending=[x for x in pending if x not in cover]
  classes.append(dict(type=tn,delay_cells_per_pin=n,pins_per_instance=2,instances=[x['part'] for x in cover],instance_count=len(cover),added_cells_per_instance=2*n,added_area_um2_per_instance=2*n*area,added_ff=0,added_cycles=0,ff_gain_cell_only_ps=0 if n==0 else n*ff_step+ff_base,tt_cost_cell_only_ps=0 if n==0 else n*tt_step+tt_base))
res=dict(schema='opentallas.head_reset_phase_classes.v1',status='PROVISIONAL_MODEL_NOT_RELEASED',limits='Fresh BUFx4 chain interpolation onlyN26..100 uses1.35umM2piRC, inputTTslew<=100ps/FFslew>=10ps and actualmeasuredDFFload. Other nodes need ownload/slewvalidation.20ps extra wire reserve is a priced modeling allowance, not measured wire guarantee. Receiver-type/pin count intersection enforced; empty global intersection requires explicit phase-class clones. Old NF15c roots only; reprice fresh NF15e clock before adoption. No plan/RTL/view changed.',characterization=dict(ff_step_ps=ff_step,ff_base_ps=ff_base,tt_step_ps=tt_step,tt_base_ps=tt_base,area_um2=area,ff_hold_target_ps=hold_margin,tt_wire_reserve_ps=wire_tt),summary=dict(receiver_instances=len(inst),valid_instances=sum(x['n_max']>=x['n_min'] for x in inst),failed_instances=len(fails),phase_view_classes=len(classes),phase_classes_by_type=dict(collections.Counter(x['type'] for x in classes)),replicated_added_cells=sum(x['added_cells_per_instance']*x['instance_count'] for x in classes),replicated_added_area_um2=sum(x['added_area_um2_per_instance']*x['instance_count'] for x in classes)),classes=classes,failed=fails,instance_intervals=inst)
(O/'phase_classes_buf4_provisional.json').write_text(json.dumps(res,indent=1)+'\n');print(json.dumps(res['summary']));print('TILE_CLASSES',json.dumps([x for x in classes if x['type']=='hd_tile']));print('FAIL_TYPES',dict(collections.Counter(x['type'] for x in fails)))
