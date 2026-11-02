from pathlib import Path
import json,re,collections,hashlib,gzip
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path.cwd();D=R/'capture_gutter_v1';base=json.load(open(R/'capture_geometry.json'));new=json.load(open(D/'capture_geometry.json'));write=json.load(open(R/'write_geometry.json'));bindings=[json.load(open(p/'native_macro_binding.json'))for p in(R,D)];critical={q['FF']for q in base['rows']if q['optimistic_legal_row_405_candidate']is None};assert len(critical)==64
lef=(R/'sram.lef').read_text();pins={}
for m in re.finditer(r'\bPIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1\s*\n',lef,re.S):
 xs=re.findall(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s*;',m[2]);pins[m[1]]=[list(map(float,x))for x in xs]
fig,axes=plt.subplots(1,3,figsize=(21,7),sharex=True,sharey=True);W,H=base['outline_um'];mw,mh=base['SRAM_size_um']
for panel,ax in enumerate(axes):
 binding=bindings[0 if panel==0 else 1];ax.set_aspect('equal');ax.set_xlim(-12,W+20);ax.set_ylim(-14,H+12);ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1));ax.add_patch(Rectangle((4.32,4.32),W-8.64,H-8.64,fill=False,lw=.7,ls='--',ec='#555'))
 for b in binding['rows']:
  x,y=b['planned_xy_um'];m=re.search(r'm([01])\.g_bank\\\[(\d+)\\\]',b['actual_native_name']);label=f'{m[1]}:{int(m[2]):02d}'
  ax.add_patch(Rectangle((x-4.32,y-4.32),mw+8.64,mh+8.64,fc='#dddddd',ec='none',alpha=.5));ax.add_patch(Rectangle((x,y),mw,mh,fc='#becbd1',ec='#567',lw=.7));ax.text(x+mw/2,y+mh/2,label,ha='center',va='center',fontsize=7)
  for prefix,color in [('rd_out[','#156b9b'),('wd_in[','#c47533')]:
   pp=[pins[n][0]for n in pins if n.startswith(prefix)];ax.plot([x+(a+d)/2 for a,c,d,e in pp],[y+(c+e)/2 for a,c,d,e in pp],'.',color=color,markersize=.6)
  a,c,d,e=pins['clk'][0];ax.plot(x+(a+d)/2,y+(c+e)/2,'d',color='#542d83',markersize=3)
 if panel in(1,2):
  for family in (0,1):
   prior=next(q for q in binding['rows']if q['actual_native_name'].startswith(f'm{family}.g_bank\\[4\\]'));following=next(q for q in binding['rows']if q['actual_native_name'].startswith(f'm{family}.g_bank\\[8\\]'));a=prior['planned_xy_um'][1]+mh+4.32;b=following['planned_xy_um'][1]-4.32;ax.axhspan(a,b,color='#74c785',alpha=.2)
 ax.set_xlabel('planned native body x (µm)');ax.grid(alpha=.1)
axes[0].set_ylabel('planned native body y (µm)')
# All 64 original impossible shared-capture FF now have independent necessary sites.
for ax,d in [(axes[0],base),(axes[1],new)]:
 grouped=collections.defaultdict(list)
 for q in d['rows']:
  if q['FF']not in critical:continue
  family='m0'if all(n.startswith('m0.')for n in q['source_macros'])else'm1';c=q['optimistic_legal_row_405_candidate']or q.get('nearest_legal_row_candidate');x,y=c['origin_um'];ax.plot(x,y,'o',ms=2,color='#bb2061');grouped[family].append((x,y))
 for k,pts in grouped.items():
  x=sum(q[0]for q in pts)/len(pts);y=sum(q[1]for q in pts)/len(pts);ax.annotate(f'{k}: {len(pts)} critical FF',xy=(x,y),xytext=(x+42,y+18),fontsize=7,arrowprops=dict(arrowstyle='-',lw=.6))
axes[0].set_title('Original 4×8 macro grid: capture FAIL\n64/1024 FF have no optimistic 405 µm row site\nWorst legal radius 464.995 µm',fontsize=10)
axes[1].set_title('Two 8.64 µm capture gutters: necessary geometry only\n1024/1024 have independent 405 µm candidates\n24 macros shift +8.64/+17.28 µm; same outline',fontsize=10)
# Explicit current GEN input rectangle to actual native SRAM pin examples.
for i,q in enumerate(write['worst_failed_pairs'][:3]):
 a,b,c,d=q['source_GEN_rectangle_um'];sx,sy=(a+c)/2,(b+d)/2;t=q['target_rectangles_um'][0];tx,ty=(t[0]+t[2])/2,(t[1]+t[3])/2
 axes[2].plot([sx,tx,tx],[sy,sy,ty],lw=.8,color='#b3312f',alpha=.6);axes[2].plot(sx,sy,'x',color='#b3312f',ms=4)
axes[2].set_title('Shared write/control ingress: HOLD before PLACE\n2256 bits reach all 32 SRAMs without an intervening FF\nOptimistic relocated input-pin bound up to 560.736 µm',fontsize=10)
for ax in axes:
 ax.plot(760.344,4.32,'*',ms=8,color='#222');ax.text(752,20,'GEN public clk',ha='right',fontsize=6)
fig.suptitle('StoreA SAME979 source-equivalent native connectivity; proposed geometry only',fontsize=14)
fig.text(.5,.015,'Blue: native SRAM read pins; orange: write-data pins; purple: native SRAM clock pins. Magenta: independent capture candidates, not global placement.\nPublic clock marker is original GEN IO proposal, not built BTerm metal. All synth instances are NONE; no routed reach / timing / PG / source-current release.',ha='center',fontsize=8)
fig.tight_layout(rect=(0,.06,1,.94));fig.savefig(R/'storeA_capture_write_review_v2.png',dpi=160)
# Compact per-FF review and complete compressed exact pin ledgers.
for name,d in [('baseline_capture_summary',base),('gutter_capture_summary',new)]:
 thin={k:v for k,v in d.items()if k!='rows'};thin['rows']=[{k:v for k,v in q.items()if k!='source_pins'}for q in d['rows']];(R/(name+'.json')).write_text(json.dumps(thin,indent=2)+'\n')
for name,path in [('baseline_capture_geometry.json.gz',R/'capture_geometry.json'),('gutter_capture_geometry.json.gz',D/'capture_geometry.json')]:
 with open(path,'rb')as f,gzip.open(R/name,'wb',compresslevel=6)as o:
  while chunk:=f.read(1024*1024):o.write(chunk)
print('RENDER_DONE',R/'storeA_capture_write_review_v2.png',flush=True)
