#!/usr/bin/env python3
"""Classify retained KV-only logs/sources without elaborating or simulating."""
import argparse,hashlib,json,re,tarfile
from collections import Counter
from pathlib import Path

def h(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packet',type=Path,required=True);a=p.parse_args();d=a.packet
 r=json.loads((d/'g9_KV_completion_terminal.json').read_text());m=json.loads((d/'g9_KV_dependency_manifest.json').read_text());old=json.loads((d/'g9_warning_classification_interim.json').read_text());base=json.loads((d/'g9_configured_terminal_r1.json').read_text())
 assert r['exit_code']==0 and r['status']=='KV_ONLY_SYNTAX_ELAB_EXIT0'
 with tarfile.open(d/'g9_KV_completion_source_r1.tgz') as t:files={x.name:t.extractfile(x).read() for x in t.getmembers() if x.isfile()}
 assert {k:h(v) for k,v in files.items()}==r['staged_files_sha256']
 graph=old['conservative_all_branch_module_edges'].copy();graph.update(m['conservative_module_closure']);parents={'ot_s81sl_slice_kv512':None};todo=list(parents)
 while todo:
  n=todo.pop()
  for c in graph.get(n,[]):
   if c not in parents:parents[c]=n;todo.append(c)
 # All existing module files except the explicitly audited fastfp companion
 # projection are byte-identical. Additional known module edges come from
 # the owner-pinned conservative16file dependency closure.
 oldfacts=[x for x in old['cases']['s0N_aggregate']['entries'] if x['class']=='PINMISSING'];actual=[x for x in r['warnings'] if x.startswith('%Warning-PINMISSING:')]
 assert len(oldfacts)==len(actual)==30
 def suffix(s):return s.split('/src/',1)[1]
 rows=[]
 for fact,raw in zip(oldfacts,actual):
  assert suffix(raw)==suffix(fact['raw']);assert fact['parent_module'] not in parents
  rows.append({'raw':raw,'parent_module':fact['parent_module'],'child_module':fact['child_module'],'pin':fact['pin'],'direction':fact['direction'],'reachable_in_conservative_KV_cone':False})
 counts=dict(Counter(re.match(r'%Warning-([^:]+)',x)[1] for x in r['warnings']));assert counts=={'PINMISSING':30,'ALWNEVER':1,'MULTIDRIVEN':2,'UNOPTFLAT':4}
 src='src/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv';norm='src/rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv'
 out={'schema':'opentallas.s81.kv_compile_terminal_collection.v1','status':'KV_ONLY_SYNTAX_ELAB_EXIT0_WITH_WARNINGS','unit':'ot-epyc5/oth-ubuntu-3285750-1792624109','exit_code':0,'top':r['top'],'params':r['params'],'defines':r['defines'],'source_ref':r['selected_ref'],'source_archive_verified_files':len(files),'source_file_count':len(files)-1,'warnings':counts,'warning_total':sum(counts.values()),'pinmissing':{'classification':'ALL30_IN_UNREACHABLE_COMPANION_PARENTS_FOR_KV_TOP','inputs':5,'outputs':25,'entries':rows},'conservative_KV_graph':{n:graph.get(n,[]) for n in sorted(parents)},'graph_provenance':'Unchanged original191source/6define graph plus owner-pinned020 manifest conservative16file closure. Fastfp projection only removes explicitly overridden bodies; full0N changed-body audit00b1 retained separately. No whole-die reachability claim.','active_multidriven':{'count':2,'source':src[4:],'sha256':h(files[src]),'path':'ot_s81sl_slice_kv512.u_slice.u_xg.u_s','signals':['tq_v[0:1]','tb_v[0:1]'],'classification':'DISJOINT_ARRAY_PARITY_ELEMENTS_WITH_DISTINCT_ASYNC_RESET_EVENTS','declaration_lines':[177,178],'driver_lines':[365,366,367,369,371,374,375,377,379],'source_rule':'gp=0,1 generate each drives only tq_v[gp] and tb_v[gp] on posedge clk with own rs_t[gp]/rs_t[2+gp] async reset. No overlapping element drivers; global reset/phase semantics not qualified.'},'active_unoptflat':{'count':4,'source':norm[4:],'sha256':h(files[norm]),'path':'ot_s81sl_slice_kv512.u_slice.u_xf.g_cp[3].u_e','signals':['V','VD','oa','ob'],'classification':'ARRAY_AGGREGATE_DEPENDENCIES_WITH_STRICTLY_ORDERED_INDEX_GRAPH','source_rule':'V/VD combinational n reads2*n,1<=n<NVP until registered boundaries; oa/ob C+1 readsC from constantindex0. Same exact norm body/lines324,333,368,373,374,377 as sealed0N source obligation; no per-index cycle.'},'active_alwnever':{'count':1,'source':'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv','line':646,'path':'ot_s81sl_slice_kv512.u_slice.g_c1.u_xr.u','classification':'UNUSED_CONSTANT_FCORE_HELPER_IN_FOREG0_BRANCH','source_rule':'always@* fcore=0 in direct-fault path; source unchanged, no behavioral qualification.'},'verilator_report':'5.050; wall376.816s cpu376.805s allocated28685.281MB bld0.000; no simulator','preserved_original_0N_case':base['cases']['s0N_aggregate'],'original_0N_rerun':False,'preserved_original_KV_failure':base['cases']['ot_s81sl_slice_kv512'],'preserved_G8_PQ_failure_commit':'f83d5919a9caed0f16bb80ed0e02a75bd36a401d','functional_qualified':False,'coherent_source_qualified':False,'global_programme_qualified':False,'physical_qualified':False,'simulation_performed':False,'file_sha256':{n:h((d/n).read_bytes()) for n in ['g9_KV_completion_terminal.json','g9_KV_completion_elab.log','g9_KV_completion_source_r1.tgz','g9_KV_dependency_manifest.json','g9_KV_dependencies.tar','g9_KV_completion_recipe.json','g9_0N_fastfp_audit.json','g9_warning_classification_interim.json']}}
 (d/'g9_KV_completion_collection.json').write_text(json.dumps(out,indent=1)+'\n');print(out['status'],counts,len(files))
if __name__=='__main__':main()
