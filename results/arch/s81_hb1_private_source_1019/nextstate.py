#!/usr/bin/env python3
"""Fleet-only Boolean one-edge diagnostic; arbitrary present state, not reachability."""
import pathlib,json,gzip,re,hashlib,argparse,ast
import z3
P=pathlib.Path(__file__).resolve().parent;A=P.parent/'s81_hb1_diagnostic_census_1019';M=P.parent/'s81_hb1_fixedpoint_model_1019'
def load(p):return json.load(gzip.open(p) if str(p).endswith('.gz') else open(p))
def norm(s):return s.replace('\\','')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Network:
 def __init__(self):
  self.m=load(A/'receipt/mapped.json.gz')['modules']['ot_s81sl_xr3'];self.cells=self.m['cells'];self.c=load(A/'receipt/native_census.json.gz');self.model=load(M/'correspondence.json.gz')
  self.fn=load(P.parent/'s81_hb1_cell_semantics_1019/projection_manifest.json')['masters'];self.native={norm(r['instance']):r['instance'] for r in self.c['pin_inventory']}
  self.dir={(norm(r['instance']),r['pin']):r['direction'] for r in self.c['pin_inventory'] if r['signal'] not in ('POWER','GROUND')}
  self.asrledger=[];self.owner={};self.cache={};self.state={};self.used=set();self.input={};self.roots={r['driver']:r for r in self.c['records'] if r['driver']!='PORT'}
  self.assign={(norm(d),dc,p):(norm(s),sc,iv) for s,sc,d,dc,p,iv in self.model['endpoint_assignments'] if d!='PORT'}
  self.copies={norm(r['driver']):r['copies'] for r in self.model['rows']}
  for n,c in self.cells.items():
   for pin,b in c['connections'].items():
    if self.dir[n,pin]=='OUTPUT':self.owner[b[0]]=(n,pin)
  for n,p in self.m['ports'].items():
   if p['direction']=='input':
    for j,b in enumerate(p['bits']):self.input[b]=z3.Bool('input__'+n+'__'+str(j))
 def expression(self,s,pins):
  # Canonical Liberty syntax, parsed structurally; no eval of source expressions.
  t=re.findall(r'[A-Za-z_][A-Za-z_0-9]*|[01]|[!()*+^]',s);i=0
  def atom():
   nonlocal i
   tok=t[i];i+=1
   if tok=='!':return z3.Not(atom())
   if tok=='(':
    v=or_();assert t[i]==')';i+=1;return v
   if tok in ('0','1'):return z3.BoolVal(tok=='1')
   return pins(tok)
  def and_():
   nonlocal i
   v=atom()
   while i<len(t) and t[i]=='*':i+=1;v=z3.And(v,atom())
   return v
  def xor_():
   nonlocal i
   v=and_()
   while i<len(t) and t[i]=='^':i+=1;v=z3.Xor(v,and_())
   return v
  def or_():
   nonlocal i
   v=xor_()
   while i<len(t) and t[i]=='+':i+=1;v=z3.Or(v,xor_())
   return v
  v=or_();assert i==len(t),(s,t[i:]);return v
 def stateq(self,n,ci):
  self.used.add((n,ci));k=(n,ci)
  if k not in self.state:self.state[k]=z3.Bool(('canonical__' if ci==0 else 'extra__')+n+'__'+str(ci))
  return self.state[k]
 def pin(self,mode,n,ci,p):
  a=self.assign.get((n,ci,p)) if mode=='candidate' else None
  if a:
   src,sc,iv=a;r=self.roots[self.native[src]];v=self.cell(mode,src,sc,r['pin']);return z3.Not(v) if iv else v
  return self.wire(mode,self.cells[n]['connections'][p][0])
 def wire(self,mode,b,nextedge=False):
  if isinstance(b,str):assert b in ('0','1');return z3.BoolVal(b=='1')
  if b in self.input:return self.input[b]
  n,p=self.owner[b]
  return self.cell(mode,n,0,p,nextedge)
 def cell(self,mode,n,ci,p,nextedge=False):
  k=(mode,n,ci,p,nextedge)
  if k in self.cache:return self.cache[k]
  c=self.cells[n];ty=c['type']
  if ty.startswith('DFF'):
   if not nextedge:v=self.stateq(n,ci)
   else:
    v=z3.Not(self.pin(mode,n,ci,'D'))
    if ty.startswith('DFFASR'):
     rn=self.pin(mode,n,ci,'RESETN');sn=self.pin(mode,n,ci,'SETN');v=z3.If(z3.Not(sn),False,z3.If(z3.Not(rn),True,v))
  else:
   # NEXT propagates only through output BUF/INV. All functional D cones are PRESENT.
   def pins(pin):
    if nextedge:
     assert ty.startswith(('BUF','INV')), ('nonregistered boundary',n,ty)
     return self.wire(mode,c['connections'][pin][0],True)
    return self.pin(mode,n,ci,pin)
   v=self.expression(self.fn[ty]['functions'][p],pins)
  self.cache[k]=v;return v
 def async_constraints(self,solver,mode):
  seen=set()
  while True:
   todo=self.used-seen
   if not todo:break
   for n,ci in todo:
    seen.add((n,ci))
    if mode=='native' and ci:continue
    if not self.cells[n]['type'].startswith('DFFASR'):continue
    q=self.stateq(n,ci);rn=self.pin(mode,n,ci,'RESETN');sn=self.pin(mode,n,ci,'SETN')
    assert z3.is_true(z3.simplify(sn)), ('SETN must be actual tiedHI for this binary scope',n,ci,str(sn))
    self.asrledger.append({'mode':mode,'instance':n,'copy':ci,'SETN':str(z3.simplify(sn)),'RESETN':str(rn),'presentQN':str(q),'role':'actual asynchronous present-state legality; no release-age claim'})
    solver.add(z3.Implies(z3.Not(sn),z3.Not(q)),z3.Implies(z3.And(sn,z3.Not(rn)),q))
  return len(seen)
