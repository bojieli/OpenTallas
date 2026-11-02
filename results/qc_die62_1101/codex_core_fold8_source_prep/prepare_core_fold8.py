import json,re,sys,hashlib,subprocess,collections
from pathlib import Path
B=Path.cwd();W=Path('/srv/opentallas-scratch2/claude/wt/codex-qc62-proposal8-bind-1101')
sys.path.insert(0,str(W/'tools/die_plan'));import cells
p=json.load(open(W/'physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json'));t=p['partition_types']['coll_core'];r=json.load(open(B/'inputs/receipt.json'));km=json.load(open(B/'inputs/kit_rtl.json'));s=(B/'inputs/core_stat.txt').read_text();v=(B/'inputs/core_synth.v').read_text();counts=cells.parse_stat(s);assert counts['qfd_qc_coll_core_part']==671634 and counts['ot_coll_fold_slice']==57002
blk=s.split('=== design hierarchy ===')[-1];hard={};views={}
for n,h in km['hard_macros'].items():
 vals={int(x)for x in re.findall(r'^\s*(\d+)\s+\S+\s+(?:\d+|-)\s+\S+\s+'+re.escape(n)+r'\s*$',blk,re.M)};assert len(vals)==1,(n,vals);hard[n]=vals.pop()
 lf=Path(h['lef']).read_text();wh=re.findall(r'\bSIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)\s*;',lf);assert len(wh)==1
 lib=next(Path(f)for f in h['libs']if f.endswith('_tt.lib'));aa=re.findall(r'\barea\s*:\s*([0-9.eE+-]+)\s*;',lib.read_text());assert len(aa)==1
 views[n]=dict(native_instances=hard[n],lef=h['lef'],lef_size_um=list(map(float,wh[0])),tt_lib=str(lib),tt_lib_area_um2=float(aa[0]))
assert hard==dict(collections.Counter(h['module']for h in t['hard_cores']))
inst=[]
for m in re.finditer(r'^\s*ot_coll_fold_slice\s+([^\s(]+)\s*\((.*?)\);',v,re.M|re.S):
 ports={k:z.strip()for k,z in re.findall(r'\.(clk|rst_n|red_in|v_out|e_out)\(([^)]*)\)',m[2])};assert ports['clk']=='clk' and ports['rst_n'].lstrip(chr(92))=='u_bound.rst_n';inst.append(dict(instance=m[1].lstrip('\\'),ports=ports))
assert len(inst)==8
# Preserve the actual mapped leaf and its retained module dependencies; no re-synthesis.
blocks={m[1].lstrip('\\'):m[0]for m in re.finditer(r'^module\s+([^\s(]+).*?^endmodule\b[^\n]*',v,re.M|re.S)}
todo=['ot_coll_fold_slice'];selected={}
while todo:
 n=todo.pop()
 if n in selected:continue
 body=blocks[n];selected[n]=body
 for typ in re.findall(r'^\s*([^\s(]+)\s+[^\s(]+\s*\(',body,re.M):
  typ=typ.lstrip('\\')
  if typ in blocks and typ not in selected:todo.append(typ)
(B/'native_fold_leaf_mapped.v').write_text('\n\n'.join(selected[n]for n in sorted(selected))+'\n')
macro_total=sum(hard.values());std=r['native_total_leaves']-macro_total;foldcount=counts['ot_coll_fold_slice'];remaining=std-8*foldcount
macro_lib_area=sum(hard[n]*views[n]['tt_lib_area_um2']for n in hard)
leaf=W/'rtl/rom/ot_coll_fold_slice.sv';src=leaf.read_text();assert 'parameter integer N = 4' in src and 'parameter integer ADD_LAT = 7' in src and 'parameter integer SEAM = 1' in src
oldlef=subprocess.check_output(['git','-C',str(W),'show','HEAD:physical/qwen_die_masters/hard/ot_coll_fold_slice/ot_coll_fold_slice.lef'],text=True);size=re.findall(r'\bSIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)\s*;',oldlef);assert size==[('180','180')]
report=dict(status='SOURCE_CUT_PREP_NOT_RELEASED',source_context='Frozen candidate9/D762 native count; no627c projections mixed',actual_native_total=r['native_total_leaves'],actual_hard_macros=hard,actual_hard_macro_count=macro_total,actual_standard_cells=std,soft_cap=400000,cap_failure=std>400000,fold_module='ot_coll_fold_slice',fold_count_each=foldcount,fold_instances=inst,fold_source=str(leaf),fold_source_sha256=hashlib.sha256(leaf.read_bytes()).hexdigest(),fold_mapped_snapshot_modules=sorted(selected),native_mapped_top_area_um2=r['native_mapped_top_area_um2'],native_hard_macro_lib_area_um2=macro_lib_area,native_standard_lib_area_um2=r['native_mapped_top_area_um2']-macro_lib_area,actual_macro_views=views,proposal=dict(harden_once_reuse=8,new_partition_types=0,new_hardcore_view_types=1,clock='same existing clk',reset='same existing u_bound.rst_n; keep internal two-flop ot_coll_rst_leaf',parameters=dict(N=4,ADD_LAT=7,SEAM=1),existing_red_to_valid_edges=23,added_functional_pipeline_edges=0,remaining_soft_before_new_physical_infrastructure=remaining,parent_macro_instances_after=macro_total+8,parent_hierarchy_leaves_after_cut=remaining+macro_total+8,planning_leaf_outline_um=[180,180],planning_leaf_area_for_eight_um2=8*180*180,footprint_reference='Existing10-11 routed180square view is planning reference only, NOT a currentSIGNED or source-equivalence claim',source_action='Harden eight already-real retained folds as one current matched view; leave parent soft wrapper/transport; no extra seam flops',preserved=['both shared FT replicas','all external ports/stations/calendars','die edge','native data/reset/clock connectivity'],required_before_plan_adoption=['complete CORE macro/dataflow repack and <=405 stage reach','canonical627c clock/reset/PG projection and priced boot release','current leaf geometry review then genuine SIGNED view, never silently use old10-11 view','fresh parent-source census after physical infrastructure changes'],placement='UNRESOLVED; no hard-macro origins fabricated'),held=['GEN','P&R','STA','canonical adoption','old-view timing reuse'])
(B/'SOURCE_PROPOSAL.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:report[k]for k in ['status','actual_native_total','actual_hard_macro_count','actual_standard_cells','fold_count_each','native_standard_lib_area_um2']}));print(json.dumps(report['proposal'],indent=1))
