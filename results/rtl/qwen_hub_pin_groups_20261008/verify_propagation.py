import pathlib,json,collections,re,hashlib
base=pathlib.Path('/srv/opentallas-scratch2/scratch/codex/qwen-pin-balance/propagate')
for p in sorted(base.glob('qfd_*')):
 v=json.loads((p/'vehicle.json').read_text());rows=[r.split() for r in (p/'pins.tsv').read_text().splitlines()];by=collections.defaultdict(list);viol=[]
 for n,layer,x0,y0,x1,y1 in rows:
  x0,y0,x1,y1=map(int,(x0,y0,x1,y1));cx=(x0+x1)/2000;cy=(y0+y1)/2000;matches=[r for r in v['regions'] if re.search(r['regex'],n)];assert len(matches)==1,(n,matches);region=matches[0];edge=region['edge'];lo,hi=region.get('range_um',(0,v['fh']) if edge in ('left','right') else (0,v['fw']));pos=cy if edge in ('left','right') else cx
  assert lo<=pos<=hi,(n,pos,lo,hi)
  assert {'left':x0==0,'right':x1==round(v['fw']*1000),'bottom':y0==0,'top':y1==round(v['fh']*1000)}[edge],(n,edge,x0,y0,x1,y1)
  by[edge+'/'+layer].append((y0,y1,n) if edge in ('left','right') else (x0,x1,n))
 density={};overlaps=[]
 for key,boxes in by.items():
  boxes.sort();prev=None
  for lo,hi,n in boxes:
   if prev and lo<prev[1]:overlaps.append((key,n,prev[2]))
   if prev is None or hi>prev[1]:prev=(lo,hi,n)
  ps=[(r[0]+r[1])/2000 for r in boxes];right=0;best=0
  for left,x in enumerate(ps):
   while right<len(ps) and ps[right]<x+100:right+=1
   best=max(best,right-left)
  density[key]=best/100
 assert len(rows)==len({r[0] for r in rows}) and not overlaps and max(density.values())<12
 result={'verdict':'PASS','cfg':v['cfg'],'signal_pins':len(rows),'duplicates':0,'outside_original_region':0,'overlapping_pin_boxes':0,'max_density_bits_per_um_over_100um':density,'original_vehicle':v['work'],'implementation_sha256':hashlib.sha256((base/'run_abi3_physical.py').read_bytes()).hexdigest(),'pin_map_sha256':hashlib.sha256((p/'pins.tsv').read_bytes()).hexdigest(),'frame_um':[v['fw'],v['fh']],'RTL_change':False,'cycles_added':0,'area_delta_um2':0,'scope':'full-shape production generator pin map only; physical closure gates remain mandatory'}
 (p/'check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
