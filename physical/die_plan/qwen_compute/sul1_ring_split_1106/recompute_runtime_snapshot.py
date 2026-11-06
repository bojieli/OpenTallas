from pathlib import Path
import sys,json,copy
r=Path(__file__).resolve().parent;sys.path[:0]=[str(r),str(r/'tools/die_plan')]
import schema,reset_tree,landing_collector_refreshed as LC
por=r/'physical/die_plan/qwen_compute/plan_of_record';path=por/'plan_sul1_geometry.json';p=json.load(open(path));side=json.load(open(r/'ev4/sidecar_base.json'));reports={}
for tn in ['slw_su_l1__clcc9d0155','slw_su_l1__cla2a78701']:
 print('SOLVE',tn,flush=True);t=p['partition_types'][tn];tree=reset_tree.for_type(schema.Plan(p,str(path)),tn);points={}
 for h in t['hard_cores']:
  if not h.get('param_wrap'):continue
  tab=json.load(open(por/h['pins_file']));points[h['inst'][3:]]=[[h['origin_um'][0]+h['track_offset_um'][0]+pin['x'],h['origin_um'][1]+h['track_offset_um'][1]+pin['y']] for name in ['ready','fault'] for pin in tab['pins'] if pin['name']==name]
 reports[tn]=LC.reattach_sources(side['collector']['types'][tn],tree,status_points=points);t['clock']['landing_contract']['collector_tree']=tree;print('DONE',tn,json.dumps(reports[tn]),flush=True)
(por/'plan_sul1_final_candidate.json').write_text(json.dumps(p,separators=(', ',': '))+'\n');(r/'ev4/sidecar_final.json').write_text(json.dumps(side,indent=1)+'\n');(r/'ev4/collector_attachments.json').write_text(json.dumps(reports,indent=1)+'\n')
