#!/usr/bin/env python3
"""Separate allocated phase pages, proposed per-stage padding, uniform templates.

Counts come from verified ownership; these are not measured config reads or an
implemented PHW10 field. Source PHW6 remains a named failing binding.
"""
import argparse, collections, json
from pathlib import Path
import dsrom_full_owner_compiler as C

ROOT=Path(__file__).resolve().parents[1]


def derive(stats):
    if len(stats)!=58 or any(s['stage']!=i or s['compiled_NP']!=4096 or s['NBF']!=724 for i,s in enumerate(stats)):
        raise ValueError('different shared geometry')
    maxphw=max(s['control']['required_PHW'] for s in stats);perpage=4096*25*48;rows=[]
    for s in stats:
        c=s['control'];p=c['phase_count'];phw=c['required_PHW'];pages=1<<phw
        rows.append({'stage':s['stage'],'allocated_matrix_phase_count':p,'required_PHW':phw,
            'source_PHW6_template_bits':perpage*64,'allocated_unpadded_cfg_source_data_bits':perpage*p,
            'conditional_per_stage_minimum_width_template_pages':pages,
            'conditional_per_stage_minimum_width_template_bits':perpage*pages,
            'uniform_max_width_template_pages':1<<maxphw,'uniform_max_width_template_bits':perpage*(1<<maxphw),
            'uniform_unused_matrix_phase_pages':(1<<maxphw)-p})
    return {'scope':'Verified symbolic ownership phases, not a measured RTL configuration trace',
        'source_current_PHW':6,'source_current_PHW6_binding':'FAIL_INSUFFICIENT_PHASE_CAPACITY',
        'required_width_distribution':dict(collections.Counter(s['control']['required_PHW'] for s in stats)),
        'zero_matrix_phase_stage_IDs':[s['stage'] for s in stats if not s['control']['phase_count']],
        'allocated_total_matrix_phase_count':sum(r['allocated_matrix_phase_count'] for r in rows),
        'allocated_unpadded_cfg_source_data_bits_per_TP_rank':sum(r['allocated_unpadded_cfg_source_data_bits'] for r in rows),
        'conditional_per_stage_minimum_width_template_bits_per_TP_rank':sum(r['conditional_per_stage_minimum_width_template_bits'] for r in rows),
        'uniform_max_required_PHW':maxphw,'uniform_template_bits_per_TP_rank':sum(r['uniform_max_width_template_bits'] for r in rows),
        'source_current_PHW6_template_bits_per_TP_rank':sum(r['source_PHW6_template_bits'] for r in rows),
        'stage_profiles':rows,'no_width_profile_selected_or_implemented':True,
        'no_elimination_of_zero_or_unused_config_pages_credited':True,
        'all4096_pairs_and_all58_stages_charged':True,'physical_fit_qualified':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--readback',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    x=json.loads(a.readback.read_text());r=derive(x['stage_stats']);r.update(candidate=x['candidate'],
        compiler_sha256=C.sha(Path(__file__).read_bytes()),input_sha256=C.sha(a.readback.read_bytes()))
    a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:r[k] for k in ['required_width_distribution','allocated_total_matrix_phase_count','uniform_template_bits_per_TP_rank']}))
