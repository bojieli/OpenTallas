import json,re,sys
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
p=Path(__file__).parent;D=G.Design(p/'tile_geom.tsv');pred=json.load(open(p/'xpredecessors.json'))['predecessors']
groups={};rects={
 'a_capture':[300,334,410,374], 'a_early_edge':[150,750,200,800], 'b_tail':[515,815,550,900], 'a_early_skew':[90,750,200,1028],
 'a_tail_0':[340,700,369,728], 'a_tail_1':[340,568,369,596], 'a_tail_2':[340,448,369,476], 'a_tail_3':[340,334,369,374],
 'b_skew':[515,770,675,1000], 'a_x':[340,600,369,630], 'b_x':[510,825,540,855],
 'a_prev':[150,744,190,774], 'b_prev':[180,800,210,830]}
for c in D.cells.values():
 if c[0]!='S':continue
 name=c[6];n=name.replace('\\','');key=None
 if '.g_a[' in n and ('.u_ad1/' in n or '.u_av1/' in n):key='a_capture'
 m=re.search(r'\.g_sk\[(\d+)\]\.u_([ab])\..*line\[(\d+)\]',n)
 if m:
  j,ab,idx=m.groups();depth=11*(int(j)%8);stage=int(idx)//16
  key=('b_tail' if stage==depth-1 else 'b_skew') if ab=='b' else 'a_early_edge' if stage in (0,depth-5) else 'a_early_skew' if stage<depth-4 else 'a_tail_'+str(stage-(depth-4))
 if '.u_b.u_x.genblk' in n:
  idx=int(re.search(r'line\[(\d+)\]',n)[1]);key='a_x' if idx%512>=256 else'b_x'
 if name in pred:key='a_prev' if pred[name]=='A' else'b_prev'
 if key:groups.setdefault(key,[]).append(name)
# Keep every planned instance bit; Tcl reads exact actual OpenDB names (JSON preserves backslashes).
(p/'tile_groups.json').write_text(json.dumps({'rects':rects,'groups':groups},indent=1)+'\n')
lines=['# PLACE-only HEAD non-plan trial, no RTL/latency/macros/pins changed.','set cland_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]']
for key,names in groups.items():
 rect=' '.join(map(str,rects[key]));lines+=['set cland_cursor {}']
 for name in sorted(names):
  safe=name.replace('}','\\}')
  lines += [f'set ti [$ff_blk findInst {{{safe}}}]',f'if {{$ti eq "NULL"}} {{ error "TILEHOP missing exact instance" }}',f'cland_put $ti {{{rect}}} tilehop:{key} 0.6 1']
 lines += [f'puts "TILEHOP {key} placed {len(names)}"']
lines += ['close $cland_fh']
(p/'tile_hop.tcl').write_text('\n'.join(lines)+'\n')
print({k:len(v) for k,v in groups.items()})
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(7,10));ax.set(xlim=(0,708.48),ylim=(0,1036.8),aspect='equal',title='hd_tile existing-stage placement candidate (PLACE only)')
for c in D.cells.values():
 if c[0]=='M':ax.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],color='gray',alpha=.4));ax.text(c[2]+10,c[3]+30,c[6].split('.')[-1],fontsize=8)
for i,(k,r) in enumerate(rects.items()):
 ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fill=False,color=plt.cm.tab20(i),linewidth=1.8));ax.text(r[0],r[1],k,fontsize=6)
ax.plot([30,170,354,354],[858,760,615,354],color='red',marker='o');fig.savefig(p/'tile_candidate.png',dpi=150)
