#!/usr/bin/env python3
"""One parallel split: compiled-run capacity and finite deadline interface.
Allocation metadata only; no payload, allocator, encoding or simulation.
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_parallel_owner_capacity_calendar_20261002'
JOURNAL_SHA='c91855b5b33c21c56dac3ea9ebc69a201ff582a3a6ad67a19024e89cd113881f'


def run_census(r):
    if r['compiled_NP']!=4096:raise ValueError('different compiled field')
    pairs=[set(),set()];rows=[0,0];runs=[0,0]
    for segment,pair,first,n,stride,start,words in r['plans']:
        if (not 0<=pair<4096 or stride!=128 or first%128!=pair//32
                or n<=0 or start<0 or start+n*words>8192):
            raise ValueError('run violates source row/root or logical8192 bank from two4096 leaves')
        shard=pair//2048;pairs[shard].add(pair);rows[shard]+=n;runs[shard]+=1
    return dict(layer=r['layer'],expert=r['expert'],alias=r['alias'],format=r['format'],
        stage=r['stage'],rows_per_rank=r['rows'],K=r['K'],segments=len(r['segments']),
        active_unique_pairs=[len(s) for s in pairs],ordered_superrow_segment_nodes=rows,
        allocation_runs=runs,source_root_regions_cut=0,
        per_shard_active_pair_capacity_pass=all(len(s)<=2048 for s in pairs),
        single2048_die_complete_operator_fit=sum(len(s) for s in pairs)<=2048,
        source_issue_cycles_LAT8_condition=r['issue_cycles_LAT8_condition'],
        raw_ECC=r['ECC'],immutable_provider_home=r['immutable_provider_home'])


def extract(journal,output):
    h=hashlib.sha256()
    with journal.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
    if h.hexdigest()!=JOURNAL_SHA:raise ValueError('not frozen corrected622 allocation journal')
    counters=collections.Counter();records=[]
    with gzip.open(journal,'rt') as f:
        for ordinal,line in enumerate(f):
            r=json.loads(line);rec=run_census(r);s=r['stage']
            rec.update(matrix_journal_ordinal=ordinal,phase=counters[s]);counters[s]+=1;records.append(rec)
    if len(records)!=46509:raise ValueError('full-product coverage lost')
    d=dict(source_commit='622dbc897fd5ecb5a5b691e1ae39bea0ad751524',source_path=str(journal),
        source_sha256=JOURNAL_SHA,matrix_count=len(records),stage_phase_counts=dict(counters),
        records=records,allocator_reexecuted=False,payload_reads=0)
    data=gzip.compress((json.dumps(d,sort_keys=True)+'\n').encode(),mtime=0)
    with output.open('xb') as f:f.write(data)
    print(json.dumps(dict(census_sha256=hashlib.sha256(data).hexdigest(),matrices=len(records))))


def accepted_deadline_delta(original_consumer_deadline, receipts):
    """Concrete candidate-specific accepted completion edges, never nominal rate."""
    if original_consumer_deadline<0:raise ValueError('missing original deadline')
    mandatory={'XN_broadcast','cfg_ECC_fence','native_compute','ordered_result_gather'}
    if set(receipts)!=mandatory:raise ValueError('every actual provider path required')
    if len({r.get('resource_calendar') for r in receipts.values()})!=1:
        raise ValueError('one composed shared-resource calendar required, not independent rank overlap')
    if len({r.get('timebase') for r in receipts.values()})!=1 or not all(r.get('timebase') for r in receipts.values()):
        raise ValueError('common clock/CDC timebase required')
    finish=0
    for r in receipts.values():
        if (not r.get('source_receipt') or not r.get('resource_calendar')
                or r['accepted_edge']<r['ready_edge']
                or r['visible_edge']<=r['accepted_edge']
                or r['peak_live_bytes']>r['reserved_bytes']):
            raise ValueError('missing positive accepted service/finite capacity')
        finish=max(finish,r['visible_edge'])
    compute=receipts['native_compute'];gather=receipts['ordered_result_gather']
    if not compute.get('weight_code_scale_ECC_terminal_receipts'):
        raise ValueError('native compute cannot omit inline/remote weight ECC terminal service')
    if compute['accepted_edge']<max(receipts['XN_broadcast']['visible_edge'],receipts['cfg_ECC_fence']['visible_edge']):
        raise ValueError('compute before producer/config accepted visibility')
    if gather['accepted_edge']<compute['visible_edge']:
        raise ValueError('gather before native result; streaming needs per-chunk causal receipts')
    return max(0,finish-original_consumer_deadline)


def hbm_trace_binding(trace,review,terminal):
    if (review['log_sha256']!=terminal['logs_sha256']['Qwen/actual_sim.log']
            or review['source_commit']!=terminal['source_commit']
            or terminal['physical_credit'] or trace['SSFF']):
        raise ValueError('retained source/trace scope mismatch')
    source_cases={c['case']:c for c in trace['cases']};bound=[]
    for r in review['cases']:
        c=source_cases[r['case']]
        if sum(r['segments_cycles'].values())!=r['sum_cycles'] or r['sum_cycles']!=c['RF_fence_to_next_issue_cycles']:
            raise ValueError('phase decomposition does not telescope to actual trace')
        bound.append(dict(case=c['case'],rows=c['rows'],vectors=c['vectors'],
            dependent_SIMD_ops=c['dependent_alias_operations'],segments_cycles=r['segments_cycles'],
            total_schedule_cycles=r['sum_cycles'],last_visible_to_issue_cycles=c['RF_last_visible_to_next_issue_cycles'],
            last_retire_to_issue_cycles=c['RF_last_retire_to_next_issue_cycles'],
            last_ACK_hold_cycles=c['actual_last_ACK_hold_cycles']))
    return dict(target='Qwen_HBM',source_commit=terminal['source_commit'],
        source_hashes=terminal['source_sha256'],binary_sha256=terminal['binary_sha256'],
        log_sha256=review['log_sha256'],bench_clock_period_ns=trace['clock_period_ns'],
        testbench_policy=review['testbench_policy'],cases=bound,
        provider_natural_II_inferred=False,pure_launch_cost_inferred=False,
        directed_hold_cycles_not_subtracted_without_new_scheduler_evidence=True,
        calibrated_fulltoken_cost_or_DS_ROM_transfer=False,SSFF_or_frequency_credit=False)


def build():
    pins=[]
    def load(name):
        b=(OUT/'inputs'/name).read_bytes();pins.append(dict(snapshot=name,sha256=hashlib.sha256(b).hexdigest()))
        decoded=gzip.decompress(b) if name.endswith('.gz') else b
        return [json.loads(s) for s in decoded.splitlines()] if name.endswith('.jsonl.gz') else json.loads(decoded)
    manifest=load('manifest.json')
    for p in manifest:
        if hashlib.sha256((OUT/'inputs'/p['snapshot']).read_bytes()).hexdigest()!=p['sha256']:
            raise ValueError('input snapshot changed')
    partition=load('partition_model.json');cfg=load('cfg_interface.json');readback=load('readback.json')
    census=load('compiled_run_census.json.gz');records=census['records']
    if census['source_sha256']!=JOURNAL_SHA or len(records)!=46509:raise ValueError('wrong allocator census')
    if not readback['all40_all384_placed']:raise ValueError('not corrected full-product placement')
    if any(not r['per_shard_active_pair_capacity_pass'] for r in records):raise ValueError('actual run capacity exceeded')
    engram=[r for r in records if r['alias']=='engram.wkv']
    if len(engram)!=2 or any(sum(r['active_unique_pairs'])!=3200 for r in engram):raise ValueError('Engram witness missing')
    candidate=partition['single_parallel_successor'];dedicated=readback['dedicated_providers']
    ecc=load('cfg_ECC_directory.jsonl.gz');raw=load('cfg_provider_directory.jsonl.gz')
    if len(ecc)!=58 or len(raw)!=80:raise ValueError('all immutable providers required')
    provider_placements=[dict(kind=r['kind'],stage=r['stage'],
        layer=r.get('layer'),pairs=r['pairs'],
        shard_pair_counts=[sum(p//2048==s for p in r['pairs']) for s in (0,1)],
        declared_bits=r.get('bits'),protected_capacity_bits=r.get('protected_data_capacity_bits')) for r in raw+ecc]
    if any(r['shard_pair_counts']!=[103,0] for r in provider_placements if r['kind']=='ECC_FP4_SIDECAR'):
        raise ValueError('sidecar placement changed; reprice remote ECC')
    fp4_max=[max(r['active_unique_pairs'][s] for r in records if r['format']=='fp4') for s in (0,1)]
    review=load('Qwen_phase_review.json');terminal=load('Qwen_terminal.json')
    if review['terminal_receipt_sha256']!=hashlib.sha256((OUT/'inputs/Qwen_terminal.json').read_bytes()).hexdigest():
        raise ValueError('parent reviewed terminal receipt identity mismatch')
    trace=hbm_trace_binding(load('Qwen_trace.json'),review,terminal)
    return dict(schema='opentallas.dsrom.parallel-owner-capacity-calendar.v1',
        candidate_id=candidate['candidate_id'],source_pins=pins,input_manifest=manifest,
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        full46509_metadata_run_census_bound=True,all40_all384_symbolic_map_unchanged=True,
        source_header_and_encoded_storage_conservation=readback['conservation'],
        header_native_bytes_not_relabelled_as_padded_ROM_or_compute_area=True,
        site_shards=candidate['actual_622_shard_site_census'],
        largest_unpartitionable_Engram_witness=engram,
        one2048_die_whole_operator_compiler_admission=False,
        split_is_two_die_4096_logical_provider_not_two_independent_fulloperators=True,
        source_root_region_cuts=sum(r['source_root_regions_cut'] for r in records),
        single_die_overcapacity_operator_count=sum(not r['single2048_die_complete_operator_fit'] for r in records),
        max_active_pairs_by_shard=[max(r['active_unique_pairs'][s] for r in records) for s in (0,1)],
        compiled_capacity=dict(local_NP=2048,local_BF_dual_sites=362,local_q_sites=1686,
            macros4096x274_per_shard=8192,all721_original_padding_retained=True,
            cfg4096x72_macros_per_shard=14336,cfg_physical_bits_per_shard=4227858432,
            cfg_logical_payload_bits_per_shard=2516582400,
            all58x4x2_cfg_macros=6651904,
            return_declared_bits_per_shard=34885504,
            full_fixed_service_and_residual_per_shard_mm2=418.26916414007+47.208013178655904,
            total_priced_per_shard_mm2=candidate['conservative_priced_per_shard_mm2'],
            remaining_for_actual_link_adapter_exclusions_mm2=candidate['per_shard_margin_for_extra_IO_link_adapter_hardware_mm2'],
            hard_geometry_SSFF_and_extra_link_area_unbound=True),
        cfg_ECC=dict(actual_provider_contract=cfg['cfg_adapter_required_contract'],
            phase_words_delivered_per_shard=2048*25,
            field_ECC=cfg['raw_provider_adaptations'],
            ECC_sidecar_storage_not_freed_or_replicated_from_active_mask=True,
            require_global_codeword_pair_row_generation_to_local_site_translation=True,
            source_decoder_provider_and_terminal_fence_unimplemented=True),
        immutable_provider_shard_placement=provider_placements,
        mandatory_remote_ECC=dict(source_sidecar_sites_per_stage=103,all_sites_on_shard=0,
            declared_bits_by_stage={str(r['stage']):r['bits'] for r in ecc},
            protected_capacity_bits_per_stage=ecc[0]['protected_data_capacity_bits'],
            max_fp4_active_pairs_per_shard=fp4_max,
            source_sidecar_read_bits_per_active_pair_cycle=16,
            worst_declared_remote_sidecar_bits_per_stream_cycle=16*fp4_max[1],
            width_contract_not_guaranteed_read_service=True,
            no_sidecar_storage_halving_or_free_local_replica=True,
            calendar='Actual accepted shard1 codeword read -> source sidecar address/read at shard0 -> matching codeword/row/generation ECC terminal -> arithmetic acceptance; queue/ports/CDC and fault drain must be priced.',
            independent_cfg_ECC7_and_weight_ECC10_not_conflated=True),
        expert_envelope=dict(provenance='User-authorized current interface envelope; provider port implementation/calibration pending.',
            XN_FP32_elements_per_rank=5120,XN_broadcast_bytes_per_rank=20480,
            expert_activation_elements_per_rank=576,activation_local_bytes=2304,
            TP4_gathered_activation_elements=2304,TP4_gathered_activation_bytes=9216,
            BF16_in_FP32_result_elements_per_rank=1280,result_bytes_per_expert_per_rank=5120,
            ordered_six_results_bytes_per_rank=30720,ordered_six_plus_shared_last_bytes_per_rank=35840,
            EID_order='Actual selected6 slot order, then shared last; never sort by physical die, readiness or EID value.',
            do_not_add_per_expert_final_gathers_without_source_collective=True,
            ready_buffer_bytes_and_link_replica_lanes_and_ports_not_inferred_from_payload=True,
            pending_result_buffer_occupancy_requires_actual_acceptance_and_ordered_retirement=True),
        head_and_tables=dict(source_dedicated_provider_ledger=dedicated,
            unchanged_other_dies=44,largest_global_tensor_pairs=2525,
            compiler_global_pair_directory_not_physical_per_die_layout=True,
            no_dedicated_head_phase_in_layer_map=True,
            head_XN_BF16_proof_not_provider_or_argmax_or_order_qualification=True,
            head_ports_cfg_ECC_and_ordered_consumers_still_unbound=True),
        accepted_calendar_contract=dict(
            mandatory_paths=['XN_broadcast','cfg_ECC_fence','native_compute','ordered_result_gather'],
            each_receipt=['owner_node_rank_stage_phase_journal','source_receipt','resource_calendar',
                'timebase','ready_edge','accepted_edge','visible_edge','peak_live_bytes','reserved_bytes'],
            native_compute_requires_weight_code_scale_ECC_terminal_receipts=True,
            shared_transport='Global shared-resource/domain/II calendars, credits/leases; no per-rank free overlap.',
            intraowner_remote_result_port_bits_per_cycle=4416,
            port_width_is_not_transport_capacity=True,
            added_serial_stage_hops=0,logical_TP=4,
            actual_critical_path_delta_not_yet_bound=True,
            no_single_token_loss_condition='All accepted remote/config/native/ordered gather visibility meets original dependent consumer deadlines, with no new shared-resource stalls and full finite capacity.',
            deadline_check_API='accepted_deadline_delta(original_consumer_deadline, all_four_actual_receipts)',
            source_mode_fault_entry_contract_commit='c7d5ca90d0ac077c0af88956f16163f7bf0672b2',
            no_free_launch_or_overflow_or_missing_cost_defaults=True),
        measured_HBM_Qwen_connected_schedule=trace,
        DS_and_Qwen_workspaces=dict(no32MiB_cacheless_reference_free_compute=True,
            actual_polynomial_tiled_kernels_and_cache_traffic_provider_required=True,
            existing_workspace_debits_retained_until_source_bound_replacement=True),
        verdict='ONE_PARALLEL_LOGICAL_PROVIDER_CAPACITY_PASS_CONNECTED_DEADLINE_AND_PHYSICAL_GATES_OPEN',
        partition_count_or_NP_selected=False,build_admitted=False,
        physical_fit_or_full_token_admitted=False,new_allocator_reemit_RTL_PR_jobs=0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--extract-journal',type=Path);p.add_argument('--out',type=Path)
    a=p.parse_args()
    if a.extract_journal:
        extract(a.extract_journal,a.out or OUT/'inputs/compiled_run_census.json.gz');return
    output=a.out or OUT/'model-r5.json';b=(json.dumps(build(),indent=2,sort_keys=True)+'\n').encode()
    if output.exists() and output.read_bytes()!=b:raise ValueError('immutable verdict changed')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(b);print(hashlib.sha256(b).hexdigest())


if __name__=='__main__':main()
