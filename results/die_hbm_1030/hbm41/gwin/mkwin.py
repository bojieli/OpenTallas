#!/usr/bin/env python3
"""DIE-HBM-41 windowed G2 GRT probe: crop a placed g2-partition probe (probe.v + io.tcl + probe.tcl + insts.tsv from a
finished q0f run) to a full-width y-window [y0,y1] (multiples of 8.64 so rows/tracks keep their phase).
Nets (all degree 2): both ends inside -> kept; one end outside -> the outside end becomes a boundary IO pin at its clamp
onto the window edge; both outside with the window between them (one below, one above) -> pass-through, two boundary
pins joined by `assign`; grazing nets dropped.  Boundary pins: N/S window edges, layers M5/M7 alternating, on-track,
de-duplicated.  Clock nets/taps dropped (G2 routes 0 clock nets).  Cells keep their post-DPL positions (FIRM)."""
import re,sys,os,json,collections
src,out,y0,y1,iters=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4]),int(sys.argv[5])
W=829.44; H=y1-y0
assert abs(y0/8.64-round(y0/8.64))<1e-6 and abs(y1/8.64-round(y1/8.64))<1e-6
os.makedirs(out,exist_ok=True)
# --- io pins
pin={}
for ln in open(f'{src}/io.tcl'):
    if ln.startswith('place_pin'):
        m=re.search(r'-pin_name \{?([^{} ]+)\}? -layer (\S+) -location \{(\S+) (\S+)\} -pin_size \{(\S+) (\S+)\}',ln)
        if not m: continue
        pin[m.group(1)]=(m.group(2),float(m.group(3)),float(m.group(4)),m.group(5),m.group(6))
# --- insts
ib={}
for ln in open(f'{src}/insts.tsv'):
    n,c,a,b,c2,d=ln.split('\t'); ib[n]=(c,float(a),float(b),float(c2),float(d))
# --- netlist
term=collections.defaultdict(list)   # net -> [('I',inst,pin) | ('P',portbit)]
insts=[]
portdir={}
for ln in open(f'{src}/probe.v'):
    s=ln.strip()
    m=re.match(r'(input|output)\s*(?:\[(\d+):0\])?\s*(\w+)',s)
    if m and not s.startswith('wire'):
        d,msb,nm=m.groups()
        if msb is None: portdir[nm]=d
        else:
            for i in range(int(msb)+1): portdir[f'{nm}[{i}]']=d
        continue
    m=re.match(r'(\w+)\s+(\w+)\s*\((.*)\);',s)
    if m and m.group(1) not in ('module',):
        cell,inst,conns=m.groups()
        cs=re.findall(r'\.(\w+)\(([^)]+)\)',conns)
        insts.append((cell,inst,cs))
        for p,net in cs: term[net.strip()].append(('I',inst,p))
for nm in portdir:
    term[nm].append(('P',nm))
def xy(t):
    if t[0]=='P': p=pin[t[1]]; return p[1],p[2]
    c,a,b,c2,d=ib[t[1]]; return (a+c2)/2,(b+d)/2
inside=lambda y: y0<=y<=y1
TR={'M5':(0.024,0.048),'M7':(0.032,0.064)}
used=collections.defaultdict(set)
def bpin(x,edge,k):
    lay='M5' if k%2==0 else 'M7'; off,pit=TR[lay]
    t=round((x-off)/pit); 
    for dt in range(0,4000):
        for s in ((t+dt),(t-dt)):
            xx=off+s*pit
            if 1.0<xx<W-1.0 and s not in used[(edge,lay)]:
                used[(edge,lay)].add(s); return lay,round(xx,4)
    raise RuntimeError('edge full')
keep_inst=set(); nets=[]; bpins=[]; stats=collections.Counter(); k=0
for net,ts in term.items():
    if len(ts)!=2: stats['deg%d'%len(ts)]+=1; continue
    if any(t[0]=='I' and ib[t[1]][0].startswith('BUF') for t in ts) or net.startswith('clk'): stats['clock']+=1; continue
    (xa,ya),(xb,yb)=xy(ts[0]),xy(ts[1]); ia,ibn=inside(ya),inside(yb)
    if ia and ibn: nets.append((net,ts,None)); stats['in']+=1
    elif ia or ibn:
        ti,to=(ts[0],ts[1]) if ia else (ts[1],ts[0]); (xo,yo)=xy(to)
        edge='S' if yo<y0 else 'N'; lay,xx=bpin(xo,edge,k); k+=1
        bn=f'bp{len(bpins)}'; bpins.append((bn,lay,xx,edge,'input' if to==ts[0] or (to[0]=='I' and to[2]=='QN') or (to[0]=='P' and portdir[to[1]]=='input') else 'output'))
        nets.append((net,[ti],bn)); stats['cut']+=1
    elif (ya<y0)!=(yb<y0) and (ya>y1 or yb>y1):
        e1,e2=('S','N') if ya<y0 else ('N','S')
        l1,x1=bpin(xa,e1,k); l2,x2=bpin(xb,e2,k+1); k+=2
        a=f'bp{len(bpins)}'; bpins.append((a,l1,x1,e1,'input')); b=f'bp{len(bpins)}'; bpins.append((b,l2,x2,e2,'output'))
        nets.append((net,[],(a,b))); stats['pass']+=1
    else: stats['out']+=1; continue
    for t in ts:
        if t[0]=='I' and inside(xy(t)[1]): keep_inst.add(t[1])
