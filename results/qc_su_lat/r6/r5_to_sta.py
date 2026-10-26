"""Apples-to-apples model check on the MEASURED R5 btab plan: emit the same star (no-shared-wire) OpenSTA DMP model
that core_infra_htree uses, from the R5 plan (nodes, maze segment lengths, exact leaf membership)."""
import json,re,sys
sys.path.insert(0,'/home/ubuntu/.claude/jobs/b7f906df/tmp/wt-r6/tools/die_plan');import core_infra_htree as H
d=json.load(open('../r5/btab_r5.tcl.json'));tcl=open('../r5/btab_r5.tcl').read()
geo={}
for l in open('../r5/btab_geo.txt'):
  f=l.split()
  if f and f[0]=='SINK':geo[f[4]]=(float(f[1]),float(f[2]),f[4],f[5],f[3])
class MZ:
  def xy(self,c):return tuple(c)
nodes=[('root',None,tuple(d['entry']),H.BIG,'entry')]+[(n,p,tuple(xy),m,'branch') for n,p,xy,m in d['nodes']]
leafsinks={}
lv=tcl[tcl.index('set ot_ms_leaves {'):tcl.index('set ot_ms_macros')]
for line in lv.splitlines()[1:]:
  m=re.match(r' \{(\S+) (\S+) \{([\d.]+) ([\d.]+)\} \{(.*)\} (\S+)\}$',line)
  if not m:continue
  name,par,x,y,body,cell=m.groups()
  insts=re.findall(r'\{\{(.*?)\} \{CLK\}\}',body)
  leafsinks[name]=[geo[i] for i in insts]
  nodes.append((name,par,(float(x),float(y)),cell,'leaf'))
wires=[]
for lvl,rows in d['seg'].items():
  for cname,T,segs in rows:
    wires.append(dict(edge=cname,segs=segs))
# R5 chain naming: cname_r0.. then cname; core_infra_htree expects [edge_br, edge_r0.., edge] -> map: names[i+1]=segs[i]
# emulate by renaming: wirelen key uses edge+'_r%d' and edge, so prepend a dummy first segment of 0 for '_br'
for w in wires:w['segs']=w['segs']
P=dict(mz=MZ(),nodes=nodes,wires=[],land={},leafsinks=leafsinks)
# build explicit wirelen through fake wires whose names line up: names=[e_br, e_r0.., e]; we need e_r0..e keyed -> segs
for w in wires:
  P['wires'].append(dict(edge=w['edge'],segs=w['segs'],cells=[[(0,0)]]))
r=0.5*(1.80365e-2+1.89935e-2)*0.8;c=0.5*(1.78475e-1+1.64264e-1)*0.9
H.emit_sta(P,'sta/r5star',r,c)
libs={'TT':H.lib_cells('../r5/invbuf_tt.lib',[H.REP,H.BIG]),'FF':H.lib_cells('../r5/invbuf_ff.lib',[H.REP,H.BIG])}
pred=H.model(P,libs,r,c,0.0,allow_star=True)
print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk!='leaf'} for k,v in pred.items()}))
