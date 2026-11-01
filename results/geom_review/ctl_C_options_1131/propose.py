from pathlib import Path
import json,math,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).parent
pins=json.loads((R/'pins.json').read_text());W0=H0=371.52;MW,MH=52.296,39.960;HALO=4.32;AREA=22127.9
names=['u_leaf.u_wprg.g_sr.genblk1.g_s2.u_rows_b','u_leaf.u_lprg.genblk1.g_s2.u_rowb_b','u_leaf.u_lprg.genblk1.g_s2.u_rowa_b']
def snap(v,phase):return round(phase+round((v-phase)/.048)*.048,6)
def proposals(tag,w,h):
 out=R/tag;out.mkdir(exist_ok=True);new=[dict(p) for p in pins]
 for face in ('W','E','N','S'):
  layer='M4' if face in ('W','E') else 'M5';items=sorted([p for p in new if p['face']==face],key=lambda p:p['y'] if face in ('W','E') else p['x'])
  length=h if face in ('W','E') else w;coords=[snap(4.32+i*(length-8.64)/(len(items)-1),.024) for i in range(len(items))]
  assert min(b-a for a,b in zip(coords,coords[1:]))>= (.096 if face in ('W','E','N') else .048)-1e-6
  for p,c in zip(items,coords):
   p['x'],p['y']=(0,c) if face=='W' else ((w,c) if face=='E' else ((c,h) if face=='N' else (c,0)))
 for p in new:
  if p['face']=='interior':p['x']=round(w/2+(-.024 if p['bus']=='ck' else .36),6);p['y']=h/2
 ident=lambda p:(p['bus'],p['bit']);assert {ident(p) for p in new}=={ident(p) for p in pins}
 b=[];ys=[snap(20,.012),snap((h-MH)/2,.012),snap(h-20-MH,.012)]
 for row,y in enumerate(ys):
  for col,x in enumerate((snap(12.96,.012),snap(w-12.96-MW,.012))):
   b.append(dict(inst=names[row]+str(col),master='ctl_sram_1r1w_64x128_p192',x=x,y=y,w=MW,h=MH,orient='MY' if col==0 else 'R0',group=('writer','row_b','row_a')[row],bank=col))
 for i,a in enumerate(b):
  assert a['x']-HALO>=4.32 and a['y']-HALO>=4.32 and a['x']+MW+HALO<=w-4.32 and a['y']+MH+HALO<=h-4.32
  for c in b[i+1:]:assert a['x']+MW+HALO<=c['x']-HALO or c['x']+MW+HALO<=a['x']-HALO or a['y']+MH+HALO<=c['y']-HALO or c['y']+MH+HALO<=a['y']-HALO
 xgap=b[1]['x']-(b[0]['x']+MW)-2*HALO;ygap=min(ys[i+1]-ys[i]-MH-2*HALO for i in (0,1))
 clock=(w/2-.024,h/2);clockreach=max(abs((a['x']+MW-.012 if a['orient']=='MY' else a['x']+.012)-clock[0])+abs(a['y']+.780-clock[1]) for a in b)
 model=dict(name=tag,outline_um=[w,h],nominal_area_occupancy=AREA/(w*h),source_cell_area_um2=AREA,stdcell_area_um2=9589.44,macro_area_um2=12538.5,macro_count=6,macro_size_um=[MW,MH],halo_um=HALO,pins=len(new),face_layer_counts={f'{f}/{l}':sum(p['face']==f and p['layer']==l for p in new) for f,l in [('W','M4'),('E','M4'),('N','M5'),('S','M5'),('interior','M5')]},min_M4_face_height_um=2523*.096+8.64,vertical_signal_channel_um=xgap,horizontal_signal_channel_um=ygap,track_pitch_um=.048,capacity_reserve_fraction=.35,vertical_reserved_capacity_tracks=math.floor(xgap/.048*.65),horizontal_reserved_capacity_tracks=math.floor(ygap/.048*.65),local_bank_bundle_bound=544,capacity_scope='one bank pair:256read+256write+24address+8control; local read-consumer logic stays between row_a/row_b; not a full-router proof',clock_max_manhattan_um=clockreach,wire_clock_estimate_ps=None,clock_estimate_basis='distance-only placement bound; shared RC/CTS insertion and OCV/droop estimate still required before physical build',parent_slot=dict(inst='kvs_ctl',module='qkd_kvs_ctl',origin_um=[898.56+(W0-w)/2,138.24+(H0-h)/2],outline_um=[w,h],orient='R0'),global_ck_xy_unchanged=[1084.296,324.0],blocks=b,verdict='PLANNING-PASS-COND',route_permission=False,held=['mapped functional EQ','exact parent plan/pin event review','actual placement/GRT/clock/reset/PDN/timing'],canonical_changed=False)
 assert min(model['vertical_reserved_capacity_tracks'],model['horizontal_reserved_capacity_tracks'])>=544
 (out/'proposal.json').write_text(json.dumps(model,indent=2)+'\n');(out/'kit_pins.json').write_text(json.dumps(new,indent=1)+'\n')
 por=[]
 for p in new:
  q=dict(name=p['bus'] if p['bit'] is None else f"{p['bus']}[{p['bit']}]",layer=p['layer'],x=p['x'],y=p['y'])
  if p['face']=='W':q['x']=.042
  if p['face']=='E':q['x']=w-.042
  if p['face']=='N':q['y']=h-.096
  if p['face']=='S':q['y']=.096
  if p['face']=='interior':q.update({k:p[k] for k in ('size','clock') if k in p})
  por.append(q)
 (out/'plan_pins.json').write_text(json.dumps(dict(schema='opentallas.die_plan.core_pins.v1',core='qkd_kvs_ctl',frame=f'core R0 outline{w}x{h}',source='PROPOSAL from exact C6849pin interface; ordered face repack; not canonical/adopted',pins=por),indent=1)+'\n')
 t=['# Proposed FIRM SRAM sites; held until functional gate and plan event review.','set blk [ord::get_db_block]','set dbu [$blk getDbUnitsPerMicron]']
 for a in b:
  t+=['set hit {}',f'foreach i [$blk getInsts] {{ if {{[$i getName] eq {{{a["inst"]}}}}} {{lappend hit $i}} }}',f'if {{[llength $hit] != 1}} {{error {{{a["inst"]}: expected one current SRAM}}}}','set i [lindex $hit 0]',f'$i setOrient {a["orient"]}','$i setLocation 0 0','set bb [$i getBBox]',f'$i setLocation [expr {{round({a["x"]}*$dbu)-[$bb xMin]}}] [expr {{round({a["y"]}*$dbu)-[$bb yMin]}}]','$i setPlacementStatus FIRM']
 (out/'macro_place.tcl').write_text('\n'.join(t)+'\n')
 return model,new
