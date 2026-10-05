#!/usr/bin/env python3
"""Selected W12 common-advance pre-RTL sizing; no token or physical admission."""
import hashlib
import json
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = Path("results/rtl/qwen_plain_ar_stream4_P8191_20261005/clock_join")


def beat_calendar(n, kc, *, publish_edges=0):
    """3:4 old-peer event calendar, retained148-fast/38-serial pipelines.

    Existing pipeline records are owned seats, NOT four imaginary FIFO seats.
    All arithmetic/feedback/tag registers advance together or hold together.
    Macro responses and FIFO pointer/shadow captures remain unpaused. A due
    result freezes the whole upper pipeline until its CAP1 publication retires.
    Healthy ready operands/consumer only; external stalls extend this calendar.
    """
    fast = deque([None]*148); slow = deque([None]*38)
    fifo = deque(); wp = rp = seen_rp = seen_wp = 0
    old_wp = old_rp = 0
    issue = []; retired = {}; published = {}; next_issue = 0
    slow_until = 0; pending = None; release_tick = -1; tick = 0; paused_fast = paused_slow = 0
    while len(published) < n:
        if pending is not None and tick >= slow_until:
            published[pending] = tick
            pending = None
            release_tick = tick # no CAP1 release/reuse on same edge
        we, re = tick % 3 == 0, tick % 4 == 0
        # Pointer samplers use prior-edge state, including coincident edges.
        if we:
            head = fast[0]
            advance = head is None or wp-seen_rp < 4
            if advance:
                head = fast.popleft()
                if head is not None:
                    fifo.append(head); wp += 1
                if next_issue < n:
                    fast.append(next_issue); issue.append(tick); next_issue += 1
                else:
                    fast.append(None)
            else:
                paused_fast += 1
            seen_rp = old_rp
        if re:
            if pending is None and tick > release_tick:
                output = slow.popleft()
                if output is not None:
                    retired[output] = tick
                    last_k = (output // 8) % kc == kc-1
                    if last_k and publish_edges:
                        pending = output; slow_until = tick + publish_edges*4
                    else:
                        published[output] = tick
                incoming = fifo.popleft() if seen_wp > rp else None
                if incoming is not None:
                    rp += 1
                slow.append(incoming)
            else:
                paused_slow += 1
            seen_wp = old_wp
        old_wp, old_rp = wp, rp
        tick = min((tick//3+1)*3, (tick//4+1)*4)
    return dict(issue_ticks=issue, upper_output_ticks=[retired[i] for i in range(n)],
                publication_ticks=[published[i] for i in range(n)],
                fast_pause_edges=paused_fast, serial_pause_edges=paused_slow,
                last_publication_ns=published[n-1]*5/18,
                scope="prospective healthy finite-control calendar, not observed edges")


def model(root=ROOT):
    import hdc_isa as I
    import hdc_timing as T
    import hdc_qwen_fullshape_isa_w12 as Q
    import qwen_rom_finite_vm_schedule as V
    root=Path(root)
    inp=json.loads((root/BOOK/'program_inputs.json').read_text())
    raw=json.loads((root/BOOK/'minimum_programs.json').read_text())
    cut=json.loads((root/'results/uarch/qwen_w12_lvl7_clock_cut_20261005/prebuild_model.json').read_text())
    assert cut['issue']['issue_to_cut_logical_fast_edges']==148
    census=Counter(); per_stage=[]
    for st in inp['stages']:
        for rank in st['ranks']:
            assert rank['rank'] in range(4)
            row=dict(stage=st['stage'],rank=rank['rank'],program_sha256=rank['sha256'],
                     PCs=len(rank['ops']),ME_beats=0,SU_vectors=0,ME_ops=0,SU_ops=0)
            for op in rank['ops']:
                if 'me_rounds_k' in op:
                    rr,k=op['me_rounds_k'];row['ME_beats']+=rr*k*8;row['ME_ops']+=1
                if 'su_vectors' in op:
                    row['SU_vectors']+=op['su_vectors'];row['SU_ops']+=1
                for name in ('barrier','wait_me','wait_su','chase'):
                    census[name]+=bool(op.get(name))
            per_stage.append(row)
    # Separate native service/macro capture from logical pipeline advancement.
    # Two already-accepted responses: MEM_EXTRA capture plus read/capture phase.
    tiles=1536; bits_per_response=512+2048+128+167+4
    capture_ff=tiles*2*bits_per_response
    flags=148*3 + 38*3 + tiles*16 + 256
    gates=tiles+2 # new service/logical separation; reuse existing1536 tileICGs
    scale_capture_ff=2*(12288+48*24+167+4)
    capture_ff+=scale_capture_ff
    # fanout8 finite trees, estimate existing-policy cells. Not CTS/wire closure.
    buffers=(gates-1+6)//7 + (capture_ff+flags+cut['crossing']['total_ff']-1+6)//7
    nand=6*capture_ff + 12*flags + 3*24745*3
    ff=capture_ff+flags+cut['crossing']['total_ff']
    body=ff*.2916+nand*.08748+buffers*.10206+gates*.5
    import qwen_stream4_inline_landing as L
    inline=L.model(root)
    # Existing Arendt CAP1 frame already prices865 write records: no second
    # output payload landing. Due output holds all serial regs until true ACK.
    vm=V.proposal(root)
    pub=4+865+30*48+2 # full source48-word-vector collision bound + captured ACK
    stage_cases=[]
    for name in ('L0','L1'):
        decoded=[Q.decode_instruction(int(w,16)) for w in raw[name]['program'].split()]
        exported=next(s for s in inp['stages'] if s['stage']==name)['ranks'][0]['ops']
        for use_provider in (False,True):
            for mixed in (False,True):
                time=9; me_idle=su_idle=me_free=su_free=0; last_me=[];last_su=None
                events=[];previous=None;su_class=None;su_class_idle=0
                for pc,(f,work) in enumerate(zip(decoded,exported)):
                    if f['unit']==I.UNIT_END:
                        events.append(dict(pc=pc,kind='END',tick=max(time,me_idle+12,su_idle+4),
                                           binding='max sequencer, ME publication, SU drain'))
                        break
                    candidates=[(time,'sequencer')]
                    if f['barrier'] or f['wait_me']:candidates.append((me_idle+12,'ME publication/drain'))
                    if f['barrier'] or f['wait_su']:candidates.append((su_idle+4,'SU drain'))
                    if f['chase']:
                        if f['unit']==I.UNIT_ME:
                            first,cnt,per=last_su
                            take=min(f['chase_n']*(per if f['chase_rows'] else 1),cnt)
                            candidates.append((first+(take-1)*(4 if mixed else 3)+3,'SU producer chase'))
                        else:
                            candidates.append((last_me[min(f['chase_n'],len(last_me))-1]+3,'ME visible chase'))
                    period=4 if mixed else 3
                    if f['unit']==I.UNIT_ME:
                        candidates.append((me_free,'ME accepted issue capacity'))
                    else:
                        candidates.append((su_free,'SU accepted issue capacity'))
                        if su_class is not None and su_class!=f['sfu']:
                            candidates.append((su_class_idle,'SU class drain'))
                    go,bind=max(candidates)
                    go=((go+2)//3)*3
                    if f['unit']==I.UNIT_ME:
                        rr,k=work['me_rounds_k'];n=rr*k*8
                        if mixed:
                            c=beat_calendar(n,k,publish_edges=pub if use_provider else 0)
                            ticks=c['publication_ticks']; issue=c['issue_ticks']
                        else:
                            # Same retained pipeline and finite publication vehicle;
                            # commonclock reference, not193955-cycle recalibration.
                            c=beat_calendar(n,k,publish_edges=pub if use_provider else 0)
                            # Matched reference is conservatively simulated with
                            # serial wait converted separately, so do not use it
                            # as a gain denominator. Source no-stall reference below.
                            ticks=[(i+148+38)*3 for i in range(n)]
                            issue=[i*3 for i in range(n)]
                            if use_provider:
                                extra=0
                                for i in range(n):
                                    if (i//8)%k==k-1:extra+=pub*3
                                    ticks[i]+=extra
                                    issue[i]+=extra
                        last_me=[go+3+ticks[r*k*8+(k-1)*8+j] for r in range(rr) for j in range(8)]
                        me_idle=last_me[-1];me_free=go+3+issue[-1]+3
                        events.append(dict(pc=pc,kind='ME',accepted_issue=go,binding=bind,
                            beats=n,outputs=len(last_me),last_visible_tick=me_idle,
                            publication_edges_per_due_output=pub if use_provider else 0))
                    else:
                        n=work['su_vectors'];depth=T.K['su_depth'][f['sfu']]
                        e0=go+T.K['su_start']*period
                        first=e0+depth*period;last=first+(n-1)*period
                        tail=T.red_tail(T.K,64)*period if f['red'] else 0
                        su_idle=last+tail;su_free=e0+n*period;su_class_idle=last;su_class=f['sfu']
                        last_su=(first,n,n//max(1,f['su_nout']))
                        events.append(dict(pc=pc,kind='SU',accepted_issue=go,binding=bind,
                                           vectors=n,last_write_tick=last,drain_tick=su_idle))
                    time=go+3
                stage_cases.append(dict(stage=name,split=mixed,finite_publication=use_provider,
                    end_ns=events[-1]['tick']*5/18,events=events,
                    scope='first literal attention segment only; modeled healthy grants, no measured delta'))
    paths=[BOOK/'program_inputs.json',BOOK/'minimum_programs.json',
        Path('results/uarch/qwen_w12_lvl7_clock_cut_20261005/source_cut.json'),
        Path('results/uarch/qwen_w12_lvl7_clock_cut_20261005/prebuild_model.json'),
        Path('tools/qwen_rom_finite_vm_schedule.py'),Path('tools/hdc_timing.py'),
        Path('tools/qwen_stream4_inline_landing.py'),Path('tools/two_clock_crossing_model.py'),
        Path('tools/qwen_w12_clock_composition.py')]
    return dict(schema='opentallas.qwen.w12.common_advance_composition.v1',
        selected='retained148-fast-pipeline/common advance, DEPTH4/HOLD2 crossing, held38-serial pipeline, Arendt CAP1 publication',
        model_before_RTL_complete=True,default_enabled=False,functional_RTL_preparation_allowed=True,
        implementation_obligations=['global issue/advance includes all1536 PART1 loops, feedback IL8 and tags',
            'held pipelines own148+38 records; reserve available physical pipeline seat BEFORE issue',
            'separate macro/KV service capture from logical clocks, two accepted response seats/tile',
            'serial pipeline advance holds on due-output CAP1 busy; never pop crossing without accepted serial advance',
            'reserve existing865-seat writer frame before due output; actual postverified publication ACK retires it',
            'fault sticky even paused/nonvalid; reset drains service debt and quarantines both FIFO epochs',
            'clock pause masks repeated memory strobes; no reissued macro/write on held logical edge'],
        budgets=dict(crossing_ff=cut['crossing']['total_ff'],additional_response_capture_ff=capture_ff,
            response_record_bits=bits_per_response,response_seats_per_tile=2,
            separate_scale_response_capture_ff=scale_capture_ff,
            existing_tile_ICGs_reused=1536,hosted_lower_nodes_share_tile_clock=True,
            alignment_credit_reset_fault_control_ff=flags,clock_gates=gates,
            fanout8_buffer_estimate=buffers,nand2_mux_control_estimate=nand,
            ICG_cell_allowance_um2_each=.5,register_body_um2_each=.2916,
            clock_sink_cap_estimate_fF=ff*1.0,
            ICG_enable_cap_estimate_fF=gates*1.0,
            cap_basis='engineering1fF/sink estimate; actual Liberty/loaded wire validation required',
            maximum_branch_fanout=8,
            required_slot_envelope_um=[2000,9000],
            existing_upper_tree_clock_load_relocated_not_new=6*4*24576+96,
            pipeline_ownership_credits=148+4,serial_retained_records=38,
            existing_167bit_canonicaltag_repartitioned_not_duplicated=True,
            total_added_cell_estimate_mm2=body/1e6,
            required_50pct_slot_with_20pct_PG_wire_reserve_mm2=body/1e6*2*1.2,
            parent_slot_reserved=False,routing_tracks_data_lower_bound=24745,
            response_capture_bytes_per_tile=2*bits_per_response/8,
            serial_output_ports=48,serial_output_word_lanes=768,
            existing_VM_frame_reused_not_added_twice=True,
            separate_VM_provider_placement_mm2=vm['priced_component_terms']['preliminary_50pct_placement_mm2'],
            physical_site_and_tracks_fit=False,fanout_and_cell_prices='conservative engineering estimates; no loaded STA'),
        service=dict(fast_GHz=1.2,serial_GHz=.9,issue_to_cut_logical_edges=148,
            upper_tree_edges=24,scale_edges=5,output_edges=2,ORD_edges=7,
            serial_pipeline_edges=38,publication_frame_capacity=1,
            healthy_max_write_batches_per_native_edge=48,publication_caller_edges=pub,
            service_includes='4capture/control +865literal writer walk +30*48 masked flush +2 captured ACK',
            input_reads='existing Arendt2256 reader seats/checked9+miss11; not counted as free accepted grants',
            input_provider_stall_additive=True,
            minimum_checked_operand_window_edges=9,
            extra_readmiss_edges=11,
            scale_macro_request_to_held_capture_fast_edges=2,
            read_grants_before_common_advance_required=True,
            reset_startup_fast_edges=12,reset_startup_serial_edges=12,
            reset_startup_bound_ns=13.333333333333334),
        program_census=dict(programs=len(per_stage),stages=len(inp['stages']),dependencies=dict(census),rows=per_stage),
        minimum_stage_cases=stage_cases,
        inline_landing=inline,
        inline_registration=dict(existing_dense_and_tile_captures_added_FF=0,
            existing_tile_capture_bits=1536*1032,
            per_tile_SRAM_data_ports=2,per_port_bits=256,
            ungated_capture_and_macro_clock_required=True,
            E0_accept_E8_service_E9_tile_E10_write_E11_inflight_clear=True,
            writeback_drain_is_independent=True,
            clock_added_latency_edges=0,
            complete_healthy_token_delta_not_established=True),
        headline_latency_ns=None,headline_rate=None,physical_admitted=False,
        exclusions=['no actual accepted timestamps in program-work export',
            'no fulltoken delta; firstsegment calendar omits actual KV/service contention and collective',
            'HEAD AMAX remains own source-bound retirement, not ordinary write tail',
            'singleclock finite reference is a conservative envelope, not matched measured baseline',
            'real input/read grant delays extend calendars; not asserted zero',
            'reset and ICG loaded setup/hold still require contextual validation'],
        source_sha256={str(p):hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})

if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT/'tools'))
    out=ROOT/BOOK/'composition.json'
    out.write_text(json.dumps(model(),indent=2,sort_keys=True)+'\n')
