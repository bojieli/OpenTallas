import lec_fsm as lec
Base=lec.Aig
class ParityAig(Base):
 def __init__(self):
  super().__init__();self.expr={};self.paritycache={};self.hits=0
 def children(self,a):
  v=(a>>1)-self.ni-1
  return (self.ands[2*v],self.ands[2*v+1]) if v>=0 else None
 def AND(self,a,b):
  if a&1 and b&1 and a>1 and b>1:
   x=self.children(a);y=self.children(b)
   if x and y and set(x)=={z^1 for z in y}:
    self.hits+=1
    return self.XOR(*x)
  return Base.AND(self,a,b)
 def exp(self,a):
  if a<=1:return frozenset(),a
  if a in self.expr:return self.expr[a]
  if a^1 in self.expr:
   x,c=self.expr[a^1];return x,c^1
  return frozenset([a&~1]),a&1
 def XOR(self,a,b):
  aa,ac=self.exp(a);bb,bc=self.exp(b);terms=aa^bb;c=ac^bc
  if not terms:return c
  key=terms
  if key in self.paritycache:return self.paritycache[key]^c
  def build(ts):
   if len(ts)==1:return ts[0]
   mid=len(ts)//2;x=build(ts[:mid]);y=build(ts[mid:])
   r=Base.AND(self,Base.AND(self,x,y^1)^1,Base.AND(self,x^1,y)^1)^1
   self.expr[r]=(frozenset(ts),0)
   return r
  r=build(sorted(terms));self.expr[r]=(terms,0);self.paritycache[key]=r
  return r^c
old_AND=ParityAig.AND
old_init=ParityAig.__init__
def init_affine(self):
 old_init(self);self.eq_expr={};self.eq_cache={}
def equations(self,a):
 if a in self.eq_expr:return self.eq_expr[a]
 if a in self.expr or a^1 in self.expr:
  terms,c=self.exp(a)
  if len(terms)>=2:return ((terms,c^1),)
 return None
def affine_AND(self,a,b):
 # XOR recognition precedes conjunction canonicalisation.
 if a&1 and b&1 and a>1 and b>1:
  x=self.children(a);y=self.children(b)
  if x and y and set(x)=={v^1 for v in y}:return old_AND(self,a,b)
 aa,bb=equations(self,a),equations(self,b)
 if aa is None or bb is None:return old_AND(self,a,b)
 basis={}
 for terms,c in list(aa)+list(bb):
  terms=set(terms)
  for pivot,(row,rc) in sorted(basis.items()):
   if pivot in terms:terms.symmetric_difference_update(row);c^=rc
  if not terms:
   if c:return 0
   continue
  pivot=min(terms);row=frozenset(terms)
  for p,(r,rc) in list(basis.items()):
   if pivot in r:basis[p]=(r^row,rc^c)
  basis[pivot]=(row,c)
 key=tuple((tuple(sorted(r)),c) for p,(r,c) in sorted(basis.items()))
 if key in self.eq_cache:return self.eq_cache[key]
 result=1
 for ts,c in key:
  v=0
  for t in ts:v=self.XOR(v,t)
  result=Base.AND(self,result,v^(c^1))
 self.eq_cache[key]=result;self.eq_expr[result]=tuple((frozenset(ts),c) for ts,c in key)
 return result
ParityAig.__init__=init_affine
ParityAig.AND=affine_AND
lec.Aig=ParityAig
# Exact finite check includes all assignments for many nested AIG patterns.
import random
for seed in range(20):
 m=ParityAig();a=[m.add_input(str(i)) for i in range(5)]; vals=list(a)
 for k in range(100):
  x,y=random.Random(seed*100+k).sample(vals,2)
  vals.append(m.XOR(x,y) if k%2 else m.AND(x,y))
 # validate every recognition by comparing scalar truth and canonical expression.
 for lit,(terms,c) in m.expr.items():
  value,mask=m.simulate(2,seed)
  exp=mask if c else 0
  for t in terms:exp^=lec.lit_val(value,mask,t)
  assert lec.lit_val(value,mask,lit)==exp
print('parity_exact_checks PASS',flush=True)
exec(open('engine_hyp.py').read().replace("Path('eng_hyp')","Path('eng_affine')"))
