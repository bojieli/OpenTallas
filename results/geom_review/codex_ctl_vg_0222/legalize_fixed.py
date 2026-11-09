import json, math, collections, re, sys
from pathlib import Path
r=Path(sys.argv[1]); j=json.loads((r/'guide_layout.json').read_text())
def norm(n):return n.replace('\\','')
cs=j['std_cells']; fixed={norm(c[0]):list(c) for c in cs if c[2] in ('FIRM','LOCKED','FIXED')}
def target(n):return any(n.startswith('u_core.u_logic.'+p) for p in ('xa2[','xb2[','sn_o[','g_window_pre.window_nz_q'))
# Baseline 1025 source anchors remain immutable; only capture collisions get a separate explicit delta.
targets={n:c for n,c in fixed.items() if target(n)}
assert len(targets)==1025
bins=collections.defaultdict(set)
def keys(bb):
 return [(x,y) for x in range(math.floor(bb[0]/2),math.floor((bb[2]-1e-8)/2)+1) for y in range(math.floor(bb[1]/2),math.floor((bb[3]-1e-8)/2)+1)]
for n,c in fixed.items():
 for k in keys(c[3:7]):bins[k].add(n)
def hits(n,bb):
 near=set().union(*(bins[k] for k in keys(bb)))
 return [m for m in near if m!=n and min(bb[2],fixed[m][5])-max(bb[0],fixed[m][3])>1e-5 and min(bb[3],fixed[m][6])-max(bb[1],fixed[m][4])>1e-5]
bad={n:hits(n,c[3:7]) for n,c in targets.items()};bad={n:h for n,h in bad.items() if h}
assert all(n.startswith('u_core.u_logic.sn_o[') for n in bad)
original={n:c[3:7] for n,c in targets.items()};moves=[]
# Same row/site lattice as actual data flops. Search nearest L1 row/site centre, up to 8um.
site=.054; row=.270
for n in sorted(bad):
 c=fixed[n]; old=list(c[3:7]); w=old[2]-old[0];h=old[3]-old[1]
 cand=[]
 for dy in range(-29,30):
  for dx in range(-148,149):
   dist=abs(dx*site)+abs(dy*row)
   if dist>8:continue
   cand.append((round(dist,9),abs(dy),dy,dx))
 cand.sort(); chosen=None
 for dist,_,dy,dx in cand:
  bb=[old[0]+dx*site,old[1]+dy*row,old[2]+dx*site,old[3]+dy*row]
  if bb[0]<0 or bb[1]<0 or bb[2]>j['die'][2] or bb[3]>j['die'][3]:continue
  if any(min(bb[2],b[4])-max(bb[0],b[2])>1e-5 and min(bb[3],b[5])-max(bb[1],b[3])>1e-5 for b in j['blocks']):continue
  if not hits(n,bb):chosen=(bb,dist);break
 if chosen is None:raise RuntimeError('no site within8um '+n)
 for k in keys(old):bins[k].discard(n)
 bb,dist=chosen;c[3:7]=bb
 for k in keys(bb):bins[k].add(n)
 moves.append({'name':n,'old_bbox':old,'new_bbox':bb,'move_l1_um':dist,'collided_with':bad[n]})
assert all(not hits(n,c[3:7]) for n,c in targets.items())
tcl=['# Private CTL legal capture anchors: avoid all current fixed cland/reset sites.', 'set ::cm_out [open $::env(RESULTS_DIR)/ot_ctl_capture_legal.txt w]']
for m in moves:
 n=m['name'].split('$_DFF',1)[0];x0,y0,x1,y1=m['new_bbox'];tcl.append('cm_site {%s} %.6f %.6f'%(n,(x0+x1)/2,(y0+y1)/2))
tcl.append('close $::cm_out')
tcl.append('puts "CTL_CAPTURE_LEGAL relocated %d fixed collisions; zero new cycles"'%len(moves))
(r/'ctl_capture_legal_sites.tcl').write_text('\n'.join(tcl)+'\n')
rep={'schema':'opentallas.ctl_fixed_anchor_legal.v1','targets':len(targets),'before_overlapping_targets':len(bad),'after_overlapping_targets':0,'max_capture_move_l1_um':max(m['move_l1_um'] for m in moves),'new_cycles':0,'moves':moves,'limitation':'Fixed-guide geometry derived from real3_2 ODB, not final GPL/DPL or timing signoff.'}
(r/'capture_legal.json').write_text(json.dumps(rep,indent=1)+'\n')
for mode in ['before','after']:
 svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1100" viewBox="-10 -30 610 565">','<rect x="-10" y="-30" width="610" height="565" fill="white"/>','<text x="0" y="-15" font-size="8">CTL real fixed guides '+mode+': 1025 targets; '+str(len(bad) if mode=='before' else 0)+' overlap targets</text>','<rect x="0" y="0" width="587.52" height="518.4" fill="#fafcff" stroke="black" stroke-width=".5"/>']
 for b in j['blocks']:
  _,_,x0,y0,x1,y1=b;svg.append(f'<rect x="{x0}" y="{518.4-y1}" width="{x1-x0}" height="{y1-y0}" fill="#d1d5db" stroke="#555" stroke-width=".5"/>')
 for n,c in fixed.items():
  if target(n):continue
  x0,y0,x1,y1=c[3:7];svg.append(f'<rect x="{x0}" y="{518.4-y1}" width="{x1-x0}" height="{y1-y0}" fill="#999"/>')
 for n,c in targets.items():
  bb=original[n] if mode=='before' else c[3:7];x0,y0,x1,y1=bb;color='#d22' if n in bad else '#1678b8';svg.append(f'<circle cx="{(x0+x1)/2}" cy="{518.4-(y0+y1)/2}" r="{1.1 if n in bad else .65}" fill="{color}"/>')
 svg.append('<text x="0" y="534" font-size="7">Grey: other actual FIRM cells; blue: target anchors; red: 78 corrected capture targets. Macros unchanged.</text></svg>')
 (r/('fixed_'+mode+'.svg')).write_text('\n'.join(svg))
print(json.dumps({k:v for k,v in rep.items() if k!='moves'}))
