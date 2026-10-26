#!/usr/bin/env python3
"""Render conditional VM geometry and audit graph exclusions. No physical adoption."""
import collections,gzip,hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/arch/s81_vm_margin_0253'
a=json.loads((ROOT/'results/arch/s81_vm_area_1417/a2_inventory.json').read_text());r=json.loads((OUT/'baseline_gapE.json').read_text())
status=collections.Counter();missing=collections.Counter();parents=collections.Counter()
for line in gzip.open(ROOT/'results/arch/s81_vm_area_1417/a2_pin_join.jsonl.gz','rt'):
 if not line.strip():continue
 n=json.loads(line);status[n['status']]+=1
 if n['status']=='PARENT_LOGIC_OR_UNRESOLVED':
  for i,p,b,d in n['consumers']:missing[(a['leaves'][i]['master'],p)]+=1
peer=r['peer_plan']['source']
audit=dict(inventory_scope=a['scope'],base_source_commit=a['base_source_commit'],configuration=a['configuration'],join_status=dict(status),unresolved_consumers=sum(missing.values()),unresolved_classes=[dict(master=m,port=p,bits=n) for (m,p),n in missing.most_common()],baseline_peer_plan_sha256=r['peer_plan']['sha256'],baseline_pin_grant_sha256=r['assigned_pins']['sha256'],critical_findings=['5431 unresolved records excluded by load(); 6152 consumer endpoints including payload2560b and x43_t2049b','Only f_capture has assigned per-bit parent pins; other ports span-planned','WFC r5 194.4x394.2um has no baseline leaf/home; old middle band only345.6um high; r5 now nativeFAIL capture311ps and successor shape pending','New payload1166.4x86.4um differs old1706.4x64.8um: new height consumes existing21.6um channel','Read-leaf optimization preserves existing graph, not fresh full native elaboration','VMBb9 actual child home/variant not emitted by c26b yet; no side-delivery adoption'])
(OUT/'graph_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
fig,axes=plt.subplots(1,2,figsize=(16,9),gridspec_kw={'width_ratios':[1.25,1]});ax=axes[0]
colors={'bank':'#a3cce0','field':'#dab5e5','read':'#a8d6ad','capture':'#f2c891','control':'#ef9c96','other':'#c9c9c9'}
for name,v in r['placement'].items():
 master,x,y,w,h,fx,fy=v
 cls='bank' if 'bank128' in master else 'field' if 'field4' in master else 'read' if any(k in master for k in ['read_','fsr_','return_bank']) else 'capture' if '.u_cap.' in name else 'control' if any(k in master for k in ['control4','w0_','rsched','seq_tile','fault_join']) else 'other'
 ax.add_patch(Rectangle((x,y),w,h,facecolor=colors[cls],edgecolor='white',linewidth=.3))
 if 'w0_payload' in master:ax.text(x+w/2,y+h/2,'payload',ha='center',va='center',fontsize=5)
 if 'rsched' in master:ax.text(x+w/2,y+h/2,'RS',ha='center',va='center',fontsize=6)
ax.add_patch(Rectangle((0,0),5037,4600.8,fill=False,edgecolor='black',linewidth=1.5))
# Exact c26b macro peer homes translated into VM-local coordinates (die_live source17b13fb06).
for name,rect in [('MIX4 A W1x4',(-1453.248,475.2,1431.648,3652.56)),('Capture',(1654.56,4622.4,1727.976,561.576)),('Collective',(5469.12,0,1727.976,2721.576)),('WFC peer MY',(5469.12,2764.8,1727.976,328.296))]:
 x,y,w,h=rect;ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='#555555',linewidth=1));ax.text(x+w/2,y+h/2,name,ha='center',va='center',fontsize=7,rotation=90 if h>w else 0)
