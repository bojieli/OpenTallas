from pathlib import Path
import json,re,sys,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
B=Path(sys.argv[1]);K=B/'kit';label=sys.argv[2] if len(sys.argv)>2 else'GENERATED PHYSICAL INTENT — not placed';cfg=(K/'config.mk').read_text();die=list(map(float,re.search(r'^export DIE_AREA = (.*)$',cfg,re.M)[1].split()));core=list(map(float,re.search(r'^export CORE_AREA = (.*)$',cfg,re.M)[1].split()));io=(K/'io.tcl').read_text();ps=[]
for m in re.finditer(r'place_pin -pin_name (?:\{([^}]+)\}|(\S+)) -layer (\w+) -location \{([\d.-]+) ([\d.-]+)\}',io):ps.append((m[1]or m[2],m[3],float(m[4]),float(m[5])))
fig,a=plt.subplots(figsize=(8,14));a.add_patch(Rectangle((0,0),die[2],die[3],fill=False));a.add_patch(Rectangle((core[0],core[1]),core[2]-core[0],core[3]-core[1],fill=False,ec='gray',ls=':'))
for l,c in {'M4':'#ad69b0','M5':'#3c9d55','M6':'#c18437','M7':'#3b68ba'}.items():
 z=[p for p in ps if p[1]==l];a.scatter([x[2] for x in z],[x[3] for x in z],s=.9,c=c,label=l)
for m in re.finditer(r'place_macro -macro_name \{([^}]+)\} -location \{([\d.-]+) ([\d.-]+)\}',(K/'macro_place.tcl').read_text()):
 x,y=float(m[2]),float(m[3]);a.add_patch(Rectangle((x-4.32,y-4.32),130.488,71.592,fill=False,ec='gray',ls='--'));a.add_patch(Rectangle((x,y),121.848,62.952,fc='#ccc',ec='black'));a.text(x+60,y+31,m[1].split('.')[-1],ha='center')
for m in re.finditer(r'^  \{u_cland_(\S+) \{([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)\}',(K/'landing_placement.tcl').read_text(),re.M):
 x,y,u,v=map(float,m.groups()[1:]);a.add_patch(Rectangle((x,y),u-x,v-y,fc='green',ec='green',alpha=.08));a.text((x+u)/2,(y+v)/2,m[1],fontsize=5,ha='center')
rt=[]
for m in re.finditer(r'^rtr_place (\S+) \{([^}]+)\} ([\d.-]+) ([\d.-]+)',(K/'reset_tree.tcl').read_text(),re.M):rt.append((m[1],m[2],float(m[3]),float(m[4])))
a.scatter([x[2] for x in rt],[x[3] for x in rt],s=4,c='red',marker='+',label='actual emitted reset/start target sites')
for z in ps:
 if z[0] in ('arst_n','start_i'):a.annotate(z[0],(z[2],z[3]),xytext=(-65,-5 if z[0]=='arst_n' else 15),textcoords='offset points',fontsize=7,color='red',arrowprops={'arrowstyle':'->','color':'red'})
a.set(xlim=(-9,die[2]+9),ylim=(-9,die[3]+9),aspect='equal',xlabel='um',ylabel='um',title=label+'\n'+str(len(ps))+'actual emitted contacts; CORE inset4.32um\nOnly emitted decks shown; estimated whole-bank windows are NOT enforced regions')
a.legend(fontsize=6,loc='lower right');fig.tight_layout();fig.savefig(B/'generated_physical_intent.png',dpi=150)
print('RENDER',len(ps),'contacts',len(rt),'reset/start placements')
