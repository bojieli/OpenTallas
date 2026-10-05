#!/usr/bin/env python3
"""Additive source-selected HBM inventory audit; no elaboration or payload reads.

Reads committed records only. Reservation containment and historical packing
are deliberately distinct from installed macros, routing and timing closure.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEST = 'results/uarch/hbm_fullsize_inventory_20261003'
BASE = '86996e8f4a62f02f58b0f5592d3352b130dd57cb'
GATE = 'results/uarch/h4_hbm_gateway_constructive_20261002/'
RF_MODEL = 'results/uarch/full_sm_rf_service_20261002/model_final.json'
PARENT = 'results/uarch/full_sm_actual_parent_route_20261002/model.json'
CAPACITY = 'results/uarch/hbm_tc_parent_capacity_20261002/model.json'
FENCE = 'results/uarch/h4_hbm_kv_validity_fence_20261003/model.json'
VISIBILITY = 'results/uarch/hbm_rf_visibility_fence_20261002/model_connected_review.json'
BRIDGE='results/uarch/h4_hbm_baseline_bridge_20261003/w5_w10_r4/model.json'
W6='results/uarch/hbm_W6_connector_model_20261003/r1/model.json'
INPUTS = [
    'tools/uarch_model.py', RF_MODEL, PARENT, CAPACITY, FENCE, VISIBILITY, BRIDGE, W6,
    GATE+'manifest.json', GATE+'final_handoff_r10.json',
    GATE+'inputs/0.json', GATE+'inputs/5.json', GATE+'inputs/6.json',
    GATE+'inputs/7.json', GATE+'inputs/8.json',
    'results/floorplan/hbm_gpu/qwen_hbm_die.json',
    'results/floorplan/hbm_gpu/v41_hbm_die.json',
    'rtl/gpu/ot_gpu_sm_q.sv', 'rtl/gpu/ot_gpu_sm_v.sv',
    'rtl/gpu/ot_gpu_bulk_copy.sv', 'rtl/gpu/ot_gpu_xstore.sv',
    'rtl/gpu/ot_gpu_rf_service.sv', 'rtl/gpu/ot_gpu_scratch_service.sv',
    'rtl/gpu/ot_gpu_hbm_rf_shared_context.sv',
    'rtl/gpu/ot_gpu_rf_visibility_fence.sv',
    'results/uarch/native_software_parent_intake_20261002/HBM_32SM_constructive_parent_review.json',
]
MASTERS = ['ot_sram_1r1w_128x256_m1_r2c2',
           'ot_sram_1r1w_1024x256_m2_r2c2',
           'ot_sram_1r1w_256x256_m2_r2c2',
           'ot_sram_1r1w_64x512_m1_r2c2', 'ot_hbm3e_phy']
for master in MASTERS:
    INPUTS.append(f'physical/asap7_memory_macros/{master}/{master}.lef')
PHY_METADATA='physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.json'
INPUTS.append(PHY_METADATA)
SOURCE_EQUIVALENCE = {
    'rtl/gpu/ot_gpu_sm_q.sv':'8e0aa477664f385a8536b1610c508fdd637bb020377adf744671c960d984b06f',
    'rtl/gpu/ot_gpu_sm_v.sv':'2fa17cd4893171850fe87232ccf20f576e58ef663e855b4d069fb8ad61a1460c',
    'rtl/gpu/ot_gpu_bulk_copy.sv':'99ea676a25fa560f62f4461ce0da29e6dc44f84b412d486b5c646ce4fa1c7ee4',
    'rtl/gpu/ot_gpu_xstore.sv':'990094f52f6a13f1618730bb2b61f02b7d439df872e31509b0cb83ae9eb770ca',
}

def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def unique_inventory(rows):
    keys = [(r['owner'], r['role']) for r in rows]
    require(len(keys)==len(set(keys)), 'duplicate inventory ownership')

def sum_additive_area(rows):
    """Only disjoint envelope charges may be summed; contained costs are zero."""
    keys = [r['charge_id'] for r in rows]
    require(len(keys)==len(set(keys)), 'duplicate area charge')
    for r in rows:
        require(r['additional_mm2'] >= 0, 'negative area credit')
        require(not r['contained'] or r['additional_mm2']==0, 'contained cost recharged')
    return sum(r['additional_mm2'] for r in rows)

def baseline_literals(raw):
    tree = ast.parse(raw)
    sm = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sm_area')
    storage = next(n.value for n in ast.walk(sm) if isinstance(n,ast.Assign)
                   and any(isinstance(t,ast.Name) and t.id=='sram_kb' for t in n.targets))
    require(isinstance(storage,ast.Call) and {k.arg for k in storage.keywords}=={'x_store','staging','scratch'},
            'baseline SM SRAM roles changed; RF debit review required')
    return {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
            if isinstance(n, ast.Assign) and len(n.targets)==1
            and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id == 'GPU_MACRO_PACK'}

def compose(root=ROOT, verify_pins=True):
    pinpath = root/DEST/'source-pins-r1.json'
    pins = json.loads(pinpath.read_bytes())
    require(set(pins['sources'])==set(INPUTS), 'source-selected dependency inventory')
    data = {}
    for path in INPUTS:
        raw = (root/path).read_bytes()
        if verify_pins:
            require(sha(raw)==pins['sources'][path]['sha256'], 'source drift: '+path)
        data[path] = raw
    load = lambda p: json.loads(data[p])
    # Bind the selected archive slots to their original source manifest, not
    # to an all-tree historical census or a current-path existence assertion.
    manifest = load(GATE+'manifest.json')
    for path in INPUTS:
        if path.startswith(GATE+'inputs/'):
            rec = next(r for r in manifest['inputs'] if GATE+r['archive']==path)
            require(sha(data[path])==rec['sha256'] and len(data[path])==rec['bytes'], 'archive origin drift')
    baseline = baseline_literals(data['tools/uarch_model.py'].decode())
    require(baseline['GPU_MACRO_PACK']==1.31, 'historical packing policy')
    for path, expected in SOURCE_EQUIVALENCE.items():
        require(sha(data[path])==expected, 'retained source equivalence: '+path)
    master_views = {}
    for master in MASTERS:
        path=f'physical/asap7_memory_macros/{master}/{master}.lef'
        width,height=map(float,re.search(r'SIZE\s+([.0-9]+)\s+BY\s+([.0-9]+)',data[path].decode()).groups())
        master_views[master]=dict(size_um=[width,height],area_um2=width*height,source=path,
                                  abstract_only=True,contextual_SSFF=False)
    service = load(RF_MODEL)
    retained = load(PARENT)
    capacity = load(CAPACITY)
    expanded = load(GATE+'inputs/6.json')
    atomic = load(GATE+'inputs/0.json')
    context = load(GATE+'inputs/5.json')
    gateway = load(GATE+'final_handoff_r10.json')
    protection = load(FENCE)
    visibility = load(VISIBILITY)
    bridge = load(BRIDGE)
    w6 = load(W6)
    phy_metadata = load(PHY_METADATA)
    phy_interface = phy_metadata['interface']['controller_side']
    models = {}
    historical_floorplans = {}
    for name, path in [('Qwen','results/floorplan/hbm_gpu/qwen_hbm_die.json'),
                       ('DeepSeek','results/floorplan/hbm_gpu/v41_hbm_die.json')]:
        f=load(path)
        require(f['sm_count']==32 and f['sm_tile']['macros']==[] and f['sm_tile']['sram']==0,
                'historical abstract SM inventory changed')
        historical_floorplans[name]=dict(die_um=f['die_um'],placed_counts=f['macro_counts'],
            abstract_SM_macros=f['sm_tile']['macros'],abstract_LEF=f['sm_tile']['abstract_lef'],
            rectangle_fit=f['fits'],physical_qualified=False)
    small,big,scale,queue,phy = [master_views[m]['area_um2'] for m in MASTERS]
    for name, key, short, fp_path in [
            ('Qwen','qwen','Qwen',GATE+'inputs/7.json'),
            ('DeepSeek','deepseek_v41','DS',GATE+'inputs/8.json')]:
        r = service['models'][short]
        old = retained['models'][short]
        e = expanded['models'][name]
        a = atomic['models'][name]
        c = context['models'][name]
        g = gateway['models'][name]
        b = bridge['floorplan'][name]
        ledger = bridge['resource_ledger']
        fp = load(fp_path)
        require((r['SM_replicas'],r['RF_banks'],r['RF_pages_per_bank'],r['RF_read_copies'])==(32,16,4,2), 'RF organisation')
        placed_rf = [m for m in e['service']['macro_placements'] if m['name'].startswith('RF.')]
        placed_scratch = [m for m in e['service']['macro_placements'] if not m['name'].startswith('RF.')]
        require(len(placed_rf)==r['RF_macros']==128 and len(placed_scratch)==r['scratch_macros']==2, 'source service count')
        inv = capacity['models'][key]['proposed_full_inventory']
        require(len({p['name'] for p in inv})==len(inv), 'retained instance duplicate')
        x = [p for p in inv if p['name'].startswith(('g_xm[','u_x.'))]
        staging = [p for p in inv if p['name'].startswith('u_bc.')]
        row_scale = [p for p in inv if p['name']=='u_scale']
        params = old['actual_params']
        rtl=data['rtl/gpu/ot_gpu_sm_q.sv' if name=='Qwen' else 'rtl/gpu/ot_gpu_sm_v.sv'].decode()
        defaults={k:int(v) for k,v in re.findall(r'parameter integer\s+(\w+)\s*=\s*(\d+)',rtl)}
        require(all(defaults[k]==v for k,v in params.items()), 'actual retained parameter/source default join')
        if name=='Qwen':
            x_formula = params['NXM']
            line_bits = params['SUB']*params['LS']*8
            require(len(row_scale)==1, 'Qwen scale macro')
            x_bytes = 32768
        else:
            x_formula = (params['NC']*(params['SUB']*params['LBS']*266+params['SUB']*params['LSB']*16)+255)//256
            line_bits = 1088
            require(not row_scale, 'DS scale inventory')
            x_bytes = 4096
        require(len(x)==x_formula and len(staging)==(line_bits+255)//256, 'source xstore/staging formula')
        master_counts = old['retained_macro_master_counts']
        require(sum(master_counts.values())==len(inv), 'retained mapped master census')
        require(len(x)+len(staging)+len(row_scale)==sum(v for k,v in master_counts.items() if k.startswith('ot_sram_')), 'retained SRAM role census')
        counts = Counter(p['macro'] for p in fp['macro_placements'])
        require(counts['ot_hbm3e_phy']==4 and counts['ot_sram_1r1w_1024x256_m2_r2c2']==256, 'die L2/PHY census')
        frames = a['DS_result_macros']
        require(len(frames)==a['new_SRAM_macros'], 'capture macro census')
        if frames:
            require(Counter(p['SM'] for p in frames)==Counter({i:8 for i in range(32)}), 'DS capture replicas')
        rows = []
        def row(role, count, bytes_each, area_um2, owner, scope, ports):
            rows.append(dict(role=role,owner=owner,count_per_die=count,physical_bytes_per_die=None if bytes_each is None else count*bytes_each,
                raw_macro_area_mm2=None if area_um2 is None else count*area_um2/1e6,
                evidence_scope=scope,ports=ports,physical_qualified=False))
        row('RF',128*32,4096,small,'SM RF','source-sized service and 32SM reservation; not full mapped successor','1R1W per copy; two reads512B each; write512B mirrored')
        row('scratch',2*32,32768,big,'SM shared','source-sized64KiB/SM; finite64B port','two256b macros;64B read/write service')
        row('L2',256,32768,big,'L2','retained die placement inventory','1R1W256b per macro;128B line requires four bank reads')
        row('PHY',4,None,phy,'shoreline','external PHY abstract; sustained service/internal timing unknown',
            'retained AW31/LEN5/BEAT4 vs selected AW31/LEN6/BEAT5 requires exact provider join')
        row('xstore',len(x)*32,x_bytes,small if name=='DeepSeek' else big,'matrix SM','retained mapped-source inventory; not current full SM qualification','DS full group fragment; Qwen buffered fragment')
        row('staging',len(staging)*32,32768,big,'matrix SM','retained source ring, depth1024; padded to256b macro lanes','one source line/cycle only when actual flow permits')
        row('row_scale',len(row_scale)*32,8192,scale,'matrix SM','retained source; Qwen BF16 scale layout','256b1R1W macro; selected scale field')
        row('capture',len(frames),32768,big,'matrix capture','constructed DS8macros/SM; Qwen no additional SRAM in this contract','accepted producer/consumer and owner intervals unqualified')
        # Qwen shoreline metadata/queues are placed in the selected r11 record.
        # DS r11 exposes only an envelope, not a complete provider census.
        row('shoreline_context',counts['ot_sram_1r1w_128x256_m1_r2c2'],4096,small,'shoreline','Qwen selected metadata reservation; DS missing implementation census','1R1W256b')
        row('shoreline_queues',counts['ot_sram_1r1w_64x512_m1_r2c2'],4096,queue,'shoreline','Qwen selected request/return queues; DS complete provider census absent','1R1W512b; actual selected queue/controller qualification open')
        unique_inventory(rows)
        pf = protection['constructive_design']
        require(sum(pf['descriptor_fields'].values())==pf['request_descriptor_bits'], 'descriptor identity width')
        require(pf['queue_bits_per_die']+pf['arbitration_bits_per_die']+pf['parent_identity_bits_per_die']+256==pf['total_state_bits_per_die'], 'protection state sum')
        charge_rows = [dict(charge_id='selected_expanded_die',additional_mm2=e['area']['complete_reserved_occupancy_mm2'],contained=False)]
        for charge_id in ('RF','scratch','L2','PHY','capture','gateway_clock','gateway_controller'):
            charge_rows.append(dict(charge_id=charge_id,additional_mm2=0,contained=True))
        total = sum_additive_area(charge_rows)
        require(total==a['full_reserved_die_mm2']==g['whole_die_reserved_occupancy_mm2'], 'selected envelope changed')
        require(b['retained_context_occupied_mm2']==total,'bridge context identity')
        current_charges=charge_rows+[dict(charge_id='current_W5_W10_disjoint_slot_envelope',additional_mm2=b['reserved_area_mm2'],contained=False)]
        current_total=sum_additive_area(current_charges)
        require(abs(current_total-b['complete_context_plus_new_slots_mm2'])<1e-9,'once-only bridge slot total')
        macros = sum(p['count_per_die'] for p in rows if p['role']!='PHY')
        memories_per_sm = len(x)+len(staging)+len(row_scale)
        models[name] = dict(inventory=rows,SRAM_macros_per_die=macros,SM_replicas=32,die_count_scope='per die; package/rank mapping requires owner calendar, not96 identical die inference',
            retained_source=dict(commit=old['source_commit'],params=params,mapped_master_counts_per_SM=master_counts,
                mapped_parent_FF_per_SM=e['actual_source_geometry']['actual_FFs'],source_geometry_is_historical=True),
            staging=dict(line_bits=line_bits,depth=1024,useful_bytes_per_SM=line_bits*1024//8,physical_bytes_per_SM=len(staging)*32768,
                context_summary_bytes_per_SM=c['storage']['retained_bulk_ring_bytes_per_SM'],
                context_summary_matches_source=(line_bits*1024//8==c['storage']['retained_bulk_ring_bytes_per_SM'])),
            protection=dict(KV_constructive_state_bits_per_die=pf['total_state_bits_per_die'],KV_ASSUMED_footprint_mm2=pf['incremental_footprint_mm2_per_die_ASSUMED'],
                KV_source_operator_bound=name=='Qwen',KV_installed=False,KV_area_added_to_selected_total=False,
                KV_parent_composition_total_upper=pf['full_die_with_delta_upper_only'][name],KV_parent_total_is_different_scope=True,
                RF_visibility_state_bits_per_SM=visibility['total_state_bits'],RF_visibility_payload_bits=visibility['payload_buffer_bits'],
                RF_visibility_installed_in_selected_full_context=False,mutable_memory_and_link_protection_not_removed=True,
                bulk_ring_full_bits_per_SM=1024,bulk_response_queue_payload_bits_per_SM=2*line_bits,
                bulk_source_completion_flags_are_not_epoch_or_integrity_proof=True,
                current_bridge_protected_state_bits=ledger['full_new_protected_bits'],
                current_NC6_raw_state_bits=ledger['W2_bound_composition']['W2_model_costs']['full_wrapper_variant']['raw_state_bits_all128PC'],
                current_NC6_protected_state_bits=ledger['W2_bound_composition']['W2_model_costs']['full_wrapper_variant']['protected_state_bits_all128PC'],
                W6_frame_raw_bits=w6['frame']['data_bits_full32SM'],W6_frame_protected_bits=w6['frame']['data_protected_full32SM_bits'],
                W6_same_index_sidecar_macro_alternative_count=w6['sidecar']['macros'],
                W6_sidecar_macro_alternative_selected=False,bridge_sidecar_realization=ledger['sidecar_realization'],
                ECC_or_parity_complete_selected_source_census=None,complete_protection_physical_area=None),
            capture=dict(constructed_SRAM_bytes_per_SM=a['DS_frame_bytes_per_SM'],historical_full_operation_payload_bytes_per_SM=visibility['capture_budget']['Qwen_payload_bytes' if name=='Qwen' else 'DS_payload_bytes'],
                historical_capture_cost_recharged=False,contracts_equivalent=False,accepted_demand_and_backpressure_proof=False),
            shoreline=dict(retained_PHY_interface_bits={k:phy_interface[k] for k in ('address_bits','len_bits','beat_bits')},
                selected_controller_required_bits=dict(address_bits=31,len_bits=6,beat_bits=5),
                PHY_exact_interface_join=False,PHY_claim_boundary=phy_metadata['claim_boundary'],
                complete_DS_controller_storage_count=None if name=='DeepSeek' else 'Qwen source reservation only',
                PHY_internal_physical_qualification=None,sustained_bandwidth_measurement=None),
            area=dict(charges=charge_rows,selected_reserved_occupancy_mm2=total,RF_raw_mm2=128*32*small/1e6,
                historical_RF_packed_mm2=128*32*small*baseline['GPU_MACRO_PACK']/1e6,RF_packing_debit_added_again=0,
                RF_already_contained_in_service_envelope=True,service_envelope_mm2=e['area']['service_mm2_per_die'],
                envelope_is_not_sum_of_raw_macro_areas=True,complete_current_source_area=None),
            current_bridge_composition=dict(charges=current_charges,context_plus_reserved_slots_mm2=current_total,
                source_contract=BRIDGE,bridge_logic_upper_mm2_ASSUMED=ledger['complete_service_area_upper_mm2_ASSUMED'],
                bridge_upper_is_contained_in_slot_not_added_again=True,
                NC6_gross_upper_mm2_unreconciled=ledger['W2_gross_bound_mm2_unreconciled'],
                NC6_matched_old_debit_mm2=ledger['W2_matched_old_debit_mm2'],NC6_net_increment_mm2=ledger['W2_net_increment_mm2'],
                NC6_once_only_rule=ledger['F0_once_only_rule'],
                W6_component_mm2=w6['W6_component']['area']['full32SM_slot_mm2'],W6_subcomponent_added_again=False,
                exact_current_complete_area=None,source_owned_reset_release_implemented=False,
                reset_drain_upper_ns_prospective=bridge['reuse']['prospective_reset_drain_positive_ns'],
                old_rejected_single_bundle_cut_min_tracks=min(x['margin_after_single_bundle'] for x in b['retained_corridor_additive_cut_screens']),
                current_single_shared_bus_cut_screen=b['selected_corridor_single_bus_screens_pass'],
                actual_constructive_routes_and_PG_cuts=b['constructive_route_cut_assignment'],
                physical_admitted=False),
            routing=dict(distributed_cuts=g['distributed_cuts'],minimum_margin_tracks=g['minimum_distributed_cut_margin_tracks'],
                L2_demand_tracks=g['L2_endpoint_demand_tracks'],L2_available_tracks=g['L2_endpoint_available_tracks'],
                conditional_constructive_screen=True,actual_complete_route=False),
            clock=dict(stream_GHz=1.2,serial_GHz=.9,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
                gateway_service_macro_endpoints_per_SM=g['macro_clock_endpoints_per_SM'],
                retained_matrix_memory_macro_endpoints_per_SM=memories_per_sm,
                retained_compute_macro_endpoints_per_SM=sum(v for k,v in master_counts.items() if not k.startswith('ot_sram_')),
                gateway_clock_is_full_parent_load=False,global_root_reset_release_PG_proof=False,balanced_CTS_and_contextual_SSFF=False),
            composition=dict(whole_token_ns=None,production_interval_bound_calls=gateway['actual_production_interval_bound_calls'],
                source_span_bound_calls=gateway['corrected_source_span_bound_calls'],source_span_is_not_finite_service=True,
                RF_I64_RMW_C0_recharged=False,hardware_admitted=False,build_GO=False),
            blockers=['complete selected SM source/parameter and macro ownership join','full matrix+service+shoreline clock/reset/PG sink census and balance',
                'accepted-demand finite backend/consumer/reverse intervals','complete capture/protection/controller once-only allocation',
                'PHY sustained bandwidth and contextual SS setup/FF hold, power/IR and routes'])
    return dict(schema='opentallas.hbm.fullsize-inventory-composition.v1',base_git=BASE,default_enabled=False,
        input_pin_manifest_sha256=sha(pinpath.read_bytes()),models=models,macro_views=master_views,
        retained_source_equivalence=dict(commit='000ba0898f5120a66d5905ccff333ebbbe28394d',sha256=SOURCE_EQUIVALENCE,
                                        current_source_bytes_equal=True,does_not_transfer_physical_qualification=True),
        historical_baseline=dict(unified_model_byte_unchanged=True,RF_absent_from_baseline_sm_area=True,floorplans=historical_floorplans,
            baseline_floorplans_have_abstract_SM_internal_macro_lists=True,historical_RF_debit_not_universally_missing=True),
        evidence_classification=dict(inventory_and_constructor_free_metadata='SOURCE_METADATA_ONLY',
            constructor_execution='NOT_EXECUTED_BY_THIS_RECEIPT',checkpoint_payload='NOT_READ_BY_THIS_RECEIPT',
            native_numerical='NO_NEW_RUN_OR_PASS',physical='UNKNOWN_NOT_QUALIFIED'),
        coordination=dict(Popper='selected service/controller/ownership/CDC and once-only area join',
            Archimedes='full macro abstracts, root clock/reset/PG/cuts and contextual physical admission',
            Dewey='source accepted-demand event DAG and finite interval composition',Ampere='bounded inventory and binding metadata only'),
        RTL_elaborations=0,PnR_jobs=0,payload_reads=0,hardware_admitted=False,build_GO=False)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--freeze-inputs',action='store_true')
    args = parser.parse_args()
    if args.freeze_inputs:
        pins = dict(schema='opentallas.hbm.inventory-source-pins.v1',base_git=BASE,
                    sources={p:dict(sha256=sha((ROOT/p).read_bytes()),bytes=(ROOT/p).stat().st_size) for p in INPUTS},
                    historical_archives_are_not_current_source_equivalence=True)
        path=ROOT/DEST/'source-pins-r1.json'
        require(not path.exists() or path.read_bytes()==encoded(pins),'immutable source pins differ')
        path.write_bytes(encoded(pins))
    result=encoded(compose())
    if args.out:
        require(not args.out.exists() or args.out.read_bytes()==result,'immutable model differs')
        args.out.write_bytes(result)
    else:
        print(result.decode(),end='')

if __name__=='__main__':
    main()
