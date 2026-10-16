#!/usr/bin/env python3
"""Concrete provisional local slots: actual named bits, grid contacts, PG exclusion."""
import hashlib,json,math
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'results/arch/qwen_vm_residual_1015/local_leaf_contract_0253';O.mkdir(exist_ok=True)
W=H=64.8;pitch=.048;offset=.012;PG=[.300+2.7*k+delta for k in range(25)for delta in [0,.192]]
def bus(n,w):return [f'{n}[{i}]'for i in range(w)]
def grid(x):return round(offset+round((x-offset)/pitch)*pitch,6)
clk=grid(W/2)
def sides(ns,face):
 step=.192;start=grid((H-(len(ns)-1)*step)/2)
 return [{'name':n,'face':face,'layer':'M4','xy':[0 if face=='W'else W,round(start+i*step,6)],'size':[.144,.024]}for i,n in enumerate(ns)]
def south(ns):
 avail=[round(offset+pitch*k,6)for k in range(math.ceil(W/pitch))if 4.32<=offset+pitch*k<=W-4.32 and abs(offset+pitch*k-clk)>2.16 and min(abs(offset+pitch*k-g)for g in PG)>=.120-1e-9]
 sel=([min(avail,key=lambda x:abs(x-clk))]if len(ns)==1 else [avail[round(i*(len(avail)-1)/(len(ns)-1))]for i in range(len(ns))])
 assert len(set(sel))==len(ns)
 return [{'name':n,'face':'S','layer':'M5','xy':[x,0],'size':[.024,.144]}for n,x in zip(ns,sel)]
def emit(name,top,params,nff,nrep,w,e,s):
 pins=sides(w,'W')+sides(e,'E')+south(s)+[{'name':'ck','face':'S','layer':'M5','xy':[clk,0],'size':[.024,.144]}]
 assert len({p['name']for p in pins})==len(pins)
 assert min(abs(clk-g)for g in PG)>=.120
 for p in pins:
  assert all(-1e-8<=v<=W+1e-8 for v in p['xy'])
  if p['layer']=='M5':assert min(abs(p['xy'][0]-g)for g in PG)>=.120-1e-9
  v=p['xy'][1]if p['layer']=='M4'else p['xy'][0];assert abs((v-offset)/pitch-round((v-offset)/pitch))<1e-6
 body='\n'.join(f"place_pin -pin_name {{{p['name']}}} -layer {p['layer']} -location {{{p['xy'][0]:.6f} {p['xy'][1]:.6f}}} -pin_size {{{p['size'][0]} {p['size'][1]}}}"for p in pins)+'\n';(O/(name+'.tcl')).write_text('# PROVISIONAL LOCAL die-owner slot; exact named bits for review, no global-home grant.\n'+body)
 report=dict(schema='opentallas.qwen.vm-local-leaf-candidate.v1',name=name,top=top,params=params,outline_um=[W,H],replicas=nrep,source_ff_bits=nff,signal_pins=len(pins),clock_pin=[clk,0],layer_cap='M5',source_sha256={f:hashlib.sha256((R/f).read_bytes()).hexdigest()for f in ['rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv']+(['rtl/qwen_sys/vm_native_physical_20261015/qvm_return_plane_pin_native.sv']if name=='return_plane'else[])},pins=pins,PG=dict(layer='M5',pitch=2.7,width=.12,spacing=.072,offset=.300,contact_center_clearance_um=.120,clock_reserved_halfspan_um=2.16),capacity=dict(M4_face_available_tracks=int((H-8.64)/pitch),M4_W_bits=len(w),M4_E_bits=len(e),M4_W_raw_cut=len(w)/int((H-8.64)/pitch),M4_W_25pct_derated_cut=len(w)/(int((H-8.64)/pitch)*.75),two_track_contact_slots=int((H-8.64)/(2*pitch)),W_two_track_contact_fraction=len(w)/int((H-8.64)/(2*pitch))),qualification='Provisional local slot from compute die owner, no whole-parent homes or physical qualification. Pinflop/hold/actual PG/vias/CTS/native220/190/80/route remain required.')
 (O/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n');return report
ret=emit('return_plane','qvm_return_plane_pin_native',dict(ELEMS=177808,AW=24,SW=64,NRBS=16,MUT=0),668,96,bus('d',256),bus('q',64),bus('a5',24)+bus('a6',24)+bus('a7',24)+['v5','v6','v7','stride1'])
ctl=emit('read_control_ro6','ot_qfd_vm_su_read_control',dict(AW=24,SW=64,NRBS=16,LAWS=10,SX=12),699,3,['re0','re1']+bus('a0',24)+bus('a1',24),bus('sb_re',16)+bus('sb_ra',160)+['d2_bad','ov3','ov5','ov6','ov7','osi7']+bus('oa5',24)+bus('oa6',24)+bus('oa7',24),['rst_n'])
assert ret['signal_pins']==397 and ctl['signal_pins']==306
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,axs=plt.subplots(1,2,figsize=(13,7))
for ax,row in zip(axs,[ret,ctl]):
 ax.add_patch(Rectangle((0,0),W,H,facecolor='#f3f7fa',edgecolor='black'))
 for x in PG:
  if x<W:ax.add_patch(Rectangle((x-.06,0),.12,H,color='#e6c9ba',alpha=.7))
 for p in row['pins']:
  x,y=p['xy'];dx,dy=p['size'];ax.add_patch(Rectangle((x-dx/2,y-dy/2),dx,dy,color='#c83c40'if p['name']=='ck'else'#247ba0'))
 ax.scatter([clk],[0],s=55,c='#c83c40');ax.annotate('ck (32.412,0), M5\n2.16um reserved each side',(clk,0),xytext=(20,8),arrowprops={'arrowstyle':'->'},fontsize=8)
 for face,x,y in [('W',-5,H/2),('E',W+5,H/2),('S',W/2,-6)]:ax.text(x,y,f"{face}: {sum(p['face']==face for p in row['pins'])}",ha='center',fontsize=8)
 ax.set(xlim=(-8,W+8),ylim=(-9,H+4),xlabel='um',ylabel='um',title=f"{row['name']}: {row['source_ff_bits']} FF, {row['signal_pins']} pins\n64.8 square, cap M5, PG contacts excluded");ax.set_aspect('equal')
fig.suptitle('PROVISIONAL local pin/slot candidates; no placement/CTS/route qualification',fontsize=11);fig.tight_layout();fig.savefig(O/'local_leaf_pins.png',dpi=150)
print(json.dumps({'return_plane_pins':397,'read_control_pins':306,'ck_x':clk,'area99_mm2':99*W*H/1e6,'W_face_derated_cut':ret['capacity']['M4_W_25pct_derated_cut']}))
