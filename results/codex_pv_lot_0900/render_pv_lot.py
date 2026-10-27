import json,pathlib,sys,re,collections,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
C={'ts0':'#8c4bba','ts1':'#2171b5','ts2':'#e08214','ts3':'#238b45','y':'#d7191c','fault':'#d7191c','y_valid':'#d7191c','sf':'gray','join_go':'gray','clk':'black','rst_n':'black'}
fig,axs=plt.subplots(1,3,figsize=(17,5.3))
for ax,suf in zip(axs,('','_fMX','_fR180')):
 f='pv_join_pins'+suf+'.json';x=json.load(open(p/'pd/cores'/f));q=x['pins'];D=json.load(open(p/'pin_density.json'))[f]
 for k in range(31):ax.axvline(k*8.64,c='#ddd',lw=.35)
 for k in range(21):ax.axhline(k*8.64,c='#ddd',lw=.35)
 for b in C:
  pts=[z for z in q if z['name'].split('[')[0]==b]
  if pts:ax.scatter([z['x'] for z in pts],[z['y'] for z in pts],s=2 if b not in ('clk','rst_n') else 15,color=C[b],label=b)
 for x0 in (60.48,190.08):ax.add_patch(Rectangle((x0,82.08),8.64,8.64,fill=False,ec='royalblue',ls='--',lw=.8))
 ax.add_patch(Rectangle((125.28,82.08),8.64,8.64,fill=False,ec='black',ls='--',lw=.8))
 ax.set_xlim(-4,263);ax.set_ylim(-4,177);ax.set_aspect('equal');ax.set_title((suf or 'R0')+' numeric pin banks\n'+', '.join(k+':'+str(v['pins'])+'/'+str(v['peak_10um']) for k,v in D.items()),fontsize=9)
 ax.set_xlabel('um');ax.set_ylabel('um')
axs[0].legend(loc='center left',fontsize=7,markerscale=2)
fig.suptitle('PV join proposed 259.2 x 172.8 um; 4619 face pins; each 10um window <=60 pins\nRoot entries unchanged globally; 2x1 internal clock islands planned, no RTL/cycle change',fontsize=12);fig.tight_layout();fig.savefig(out/'pv_pin_windows.png',dpi=150)
P=json.load(open(p/'pd/hm_pv_lot.json'));t=P['partition_types']['kv3_pv_v12'];cl=json.load(open(p/'parent_clock_relocate.json'));mv=json.load(open(p/'ft_station_delta.json'))
fig,axs=plt.subplots(1,2,figsize=(17,6.8));mod='ot_qwen_tp8_pv_join_t'
for ax in axs:
 for h in t['hard_cores']:
  ox,oy=h.get('track_offset_um',[0,0]);x,y=h['origin_um'];x+=ox;y+=oy;w,hh=h['outline_um'];join=h['module']==mod
  ax.add_patch(Rectangle((x,y),w,hh,fc='#c6dbef' if join else '#c7e9c0',ec='#2171b5' if join else '#238b45',lw=1))
  if join:ax.add_patch(Rectangle((x+43.2,y),172.8,172.8,fill=False,ec='gray',ls='--'));ax.text(x+w/2,y+hh/2,h['inst'],ha='center',fontsize=7)
 for r in t['clock'].get('die_islands_um',[]):ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc='gray',alpha=.35))
 for r in cl:
  if r['type']=='kv3_pv_v12':
   x0,y0,x1,y1=r['rect_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='red',ec='red'));ax.scatter([(x0+x1)/2],[(y0+y1)/2],s=16,c='red')
 for r in mv:
  if r['type']=='kv3_pv_v12':ax.annotate('',xy=r['new'],xytext=r['old'],arrowprops=dict(arrowstyle='->',color='#aa00aa',lw=1));ax.scatter(*r['new'],s=12,c='#aa00aa')
 ax.set_aspect('equal');ax.set_xlabel('partition-local um');ax.set_ylabel('partition-local um')
axs[0].set_xlim(0,2160);axs[0].set_ylim(0,1520.64);axs[0].set_title('Worst FT variant kv3_pv_v12: parent lots\nBlue=new join body, dashed=old; green=pv_pair')
axs[1].set_xlim(1100,1525);axs[1].set_ylim(515,815);axs[1].set_title('Join group2 detail: vertical channels retained\nRed=parent clock cells needing relocation; purple=FT anchor moves')
fig.suptitle('GEOMETRY BLOCKED pending CLOCK-KV resite of 160 parent clock cells\nNew core bodies fit all lots; 28 existing FT anchors relocated, counts unchanged, max affected hop404.318um',fontsize=12);fig.tight_layout();fig.savefig(out/'pv_parent_lots.png',dpi=150)
