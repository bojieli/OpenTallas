import json,sys,pathlib,hashlib
sys.path.insert(0,sys.argv[1]);import textbook_lint as T
v=pathlib.Path(sys.argv[2]);layout=json.load(open(sys.argv[3]));g,top=T.flatten(T.parse_verilog(v.read_text()),'ot_hbm_static_cfg_collar_idx256');a=T.build(g,None);ck,_=T.clock_nets(g,a)
clean=lambda n:n.replace('\\','')
cells={clean(r[0]):r[3:7] for r in layout['std_cells']};ports={}
for n,layer,*bb in layout['pins']:
 if n in ports:
  z=ports[n];bb=[min(z[0],bb[0]),min(z[1],bb[1]),max(z[2],bb[2]),max(z[3],bb[3])]
 ports[n]=bb
missing=set();rows=[]
def cellbox(ci):
 n=clean(g.cells[ci][1]);b=cells.get(n)
 if b is None:missing.add(n)
 return b
def distance(b,c):
 return max(abs(b[i]-c[j])+abs(b[k]-c[l]) for i in [0,2] for j in [0,2] for k in [1,3] for l in [1,3])
for x,(ci,pn) in a['driver'].items():
 if x<=3 or x in ck or (ci>=0 and a['kind'][ci]=='buf'):continue
 bb=cellbox(ci) if ci>=0 else ports.get(pn)
 stack=[x];seen={x};end=[];span=0.;worst=None
 while stack:
  y=stack.pop()
  for si,sp,bi in a['loads'].get(y,[]):
   if a['kind'][si]=='buf':
    for z in T._out_nets(g,a,si):
     if z not in seen:seen.add(z);stack.append(z)
   else:end.append((si,sp,bi))
 for si,sp,bi in end:
  sb=cellbox(si)
  if bb and sb:
   d=distance(bb,sb)
   if d>span:span=d;worst=g.cells[si][1]+'/'+sp
 outports=[n for y in seen for n in a['out_ports'].get(y,[])]
 for n in outports:
  sb=ports.get(n)
  if sb and bb:
   d=distance(bb,sb)
   if d>span:span=d;worst='port:'+n
 rows.append({'net':T.net_label(g,a,x),'kind':a['kind'][ci] if ci>=0 else 'input','loads':len(end)+len(outports),'reach_upper_um':round(span,6),'worst_sink':worst})
die=layout['die'];outside=[r[0] for r in layout['std_cells'] if r[3]<die[0] or r[4]<die[1] or r[5]>die[2] or r[6]>die[3]];unplaced=[r[0] for r in layout['std_cells'] if r[2] in ['NONE','UNPLACED']]
summary={'scope':'actual post-CTS cells and IO rectangles; BUF/INV collapsed endpoint Manhattan reach upper bounds (cell corners), not routed wire-length','netlist_sha256':hashlib.sha256(v.read_bytes()).hexdigest(),'roots_including_ties':len(rows),'ties':sum(r['kind']=='tie' for r in rows),'max_loads':max(r['loads'] for r in rows),'over32':[r for r in rows if r['loads']>32],'max_reach_upper_um':max(r['reach_upper_um'] for r in rows),'reach_over405':[r for r in rows if r['reach_upper_um']>405],'missing_cells':sorted(missing),'unknown_cells':sum(k=='macro' for k in a['kind']), 'unknown_cell_types':{g.cells[i][0]:g.cells[i][1] for i,k in enumerate(a['kind']) if k=='macro'},'std_cells':len(cells),'outside_die':outside,'unplaced':unplaced,'top_reach':sorted(rows,key=lambda r:-r['reach_upper_um'])[:30]}
print(json.dumps(summary,indent=2));pathlib.Path(sys.argv[4]).write_text(json.dumps(rows,indent=1)+'\n')
