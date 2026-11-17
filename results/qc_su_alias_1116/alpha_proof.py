from pathlib import Path
import re,json,hashlib,difflib
BASE=Path('/srv/opentallas-scratch2/claude/fable-fix-qc-cbglue/headseg44/group44/w1_44868/src/rtl/physical')
OUT=Path('/srv/opentallas-scratch2/claude/qc-types-r/aliasprep');OUT.mkdir(parents=True,exist_ok=True)
sha=lambda x:hashlib.sha256(x).hexdigest()
LEX=re.compile(r'\s+|//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\\[^\s]+|[A-Za-z_$][A-Za-z0-9_$]*|.',re.S)
ID=re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*\Z')
def tokens(s):
 return [m.group() for m in LEX.finditer(s) if not m.group().isspace() and not m.group().startswith(('//','/*'))]
def alpha(s,lane):
 rename={}; out=[]
 for t in tokens(s):
  n=t
  if ID.fullmatch(t):
   if t==f'qfd_qc_su_lane_w_l{lane}_m44s1':n='qfd_qc_su_lane_w_lLANE_m44s1'
   n=re.sub(r'u_(exp|head|lrly|rcp|rsq)'+str(lane)+r'(?=_|$)',r'u_\1LANE',n)
   if n!=t:rename[t]=n
  out.append(n)
 return out,rename
raw={i:(BASE/f'qfd_qc_su_lane_w_l{i}_m44s1.sv').read_bytes() for i in range(1,8)}
norm={};maps={}
for i,b in raw.items():norm[i],maps[i]=alpha(b.decode(),i)
b=norm[1]; results=[]
for i in range(1,8):
 dif=[]
 if norm[i]!=b:
  for index,(bt,lt) in enumerate(zip(b,norm[i])):
   if bt!=lt:
    dif.append(dict(index=index,baseline=bt,lane=lt))
    if len(dif)>=32:break
  if len(norm[i])!=len(b):dif.append(dict(token_count_baseline=len(b),token_count_lane=len(norm[i])))
 results.append(dict(lane=i,path=str(BASE/f'qfd_qc_su_lane_w_l{i}_m44s1.sv'),source_sha256=sha(raw[i]),normalized_sha256=sha('\n'.join(norm[i]).encode()),token_count=len(norm[i]),alpha_identity=norm[i]==b,renamed_identifiers=maps[i],differences=dif))
# Swap two distinct real top input bits on a disposable text copy only.
s=raw[1].decode();p=re.compile(r'(assign\s+[^;=]+\s*=\s*)(c_i\[\d+\])(\s*;)');matches=list(p.finditer(s));pair=next(((a,z) for a in matches for z in matches if a.start()<z.start() and a[2]!=z[2]),None)
assert pair,'No two real distinct top input assignments found'
a,z=pair; mutant=s[:a.start(2)]+z[2]+s[a.end(2):z.start(2)]+a[2]+s[z.end(2):]
mn,_=alpha(mutant,1);assert mn!=b
(OUT/'mutant_swap_inputs.sv').write_text(mutant)
receipt=dict(scope='Entire actual wrapper token stream; comments/whitespace discarded; no literal, arithmetic, width, port or connection normalization',allowed_alpha_renames=['qfd_qc_su_lane_w_lN_m44s1 module identifier','u_{exp,head,lrly,rcp,rsq}N substrings within identifiers only'],semantic_basis='Identical full wrapper token streams under a capture-free renaming denote the same transition/output system for arbitrary identical stateful leaf bodies and identical initial states',verdict='PASS' if all(x['alpha_identity'] for x in results) else 'FAIL_NON_ALPHA',results=results,negative_control=dict(change='Swap two actual distinct input assignment RHS bits on disposable W1 text',assignments_before=[a.group(),z.group()],assignments_after=[a[1]+z[2]+a[3],z[1]+a[2]+z[3]],mutant_sha256=sha(mutant.encode()),checker_verdict='REFUSED',normalized_equals_baseline=False),source_files_unchanged={str(BASE/f'qfd_qc_su_lane_w_l{i}_m44s1.sv'):sha((BASE/f'qfd_qc_su_lane_w_l{i}_m44s1.sv').read_bytes())==sha(raw[i]) for i in raw})
(OUT/'alpha_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(verdict=receipt['verdict'],lanes=[dict(lane=x['lane'],equal=x['alpha_identity'],tokens=x['token_count'],diffs=len(x['differences'])) for x in results],mutant='REFUSED')))
