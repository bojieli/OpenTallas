#!/usr/bin/env python3
from pathlib import Path
import json,math,heapq,re,statistics,html
R=Path(__file__).resolve().parent
d=json.loads((R/'plan_inputs.json').read_text());P={k:tuple(v) for k,v in d['points'].items()}
CLEAR=2.052
O=[(b[2]-CLEAR,b[3]-CLEAR,b[4]+CLEAR,b[5]+CLEAR) for b in d['blocks']]
def inside(p):return any(a+1e-8<p[0]<c-1e-8 and b+1e-8<p[1]<e-1e-8 for a,b,c,e in O)
def lineok(p,q):
 if inside(p) or inside(q):return False
 for a,b,c,e in O:
  if abs(p[0]-q[0])<1e-8:
   if a+1e-8<p[0]<c-1e-8 and max(min(p[1],q[1]),b)<min(max(p[1],q[1]),e)-1e-8:return False
  elif abs(p[1]-q[1])<1e-8:
   if b+1e-8<p[1]<e-1e-8 and max(min(p[0],q[0]),a)<min(max(p[0],q[0]),c)-1e-8:return False
  else:return False
 return True
def route(p,q):
 if inside(p) or inside(q):raise ValueError(('inside expanded macro',p,q))
 for z in [(p[0],q[1]),(q[0],p[1])]:
  if lineok(p,z) and lineok(z,q):
   return abs(p[0]-q[0])+abs(p[1]-q[1]),[p,z,q]
 xs=sorted(set([p[0],q[0]]+[v for o in O for v in [o[0],o[2]]]))
 ys=sorted(set([p[1],q[1]]+[v for o in O for v in [o[1],o[3]]]))
 start=(xs.index(p[0]),ys.index(p[1]));goal=(xs.index(q[0]),ys.index(q[1]))
 dist={start:0};prev={};h=[(0,start)]
 while h:
  cost,u=heapq.heappop(h)
  if cost!=dist[u]:continue
  if u==goal:break
  for v in [(u[0]-1,u[1]),(u[0]+1,u[1]),(u[0],u[1]-1),(u[0],u[1]+1)]:
   if not(0<=v[0]<len(xs) and 0<=v[1]<len(ys)):continue
   up=(xs[u[0]],ys[u[1]]);vp=(xs[v[0]],ys[v[1]])
   if not lineok(up,vp):continue
   w=cost+abs(up[0]-vp[0])+abs(up[1]-vp[1])
   if w<dist.get(v,1e99):dist[v]=w;prev[v]=u;heapq.heappush(h,(w,v))
 if goal not in dist:raise ValueError(('no legal route',p,q))
 path=[];u=goal
 while True:
  path.append((xs[u[0]],ys[u[1]]))
  if u==start:break
  u=prev[u]
 return dist[goal],path[::-1]
def key(bus,i):return f'u_core.u_logic.{bus}[{i}]$_DFF_P_'
# Preserve xa2 and its real capture neighbors. Eight xb2 selector groups stay compact.
groups={0:(238,194),1:(238,198.32),2:(180,196.16),3:(110,198.32),
        4:(110,204.80),5:(180,204.80),6:(230,202.64),7:(230,206.96)}
