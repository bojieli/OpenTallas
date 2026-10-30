import odb,json,re
from pathlib import Path
B=Path('/work');out=[]
for t in ['sle_su_c','slw_su_c__cl92142dac','slw_su_c__cl19bb38ef']:
 db=odb.dbDatabase.create();p=B/'gen_red_keep'/t/t/'run/results/asap7'/('dp_'+t)/'base/1_synth.odb';odb.read_db(db,str(p));block=db.getChip().getBlock();du=block.getDbUnitsPerMicron();rows={'child':dict(std=0,macros=0,area_um2=0.0,seq=0),'parent':dict(std=0,macros=0,area_um2=0.0,seq=0)}
 def child(i):return i.getName().startswith('u_bound.u_u_red.') or i.getName().startswith('u_bound.u_u_red/')
 for i in block.getInsts():
  m=i.getMaster();r=rows['child' if child(i) else 'parent'];r['macros' if m.isBlock() else 'std']+=1
  if not m.isBlock():r['area_um2']+=m.getWidth()*m.getHeight()/du**2;r['seq']+=int(bool(re.search('DFF|SDF|DHL|DLL|LQN',m.getName())))
 cross=0;examples=[]
 for n in block.getNets():
  ins=[];outs=[]
  for it in n.getITerms():(ins if child(it.getInst()) else outs).append(it)
  if ins and (outs or n.getBTerms()):
   cross+=1
   if len(examples)<6:examples.append(n.getName())
 metric=json.load(open(B/'gen_red_keep'/t/t/'run/logs/asap7'/('dp_'+t)/'base/1_synth.json'));assert rows['child']['std']+rows['parent']['std']==metric['synth__design__instance__count__stdcell']
 for r in rows.values():r['reserve40pct_um2']=r['area_um2']/.4
 row=dict(type=t,source=str(p),ownership=rows,actual_crossing_nets=cross,examples=examples,total_std=metric['synth__design__instance__count__stdcell'],total_macros=metric['synth__design__instance__count__macros']);out.append(row);print(t,json.dumps(row),flush=True);odb.dbDatabase.destroy(db)
(B/'su_hierarchy/keep_budget.json').write_text(json.dumps(dict(scope='Exact full native wrapper mapping with existing RED source leaf hierarchy preserved. Complete disjoint native ownership, no omitted cells/macros; no hardening/adoption/face/clock/PG/EQ claim. Physical sourcecut still needs full contract.',counts=out),indent=2)+'\n')
