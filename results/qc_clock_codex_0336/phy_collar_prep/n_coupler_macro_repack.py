import json,re
from pathlib import Path
p=json.load(open('/tmp/qcclock0336/plan_qc45.json'));out={'status':'PAIRED GEOMETRY PREP ONLY; nativeSRAM/CA/reservedband nonoverlap witness, not codec/data/PG closure','types':{}}
for typ,height in [('coll_s',734.4),('coll_n',786.24)]:
 t=p['partition_types'][typ];hs=t['hard_cores'];groups={}
 for h in hs:
  m=re.search(r'u_g_face_(\d+)',h['inst']);f=m[1] if m else '2';groups.setdefault(f,[]).append(h)
 placed=[]
 for gi,(face,hh) in enumerate(sorted(groups.items())):
  for i,h in enumerate(hh):
   col=2*gi+i%2;row=i//2;x=41.472+187.272*col;y=103.68+103.68*row
   if col==3:y=[155.52,345.6,449.28][row]
   if typ=='coll_n':
    # Keep86.4Nband free. ActualR0-native macrorows, not blindlymirroringphysicalcells.
    y=69.12+103.68*row
   z=dict(h,candidate_origin_um=[x,y],original_origin_um=h['origin_um'],logical_face=face);placed.append(z)
 ca=[]
 for q in t['clock']['landing_contract'].get('collector_local_sources',[]):
  rect=list(q['band']['rect_um'])
  if typ=='coll_s' and rect[1]>700:rect=[rect[0],rect[1]-69.12,rect[2],rect[3]-69.12]
  ca.append({'name':q['name'],'rect_um':rect,'reserve_um2':q['band']['area_reserve_um2'],'scope':'ExistingplanPROPOSEDcollector band. Live/padded counts unchanged; actualclockandpinarrival mustreprice.'})
 def box(z):x,y=z['candidate_origin_um'];w,h=z['outline_um'];return[x,y,x+w,y+h]
 def overlap(a,b):return a[0]<b[2]-1e-8 and b[0]<a[2]-1e-8 and a[1]<b[3]-1e-8 and b[1]<a[3]-1e-8
 failure=[]
 for i,h in enumerate(placed):
  b=box(h);halo=[b[0]-4.32,b[1]-4.32,b[2]+4.32,b[3]+4.32]
  if halo[0]<0 or halo[1]<0 or halo[2]>t['outline_um'][0]+1e-8 or halo[3]>height+1e-8:failure.append([h['inst'],'outline'])
  coupler=[0,0,t['outline_um'][0],86.4] if typ=='coll_s' else[0,height-86.4,t['outline_um'][0],height]
  if overlap(halo,coupler):failure.append([h['inst'],'coupler86.4'])
  for c in ca:
   if overlap(halo,c['rect_um']):failure.append([h['inst'],'CA:'+c['name']])
  for hh in placed[i+1:]:
   b2=box(hh);halo2=[b2[0]-4.32,b2[1]-4.32,b2[2]+4.32,b2[3]+4.32]
   if overlap(halo,halo2):failure.append([h['inst'],hh['inst'],'halo'])
 out['types'][typ]={'outline_candidate_um':[t['outline_um'][0],height],'native_memories':placed,'existing_CA_bands_rebased':ca,'macro_or_CA_or_coupler_overlap_failures':failure,'macro_only_verdict':'PASS' if not failure else'FAIL','CA_area_reserve_sum_um2':sum(c['reserve_um2'] for c in ca),'coupler_macrofree_rect_um':coupler,'HOLD':['fullactualcodec+datapath<=405','realstandardcellandtap/endcap/PGbodyreserve','allCA/START/nativeclockandforwardedclocktiming','hardcorepin-to-registerandnativeITermclockgraph','FT/portcapacity/rootreview'],'planned_contents_envelopes':'Reworkcontents518x388 rectangles do NOTremain sealed; allactualmemoryviews/trackoffsets preserved. Codec/sourceconnectiongraphs unchangedpendingphysicalplanadoption.'}
Path('/tmp/qcclock0336/n_coupler_macro_repack.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v['macro_or_CA_or_coupler_overlap_failures'] for k,v in out['types'].items()})
