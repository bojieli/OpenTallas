import os,sys,json,copy,hashlib,importlib.util
from pathlib import Path
B=Path(__file__).parent
sys.path[:0]=['tools','results/arch/qwen_tp8_1012']
import qwen_split
spec=importlib.util.spec_from_file_location('qwen_split.fault_emit',B/'fault_emit.py')
F=importlib.util.module_from_spec(spec);sys.modules[spec.name]=F;spec.loader.exec_module(F)
qwen_split.fault_emit=F
import qwen_rom_fulldie_b3r2 as G
import die_top_lint as D
projections=[]
original_geometry=F.source_bit_geometry

def geometry(v,m,GG,hard=None):
 hard=F._hard() if hard is None else hard
 by={i.name:i for i in m['insts']};selected=v.masters(m,1)
 names={by[n].master for n in hard}
 old={n:copy.deepcopy((selected[n].ports,selected[n].order,getattr(selected[n],'assigned_fragment_rects',{}))) for n in names}
 raw={n:v.pin_rects(selected[n],1,{p:sp[1] for p,sp in selected[n].ports.items()}) for n in names}
 result=original_geometry(v,m,GG,hard)
 import re
 def canon(name,rects):
  rows=[]
  for p,L,r in rects:
   q=re.fullmatch(r'(.*?)(?:\[(\d+)\])?',p);base,bit=q[1],int(q[2] or 0)
   real,indices=m.get('port_join',{}).get(name,{}).get(base,(base,None))
   rows.append((real,indices[bit] if indices is not None else bit,L,tuple(r)))
  return sorted(rows)
 for n in names:
  assert old[n]==(selected[n].ports,selected[n].order,getattr(selected[n],'assigned_fragment_rects',{})),('selected master mutated',n)
  q=result[0][n]
  new=v.pin_rects(q,1,{p:sp[1] for p,sp in q.ports.items()})
  assert canon(n,raw[n])==canon(n,new),('actual selected physical rectangles moved',n)
  projections.append(dict(master=n,pin_rectangles=len(new),selected_original_unchanged=True))
 return result
F.source_bit_geometry=geometry
class PreComplete(Exception):pass

def stop(v,m,*a,**kw):
 entries=m.get('fault_source_bit_contract')
 assert entries and projections,'stopped before source preflight'
 rec=dict(scope='actual selected full-source PRE completed; intercepted before every relay planner; no GEN/route result',source=str(Path.cwd()),source_bits=len(entries),source_bit_contract=entries,projection_checks=projections,fault_roots=len(m['fault_emit']['roots']),fault_edges=len(m['fault_emit']['edges']),die=m['die'],flags={k:v for k,v in os.environ.items() if k.startswith(('OT_SPLIT_','OT_QWEN_','OT_RELAY_','OT_PIN_BIT_'))},candidate_sha256=hashlib.sha256((B/'fault_emit.py').read_bytes()).hexdigest())
 import pickle
 with (B/'ACTUAL_PRE_MODEL.pkl').open('wb') as out:
  pickle.dump(dict(fault=m['fault_emit'],insts=[dict(name=i.name,master=i.master,x=i.x,y=i.y,w=i.w,h=i.h,orient=getattr(i,'orient','R0')) for i in m['insts']],buses=m['buses'],die=m['die'],fault_masters={n:v.pin_rects(q,1,{p:sp[1] for p,sp in q.ports.items()}) for n,q in v.masters(m,1).items() if n.startswith('qfd_flt')}),out)
 (B/'ACTUAL_PRE.json').write_text(json.dumps(rec,indent=2))
 print('ACTUAL_SOURCE_PRE_PASS',rec['source_bits'],'source bits',len(projections),'source masters',sum(r['pin_rectangles'] for r in projections),'physical rectangles preserved','roots',rec['fault_roots'],'STOP BEFORE RELAYS',flush=True)
 raise PreComplete()
G._relays_fanout=stop;G._relays=stop
D.QWEN_RECIPE='tp8b';D._QW.clear();D.QSRC=None
source=D.qwen_src()
assert Path(source['root']).resolve()==Path.cwd().resolve(),source
assert Path(G.__file__).resolve().parent==Path.cwd().resolve()/'tools'
assert sys.modules['qwen_rom_fulldie_b3r2'] is G
assert G._relays is stop and G._relays_fanout is stop
recipe=dict(D.QWEN_RECIPES['tp8b']);cdc=recipe.pop('cdc')
print('PRE_DRIVER_DIRECT_SELECTED',str(Path(G.__file__).resolve()),'relay hooks verified',flush=True)
try:G.selected(True,cdc=G._cdc_arg(cdc),**recipe)
except PreComplete:sys.exit(0)
raise SystemExit('PRE interception was not reached')
