import odb,json,collections,math,re
DB='/base/6_final.odb'
print('READING_EXACT_ODB',flush=True)
db=odb.dbDatabase.create();odb.read_db(db,DB);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
print('ODB_LOADED',flush=True)
def loc(it):
 x,y=it.getAvgXY()[1:];return [x/u,y/u]
def seq(i):return any(t.getMTerm().getName() in ('CLK','CK') for t in i.getITerms()) and not i.getMaster().isBlock()
def box(i):
 r=i.getBBox();return [r.xMin()/u,r.yMin()/u,r.xMax()/u,r.yMax()/u]
def transparent(i):return i.getMaster().getName().startswith(('BUF','INV','HB'))
def traverse(n,forward,seen=None):
 seen=set() if seen is None else seen
 if n is None or n.getName() in seen:return []
 seen=seen|{n.getName()}; out=[]
 for t in n.getITerms():
  if t.getIoType()!=('INPUT' if forward else 'OUTPUT'):continue
  i=t.getInst()
  if seq(i) or i.getMaster().isBlock():out.append({'inst':i.getName(),'master':i.getMaster().getName(),'pin':t.getMTerm().getName(),'xy':loc(t),'box':box(i),'via':[]});continue
  if not transparent(i):out.append({'inst':i.getName(),'master':i.getMaster().getName(),'pin':t.getMTerm().getName(),'xy':loc(t),'box':box(i),'nontransparent':True,'via':[]});continue
  for other in i.getITerms():
   if other.getIoType()==('OUTPUT' if forward else 'INPUT'):
    for row in traverse(other.getNet(),forward,seen):row['via'].insert(0,{'inst':i.getName(),'master':i.getMaster().getName(),'xy':loc(t)});out.append(row)
 return out
ports=[]
for p in b.getBTerms():
 if p.getName() in ('ck','rst_n') or p.getIoType() not in ('INPUT','OUTPUT') or p.getSigType() in ('POWER','GROUND'):continue
 ps=[]
 for pin in p.getBPins():
  for r in pin.getBoxes():ps.append([(r.xMin()+r.xMax())/2/u,(r.yMin()+r.yMax())/2/u])
 direction=p.getIoType();ends=traverse(p.getNet(),direction=='INPUT')
 for e in ends:
  path=[ps[0]]+[q['xy'] for q in e['via']]+[e['xy']]
  e['wire_manhattan_um']=sum(abs(a[0]-c[0])+abs(a[1]-c[1]) for a,c in zip(path,path[1:]));e['direct_manhattan_um']=abs(path[0][0]-path[-1][0])+abs(path[0][1]-path[-1][1])
 ports.append({'port':p.getName(),'direction':direction,'xy':ps,'ends':ends})
names=[]
for line in open('/out/mapped.v'):
 m=re.match(r'^\s*(\S+)\s+(\\[^ ]+|[^ (]+)\s+\(',line)
 if m and m[1]!='module' and not m[1].startswith(('FILL','TAP','DECAP')):names.append(m.groups())
def lookup(n):
 n=n.lstrip('\\')
 return b.findInst(n) or b.findInst(n.replace('[',r'\[').replace(']',r'\]'))
functional=[lookup(n) for master,n in names if not master.startswith(('FILL','TAP','DECAP'))]
print('MISSING_FUNCTIONAL_NAMES',len([i for i in functional if i is None]),flush=True)
functional=[i for i in functional if i is not None]
print('FUNCTIONAL',len(functional),flush=True)
regs=[i for i in functional if seq(i)]; fan=[]
for i in regs:
 for t in i.getITerms():
  if t.getIoType()!='OUTPUT':continue
  ends=traverse(t.getNet(),True)
  if len(ends)>32:fan.append({'inst':i.getName(),'pin':t.getMTerm().getName(),'loads':len(ends),'xy':loc(t),'targets':collections.Counter(x['pin'] for x in ends)})
macros=[{'inst':i.getName(),'master':i.getMaster().getName(),'box':box(i),'orient':i.getOrient(),'pins':{t.getMTerm().getName():loc(t) for t in i.getITerms() if t.getMTerm().getName() in ('clk','ck','rst_n')}} for i in functional if i.getMaster().isBlock()]
r={'schema':'opentallas.ahub.routed_census.v1','source':'c6c412b4c','record':'0770ddeba','registers':len(regs),'std_area_um2':sum(i.getMaster().getWidth()*i.getMaster().getHeight()/u/u for i in functional if not i.getMaster().isBlock()),'macro':macros,'ports':ports,'register_fanout_over32':sorted(fan,key=lambda x:-x['loads'])}
assert len(regs)+len(macros)==3401, f'wrong exact routed sequential census: {len(regs)} FF + {len(macros)} hard children !=3401'
assert len(functional)==len(names), 'unresolved mapped physical instance'
r['sequential_entries_including_hard_children']=len(regs)+len(macros)
r['functional_cells']=len(functional)
json.dump(r,open('/out/census.json','w'),indent=2)
print('REGISTERS',len(regs),'PORTS',len(ports),'FANOUT_GT32',len(fan),'STD_AREA',r['std_area_um2'])
for direction in ('INPUT','OUTPUT'):
 rows=[(e['wire_manhattan_um'],p['port'],e['inst'],len(e['via'])) for p in ports if p['direction']==direction for e in p['ends']];print(direction,'WORST_GEOMETRY',sorted(rows,reverse=True)[:8])
print('FANOUT_TOP',[(x['inst'],x['loads'],x['targets']) for x in r['register_fanout_over32'][:15]])
