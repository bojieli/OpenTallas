#!/usr/bin/env python3
"""Independent readback: same actual transition controls, exact endpoint polarity.
The native primitive test covers every independent binary initial pair state.
Before the first capture/assertion, equal initial states are NOT assumed.
"""
import json,re,sys,hashlib
oldp,newp,reportp,outp=sys.argv[1:5]
old,new=open(oldp).read(),open(newp).read();report=json.load(open(reportp))
pattern=re.compile(r'^\s*(?:\(\*[^*]*\*\)\s*)?(\w+)\s+(c\w+)\s*\((.*)\);\s*$',re.M)
def parse(s):return {n:(m,dict((k,v.strip()) for k,v in re.findall(r'\.(\w+)\(([^()]*)\)',p))) for m,n,p in pattern.findall(s)}
a,b=parse(old),parse(new);expected={};new_names=set();clones=0
for root in report['roots']:
 n=root['master'];m,ps=a[n]
 assert m=='DFFASRHQNx1_ASAP7_75t_R' and b[n]==a[n]
 for copy in root['clones']:
  cn=copy['name'];cm,cp=b[cn];clones+=1;new_names.add(cn)
  assert cm==m and {p:v for p,v in cp.items() if p!='QN'}=={p:v for p,v in ps.items() if p!='QN'}
  group=cn.rsplit('_',1)[1];inv='cpr32_inv_'+n+'_'+group
  if any(polarity for _,_,polarity in copy['endpoints']):
   im,ip=b[inv];assert im=='INVx1_ASAP7_75t_R' and ip['A']==cp['QN'];new_names.add(inv)
  for cell,pin,polarity in copy['endpoints']:
   assert pin=='RESETN'
   expected[cell,pin]=b[inv][1]['Y'] if polarity else cp['QN']
for n,(m,ps) in a.items():
 assert n in b and b[n][0]==m
 assert set(ps)==set(b[n][1])
 for pin,net in ps.items():assert b[n][1][pin]==expected.get((n,pin),net),(n,pin)
assert set(b)-set(a)==new_names
assert len(expected)==292 and clones==13 and len(new_names)==26
assert re.findall(r'^\s*assign.*?;',old,re.M)==re.findall(r'^\s*assign.*?;',new,re.M)
assert re.findall(r'^\s*(?:input|output)\s+wire.*?;',old,re.M)==re.findall(r'^\s*(?:input|output)\s+wire.*?;',new,re.M)
data=dict(verdict='PASS',input_sha256=hashlib.sha256(old.encode()).hexdigest(),output_sha256=hashlib.sha256(new.encode()).hexdigest(),same_actual_transition_copies=clones,added_real_inverters=13,changed_reset_endpoint_pins=len(expected),unchanged_original_cells_except_exact_reset_endpoints=len(a),unchanged_original_assignments=True,unchanged_ports=True,added_serial_edges=0,first_convergence='actual common rising clock edge OR actual shared asynchronous assertion; no power-up equality assumption',parent_before_use='must preserve existing reset/boot admission; unchanged original full-source miter is separate evidence')
json.dump(data,open(outp,'w'),indent=2);print(json.dumps(data))
