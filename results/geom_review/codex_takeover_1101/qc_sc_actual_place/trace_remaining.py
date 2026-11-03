import sys,json,collections
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design(str(P/'sc_geom.tsv'));pairs=json.load(open(P/'r2r_capture_failures.json'))['captures'];ids={c[6]:i for i,c in D.cells.items()}
def inputs(cid):
 seen=set();q=[cid];ports=set();regs=set()
 while q:
  v=q.pop()
  for ni,clk in D.cell_in.get(v,[]):
   if clk:continue
   r=D.nets[ni][1]
   if not r:continue
   if r[0]=='p':ports.add(D.pin_by_k[r[1]]['name']);continue
   k=r[1];c=D.cells[k]
   if c[0]=='S':regs.add(c[6]);continue
   if k not in seen:seen.add(k);q.append(k)
 return sorted(ports),sorted(regs)
def outputs(cid):
 q=list(D.drives[cid]);seen=set(q);ports=set()
 while q:
  n=q.pop()
  for s in D.nets[n][2]:
   if s[0]=='p':ports.add(D.pin_by_k[s[1]]['name']);continue
   if s[2] or D.cells[s[1]][0]!='B':continue
   for nn in D.drives.get(s[1],[]):
    if nn not in seen:seen.add(nn);q.append(nn)
 return sorted(ports)
rows=[]
for p in pairs:
 if p['launch']=='u.u_15646/Q$_DFF_P_':continue
 a,b=inputs(ids[p['launch']]);row=dict(p,launch_input_ports=a,launch_prior_regs=b,capture_output_ports=outputs(ids[p['capture']]));rows.append(row)
(P/'remaining45_port_trace.json').write_text(json.dumps(rows,indent=1)+'\n')
print('launchports',collections.Counter(tuple(x['launch_input_ports'])for x in rows));print('captureports',collections.Counter(tuple(x['capture_output_ports'])for x in rows));print(json.dumps(rows[:3],indent=1)[:3000])
