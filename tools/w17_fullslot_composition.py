#!/usr/bin/env python3
"""Compose expert bank slack and descriptor/owner area without old fit credit."""
import argparse,gzip,hashlib,json,subprocess
from collections import Counter
from decimal import Decimal as D
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={
 'residency':('0fb58ac09c4415b4f143c97fed1fbfa4a5486aa9','results/quality/w16_w17_integer_residency_20261001/candidate.json.gz'),
 'descriptor':('59d0630e62502eca15ef1151085aaf63c92c8e4e','results/quality/w16_w17_descriptor_price_20261001/price.json'),
 'fullmap':('4d40ecadbbfb73c51c187fddc9ae2d3b6be28eb6','results/uarch/w10_baseline_wake/fullmap_r2/readiness.json'),
 'historical_fullgoal':('4d40ecadbbfb73c51c187fddc9ae2d3b6be28eb6','results/uarch/w10_baseline_wake/fullgoal_bound.json'),
 'clock_slot':('0cdd92fd35f142c8f0fa170426113a5b2a64e153','results/uarch/w10_clock_tree_site_budget_r1/receipt.json'),
 'spatial_clock':('38695f435d25f4eade8ea7b050cefecd1f301fa7','results/uarch/w10_spatial_clock_preflight_r1/preflight.json'),
 'rootstop':('bf097e43e1b01902c21af0e71b6e0b1ae337961e','results/quality/w10_clock_provider_join_r1/join.json'),
 'ckv_write_failure':('d4391b2e0','results/quality/parent_ckv_writepath_review_20261001/receipt.json'),
 'ckv_lease':('2723dbc74','results/rtl/w17_connected_token_preparation_20261001/ckv_publication_lease_model.json'),
 'engram_contract':('a9d1fad2835d96e4c0585a150b6a9d484b9791cc','results/quality/w16_dsrom_engram_contract_20261001/summary.json')}
