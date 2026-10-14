#!/usr/bin/env python3
"""Bind actual cut IDX source graph and lower-bound area; no slot or clock grant."""
import argparse,json,subprocess
from pathlib import Path
from report import digest


def build(repo,revision):
    path='results/arch/native_idx_parent_1014/cut_edab82fb5/request_graph.json'
    raw=subprocess.check_output(['git','show',revision+':'+path],cwd=repo);d=json.loads(raw)
    for source,sha in d['source_sha256'].items():
        data=subprocess.check_output(['git','show',revision+':'+source],cwd=repo)
        if digest(data)!=sha:raise ValueError('source hash mismatch: '+source)
    macros=d['catalog_macros'];macro_count=sum(x['instances'] for x in macros.values());macro_area=sum(x['instances']*x['width_um']*x['height_um'] for x in macros.values())
    if abs(macro_area-d['macro_outline_sum_um2'])>1e-5:raise ValueError('catalog area mismatch')
    old_area=4*2000.16*2646;lower=macro_area+d['related_leaf_outline_lower_bound_um2']
    return {'schema':'opentallas.idx_cut_feasibility.v1','request_revision':revision,'request_path':path,'request_sha256':digest(raw),'all_source_hashes_verified':len(d['source_sha256']),'actual_clock_names':len(d['source_clock_entries']),'max_retained_glue_bits_per_root':max(d['retained_bits_including_inferred_buffers_by_clock'].values()),'actual_catalog_macro_instances':macro_count,'catalog_macro_outline_mm2':macro_area/1e6,'related_leaf_lower_bound_mm2':d['related_leaf_outline_lower_bound_um2']/1e6,'related_leaf_plus_actual_macro_mm2':lower/1e6,'four_legacy_slots_mm2':old_area/1e6,'lower_bound_ratio_vs_legacy_slots':lower/old_area,'fresh_ready_nominal_sinks':d['fresh_ready_leaf_nominal_sinks'],'fresh_ready_physical_accepted':d['fresh_ready_leaf_physical_accepted'],'actual_driver_abi_assigned':d['actual_driver_abi_assigned'],'assigned_slots':d['assigned_slots'],'physical_period_or_slew_proven':d['physical_period_or_slew_proven'],'functional_bench_reference_ps':d['functional_bench_period_reference_ps'],'qualified':False,'full_cut_numeric_proof':'source987dcdb69/unit2762217 owner reported EXIT0 fullgold; immutable receipt publication pending; mutation suite pending','unquantified_area':['fresh ready-leaf actual physical change','glue implementation and clock/reset delivery','macro halos/route/pin/PG channels'],'catalog_macros':macros,'previous_oversized_root_source_remains_history':True}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--repo',type=Path,required=True);a.add_argument('--revision',required=True);a.add_argument('--output',type=Path,required=True);p=a.parse_args();p.output.write_text(json.dumps(build(p.repo,p.revision),indent=2)+'\n')
