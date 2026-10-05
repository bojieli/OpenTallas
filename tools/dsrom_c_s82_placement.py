"""One S82 fixed-inventory placement preview; no hardened/route admission transfer."""
import json,math,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'results/uarch/dsrom_c_w4_20261003';I=BASE/'s82_inputs'
def read(n):return json.loads((I/(n+'.json')).read_text())
def overlap(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def snap(x):return math.ceil((x-1e-7)/.432)*.432
def build():
 inv=read('inventory');stage=read('stage_map');ledger=read('area_ledger');ret=read('return_baseline');wake=json.loads((BASE/'inputs/wake.json').read_text());fixed=json.loads((BASE/'inputs/fixed.json').read_text())
 assert inv['stages']==82 and inv['pairs_per_rank_die']==2388 and ret['RD']==64
 BF=set(stage['BF_site_IDs']);assert len(BF)==512
 rect=[]
 def add(name,b,kind,**kw):rect.append(dict(name=name,bbox_um=[round(v,6) for v in b],kind=kind,**kw))
 for s in fixed['source_service_rectangles']:
  if s['name']=='X_SEL_TOPK_STORE':continue # retained old store already replaced by complete selector
  add(s['name'],[v/1000 for v in s['bbox_DBU']],'service_reservation')
 add('FULL_SELECTOR',wake['selector']['single_full_slot_bbox_DBU'],'temporary_DBU')
 rect[-1]['bbox_um']=[v/1000 for v in rect[-1]['bbox_um']];rect[-1]['kind']='selector_reservation'
 r=read('R49');c=read('C9')
 add('CAPTURE_RAW',[v/1000 for v in r['per_shard_raw_homes'][0]['bbox_DBU']],'capture_reservation',seats=320,source_scope='retained 320-seat raw record template')
 raw0=r['per_shard_raw_homes'][0]['bbox_DBU'];raw1=r['per_shard_raw_homes'][1]['bbox_DBU'];y1=raw0[3]/1000+4.32
 add('CAPTURE_RAW_256_PAIRED',[raw0[0]/1000,y1,raw0[2]/1000,y1+(raw1[3]-raw1[1])/1000],'capture_reservation',seats=256,source_scope='same retained 256-seat template, translated to this PAIR1 die; no crossdie mux or new SRAM credit')
 add('CAPTURE_COMMON',[v/1000 for v in r['corrected_common_bbox_DBU']],'capture_reservation')
 add('C9_CLOCK_BANK',[v/1000 for v in c['selected_selector_clock_construction']['named_bank_bbox_DBU']],'clock_reservation')
 obstacles=list(rect);bounds=stage['region_bounds'];Q=wake['field']['mapped_q_outline_um'];B=wake['field']['BF_outline_um'];halo=4.32;rowpitch=snap(B[1]+2*halo);region_fail=[]
 for region,(lo,hi) in enumerate(zip(bounds,bounds[1:])):
  origin=snap((region%2)*16500);x=origin+halo;y=(region//2)*rowpitch+halo
  for pair in range(lo,hi):
   w,h=B if pair in BF else Q
   while True:
    box=[x-halo,y-halo,x+w+halo,y+h+halo];hits=[o for o in obstacles if overlap(box,o['bbox_um'])]
    if not hits:break
    x=snap(max(o['bbox_um'][2] for o in hits)+halo)
   if x+w+halo>origin+16500:region_fail.append(dict(region=region,pair=pair,right=x+w+halo,limit=origin+16500))
   add('pair'+str(pair),[x,y,x+w,y+h],'BF' if pair in BF else 'q',site=pair,root_region=region,halo_um=halo)
   x=snap(x+w+2*halo)
 end=64*rowpitch;y0=snap(end+8.64);pitchx=46.656;pitchy=snap(62.910+8.64);cols=math.floor(33000/pitchx);N=2388*max(inv['configuration_macro_inventory']['macros_per_pair_by_stage'])
 for k in range(N):
  x=(k%cols)*pitchx+halo;y=y0+(k//cols)*pitchy+halo
  add('cfg'+str(k),[x,y,x+38.016,y+62.910],'cfg',pair=k//7,slice=k%7,halo_um=halo)
 top=y0+math.ceil(N/cols)*pitchy+8.64
 add('RD64_RETURN_FULL4096',[0,top,33000,top+ret['FF50_reservation_mm2']*1e6/33000],'return_FF50_reservation',no_inactive_input_credit=True)
 # Exact rectangle collisions with coarse spatial bins, not area-only screening.
 grid={};collisions=[]
 for ix,a in enumerate(rect):
  b=a['bbox_um'];keys=[(x,y) for x in range(int(b[0]//1000),int((b[2]-1e-6)//1000)+1) for y in range(int(b[1]//1000),int((b[3]-1e-6)//1000)+1)]
  prior=set(j for k in keys for j in grid.get(k,[]))
  for j in prior:
   if overlap(b,rect[j]['bbox_um']):collisions.append([rect[j]['name'],a['name']])
  for k in keys:grid.setdefault(k,[]).append(ix)
 out_of_die=[a['name'] for a in rect if min(a['bbox_um'][:2])<0 or a['bbox_um'][2]>33000 or a['bbox_um'][3]>26000]
 return dict(candidate='DS4096-TP4-S82-PAIR1',source_inventory_commit='717a32dcf',known_rectangle_union_mm2=sum((a['bbox_um'][2]-a['bbox_um'][0])*(a['bbox_um'][3]-a['bbox_um'][1])/1e6 for a in rect) if not collisions else None,known_union_is_not_858_composed_fit=True,rectangle_count=len(rect),capture_seats=sum(a.get('seats',0) for a in rect),q=1876,BF=512,weight_macros=9552,cfg_macros=N,region_overflow=region_fail,collisions=collisions,out_of_die=out_of_die,rectangles=rect,screen_mm2=ledger['candidate_screen']['screen_mm2'],screen_margin_mm2=ledger['candidate_screen']['margin_mm2'],return_mm2=ret['FF50_reservation_mm2'],return_bits=ret['bits'],complement_credit_mm2=0,unmapped_complement_mm2=287.02184985143003,known_rectangle_no_overlap=not(collisions or region_fail or out_of_die),full_placement_admitted=False,PnR_admitted=False,rate_adopted=False,missing_physical_construction=['source-matched hardened q/BF abstracts/SSFF, including selected pipeline','PAIR1 576-seat capture control/read/gather timing and loaded clock; templates co-located, no global mux qualification','return control/arithmetic/clock/PG beyond retained FF52.8976','RNE/WAKE containment union, no double charge','W3 scan/non-scan PHY/controller/SerDes placements','287 complement replacement: clock/PG/decap/DFT/IO and unusable-region union'],latency={'S82_vs_S73_stage_hops_us_only':4.338,'full_single_user_MTP_delta_us':None,'pipeline_owner':'Epicurus/Peirce; no latency transferred from old frame'},source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(I.iterdir()) if p.is_file()})
if __name__=='__main__':print(json.dumps(build(),indent=2,sort_keys=True))
