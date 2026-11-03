from pathlib import Path
from collections import Counter
import re,json
b=Path('.')
old=(b/'old_qfd_dv_s5_sc2_k79.sv').read_text();new=(b/'new_qfd_dv_s5_sc2_k79.sv').read_text();fix=(b/'gate0.v').read_text();gold=(b/'gold.v').read_text()
gen=re.compile(r'generate if \(HARD_PINREG\) begin : (\w+)\n(.*?)\nend else begin : \w+\n.*?\nend endgenerate',re.S)
def selected_true(m):
 scope,body=m[1],m[2]
 return re.sub(r'(qfd_s2_bmath_\w+\s*#\(\.ID\(\d+\)\)\s+)(\w+)(\s*\()',lambda x:x[1]+scope+'__'+x[2]+x[3],body)
def h1(t):
 t=gen.sub(selected_true,t);t=re.sub(r"HARD_PINREG\s*\?\s*1'b1\s*:\s*\w+","1'b1",t)
 return re.sub(r'HARD_PINREG\s*\?\s*\(([^()]*)\)\s*:\s*\w+',r'(\1)',t)
def prim(t):
 d={}
 for m in re.finditer(r'\b(qfd_s2_bmath_\w+)\s*#\(\.ID\((\d+)\)\)\s+(\w+)\s*\((.*?)\);',t):
  assert m[3]not in d;d[m[3]]=[m[1],int(m[2]),sorted((k,re.sub(r'\s+','',v))for k,v in re.findall(r'\.(\w+)\(([^()]*)\)',m[4]))]
 assert len(d)==len(re.findall(r"\bqfd_s2_bmath_\w+\s*#",t))
 return d
a,c,fg,fn=prim(old),prim(h1(new)),prim(gold),prim(h1(fix))
assert all(a.get(k)==v for k,v in fg.items())
assert all(c.get(k)==v for k,v in fn.items())
ra={k:v for k,v in a.items()if k not in fg};rc={k:v for k,v in c.items()if k not in fn}
assert ra==rc
assigns=lambda t:Counter(re.sub(r'\s+','',x)for x in re.findall(r'\bassign\s+([^;]+);',t))
aa,cc,ff=assigns(old),assigns(h1(new)),assigns(h1(fix));removed=aa-cc;added=cc-aa
assert not removed;assert not(added-ff)
used=set(v[0]for v in fn.values());act=(b/'actual_helpers.sv').read_text();arch=(b/'helpers.sv').read_text();helper={}
for t in used:
 get=lambda s:re.sub(r'\s+','',re.search(r'\bmodule '+t+r'\b.*?endmodule',s,re.S)[0])
 helper[t]=get(act)==get(arch);assert helper[t]
out={'scope':'EXACT_HARD1_LITERAL_CHANGED_FOOTPRINT_COVERAGE_OF_ARCHIVED_LOCAL_LEMMA','source_old':'051340895d9','source_new':'98bbbbd8184','archived_fixture':'41612e22eac','old_full_primitives':len(a),'new_HARD1_full_primitives':len(c),'old_selected_primitives':len(fg),'new_HARD1_selected_primitives':len(fn),'outside_selected_primitives_equal':len(ra),'removed_outside_assignments':sum(removed.values()),'added_assignments_all_in_selected_lemma':dict(added),'actual_vs_archived_used_helper_bodies_equal':helper,'verdict':'PASS','limits':'Source-literal composition audit of existing first-capture/four-step lemma only. No fresh wholeLEC, unrestricted invalid-state/reset/analog proof, native mapped parent count or adoption.'}
(b/'hard1_footprint_coverage.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
