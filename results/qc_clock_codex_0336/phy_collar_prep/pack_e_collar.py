import json,math,bisect
from pathlib import Path
D=json.load(open('/tmp/qcclock0336/collar_geometry_prep.json'));bits=[b for b in D['bits'] if b['type']=='phy_serdes_b'];site=.054;row=.54;free={};cells=[]
# All rows fixedR0, cellbottom y. Nativebody [0.270,0,1563.84,2320.056]. Two2.16halos.
for yi in range(math.ceil(2.16/row),math.floor((2393.28-2.16-.27)/row)+1):
 y=yi*row;xlo=2.16 if y>=2320.056+2.16 else 1563.84+2.16;xhi=1632.96-2.16
 free[yi]=[(math.ceil(xlo/site),math.floor(xhi/site))]
def alloc(ideal,width_sites=29,kind='DFF_INV',ident=''):
 best=None;wantx=ideal[0]-.54;wanty=ideal[1]-.135;yi0=round(wanty/row)
 for yi in range(yi0-58,yi0+59):
  if yi not in free:continue
  for lo,hi in free[yi]:
   if hi-lo<width_sites:continue
   xi=max(lo,min(hi-width_sites,round(wantx/site)));cost=abs(xi*site-wantx)+abs(yi*row-wanty)
   if best is None or (cost,yi,xi)<best:best=(cost,yi,xi)
 if best is None:raise ValueError(('NO_SPACE',ident))
 cost,yi,xi=best;new=[]
 for lo,hi in free[yi]:
  if lo<=xi and xi+width_sites<=hi:
   if lo<xi:new.append((lo,xi))
   if xi+width_sites<hi:new.append((xi+width_sites,hi))
  else:new.append((lo,hi))
 free[yi]=new;rec={'id':ident,'kind':kind,'origin_um':[xi*site,yi*row],'reserved_bbox_um':[xi*site,yi*row,(xi+width_sites)*site,(yi+1)*row],'ideal_xy_um':ideal,'anchor_delta_L1_um':cost,'proxy_clock_pin_um':[xi*site+.108,yi*row+.135],'positive_data_input_pin_um':[xi*site+1.116,yi*row+.135],'positive_data_output_pin_um':[xi*site+1.037,yi*row+.135]};cells.append(rec);return rec

def point(path,t):
 lengths=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(path,path[1:])];d=sum(lengths)*t
 for a,b,ll in zip(path,path[1:],lengths):
  if d<=ll:return[a[0]+(b[0]-a[0])*d/ll,a[1]+(b[1]-a[1])*d/ll]
  d-=ll
 return path[-1]
bybit={}
for j in range(1,10):
 for b in bits:
  k=(b['bus'],b['bit']);ideal=point(b['polyline_um'],j/9)
  bybit.setdefault(k,[]).append(alloc(ideal,ident=f'b{j}.{k[0]}[{k[1]}]'))
