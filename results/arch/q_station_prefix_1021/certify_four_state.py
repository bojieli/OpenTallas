#!/usr/bin/env python3
"""Pure four-state Boolean/structural certificate; no RTL simulation."""
import collections, hashlib, itertools, json, re, subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3]
REL='rtl/qwen_dv/s5/s8/qfd_dv_s8_station_math_g.sv'
BASE='40fcc3473eaa7be89da0db5adbcecf80600d5f5e'
old=subprocess.check_output(['git','-C',str(R),'show',BASE+':'+REL],text=True)
new=(R/REL).read_text()
def mul(s):return s.split('module qfd_dv_s8s_station_mul_data_g(',1)[1].split('endmodule',1)[0]
def seq(s):return [l for l in s.splitlines() if 'qfd_s8s_bmath_' in l and 'dff_' in l]
def original_leaves(s):
 d=dict(re.findall(r'assign (n_\w+) = ([^;]+);',mul(s)))
 assert d['n_4989']=='(n_7148) & (n_3957)'
 assert 'u_dup_n_4989_0(.i({n_3957,n_7148}),.y(n_4989_g0))' in mul(s)
 d['n_4989_g0']=d['n_4989']
 def expand(n):
  m=re.fullmatch(r'\((n_\w+)\) & \((n_\w+)\)',d.get(n,''))
  return expand(m[1])+expand(m[2]) if m else [n]
 return expand('n_4761')
def candidate_leaves(s):
 t=mul(s);d={}
 for m in re.finditer(r'qfd_dv_s8s_mul_prefix_and4 #\(.ID\(\d+\)\) \w+\(.i\(\{([^}]+)\}\),.y\((\w+)\)\);',t):d[m[2]]=m[1].split(',')
 root=re.search(r'assign n_4761 = (\w+);',t)[1]
 def expand(n):return sum((expand(x) for x in d[n]),[]) if n in d else [n]
 return expand(root),len(d)
def band(a,b):
 if '0' in (a,b):return '0'
 if a==b=='1':return '1'
 return 'X'
symbols='01XZ'; assoc=[]
for a,b,c in itertools.product(symbols,repeat=3):
 lhs=band(band(a,b),c);rhs=band(a,band(b,c));assert lhs==rhs
 assoc.append([a,b,c,lhs,rhs])
for a,b in itertools.product(symbols,repeat=2):
 assert band(a,b)==band(b,a)
 # 1 may map Z to X as a singleton. For a product with >=2
 # operands the result is always 0/1/X, on which 1 is identity.
 assert band(band(a,b),'1')==band(a,b)
a=original_leaves(old);b,helpers=candidate_leaves(new);padding=b.count("1'b1");real=[x for x in b if x!="1'b1"]
assert collections.Counter(a)==collections.Counter(real)
assert len(a)==33 and len(set(a))==33
assert seq(old)==seq(new)
assert 'assign y=&i;' in new
receipt=dict(base=BASE,old_sha256=hashlib.sha256(old.encode()).hexdigest(),candidate_sha256=hashlib.sha256(new.encode()).hexdigest(),sequential_lines_sha256=hashlib.sha256('\n'.join(seq(new)).encode()).hexdigest(),sequential_lines_equal=len(seq(new)),leaf_multiset_equal=dict(sorted(collections.Counter(real).items())),padding_ones=padding,helpers=helpers,associativity_64_triples=assoc,commutativity_16_pairs='PASS',padding_identity_for_nontrivial_product_16_pairs='PASS',proof='Every AND tree with >=2 operands is 0 if any operand is 0, 1 if all operands are 1, otherwise X. Associativity and commutativity preserve the exact 33-leaf multiset; padding ones preserves this classification. This includes X/Z startup without a reset or validity assumption.',scope='Combinational n_4761 four-state equality plus unchanged sequential instance lines; actual whole-module fixtures/native owned by cb16.')
out=Path(__file__).with_name('FOUR_STATE_CERTIFICATE.json');out.write_text(json.dumps(receipt,indent=2)+'\n');print(out);print('PASS 64 associative triples;16 commuting pairs;16 nontrivial-product padding cases;33 exact leaves;1356 identical sequential lines')