sites={};logical={}
for i in range(256):
 n=key('xa2',i);sites[n]=P[n];logical[n]=f'u_core.u_logic.xa2[{i}]'
 x,y=groups[i//32];j=i%32
 yy=4.32+round((y-4.32)/.27)*.27
 xx=4.32+round((x-4.32)/.054)*.054
 n=key('xb2',i);sites[n]=(xx+.54+(j%8)*4.32,yy+.135+(j//8)*.81);logical[n]=f'u_core.u_logic.xb2[{i}]'
for i in range(512):
 n=key('sn_o',i);sites[n]=P[n];logical[n]=f'u_core.u_logic.sn_o[{i}]'
wc=[v for k,v in P.items() if 'u_core.u_logic.wcnt[' in k]
cx=statistics.mean(p[0] for p in wc);cy=statistics.mean(p[1] for p in wc)
# One new control flop stays beside the old counter, same reset and clock region.
cand=[]
for dx in [0,2.16,-2.16,4.32,-4.32]:
 for dy in [0,.54,-.54,1.08,-1.08]:
  p=(cx+dx,cy+dy)
  if inside(p) or any(abs(p[0]-v[0])<1.2 and abs(p[1]-v[1])<.27 for v in P.values()):continue
  cand.append((abs(dx)+abs(dy),p))
assert cand
wnz=min(cand)[1];sites['window_flag']=wnz;logical['window_flag']='u_core.u_logic.g_window_pre.window_nz_q'
summary={};paths=[]
for fam,banks,off in [('xa2',['ra0_q','ra1_q'],0),('xb2',['rb0_q','rb1_q'],256)]:
 raw=[];out=[]
 for i in range(256):
  b=sites[key(fam,i)]
  for bank in banks:
   for bit in [i,i+256]:
    a=P[f'u_core.u_logic.g_raw_capture.{bank}[{bit}]$_DFF_P_']
    n,path=route(a,b);raw.append(n)
    if fam=='xb2' and i in [0,64,96,128,160,213,255] and bit==i+256 and bank=='rb0_q':paths.append(('raw',path))
  n,path=route(b,P[key('sn_o',off+i)]);out.append(n)
  if fam=='xb2' and i in [0,64,96,128,160,213,255]:paths.append(('return',path))
 summary[fam]=dict(raw_macro_avoiding_max_um=max(raw),capture_macro_avoiding_max_um=max(out))
# Explicit group spread and existing legal clock access; this is not a CTS skew claim.
clocks=[(x[0],((x[2]+x[4])/2,(x[3]+x[5])/2)) for x in d['clocks']]
clock_access=[]
for g in range(8):
 ps=[sites[key('xb2',i)] for i in range(g*32,(g+1)*32)]
 spread=max(abs(a[0]-b[0])+abs(a[1]-b[1]) for a in ps for b in ps)
 assert spread<100
 center=(statistics.mean(p[0] for p in ps),statistics.mean(p[1] for p in ps))
 best=min((route(c,center)[0],n,c,route(c,center)[1]) for n,c in clocks if not inside(c))
 clock_access.append(dict(group=g,clock=best[1],legal_access_um=best[0],select_sink_span_um=spread))
 paths.append(('clock',best[3]))
rr=[(k,v) for k,v in P.items() if 'u_rr.g_local[1].local_r' in k]
assert len(rr)==1,rr
reset_route=route(rr[0][1],wnz)
summary['window_flag']=dict(site_um=wnz,old_counter_centroid_um=[cx,cy],reset_source=rr[0][0],reset_legal_access_um=reset_route[0])
summary['groups']=clock_access
wclk=min((route(c,wnz)[0],n,c,route(c,wnz)[1]) for n,c in clocks if not inside(c))
summary['window_flag']['clock']=wclk[1]
summary['window_flag']['clock_legal_access_um']=wclk[0]
paths.append(('clock',wclk[3]));paths.append(('reset',reset_route[1]))
xa_clocks=[]
for g in range(8):
 ps=[sites[key('xa2',i)] for i in range(g*32,(g+1)*32)]
 center=(statistics.mean(p[0] for p in ps),statistics.mean(p[1] for p in ps))
 c=min((route(p,center)[0],n,p,route(p,center)[1]) for n,p in clocks if not inside(p))
 xa_clocks.append(dict(group=g,clock=c[1],legal_access_um=c[0]))
 paths.append(('clock',c[3]))
summary['xa2_clock_access']=xa_clocks
summary['qualification']='PLANNED macro-avoiding XY corridors from actual vF cells; no CTS/route or clock-skew qualification'
assert max(summary[f][k] for f in ['xa2','xb2'] for k in ['raw_macro_avoiding_max_um','capture_macro_avoiding_max_um'])<=405
(R/'corridor_budget.json').write_text(json.dumps(summary,indent=2)+'\n')
(R/'mux_sites.json').write_text(json.dumps({logical[n]:p for n,p in sites.items()},indent=1)+'\n')
# Standard generated Tcl cache: resolve the production flop name, snap to native rows/sites, fail closed.
tcl=r'''# Private CTL vG: source after original raw-bank placement.
global cm_blk cm_dbu cm_core cm_x0 cm_y0 cm_rows cm_sw cm_rh cm_orient cm_ff cm_out
set cm_blk [ord::get_db_block]
set cm_dbu [$cm_blk getDbUnitsPerMicron]
set cm_core [$cm_blk getCoreArea]
set cm_x0 [$cm_core xMin]; set cm_y0 [$cm_core yMin]
set cm_rows [$cm_blk getRows]
set cm_sw [[[lindex $cm_rows 0] getSite] getWidth]
set cm_rh [[[lindex $cm_rows 0] getSite] getHeight]
set cm_orient {}
foreach r $cm_rows { dict set cm_orient [lindex [$r getOrigin] 1] [$r getOrient] }
set cm_ff {}
foreach c [$cm_blk getInsts] {
 if {![string match DFF* [[$c getMaster] getName]]} continue
 set n [string map [list "\\" ""] [$c getName]]
 set p [string first {$_DFF} $n]
 if {$p<0} continue
 dict lappend cm_ff [string range $n 0 [expr {$p-1}]] $c
}
set cm_out [open $::env(RESULTS_DIR)/ot_ctl_mux_fixed.txt w]
proc cm_site {n x y} {
 if {![dict exists $::cm_ff $n] || [llength [dict get $::cm_ff $n]]!=1} { error "CTL_MUX expected one flop $n" }
 set c [lindex [dict get $::cm_ff $n] 0]
 set w [[$c getMaster] getWidth]; set h [[$c getMaster] getHeight]
 if {$h!=$::cm_rh} { error "CTL_MUX non-single-row flop $n" }
 set xx [expr {$::cm_x0+round(($x*$::cm_dbu-$w/2.0-$::cm_x0)/$::cm_sw)*$::cm_sw}]
 set yy [expr {$::cm_y0+round(($y*$::cm_dbu-$h/2.0-$::cm_y0)/$::cm_rh)*$::cm_rh}]
 if {![dict exists $::cm_orient $yy]} { error "CTL_MUX no row $yy" }
 $c setPlacementStatus PLACED
 $c setOrient [dict get $::cm_orient $yy]
 $c setLocation [expr {int($xx)}] [expr {int($yy)}]
 $c setPlacementStatus FIRM
 puts $::cm_out [$c getName]
}
'''
for n,p in sites.items():tcl+=f'cm_site {{{logical[n]}}} {p[0]:.6f} {p[1]:.6f}\n'
tcl+='close $cm_out\nputs "CTL_MUX fixed 1025 mux/capture/window flops from explicit source/capture budgets"\n'
(R/'ctl_mux_sites.tcl').write_text(tcl)
(R/'ctl_mux_release.tcl').write_text(r'''# Source after the original raw-bank release, before DPL.
set cm_r [open $::env(RESULTS_DIR)/ot_ctl_mux_fixed.txt r]
while {[gets $cm_r n]>=0} {
 set c [[ord::get_db_block] findInst $n]
 if {$c eq "NULL"} { error "CTL_MUX release missing $n" }
 $c setPlacementStatus PLACED
}
close $cm_r
''')
def svgpath(ps):return ' '.join(f'{x:.3f},{518.4-y:.3f}' for x,y in ps)
s=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1100" viewBox="-25 -20 640 580"><rect x="-25" y="-20" width="640" height="580" fill="white"/>',
'<text x="0" y="-6" font-size="10">CTL vG planned corridors: actual raw/capture sites; both mux families; zero new cycles</text>',
'<rect x="0" y="0" width="587.52" height="518.4" fill="#f9fbff" stroke="#222"/>']
for b in d['blocks']:
 s.append(f'<rect x="{b[2]}" y="{518.4-b[5]}" width="{b[4]-b[2]}" height="{b[5]-b[3]}" fill="#d4d7de" stroke="#555"/><text x="{b[2]+4}" y="{518.4-b[5]+12}" font-size="7">{html.escape(b[0].split(".")[-1])}</text>')
for n,p in P.items():
 if '.sn_o[' in n:s.append(f'<circle cx="{p[0]}" cy="{518.4-p[1]}" r=".7" fill="#888"/>')
 elif 'g_raw_capture' in n and int(re.search(r'\[(\d+)\]',n)[1])%8==0:s.append(f'<circle cx="{p[0]}" cy="{518.4-p[1]}" r="1.1" fill="#7d319b"/>')
for typ,ps in paths:
 color={'raw':'#b14ca0','return':'#1274bc','clock':'#d89908','reset':'#008b7f'}[typ]
 s.append(f'<polyline points="{svgpath(ps)}" fill="none" stroke="{color}" stroke-width=".7" opacity=".55"/>')
for i in range(256):
 for fam,color in [('xa2','#18945a'),('xb2','#db552b')]:
  p=sites[key(fam,i)];s.append(f'<circle cx="{p[0]}" cy="{518.4-p[1]}" r=".8" fill="{color}"/>')
for g,(x,y) in groups.items():
 s.append(f'<rect x="{x-1}" y="{518.4-y-3.5}" width="35" height="4.5" fill="none" stroke="#d34c20"/><text x="{x}" y="{518.4-y-5}" font-size="6">XB group{g}</text>')
s.append(f'<circle cx="{wnz[0]}" cy="{518.4-wnz[1]}" r="2" fill="#111"/>')
s.append('<text x="0" y="540" font-size="8">Purple: raw/data ingress; blue: macro-avoiding return to retained sn_o; gold: existing legal clock access.</text>')
s.append('<text x="0" y="553" font-size="8">Each32-bit select group stays compact. Mux data flops retain reset-free policy; window flag uses original rr[1].</text></svg>')
(R/'planned.svg').write_text(''.join(s))
print(json.dumps(summary,indent=1))
