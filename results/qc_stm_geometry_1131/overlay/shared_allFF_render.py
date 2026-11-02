import gzip,json,pathlib,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
B=pathlib.Path(__file__).resolve().parent;J=json.load(gzip.open(B/'shared_allFF_membership.json.gz'));T=json.load(open(B/'type_overlay.json'));fig,a=plt.subplots(figsize=(9,15));a.add_patch(Rectangle((0,0),311.04,613.44,fill=False,lw=1.5));cols={'FT':'#538acb','stream':'#b47abe','boundary':'#dbb45b','control':'red','tload':'orange'}
for z in J['regions']:
 r=z['window_um'];kind=z['kind'];c='#3b9d51' if kind=='existing_semantic_intent' else cols[kind];a.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc=c,alpha=.10 if kind=='existing_semantic_intent' else.35,ec=c,lw=.45))
 if z['name'].startswith('landing_'):a.text((r[0]+r[2])/2,(r[1]+r[3])/2,z['name'][8:]+'\n'+str(z['actual_FF_count'])+'FF / '+str(round(100*z['FF_area_fraction_in_own_window'],1))+'%',fontsize=5.5,ha='center')
for h in T['hard_cores']:
 x,y=h['origin_um'];a.add_patch(Rectangle((x-4.32,y-4.308),130.488,71.592,fill=False,ec='gray',ls='--',lw=.6));a.add_patch(Rectangle((x,y+.012),121.848,62.952,fc='#ddd',ec='black'));a.text(x+60,y+31,h['inst'].split('.')[-1],ha='center',fontsize=10)
for z in T['clock']['taps']:
 x,y=z['xy'];a.add_patch(Rectangle((x-2.16,y-2.16),4.32,4.32,fill=False,ec='blue',lw=.35));a.plot(x,y,'b.',ms=2.5)
for k,c in cols.items():a.plot([],[],color=c,lw=5,label=k)
a.plot([],[],color='#3b9d51',lw=5,label='existing semantic windows incl exact forwarded FFs');a.legend(fontsize=7,loc='lower right')
a.text(10,497,'Peak combined FF projection84.2%\nin1.184um² reset/core-relay overlap\nNonFF regional use unreserved',fontsize=5.5,color='red',ha='left')
a.set(xlim=(-8,319),ylim=(-8,622),aspect='equal',xlabel='um',ylabel='um',title='PRIVATE shared-soft-row STM proposal — NO GEN/CAD\n68,857 exact FFs once:52,609 local +16,248 forwarded (4,737.9168um²)\nAll finite regions fit conservative FF rows;10,691.5869um² nonFF area remains regional HOLD\n76 clock homes/sources, native ABI/cycles and4ROMs unchanged; not actual placement PASS')
fig.tight_layout();fig.savefig(B/'shared_allFF_proposal.png',dpi=150)