ax.text(5037+216,1350,'432.12 um road',fontsize=7,rotation=90,ha='center')
ax.annotate('SU below: 1889.976 x 10709.256\nactual die peer; rest clipped',xy=(1878,-30),xytext=(200,-500),arrowprops={'arrowstyle':'->'},fontsize=8)
ax.set(xlim=(-1550,7250),ylim=(-750,5400),aspect='equal',xlabel='VM-local x (um)',ylabel='VM-local y (um)',title='Exact c26b peers + historical gapE VM placement\n128 bank leaves; unchanged capacity; cut proof conditional')
for k,c in colors.items():ax.plot([],[],color=c,linewidth=6,label=k)
ax.legend(loc='upper left',ncol=3,fontsize=6)
ax=axes[1]
# Show actual predecessor/payload successor geometries to scale near the middle band.
for name,v in r['placement'].items():
 master,x,y,w,h,fx,fy=v
 if not (1500<y<2200):continue
 ax.add_patch(Rectangle((x,y),w,h,facecolor='#d5d5d5',edgecolor='#666666',linewidth=.4))
 if master=='s81_a2_w0_payload':
  ax.add_patch(Rectangle((x,y),1166.4,86.4,fill=False,edgecolor='red',linewidth=1.5))
  ax.text(x+583.2,y+43.2,'NEW payload 1166.4x86.4',fontsize=6,ha='center',color='red')
 if 'u_wfc' in name:ax.text(x+w/2,y+h/2,name.split('u_wfc.')[-1],rotation=90,fontsize=5,ha='center',va='center')
# Proposed explicit east bay (outside granted VM), actual WFC master outline and exact wider channel impact.
ax.add_patch(Rectangle((5058.6,1760.4),194.4,394.2,fill=False,edgecolor='red',linewidth=2,linestyle='--'))
ax.text(5155.8,1957.5,'WFC r5\n194.4x394.2\nFAIL / NO HOME',fontsize=6,color='red',ha='center',va='center',rotation=90)
ax.axvline(5037,color='black');ax.axvline(5469.12,color='#777777',linestyle=':')
ax.axhspan(1738.8,1760.4,color='#f5d275',alpha=.7);ax.axhspan(2106,2127.6,color='#f5d275',alpha=.7)
ax.set(xlim=(0,5500),ylim=(1560,2260),aspect='equal',xlabel='VM-local x (um)',ylabel='VM-local y (um)',title='Connected middle-band audit: actual new outlines\nRed = requires placement/pin rebind; dashed bay NOT adopted')
fig.text(.60,.36,'Findings after actual geometry comparison:\n1. WFC 394.2 um height exceeds 345.6 um middle band.\n2. New payload height adds 21.6 um, consuming a channel.\n3. East bay would grow VM by 216 um and halve 432.12 um road.\n4. Missing graph endpoints and incomplete parent pin grant\n   block any claim of honest complete cut <0.60.\n\nNext: fresh full-parent elaborated graph and legal homes,\nthen fixed-cycle relay accounting + cut/GRT/TT/FF/DRC proof.',fontsize=10,va='top',linespacing=1.5)
fig.suptitle('S81 VM geometry margin audit — actual connected group; SCREEN ONLY / NO ADOPTION',fontsize=14)
axes[0].set_position([.045,.13,.50,.77]);axes[1].set_position([.60,.48,.38,.40]);fig.savefig(OUT/'connected_audit.png',dpi=160)
if all((OUT/(c+'.json')).exists() for c in ['baseline','face','balanced','internal']):
 fig,axs=plt.subplots(1,4,figsize=(17,6));palette=plt.get_cmap('tab10')
 for ax,c in zip(axs,['baseline','face','balanced','internal']):
  doc=json.loads((OUT/(c+'.json')).read_text());changed={x[0] for x in doc['changed']}
  for name,v in doc['placement'].items():
   m,x,y,w,h,fx,fy=v;col='#d9d9d9'
   if 'read_q' in m:col=palette(int(m.split('read_q')[1].split('_')[0]))
   ax.add_patch(Rectangle((x,y),w,h,facecolor=col,edgecolor='black' if name in changed else 'white',linewidth=.4))
  cut=doc['cuts'];ax.set(aspect='equal',xlim=(0,5037),ylim=(0,4600.8),xlabel='um',title=f"{c}: {cut['worst_share']:.3f} / p99 {cut['p99_share']:.3f}\n{len(changed)} read leaves moved; {cut['edges_over_060']} edges >0.60")
 fig.suptitle('Actual unchanged 503-leaf /128-bank graph: read-leaf assignment alternatives\n30 PathFinder passes; exact baseline replay; fixed baseline parent pins; conditional graph scope')
 fig.tight_layout(rect=(0,.03,1,.88));fig.savefig(OUT/'alternatives.png',dpi=160)
