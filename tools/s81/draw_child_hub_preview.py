#!/usr/bin/env python3
"""Draw an explicitly incomplete actual-leaf hub proposal beside its immutable baseline.

Source/current-view gaps and original physical obstructions remain visible.
The drawing never qualifies die fit, cut, clock delivery, or static calendars.
"""
import argparse,json,gzip,hashlib,pathlib,collections,math
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
ap=argparse.ArgumentParser(description=__doc__)
for name in ('model','placement','sizes','vm','su','hc','capture','gather','out'):ap.add_argument('--'+name,required=True)
a=ap.parse_args();B=pathlib.Path(a.out);B.mkdir(parents=True,exist_ok=True)
paths={k:getattr(a,k)for k in ('model','placement','sizes','vm','su','hc','capture','gather')}
raw_inputs={k:pathlib.Path(p).read_bytes()for k,p in paths.items()}
d={k:json.loads(gzip.decompress(raw_inputs[k])if p.endswith('.gz')else raw_inputs[k])for k,p in paths.items()}
(B/'inputs').mkdir(exist_ok=True)
for k,p in paths.items():(B/'inputs'/(k+'.json'+('.gz'if p.endswith('.gz')else''))).write_bytes(raw_inputs[k])
# Use actual emitted DEF and the exact case LEF sizes for every obstruction.
for r in d['model']['insts']:
 q=d['placement']['placed'][r[0]]
 if q[0]!=r[1]:raise ValueError('Actual placed master differs from immutable model: '+r[0])
 r[5:7]=q[1:3];r[7:9]=d['sizes']['sizes'][q[0]]
 if q[3]in('E','W','FE','FW'):r[7],r[8]=r[8],r[7]
parents={r[0]:r for r in d['model']['insts']if r[2]in('hub','band_blk')}
children=[];homes={};colors=dict(VM='#388ca8',SU='#bc8c42',HC='#8e6bae',Capture='#db7168',Gather='#68aa78')
def add(group,name,xy,size,status,source):children.append(dict(group=group,name=name,xy_um=xy,outline_um=size,status=status,source=source))
def home(name,xy,size,status):homes[name]=dict(xy_um=xy,outline_um=size,status=status)
vmxy=[10000,16000];home('sp_vm',vmxy,[5036.664,4600.800],'538 actual leaves; external pins/hf OR/WFC native failure OPEN')
for n,r in d['vm']['placement'].items():add('VM',n,[vmxy[0]+r['x_um'],vmxy[1]+r['y_um']],[r['w_um'],r['h_um']],'CURRENT538_ACTUAL_VIEW_GEOMETRY_NATIVE_GAPS_EXPLICIT',paths['vm'])
su=next(o for o in d['su']['options']if o['outline_um'][0]==5184);suxy=[10000,8500];home('sp_su_s',suxy,su['outline_um'],'711 historical leaf homes; current750+5258owners NOT physically fitted')
for r in su['leaves']:add('SU',r['name'],[suxy[i]+r['origin_um'][i]for i in(0,1)],r['outline_um'],'HISTORICAL_LEAF_CANDIDATE_CURRENT_SOURCE_BINDING_OPEN',r['view'])
hc=next(o for o in d['hc']['options']if o['columns']==6);hcxy=[17800,9500];home('HC_folded64',hcxy,hc['outline_um'],'64CTH combined: hc_s30, hc_t34 exact IDs; croot/comb/controller OPEN')
for r in hc['leaves']:add('HC',r['name'],[hcxy[i]+r['origin_um'][i]for i in(0,1)],r['outline_um'],r['binding_status'],paths['hc'])
capxy=[11900,20643.2];home('sp_capture',capxy,d['capture']['outline_um'],'53 source-exact children; new proposed pins/physical native OPEN')
for n,r in d['capture']['children'].items():add('Capture',n,[capxy[i]+r['at_um'][i]for i in(0,1)],r['outline_um'],'PROPOSED_PIN_GEOMETRY_NOT_PHYSICAL_QUALIFIED',paths['capture'])
gxy=[11900,21248];home('sp_gather',gxy,[1727.976,1045.416],'214 source-exact actual view children; all die incident joins OPEN')
for n,r in d['gather']['instances'].items():add('Gather',n,[gxy[i]+r['at_um'][i]for i in(0,1)],r['outline_um'],'SOURCE_EXACT_ACTUAL_LEF',r['view'])
for n,xy in [('sp_collective',[15636,11500]),('bk_collector',[14500,21000]),('bk_selector',[14500,22000]),('sp_pq',[11900,22550])]:home(n,xy,parents[n][7:9],'LEGACY_PARENT_GEOMETRY_ONLY_CURRENT_CHILD_BINDING_OPEN')
# Actual immovable field outlines remain visible. No transport or field is silently deleted to make room.
fixed=[r for r in d['model']['insts']if r[0]not in set(homes)|{'sp_hc_s','sp_hc_t'}];grid=collections.defaultdict(list);cs=216.
for r in fixed:
 for x in range(math.floor(r[5]/cs),math.floor((r[5]+r[7])/cs)+1):
  for y in range(math.floor(r[6]/cs),math.floor((r[6]+r[8])/cs)+1):grid[x,y].append(r)
