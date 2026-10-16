import json,re,hashlib
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
x=json.load(open('results/rtl/s81_cfifo_native_1016/cf0_c21h_peer_geometry.json'))
p=Path('physical/s81_die_pins/cfifo_x2pair/dsfd_cfifo.tcl');t=p.read_text()
st={a[0]:((a[1]+a[3])/2+4266.432,(a[2]+a[4])/2+3324.240) for a in reversed(x['dsfd_sstn_e0c0sinf_x2']['pins'])}
old={a[0]:((a[1]+a[3])/2+4229.712,(a[2]+a[4])/2+3220.560) for a in x['dsfd_cfifo']['pins']}
new={a:(float(b)+4229.712+103.68,float(c)+3220.560+43.176) for a,b,c in re.findall(r'place_pin -pin_name \{(x2\[\d+\])\} -layer M5 -location \{([\d.]+) ([\d.]+)\}',t)}
fig,axs=plt.subplots(2,1,figsize=(12,7),sharex=True,sharey=True)
for ax,src,title in zip(axs,[old,new],['Bound c21h: legacy 0.048 um pitch, worst jog 25.680 um','Proposed rebind: 0.096 um pitch, zero x jog']):
 ax.add_patch(Rectangle((4229.712,3220.560),431.976,95.016,color='#dce7fa',ec='navy')) if src is old else ax.add_patch(Rectangle((4333.392,3263.736),280.8,51.84,color='#dce7fa',ec='navy'))
 ax.add_patch(Rectangle((4266.432,3324.240),172.776,30.216,color='#e2f0d9',ec='darkgreen'))
 for k in range(0,536,16):
  a=src[f'x2[{k}]'];b=st[f'x2i[{k}]'];ax.plot([a[0],a[0],b[0]],[a[1],b[1],b[1]],lw=.8,color='#c85625' if src is old else '#16854c')
 ax.set_title(title);ax.text(4336,3304,'cf0.x2 north face',fontsize=10);ax.text(4310,3338,'t0_0.x2i south face',fontsize=10)
 ax.set_xlim(4300,4448);ax.set_ylim(3297,3347);ax.set_aspect('equal');ax.grid(alpha=.2);ax.set_ylabel('Die y (um)')
axs[1].set_xlabel('Die x (um)');fig.suptitle('Actual c21h cf0 → slot-0 x2 station pin context; rebind proposal, not routed proof')
fig.tight_layout(); out=Path('results/rtl/s81_cfifo_native_1016');fig.savefig(out/'cf0_x2_peer_context.png',dpi=150)
shifts=[abs(new[f'x2[{k}]'][0]-st[f'x2i[{k}]'][0]) for k in range(536)]
rec=dict(scope='c21h cf0/t0_0 actual LEF+DEF; proposed committed cfifo Tcl + requested origin shift',source='/srv/opentallas-scratch/claude/s81-die-iter/c21h/a_real/{elements.lef,floorplan_placed.def}',old_pitch_um=.048,new_pitch_um=.096,old_max_x_jog_um=max(abs(old[f'x2[{k}]'][0]-st[f'x2i[{k}]'][0]) for k in range(536)),new_max_x_jog_um=max(shifts),pins=536,new_pin_tcl_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),notes='Actual post-rebind GEN and routing must still confirm all128 homes, orientation, clock-root wiring and incident paths.')
(out/'cf0_x2_peer_context.json').write_text(json.dumps(rec,indent=2)+'\n')
print(json.dumps(rec))
