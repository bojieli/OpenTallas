"""PREP only: emit native partition FT obstruction coupon, execute no EDA."""
import copy,json,sys,math,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/die_plan'))
import schema as S,die_trial as D,partition_ft_reserve as F,gen_phys as GP
O=Path(__file__).parent;source=Path('/srv/opentallas-scratch/claude/codex-current-ci-2049/physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json');D.ROOT=source.parents[4]
raw=json.loads(source.read_text());delta=json.loads((O/'north_channel_PREP_ONLY.json').read_text())['type_band_delta']
def union(v):
 out=[]
 for a,b in sorted(v):
  if b<=a:continue
  if out and a<=out[-1][1]:out[-1][1]=max(out[-1][1],b)
  else:out.append([a,b])
 return out
def subtract(free,blocked):
 out=[]
 for a,b in free:
  x=a
  for c,d in union(blocked):
   if d<=x:continue
   if c>=b:break
   if c>x:out.append([x,min(c,b)])
   x=max(x,d)
  if x<b:out.append([x,b])
 return out
summary={'scope':'local-frame source coupon; no EDA executed; PG model is not an actual ODB measurement','consumer':'gen_phys.py reservation(P,tn) => partition_ft_reservation.json plus dbObstruction_create Tcl in pdn.tcl; ordinary FP/route consumes it','physical_OPEN':['global parent complement repeated-type identity','actual pdngen geometry including macro PG connect/vias','track grid quantization and PG spacing/via keepouts','local partition routing under reduced capacity','matching actual parent GRT0'],'coupons':{}}
for tn in ['kv3_hgi_v3','kv3_hgi_v8']:
 a=copy.deepcopy(raw);t=a['partition_types'][tn];t['die_ft_bands']=delta[tn]
 a['die']['outline_um']=t['outline_um'];a['partition_types']={tn:t};a['partitions']=[dict(name='coupon',type=tn,origin_um=[0,0],orient='R0')];a['ports']=[];a['lanes']=[]
 P=S.Plan(a,path=source);r=F.reservation(P,tn);dest=O/('native_coupon_'+tn);dest.mkdir(exist_ok=True)
 (dest/'partition_ft_reservation.json').write_text(json.dumps(r,indent=1)+'\n');(dest/'partition_ft_reservation.tcl').write_text(F.tcl(r));(dest/'tracks.tcl').write_text(GP.make_tracks_tcl(P));(dest/'pdn_source.tcl').write_text(GP.PDN+F.tcl(r))
 rows={};cut=100.;w,h=t['outline_um'];_,regs=D.band_region_adjust(P,.75);dieblock=D.band_share_obs(P,regs)
 for L,width,spacing,pitch,offset in [('M5',.12,.072,4.32,2.064),('M7',.288,.096,8.64,4.128)]:
  obs=[(x0,x1) for x0,y0,x1,y1 in D.die_core_rects(P,L) if y0<cut<y1]
  obs += [(x0,x1) for layer,x0,y0,x1,y1 in dieblock if layer==L and y0<cut<y1]
  free=subtract([(0,w)],obs)
  pg=[]
  # Model paired VDD/VSS metal from exact native PDN source constants.
  # Uses offset as stripe center, matching plan PG conventions.
  # Actual native pdngen/cut/via geometry is deliberately still OPEN.
  for k in range(-2,math.ceil(w/pitch)+2):
   for shift in [0,width+spacing]:
    x=offset+k*pitch+shift
    pg.append((x-width/2,x+width/2))
  after=subtract(free,pg);trackpitch=P.layers[L]['pitch_um']
  halo=.072+P.layers[L].get('width_um',.024 if L=='M5' else .032)/2
  pg_halo=[(x-halo,y+halo) for x,y in pg]
  after_halo=subtract(free,pg_halo)
  points=[P.layers[L]['offset_um']+i*trackpitch for i in range(math.ceil(w/trackpitch))]
  center_tracks=sum(any(x0+1e-8<x<x1-1e-8 for x0,x1 in after_halo) for x in points)
  rows[L]=dict(PG_spacing_um=.072,PG_and_signal_halfwidth_halo_um=halo,PG_spacing_tracks=center_tracks,PG_spacing_open_um=sum(b-a for a,b in after_halo),native_PDN=dict(width_um=width,spacing_um=spacing,pitch_um=pitch,offset_um=offset),cut_y_um=cut,physical_die_intervals_um=free,open_um=sum(b-a for a,b in free),tracks_before_PG=sum(b-a for a,b in free)/trackpitch,PG_metal_only_tracks=sum(b-a for a,b in after)/trackpitch,PG_metal_intervals_um=union(pg))
 native=[]
 for c in t['hard_cores']:
  lef=D.ROOT/c['lef'];obs=lef.read_text().split('  OBS\n')[-1];layers={L:[list(map(float,m)) for m in re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',section.split('LAYER')[0])] for L,section in re.findall(r'LAYER\s+(M[567])\s*;(.*?)(?=LAYER|END\n)',obs,re.S)}
  native.append(dict(inst=c['inst'],origin_um=c['origin_um'],outline_um=c['outline_um'],lef=str(lef),OBS=layers))
 summary['coupons'][tn]=dict(reservation_rectangles=len(r['rectangles_um']),layers=rows,native_macros=native,nominal_tracks=sum(x['tracks_before_PG'] for x in rows.values()),PG_metal_only_tracks=sum(x['PG_metal_only_tracks'] for x in rows.values()),PG_spacing_tracks=sum(x['PG_spacing_tracks'] for x in rows.values()))
(O/'native_coupon_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
for tn,c in summary['coupons'].items():print(tn,c['reservation_rectangles'],c['nominal_tracks'],c['PG_metal_only_tracks'],c['PG_spacing_tracks'])
# Smallest 1%-step additional allocation in this R0 source coupon after PG
# spacing and native routing-grid quantization. Still not a route result.
search={}
for tn,start,target in [('kv3_hgi_v3',40,3623/.6),('kv3_hgi_v8',61,5055/.6)]:
 a=copy.deepcopy(raw);t=a['partition_types'][tn];t['die_ft_bands']=copy.deepcopy(delta[tn]);a['die']['outline_um']=t['outline_um'];a['partition_types']={tn:t};a['partitions']=[dict(name='coupon',type=tn,origin_um=[0,0],orient='R0')];a['ports']=[];a['lanes']=[]
 P=S.Plan(a,path=source);w,h=t['outline_um'];samples=[]
 for pct in range(start,101):
  for band in t['die_ft_bands']:
   if (tn=='kv3_hgi_v3') or band['layers']==['M5']:band['die_share']=pct/100
  _,regs=D.band_region_adjust(P,.75);dieblock=D.band_share_obs(P,regs);count=0
  for L,width,spacing,pitch,offset in [('M5',.12,.072,4.32,2.064),('M7',.288,.096,8.64,4.128)]:
   obs=[(x0,x1) for x0,y0,x1,y1 in D.die_core_rects(P,L) if y0<100<y1]
   obs.extend((x0,x1) for layer,x0,y0,x1,y1 in dieblock if layer==L and y0<100<y1)
   half=P.layers[L].get('width_um',.024 if L=='M5' else .032)/2
   for k in range(-2,math.ceil(w/pitch)+2):
    for shift in [0,width+spacing]:
     x=offset+k*pitch+shift;obs.append((x-width/2-.072-half,x+width/2+.072+half))
   free=subtract([(0,w)],obs);trackpitch=P.layers[L]['pitch_um'];offset_track=P.layers[L]['offset_um']
   # Count grid centers in each disjoint interval, excluding boundary equality.
   count+=sum(max(0,math.ceil((b-offset_track-1e-8)/trackpitch)-math.floor((a-offset_track+1e-8)/trackpitch)-1) for a,b in free)
  samples.append(dict(share_pct=pct,tracks=count))
  if count>=target:break
 search[tn]=dict(required_tracks=target,first_sufficient_grid_share_pct=pct,modeled_tracks=count,samples=samples,qualification='R0 native-source PG-spacing lower-bound only; vias, global map phase and localroute OPEN')
summary['grid_allocation_search']=search
(O/'native_coupon_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('Allocation search:',{k:(v['first_sufficient_grid_share_pct'],v['modeled_tracks']) for k,v in search.items()})
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Patch
fig,ax=plt.subplots(figsize=(14,5));row=0
for tn in ['kv3_hgi_v3','kv3_hgi_v8']:
 for L in ['M5','M7']:
  q=summary['coupons'][tn]['layers'][L]
  ax.add_patch(Rectangle((220,row-.35),130,.7,color='#dddddd'))
  # True native core edge: first column ends233.28; second starts336.96.
  ax.add_patch(Rectangle((233.28,row-.35),103.68,.7,color='white'))
  for a,b in q['physical_die_intervals_um']:
   if b>220 and a<350:ax.add_patch(Rectangle((a,row-.3),b-a,.6,color='#69c7df'))
  for a,b in q['PG_metal_intervals_um']:
   if b>220 and a<350:
    halo=q['PG_and_signal_halfwidth_halo_um'];ax.add_patch(Rectangle((a-halo,row-.3),b-a+2*halo,.6,color='#f3a747'));ax.add_patch(Rectangle((a,row-.3),b-a,.6,color='#b61f2d'))
  ax.text(219,row,('EN' if tn.endswith('v3') else 'WN')+' '+L,ha='right',va='center');row+=1
ax.set(xlim=(220,350),ylim=(-.6,3.6),xlabel='Type-frame x (um); representative y =100 um',yticks=[],title='Native OBS-clipped continuous gap: actual generated ownership strips and native PDN source model\nPREP only: no OpenROAD execution; PG/via geometry and global placement phases remain open')
ax.legend(handles=[Patch(color='#ddd',label='Native macro M5/M7 OBS'),Patch(color='#69c7df',label='Die-owned strips'),Patch(color='#b61f2d',label='PG metal model'),Patch(color='#f3a747',label='PG spacing + signal half-width')],loc='upper center',bbox_to_anchor=(.5,-.12),ncol=4)
fig.subplots_adjust(bottom=.25,left=.1);fig.savefig(O/'native_gap_PG_coupon.png',dpi=130)
