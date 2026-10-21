"""Tiny exact-allocator slot model; no full-stage build or changed live source."""
import os,sys,json,hashlib,math
from pathlib import Path
D=Path(__file__).resolve().parent
for k,v in dict(OT_XS_QPAIRS='12',OT_XS_PAIR_ROTATE='0',OT_XS_GU_MERGE='1',OT_XS_TOPO='1',OT_XS_PROP='1',OT_XS_CAL_SEGMENT='1',OT_XS_APROJ_TOPO='1',OT_XS_COMPACT_TAILS='0',OT_XS_KSLOT='1').items():os.environ[k]=v
sys.path.insert(0,str(D/'root/tools/s81_dv/layer_prog'))
import xs_capacity as XC
import xs_topo as TP
removed=json.loads((D/'idx3_frame_inventory.json').read_text())['frames_removed']
res={}
for nf in (122,116):
 die=XC._die('/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref')
 if nf==116: die.plan['blocks']=[b for b in die.plan['blocks'] if b['name'] not in removed]
 TP.set_from_die(die)
 inv=[{'name':'u_'+b['name'],'master':b['master'],'group':b['group']} for b in die.plan['blocks'] if b['kind']=='frame']
 assert len(inv)==nf
 # These source-bound representatives include the constraining central slice
 # and the full eight-frame edge; exact all-frame qualification remains owed.
 frames=['u_f_3L02','u_f_3R03','u_f_0L00','u_f_0L10']
 rows=[]
 for n in (1,2,3):
  for frame in frames:
   r=XC.frame_alloc(die,frame,str(Path('/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0')),{'id':f'exp_n{n}','dense_layer':None,'experts':n})
   rows.append({'n':n,'frame':frame,'q':r['q_fill_ub'],'phases':r['nphases'],'identical':r['layout_identical']})
 slopes=[(max(r['q'])/r['n']) for r in rows]
 slope=max(slopes)
 res[str(nf)]={'inventory':inv,'inventory_sha256':hashlib.sha256(json.dumps(inv,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'topology':TP.describe(),'exact_small_rows':rows,'worst_expert_words_per_pair_representatives':slope,'expert_only_max_per_stage':math.floor(8191/slope),'expert_only_stage_lower_bound':math.ceil(15360/math.floor(8191/slope)),'scope':'exact tiny allocator samples; dense overhead and all-frame exact map still owed'}
 print('SLOT_MODEL',nf,json.dumps({k:v for k,v in res[str(nf)].items() if k not in ('inventory','exact_small_rows')}),flush=True)
 (D/'inventory_slot_model.json').write_text(json.dumps(res,indent=2)+'\n')
