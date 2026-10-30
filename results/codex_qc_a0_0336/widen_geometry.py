from pathlib import Path
import json,re,csv,collections,math
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path('/srv/opentallas-scratch2/claude/codex-qc-a0-0336');old=p.with_name('codex-qc-a0-2249');out=p/'widen';out.mkdir(exist_ok=True)
impact={'scope':'internal unfrozen A0 core placement candidate only','rtl_cycles_added':0,'top_pin_outline_unchanged':True,'masters_and_libs_unchanged':True,'corners':{},'dies':{}}
fig,axs=plt.subplots(1,2,figsize=(9,12))
nlshift={}
for tag,ax in zip(('nl','nk'),axs):
 fr=json.load(open(old/f'kit_{tag}/freeze.json'));before=json.loads(json.dumps(fr));cols=sorted({h['at'][0] for h in fr['hard_children'] if 'rawfault' in h['master']});shifts={x:2.16*i for i,x in enumerate(cols)};changes=[];boxes=[]
 for h in fr['hard_children']:
  txt=(old/f'kit_{tag}/macros/{h["master"]}.lef').read_text();w,hh=map(float,re.search(r'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)',txt).groups());x,y=h['at'];dx=shifts[x] if 'rawfault' in h['master'] else 0
  if dx:changes.append(dict(inst=h['inst'],master=h['master'],before=h['at'][:],after=[round(x+dx,6),y],pin_translation_um=[dx,0]));h['at'][0]=round(x+dx,6)
  if tag=='nl':nlshift[h['inst']]=dx
  boxes.append(dict(inst=h['inst'],master=h['master'],x=h['at'][0],y=y,w=w,h=hh))
  ax.add_patch(Rectangle((x,y),w,hh,fill=False,edgecolor='#b7b7b7',linestyle='--',linewidth=1));ax.add_patch(Rectangle((h['at'][0],y),w,hh,facecolor='#c5d2df',edgecolor='#23394d',linewidth=.7))
 corridors=[]
 for i in range(len(cols)-1):
  left=cols[i]+shifts[cols[i]]+115.344;right=cols[i+1]+shifts[cols[i+1]]
  for y in (834.432,994.944):
   # Actual existing row cut is physical macro+4.32um at either face.
   row=[round(left+4.32,6),y,round(right-4.32,6),y+140.4]
   mid=(row[0]+row[2])/2;clock=[round(mid-1.08,6),y,round(mid+1.08,6),y+140.4]
   corridors.append(dict(row_rect_um=row,clock_reserved_rect_um=clock,row_width_um=row[2]-row[0],clock_width_um=2.16))
   ax.add_patch(Rectangle((clock[0],y),2.16,140.4,facecolor='#cc4747',alpha=.85))
 overlaps=[]
 for i,a in enumerate(boxes):
  if a['x']<0 or a['y']<0 or a['x']+a['w']>fr['outline_um'][0] or a['y']+a['h']>fr['outline_um'][1]:overlaps.append(['OUTLINE',a['inst']])
  for b in boxes[i+1:]:
   if min(a['x']+a['w'],b['x']+b['w'])>max(a['x'],b['x']) and min(a['y']+a['h'],b['y']+b['h'])>max(a['y'],b['y']):overlaps.append([a['inst'],b['inst']])
 fr['candidate_clock_corridors']=corridors;(out/f'{tag}_freeze_candidate.json').write_text(json.dumps(fr,indent=1)+'\n')
 impact['dies'][tag]=dict(changes=changes,child_count=len(boxes),macro_overlap_or_outline_errors=overlaps,clock_corridors=corridors,rightmost_macro_um=max(b['x']+b['w'] for b in boxes),right_outline_margin_um=fr['outline_um'][0]-max(b['x']+b['w'] for b in boxes))
 ax.set_xlim(0,fr['outline_um'][0]);ax.set_ylim(0,fr['outline_um'][1]);ax.set_aspect('equal');ax.set_title(f'{tag.upper()}: +2.16um per internal gap\nred = planned clock-only column');ax.set_xlabel('um');ax.set_ylabel('um')
# Direct existing net endpoints, with exact child-pin shifts and unchanged std
# coordinates: an impact estimate, NOT a new-placement reach gate.
rows=list(csv.DictReader(open(p/'probe/macro_data_edges.tsv'),delimiter='\t'));stats=collections.Counter();new=[]
for r in rows:
 inst=lambda s:s.replace(chr(92),'')
 a,b=inst(r['inst0']),inst(r['inst1']);dx0=nlshift.get(a,0);dx1=nlshift.get(b,0)
 if not(dx0 or dx1):continue
 x0,y0,x1,y1=(float(r[k])/1000 for k in ('x0','y0','x1','y1'));before=abs(x1-x0)+abs(y1-y0);after=abs(x1+dx1-x0-dx0)+abs(y1-y0)
 stats['affected_edges']+=1;stats['baseline_gt405']+=before>405;stats['candidate_gt405']+=after>405
 if before<=405<after:new.append(dict(net=r['net'],before_um=before,after_um=after,inst0=a,inst1=b))
impact['nl_existing_endpoint_reach_impact']=dict(stats,new_over405=new)
impact['capacity_estimate']=dict(actual_existing_strip_area_um2=303.264,actual_existing_std_area_um2=216.26514,clock_pair_leaf_plus_p2p_estimate_um2=85.,new_strip_area_um2=606.528,projected_fill=(216.26514+85.)/606.528,clock_master_max_width_um=1.620,reserved_clock_column_um=2.160,remaining_crosssection_um=.540,M6_clock_2x_with_two_vss_shields_width_um=.256)
(out/'impact.json').write_text(json.dumps(impact,indent=1)+'\n');fig.tight_layout();fig.savefig(out/'macro_channel_candidate.png',dpi=170);print(json.dumps(impact,indent=1))
