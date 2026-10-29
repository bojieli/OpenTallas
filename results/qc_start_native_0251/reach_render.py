"""Conservative row-envelope reach census and actual proposed perimeter view."""
import json,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-qc-start-native-0251');O=R/(sys.argv[1] if len(sys.argv)>1 else 'perimeter1');sys.path.insert(0,str(R/'src407/tools/die_plan'))
import schema as S
p=S.Plan(S.load('/srv/opentallas-scratch2/claude/codex-qc-1029/physical_event/plan_start_native_h800.json'))
doc=json.load(open(O/'emitted/start_stages.json'));stage={s['region']:s for s in doc['stages']};plan=json.load(open(R/'perimeter1/plan.json'))
gg=json.load(open(R/'perimeter1/stage_placement_overrides.json'));rows=[]
def rect(region,physical_part=None):
 if region in stage:return stage[region]['rect_um']
 region=physical_part or region
 part=p.parts[region];tn=part['type'];pin=next(q for q in p.types[tn]['clock']['landing_contract']['pins'] if q['name']=='cland_tstart_in')
 x,y=p.to_die(region,pin['xy_um']);return [x-.04,y-.4,x+.04,y+.4]
def hops(a,b):
 return max(abs(x-u)+abs(y-v) for x,y in [(a[0],a[1]),(a[0],a[3]),(a[2],a[1]),(a[2],a[3])] for u,v in [(b[0],b[1]),(b[0],b[3]),(b[2],b[1]),(b[2],b[3])])
for e in plan['start_edges']:
 a,b=rect(e['src'],e.get('launch_part')),rect(e['dst'],e.get('capture_part'));rows.append(dict(port=e['port'],src=e['src'],dst=e['dst'],reach_um=hops(a,b),src_rect_um=a,dst_rect_um=b))
bad=sorted((x for x in rows if x['reach_um']>405),key=lambda x:-x['reach_um'])
sumry=dict(scope='conservative provisional FF-row envelopes + actual native cland_tstart_in pins; all technology-mapped combinational cells still require full physical census',edges=len(rows),over405=len(bad),max_um=max(x['reach_um'] for x in rows),failures=bad)
(O/'reach.json').write_text(json.dumps(dict(summary=sumry,edges=rows),indent=1));print(json.dumps(sumry),flush=True)
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
chosen='c_E1_tn_00';aliases=[(k,v) for k,v in gg.items() if v['replaced_port'].endswith('->'+chosen)];aliases.sort(key=lambda kv:0 if '@qcperimeter0_' in kv[0] else 1)
bar=aliases[0][1]['barrier_rect_um'];fig,ax=plt.subplots(figsize=(12,7))
ax.add_patch(Rectangle((bar[0],bar[1]),bar[2]-bar[0],bar[3]-bar[1],facecolor='#d8dce2',edgecolor='#607080',label='actual core + halo'))
new=[r for r in rows if r['dst'] in [a for a,_ in aliases] or r['dst']==chosen]
for r in new:
 a,b=r['src_rect_um'],r['dst_rect_um'];aa=((a[0]+a[2])/2,(a[1]+a[3])/2);bb=((b[0]+b[2])/2,(b[1]+b[3])/2)
 # Planned neighbor START segments are outside the rectangular core.
 ax.plot([aa[0],bb[0],bb[0]],[aa[1],aa[1],bb[1]],color='#167d9a',marker='o',linewidth=2)
 ax.annotate(f"{r['reach_um']:.1f} um",((aa[0]+bb[0])/2,(aa[1]+bb[1])/2),fontsize=9)
for k,v in aliases:
 s=stage[k];r=s['rect_um'];ax.add_patch(Rectangle((r[0],r[1]),max(r[2]-r[0],5),2,facecolor='#159b63'))
 ax.annotate('new START relay', (r[0],r[1]),xytext=(8,-22),textcoords='offset points',fontsize=9)
 c=v['source_xy_um'];ax.plot([c[0],c[0],r[0]],[c[1],r[1],r[1]],'--',color='#ce7c28',linewidth=1,label='proposed clock stub' if k==aliases[0][0] else None)
ax.set_xlim(bar[0]-80,bar[2]+100);ax.set_ylim(bar[1]-90,bar[1]+450);ax.set_aspect('equal');ax.set_xlabel('die x (um)');ax.set_ylabel('die y (um)');ax.legend(loc='upper left');ax.set_title('QC native START: explicit perimeter relays / clock stubs need actual extraction');fig.tight_layout();fig.savefig(O/'perimeter_geometry.png',dpi=160)