def main(out):
 out.mkdir(parents=True,exist_ok=False);nw=Network();s=z3.Solver()
 b=nw.m['ports']['sw_d']['bits'][0];v=nw.m['ports']['sw_v']['bits'][0]
 nd=nw.wire('native',b,True);cd=nw.wire('candidate',b,True);nv=nw.wire('native',v,True);cv=nw.wire('candidate',v,True)
 # Source owns qualification; demanding both valid avoids an inactive-output-only witness.
 s.add(nv,cv,nd!=cd)
 before=-1
 while before!=len(nw.used):
  before=len(nw.used);nw.async_constraints(s,'native');nw.async_constraints(s,'candidate')
 (out/'async_constraints.json').write_text(json.dumps(nw.asrledger,indent=2)+'\n')
 (out/'query.smt2').write_text(s.to_smt2());verdict=s.check();info={'scope':'Boolean NEXTSTATE arbitrary present-state diagnostic; NOT source equivalence, startup or reachability proof','verdict':str(verdict),'target':'sw_d[0] nextedge with native/candidate sw_v[0] nextedge both true','canonical_state_correlated':True,'extra_copy_state_independent':True,'async_present_and_next_action':'actual RESETN/SETN pins; low SETN wins QN0, else low RESETN QN1','used_ff_instances':len(nw.used),'used_extra_ff':sum(ci>0 for n,ci in nw.used),'symbolic_nodes':len(nw.cache),'source_hashes':{str(p.relative_to(P.parent)):sha(p) for p in [A/'receipt/mapped.json.gz',M/'correspondence.json.gz',P.parent/'s81_hb1_cell_semantics_1019/projection_manifest.json']}}
 if verdict==z3.sat:
  model=s.model();(out/'model.txt').write_text(str(model)+'\n');vals={str(v):bool(z3.is_true(model.eval(v,model_completion=True))) for v in nw.state.values()};(out/'state.json').write_text(json.dumps(vals,indent=2)+'\n')
  info['witness']={k:str(model.eval(expr,model_completion=True)) for k,expr in [('native_sw_d0',nd),('candidate_sw_d0',cd),('native_sw_v0',nv),('candidate_sw_v0',cv)]}
 s.push()
 for (name,ci),q in list(nw.state.items()):
  if ci:s.add(q==nw.stateq(name,0))
 equal_verdict=s.check();info['equal_copy_induction_control']=str(equal_verdict)
 assert equal_verdict==z3.unsat, 'Equal-copy exactgraph control must have no nextoutput difference'
 s.pop()
 (out/'result.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info,indent=2));return 0
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('out',type=pathlib.Path);raise SystemExit(main(ap.parse_args().out))
