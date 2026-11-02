from pathlib import Path
import sys,json,re,hashlib
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent;D=g.Design(str(P/'inputs/geom.tsv'));z=json.load(open(P/'current_packer_witness.json'));loc={int(k):v for k,v in z['positions'].items()};bus='i_kvpc_Q_N_o_next';st=next(p for p in D.pins if p['name']=='cland_fstart_in_'+bus+'[0]');ck=next(p for p in D.pins if p['name']=='fclk_in_'+bus+'[0]')
ctl=[];cd=[]
for k,b in loc.items():
 x=(b[0]+b[2])/2;y=(b[1]+b[3])/2;cd.append(abs(ck['x']-x)+abs(ck['y']-y));n=D.cells[k][6].replace(chr(92),'')
 if not re.search(r's_d\[\d+\]\[\d+\]|dch\[\d+\].u_dsel/y',n):ctl.append(abs(st['x']-x)+abs(st['y']-y))
z['control_ff_START_envelope_um']=max(ctl);z['all_ffs_forwarded_clock_envelope_um']=max(cd);z['helper_sha256']=hashlib.sha256(Path('/home/ubuntu/OpenTallas/tools/die_plan/landing_placement.tcl').read_bytes()).hexdigest();z['actual_rvt_lef_sha256']=hashlib.sha256((P/'inputs/asap7_R_actual.lef').read_bytes()).hexdigest();(P/'current_packer_witness.json').write_text(json.dumps(z,indent=2)+'\n')
fig,axs=plt.subplots(1,2,figsize=(15,5),sharex=True,sharey=True)
for ax,actual,title in zip(axs,[True,False],['Actual failed all-cell FIRM band','Current approved FF-only Tcl packer: geometry adapter']):
 for k,c in D.cells.items():
  isring='u_cland_'+bus+'/' in c[6];b=list(c[2:6]) if actual or k not in loc else loc[k]
  if b[2]<1280 or b[0]>1450 or b[3]<0 or b[1]>125:continue
  if not actual and isring and k not in loc:continue
  ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],facecolor=('#c52962' if k in loc else '#e8ad4a' if isring else '#7f939a'),edgecolor='none',alpha=.8 if k in loc else .4))
 ax.add_patch(Rectangle((1326.24,86.4),86.4,34.56,fill=False,edgecolor='#127cb8',lw=2))
 for p in D.pins:
  if p['name'].startswith(bus+'['):ax.plot(p['x'],p['y'],'k.',ms=2)
 ax.plot(ck['x'],ck['y'],'*',color='green',ms=12);ax.set(xlim=(1280,1450),ylim=(-5,125),xlabel='x (um)',title=title);ax.grid(alpha=.15)
axs[0].set_ylabel('y (um)');fig.suptitle('kv3_hroot Q_N —1585 exact FFs, native pinned LEF, current PINSLOT +resize +singleton START\n1200storage pinreach125.631um; control START%.3fum;0additional r2r failures; PREP only / no OpenDB / no PG or route credit'%max(ctl));fig.tight_layout();fig.savefig(P/'current_packer_review.png',dpi=160)
print('control START',max(ctl),'clock allFF envelope',max(cd))
