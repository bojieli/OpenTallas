import json,sys
from pathlib import Path
sys.path.insert(0,'tools');import schema as S,lane_add as L
raw=json.load(open('out_shared_v4/die_plan.json'))
rml={x['id'] for x in raw['lanes'] if x['id'].startswith(('L702','L703','L704','L705'))};rmp={q for x in raw['lanes'] if x['id'] in rml for q in x['ports']};raw['ports']=[x for x in raw['ports'] if x['id'] not in rmp];raw['lanes']=[x for x in raw['lanes'] if x['id'] not in rml]
for t in raw['partition_types'].values():
 for k in ('buses','ft_slots'):t[k]=[x for x in t.get(k,[]) if not x['name'].startswith(tuple(rml))]
for k in rml:raw['latency']['lanes'].pop(k,None)
B=L.Builder(raw,require_cycle_match=False);B.shared=set();out=[]
def resite(chain,slots,start,end):
 for sl in slots:
  boxes=S.placed_macro_boxes(B.P.ptype(sl[0]),halo=4.32)
  for xy in sl[9]:
   x,y=B.P.to_type(sl[0],xy)
   hit=[nm for nm,(x0,y0,x1,y1) in boxes.items() if x0<=x<=x1 and y0<=y<=y1]
   if hit:out.append({'part':sl[0],'die_um':xy,'type_um':[x,y],'hits':hit,'slot_stations':sl[8]})
 return None
B.resite=resite
B.build_one('NW_spb0','NW_hub',615,['NW_spb0','NW_sm3','NW_su30','NW_hub'],'path',None,record=False)
rep={'why':B._why,'macro_hits':out};Path('reverse_probe.json').write_text(json.dumps(rep,indent=1));print(json.dumps(rep)[:3500])
