from pathlib import Path
import tkinter,json,sys
p=Path(__file__).parent;t=tkinter.Tcl()
alias={}
for line in (p/'control16_replica_manifest.tcl').read_text().splitlines():
 a=t.splitlist(line)
 if len(a)==3 and a[1]=='::ot_control_copy_aliases':
  v=t.splitlist(a[2]);alias=dict(zip(v[::2],v[1::2]))
def root(n):
 seen=set()
 while n in alias:
  assert n not in seen;seen.add(n);n=alias[n]
 return n
def read(f):
 d={}
 for line in (p/f).read_text().splitlines():
  a=line.split('\t');k=tuple(a[:3]) if a[0]=='INPUT' else tuple(a[:2]);d[k]=a[3:] if a[0]=='INPUT' else a[2:]
 return d
a=read('control16_before_equations.tsv');b=read(sys.argv[1] if len(sys.argv)>1 else 'control16_after_equations.tsv');errors=[]
for k,v in a.items():
 if b.get(k)!=v:errors.append((k,v,b.get(k)))
newmasters=[k[1] for k in b if k[0]=='MASTER' and k not in a]
inputs=0
bycell={}
for k,v in b.items():
 if k[0]=='INPUT':bycell.setdefault(k[1],[]).append((k,v))
for n in newmasters:
 o=root(n)
 if a.get(('MASTER',o))!=b[('MASTER',n)]:errors.append(('copy_master',n,o))
 for k,v in bycell.get(n,[]):
  inputs+=1
  if a.get(('INPUT',o,k[2]))!=v:errors.append(('copy_input',n,o,k[2],v,a.get(('INPUT',o,k[2]))))
report=dict(verdict='PASS' if not errors else 'FAIL',proof='Exact source-master and input-equation congruence, with induction over corresponding state',initial_state_contract='Corresponding FF states established by existing reset/program initialization; no claim for unrelated uninitialized shadow states',original_nontransparent_masters=sum(k[0]=='MASTER' for k in a),original_input_equations=sum(k[0]=='INPUT' for k in a),original_ports=sum(k[0]=='PORT' for k in a),original_output_equations=sum(k[0]=='OUTPUT' for k in a),new_nontransparent_driver_copies=len(newmasters),new_copy_input_equations=inputs,errors=errors[:20],error_count=len(errors))
(p/('control16_inductive_equivalence_mutant.json' if len(sys.argv)>1 else 'control16_inductive_equivalence.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert not errors
