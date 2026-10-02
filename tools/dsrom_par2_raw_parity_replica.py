#!/usr/bin/env python3
"""Raw parity replica envelope and immutable journal demand, not hardware admission.
No allocator, weight payload, RTL, encoding or physical execution. Interval arithmetic
uses the already exported f607 sidecar mapping; scheduling below is a proposal.
"""
import argparse, collections, gzip, hashlib, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_par2_raw_parity_replica_20261002'
JOURNAL_SHA='c91855b5b33c21c56dac3ea9ebc69a201ff582a3a6ad67a19024e89cd113881f'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def union_count(spans):
    total=0;end=-1
    for a,b in sorted(spans):
        if a<0 or b<a:raise ValueError('bad inclusive interval')
        total+=max(0,b-max(a,end+1)+1);end=max(end,b)
    return total

def leaf_intervals(start_bit,bits):
    """Canonical physical-word/MB/parity/4096-row arithmetic, no new placement."""
    if start_bit<0 or bits<=0:raise ValueError('invalid parity range')
    first=start_bit//256;last=(start_bit+bits-1)//256;out=[]
    while first<=last:
        bank=first//8192;end=min(last,(bank+1)*8192-1)
        for parity in (0,1):
            a=first+((parity-first)%2);b=end-((end-parity)%2)
            if a<=b:out.append(((bank//2,bank%2,parity),(a%8192//2,b%8192//2)))
        first=end+1
    return out

def demand(r,provider):
    if r['compiled_NP']!=4096 or r['format']!='fp4':raise ValueError('not corrected FP4 field')
    banks=collections.defaultdict(list);first_reads=collections.defaultdict(set)
    bits=[0,0];prefix=0;active=set();lane_bits=collections.Counter()
    for seg,pair,first,n,stride,start,words in r['plans']:
        if not 0<=pair<4096 or n<=0 or words<=0 or stride!=128:raise ValueError('invalid frozen run')
        base=r['ecc_bit_base']+prefix;length=n*words*16
        if base+length>provider['bits']:raise ValueError('outside declared sidecar')
        bits[pair//2048]+=length
        if pair>=2048:
            active.add(pair);lane_bits[pair]+=length
            for bank,span in leaf_intervals(base,length):banks[bank].append(span)
            for bank,span in leaf_intervals(base,16):first_reads[bank].add(span[0])
        prefix+=length
    counts={','.join(map(str,k)):union_count(v) for k,v in sorted(banks.items())}
    return dict(resident_parity_bits_local=bits[0],resident_parity_bits_remote=bits[1],
        remote_active_pairs=len(active),maximum_parity_bits_per_remote_pair=max(lane_bits.values(),default=0),requested_remote_parity_bits=bits[1],
        unique_raw256_reads_by_leaf=counts,unique_raw256_reads=sum(counts.values()),
        prefetch_single_read_port_per_leaf_cycles=max(counts.values(),default=0),
        simultaneous_run_start_bank_conflict_lower_bound=max((len(s) for s in first_reads.values()),default=0),
        simultaneous_run_start_model_not_retained_accepted_trace=True,
        touched_leaf_banks=len(counts),
        prefetch_buffer_required_data_bits=bits[1],
        parity_requests_16bits_per_paired_codeword=True)

def extract(journal,out):
    if sha(journal)!=JOURNAL_SHA:raise ValueError('not corrected622 journal')
    providers={r['stage']:r for r in rows(OUT/'inputs/canonical_ECC_directory.jsonl.gz')}
    records=[];ph=collections.Counter();local=remote=0
    with gzip.open(journal,'rt') as f:
        for ordinal,line in enumerate(f):
            r=json.loads(line);phase=ph[r['stage']];ph[r['stage']]+=1
            if r['format']!='fp4':continue
            d=demand(r,providers[r['stage']]);local+=d['resident_parity_bits_local'];remote+=d['resident_parity_bits_remote']
            records.append(dict(matrix_journal_ordinal=ordinal,stage=r['stage'],phase=phase,
                layer=r['layer'],expert=r['expert'],alias=r['alias'],**d))
    if len(records)!=46080:raise ValueError('missing full expert population')
    b=(json.dumps(dict(source_journal_sha256=JOURNAL_SHA,source_commit='622dbc897fd5ecb5a5b691e1ae39bea0ad751524',
        resident_local_bits=local,resident_remote_bits=remote,records=records),sort_keys=True)+'\n').encode()
    out.write_bytes(gzip.compress(b,mtime=0))

def rows(p):
    with gzip.open(p,'rt') as f:return [json.loads(l) for l in f]

def selected_cost(profile,read_II,read_latency,raw_decode,delivery,weight_decode,grants,credits_per_leaf):
    """Conservative full-phase prefetch; no speculative overlap or zero service."""
    if any(not isinstance(x,int) or x<=0 for x in (read_II,read_latency,raw_decode,delivery,weight_decode,grants,credits_per_leaf)):
        raise ValueError('positive calibrated/provisional cycles and grants required')
    required_credits=math.ceil((read_latency+raw_decode+delivery)/read_II)
    if credits_per_leaf<required_credits:raise ValueError('insufficient retained read debt credits for proposed II')
    rounds=max(profile['prefetch_single_read_port_per_leaf_cycles'],math.ceil(profile['unique_raw256_reads']/grants))
    # Whole batch terminal at last read + raw parity SECDED decode and actual delivery.
    load=0 if rounds==0 else (rounds-1)*read_II+read_latency+raw_decode+delivery
    return dict(required_read_debt_credits_per_leaf=required_credits,prefetch_before_compute_cycles=load,paired_weight_ECC_decode_cycles=weight_decode,
        nonoverlap_positive_cost_cycles=load+weight_decode,fullphase_prefetch_policy=True,
        cost_is_provisional_until_actual_accepted_calendar=True)

def build():
    paths=[OUT/'inputs/demand_profiles.json.gz',OUT/'inputs/native_mode_r6.json',OUT/'inputs/cfg_export_f607.py',
        OUT/'inputs/parallel_capacity_model_r5.json',OUT/'inputs/canonical_ECC_directory.jsonl.gz',
        OUT/'inputs/element_envelope_4096.json']
    paths += [OUT/'inputs'/n for n in ('ot_rom_4096x274_m8.json','ot_rom_4096x274_m8.lef','ot_rom_4096x274_m8_ss.lib','ot_rom_4096x274_m8_ff.lib','ot_rom_4096x274_m8.v','qwen_o4_unit_areas.json')]
    paths += [OUT/'inputs/local_ECC_mirror_option.jsonl.gz',OUT/'inputs/parallel_source_contract_r3.json',OUT/'inputs/compiled_readback_622.json',OUT/'inputs/snapshot_provenance.json']
    for p in json.loads((OUT/'inputs/snapshot_provenance.json').read_text()):
        if sha(OUT/'inputs'/p['snapshot'])!=p['sha256']:raise ValueError('source snapshot changed')
    pins=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in paths]
    d=json.loads(gzip.decompress(paths[0].read_bytes()));mode=json.loads(paths[1].read_text());base=json.loads(paths[3].read_text())
    if d['source_journal_sha256']!=JOURNAL_SHA or len(d['records'])!=46080:raise ValueError('incomplete source demand')
    providers=rows(paths[4]);env=json.loads(paths[5].read_text());rec=d['records']
    if any(len(p['pairs'])!=103 or max(p['pairs'])>=2048 for p in providers):raise ValueError('canonical provider placement changed')
    macro=json.loads(paths[6].read_text());units=json.loads(paths[11].read_text())
    if abs(macro['area']['macro_area_um2']-env['classes']['q_pair']['ROM_macro_area_um2']/4)>1e-7:raise ValueError('macro catalog body mismatch')
    for p in paths[6:11]:
        key='physical/asap7_memory_macros/ot_rom_4096x274_m8/'+p.name
        if key in env['source_sha256'] and env['source_sha256'][key]!=sha(p):raise ValueError('source envelope macro view mismatch')
    macro_um2=env['classes']['q_pair']['ROM_macro_area_um2']/4
    mirror=rows(paths[12]);contract=json.loads(paths[13].read_text())
    if contract['candidate']!=base['candidate_id'] or len(mirror)!=58:raise ValueError('not same PAR2 candidate')
    bf={i*4096//724 for i in range(724)}
    compiled=json.loads(paths[14].read_text())['compiled_field']
    padding=set(compiled['padding_site_IDs'])
    for original,copy in zip(providers,mirror):
        if (original['stage']!=copy['stage'] or original['pairs']!=copy['original_pairs'] or original['bits']!=copy['bits']
                or len(set(copy['mirror_pairs']))!=103 or any(p<2048 or p>=4096 or p in bf for p in copy['mirror_pairs'])
                or not set(copy['mirror_pairs'])<=padding or copy['extra_weight_macro_instances']!=0):raise ValueError('mirror alias/site/provider mismatch')
    body=103*4*macro_um2/1e6
    margin=base['compiled_capacity']['remaining_for_actual_link_adapter_exclusions_mm2']
    groups=collections.defaultdict(list)
    for r in rec:groups[r['layer'],r['expert']].append(r)
    if len(groups)!=40*384 or any(len(v)!=3 for v in groups.values()):raise ValueError('expert triple lost')
    best=worst=0
    for layer in range(40):
        values=sorted(sum(x['prefetch_single_read_port_per_leaf_cycles'] for x in groups[layer,e]) for e in range(384))
        best+=sum(values[:6]);worst+=sum(values[-6:])
    buffer_bits=128*max(r['maximum_parity_bits_per_remote_pair'] for r in rec)
    # FF proxy only; preserve raw captured274 plus per-lane authenticated headers.
    capture_bits=412*274;headers=128*58;bank_control=412*(58+12+1)
    ff_proxy=(buffer_bits+capture_bits+headers+bank_control)*units['dff_bit_um2']/0.5/1e6
    mandatory_state_bits=contract['minimal_adapter_state']['additional_table_copy_bits_per_old_rank_owner']+contract['minimal_adapter_state']['root_capture_one_full64packet_burst_bits']+mode['composition_cost']['new_FF_bits_per_adapter']
    other_state_proxy=mandatory_state_bits*units['dff_bit_um2']/0.5/1e6
    def maximum(k):
        r=max(rec,key=lambda r:r[k]);return {x:r[x] for x in ('matrix_journal_ordinal','stage','phase','layer','expert','alias',k)}
    return dict(schema='opentallas.dsrom.par2.raw-parity-replica.v1',candidate_id=base['candidate_id'],
        variant_id=base['candidate_id']+'-LOCAL-RAW-ECC-IN-PADDING',opt_in_default=False,
        source_pins=pins,generator_sha256=sha(Path(__file__)),
        canonical_sidecar_API='f6073fffd sidecar_address(provider, linear_bit); unchanged stage, canonical provider pair, MB/parity/physical-row/data-bit. Explicit local replica alias required; not a compiled weight site.',
        replica=dict(raw_pairs_per_stage_rank=103,raw4096x274_macros_per_shard1_die=412,
            extra_macros_all58x4_shard1_dies=0,already_charged_macros_repurposed_all58x4_shard1_dies=412*58*4,raw_physical_bits_per_shard1=412*4096*274,
            protected256bit_capacity=103*16384*256,declared_stage_bits={str(p['stage']):p['bits'] for p in providers},
            body_only_mm2=body,additive_macro_body_mm2=0,macro_body_already_contained_in_compiled_field=True,
            remaining_padding_q_pairs_per_shard1=281,mirror_alias_source_commit='124e870c5',
            macro_body_each_um2=macro_um2,adjacent_q_compute_replication=False,
            added_compiled_weight_sites=0,old_weight_and_ECC_storage_retained=True,
            placement='Exact Nash103Q_ONLY padding aliases per stage inside chargedNP2048; no original compute/frame/capture area reclaimed, no new raw instances. Copy identity/content and physical ports unqualified',
            remaining_mm2_before_replica_control_and_physical_exclusions=margin,
            explicit_staging_FF50_proxy_mm2=ff_proxy,
            explicit_staging_bits=dict(raw_all_leaf_captures=capture_bits,parity128_dedicated_lane_queues=buffer_bits,per_pair128_authenticated_headers=headers,bank_credit1_tag58_address12_valid1=bank_control),
            FF_area_provenance='retained qwen_o4_unit_areas dff_bit_um2; TT cell proxy at50pct density, not contextual SSFF',
            remaining_after_body_and_explicit_staging_proxy_mm2=margin-ff_proxy,
            additional_transport_admission_state_no_containment_proxy=dict(bits=mandatory_state_bits,
                phase_key_policy_copy_bits=33792,root108_capture_bits=6912,mode_guard_bits=17,
                FF50_proxy_mm2=other_state_proxy,
                table_RAM_implementation_and_existing_state_containment_unbound=True),
            total_priced_per_shard1_with_new_proxies_mm2=base['compiled_capacity']['total_priced_per_shard_mm2']+ff_proxy+other_state_proxy,
            remaining_after_all_explicit_proxies_mm2=margin-ff_proxy-other_state_proxy,
            macro_pin_demand=dict(addr12_per_leaf=412*12,ce_per_leaf=412,clk_per_leaf=412,rd274_per_leaf=412*274,signal_pins=412*288),
            macro_geometry_um=macro['area'],
            macro_clock=dict(SS_clk_to_q_ps=macro['timing']['ss']['clk_to_q_ps'],SS_min_period_ps=macro['timing']['ss']['min_period_ps'],FF_hold_ps=macro['timing']['ff']['hold_ps'],
                target_period_ps=1000/1.2,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
                remaining_SS_capture_setup_wire_clock_budget_ps=1000/1.2-60-macro['timing']['ss']['clk_to_q_ps'],
                generated_characterized_views_not_contextual_signoff=True),
            additional_read_credits_FF50_proxy_formula_mm2='(credits_per_leaf-1)*412*58*0.2916/0.5/1e6; base1credit/leaf charged. Need credits>=ceil((macro+rawdecode+delivery latency)/II).',
            no_existing_capture_register_containment_credit=True,
            unknown_positive_charges=['address distribution/fanout','bank grant arbitration and bounded credits',
                'raw SECDED10 decoder(s) and quarantine','gather demux and FIFO controls (data storage proxy charged)',
                'weight ECC decode/align pipeline','accepted read/visible/terminal tags and cancellation',
                'pins/OBS/halo/clock/PG/hold/channel tracks','SS macro clk-to-q and FF hold in context'],
            whole_reticle_geometry_fit=False),
        full_resident_census=dict(fp4_phases=len(rec),local_bits=d['resident_local_bits'],remote_bits=d['resident_remote_bits'],
            remote_fraction=d['resident_remote_bits']/(d['resident_local_bits']+d['resident_remote_bits']),
            all_fp4_have_remote=all(r['remote_active_pairs']>0 for r in rec),
            is_selected_token_traffic=False,rank0to3_identical_symbolic_layout_not_measured_traffic=True),
        selected_phase_demand=dict(profiles_path=pins[0]['path'],
            max_prefetch_leaf_cycles=maximum('prefetch_single_read_port_per_leaf_cycles'),
            max_unique_reads=maximum('unique_raw256_reads'),
            max_prefetch_buffer_bits=maximum('prefetch_buffer_required_data_bits'),
            max_run_start_conflict=maximum('simultaneous_run_start_bank_conflict_lower_bound'),
            requested_stream_bits_per_cycle_upper=2048,
            raw_word_bits=256,read_ports_per_leaf_proposed=1,leaf_banks_available_storage_only=412,
            all_leaf_read_simultaneity_not_qualified=True,
            reuse='One accepted corrected raw256 word may supply up to16paired-codeword side16 fields, only within authenticated immutable phase/generation lease. Count unique words, not one remote transaction per16bit request.',
            selected_six_expert_fullphase_prefetch_leaf_work_bounds=dict(
                minimum_over_six_distinct_selected_EIDs_all40_layers=best,maximum=worst,
                triples=720,units='single-port leaf read iterations, not fulltoken cycles',
                actual_EIDs_required=True,no_intertoken_cache_or_overlap_credit=True,
                fresh_prefetch_before_each_phase_policy_is_not_mandatory_architecture_lower_bound=True),
            minimum_crossbar_operation_screen=dict(raw_decode_lanes_proposed=4,shared_grants_per_die=4,
                raw266_selector_mux2_upper=4*(412-1)*266,
                decoded_data256_grant_boundary_bits=4*256,
                parity_lane_delivery_boundary_bits=128*16,
                address_per_bank_bits=12,per_bank_control_proposed_credit=1,
                counts_are_prospective_structure_not_synthesized_cells=True,
                actual_decoder_code_map_and_logic_area_unbound=True,
                actual_track_capacity_and_macro_OBS_PG_union_missing=True),
            decoder_gather_schedule='At most4distinct leaf banks touched per frozen FP4 phase. Up to4parallel corrected256bit gather grants plus412:4 bank selection are a proposal, not new read ports inside macros; arbitrate per-bank rows and retain finite outstanding debt.',
            prefetch_buffer='128 finite per-active-pair queues, each maximum frozen per-pair parity demand; explicit FF50proxy. No SRAM or existing-register reuse credit. Assign run pair to queue on accepted phase lease; refill/grants/tags/overflow/fault drain needed.',
            transport='Nominal2048bits/cycle is consumer demand, not raw-bank/gather throughput.'),
        finite_calendar=dict(policy='Full-phase local prefetch then weight+parity ECC before arithmetic; nonoverlap priced, no assumed prefetch hiding.',
            formula='load=(max(max_leaf_unique_reads,ceil(total_unique_reads/grants))-1)*read_II+macro_latency+raw_SECDED_latency+delivery_latency; add positive weight_ECC latency before corresponding compute.',
            require_debt_credits_per_leaf='ceil((macro_latency+raw_decode+delivery)/read_II); reject II below finite credit capability. Whole owner credit is distinct from per-leaf accepted read debt.',
            per_leaf_default_debt_credit=1,require_shared_raw_decoder_gather_grant_calendar_across_banks=True,
            all_rank_die_channels_dedicated_only_if_provider_instance_mapping_proven=True,
            native_owner_credit=1,VM_credit=1,VM_request_sequence_bits=10,
            result_identity_bits=58,identity_components='r6 57bits(operation sequence13+phase10+base34) plus explicit shard1',
            mode_source_commit='1d8380224b0cc5b11364c4a20f8328d4998abdb0',
            native_mode_composition=mode['composition_cost'],
            ordered_dependencies=['accepted authenticated descriptor/EID','owner credit acquired','actual accepted config25word delivery fences',
                'immutable canonical parity word accepted','raw sidecar SECDED good/corrected terminal',
                'same codeword paired weight+sidecar ECC good/corrected terminal','arithmetic valid acceptance',
                'golden ordered result delivery','owner debt drain including canceled/quarantined transfers'],
            clock_domains='Stream1.2GHz and serial0.9GHz targets only; CDC and measured SS/FF required.',
            latency_delta_calibrated=False,zero_cross_die_ECC_data_only_if_local_adapter_qualified=True,
            corrected_source_transport_contract=contract['finite_transport_requirements'],
            source_root_packet_bits=contract['source_widths']['root_packet_proposal'],
            nonbackpressured64root_burst_capture_bits=contract['minimal_adapter_state']['root_capture_one_full64packet_burst_bits'],
            exact_mirror_alias_directory_path=str(paths[12].relative_to(ROOT)),
            remaining_cross_die_paths=['XN activation','config/provider admission','HE/CROM if remote','ordered paired result gather']),
        decision='Raw-body already contained by exact padding alias; zero additional macro body. Explicit FIFO/capture/header proxy and positive finite bank service. No single-token no-loss proof, no candidate adoption.',
        build_admitted=False,physical_qualified=False,fulltoken_rate_qualified=False,
        historical_924mm2_FAIL_and_old_S58_FAIL_preserved=True,
        dedicated_outside_padding_counterfactual=dict(extra_macros=412,body_additive_mm2=body,
            reason='Earlier requested standalone raw-block screen retained as policy counterfactual, superseded by exact124 padding aliases; not charged to current variant.'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--extract-journal',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.extract_journal:extract(a.extract_journal,a.output)
    else:dump(a.output,build())
