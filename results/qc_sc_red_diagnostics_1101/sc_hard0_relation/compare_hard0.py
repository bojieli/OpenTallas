from pathlib import Path
import re,json,hashlib
b=Path('.')
old=(b/'old_qfd_dv_s5_sc2_k79.sv').read_text();new=(b/'new_qfd_dv_s5_sc2_k79.sv').read_text()
gen=re.compile(r'generate if \(HARD_PINREG\) begin : \w+\n.*?\nend else begin : \w+\n(.*?)\nend endgenerate',re.S)
new,n=gen.subn(lambda m:m[1],new)
new,n_const=re.subn(r"HARD_PINREG\s*\?\s*1'b1\s*:\s*(\w+)",r'\1',new)
new,n_mask=re.subn(r'HARD_PINREG\s*\?\s*\([^()]*\)\s*:\s*(\w+)',r'\1',new)
assert not re.search(r'generate if \(HARD_PINREG\)',new)
inst_re=re.compile(r'\b(qfd_s2_bmath_\w+)\s*#\(\.ID\((\d+)\)\)\s+(\w+)\s*\((.*?)\);')
port_re=re.compile(r'\.(\w+)\(([^()]*)\)')
class UF:
 def __init__(self):self.p={}
 def get(self,x):
  if x not in self.p:self.p[x]=x
  if self.p[x]!=x:self.p[x]=self.get(self.p[x])
  return self.p[x]
 def union(self,a,c):
  a,c=self.get(a),self.get(c)
  if a!=c:self.p[max(a,c)]=min(a,c)
def model(text):
 u=UF();assigns=re.findall(r'\bassign\s+([^;]+);',text)
 for a in assigns:
  m=re.fullmatch(r'\s*(\w+)\s*=\s*(\w+)\s*',a)
  if m:u.union(m[1],m[2])
 def canon(s):return re.sub(r'\b(?:n_\d+|sc_pin_\w+)\b',lambda m:u.get(m[0]),re.sub(r'\s+','',s))
 inst={}
 for m in inst_re.finditer(text):
  ports=port_re.findall(m[4]);assert ports,(m[3],m[4])
  assert 'HARD_PINREG' not in m[4]
  assert m[3] not in inst,m[3]
  inst[m[3]]=[m[1],int(m[2]),sorted((k,canon(v))for k,v in ports)]
 rest=[]
 for a in assigns:
  if re.fullmatch(r'\s*\w+\s*=\s*\w+\s*',a):continue
  # Unused HARD1-only shared data wires are tied0 in HARD0 and have no old subject.
  if re.match(r"\s*sc_pin_rstcap_\d+\s*=\s*1'b0\s*$",a):continue
  rest.append(canon(a))
 return inst,sorted(rest)
a,aa=model(old);c,cc=model(new)
missing=sorted(set(a)-set(c));added=sorted(set(c)-set(a));changed={k:[a[k],c[k]]for k in set(a)&set(c)if a[k]!=c[k]}
summary={'scope':'STATIC_LITERAL_HARD0_BRANCH_SELECTION_PLUS_ALIAS_NORMALIZED_PRIMITIVE_GRAPH_COMPARISON','source_old':'051340895d9','source_new':'98bbbbd8184','conditional_blocks_selected_default0':n,'reset_data_ternaries_resolved':n_const,'reset_mask_ternaries_resolved':n_mask,'old_primitives':len(a),'new_HARD0_primitives':len(c),'old_declared_FFs':sum(v[0].startswith('qfd_s2_bmath_dff')for v in a.values()),'new_HARD0_declared_FFs':sum(v[0].startswith('qfd_s2_bmath_dff')for v in c.values()),'missing_instances':missing,'added_instances':added,'changed_primitives':changed,'remaining_nontrivial_assignments_equal':aa==cc,'remaining_old_assignment_n':len(aa),'remaining_new_assignment_n':len(cc),'verdict':'PASS'if not(missing or added or changed)and aa==cc else'FAIL','limitations':'Static literal branch/alias graph relation, not Yosys/native elaboration, sequential proof or mapped/default physical count. No source/count adoption.'}
(b/'hard0_static_relation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items()if k!='changed_primitives'},indent=2));print('CHANGED first',str(dict(list(changed.items())[:3]))[:1500])
