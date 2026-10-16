#!/usr/bin/env python3
"""Actual per-pin routed TT/FF ETM joins with a declared optimistic L1 wire model."""
import argparse,json,re,subprocess,sys,hashlib,tempfile,collections,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--constant-proof',type=Path);p.add_argument('--frozen-plan',type=Path);a=p.parse_args();R=Path(__file__).resolve().parents[3];O=a.out;sys.path.insert(0,str(R/'tools/hier_contract'));import pinreg_audit as A
j=json.loads((O/'connected_geometry.json').read_text());layout=j['results']['Q_cooptimized_capsules']['placement'];
if a.frozen_plan:layout=json.loads(a.frozen_plan.read_text())['results']['Q_cooptimized_capsules']['placement']
graph=json.loads((O/'cluster_graph.json').read_text());top=next(v for v in graph['modules'].values()if v.get('attributes',{}).get('top') in [1,'1','00000000000000000000000000000001']);cells=top['cells'];pins={};metrics={};provenance={}
for master,v in j['leaf_views'].items():
 base=v['path'].rsplit('/',1)[0];show=lambda suffix:subprocess.check_output(['git','show',v['record']+':'+base+'/'+suffix],cwd=R)
 insraw=show('insertion.json');ins=json.loads(insraw);metrics[master]={};provenance[master]={'record':v['record'],'insertion_sha256':hashlib.sha256(insraw).hexdigest()}
 for corner in ['tt','ff']:
  raw=show(master+'_'+corner+'.lib')
  with tempfile.TemporaryDirectory()as td:
   lp=Path(td)/'cell.lib';lp.write_bytes(raw);lib=A.parse_lib(lp)
  refs=A.clock_refs(lib,ins,corner);metrics[master][corner]=A.pin_metrics(lib,refs);provenance[master][corner]={'lib_sha256':hashlib.sha256(raw).hexdigest(),'clock_refs':refs}
 raw=show(master+'.lef');assert hashlib.sha256(raw).hexdigest()==v['sha256'];pins[master]={}
 for m in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',raw.decode(),re.M|re.S):
  shapes=[]
  for b in re.finditer(r'\bRECT\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)',m[2]):
   x0,y0,x1,y1=map(float,b.groups());shapes.append(((x0+x1)/2,(y0+y1)/2))
  pins[master][m[1]]=shapes
D=collections.defaultdict(list);S=collections.defaultdict(list)
for n,c in cells.items():
 for port,bits in c['connections'].items():
  if port in ['ck','clk','arst_n','rst']:continue
  for i,bit in enumerate(bits):
   if isinstance(bit,int):(D if c['port_directions'][port]=='output'else S)[bit].append((n,port if len(bits)==1 else f'{port}[{i}]'))
def coords(ep):
 n,pin=ep;b=layout[n];return[(b['x']+x,b['y']+y)for x,y in pins[cells[n]['type']][pin]]
proved_constants={};constant_identity={}
if a.constant_proof:
 proof=json.loads(a.constant_proof.read_text());assert proof['status']=='ACTUAL_ODB_AND_LIBERTY_CONSTANT_DRIVER_PROOF'
 for item in proof['cells']:
  assert item['record'].startswith(j['leaf_views'][item['cell']]['record'])
  proved_constants[item['cell']]={r['port']for r in item['rows']if r['constant_zero_proved']}
  constant_identity[item['cell']]={'record':item['record'],'odb_sha256':item['odb_sha256'],'ports':len(proved_constants[item['cell']])}
