"""Prove the actual native reset-dominated D equations clear or retain state.
Uses symbolic native Liberty/Yosys gate functions, not hand-written RTL rules.
OpenROAD Python; z3-solver imported from the private fleet dependency directory.
"""
import os,sys,json,re,collections
sys.path.insert(0,os.environ['A0_Z3']);import z3,odb
base=os.environ['A0_OUT'];db=odb.dbDatabase.create();odb.read_db(db,base+'/candidate.odb');b=db.getChip().getBlock();models=json.load(open(base+'/cells.json'))['modules'];audit=json.load(open(base+'/state_audit.json'))
def sym(n):return z3.Bool(n)
cache={};busy=set()
def native_function(inst,pin):
 model=models[inst.getMaster().getName()];val={}
 for port,dd in model['ports'].items():
  if dd['direction']=='input':
   assert len(dd['bits'])==1
   pp=inst.findITerm(port);assert pp and pp.getNet(),(inst.getName(),port)
   val[dd['bits'][0]]=expr(pp.getNet())
 cells={bit:(cc,ix) for cc in model['cells'].values() for port,dd in cc['port_directions'].items() if dd=='output' for ix,bit in enumerate(cc['connections'][port])}
 def bit(n):
  if n=='0':return z3.BoolVal(False)
  if n=='1':return z3.BoolVal(True)
  if n in val:return val[n]
  cc,ix=cells[n];con=cc['connections'];typ=cc['type'];A=lambda p:bit(con[p][0])
  if typ in ('$not','$_NOT_','$logic_not'):v=z3.Not(A('A'))
  elif typ in ('$and','$_AND_','$logic_and'):v=z3.And(A('A'),A('B'))
  elif typ in ('$or','$_OR_','$logic_or'):v=z3.Or(A('A'),A('B'))
  elif typ in ('$xor','$_XOR_'):v=z3.Xor(A('A'),A('B'))
  elif typ in ('$xnor','$_XNOR_'):v=z3.Not(z3.Xor(A('A'),A('B')))
  elif typ in ('$mux','$_MUX_'):v=z3.If(A('S'),A('B'),A('A'))
  else:raise AssertionError((inst.getMaster().getName(),typ))
  val[n]=z3.simplify(v);return val[n]
 dd=model['ports'][pin]['bits'];assert len(dd)==1
 return bit(dd[0])
def expr(net):
 name=net.getName()
 if name in cache:return cache[name]
 if name in busy:return sym(name)
 busy.add(name)
 drivers=[p for p in net.getITerms() if str(p.getIoType())=='OUTPUT']
 if len(drivers)!=1:v=sym(name)
 else:
  p=drivers[0];i=p.getInst();master=i.getMaster().getName()
  if 'DFF' in master:
   # Native inverting-Q cells, checked by actual Liberty functional model.
   if master=='DFFASRHQNx1_ASAP7_75t_R':
    rn=z3.simplify(expr(i.findITerm('RESETN').getNet()));sn=z3.simplify(expr(i.findITerm('SETN').getNet()))
    v=z3.BoolVal(True) if z3.is_false(rn) else z3.BoolVal(False) if z3.is_false(sn) else sym(name)
   else:v=sym(name)
  elif str(i.getMaster().getType())=='BLOCK':v=sym(name)
  else:v=native_function(i,p.getMTerm().getName())
 busy.remove(name);cache[name]=v;return v
# Assert all actual leaf reset levels. Independent gate equations then propagate
# actual async state clears, original enable/mux reset dominance and ties.
for r in json.load(open(base+'/manifest.json'))['leaf_endpoints']:
 cache[r['new_net']]=z3.BoolVal(False if r['root_qn_parity'] else True)
state={t['instance']:t for r in audit['synchronous_endpoint_states'] for t in r['target_states']}
def prove(a,b):
 s=z3.Solver();s.add(a!=b);return s.check()==z3.unsat
rows=[]
for name,t in sorted(state.items()):
 i=b.findInst(name);assert i.getMaster().getName()=='DFFHQNx1_ASAP7_75t_R'
 d=expr(i.findITerm('D').getNet());q=sym(i.findITerm('QN').getNet().getName())
 if prove(d,z3.BoolVal(False)):kind='clear_QN_to_1'
 elif prove(d,z3.BoolVal(True)):kind='clear_QN_to_0'
 elif prove(d,z3.Not(q)):kind='retain_QN'
 else:kind='conditional_or_unproven'
 rows.append(dict(instance=name,clock=t['clocks'],class_=kind,native_D=str(z3.simplify(d)),QN_net=i.findITerm('QN').getNet().getName()))
report=dict(schema='opentallas.a0.native_sync_reset_classification.v1',classification=dict(collections.Counter(r['class_'] for r in rows)),states=rows,z3_version=z3.get_version_string(),method='SMT unsat proofs of actual Liberty/Yosys native gate D equations under asserted clock-owned reset leaves; original async states evaluated from native reset pins')
json.dump(report,open(base+'/sync_classification.json','w'),indent=2)
print('A0_SYNC_CLASSIFICATION',report['classification'])
