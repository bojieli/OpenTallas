#!/usr/bin/env python3
"""Pure frozen-source all-branch 0N fastfp binding audit; no elaboration."""
import argparse, hashlib, importlib.util, json, re, subprocess, tarfile, tempfile
from pathlib import Path

def h(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packet',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 ref='8a495768f02316a7a8ad2e2bafef2f4d3741b741'
 def git(path):return subprocess.check_output(['git','show',ref+':'+path])
 graph=json.loads((a.packet/'g9_warning_classification_interim.json').read_text());edges=graph['conservative_all_branch_module_edges'];parent={'s0N_aggregate':None};todo=list(parent)
 while todo:
  n=todo.pop()
  for c in edges.get(n,[]):
   if c not in parent:parent[c]=n;todo.append(c)
 with tarfile.open(a.packet/'g9_configured_source_r1.tgz') as t:
  candidates=[m for m in t.getmembers() if m.name.endswith('/ot_hdc_fastfp.sv')];assert len(candidates)==1
  old=t.extractfile(candidates[0]).read();oldpath=candidates[0].name
 new=git('rtl/hdc/ot_hdc_fastfp.sv')
 with tempfile.TemporaryDirectory(prefix='s81-source-audit-') as td:
  path=Path(td)/'die_port_bind.py';path.write_bytes(git('tools/die_port_bind.py'))
  spec=importlib.util.spec_from_file_location('D',path);D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
  def mods(payload):
   txt=D.preprocess(D.strip_comments(payload.decode()),{x:'' for x in graph['defines']})
   return {m[1]:re.sub(r'\s+',' ',m[0]).strip() for m in re.finditer(r'\bmodule\s+(\w+)\b.*?\bendmodule\b',txt,re.S)}
  om,nm=mods(old),mods(new)
  rows={}
  for name in sorted(set(om)|set(nm)):
   path=[];n=name
   if n in parent:
    while n is not None:path.append(n);n=parent[n]
    path.reverse()
   rows[name]={'frozen_full_module_sha256':h(om[name].encode()) if name in om else None,'production_full_module_sha256':h(nm[name].encode()) if name in nm else None,'full_body_ports_default_params_equal':om.get(name)==nm.get(name),'reachable_in_all_branch_0N_graph':name in parent,'conservative_path':path}
 changed=[n for n,v in rows.items() if not v['full_body_ports_default_params_equal']]
 active=[n for n in changed if rows[n]['reachable_in_all_branch_0N_graph']]
 out={'schema':'opentallas.s81.0n_fastfp_binding_audit.v1','status':'CHANGED_BODY_REACHABLE_OBLIGATION' if active else 'ALL_CHANGED_FASTFP_BODIES_UNREACHABLE_IN_0N_SUPERSET','selected_ref':ref,'frozen_file':oldpath,'frozen_file_sha256':h(old),'production_file':'rtl/hdc/ot_hdc_fastfp.sv','production_file_sha256':h(new),'defines':graph['defines'],'graph_receipt_sha256':h((a.packet/'g9_warning_classification_interim.json').read_bytes()),'frozen_archive_sha256':h((a.packet/'g9_configured_source_r1.tgz').read_bytes()),'preprocessor_source_sha256':h(git('tools/die_port_bind.py')),'conservative_root':'s0N_aggregate','conservative_reachable_module_count':len(parent),'all_branch_edges':{n:edges.get(n,[]) for n in sorted(parent)},'module_comparisons':rows,'changed_modules':changed,'changed_reachable_modules':active,'qualification':'Pure full preprocessed module-body comparison including ports/default parameters and all known parameter branches. Missing KV-only definitions are outside successful 0N active elaboration; this does not prove KV or whole-die closure. Frozen0N446 inventory remains unchanged; productionff9 was NOT executed in 0N. No compiler, simulator, body replacement, or rerun.'}
 a.out.write_text(json.dumps(out,indent=1)+'\n');print(out['status'],changed,active)
if __name__=='__main__':main()