rows=[];missing=[];constant_joins=[];groups=collections.defaultdict(lambda:{'bits':0,'fail90':0,'fail150':0,'ff_no_wire_reserve_fail':0,'min_slack90_ps':1e9,'min_slack150_ps':1e9,'max_distance_um':0,'minimum_pair_reach150_um':1e9})
for bit,targets in S.items():
 if bit not in D:continue
 assert len(D[bit])==1
 source=D[bit][0];sm=cells[source[0]]['type'];at=metrics[sm]['tt'].get(source[1]);af=metrics[sm]['ff'].get(source[1])
 for target in targets:
  tm=cells[target[0]]['type'];bt=metrics[tm]['tt'].get(target[1]);bf=metrics[tm]['ff'].get(target[1])
  if not at or not bt or at['out']is None or bt['inp']is None:
   if source[1]in proved_constants.get(sm,set()):constant_joins.append({'source':source,'target':target});continue
   missing.append({'source':source,'target':target,'source_arc':at,'target_arc':bt});continue
  distance=min(abs(x-u)+abs(y-v)for x,y in coords(source)for u,v in coords(target));launch,capture=at['out'],bt['inp'];slack90=833.333-60-90-launch-capture-.76*distance;slack150=slack90-60;reach150=(833.333-60-150-launch-capture)/.76
  sr=max(provenance[sm]['tt']['clock_refs'][ck]['rise']for ck in at['clk']);tr=max(provenance[tm]['tt']['clock_refs'][ck]['rise']for ck in bt['clk']);skew=150 if max(sr,tr)>300 else 90
  selected=slack150 if skew==150 else slack90
  ff=af['lmin']-bf['hold']-100 if af and bf and af['lmin']is not None and bf['hold']is not None else None
  row={'source':source,'target':target,'source_master':sm,'target_master':tm,'distance_um':distance,'O_minus_R_ps':launch,'S_plus_R_ps':capture,'source_clocks':at['clk'],'target_clocks':bt['clk'],'pair_reach150_um':reach150,'source_R_ps':sr,'target_R_ps':tr,'selected_skew_ps':skew,'selected_setup_ps':selected,'child_boundary_defect':launch>220 or capture>190,'setup90_ps':slack90,'setup150_ps':slack150,'ff_no_wire_reserve_ps':ff};rows.append(row)
  key=source[0]+'.'+source[1].split('[')[0]+' -> '+target[0]+'.'+target[1].split('[')[0];g=groups[key];g['bits']+=1;g['fail90']+=slack90<0;g['fail150']+=slack150<0;g['ff_no_wire_reserve_fail']+=ff is not None and ff<0;g['min_slack90_ps']=min(g['min_slack90_ps'],slack90);g['min_slack150_ps']=min(g['min_slack150_ps'],slack150);g['max_distance_um']=max(g['max_distance_um'],distance);g['minimum_pair_reach150_um']=min(g['minimum_pair_reach150_um'],reach150)
# Necessary anchor feasibility: even freely translating the existing source
# master cannot satisfy a fanout if its transformed L1 strips do not intersect.
anchor_groups={}
for source_node in ['shell.ctl','mix.control','mix.relay']:
 for port_group in ['ALL','iv','phase','fr','fa','copy']:
  selected=[r for r in rows if r['source'][0]==source_node and(port_group=='ALL'or r['source'][1].split('[')[0]==port_group)]
  if not selected:continue
  bounds={'x+y':[-1e99,1e99],'x-y':[-1e99,1e99]};witness={}
  for r in selected:
   sp=pins[r['source_master']][r['source'][1]];tp=coords(r['target']);centers=[(x-u,y-v)for x,y in tp for u,v in sp];reach=(833.333-60-r['selected_skew_ps']-r['O_minus_R_ps']-r['S_plus_R_ps'])/.76
   for axis,vals in [('x+y',[x+y for x,y in centers]),('x-y',[x-y for x,y in centers])]:
    lo,hi=min(vals)-reach,max(vals)+reach
    if lo>bounds[axis][0]:bounds[axis][0]=lo;witness[axis+'_lower']={'source':r['source'],'target':r['target'],'reach_um':reach}
    if hi<bounds[axis][1]:bounds[axis][1]=hi;witness[axis+'_upper']={'source':r['source'],'target':r['target'],'reach_um':reach}
  anchor_groups[source_node+'.'+port_group]={'fanout_bit_joins':len(selected),'necessary_anchor_strips_um':bounds,'impossible_even_without_obstacles':any(lo>hi for lo,hi in bounds.values()),'conflict_witness':witness,'scope':'Necessary L1-strip enclosure over all actual pin shapes; failure proves no translation of this existing source master can serve these fixed sinks under actual ETM pair budgets. It does not price/implement new pipeline or replicated logic.'}