# Extra bankcontrols clock/resetbody reserve: real master counts padded tocommon29sitepair allocation perunit.
for j in range(1,10):
 anchor=point(bits[len(bits)//2]['polyline_um'],j/9)
 for k in range(5):alloc(anchor,width_sites=40,kind='ASR_INV_TIEHI',ident=f'b{j}.epoch{k}')
 for k in range(6):alloc(anchor,width_sites=33,kind='CONTROL_DFF_LOGIC',ident=f'b{j}.ctl{k}')
 # Real38leafBUF8+17BUF24+localresetBUF8 PAD0 envelope. Actualconnectivitynotinvented bypacking.
 for k in range(39):alloc(anchor,width_sites=15,kind='BUF8',ident=f'b{j}.leaf_reset{k}')
 for k in range(17):alloc(anchor,width_sites=38,kind='BUF24',ident=f'b{j}.clk{k}')
# Route geometrically outside body byN/Ecorner. ModelactualFFpin endpoints; noRC/signoff.
def route(a,b):
 if a[1]>=2322.216 and b[1]>=2322.216:return[a,[b[0],a[1]],b]
 if a[0]>=1566 and b[0]>=1566:return[a,[a[0],b[1]],b]
 return[a,[a[0],b[1]],b] if a[1]<2322.216 else [a,[b[0],a[1]],b]
hops=[];outer=[]
for b in bits:
 chain=bybit[(b['bus'],b['bit'])];source=b['polyline_um'][0];last=source
 for j,c in enumerate(chain):
  # actualpositiveA/Qpin differsdirection butbothcells arewithinbound by<1.2um.
  dest=c['positive_data_input_pin_um'];path=route(last,dest);length=sum(abs(a[0]-z[0])+abs(a[1]-z[1]) for a,z in zip(path,path[1:]));hops.append({'bus':b['bus'],'bit':b['bit'],'stage':j+1,'wire_um':length,'polyline_um':path});last=c['positive_data_output_pin_um']
 outer.append(sum(abs(a-z) for a,z in zip(last,b['polyline_um'][-1])))
# Rowsdisjointfreeintervalsplit guaranteesnonoverlap. Reservedunits reflect40% onR0only lattice: physicalwidth1.242 /reserved1.566 * .27/.54 =39.655%.
summary={'status':'GEOMETRY PREP ONLY, notreviewapproved, noRTLadoption or timingrun','cell_entries':len(cells),'data_FF':9*1197,'per_bank_epochs':5,'per_bank_control_DFF':6,'per_bank_BUF8_clock_reset':39,'per_bank_BUF24_clock':17,'data_repeater_cells':'NOT YET PACKED; fullgeometrynotclosed','max_actual_pin_hop_um':max(x['wire_um'] for x in hops),'hops_over405':sum(x['wire_um']>405 for x in hops),'outer_pin_to_lastFF_proxy_max_um':max(outer),'max_cell_anchor_shift_um':max(c['anchor_delta_L1_um'] for c in cells),'master_actualpins':'DFFQN positiveoutput via inputINV; DFFpinclock/input/output actualmasterlocalpositions included. Controlcompactsubcellsplanned, notindividualplaced; epochclockroleprepriced notadopted.','R0rows':.54,'xsite':.054,'conservative_clear_rectangles':'N y>=2322.216; E x>=1566; outer2.16haloboundaries. TrackcutactualE64.8um/N68.904um, not69.12clear.','failures':['datarepeaterpacking notdone','clockconnectivity/RC notbuilt fromallactualcells','nativeinputdirection andepoch/wavefront semantics needexactRTL+miter','intermediateepoch/control compactsubcells needexplicitbodycoordinates','fullPG/island/cutcapacitynotrouted']}
repeaters=[];segments=[];allsegments=[];local_segs=[];global_segs=[]
for h in hops:
 chain=[]
 for q in [0.01,.2,.4,.6,.8]:
  rr=alloc(point(h['polyline_um'],q),width_sites=38,kind='DATA_BUF24',ident=f"{h['bus']}[{h['bit']}].h{h['stage']}.r{q}")
  rr['A_xy_um']=[rr['origin_um'][0]+.048,rr['origin_um'][1]+.135];rr['Y_xy_um']=[rr['origin_um'][0]+.956,rr['origin_um'][1]+.234];chain.append(rr)
 prev=h['polyline_um'][0]
 for rr in chain:
  path=route(prev,rr['A_xy_um']);allsegments.extend(zip(path,path[1:]));(local_segs if sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(path,path[1:]))<=30 else global_segs).extend(zip(path,path[1:]));segments.append(sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(path,path[1:])));prev=rr['Y_xy_um']
 path=route(prev,h['polyline_um'][-1]);allsegments.extend(zip(path,path[1:]));(local_segs if sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(path,path[1:]))<=30 else global_segs).extend(zip(path,path[1:]));segments.append(sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(path,path[1:])));repeaters.extend(chain)
summary['data_repeater_cells']=len(repeaters);summary['max_buffered_wire_section_um']=max(segments);summary['buffered_wire_sections_over120']=sum(z>120 for z in segments);summary['max_cell_anchor_shift_um']=max(c['anchor_delta_L1_um'] for c in cells);summary['cell_entries']=len(cells);summary['failures'][0]='datarepeaterspacked; electricalwiresections over120 remainFAIL' if max(segments)>120 else 'datarepeaterspacked; native/sourcecq/load and actualM6/M7 RC stillunbound'
def cuts(axis,region,source=None):
 ev=[]
 for a,b in (allsegments if source is None else source):
  if abs(a[1-axis]-b[1-axis])>1e-6:continue
  if region=='N' and a[1]<2322.216:continue
  if region=='E' and a[0]<1566:continue
  lo,hi=sorted([a[axis],b[axis]])
  if hi-lo>1e-6:ev.extend([(lo,1),(hi,-1)])
 cur=0;best=(0,None)
 for loc,delta in sorted(ev):
  cur+=delta
  if cur>best[0]:best=(cur,loc)
 return {'peak_segments':best[0],'cut_coordinate_um':best[1],'includes':'actualmanhattan datarepeaters/FF paths only; noPG/clock/reset/epoch'}
summary['N_horizontal_trackcut']=cuts(0,'N');summary['E_vertical_trackcut']=cuts(1,'E')
summary['routing_layer_assignment']={'local_wirelength_limit_um':30,'local_layers':['M2horizontal','M3vertical'],'global_layers':['M4/M6horizontal','M5/M7vertical'],'reason':'Lower layers permitted by partition<=M7; no localdataoverlicensedbody. Must reserve actualPG/clockaccess before route.'};summary['N_global_M4_M6_cut']=cuts(0,'N',global_segs);summary['E_global_M5_M7_cut']=cuts(1,'E',global_segs);summary['N_local_M2_cut']=cuts(0,'N',local_segs);summary['E_local_M3_cut']=cuts(1,'E',local_segs);summary['N_local_M2_60pct_budget']=.6*68.904/.036;summary['E_local_M3_60pct_budget']=.6*64.8/.036
summary['N_track_upperbudget_at60pct']=.6*68.904*(1/.048+1/.064);summary['E_track_upperbudget_at60pct']=.6*64.8*(1/.048+1/.064)
out={'summary':summary,'cells':cells,'hops':hops};Path('/tmp/qcclock0336/e_collar_placement_prep.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(summary,indent=2))
