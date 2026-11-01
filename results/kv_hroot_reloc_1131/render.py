import json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/die_plan'));import schema as S
p=json.load(open(sys.argv[1]));variant=sys.argv[2];out=Path(sys.argv[3]);out.parent.mkdir(parents=True,exist_ok=True)
ts=p['partition_types'];P=S.Plan(p,root/'physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json')
fig,axs=plt.subplots(2,2,figsize=(16,12));col={'i_seq__g_fan_N__u_fan_kc':'#d95f02','i_fch_pc_Q_N_q':'#1b9e77','i_kvpc_Q_N_pc__fo':'#7570b3'}
def rect(ax,r,**kw):ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],**kw))
def frame(ax,t,title):
 w,h=t['outline_um'];rect(ax,[0,0,w,h],fill=False,edgecolor='black');ax.set(xlim=(-20,w+20),ylim=(-20,h+20),title=title,xlabel='um',ylabel='um');ax.set_aspect('equal')
a=axs[0,0];t=ts['kv3_hroot'];frame(a,t,'hroot '+variant+': paired landing relocation, existing registers')
for n,b in t['clock']['landing_contract']['bands'].items():
 c=col.get(n,'#aaaaaa');rect(a,b['rect_um'],facecolor=c,edgecolor=c,alpha=.6 if n in col else .25)
 if n in col:a.text((b['rect_um'][0]+b['rect_um'][2])/2,b['rect_um'][3]+10,n.replace('i_','',1),fontsize=7,ha='center',rotation=25)
pts=list(t['relay_sites'].values());a.scatter([x[0] for x in pts],[x[1] for x in pts],s=.7,c='steelblue',alpha=.25)
b=t['clock']['landing_contract']['bands']['i_kvs_ctl_o_hroot_Q'];a.annotate('hroot_Q: existing FF form;\nremove +x cursor to use y pin slots',xy=(1860,555),xytext=(1150,160),fontsize=8,arrowprops={'arrowstyle':'->'})
for n,x,y in S.tap_grid(P,'kv3_hroot'):a.plot(x,y,'kx',markersize=3,alpha=.5)
a=axs[0,1];t=ts['kv3_pc_v3'];frame(a,t,'PCv3 FT1: same seven stages, macro-clear detour')
for c in t['hard_cores']:
 x,y=c['origin_um'];w,h=c['outline_um'];rect(a,[x,y,x+w,y+h],facecolor='#dddddd',edgecolor='black');a.text(x+w/2,y+h/2,c['inst'],ha='center',va='center')
f=next(x for x in t['ft_slots'] if x['name']=='ft1');points=f['regs_um'][:]
# Canonical WS frame: output ft1_o is the hroot S input window.
p0=next(x for x in p['ports'] if x['src']['part']=='pc_WS_7' and x['src']['bus']=='ft1_o');points=points+[[sum(p0['window_um'])/2-864,1520.64]]
a.plot([q[0] for q in points],[q[1] for q in points],'-o',c='#1b9e77',markersize=4)
for i,q in enumerate(points):a.text(q[0]+10,q[1],str(i),fontsize=8)
a.text(505,1390,'Max new FT1 hop 396.58um\nNo extra stages',fontsize=8)
for ax,tn in zip(axs[1],['kv3_hub_Wo','kv3_hub_Eo']):
 t=ts[tn];frame(ax,t,tn+': source export pins and existing grid taps')
 for c in t['hard_cores']:
  x,y=c['origin_um'];w,h=c['outline_um'];rect(ax,[x,y,x+w,y+h],facecolor='#ddd',edgecolor='black')
 taps={n:(x,y) for n,x,y in S.tap_grid(P,tn)}
 for n,(x,y) in taps.items():ax.plot(x,y,'kx',markersize=4)
 for z in t['clock']['landing_contract']['pins']:
  if z['name'] in ['fclk_out_o_seq__g_fan_N__u_fan_kc','fclk_out_o_seq__g_fan_N__u_fan_kc_d1']:
   x,y=z['xy_um'];tx,ty=taps[z['source_clock_tap']];ax.plot([x,tx],[y,ty],'-o',c='#d95f02');ax.text((x+tx)/2,(y+ty)/2,f'{abs(x-tx)+abs(y-ty):.1f}um',fontsize=8)
 ax.text(310,800,'Existing source legs improve ~950 to805um;\nclock trunks/arrival remain held for CTS/STA',fontsize=8)
fig.suptitle('KV hroot zero-cycle relocation '+variant+' — prototype, not routed/qualified',fontsize=14);fig.tight_layout();fig.savefig(out,dpi=150);print(out)
