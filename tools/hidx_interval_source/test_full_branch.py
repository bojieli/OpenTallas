"""Small-domain source differential only; original AST functions verbatim."""
import ast,collections,hashlib,itertools,json,random
from pathlib import Path
from interval_successor import optimum_pair
P=Path(__file__).parent

def extract(name):
 source=(P/name).read_text();tree=ast.parse(source)
 nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('free','seg','joglayer','branch')]
 ns={'collections':collections,'optimum_pair':optimum_pair}
 # Compile the original function AST without rewriting any statement.
 exec(compile(ast.Module(body=nodes,type_ignores=[]),name,'exec'),ns)
 return ns
original=extract('coupled_original.py');optimized=extract('coupled_optimized.py')
rng=random.Random(10192322);count=0

def check(a,b,H,V,owned):
 global count
 results=[]
 for ns in (original,optimized):
  ns.update(H=H,V=V,owned=collections.defaultdict(list,{k:list(v) for k,v in owned.items()}))
  results.append(ns['branch'](a,b,7))
 assert results[0]==results[1],(a,b,H,V,owned,results)
 count+=1

# Inclusive +/-100 forbidden boundaries, duplicate native layer contacts,
# empty domains, H/V/local-jog blocking, same-net exemption, strict H ties.
for a,b in [((2200,2200),(2600,2600)),((2000,2000),(2600,2600)),((139000,2200),(2600,139000)),((2200,2200),(2200,2200))]:
 for mask in range(16):
  V=[(l,x) for j,x in enumerate((2100,2200,2300,2600)) if mask>>j&1 for l in ('M3','M5')]
  for hmask in range(8):
   H=[(l,y) for j,y in enumerate((2100,2300,2600)) if hmask>>j&1 for l in ('M2','M4')]
   check(a,b,H,V,{})
   for axis in ('H','V'):
    for layer in (('M2','M4') if axis=='H' else ('M3','M5')):
     for delta in (-101,-100,-99,0,99,100,101):
      key=(layer,axis,2300 if axis=='H' else 2200)
      check(a,b,H,V,{key:[(2200+delta,2200+delta,8)]})
      check(a,b,H,V,{key:[(2200+delta,2300+delta,7)]})
# Mixed blockers expose original bound pruning/tie behavior across H rays.
for trial in range(4000):
 points=(2000,2100,2200,2300,2500,139000)
 a=(rng.choice(points),rng.choice(points));b=(rng.choice(points),rng.choice(points))
 H=sorted((l,y) for l in ('M2','M4') for y in points if rng.randrange(3))
 V=sorted((l,x) for l in ('M3','M5') for x in points if rng.randrange(3))
 owned=collections.defaultdict(list)
 for j in range(rng.randrange(15)):
  axis=rng.choice(('H','V'));l=rng.choice(('M2','M4') if axis=='H' else ('M3','M5'))
  c=rng.choice(points);lo=rng.choice(points)+rng.choice((-101,-100,-99,0,99,100,101));hi=lo+rng.randrange(201)
  owned[l,axis,c].append((lo,hi,rng.choice((7,8,9))))
 check(a,b,H,V,owned)
print(json.dumps({'status':'PASS','full_branch_exact_tuple_comparisons':count,'seed':10192322,'original_sha256':hashlib.sha256((P/'coupled_original.py').read_bytes()).hexdigest(),'optimized_sha256':hashlib.sha256((P/'coupled_optimized.py').read_bytes()).hexdigest(),'scope':'small-domain SOURCE only; no full model execution'}))
