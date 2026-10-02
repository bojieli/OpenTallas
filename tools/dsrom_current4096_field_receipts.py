#!/usr/bin/env python3
"""Independent metadata/abstract receipt audit, reusing retained owner inventory.
Never opens checkpoint or ROM payloads, runs engines, or changes original inputs.
"""
import argparse
import collections
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN='4c8b7f2d8e246bd09250051fc8f7cb3e3340f574'
OUT=ROOT/'results/uarch/dsrom_current4096_field_receipts_20261002'
CAT='results/quality/w16_w17_checkpoint_header_catalogue_20261001/'
RETURN='530aa6eb47e6842eacf1726c7f9941b6075f3c55'
NASH='09358afc825bc531d95575dff710ee554ab9ba60'
KEPLER='1e714c0a1c1f648ca8cf7a99012246acf94c87b5'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def source(path,ref=PIN):
    if path.endswith('.safetensors') or 'viamap.hex' in path:raise ValueError('Payload forbidden')
    return subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT)
def build():
    pins={}
    def read(path,ref=PIN):
        raw=source(path,ref);pins[ref+':'+path]=sha(raw);return raw
    def js(path,ref=PIN):return json.loads(read(path,ref))
    snapshot=json.loads((OUT/'inputs/snapshot_receipt.json').read_text())
    for name,s in snapshot.items():assert sha((OUT/'inputs'/name).read_bytes())==s['SHA256']
    inv=json.loads((OUT/'inputs/inventory.json').read_text())
    env=json.loads((OUT/'inputs/per_element_envelope.json').read_text())
    owner_prefix='results/uarch/dsrom_4096_reticle_inventory_20261002/'
    for name in ['inventory.json','per_element_envelope.json']:
        assert read(owner_prefix+name,NASH)==(OUT/'inputs'/name).read_bytes()
    for p,h in inv['source_sha256'].items():assert sha(read(p))==h
    cat=js(CAT+'catalogue.json');index=js(CAT+'model.safetensors.index.json')['weight_map']
    keys={};groups=collections.defaultdict(lambda:dict(tensor_count=0,stored_extent_bytes=0,dtypes=collections.Counter()))
    nonexpert=[];bf=[];routed=collections.Counter();families=collections.defaultdict(list)
    for shard,s in cat['shards'].items():
        raw=read(CAT+s['raw_header_path']);assert sha(raw)==s['raw_header_sha256']
        for key,t in json.loads(raw).items():
            if key=='__metadata__':continue
            assert key not in keys and index[key]==shard
            keys[key]=t
            expert=bool(re.match(r'layers\.\d+\.ffn\.experts\.\d+\.',key))
            layer=re.match(r'layers\.(\d+)\.(.+)',key)
            group='backbone_routed' if expert else 'backbone_nonexpert' if layer else 'other_roles'
            g=groups[group];g['tensor_count']+=1;g['stored_extent_bytes']+=t['data_offsets'][1]-t['data_offsets'][0];g['dtypes'][t['dtype']]+=1
            if expert:
                routed['weight' if key.endswith('.weight') else 'scale' if key.endswith('.scale') else 'other']+=1
            elif layer:
                item=dict(key=key,layer=int(layer[1]),dtype=t['dtype'],stored_shape=t['shape'],stored_extent_bytes=t['data_offsets'][1]-t['data_offsets'][0])
                nonexpert.append(item)
                if t['dtype']=='BF16':bf.append(item)
                families[layer[2]].append(item)
    assert set(keys)==set(index) and len(keys)==96085
    assert routed['weight']==routed['scale']==46080
    family_rows=[]
    for name,items in sorted(families.items()):
        family_rows.append(dict(name=name,count=len(items),dtypes=dict(collections.Counter(i['dtype'] for i in items)),
            distinct_stored_shapes=[list(x) for x in sorted({tuple(i['stored_shape']) for i in items})],
            total_stored_extent_bytes=sum(i['stored_extent_bytes'] for i in items),
            source_tensor_to_stage_rank_bank_owner_bound=False))
    ret=js('results/rtl/dsrom_return_wake_context_prepare_20261002/model.json',RETURN)['actual_field_return']
    n=ret['macro_leaves'];roots=ret['roots'];nodes=n-roots
    bits=nodes*(2*64*65+65+1)+roots*(128*65+128*66)
    assert nodes==16256 and bits==ret['storage_lower_bound_bits']==138469120
    read('rtl/v41die/ot_v41_field_w17w10.sv');read('rtl/v41die/ot_v41_retn_w17w10.sv');read('rtl/v41rom/ot_v41_ret.sv')
    kepler=js('results/uarch/dsrom_current4096_floorplan_diagnostic_r18_20261002/service_floor_handoff_to_Maxwell.json',KEPLER)
    negative=js('results/uarch/dsrom_l20_reticle_prerequisite_20261002/model.json')['constrained_alternative']
    assert negative['source_field_collisions_with_proposed_hub_envelope']==2550
    abstract=js('results/physical_abi3/asap7/chip/v41_w18/pair_w10p5_abstract.json')
    hardleaf='results/physical_abi3/asap7/chip/abstracts/ot_v41_rom_elem_q_w10p5/ot_v41_rom_elem_q_exact.lef'
    raw=read(hardleaf);assert sha(raw)==abstract['abstract']['files']['ot_v41_rom_elem_q_exact.lef']
    read('results/physical_abi3/asap7/chip/abstracts/ot_v41_rom_elem_q_w10p5/ot_v41_rom_elem_q_typ.lib')
    sizes=list(map(float,re.search(rb'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',raw).groups()))
    stages=inv['per_stage_per_rank'];pair_total=sum(s['reservation_pairs'] for s in stages)
    assert len(stages)==164 and all(s['BF16_column_pairs']==1024 for s in stages)
    assert all(s['total_ROM4096_instances']==4*s['reservation_pairs'] for s in stages)
    fullest=max(stages,key=lambda s:s['reservation_pairs'])
    assert fullest['reservation_pairs']==4773 and fullest['q_pairs']==3749
    classes={}
    for name,c in env['classes'].items():
        classes[name]={k:c[k] for k in ['outline_um','frame_area_um2','ROM_macro_area_um2','ROM_data_bitcell_area_um2','adjacent_compute_control_wires_margin_reservation_um2','physical_ROMs','ROMs_per_logical_slot','logical_slots','gross_storage_bits','whole_element_hard_abstract_available']}
    qtotal=sum(x['q_pairs'] for x in stages);btotal=sum(x['BF16_column_pairs'] for x in stages)
    total_frame=(qtotal*env['classes']['q_pair']['frame_area_um2']+btotal*env['classes']['BF16_column_pair']['frame_area_um2'])/1e6
    rne_pair=18.368818053120002/1024
    wake_total=(qtotal*env['classes']['q_pair']['WAKE_opt_in_separate_increment']['incremental_placement_um2_at_50pct']+btotal*env['classes']['BF16_column_pair']['WAKE_opt_in_separate_increment']['incremental_placement_um2_at_50pct'])/1e6
    allowance=kepler['field_capacity_equation']['remaining_for_weight_plus_compute_RNE_WAKE_after_full_return_mm2']
    shared=js('results/uarch/dsrom_shared_complete_pair_candidate_r20_20261002/shared_candidate.json','c1b460ae0665909cd41b393ea037ebf58ce9f057')
    arch_ref='c9b4730bd57e523857a91f7dc9f61eea7f4f68d5'
    arch_base='results/uarch/dsrom_service_hub_arch_handoff_20261002/'
    arch_join=js(arch_base+'inventory_service_join.json',arch_ref)
    arch_overlay=js(arch_base+'shared_numeric_overlay.json',arch_ref)
    arch_model_raw=read(arch_base+'model.json',arch_ref)
    assert sha(arch_model_raw)==arch_overlay['model_sha256']
    arch_model=json.loads(arch_model_raw)
    added_corridor=arch_model['geometry']['native_bidirectional_extra_service_rectangle_mm2']
    corrected_field=kepler['field_capacity_equation']['usable_field_after_inherited_service_and_policy_mm2']-added_corridor
    corrected_after_return=corrected_field-kepler['service_fixed_floor']['return_FF_reservation_mm2']
    shared_need=shared['area_and_service_reserve']['full_conservative_field_need_mm2']
    corrected_margin=corrected_field-shared_need
    assert corrected_margin<0
    option_raw=read(shared['sizing_source']['path'])
    assert sha(option_raw)==shared['sizing_source']['SHA256']
    q58=shared['single_candidate_counts']['q_pairs_per_die_reservation'];b58=shared['single_candidate_counts']['BF_pairs_per_die_reservation']
    frame58=(q58*env['classes']['q_pair']['frame_area_um2']+b58*env['classes']['BF16_column_pair']['frame_area_um2'])/1e6
    price58=next(r for r in json.loads(option_raw)['priced_options'] if r['capacity']['stages']==58)['capacity']
    unresolved_field_reservation=price58['field_need_mm2']-frame58
    assert math.isclose(frame58+unresolved_field_reservation+price58['RNE_increment_mm2']+price58['WAKE_increment_mm2']+price58['return_no_unproved_partition_credit_mm2'],shared_need,abs_tol=1e-8)
    candidate=json.loads(source('results/uarch/dsrom_coordinated_partition_decision_20261002/decision-r3.json','aa5b449b2d807098b8b90a7087ff168355c67fe7'))
    pins['aa5b449b2d807098b8b90a7087ff168355c67fe7:results/uarch/dsrom_coordinated_partition_decision_20261002/decision-r3.json']=sha(source('results/uarch/dsrom_coordinated_partition_decision_20261002/decision-r3.json','aa5b449b2d807098b8b90a7087ff168355c67fe7'))
    return dict(schema='opentallas.DSROM.current4096.field-source-receipts.v1',base_commit=PIN,source_pins=pins,
        current_service_capacity_negative=dict(canonical_candidate_id=shared['candidate_id'],historical_Arch_identity_alias=arch_join['candidate_id'],identity_join_scope='Same completeNB2/PP1 fixed4096 grain and service context; counts remain onlyS58 review reservation, no worker agreement or adoption presumed.',
            service_join_source=arch_ref,verdict='FAIL_S58_CORRECTED_SERVICE_CAPACITY_SCREEN',
            old_passing_screen_preserved=True,old_field_available_mm2=kepler['field_capacity_equation']['usable_field_after_inherited_service_and_policy_mm2'],
            additional_bidirectional_corridor_debit_mm2=added_corridor,corrected_field_available_mm2=corrected_field,
            corrected_after_return_allowance_mm2=corrected_after_return,unchanged_S58_gross_field_need_mm2=shared_need,
            corrected_margin_mm2=corrected_margin,corrected_deficit_mm2=-corrected_margin,new_partition_count_selected=False,
            native_frame_only_S58_mm2=frame58,analytical_field_reservation_beyond_frame_mm2=unresolved_field_reservation,
            return_no_credit_mm2=price58['return_no_unproved_partition_credit_mm2'],RNE_separate_construction_mm2=price58['RNE_increment_mm2'],WAKE_separate_construction_mm2=price58['WAKE_increment_mm2'],
            frame_plus_repairs_embedded_or_disjoint_reconciliation_proven=False,
            reservation_not_added_to_native_frame_twice=True,no_credit_from_density_remainder_without_source_map=True,
            physical_GO=False),
        owner_inventory_committed_source=NASH,reused_owner_snapshot_receipt=snapshot,owner_generator_executed=False,
        coordinated_binding_task=dict(candidate_id=shared['candidate_id'],candidate_stage_groups=58,fixed_TP=4,fixed_depth=4096,physical_macros_per_element_slot=2,
            selected_or_proven_minimum=False,layer_HBM_stacks_if_source4per_die_retained=shared['new_replicated_service_cost_obligations']['layer_HBM_stacks_if_source4per_die_retained'],
            baseline_layer_HBM_stacks=shared['new_replicated_service_cost_obligations']['baseline_layer_HBM_stacks'],reference_total_q_pairs=qtotal,reference_total_BF_pairs=btotal,
            candidate_total_q_pairs=candidate['capacity_preservation']['candidate_q_pairs_TP4'],candidate_total_BF_pairs=candidate['capacity_preservation']['candidate_BF_pairs_TP4'],
            candidate_rounding_surplus_q_vs_current_inventory=candidate['capacity_preservation']['candidate_q_pairs_TP4']-qtotal,
            current_frame_mm2=inv['area_ledgers']['busiest_current_leaf_and_frame']['composite_frame_total_mm2'],historical_allowance_after_return_mm2=allowance,allowance_after_return_mm2=corrected_after_return,
            direct_frame_allowance_equivalence_proven=False,
            RNE_WAKE_containment_question='Frame includes unspecified adjacent logic/control/channel margin; prove mapped repair placement fits that SAME frame or charge source-bound disjoint growth. Never add another full frame.',
            conserved_frame_all_layer_dies_mm2=total_frame,
            ideal_area_only_lower_bound_stage_groups=math.ceil(total_frame/(4*corrected_after_return)),
            separate_RNE_WAKE_upper_reservation_all_layer_dies_mm2=btotal*rne_pair+wake_total,
            ideal_area_lower_bound_if_all_RNE_WAKE_is_disjoint=math.ceil((total_frame+btotal*rne_pair+wake_total)/(4*corrected_after_return)),
            lower_bounds_not_candidate_selections=True,
            critical_task='Nash allocator owner-atom export + Kepler per-class RNE/WAKE containment certificate; Arch packing consumes these exact atoms for the SAME58-group review candidate.',
            exact_owner_atom_fields=['tensor_key','stored_header_SHA256','logical_format','output_row_first_last','golden_K_chunk_first_last','aligned_reduction_subtree_id','expert_id_or_dense','BF_pair_class','required_words_per_physical_bank','stage','TP_rank','return_region','slot_ids','ROM_bank_addresses','parent_root_port'],
            source_granularity='Row segments all in one return region; legal source K runs are power-of-two aligned256-element golden chunks; FP4 minimum aligned sibling-chunk pair512elements. Source runtimeNP and R are powers of two. These rules are bound; actual atom list/largest atom footprint are missing.',
            executor='Nash existing allocator metadata-only export, no numeric weight payload, no second compile or RTL/PnR; Kepler source containment map; Arch read-only packing.',
            acceptance_checks=['Every indexed field tensor/scale/constant has a role and owner; Engram table bytes stay on table roles, not layer field twice.', 'All reference words and output rows covered exactly once with source storage replication explicit; no omitted BF/routed/dense owners.', 'Every row has one legal return-region owner and unchanged sibling reduction order/round points; largest atom fits assigned candidate die.', 'Per-bank depth4096, two macros per physical element slot, realBF pins, disjoint repair/exclusion cost and finite root/port namespace fit.', 'After owner packingPASS regenerate actual token cut-edge hops/serialization; TP changes remain separate.'],
            minimum_missing_input='One source-pinned owner-atom table plus per-class repair-containment/growth map; existing inventory/header/return/LEF receipts supply remaining fixed inputs.',
            hardware_admission=False),
        header_census=dict(revision=cat['checkpoint_revision'],shards=len(cat['shards']),tensor_keys=len(keys),groups={k:dict(v,dtypes=dict(v['dtypes'])) for k,v in groups.items()},routed_expert_count=dict(routed),nonexpert_families=family_rows,backbone_nonexpert_tensor_count=len(nonexpert),backbone_BF16_tensor_count=len(bf),backbone_BF16_stored_extent_bytes=sum(i['stored_extent_bytes'] for i in bf),
            Engram_table_metadata_separated_from_layer_field=dict(weight_bytes=sum(f['total_stored_extent_bytes'] for f in family_rows if f['name']=='engram.embed.weight'),scale_bytes=sum(f['total_stored_extent_bytes'] for f in family_rows if f['name']=='engram.embed.scale'),table_role_not_layer_compute=True),stored_headers_are_not_logical_FP4_shape_or_ROM_word_map=True,checkpoint_payload_bytes_read=0,tensor_to_bank_mapping_proven=False),
        current4096_inventory=dict(stages=41,ranks=4,layer_dies=164,total_analytical_pairs=pair_total,total_complete_element_slots=2*pair_total,total_physical4096_macros=4*pair_total,
            busiest_pairs=4773,busiest_q_pairs=3749,busiest_BF16_column_pairs=1024,busiest_complete_slots=9546,busiest_physical_macros=19092,
            BF16_column_pair_is_two_slots=True,BF16_physical_macros_per_layer_die=4096,
            stage_reservation_pair_range=[min(s['reservation_pairs'] for s in stages),max(s['reservation_pairs'] for s in stages)],
            executable_tensor_bank_owner_bound=False,classes=classes,coarse_layer_owner_count=len(inv['nonexpert_and_BF16_ownership']['layer_candidate_obligations']),
            nonexpert_owner_bound=False,head_table_inventory_not_in_layer_count=True),
        full_return=dict(source=RETURN,NP=8192,leaves=n,roots=roots,nodes=nodes,RD=64,ROOTD=128,storage_lower_bound_bits=bits,
            formula='(2*8192-128)*(2*64*65+65+1)+128*(128*65+128*66)',
            provider_scope='Declared queues/tag/data/error; control/adder/pointer/mux state extra. Not a4773-pair compiled native provider or occupancy proof.',
            source_tags_and_ports=ret['ports'],return_root_public_bits_per_cycle=ret['root_public_bits_per_cycle'],
            all_links_bits_per_cycle=ret['tree_all_links_bits_per_cycle'],
            full_return_conservative_FF_mm2=kepler['service_fixed_floor']['return_FF_reservation_mm2'],native_area_or_dedup_credit_proven=False,
            largest_owner_granularity_issue='Current field requires power-of-twoNP and regional subtrees;4773reservation pairs cannot replaceNP8192 without exact mapped ownership/padding/tree proof.'),
        physical=dict(current_model_classes=classes,historical_q_hard_outline_um=sizes,historical_q_source=abstract['element'],historical_q_defects=abstract['defects'],
            historical_q_abstract_not_current_RNE_WAKE_4096_SSFF=True,current_q_and_BF_hard_abstracts_available=False,
            macro_leaf_LEF_is_not_composite_abstract=True,PDN_halo_um=inv['placement_contract']['PDN_macro_halo_um'],
            PDN_halo_not_placement_halo=True,parent_halo_OBS_PDN_clockPG_occupancy_bound=False,clock_policy=inv['clock_PG'],
            service_proxy_already_in_inherited_field_debit_mm2=kepler['service_fixed_floor']['sum_named_source_proxy_mm2'],additional_service_proxy_debit_mm2=0.,
            full_return_debited_once=True),
        retained_negative=dict(historical8192_proposed_hub_collision_count=2550,exact_committed_receipt_located=True,
            source='results/uarch/dsrom_l20_reticle_prerequisite_20261002/model.json:constrained_alternative.source_field_collisions_with_proposed_hub_envelope',
            not_current4096_collision_measurement=True,no_FAIL_overwritten=True),
        exact_count_and_geometry_gaps=[
            'All current4096 tensor/scale/constant/BF16 stage/rank/physical bank/address owners; coarse integer reservation is not executable allocation.',
            'Source-matched RNE/WAKE q and BF16 hard abstracts/SSFF ETMs with halo/OBS/PG/clock endpoints; historical q p5 failed and is different source.',
            'Full138469120bit return native provider ledger and existing storage dedup; sourceNP8192/R128 cannot be proportionally shrunk to4773.',
            'Largest indivisible operator/reduction subtree and fullfield region/namespace ownership for the ONE common partition candidate.',
            'Head/table role storage and co-resident services/link/PHY inventory; no treating layer-only counts as whole product fit.',
            'Actual disjoint parent rows/macros/corridors/PDN/CTS/hold exclusions and per-cut ports; inherited budgets are proxies.'],
        intended_recipient='Archimedes01a0f9c6 and parent; no execution duplication',new_hardware_jobs=0,RTL_PnR=False,physical_admission=False,rate_claim=False)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=build()
    if a.output.exists():raise ValueError('Refusing evidence overwrite')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(headers=r['header_census']['tensor_keys'],inventory=r['current4096_inventory']['busiest_pairs'],return_bits=r['full_return']['storage_lower_bound_bits'],physical_admission=False)))
