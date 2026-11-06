import json,pathlib,math,re,sys
R=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path.cwd();S=json.loads((R/'native_tiles_regions.json').read_text());A=json.loads((R/'native_tiles_reservations.json').read_text());O=json.loads((R/'bands.json').read_text());rec=json.loads((R/'native_tiles_receipt.json').read_text());halo=.432
protected=[(n,kind,[r[0]-halo,r[1]-halo,r[2]+halo,r[3]+halo]) for n,kind,r in A['fixed_points'] if kind!='native_held'];chosen={}
def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
for bus,info in rec['families'].items():
 old=info['box_um'];opts=[]
 # Geometry fit search only; no route/STA recipes or source changes.
 for dx in [2.16*i for i in range(-8,9)]:
  for dy in [2.16*i for i in range(-8,9)]:
   box=[old[0]+dx,old[1]+dy,old[2]+dx,old[3]+dy]
   if not (4.32<=box[0]<box[2]<=1274.4 and 4.32<=box[1]<box[3]<=1032.48):continue
   if any(overlap(box,r) for n,k,r in protected):continue
   if any(overlap(box,v['rect_um']) for k,v in O['bands'].items() if k not in rec['families']):continue
   if any(overlap(box,r) for r in A['hard_blockages']):continue
   opts.append((abs(dx)+abs(dy),abs(dx),dx,dy,box))
 if not opts:raise Exception(('no clear local box',bus))
 _,_,dx,dy,new=min(opts);chosen[bus]=dict(dx=dx,dy=dy,old=old,new=new)
 for r in S['regions']:
  if not r['name'].startswith('ot_rg_native_'+bus+'_'):continue
  r['box_um']=[r['box_um'][0]+dx,r['box_um'][1]+dy,r['box_um'][2]+dx,r['box_um'][3]+dy]
  j=int(r['name'].rsplit('_',1)[1]);pts=[(x,y) for n,x,y in A['pins'] if n.startswith(bus+'[') and int(re.search(r'\[(\d+)\]',n)[1])//64==j];a,c,dd,e=r['box_um'];r['max_pin_to_tile_l1_um']=max(abs(x-xx)+abs(y-yy) for x,y in pts for xx in [a,dd] for yy in [c,e]);assert r['max_pin_to_tile_l1_um']<=405
 info['box_um']=new;info['max_pin_to_tile_l1_um']=max(r['max_pin_to_tile_l1_um'] for r in S['regions'] if r['name'].startswith('ot_rg_native_'+bus+'_'))
for a,x in chosen.items():
 for b,y in chosen.items():
  if a!=b:assert not overlap(x['new'],y['new'])
rec['reservation_check']=dict(halo_um=halo,non_native_fixed_band_overlaps=0,hard_blockages=0,other_native_band_overlaps=0,translations=chosen)
(R/'native_tiles_regions_clear.json').write_text(json.dumps(S,indent=1));(R/'native_tiles_receipt_clear.json').write_text(json.dumps(rec,indent=1));print(json.dumps(chosen,indent=1));print('MAX_L1',max(r['max_pin_to_tile_l1_um'] for r in S['regions']))