(O/('anchor_constraints_frozen.json'if a.frozen_plan else'anchor_constraints.json')).write_text(json.dumps(anchor_groups,indent=1)+'\n')
(O/'perpin_native_metrics.json').write_text(json.dumps({'metrics':metrics,'view_provenance':provenance},indent=1)+'\n')
report={'status':'ACTUAL_ETM_OPTIMISTIC_WIRE_SCREEN_ONLY','top':'own-column-valid candidate'if 'localized'in next(n for n,v in graph['modules'].items()if v is top)else'baseline193cluster','geometry':'frozen baseline placement with current source graph'if a.frozen_plan else'Q_cooptimized_capsules','actual_interchild_bit_joins':len(rows)+len(missing)+len(constant_joins),'constant_join_count':len(constant_joins),'mapped_constant_identity':constant_identity,'selected_actual_R_rule_fail_bits':sum(r['selected_setup_ps']<0 for r in rows),'selected_min_setup_ps':min(r['selected_setup_ps']for r in rows),'selected_150ps_bits':sum(r['selected_skew_ps']==150 for r in rows),'max_actual_R_ps':max(max(r['source_R_ps'],r['target_R_ps'])for r in rows),'child_boundary_defect_bits':sum(r['child_boundary_defect']for r in rows),'mapped_joins':len(rows),'missing_arcs':missing,'missing_arc_count':len(missing),'tt_setup_fail90_bits':sum(r['setup90_ps']<0 for r in rows),'tt_setup_fail150_bits':sum(r['setup150_ps']<0 for r in rows),'ff_no_wire_reserve_fail_bits':sum(r['ff_no_wire_reserve_ps']is not None and r['ff_no_wire_reserve_ps']<0 for r in rows),'min_tt_setup90_ps':min(r['setup90_ps']for r in rows),'min_tt_setup150_ps':min(r['setup150_ps']for r in rows),'min_ff_no_wire_reserve_ps':min(r['ff_no_wire_reserve_ps']for r in rows if r['ff_no_wire_reserve_ps']is not None),'rules':{'period_ps':833.333,'setup_uncertainty_ps':60,'skew_cases_ps':[90,150],'actual_R_skew_rule':'90ps normal;150ps whenever either actual R exceeds300ps unless explicit shared-level clock proof exists; no such exception applied','wire_ps_per_um':.76,'hold_reserve_ps':100,'hold_wire_credit_ps':0,'ETM_table_convention':'same first tablepoint as pinreg_audit/native leaf policy; no external load/slew sweep'},'view_provenance':provenance,'port_groups':[{'port_pair':key,**v}for key,v in sorted(groups.items(),key=lambda item:(-item[1]['fail150'],item[1]['min_slack150_ps']))],'worst_setup150':sorted(rows,key=lambda r:r['setup150_ps'])[:100],'worst_ff_no_wire':sorted((r for r in rows if r['ff_no_wire_reserve_ps']is not None),key=lambda r:r['ff_no_wire_reserve_ps'])[:30],'scope':['Actual source graph/actual routed child ETM per-bit arcs and measured clock references. Not extracted parent STA.','Wire is optimistic minimum terminal-center L1 at.76ps/um; obstacles, PG, clock delivery, slew/load, fill/GRT remain OPEN.','500um is a necessary reach screen only; actual source/target ETM pair can have smaller reach. Missing arcs fail closed.']}
(O/('perbit_timing_frozen.json'if a.frozen_plan else'perbit_timing.json')).write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:report[k]for k in ['mapped_joins','constant_join_count','missing_arc_count','selected_actual_R_rule_fail_bits','selected_min_setup_ps','selected_150ps_bits','max_actual_R_ps','child_boundary_defect_bits','tt_setup_fail90_bits','tt_setup_fail150_bits','ff_no_wire_reserve_fail_bits','min_tt_setup90_ps','min_tt_setup150_ps','min_ff_no_wire_reserve_ps']},indent=1))
