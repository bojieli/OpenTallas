import json,re,sys
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
p=Path(__file__).parent;D=G.Design(p/'tile_geom.tsv');pred=json.load(open(p/'xpredecessors.json'))['predecessors']
groups={};rects={
 'a_capture':[300,334,410,374], 'a_early_edge':[150,750,200,800], 'b_tail':[515,815,550,900], 'a_early_skew':[90,750,200,1028],
 'a_tail_0':[340,700,369,728], 'a_tail_1':[340,568,369,596], 'a_tail_2':[340,448,369,476], 'a_tail_3':[340,334,369,374],
 'b_skew':[515,770,675,1000], 'a_x':[340,600,369,630], 'b_x':[510,825,540,855],
 'a_prev':[150,744,190,774], 'b_prev':[180,800,210,830]}
rects.update(row0_local=[330,334,380,374],go_final=[342,630,369,660],a_capture=[330,334,380,374],bundle_bdata=[342,680,369,699],merge_pipeline=[330,334,380,374],bundle_result=[342,600,369,630],a_x=[340,615,369,640],x_input=[180,800,210,830],x_output=[510,800,530,825],control_input=[180,714,210,744],control_hub=[250,704,500,728],control_output=[510,704,530,728],control_enable=[510,740,550,780])
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
 if name in pred:key='x_output'
 if n.startswith('u_core.x_q['):key='x_input'
 if n.startswith('u_core.') and not n.startswith('u_core.u_b.') and not n.startswith('u_core.x_q[') and not n.startswith('u_core.xo_q['):
  root=n.split('[')[0].split('$_')[0]
  key='control_input' if root in ['u_core.go_q','u_core.xv_q','u_core.row_q','u_core.bits_q','u_core.flt_q','u_core.rv_q'] else 'control_output' if root in ['u_core.goo_q','u_core.xvo_q','u_core.o_bits','u_core.o_row','u_core.o_rv','u_core.o_flt'] else 'control_enable' if root=='u_core.b_en' else 'control_hub'
 if '.u_b.u_go.' in n:key='control_hub'
 if n.startswith('u_core.u_b.bd_r[') or n.startswith('u_core.u_b.bv_r['):key='bundle_bdata'
 if n.startswith(('u_core.u_b.pk_q[','u_core.u_b.pk_h[','u_core.u_b.c1[','u_core.u_b.c1_h[')):key='merge_pipeline'
 if n.startswith(('u_core.u_b.res_bits[','u_core.u_b.res_row[','u_core.u_b.res_v$')):key='bundle_result'
 if key:groups.setdefault(key,[]).append(name)
for k,r in enumerate(json.load(open(p/'tile_bin_neighbor_estimate.json'))['rows']):
 key='post_ring_'+str(k);rects[key]=r['rect_um'];groups[key]=[r['capture']]
for key,names in list(groups.items()):
 for name in list(names):
  clean=name.replace('\\','')
  tgt='row0_local' if clean.startswith('u_core.row0_q[') else 'go_final' if clean=='u_core.u_b.u_go.genblk1.g_line.line[1]$_DFF_PN0_' else None
  if tgt:names.remove(name);groups.setdefault(tgt,[]).append(name)
# Keep every planned instance bit; Tcl reads exact actual OpenDB names (JSON preserves backslashes).
(p/'tile4_groups.json').write_text(json.dumps({'rects':rects,'groups':groups},indent=1)+'\n')
lines=['# PLACE-only HEAD non-plan trial, no RTL/latency/macros/pins changed.','set cland_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]']
for key,names in groups.items():
 rect=' '.join(map(str,rects[key]));lines+=['set cland_cursor {}']
 for name in sorted(names):
  safe=name.replace('}','\\}')
  lines += [f'set ti [$ff_blk findInst {{{safe}}}]',f'if {{$ti eq "NULL"}} {{ error "TILEHOP missing exact instance" }}',f'cland_put $ti {{{rect}}} tilehop:{key} 0.6 1']
 lines += [f'puts "TILEHOP {key} placed {len(names)}"']
lines += ['close $cland_fh']
(p/'tile4_hop.tcl').write_text('\n'.join(lines)+'\n')
print({k:len(v) for k,v in groups.items()})
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(7,10));ax.set(xlim=(0,708.48),ylim=(0,1036.8),aspect='equal',title='hd_tile existing-stage placement candidate 4 (PLACE only)')
for c in D.cells.values():
 if c[0]=='M':ax.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],color='gray',alpha=.4));ax.text(c[2]+10,c[3]+30,c[6].split('.')[-1],fontsize=8)
for i,(k,r) in enumerate(rects.items()):
 ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fill=False,color=plt.cm.tab20(i),linewidth=1.8));
 if not k.startswith('post_ring_'):ax.text(r[0],r[1],k,fontsize=6)
ax.plot([30,170,354,354],[858,760,615,354],color='red',marker='o');fig.savefig(p/'tile4_candidate.png',dpi=150)