def blob(pin):return subprocess.check_output(['git','show',pin[0]+':'+pin[1]],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()

def bank_slack(candidate,experts):
    q=candidate['geometry']['q_pairs'];hist=Counter()
    # Four physical mate/parity banks/pair; template stride even, paritybalanced.
    for region in range(128):
        for p in range(region*64,region*64+q//128+(region<q%128)):
            stride=candidate['pair_stride'].get(str(p),0)
            if stride%2:raise ValueError('PP stride not balanced')
            used=experts*stride//2
            if used>4096:raise ValueError('actual expert bank overflow')
            hist[4096-used]+=4
    return dict(q_physical_banks=4*q,total_q_spare_physical_words=sum(words*banks for words,banks in hist.items()),
        minimum_q_spare_words_per_physical_bank=min(hist),spare_word_histogram=[dict(words_per_bank=w,physical_banks=n) for w,n in sorted(hist.items())],
        reserved_BF_physical_banks=1024*4,reserved_BF_capacity_words=1024*4*4096,
        dense_HC_occupancy_words=None,shared_expert_occupancy_words=None,constants_occupancy_words=None,
        total_nonexpert_fit=None,scope='Exact expert-only affine bank slack; aggregate free words do not prove segment/region/nonexpert fit. BF slots unallocated, not proof of enough storage.')

def compose(data):
    c=data['residency'];d=data['descriptor'];f=data['fullmap'];old=data['historical_fullgoal'];clock=data['clock_slot'];spatial=data['spatial_clock']
    q=c['geometry']['q_pairs'];count=len(c['stages']);bf=1024
    if q!=3749 or f['structure']['icg_count']!=8:raise ValueError('source geometry changed')
    baseline_q_area=D(str(old['elements']['q']['tile_um2']))/D('1000000')
    bf_outline=[D(str(x)) for x in clock['slot']['outline_um']]
    bf_area=bf_outline[0]*bf_outline[1]/D('1000000')
    desc_pair=D(d['template_storage']['cfg_affine_register_mux_screen_mm2_per_pair'])
    spine=D(d['template_storage']['spine_register_storage_screen_mm2_per_stage_rank'])
    owner=D(d['owner_lookup']['analytic_register_mux_screen_mm2_per_replica'])
    anchors=[dict(layer=l,proposed_stage=c['owners'][l*384]['stage'],TP4_ranks=[0,1,2,3],placement_role='Layer router-hub readonlyowner lookup',physical_coordinates=None,actual_nonexpert_hub_stage=None) for l in range(40)]
    perstage=Counter(x['proposed_stage'] for x in anchors)
    bundle=[]
    for s in c['stages']:
        nowner=perstage[s['stage']]
        additions=q*desc_pair+spine+nowner*owner
        # Reference arithmetic only. Never derive a capacity or stage decision
        # from historical outlines or conditional clock slot's gross capacity.
        reference=q*baseline_q_area+bf*bf_area
        bundle.append(dict(stage=s['stage'],experts=s['experts'],owner_tables_per_rank=nowner,
            descriptor_spine_owner_candidate_screen_addition_mm2_per_rank=str(additions),
            historical_q_plus_conditional_BF_outline_reference_mm2_per_rank=str(reference),
            reference_plus_known_additions_mm2_per_rank=str(reference+additions),
            q_strip_physical_fit=None,dense_HC_addition_mm2=None,full_slot_fit=None,bank_slack=bank_slack(c,s['experts'])))
    spare=D(str(clock['slot']['stdcell_spare_um2']))
    owner_std=owner*D('1000000')*D('.5')
    return dict(schema='opentallas.w17.fullslot-composition.v1',status='FULL_PRODUCT_COMPOSITION_HOLD_NO_OLD_CAPACITY_CREDIT',
        expert_only_stage_count=count,product_stage_count=None,old_45_stage_capacity_credit=False,
        mapped_BF_baseline=dict(source_netlist_sha256=f['structure']['mapped_netlist_sha256'],measured_stdcell_um2=f['area']['measured_synthesis_stdcell_um2'],measured_macro_um2=f['area']['measured_synthesis_macro_um2'],
            original_area_test=f['area']['verdict'],conditional_625row_outline_um=[str(x) for x in bf_outline],conditional_clock_slot_stdcell_spare_um2=str(spare),
            spatial_clock_verdict=spatial['verdict'],physical_admission=False,scope='Mapped BF element only;625row integer sitebudget not adopted spatial/clock/SSFF fit, no q area transfer.'),
        q_template_composition=dict(historical_q_gross_um2=old['elements']['q']['tile_um2'],candidate_descriptor_affine_placement_um2=str(desc_pair*D('1000000')),
            addition_fraction_of_historical_gross=str(desc_pair/baseline_q_area),actual_q_fullmapped_stdcell_um2=None,actual_q_clock_and_escape_site_budget=None,
            old_outline_fit_transferred=False,mask_ROM_abstract_or_current_q_footprint=None),
        owner_placement_proposal=anchors,
        owner_space_test=dict(owner_register_mux_candidate_stdcell_um2=str(owner_std),conditional_BF_spare_um2=str(spare),
            owner_register_mux_candidate_stdcell_mm2=str(owner_std/D('1000000')),
            owner_register_mux_candidate_placed_mm2=str(owner),
            area_units='Standard-cell comparison is in square micrometres (um2); placement screens are in square millimetres (mm2). 1 mm2 = 1000000 um2.',
            qcfg_affine_candidate_placed_mm2_per_stage_rank=str(q*desc_pair),
            owner_fits_one_conditional_BF_spare_under_candidate_register_realization=owner_std<=spare,
            deficit_um2=str(owner_std-spare),required='Separate explicit hub reservation; do not hide owner tables in unallocatedBFspare orexpert ROM free words'),
        stage_bundles=bundle,
        omitted_nonexpert_contracts={k:dict(header_census_owner='Avicenna',source_pin=None,actual_ROM_word_count=None,rank_consumer_replication=None,physical_stage_assignment=None,area_mm2=None) for k in ('dense_attention','shared_experts','HC_coefficients','norm_constants','index_compressor','embedding_head','Engram','MTP')},
        no_double_count=dict(existing_element_cfg_registers_counted_once=True,new_cfg_template_ROM_and_affine_candidate_addition_separate=True,owner_tables_not_weight_bank_capacity=True,BF_mapping_not_q_area=True),
        mandatory_CKV_baseline_correction=dict(
            failure_witness=data['ckv_write_failure'],
            classification='Mandatory baseline correctness and persistent-state visibility; not an optional performance optimization.',
            one_percent_optimization_gate_applies=False,
            required_contract=['Writable CKV routing through both actual muxes',
                'Completion ownership for the untagged controller write-done response',
                'Actual backend backing-store update and done delayed through CWL plus BURST; legacy column-issue done is not visibility',
                'Finite per-stack write credit retained until visibility completion',
                'Publish row only after all nine sector writes are visible',
                'Persistent next-token state and exact context/address range guards'],
            required_model_costs=['Write requests plus controller command/burst service',
                'Completion routing, reverse CDC and publication fence latency',
                'Backend delayed-visibility queue, full-address backing store and write-buffer reservation',
                'Owner/credit registers, arbitration, staging, ports and routing area'],
            current_connected_write_path_qualified=False,
            corrected_path_exactness_qualified=False,
            corrected_path_composed_service_bound_available=False),
        current_baseline_model_inputs=dict(
            CKV_exclusive_publication_candidate=data['ckv_lease'],
            CKV_cost_composition='2952 fast cycles cover nine serialized writes, sampling, turnover and publish only; add prelease drain, CDC, consumer acceptance and final credit return. Conditional timing envelope still needs refresh/provider validation.',
            Engram_actual_header_demand_and_candidate_ports=data['engram_contract'],
            Engram_cost_composition='Immutable table backing, projection/constants, working buffers, raw lookup traffic and TP delivery are distinct. Neither proposed ROM nor HBM home receives fit or latency credit until actual address/bank/codec/port/route contracts are bound.',
            complete_product_feasibility=False),
        unresolved=['Avicenna sourceboundnonexpert census then actualTP4consumer/codec/segment proof','Godel actualtemplateword/basepatch classA gate','CurrentqPPfullmap/pin/clock/site footprint +descriptor realization/area/port contract','ActualdenseHC andownerhub physicalplacement/completebankallocator','Root/leaf clock+PG/CDC/NoC/collective/SU/CKV staging+SSFF +fullstageproviders'],
        connected_stage_cycles=None,full_token_cycles=None,full_token_rate=None,physical_admission=False,engine_RTL_build_ready=False,adopt=False,jobs_launched=0)

def build():
    raw={k:blob(pin) for k,pin in PINS.items()};data={k:json.loads(gzip.decompress(v) if k=='residency' else v) for k,v in raw.items()}
    r=compose(data);r['source_pins']={k:dict(commit=pin[0],path=pin[1],sha256=sha(raw[k])) for k,pin in PINS.items()};return r
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2)+'\n')