# --- write verilog
sid=lambda s: re.sub(r'\W','_',s)
ports=[]; body=[]; wires=[]; netname={}
keptports={}
for net,ts,bn in nets:
    if bn is None:
        pt=[t for t in ts if t[0]=='P']
        if pt: keptports[pt[0][1]]=sid(pt[0][1]); netname[net]=sid(pt[0][1])
        else: wires.append(sid(net)); netname[net]=sid(net)
    elif isinstance(bn,str):
        netname[net]=bn
        pt=[t for t in ts if t[0]=='P']
        if pt:   # inside end is a real port: pass-through port->boundary
            keptports[pt[0][1]]=sid(pt[0][1]); body.append(f'  assign {bn if portdir[pt[0][1]]=="output" else sid(pt[0][1])} = {sid(pt[0][1]) if portdir[pt[0][1]]=="output" else bn};')
            netname[net]=None
    else:
        a,b=bn; body.append(f'  assign {b} = {a};')
for nm,s in keptports.items(): ports.append(f'  {portdir[nm]} {s}')
bdir={}
for bn,lay,xx,edge,d in bpins: bdir[bn]=d
# fix directions for assign pairs / port pairs: an assign lhs must be output
for ln in body:
    m=re.match(r'  assign (\w+) = (\w+);',ln)
    if m:
        if m.group(1) in bdir: bdir[m.group(1)]='output'
        if m.group(2) in bdir: bdir[m.group(2)]='input'
for bn in bdir: ports.append(f'  {bdir[bn]} {bn}')
cells=[]
for cell,inst,cs in insts:
    if inst not in keep_inst: continue
    cc=[]
    for p,net in cs:
        n=net.strip(); nn=netname.get(n)
        if nn: cc.append(f'.{p}({nn})')
    cells.append(f'  {cell} {inst} ({", ".join(cc)});')
with open(f'{out}/probe.v','w') as f:
    f.write('module ftprobe (\n'+',\n'.join(ports)+'\n);\n')
    for w in sorted(set(wires)): f.write(f'  wire {w};\n')
    f.write('\n'.join(cells)+'\n'+'\n'.join(body)+'\nendmodule\n')
# --- io
with open(f'{out}/io.tcl','w') as f:
    for nm,s in keptports.items():
        lay,x,y,w,h=pin[nm]; f.write(f'place_pin -pin_name {{{s}}} -layer {lay} -location {{{x:.4f} {y-y0:.4f}}} -pin_size {{{w} {h}}}\n')
    for bn,lay,xx,edge,d in bpins:
        w=0.024 if lay=='M5' else 0.032; yy=0.096 if edge=='S' else H-0.096
        f.write(f'place_pin -pin_name {{{bn}}} -layer {lay} -location {{{xx:.4f} {yy:.4f}}} -pin_size {{{w} 0.192}}\n')
# --- tcl
blk=[]
for ln in open(f'{src}/probe.tcl'):
    m=re.match(r'(create_blockage|create_obstruction) -region \{(\S+) (\S+) (\S+) (\S+)\}(.*)',ln.strip())
    if m:
        a,b,c,d=map(float,m.groups()[1:5]); b2,d2=max(b,y0),min(d,y1)
        if d2>b2: blk.append(f'{m.group(1)} -region {{{a} {b2-y0:.4f} {c} {d2-y0:.4f}}}{m.group(6)}')
with open(f'{out}/probe.tcl','w') as f:
    f.write(f'''read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /work/probe.v
link_design ftprobe
initialize_floorplan -die_area {{0 0 {W} {H:.4f}}} -core_area {{4.32 0 825.12 {H:.4f}}} -site asap7sc7p5t
source /work/make_tracks.tcl
source /work/io.tcl
''')
    f.write('\n'.join(blk)+'\n')
    for inst in sorted(keep_inst):
        c,a,b,c2,d=ib[inst]; f.write(f'place_inst -name {inst} -location {{{a:.3f} {b-y0:.3f}}} -status FIRM\n')
    f.write('set_routing_layers -signal M2-M7\n'+''.join(f'set_global_routing_layer_adjustment M{i} 0.5\n' for i in range(2,8)))
    f.write(f'''set t0 [clock seconds]
global_route -congestion_iterations {iters} -allow_congestion -verbose -congestion_report_file /work/grt_congestion.rpt
puts "OT_GRT_S [expr {{[clock seconds]-$t0}}]"
puts OT_DONE
''')
os.system(f'cp {src}/make_tracks.tcl {out}/')
json.dump(dict(src=src,y0=y0,y1=y1,iters=iters,insts=len(keep_inst),bpins=len(bpins),kept_ports=len(keptports),**stats),open(f'{out}/win.json','w'),indent=1)
print(json.dumps(dict(insts=len(keep_inst),bpins=len(bpins),kept_ports=len(keptports),**stats)))
