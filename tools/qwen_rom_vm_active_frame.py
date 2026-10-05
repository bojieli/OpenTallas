#!/usr/bin/env python3
"""ROM-only active-frame engineering candidate; no provider or clock change.

Inputs are captured, source-ordered logical-edge requests, not activations.
Use Arendt's compile_frame for source ABI/order/bounds. The returned plan is
not a grant, an ACK, a runtime schedule, or a cross-edge cache lease.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from hdc_isa import decode
from qwen_rom_finite_vm_schedule import BOOK, PINS, compile_frame, proposal

OUT = Path('results/uarch/qwen_rom_vm_active_frame_20261005')
PROVIDERS = (
    'rtl/hbm_accel/qwen/finite_vm_20261005/ot_qwen_checked_vm_bank.sv',
    'rtl/model_ready_ds_native_vm_r2_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible_r2.sv',
    'rtl/test/hbm_accel/tb_qwen_finite_vm_adapter.sv',
)


def active_frame(reads, writes):
    """Filter disabled seats without sorting enabled writers or dropping aliases.

    Frame identity and request capture belong to the enclosing owner. Each
    invocation is one isolated edge. All physical reads must drain BEFORE any
    masked write, and all postverified writes must drain BEFORE release.
    """
    # Validate also disabled entries: no out-of-range garbage becomes authority.
    for rows in (reads, writes):
        for r in rows:
            if 'enabled' in r and type(r['enabled']) is not bool:
                raise ValueError('enable must be a literal captured boolean')
    # Original source ignores inactive address/data pins. Validate inactive
    # seat order with an in-range don't-care, never grant or emit that seat.
    compile_frame([dict(x, address=x['address'] if x.get('enabled', True) else 0) for x in reads],
                  [dict(x, address=x['address'] if x.get('enabled', True) else 0) for x in writes])
    r = [dict(x) for x in reads if x.get('enabled', True)]
    w = [dict(x) for x in writes if x.get('enabled', True)]
    inherited = compile_frame(r, w)
    # Keep every original ordinal, including multiple stores to the same lane.
    ordinals = {(x['source'], x['seat']): i for i, x in enumerate(writes)}
    emitted = [dict(x, original_ordinal=ordinals[(x['source'], x['seat'])]) for x in w]
    # Native source has 48 ME vector enables, one MX, 64 scalar SU,
    # one reducer and one collective. Keep each source group separate even
    # when the next family aliases its word: final-writer priority unchanged.
    groups = []
    for x in emitted:
        key = (x['source'], x['seat']//16 if x['source']=='ME' else
               x['seat'] if x['source']=='SU' else 0)
        word = x['address']//16
        if not groups or groups[-1]['source_group'] != list(key) or groups[-1]['word'] != word:
            groups.append(dict(source_group=list(key), word=word, mask=0, original_ordinals=[]))
        groups[-1]['mask'] |= 1 << (x['address']%16)
        groups[-1]['original_ordinals'].append(x['original_ordinal'])
    native_groups_legal = len({tuple(g['source_group']) for g in groups}) == len(groups) and len(groups)<=115
    return dict(reads=r, writes=emitted, inherited=inherited,
        native_writer_groups=groups, native_writer_group_count=len(groups),
        native_group_selector_candidate_legal=native_groups_legal,
        phase_active_writer_seats=len(w), input_writer_seats=len(writes),
        source_order_unchanged=True, read_before_all_writes=True,
        read_windows=inherited['read_windows'], cross_edge_reuse=False)


def reference_edge(memory, reads, writes):
    """Opaque label semantics only: original old reads and ordered NBA writes."""
    old = {(x['source'], x['seat']): memory[x['address']]
           for x in reads if x.get('enabled', True)}
    after = dict(memory)
    emitted = []
    for x in writes:
        if x.get('enabled', True):
            value = x.get('label', ('write', x['source'], x['seat']))
            emitted.append((x['source'], x['seat'], x['address'], value))
            after[x['address']] = value
    return old, after, emitted


def compare_edge(memory, reads, writes):
    plan = active_frame(reads, writes)
    expected, end, emitted = reference_edge(memory, reads, writes)
    # One fresh old-memory response per aligned window in this edge only.
    got = {}
    for window in plan['read_windows']:
        for dst in window['destinations']:
            returned_address = window['base_word']*16 + dst['return_scalar_lane']
            if not 0 <= dst['return_scalar_lane'] < 64:
                raise AssertionError('invalid aligned-window lane')
            got[(dst['source'], dst['seat'])] = memory[returned_address]
    actual_after = dict(memory)
    actual_emitted = []
    for x in plan['writes']:
        value = x.get('label', ('write', x['source'], x['seat']))
        actual_emitted.append((x['source'], x['seat'], x['address'], value))
        actual_after[x['address']] = value
    # Execute actual masked group payload: last source-ordered store to a lane
    # overwrites its earlier payload, as the existing packer does.
    grouped_after = dict(memory)
    by_ordinal = {x['original_ordinal']: x for x in plan['writes']}
    for group in plan['native_writer_groups']:
        payload = {}
        for ordinal in group['original_ordinals']:
            x = by_ordinal[ordinal]
            physical_address = group['word']*16 + x['address']%16
            payload[physical_address] = x.get('label', ('write', x['source'], x['seat']))
        grouped_after.update(payload)
    if grouped_after != end:
        raise AssertionError('native masked group merge changed lane winner')
    if (expected, end, emitted) != (got, actual_after, actual_emitted):
        raise AssertionError('old read, ordered write, or edge result mismatch')
    return actual_after, dict(old_reads=len(got), emitted_writes=len(emitted),
        aligned_read_responses=len(plan['read_windows']), exact_logical_edge=True)


def source_case(inp, name, pc):
    """Literal static k0/j0/round0 addresses; never infer later native phases."""
    program = (inp / name).read_text().splitlines()
    d = decode(int(program[pc], 16))
    if d['unit'] != 1 or d['me_d_xbase'] or d['me_d_obase'] or d['me_d_nout']:
        raise ValueError('dynamic source tuple requires actual owner-resolved frame')
    split = 1 << d['me_split']
    reads = [dict(source='VX', seat=i,
        address=d['me_xbase']+(i & (split-1))*d['me_xcs'])
        for i in range(2048) if (i >> d['me_split']) < (6144 >> d['me_split'])]
    writes = []
    if d['me_oen']:
        for q in range(min(48, 6144 >> d['me_split'])):
            for lane in range(16):
                if q*(16 if d['me_mmode'] else 128)+lane < d['me_nout']:
                    writes.append(dict(source='ME', seat=q*16+lane,
                        address=(d['me_obase']+q*d['me_ots'])*16+lane))
    return reads, writes


def price(plan):
    """Explicit ESTIMATE, serial CAP1 11/30 accounting retained, no free ports.

    General active-selector option: 10 registered binary selection levels for
    115 native source groups, one active group per 7 service edges, no II1 claim.
    Broadcast option: source-phase static alias map, validate captured addresses
    and all enable bits before service; mismatch falls back BEFORE requests.
    Distinct scalar lane muxes use six registered 2:1 levels, then one registered
    matched destination capture. Reads stay on CAP1, dispatch drains before the
    next checked command, no overlapping credit/release assumed.
    """
    b = plan['inherited']
    if not plan['native_group_selector_candidate_legal']:
        raise ValueError('source group shape unsupported: retain original walker')
    n = b['read_seats']; w = b['write_seats']; u = b['unique_aligned_read_windows']
    distinct = b['distinct_read_scalars']
    depth = math.ceil(math.log2(115))
    encoder_edges = depth*(plan['native_writer_group_count']+1)  # includes empty/done proof; zero writes can skip
    if not w:
        encoder_edges = 0
    validation = 2*n + 2  # address/bounds pipeline ESTIMATE, includes flush
    dispatch_per_window = 6+1  # 64 scalar lanes in actual aligned2048b response
    base = b['conservative_current_adapter_edges']
    compact_only = base - 865 + encoder_edges
    broadcast = (4 + validation + (11+dispatch_per_window)*u +
                 encoder_edges + 30*b['physical_write_batches'])
    # No global packed-frame crossbar. Original encoded frame stays intact.
    # Hierarchical priority/minimum-seat tree selects next original ordinal.
    selector_mux_bits = (115-1)*(512+24+16+7)
    writer_pipeline_bits = selector_mux_bits
    active_bitmap_bits = 115
    # Distinct address node shared only among SAME-edge equal scalar readers.
    read_mux_bits = distinct*63*32
    read_pipeline_bits = read_mux_bits + distinct*32
    # Source phase map entries carry scalar24, representative12, original12.
    phase_table_bits = n*48
    validation_bits = n*(24+1)*2
    raw = (writer_pipeline_bits+active_bitmap_bits+read_pipeline_bits+
           phase_table_bits+validation_bits+2048+15+227+256)
    pairs = math.ceil(raw/64)
    coded = pairs*72
    codec_body = pairs*288.50904  # unchanged SRAM/control protection proxy
    mux_body = (selector_mux_bits+read_mux_bits)*.2
    compare_body = n*24*.2
    ff_body = coded*.2916
    incremental = codec_body+mux_body+compare_body+ff_body
    writer_raw = writer_pipeline_bits+active_bitmap_bits+2048+15+227+256
    writer_pairs = math.ceil(writer_raw/64)
    writer_coded = writer_pairs*72
    writer_body = writer_pairs*288.50904+writer_coded*.2916+selector_mux_bits*.2
    return dict(status='MODEL_CANDIDATE_NOT_MEASURED',
        baseline_source_walker_edges=base,
        active_writer_selector_depth=depth, actual_active_native_writer_groups=plan['native_writer_group_count'], active_writer_selector_edges_ESTIMATE=encoder_edges,
        active_write_only_edges_ESTIMATE=compact_only,
        active_write_only_saved_edges_ESTIMATE=base-compact_only,
        active_write_only_incremental_50pct_mm2_ESTIMATE=2*writer_body/1e6,
        empty_writer_skip_requires_registered_coded_bitmap_proof=True,
        address_validation_edges_ESTIMATE=validation,
        checked_read_service_and_broadcast_edges_ESTIMATE=(11+dispatch_per_window)*u,
        checked_write_and_flush_edges=30*b['physical_write_batches'],
        compact_plus_broadcast_edges_ESTIMATE=broadcast,
        saved_edges_ESTIMATE=base-broadcast,
        service_reduction_fraction_ESTIMATE=1-broadcast/base,
        prefer_broadcast_by_service_edges=broadcast<compact_only,
        read_aligned_response_bits=2048, max_duplicate_scalar_fanout=b['maximum_same_scalar_reuse'],
        requested_new_memory_ports=0, MACs_per_cycle=0, replicas=1,
        request_bits_per_service_edge=15+227+1,
        broadcast_scalar_wire_bits=n*32, wire_tracks_at_one_per_bit=n*32,
        active_bitmap_raw_bits=active_bitmap_bits, source_phase_table_raw_bits=phase_table_bits,
        address_validation_cut_raw_bits=validation_bits,
        writer_selector_mux_bits=selector_mux_bits, reader_lane_mux_bits=read_mux_bits,
        added_pipeline_and_control_raw_bits=raw, added_coded_bits_ESTIMATE=coded,
        added_codec_pairs_ESTIMATE=pairs, codec_body_um2_ESTIMATE=codec_body,
        FF_body_um2_ESTIMATE=ff_body, mux_body_um2_ESTIMATE=mux_body,
        compare_body_um2_ESTIMATE=compare_body,
        incremental_cell_body_mm2_ESTIMATE=incremental/1e6,
        incremental_50pct_placement_mm2_ESTIMATE=2*incremental/1e6,
        original_224712_encoded_frame_bits_retained=True,
        native_group_mask_merge='ME/MX/collective each preserves original scalar lane order and mask; SU/reducer retain individual scalar order; no cross-source reorder or dropped emitted stores',
        original_frame_storage_savings_claimed=0,
        area_price_basis='conservative full original frame + coded map/cuts/bitmap; .2916 FF/.2 mux or compare-bit/288.50904 codec-pair proxies; not mapped',
        clock_wire_fanout_buffer_and_PG_area=None, slot_fit=False,
        loaded_SS60_FF25_closed=False, physical_admission=False, adopted=False,
        timing_assumptions='2edge address validation/7level native-group writer/6level reader are ESTIMATE stage plans, require Maxwell registration then minimum RTL measured clock/service; not certified1.2GHz',
        current_real_provider_service_edges='11per checked read miss and30per masked flush including9read/28postverified plus controller seats; no overlap',
        required_static_phase_guards='exact enabled bitmap+literal native addresses match source phase; otherwise original walker before any side effect',
        source_rate_or_token_gain=None, firstsegment331us_reprice=None)


def minimal_checks():
    # Literal existing minimumbench addresses and edge sequence, opaque labels.
    mem = {a: ('initial', a) for a in range(4096, 4288)}
    details = []
    for base in (4096,4160,4224):
        writes = [dict(source='ME',seat=i,address=base+i,label=('fixture',base+i)) for i in range(16)]
        mem,c = compare_edge(mem,[],writes);details.append(c)
    reads = [dict(source='VA',seat=i,address=a) for i,a in enumerate((4096,4160,4224))]
    mem,c = compare_edge(mem,reads,[dict(source='ME',seat=0,address=4096,label=('fixture',4097))]);details.append(c)
    mem,c = compare_edge(mem,[dict(source='VA',seat=i,address=4096+i) for i in range(2)],[]);details.append(c)
    # Same-edge collision across every actual writer family, disabled holes,
    # duplicate aligned reads, next-edge fresh read sees final collective writer.
    writes = [dict(source=s,seat=0,address=4096,label=s) for s in ('ME','MX','SU','REDUCER','COLLECTIVE')]
    writes.insert(1,dict(source='ME',seat=1,address=4096,label='ME-later-same-lane'))
    writes.insert(2,dict(source='ME',seat=2,address=4097,enabled=False))
    reads = [dict(source='VA',seat=i,address=4096+i%2) for i in range(4)]
    mem,c = compare_edge(mem,reads,writes);details.append(c)
    if mem[4096]!='COLLECTIVE':raise AssertionError('last-writer order lost')
    mem,c = compare_edge(mem,reads,[]);details.append(c)
    compare_edge(mem, [], [dict(source='ME',seat=0,address=1<<24,enabled=False)])
    refused = 0
    for r,w in (([],list(reversed(writes))),
                ([dict(source='VX',seat=0,address=177808)],[]),
                ([],[dict(source='ME',seat=0,address=4096,enabled=1)])):
        try:active_frame(r,w)
        except ValueError:refused+=1
        else:raise AssertionError('invalid input accepted')
    return dict(status='PASS_OPAQUE_LOGICAL_EDGE_ONLY',
        existing_source_minimum_edges=5, extra_alias_priority_nextedge_cases=2,
        rejected_invalid_inputs=refused, cases=details,
        numerical_inference=False, native_RTL_or_clock_check=False,
        semantics='source read-old-before-all-writes; exact ordered emitted stores including overwritten aliases; fresh nextedge, no cache')


def report(root):
    root=Path(root); parent=proposal(root) # verify actual59492/PART2 pins
    inp=root/BOOK/'inputs'
    cases={}
    for key,name,pc in (('HEAD_PC3','head_program.hex',3),('L20_W1_PC20','L20_program.hex',20)):
        reads,writes=source_case(inp,name,pc)
        plan=active_frame(reads,writes)
        memory={x['address']:('old',x['address']) for x in reads+writes}
        _,check=compare_edge(memory,reads,writes)
        cases[key]=dict(pc=pc,input_program_sha256=parent['source_sha256'][name],
            source_scope='only first k0/j0/round0 native addresses, not later phases or trace',
            logical_edge_check=check, plan=plan, price=price(plan))
    pins={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in PROVIDERS}
    return dict(schema='opentallas.qwen-rom.vm-active-frame.v1',
        default_enabled=False, RTL_added=False, provider_or_schedule_edited=False,
        source_pins=parent['source_sha256'], provider_source_pins=pins,
        minimal_case=minimal_checks(), cases=cases,
        service_replica_OPTION=dict(status='MODEL_ONLY_REQUIRES_OWNER_APPROVAL',
            existing_data_macros=256,existing_check_macros=32,new_macro_ports=0,
            actual_controller='ot_qwen_checked_vm_bank one CAP1 state/bank/word_addr/tag, single_write rejects multibank writes; rd_accept refuses concurrent write',
            actual_data_ports='g_bank[b].g_group[g].g_live.g_col[c].u_sram: four512x128 1R1W macros/bank/group; rd_group_cmd/rd_row shared per bank across16groups',
            actual_check_ports='g_check[g].g_pair[p].u_check: one512x128 check macro per bank pair pergroup, two banks share read/write address',
            option='pergroup protected service partition over existing macros, NOT four unrestricted banks; within a group bank-pair sidecar serializes conflicting rows',
            existing_group_count=16, proposed_group_controller_replicas=16,
            incremental_controller_replicas=15, macro_copies=0,
            minimum_per_replica_captured_data_check_owner_bits=2048+256+512+512+227+15+16+64+32,
            existing9read28write_service_cannot_be_transferred=True,
            minimum_added_controller_raw_bits=15*3682,
            minimum_added_controller_coded_bits=math.ceil(15*3682/64)*72,
            minimum_added_controller_FF_body_um2_ESTIMATE=math.ceil(15*3682/64)*72*.2916,
            minimum_added_controller_codec_pairs_ESTIMATE=math.ceil(15*3682/64),
            minimum_added_data_codec_pairs_ESTIMATE=15*(32+8),
            minimum_added_data_codec_body_um2_ESTIMATE=15*(32+8)*288.50904,
            W1_parallel_write_gain_candidate=False,
            W1_reason='all48 writes use same group2 bank3, partition cannot add a port to these same macros/sidecar',

            needs='price decode/encoder replication, demux/read holding/arbiter, coded owner/debt/ACK, clocks/macroloads/slot. Owner approves selected partition before any RTL.',
            W1_bank3_all48_writes=True,
            W1_write_group_histogram=dict(__import__('collections').Counter(str(x['group']) for x in cases['L20_W1_PC20']['plan']['inherited']['ordered_masked_write_batches'])),
            projected_gain=None, area=None, physical_admission=False),
        next='Maxwell unified registration/candidate choice then Boole smallest mechanism RTL/service measurement with Arendt hook and Goodall actual clock, no wholearray; owner approval needed for replica option')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=report(args.root)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'model.json').write_text(json.dumps(result,indent=2)+'\n')
    summary={k:v['price'] for k,v in result['cases'].items()}
    summary['minimal_case']=result['minimal_case']
    summary['source_pins']=result['source_pins']
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:{f:v[f] for f in ('baseline_source_walker_edges','compact_plus_broadcast_edges_ESTIMATE','saved_edges_ESTIMATE','incremental_50pct_placement_mm2_ESTIMATE')} for k,v in summary.items() if k in result['cases']},indent=2))
