exec(open('/srv/opentallas-scratch2/claude/qc-pinaccess-o/coll_n_hold80_1116/lec5_diag3_normalize.py').read().split('rec=dict(')[0])
from functools import lru_cache
crc_roots=nroots;cuts={};needed=set()
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
cr=[cl(l) for l in crc_roots];eq=None;c.outs=cr;c.onames=names;c.write(out/'joint_three.aig')
rec=dict(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),actual_crc_boundary_literals=crc_roots,exact_affine_cuts=len(cuts),independent_linear_basis_rank=len(basis),basis_rref=[hex(x) for x in basis],affine_rows=rowreceipt,crc_basis_roots=cr,equivalence_root=eq,small_identity_ands=len(c.ands)//2,scope='Exact joint affine substitution of only original3CP cones including all retained outer/header/slot PI unit-vectors. Fixed affine constants. No independent CRC-symbol relaxation; every nonlinear fringe unchanged. OriginalUNPROVEN untouched.')
(out/'joint_basis_certificate.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({k:v for k,v in rec.items() if k not in ['basis_rref','affine_rows']},indent=2),flush=True)
