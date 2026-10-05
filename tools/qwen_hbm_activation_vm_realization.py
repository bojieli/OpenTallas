#!/usr/bin/env python3
"""Source-only affine VM demand compiler. No weights/activations or RTL execution.

Opt-in analytical proposal; emits no engine RTL and does not modify uarch_model.
Maxwell hook: build_proposal(root, position=8191, token=24) -> JSON-compatible dict.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from hdc_isa import decode

VM_WORDS = 177808
AREA = 174.120 * 29.736  # pinned aligned-v2 LEF; square micrometres
ROOT_RECORD = Path('results/rtl/qwen_hbm_activation_vm_realization_20261005')


def physical_address(a):
    """Existing DS bank4 mapping, with scalar range guard retained."""
    if not 0 <= a < VM_WORDS:
        raise ValueError(f'VM scalar out of range: {a}')
    w, lane = divmod(a, 16)
    return dict(word=w, lane=lane, bank=w % 4, row=(w // 4) % 512,
                depth_group=w // 2048, column=lane // 4, column_lane=lane % 4)


def demand(addresses):
    # Equal scalar addresses are broadcast; whole 512-bit words count once.
    counts = Counter(addresses)
    words = {a // 16 for a in counts}
    banks = [sum(w % 4 == b for w in words) for b in range(4)]
    # A legal read returns four *consecutive* words, not four arbitrary rows.
    # Exact minimum four-word interval cover: greedily start at lowest uncovered.
    bases = []
    for w in sorted(words):
        if not bases or w >= bases[-1] + 4:
            bases.append(w)
    return dict(requests=sum(counts.values()), distinct_scalars=len(counts),
                useful_bytes=4*len(counts), broadcast_max=max(counts.values(), default=0),
                distinct_512bit_words=len(words), bank_word_counts=banks,
                arbitrary_bank_read_II_floor=max(banks, default=0),
                existing_ds_read_beats=len(bases), fetched_bytes=256*len(bases),
                existing_ds_write_beats=max(banks, default=0),
                RF_vectors=len({a//128 for a in counts}),
                RF_read_transactions=math.ceil(len({a//128 for a in counts})/2),
                scalar_min=min(counts, default=None), scalar_max=max(counts, default=None))


def effective(d, position, token):
    d = d.copy()
    dyn = [0, token*4096, position*64,
           (position//16)*(128*16)+position%16, position*128, position+1,
           position//(16*6144)+1, 0]
    for field in ('wbase','xbase','obase','nout','tiles','k'):
        index = d['me_d_'+field]
        add = position//(16*(6144//(1 << d['me_split'])))+1 if field == 'tiles' and index == 6 else dyn[index]
        d['me_'+field] = (d['me_'+field]+add) % (1 << (18 if field in ('nout','tiles','k') else 24))
    d['su_nin'] = (d['su_nin']+dyn[d['su_d_nin']]) % (1 << 18)
    for p in ('a','b','c','d'):
        d[p+'_base'] = (d[p+'_base']+dyn[d[p+'_d']]) % (1 << 24)
    return d


def extrema(samples):
    keys = ('requests','distinct_scalars','useful_bytes','broadcast_max',
            'distinct_512bit_words','arbitrary_bank_read_II_floor',
            'existing_ds_read_beats','fetched_bytes','existing_ds_write_beats','RF_vectors','RF_read_transactions')
    return {k: max((s[k] for s in samples), default=0) for k in keys}


def me_analysis(d):
    s = 1 << d['me_split']
    chunks = min(s, 2048)
    enabled = sum((c >> d['me_split']) < (6144 >> d['me_split']) for c in range(2048))
    ksteps = math.ceil(d['me_k']/s) if d['me_wsrc'] else d['me_k']
    assert ksteps > 0 and d['me_tiles'] > 0
    # Address residue determines both the four-word covering and bank conflicts.
    # k/j cycles are counted by residue, not by numerical execution.
    period = 64 // math.gcd(d['me_xks'], 64)
    hist = Counter()
    for k in range(min(ksteps,period)):
        nk = (ksteps-1-k)//period+1
        for j in range(8):
            hist[(d['me_xbase']+k*d['me_xks']+j*d['me_xjs']) % 64] += nk*d['me_tiles']
    samples = []
    read_beats = 0
    for residue, n in sorted(hist.items()):
        a = [residue+(c % s)*d['me_xcs'] for c in range(enabled)]
        q = demand(a); q.update(base_residue64=residue, logical_edges=n)
        samples.append(q); read_beats += n*q['existing_ds_read_beats']
    low = d['me_xbase']
    high = low+(ksteps-1)*d['me_xks']+7*d['me_xjs']+(chunks-1)*d['me_xcs']
    # Addresses are registered every active edge, including repeated J/tiles;
    # no dead arithmetic operand or tail read is removed from request accounting.
    writer_samples = []
    writer_words = set()
    all_scalars = set()
    scalar_collisions = []
    ports = 6144//s
    if d['me_oen']:
        for t in range(d['me_tiles']):
            for j in range(8):
                a = []
                for g in range(min(96,ports)):
                    rowbase = (t*ports*16 if d['me_mmode'] else t*ports*128+j*16)
                    rowbase += g*(16 if d['me_mmode'] else 128)
                    for lane in range(16):
                        if rowbase+lane < d['me_nout']:
                            waddr = d['me_obase']+t*ports*d['me_ots']+j*d['me_ojs']+g*d['me_ots']
                            a.append(waddr*16+lane)
                if a:
                    if len(set(a)) != len(a): scalar_collisions.append([t,j])
                    writer_words.update(x//16 for x in a);all_scalars.update(a)
                    writer_samples.append(demand(a))
    # ME writes occur at the final k only, after the selected result pipelines.
    # No simultaneous-ME/SU timing is inferred here.
    return dict(split=d['me_split'], ksteps=ksteps, tiles=d['me_tiles'],
                address_expression='xbase + k*xks + j*xjs + (port mod 2^split)*xcs; t resets xbase',
                scalar_range=[low,high], range_pass=(0 <= low <= high < VM_WORDS),
                read_max=extrema(samples), residue_histogram=samples,
                logical_read_edges=ksteps*8*d['me_tiles'], ds_read_beats_total=read_beats,
                ds_extra_read_issue_edges=read_beats-ksteps*8*d['me_tiles'],
                read_only_extra_issue_us=(read_beats-ksteps*8*d['me_tiles'])/1200,
                write_max=extrema(writer_samples), write_events=len(writer_samples),
                ds_write_beats_total=sum(x['existing_ds_write_beats'] for x in writer_samples),
                write_scalar_range=[min(all_scalars),max(all_scalars)] if all_scalars else None,
                write_range_pass=all(0 <= a < VM_WORDS for a in all_scalars),
                write_unique_words=len(writer_words), duplicate_same_event_scalars=scalar_collisions,
                mx_writer=dict(enabled=bool(d['me_rmax']),
                               scalar_addresses=[(d['me_mbase']//16)*16+((d['me_mbase']%16+j)%16) for j in range(8)] if d['me_rmax'] else [],
                               masked_word=d['me_mbase']//16 if d['me_rmax'] else None,
                               ds_write_beats=1 if d['me_rmax'] else 0),
                cross_edge_reuse_credit=0, simultaneous_su_or_collective_cost_included=False)


def su_analysis(d):
    # All three VM reads are asserted when *_src == 0, even if arithmetic
    # bypasses that operand. Preserve requests; source!=0 is ROM, not VM.
    nvec = math.ceil(d['su_nin']/64)
    samples = []; writes = []; rd_lo=[]; rd_hi=[];wr_lo=[];wr_hi=[]
    live_edges = d['su_nout']*nvec
    # Periodic residue demand with exact partial tail. At most 64 classes per
    # dimension; no activation data, no inference and no dynamic event replay.
    operiod = 64//math.gcd(64, *(d[p+'_so'] for p in 'abc'))
    vperiod = 64//math.gcd(64, *(64*d[p+'_si'] for p in 'abc'))
    for o in range(min(d['su_nout'],operiod)):
        for v in sorted(set(range(min(nvec,vperiod))) | ({nvec-1} if nvec else set())):
            nl = min(64,d['su_nin']-v*64)
            a = [d[p+'_base']+o*d[p+'_so']+(v*64+l)*d[p+'_si']
                 for p in 'abc' if d[p+'_src']==0 for l in range(nl)]
            samples.append(demand(a))
    for p in 'abc':
        if d[p+'_src']==0 and live_edges:
            rd_lo.append(d[p+'_base'])
            rd_hi.append(d[p+'_base']+(d['su_nout']-1)*d[p+'_so']+(d['su_nin']-1)*d[p+'_si'])
    if d['dst']==1 and live_edges:
        operiod = 64//math.gcd(64,d['d_so'])
        for o in range(min(d['su_nout'],operiod)):
            for v in sorted(set(range(min(nvec,1))) | {nvec-1}):
                nl=min(64,d['su_nin']-v*64)
                a=[d['d_base']+o*d['d_so']+(v*64+l)*d['d_si'] for l in range(nl)]
                q=demand(a);q['duplicate_scalar_writers']=len(a)-len(set(a));writes.append(q)
        wr_lo.append(d['d_base']);wr_hi.append(d['d_base']+(d['su_nout']-1)*d['d_so']+(d['su_nin']-1)*d['d_si'])
    if d['red']:
        wr_lo.append(d['r_base']);wr_hi.append(d['r_base']+(d['su_nout']-1)*d['r_so'])
    return dict(address_expression='base + output_row*so + (vector_step*64+lane)*si',
                read_max=extrema(samples), write_max=extrema(writes),
                logical_read_edges=live_edges, read_scalar_range=[min(rd_lo),max(rd_hi)] if rd_lo else None,
                write_scalar_range=[min(wr_lo),max(wr_hi)] if wr_lo else None,
                range_pass=all(0 <= a < VM_WORDS for a in rd_lo+rd_hi+wr_lo+wr_hi),
                reducer=dict(enabled=bool(d['red']), scalar_writes=d['su_nout'] if d['red'] else 0,
                             base=d['r_base'],stride=d['r_so'],additional_write_bank_ports=1 if d['red'] else 0),
                kv_writes_not_vm=(d['dst']==2), reads_not_elided_by_arithmetic_bypass=True,
                missing_variable_latency_ready=True)


def build_proposal(root, position=8191, token=24):
    root=Path(root); inp=root/ROOT_RECORD/'inputs'
    pins=json.loads((inp/'source_pins.json').read_text())
    params=json.loads((inp/'expected_build_params.json').read_text())
    assert all(flag in params['die'] for flag in ['-GG=6144','-GNW=18','-GD=4','-GSW=64','-GSMIN=6','-GSMAX=11','-GXVM=1','-GENABLE_AR256=0'])
    for p in pins:
        assert hashlib.sha256((root/p['path']).read_bytes()).hexdigest()==p['sha256'],p['path']
    records=[];collectives=[]
    for stage in ('L5','L20','head'):
        for rank in range(4):
            folder=inp/f'{stage}-d{rank}'
            raw=(folder/'program.hex').read_text().splitlines()
            executed=set()
            for desc in (folder/'segments.hex').read_text().splitlines():
                dw=int(desc,16)
                if dw&3==0: break
                pc=(dw>>32)&65535
                while pc<len(raw):
                    executed.add(pc)
                    if decode(int(raw[pc],16))['unit']==0:break
                    pc+=1
                else:raise ValueError('segment without finite END')
            for pc,line in enumerate(raw):
                if pc not in executed:continue
                decoded=decode(int(line,16)); d=effective(decoded,position,token)
                if d['unit'] not in (1,2):continue
                q=me_analysis(d) if d['unit']==1 else su_analysis(d)
                records.append(dict(stage=stage,rank=rank,pc=pc,unit='ME' if d['unit']==1 else 'SU',
                                    encoded_word_sha256=hashlib.sha256(line.encode()).hexdigest(),
                                    decoded=decoded,effective=d,analysis=q))
            for i,line in enumerate((folder/'segments.hex').read_text().splitlines()):
                word=int(line,16); kind=word&3;vw=(word>>2)&255; nw=(word>>10)&255
                # Selected ENABLE_AR256=0: zero remains zero (not 256).
                collectives.append(dict(stage=stage,rank=rank,descriptor=i,kind=kind,
                                        program_base=(word>>32)&65535,
                                        vector_base=vw,vector_words=nw if kind==1 else 0,
                                        scalar_range=[vw*16,(vw+nw)*16-1] if kind==1 else None,
                                        ds_read_II_per_vector=1 if kind==1 else 0,
                                        ds_write_II_per_vector=1 if kind==1 else 0,
                                        network_cycles_not_credit=0))
    me=[r for r in records if r['unit']=='ME'];su=[r for r in records if r['unit']=='SU']
    peak_r=max(r['analysis']['read_max']['existing_ds_read_beats'] for r in me)
    peak_w=max(r['analysis']['write_max']['existing_ds_write_beats'] for r in me)
    peak_su=max(r['analysis']['read_max']['existing_ds_read_beats'] for r in su)
    stagecost=[]
    for stage,rank in ((st,rk) for st in ('L5','L20','head') for rk in range(4)):
        a=[r for r in me if r['stage']==stage and r['rank']==rank]
        stagecost.append(dict(stage=stage,rank=rank,logical_ME_read_edges=sum(r['analysis']['logical_read_edges'] for r in a),
                              ds_read_issue_beats=sum(r['analysis']['ds_read_beats_total'] for r in a),
                              additional_ME_read_issue_edges=sum(r['analysis']['ds_extra_read_issue_edges'] for r in a),
                              additional_ME_read_issue_us=sum(r['analysis']['read_only_extra_issue_us'] for r in a),
                              ds_ME_write_beats=sum(r['analysis']['ds_write_beats_total'] for r in a),
                              scope='isolated read-service workload; no system delta or overlap credit'))
    rf_reference=dict(provider='ot_gpu_rf_service',selected=False,
                          vector_address='scalar>>7',lane='scalar&127',bank='(scalar&127)>>3',
                          page='(scalar>>14)&3',row='(scalar>>7)&127',
                          logical_words_per_instance=65536,physical_bytes_per_instance=524288,
                          capacity_only_instances=3,macro_body_area_per_instance_um2=128*94.824*41.040,
                          capacity_only_body_area_um2=3*128*94.824*41.040,
                          max_vectors_per_read=2,best_read_II=3,read_result_after_accept_edges=1,
                          transactions_latency='T transactions: last result N+3*(T-1)+1; consumer N+3*(T-1)+2',
                          scalar_write_mask_present=False,SU_scalar_writes_require_preservation_RMW=True,
                          coherence_and_loaded_corridor_area_um2=None)
    head_records=[r for r in me if r['stage']=='head' and r['rank']==0]
    head_writers=[r for r in su if r['stage']=='head' and r['rank']==0 and r['analysis']['write_scalar_range']]
    # Source-order ownership: the only head input writer is SU PC2; all later
    # cached commands are ME argmax (OEN=0), then END/argmax descriptor.
    assert [(r['pc'],r['analysis']['write_scalar_range']) for r in head_writers if r['analysis']['write_scalar_range'][0] <= 12287 and r['analysis']['write_scalar_range'][1] >= 8192] == [(2,[8192,12287])]
    assert all(r['effective']['me_oen']==0 for r in head_records)
    for rank in range(4):
        hr=[r for r in me if r['stage']=='head' and r['rank']==rank]
        hw=[r for r in su if r['stage']=='head' and r['rank']==rank and r['analysis']['write_scalar_range']]
        assert all(r['effective']['me_xbase']==8192 and r['effective']['me_xcs']==2 and r['effective']['me_xks']==1 and r['effective']['me_xjs']==0 and r['effective']['me_k']==2 and r['effective']['me_oen']==0 for r in hr)
        assert [(r['pc'],r['analysis']['write_scalar_range']) for r in hw if r['analysis']['write_scalar_range'][0] <= 12287 and r['analysis']['write_scalar_range'][1] >= 8192] == [(2,[8192,12287])]
    head_reuse=dict(applicable_ranks=[0,1,2,3],source_region=[8192,12287],producer_pc=2,consumer_pcs=[3,4,5,6],
                    no_later_cached_VM_writer=True,post_collective_kind=2,
                    repeated_logical_read_edges=sum(r['analysis']['logical_read_edges'] for r in head_records),
                    staging_words=4096,staging_data_bits=131072,
                    staging_DFF_body_floor_um2=131072*.2916,
                    parity_2to1_select_bits=2048*32,
                    mux_body_assumed_um2=2048*32*.2,
                    assumed_mux_basis='existing uarch_model .2um2/2:1 bit mux estimate, not measured',
                    source_fill_beats=64,source_fill_bytes=16384,
                    bank_rows_for_fill=[64,64,64,64],source_fill_issue_us=64/1200,
                    local_output_bits_per_admitted_ME_edge=65536,local_scalar_reads=2048,
                    lane_expression='staged_word[2*port+k]; k=0 or 1, j/t repeat without modifying the word',
                    local_operand_ports_are_wiring_and_2to1_selection_not_free_SRAM_reads=True,
                    per_die_macro_body_plus_local_DFF_mux_floor_um2=256*AREA+131072*.2916+65536*.2,
                    fill_requires_real_SU_PC2_write_visibility_ACK=True,
                    current_chase_n64_covers_all_64_SU_source_vectors=True,
                    current_SU_progress_has_no_physical_backend_ACK_binding=True,
                    producer_wait_cycles=None,control_clock_fanout_wire_area_um2=None,
                    per_stage_total_latency_us=None,adopted=False,credited_reuse_cycles=0)
    result=dict(schema='opentallas.qwen-hbm.activation-vm-realization.v1',
                verdict='MODEL_PROPOSAL_NOT_REALIZED_CURRENT_RATE_UNSERVICEABLE_BY_ONE_EXISTING_PROVIDER',
                opt_in=True, default_enabled=False, adopted=False, position=position,token=token,source_pins=pins,
                implementation_pins=json.loads((inp/'implementation_pins.json').read_text()),
                RF_reference=rf_reference,head_source_reuse_proposal=head_reuse,selected_build_params=params,
                mapping=dict(provider='ot_v41_vm_bank4_macro / masked_visible_r2',
                             scalar_words=VM_WORDS,retained_bytes=VM_WORDS*4,
                             scalar_to_word='a>>4',lane='a&15',bank='(a>>4)&3',
                             row='(a>>6)&511',group='a>>15',column='(a>>2)&3',
                             last_address=physical_address(VM_WORDS-1),
                             injective=True,all_scalar_addresses_checked=VM_WORDS,
                             full_existing_groups=16,existing_macros=256,physical_bytes=2097152,
                             capacity_only_required_groups=math.ceil(VM_WORDS/32768),
                             capacity_only_macros=16*math.ceil(VM_WORDS/32768),
                             full_macro_body_area_um2=256*AREA,
                             capacity_only_macro_body_area_um2=16*math.ceil(VM_WORDS/32768)*AREA,
                             capacity_only_geometry_not_adopted=True,
                             area_basis='aligned-v2 predictive LEF body only; controller/mux/clock/wires additional',
                             SS_macro_clkq_ps=524.072474,SS_macro_min_period_ps=480.333184,
                             budget_period_ps=833.333,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
                             macro_only_setup_budget_remaining_ps=833.333-60-524.072474,
                             loaded_selector_capture_setup_not_included=True,
                             floorplan_slots=None,loaded_corridor_tracks=None,physical_adopted=False),
                peak=dict(ME_read_beats=peak_r,ME_same_bank_write_beats=peak_w,SU_read_beats=peak_su,
                          ME_replicated_read_images_for_same_edge=peak_r,
                          replicated_full_body_area_um2=peak_r*256*AREA,
                          replicated_retained_bytes=peak_r*VM_WORDS*4,
                          replicated_physical_bytes=peak_r*2097152,
                          write_coherence_fanout=peak_r,
                          full_rate_write_ports_in_peak_bank=peak_w,
                          read_replication_does_not_supply_extra_write_ports=True,
                          replicas_are_existing_provider_mapping_reference_not_global_minimum=True,
                          SU_parallel_read_images_for_fixed_latency_without_reuse=peak_su),
                ports=dict(existing_DS_read_bytes_per_edge=256,existing_DS_write_bytes_per_edge=256,
                           external_VX_data_bits=65536,external_VX_address_bits=49152,external_VX_enable_bits=2048,
                           SU_data_read_bits=3*64*32,SU_address_bits=3*64*24,SU_enable_bits=192,
                           ME_write_face_bits=96*16*32,ME_write_address_bits=96*24,ME_write_lane_mask_bits=96*16,
                           SU_write_bits=64*32,SU_write_address_bits=64*24,SU_write_enables=64,
                           MX_write_bits=512,reducer_write_bits=32,collective_read_write_bits_each=512,
                           maximum_aggregate_snapshot_read_seats=2048+192+16,
                           maximum_aggregate_snapshot_read_data_bits=(2048+192+16)*32,
                           maximum_aggregate_write_seats=1536+64+16+1+16,
                           write_seat_bits=32+24+1,
                           maximum_aggregate_write_seat_bits=(1536+64+16+1+16)*(32+24+1),
                           one_frame_response_DFF_floor_um2=(2048+192+16)*32*.2916,
                           one_frame_write_seat_DFF_floor_um2=(1536+64+16+1+16)*(32+24+1)*.2916,
                           DFF_proxy_basis='existing tools/uarch_model.py DFF_UM2=.2916; no controller/mux/clock area credit',
                           buffering_area_um2=None,buffering_area_must_be_priced=True),
                finite_service=dict(existing_nonpipe_DS_read_result_after_accept_edges=1,
                                    existing_nonpipe_DS_earliest_consumer_capture_after_accept_edges=2,
                                    masked_r2_read_result_after_accept_edges=4,
                                    masked_r2_read_earliest_consumer_capture_after_accept_edges=5,
                                    masked_r2_write_macro_commit_after_accept_edges=2,
                                    masked_r2_write_ack_after_accept_edges=3,
                                    issue_II=1,
                                    isolated_read_last_return='First accept N: last result N+B for nonpipe, N+B+3 for masked r2; consumer captures no earlier than following edge',
                                    added_ME_read_issue_edge_formula='B-1, before latency/other-client/read-write-collision costs',
                                    read_write_collision='same 512-bit word cannot issue together; preserve host read-before-write',
                                    write_mask='scalar a maps to 16-lane mask of word a>>4; r2 owns actual mask/ACK',
                                    write_order='host order ME, MX, SU, reducer, collective; retain last-writer order for overlapping scalar',
                                    other_client_interference_cycles=None,total_stage_or_token_latency_us=None,
                                    cross_edge_reuse_credit=0,
                                    frame_read_issue_II='max(ME/SU/collective deduplicated read-window union B, per-bank distinct write rows W) is a throughput lower bound only',
                                    conservative_serial_frame_recipe='B read issues then W masked-write issues plus read capture/write visibility tails; not implemented and no SU freeze claimed',
                                    finite_frame_extra_edges='at least max(B,W)-1 without cross-edge reuse; read/write separation needs B+W-1 plus tails',
                                    whole_input_ready_or_visibility_inferred_from_chase=False),
                missing_hardware=[
                    'No selected VM backend instantiated; host m.vm is not a bank/controller.',
                    'ME_STALL/me_mem_ok/me_clk_en exist. New supply must freeze response/tag/XVM registers on the same admitted ME edges; hb_me_ok alone currently covers weights.',
                    'SU has no variable-latency admission during an active op. One DS service cannot provide its multi-window reads at the existing unstallable rate; need priced pre-reserved read service or explicit source-matched ready integration.',
                    'ME 96-vector output face has only source me_en write suppression, not a bank completion/visibility fence. Queue actual masks and retain progress/lease visibility until all physical ACKs.',
                    'Masked-r2 macro read is accept+1 and write accept+2. Cross-command physical-edge row hazards need an admission calendar; same-command rw_collision_fault alone is insufficient.',
                    'Collective and reducer require same namespace and visibility arbitration; descriptors do not provide an activation-memory ready port.',
                    'Read replication alone cannot solve multiple rows written to the same bank in one edge; writes need finite coalescing/queue/admission and coherence propagation.',
                    'SS/FF loaded mux, lane-select/broadcast, control, staging, SRAM-state protection and corridor area not measured; body floors are not implementation total.',
                ],records=records,collectives=collectives,stage_read_workload=stagecost)
    # Pure address algebra: reconstruct every retained scalar uniquely.
    for a in range(VM_WORDS):
        p=physical_address(a)
        assert (((p['depth_group']*512+p['row'])*4+p['bank'])*16+p['lane'])==a
    assert all(r['analysis'].get('range_pass',True) for r in records)
    assert all(r['analysis'].get('write_range_pass',True) for r in records)
    assert all(r['decoded']['me_split'] in (7,9,11) for r in me)
    for r in records:
        if r['unit']=='SU':
            a=r['analysis']
            rd=a['read_scalar_range'];wr=a['write_scalar_range']
            a['possible_same_word_read_write_overlap']=bool(rd and wr and rd[0]//16 <= wr[1]//16 and wr[0]//16 <= rd[1]//16)
            a['overlap_requires_actual_retirement_calendar']=a['possible_same_word_read_write_overlap']
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--position',type=int,default=8191);p.add_argument('--token',type=int,default=24)
    args=p.parse_args();result=build_proposal(args.root,args.position,args.token)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(verdict=result['verdict'],peak=result['peak'],stage_read_workload=result['stage_read_workload'])))


if __name__=='__main__':main()