collision_count=collections.Counter();examples=[]
for c in children:
 x,y=c['xy_um'];w,h=c['outline_um'];near={}
 for a in range(math.floor(x/cs),math.floor((x+w)/cs)+1):
  for b in range(math.floor(y/cs),math.floor((y+h)/cs)+1):near.update({r[0]:r for r in grid[a,b]})
 for n,r in near.items():
  if min(x+w,r[5]+r[7])-max(x,r[5])>1e-6 and min(y+h,r[6]+r[8])-max(y,r[6])>1e-6:
   collision_count[(c['group'],r[2])]+=1
   if len(examples)<40:examples.append([c['group'],c['name'],n,r[1],r[2]])
for mode in ('baseline','candidate'):
 fig,ax=plt.subplots(figsize=(16.5,13));ax.set(xlim=(0,33000),ylim=(0,26000),aspect='equal',xlabel='die x / um',ylabel='die y / um')
 bg=PatchCollection([Rectangle((r[5],r[6]),r[7],r[8])for r in fixed],facecolor='#a8b6bf',edgecolor='none',alpha=.16,rasterized=True);ax.add_collection(bg)
 if mode=='baseline':
  for n,r in parents.items():
   ax.add_patch(Rectangle((r[5],r[6]),r[7],r[8],facecolor='#c0cad4',edgecolor='#495565',alpha=.8));ax.text(r[5]+r[7]/2,r[6]+r[8]/2,n,ha='center',fontsize=7,rotation=90 if r[8]>2*r[7] else 0)
  ax.set_title('c26b baseline: actual placed parent homes / unchanged actual field background\nParent outlines do not certify their source-current hard-leaf implementation')
 else:
  for group in colors:
   cc=[c for c in children if c['group']==group];ax.add_collection(PatchCollection([Rectangle(c['xy_um'],*c['outline_um'])for c in cc],facecolor=colors[group],edgecolor='#ffffff',linewidth=.15,alpha=.72,rasterized=True))
  for n,r in homes.items():
   xy=r['xy_um'];w,h=r['outline_um'];ax.add_patch(Rectangle(xy,w,h,facecolor='none',edgecolor='#9f2e2e'if n in('sp_su_s','HC_folded64')else'#293d48',linewidth=1));ax.text(xy[0]+w/2,xy[1]+h+75,n,ha='center',fontsize=8)
  for n in('sp_collective','bk_collector','bk_selector','sp_pq'):
   r=homes[n];ax.add_patch(Rectangle(r['xy_um'],*r['outline_um'],facecolor='#e7e7e7',hatch='///',edgecolor='#777777',linewidth=.5,alpha=.5))
  ax.text(17500,20500,'OPEN: HC croot / comb / controller homes',fontsize=8,color='#a32929')
  ax.text(10000,8050,'OPEN: RX/controller + 1.815M transport/glue FF physical homes\n711-leaf SU drawing is incomplete for source-current750 clients',fontsize=8,color='#a32929')
  ax.text(1000,24500,'OWNER REVIEW CANDIDATE ONLY\nNo cut / native clock / static calendar / legal fit claim\nAll original field/transport obstructions retained',fontsize=10,color='#a32929')
  ax.set_title('Child-home redesign preview NEXT TO c26b: compact SU south of VM, folded HC beside centre collective\nActual538 VM +214 gather;53 capture proposed;711SU/2368HC source/view gaps explicit')
 ax.grid(alpha=.12);fig.tight_layout();fig.savefig(B/(mode+'.png'),dpi=160);plt.close(fig)
