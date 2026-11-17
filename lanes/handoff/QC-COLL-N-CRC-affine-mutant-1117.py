exec(open('/srv/opentallas-scratch2/claude/qc-pinaccess-o/coll_n_hold80_1116/lec5_diag3_normalize.py').read().split('rec=dict(')[0])
from functools import lru_cache
crc_roots=[214025,181723];cuts={};needed=set()
def scan(l):
 v=l>>1
 if not v or v in needed:return
 needed.add(v);ts,c0=b._parity(2*v)
 if ts and all(x>>1<=b.ni for x in ts):cuts[v]=(tuple(sorted(x>>1 for x in ts)),c0);return
 assert v>b.ni
 k=v-b.ni-1;scan(b.ands[2*k]);scan(b.ands[2*k+1])
for l in crc_roots:scan(l)
def vec(ts):
 x=0
 for v in ts:x^=1<<v
 return x
pv={}
for ts,c0 in cuts.values():
 x=vec(ts)
 while x:
  k=x.bit_length()-1
  if k in pv:x^=pv[k]
  else:pv[k]=x;break
for k in sorted(pv):
 for q in pv:
  if q>k and (pv[q]>>k)&1:pv[q]^=pv[k]
ks=sorted(pv,reverse=True);basis=[pv[k] for k in ks]
def coords(ts):
 x=vec(ts);cc=0
 for j,k in enumerate(ks):
  if x>>k&1:x^=pv[k];cc^=1<<j
 assert x==0
 return cc
c=m.Aig();ci=[c.add_input('exact_basis_'+str(j)) for j in range(len(basis))];cm={0:0}
rowreceipt=[]
for v,(ts,constant) in cuts.items():
 cc=coords(ts);l=constant
 for j,inp in enumerate(ci):
  if cc>>j&1:l=c.XOR(l,inp)
 cm[v]=l;rowreceipt.append(dict(original_node=v,pis=list(ts),constant=constant,basis_coordinates=hex(cc)))
cl=lambda l:cm[l>>1]^(l&1)
for v in sorted(needed):
 if v in cm:continue
 k=v-b.ni-1;cm[v]=c.AND(cl(b.ands[2*k]),cl(b.ands[2*k+1]))
cr=[cl(l) for l in crc_roots];eq=c.XOR(*cr);c.outs=[eq];c.onames=['actual_crc_bad_equivalence'];c.write(out/'crc_basis_identity.aig')
rec=dict(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),actual_crc_boundary_literals=crc_roots,exact_affine_cuts=len(cuts),independent_linear_basis_rank=len(basis),basis_rref=[hex(x) for x in basis],affine_rows=rowreceipt,crc_basis_roots=cr,equivalence_root=eq,small_identity_ands=len(c.ands)//2,scope='Exact row-basis substitution of actual CRC-only Boolean boundary DAG, constants retained. Each original affine cut verified as exact basis combination; arbitrary independent basis inputs cover all physical PI cases. Not source RTL rewrite or fullLEC retry.')
(out/'crc_basis_certificate.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({k:v for k,v in rec.items() if k not in ['basis_rref','affine_rows']},indent=2),flush=True)
# Measure the small Boolean identity, then prepare an actual physical-PI branch mutation.
def cclose(ls):
 seen=set();ps=set();st=[l>>1 for l in ls]
 while st:
  v=st.pop()
  if not v:continue
  if v<=c.ni:ps.add(v);continue
  if v in seen:continue
  seen.add(v);k=v-c.ni-1;st.extend([c.ands[2*k]>>1,c.ands[2*k+1]>>1])
 return seen,ps
ns,ps=cclose([eq]);rec['identity_reachable_ands']=len(ns);rec['identity_basis_support']=len(ps)
actual_pis=sorted({v for ts,co in cuts.values() for v in ts});mutpi=actual_pis[len(actual_pis)//2];mm={0:0}
for v,(ts,co) in cuts.items():mm[v]=cm[v]^(mutpi in ts)
ml=lambda l:mm[l>>1]^(l&1)
for v in sorted(needed):
 if v in mm:continue
 k=v-b.ni-1;mm[v]=c.AND(ml(b.ands[2*k]),ml(b.ands[2*k+1]))
mutroot=c.XOR(ml(crc_roots[0]),cr[1]);c.outs=[mutroot];c.onames=['one_actual_input_bit_flip_in_left_crc_only'];c.write(out/'crc_basis_mutant.aig')
rec['mutant']=dict(real_original_pi_index=mutpi,scope='Invert one existing saved-miter physical-input coordinate only within the left actual CRC predicate; every affine leaf toggles precisely when its exact row includes that PI',affected_affine_cuts=sum(mutpi in ts for ts,co in cuts.values()),root=mutroot)
# Prepare exact outer graph with both CRC boundary literals represented by one unconstrained symbol.
z=m.Aig();zm={0:0}
for v in range(1,b.ni+1):zm[v]=z.add_input('saved_pi_'+str(v))
sym=z.add_input('CERTIFIED_actual_crc_bad');reps={l>>1:sym^(l&1) for l in crc_roots};ns=set();st=[l>>1 for l in nroots]
while st:
 v=st.pop()
 if v<=b.ni or v in ns:continue
 ns.add(v);k=v-b.ni-1;st.extend([b.ands[2*k]>>1,b.ands[2*k+1]>>1])
zl=lambda l:zm[l>>1]^(l&1)
for v in sorted(ns):
 if v in reps:zm[v]=reps[v]
 else:
  k=v-b.ni-1;zm[v]=z.AND(zl(b.ands[2*k]),zl(b.ands[2*k+1]))
z.outs=[zl(l) for l in nroots];z.onames=names;z.write(out/'certified_outer_three.aig');rec['outer_roots_after_crc_identity']=z.outs
(out/'crc_basis_certificate.json').write_text(json.dumps(rec,indent=2)+'\n');print('FINAL',dict(identityAND=rec['identity_reachable_ands'],basis_support=rec['identity_basis_support'],mutant=rec['mutant'],outer_roots=z.outs),flush=True)
