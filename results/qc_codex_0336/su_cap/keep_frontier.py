import odb,json,re,collections
from pathlib import Path
B=Path('/work');t='sle_su_c';db=odb.dbDatabase.create();odb.read_db(db,str(B/'gen_red_keep'/t/t/'run/results/asap7'/('dp_'+t)/'base/1_synth.odb'));block=db.getChip().getBlock()
def child(i):return i.getName().startswith('u_bound.u_u_red.') or i.getName().startswith('u_bound.u_u_red/')
def desc(it):return dict(instance=it.getInst().getName(),master=it.getInst().getMaster().getName(),pin=it.getMTerm().getName())
def seq(it):return bool(re.search('DFF|SDF|DHL|DLL|LQN',it.getInst().getMaster().getName()))
rows=[]
for n in block.getNets():
 ins=[it for it in n.getITerms() if child(it.getInst())];outs=[it for it in n.getITerms() if not child(it.getInst())]
 if not ins or not (outs or n.getBTerms()):continue
 drivers=[it for it in ins if it.getIoType()=='OUTPUT'];loads=[it for it in ins if it.getIoType()=='INPUT'];r=dict(net=n.getName(),direction='out' if drivers else 'in',child_loads=[desc(x) for x in loads],child_drivers=[desc(x) for x in drivers])
 if not drivers:
  r['all_loads_seq_D']=all(seq(x) and x.getMTerm().getName()=='D' for x in loads)
 else:
  ff=[];other=[]
  for dr in drivers:
   if seq(dr):ff.append(dr)
   elif dr.getInst().getMaster().getName().startswith('INV'):
    ai=dr.getInst().findITerm('A');src=ai.getNet() if ai else None
    if src:
     ff.extend(x for x in src.getITerms() if child(x.getInst()) and x.getIoType()=='OUTPUT' and seq(x))
     other.extend(desc(x) for x in src.getITerms() if x.getIoType()=='INPUT' and x.getInst()!=dr.getInst())
  r['source_FF']=[desc(x) for x in ff];r['source_Q_other_loads']=other;r['output_internal_loads']=[desc(x) for x in loads]
 rows.append(r)
data_in=[r for r in rows if r['direction']=='in' and r['net'] not in ['clk','u_bound.rst_n']];output=[r for r in rows if r['direction']=='out'];summary=dict(crossing=len(rows),data_inputs=len(data_in),outputs=len(output),input_load_hist=dict(collections.Counter(len(r['child_loads']) for r in data_in)),non_single_D_inputs=sum(not(r['all_loads_seq_D'] and len(r['child_loads'])==1) for r in data_in),non_FF_outputs=sum(len(r['source_FF'])!=1 for r in output),shared_outputs=sum(bool(r['source_Q_other_loads'] or r['output_internal_loads']) for r in output))
out=dict(scope='Actual native sourcecut frontier only; face qualification not assumed. Clock/reset separate, native source FFs retained.',summary=summary,nets=rows);(B/'su_hierarchy/keep_frontier.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(summary),flush=True)