manifest=dict(scope='OWNER_REVIEW_INCOMPLETE_CHILD_HOMES_CANDIDATE_NOT_ADOPTED',inputs={k:dict(path=p,sha256=hashlib.sha256(raw_inputs[k]).hexdigest(),snapshot='inputs/'+k+'.json'+('.gz'if p.endswith('.gz')else''))for k,p in paths.items()},homes=homes,children=children,child_counts=dict(collections.Counter(c['group']for c in children)),retained_fixed_field_and_transport=len(fixed),child_fixed_overlap_pair_counts={str(k):v for k,v in collision_count.items()},overlap_examples=examples,cut_qualified=False,calendar_qualified=False,native_qualified=False,all_incident_scope='Original146146buses retained in source; complete routing denominator and actual source-bound new endpoint pin joins OPEN',hc_group_parent_map={str(i):('sp_hc_s'if i in set(range(0,10))|set(range(22,32))|set(range(42,52))else'sp_hc_t')for i in range(64)},production_stage_delta='OPEN: currentSU750/glue and HC/BF compiler tuples need exact source-age join')
(B/'candidate.json').write_text(json.dumps(manifest,indent=1)+'\n');print(json.dumps({k:v for k,v in manifest.items()if k in('child_counts','child_fixed_overlap_pair_counts','retained_fixed_field_and_transport')},indent=1))

(B/'review.html').write_text("""<!doctype html><meta charset="utf-8"><title>S81 child-home review</title>
<style>body{font:16px system-ui;margin:24px;color:#273441}main{display:grid;grid-template-columns:1fr 1fr;gap:16px}img{width:100%;border:1px solid #ccc}a{color:#1762a2}.open{color:#9d2828}</style>
<h1>S81 hub child-home review beside c26b</h1>
<p class="open">Candidate only. Owner review is required before adoption. Die fit, shared-channel cut, actual clock delivery and static calendar remain open.</p>
<main><section><h2>Actual c26b baseline</h2><a href="baseline.png"><img src="baseline.png"></a></section><section><h2>Child-home proposal</h2><a href="candidate.png"><img src="candidate.png"></a></section></main>
<p>The proposal draws 538 current VM leaves, 214 actual gather children, 53 source-exact capture children with proposed pins, 711 historical SU leaves, and 2,368 HC leaves in 64 folded groups. SU current source has 750 native clients and 5,258 owners / 5,302 clock entries; its 1,814,932 transport and glue FF bits have no qualified physical homes. HC residual roots, comb and controller remain open. Hatched parent rectangles are unresolved source-current implementations.</p>
<p>Every original field and transport obstruction stays in the audit. Repacking these objects requires a fresh source and physical trial. Dashed Explorer flights are straight endpoint graph segments, not detailed routed wires; their crossing a rectangle alone does not establish physical congestion.</p>
<p><a href="candidate.json">Source hashes, exact child homes, retained obstructions and overlap counts</a></p>""")
