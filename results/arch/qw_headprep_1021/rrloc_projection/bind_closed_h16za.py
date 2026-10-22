#!/usr/bin/env python3
"""Bind exact published H16ZA child to existing HP13 source; no parent qualification."""
import hashlib,json,subprocess,argparse
from pathlib import Path
REV='9803869c2'
RECEIPT='results/arch/qko_h16za_collect_1021/closed_bind/binding_receipt.json'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(p):return subprocess.check_output(['git','show',REV+':'+p],cwd=ROOT)
def main():
 p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();out=Path(a.out).resolve()
 if out.exists() and any(out.iterdir()):raise SystemExit('fresh output required')
 out.mkdir(parents=True,exist_ok=True)
 r=json.loads((HERE/'closed_h16za/closed_child_input.json').read_text())
 verified={}
 for name,digest in {**r['source_hashes'],**r['view_hashes']}.items():
  data=blob(name)
  if sha(data)!=digest:raise SystemExit('published identity mismatch: '+name)
  dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);verified[name]=digest
 for local,original in [('native32_1r_param.v','native32_1r_param.v'),('native32_helpers.sv','native32_helpers.sv')]:
  own=ROOT/'rtl/qwen_dv/headprep13/h16za'/local
  assert sha(own.read_bytes())==r['source_hashes']['results/rtl/qw_head_safe32_1020/h16z/net/'+original]
 parent=(ROOT/'rtl/qwen_dv/headprep13/qfd_tt_ctlm_dv_lpf_hp13.sv').read_bytes()
 assert parent.count(b'ot_qfd_tt_ctlm_static_hr_safe32_native32_1r #(.STAGE_ME(1), .SEGCAL(1)) u_hr')==1
 spec=json.loads(blob('physical/ref_tile/qfd_tt_head_static_h16za/spec.json'))
 assert spec['params']=={} and spec['top']=='ot_qfd_tt_ctlm_static_hr_safe32_native32_1r'
 effective={'SEGCAL':1,'STAGE_ME':1};assert sha(json.dumps(effective,separators=(',',':'),sort_keys=True).encode())==r['parameter_binding_sha256']
 head=(ROOT/'rtl/qwen_dv/headprep13/h16za/native32_1r_param.v').read_text()
 import re
 for k,v in effective.items():assert re.search(r'parameter(?:\s+integer)?\s+'+k+r'\s*=\s*'+str(v)+r'\b',head)
 latency=json.loads(blob(r['view']+'/port_latency.json'));assert len(latency['ports'])==49
 recipe_path=HERE/'generated/qfd_tt_ctlm_dv_lpf_hp13_rrloc.json';recipe=json.loads(recipe_path.read_text());assert recipe['params']['XPF_TRANSPORT_EDGES']==21
 binding={'instance':'u_hr','module':spec['top'],'view':r['view'],'spec':'physical/ref_tile/qfd_tt_head_static_h16za/spec.json','effective_params':effective,'spec_overrides':{},'parameter_binding_sha256':r['parameter_binding_sha256'],'published_main':REV,'closure_record':r['closure_record'],'record_commit':r['record_commit'],'source_and_view_hashes':verified,'source_binding':'EXACT_SAME_NATIVE_AND_HELPERS','child_status':'TT_PATHFINDING_CLOSED','parent_status':'SOURCE_ONLY_NO_PARENT_VIEW_OR_RRLOC_OR_GEN_AGES'}
 recipe['hard_child_bindings']={'u_hr':binding}
 recipe['why']+=' Exact published H16ZA CLOSED child bound at u_hr; parent view/placed RRloc and selected GEN transport ages remain unqualified.'
 (out/'selected_hp13_recipe.json').write_text(json.dumps(recipe,indent=2)+'\n')
 result={'status':'EXACT_CLOSED_CHILD_BOUND_SOURCE_ONLY_PARENT','binding':binding,'original_hp13_recipe_sha256':sha(recipe_path.read_bytes()),'parent_symbolic_sha256':sha(parent),'native_parent_sha256':sha((ROOT/'rtl/qwen_dv/headprep13/native32/qfd_tt_ctlm_dv_hp13_rrloc_native32.sv').read_bytes()),'source_local_edges':4,'source_local_edges_basis':'compositional 1+(6-3), independently qualified source/native lockstep; no transport inference','construction_XPF':21,'actual_GEN_transport_edges':None,'scope':'No RTL or programme change; original negative routes and SS sensitivity retained in source binding receipt. No old child view, no old placed coordinates, no parent closure claim.'}
 (out/'binding_receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],len(verified),'hashes',len(latency['ports']),'ports')
if __name__=='__main__':main()