A,ap=proposals('A_compact',181.44,267.84);B,bp=proposals('B_channels',198.72,267.84)
fig,axs=plt.subplots(1,3,figsize=(18,10),gridspec_kw={'width_ratios':[411.52,221.44,238.72]},layout='constrained');colors={'M4':'#1766a3','M5':'#e38c20'}
for ax,model,ps,title in [(axs[0],None,pins,'Current C kit:371.52square'),(axs[1],A,ap,'A:compact181.44x267.84'),(axs[2],B,bp,'B:channels198.72x267.84')]:
 w,h=model['outline_um'] if model else(W0,H0);ax.add_patch(Rectangle((0,0),w,h,fill=False,lw=1.5));ax.set_aspect('equal');ax.set_xlim(-20,w+20);ax.set_ylim(-45,390);ax.set_title(title,fontsize=12)
 for layer,color in colors.items():
  pp=[p for p in ps if p['layer']==layer];ax.scatter([p['x'] for p in pp],[p['y'] for p in pp],s=1,c=color,alpha=.75,label=layer+' pins')
 for x in range(int(w/4.32)):
  ax.plot([2.064+4.32*x]*2,[4.32,h-4.32],color='#a19bc4',alpha=.14,lw=.5)
 ck=next(p for p in ps if p['bus']=='ck');ax.scatter([ck['x']],[ck['y']],marker='*',s=100,c='#b3123e',zorder=6)
 if model:
  ax.add_patch(Rectangle((ck['x']-4.32,ck['y']-4.32),8.64,8.64,fill=False,edgecolor='#b3123e',linestyle=':',lw=.8))
  for a in model['blocks']:
   x,y=a['x'],a['y'];ax.add_patch(Rectangle((x-HALO,y-HALO),MW+2*HALO,MH+2*HALO,fill=False,edgecolor='#888',linestyle='--',lw=.8));ax.add_patch(Rectangle((x,y),MW,MH,color='#c7e3cf',ec='#32644c',lw=1));ax.text(x+MW/2,y+MH/2,f"{a['group']}\nb{a['bank']} {a['orient']}",ha='center',va='center',fontsize=8)
   cx=x+MW-.012 if a['orient']=='MY' else x+.012;cy=y+.780;ax.plot([ck['x'],cx],[ck['y'],cy],c='#b3123e',lw=.65,alpha=.6,linestyle=':');ax.scatter([cx],[cy],s=6,c='#b3123e')
   edge=7 if a['bank']==0 else w-7;gap_y=y-HALO-9 if a['group']=='row_a' else y+MH+HALO+9;mid=w/2+(-8.64 if a['bank']==0 else 8.64);ax.plot([cx,mid,mid,edge],[y+MH/2,y+MH/2,gap_y,gap_y],lw=.8,color='#5c7180',alpha=.8);ax.annotate('',xy=(edge,gap_y),xytext=(edge+(-6 if a['bank'] else 6),gap_y),arrowprops=dict(arrowstyle='->',lw=.8,color='#5c7180'))
  ax.text(w/2,-12,f"M4 faces2524each; pin minimum251um height\nchannels V{model['vertical_signal_channel_um']:.1f}/H{model['horizontal_signal_channel_um']:.1f}um; nominal occupancy{model['nominal_area_occupancy']:.1%}",ha='center',va='top',fontsize=8)
 else:ax.text(w/2,h*.64,'6 actual SRAMs\n52.296 x39.960um each\n4.32um halos\n\nNo fixed macro anchors in current kit\nAuto-placement remains unreviewed',ha='center',va='center',fontsize=10);ax.text(w/2,h*.29,'Actual mapped area22127.9um2\n6SRAMs +54680standard cells\n6849pins;2524perM4side\n\nArea sparsity alone does not permit\nshrinking below the pin/channel bound',ha='center',va='center',fontsize=9)
 ax.set_xlabel('um');ax.set_ylabel('um')
axs[0].legend(loc='lower right',fontsize=8);fig.suptitle('CTL current C boundary and two unsigned placement proposals — no P&R permission\nCommon um scale. SRAM pins face centre; bus sketches use open corridors. M5 PG grid/global clock site retained; dotted clocks are planning paths, not STA.',fontsize=13)
fig.savefig(R/'ctl_C_options.png',dpi=160)
(R/'review.json').write_text(json.dumps(dict(current_kit_hash='ba95e830b1c83d95',current_outline=[W0,H0],pins=len(pins),actual_synth_cells=54686,actual_synth_area_um2=AREA,options=[A,B],look_pending=True),indent=2)+'\n')
print(json.dumps({m['name']:{k:m[k] for k in ('outline_um','nominal_area_occupancy','vertical_reserved_capacity_tracks','horizontal_reserved_capacity_tracks','clock_max_manhattan_um')} for m in (A,B)}))
