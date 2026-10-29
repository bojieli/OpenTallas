#!/usr/bin/env python3
"""Emit a current unsigned WRQ one-root source/physical interface candidate.
No data/reset logic/cycles or default module change. No routes are launched.
"""
import argparse,json,shutil,hashlib,copy
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('out',type=Path);ap.add_argument('packet',type=Path);ap.add_argument('views',type=Path);a=ap.parse_args()
r=lambda p:json.loads(p.read_text())
w=lambda p,d:p.write_text(json.dumps(d,indent=1)+'\n')
assert not a.out.exists() and a.source.resolve()!=a.out.resolve()
clocks=['clk','clk_cal','clk_l0','clk_l1','clk_l2','clk_l3'];aliases=r(a.packet/'native_wrq_ctlx_source_clock.json')
actual=[q for q in aliases['rows']if q['module']=='ot_hbm_sm_vm_wr_q_t_lanes4'];assert {q['path']for q in actual}=={'smw_NW','smw_NE'}
for q in actual:assert len({q['clock_reset_ports'][n]for n in clocks})==1
shutil.copytree(a.source,a.out);d=r(a.out/'die_plan.json');ce=r(a.out/'clock_entries.json');con=r(a.out/'core_conns.json');ps=r(a.packet/'pins_oneclk.json');newname='cores/ot_hbm_sm_vm_wr_q_t_lanes4__oneclk_142p56x216.json';report={'classification':'CANDIDATE only: unsigned source/pin event, no clocktree/route/timing/adoption','source_plan_sha256':hashlib.sha256((a.source/'die_plan.json').read_bytes()).hexdigest(),'native_source_alias_sha256':aliases['sha256'],'instances':[],'source_cycles_added':0,'clock_roots_before':6,'clock_roots_after':1}
for ty,t in d['partition_types'].items():
 for h in t.get('hard_cores',[]):
  if h['module']!='ot_hbm_sm_vm_wr_q_t_lanes4':continue
  old=r(a.source/h['pins_file']);before={q['name']:q for q in old};after={q['name']:q for q in ps};assert set(before)-set(after)==set(clocks[1:]) and not set(after)-set(before)
  assert all(q==after[n]for n,q in before.items()if n not in clocks)
  report['instances'].append({'type':ty,'inst':h['inst'],'origin_um':h['origin_um'],'orient':h.get('orient','R0'),'track_offset_um':h.get('track_offset_um'),'outline_um':h['outline_um'],'old_clock_pins':[before[n]for n in clocks],'new_clock_pin':after['clk'],'data_control_pins_unchanged':len(after)-1})
  h['pins_file']=newname
  for key in ('lib','lef'):h.pop(key,None)
  h['note']=h.get('note','')+' | CANDIDATE source-exact one-root WRQ; remove five same-sourceclockaliases; all nonclockpins/outline/origin/cyclesunchanged; new SIGNEDviewrequired'
 for ent in ce.get(ty,{}).values():
  if ent.get('module')=='ot_hbm_sm_vm_wr_q_t_lanes4':ent.update(port='clk',merged_clock_ports=[],source='CANDIDATE one native same-source clock pin; exact source alias receipt, fresh localtree required')
 for inst,ports in con.get(ty,{}).items():
  if inst.startswith('u_smw_Q'):
   for n in clocks[1:]:ports.pop(n,None)
assert len(report['instances'])==4
w(a.out/'die_plan.json',d);w(a.out/'clock_entries.json',ce);w(a.out/'core_conns.json',con);w(a.out/newname,ps)
vl=r(a.views);row=next(copy.deepcopy(q)for q in vl['view_list']if q['module']=='ot_hbm_sm_vm_wr_q_t_lanes4');sha=hashlib.sha256((a.out/newname).read_bytes()).hexdigest();row.update(view='ot_hbm_sm_vm_wr_q_t_lanes4@'+sha[:12],pins_file=newname,pins_sha256=sha,pins=len(ps),recipe_keys=['ot_hbm_sm_vm_wr_q_t_lanes4__oneclk_profile']);vl.update(plan=str(a.out),plan_sha256=hashlib.sha256((a.out/'die_plan.json').read_bytes()).hexdigest(),view_list=[row]);w(a.out/'wrq_views.json',vl);w(a.out/'wrq_oneclk_report.json',report);print(json.dumps({'instances':4,'pins':len(ps),'view':row['view'],'plan':str(a.out)}))
