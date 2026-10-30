import json,math
from pathlib import Path
p=json.load(open('/tmp/qcclock0336/n_seam_coupler_prep.json'));site=.054;rp=.54;free={};cells=[]
for row in range(math.ceil(2.16/rp),math.floor((86.4-2.16-.27)/rp)+1):
 y=row*rp;intervals=[(math.ceil(779.76/site),math.floor(1561.68/site))]
 if y<17.28:
  intervals=[(math.ceil(779.76/site),math.floor(781.92/site)),(math.ceil(1036.512/site),math.floor(1561.68/site))]
 free[row]=intervals
# R0clocknativeBUF24 body, reserveseparatelynearleftoutsideboundaryFFstrip

def alloc(x,y,ident,widthsites=38,kind="BUF24"):
 best=None;w=widthsites;targetx=x-.048;targety=y-.135
 for row,ivals in free.items():
  if abs(row*rp-targety)>45:continue
  for lo,hi in ivals:
   if hi-lo<w:continue
   xi=max(lo,min(hi-w,round(targetx/site)));score=abs(xi*site-targetx)+abs(row*rp-targety)
   if best is None or (score,row,xi)<best:best=(score,row,xi)
 if best is None:raise ValueError(('NO_CELL_SPACE',ident))
 score,row,xi=best;out=[]
 for lo,hi in free[row]:
  if lo<=xi and xi+w<=hi:
   if lo<xi:out.append((lo,xi))
   if xi+w<hi:out.append((xi+w,hi))
  else:out.append((lo,hi))
 free[row]=out;c={'id':ident,'origin_um':[xi*site,row*rp],'kind':kind,'A_um':[xi*site+(.058 if kind=='BUF8' else .048),row*rp+.135],'Y_um':[xi*site+(.416 if kind=='BUF8' else .956),row*rp+.234],'reserved_bbox_um':[xi*site,row*rp,(xi+w)*site,(row+1)*rp],'anchor_L1shift_um':score};cells.append(c);return c
clock=alloc(779.808,2.295,'native_clk50fF_BUF24');reset=alloc(779.818,2.835,'native_rst_BUF8',15,'BUF8')
def point(path,t):
 lengths=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(path,path[1:])];d=sum(lengths)*t
 for a,b,ll in zip(path,path[1:],lengths):
  if ll and d<=ll:return[a[0]+(b[0]-a[0])*d/ll,a[1]+(b[1]-a[1])*d/ll]
  d-=ll
 return path[-1]
segments=[];rows=[]
for b in p['bits']:
 length=b['wire_native_to_existing_face_pin_um'];steps=math.ceil(length/60);fractions=[j/steps for j in range(1,steps)]
 if b['bus'] in ['tx_flit','tx_v'] and (not fractions or (1-fractions[-1])*length>20):fractions.append(max(0,1-20/length))
 fractions=sorted(set(fractions));chain=[alloc(*point(b['polyline_um'],t),f"{b['bus']}[{b['bit']}].r{i}") for i,t in enumerate(fractions)]
 # FullactualHtrack staysassigned; localVstubs hititsunchangedheight.
 reverse=b['bus'] in ['tx_flit','tx_v'];cur=b['polyline_um'][-1] if reverse else b['polyline_um'][0];yy=b['track_height_um'];maxlen=0;totalwire=0;prev_region=2 if reverse else 0
 def region(t):
  d=t*length
  return 0 if d<=yy+.096 else 2 if d>=yy+.096+abs(b['polyline_um'][0][0]-b['polyline_um'][-1][0]) else 1
 for ci,c in (list(enumerate(chain))[::-1] if reverse else enumerate(chain)):
  this_region=region(fractions[ci])
  dest=c['A_um'];path=[cur,[cur[0],dest[1]],dest] if prev_region==this_region and this_region in [0,2] else [cur,[cur[0],yy],[dest[0],yy],dest];ll=sum(abs(a[0]-z[0])+abs(a[1]-z[1]) for a,z in zip(path,path[1:]));segments.append(ll);totalwire+=ll;maxlen=max(maxlen,ll);cur=c['Y_um'];prev_region=this_region
 dest=b['polyline_um'][0] if reverse else b['polyline_um'][-1];last_region=0 if reverse else 2;ll=(abs(cur[0]-dest[0])+abs(cur[1]-dest[1])) if prev_region==last_region else abs(cur[1]-yy)+abs(cur[0]-dest[0])+abs(yy-dest[1]);segments.append(ll);totalwire+=ll;maxlen=max(maxlen,ll)
 rows.append({'bus':b['bus'],'bit':b['bit'],'flow_direction':'existingFF_to_native' if reverse else 'native_to_existingFF','repeaters':[c['id'] for c in chain],'max_segment_um':maxlen,'actual_repeater_wire_total_um':totalwire,'actual_with_existingFF30_um':totalwire+30,'assigned_Htrack':b['track_layer'],'track_height_um':yy})
summary={'status':'N/S existing-neighbour comb construction PREP, no dataFF added, no physical/source adoption','BUF24_data':len(cells)-2,'BUF24_nativeclk':1,'BUF8_native_reset':1,'data_BUF_master_raw_area_um2':(len(cells)-2)*.4374,'data_BUF_reserved_40pct_um2':(len(cells)-2)*.4374/.4,'existing_boundaryFF_reserve_rect_um':[781.92,0,1036.512,17.28],'reservedFFband_scope':'Candidate footprint for existing1197boundaryFF+polarity/epoch; actualmappedFFXY unavailable, no claim existing placement already matches.','required_free_soft_band':'coll_sS86.4um / mirroredcoll_nN86.4um after explicitnativeSRAM/codec/CA/FTrepack; no reservedbumps/decap logicborrowed','max_packed_buffered_section_um':max(segments),'sections_over120':sum(x>120 for x in segments),'max_anchor_shift_um':max(c['anchor_L1shift_um'] for c in cells),'nativeclk_BUF_body':clock,'native_reset_BUF_body':reset,'actual_repeater_wire_total_max_um':max(z['actual_repeater_wire_total_um'] for z in rows),'actual_with_existingFF30_max_um':max(z['actual_with_existingFF30_um'] for z in rows),'actual_total_paths_over405_withFF30':sum(z['actual_with_existingFF30_um']>405 for z in rows),'native_to_face_path_max_um':p['summary']['max_native_to_face_wire_um'],'native_to_existingFF_path_with30bound_max_um':p['summary']['max_with_existing_FF_R2_30_um'],'HOLD':['actualFF/CA/FT/body/TAPCELL/PGledger','actualnativeTT/FFandexistingFFCQ/transition; TXusesreverseBUForderwithactualA/Ypins','negative/control/reset/globalclockprice','realnativeM5accessVIAsandparentcoupledgeometryreview']}
Path('/tmp/qcclock0336/n_seam_repeaters_prep.json').write_text(json.dumps({'summary':summary,'cells':cells,'bits':rows},indent=1)+'\n');print(json.dumps(summary,indent=2))
