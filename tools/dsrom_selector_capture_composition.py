#!/usr/bin/env python3
"""Current c9 selector/capture causal program constraints, before any build.
Native acceptedread deadline is never inferred from a wait for another unit,
local cone clock origin, packet ACK or logical equal clock-cell depth.
"""
import argparse,hashlib,json,re
from pathlib import Path
from fractions import Fraction
import dsrom_I66_capture_owner as O
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_selector_capture_composition_20261003'

def wait_proof(core,consumers):
    required=['wire [4:0] idles = {he_idle, xu_idle, qe_idle, su_idle, me_idle}',
        "wire waited = ((d_wait & ~(idles & ~gos)) == 5'd0)",
        'else if (waited && unit_ready && q_gate && kv_gate && m0_gate',
        "(d_unit == 3'd2) ? su_ready",'assign me_idle = &e_idle',
        "wire qe_rom = (X_ROM != 0) && qe_mode == 2'd0",
        'wire rom_q_go = qe_go && qe_rom',
        'assign qe_ready = qe_rom ? rom_ready_w : qe_ready_e',
        'assign qe_idle = qe_idle_e && ((X_ROM == 0) || rom_idle_w)',
        "S_GO: begin pc <= pc + 1'b1; st <= S_FETCH; end"]
    if any(n not in core for n in required):raise ValueError('source consumer admission formula changed')
    proof=[]
    for op in consumers:
        for c in op['consumer']:
            mask=c['wait_mask']
            if type(mask)!=int or not 0<=mask<32:raise ValueError('source wait bits')
            proof.append(dict(producer=op['producer'],consumer=c['consumer_node'],operand=c['operand'],
                wait_mask=mask,explicit_ME_wait=bool(mask&1),explicit_SU_wait=bool(mask&2),explicit_QE_wait=bool(mask&4),
                template_sha256=c['consumer_template_word_sha256']))
    return proof

def lifetime_constraints(proof):
    pairs=[(int(p['producer'].split('I')[-1]),int(p['consumer'].split('I')[-1])) for p in proof]
    if len(pairs)!=12 or len({p for p,c in pairs})!=12:raise ValueError('complete12 source producers')
    live=[];peak=0;witness=None
    # LOWER BOUND: even release at consumer DISPATCH cannot happen sooner.
    # Actual leases last through read/X-tag and can overlap longer.
    for pc in sorted(set(x for pair in pairs for x in pair)):
        live=[p for p in live if dict(pairs)[p]>pc]
        live+=sorted(p for p,c in pairs if p==pc)
        if len(live)>peak:peak=len(live);witness=dict(pc=pc,producers=list(live))
    return dict(dispatch_only_VM_version_lease_lower_bound=peak,witness=witness,
        actual_read_tag_lifetime_maximum=None,dispatch_is_not_read_or_release=True,
        bank_rearm_before_first_shared_consumer_required=[[66,67,70]],
        bank_lease_and_VM_version_lease_must_be_separate=True,
        no_downstream_payload_seat_inferred=True,
        bank_rearm='all sourcecapture/visibility/positive returnedcredit/wire debts fenced; does not release old VMversion',
        VM_version_release='all source-associated consumer reads and observed R+2 Xtags; earlier acceptance/ACK not sufficient')

def idle_hook_floor():
    facts,_=O.T.C.facts();C=O.T.C
    # Gross construction: active and qualified-retirement ASR bits. Existing
    # active containment is NOT presumed; detailed bank/credit logic is extra.
    tie='TIEHIx1_ASAP7_75t_R';lef=json.loads((C.OUT/'inputs/cell_LEF.json').read_text())[tie]
    size=list(map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef).groups()))
    cells={C.ASR:2,tie:2,C.NAND:8,C.INV:6,C.BUF:4}
    body=2*size[0]*size[1]+sum(n*facts[name]['SS']['area_um2'] for name,n in cells.items() if name!=tie)
    return dict(gross_control_bits=2,cell_counts=cells,body_um2=body,reserve50pct_mm2=2*body/1e6,
        phase_active_existing_containment_credit=0,
        control_logic='INV(retire), NAND(active,notretire), NAND(nativeidle,enable), INV(effectiveidle)',
        feedback_per_ASR_twoBUF_lowerbound=True,hold_closed=False,
        SSFF_new_CLK_pin_fF={k:2*facts[C.ASR][k]['pins']['CLK']['cap_fF'] for k in ('SS','FF')},
        SSFF_new_RESETN_pin_fF={k:2*facts[C.ASR][k]['pins']['RESETN']['cap_fF'] for k in ('SS','FF')},
        identity_compare_counters_credit_ledger_CDC_drivers_routes_clock_reset_PG_extra=True,
        not_a_complete_state_area_or_contextual_timing_price=True)

def constructive_fences(proof,nodes,adapter):
    for need in ['assign ready = st == S_IDLE && s_ready','assign idle = st == S_IDLE && s_idle',
                 'S_WAIT: if (!s_go && s_idle) st <= S_IDLE']:
        if need not in adapter:raise ValueError('actual ROM adapter retirement/ready changed')
    index={n['instruction_index']:n for n in nodes}
    fences=[]
    for p in proof:
        prod=int(p['producer'].split('I')[-1]);cons=int(p['consumer'].split('I')[-1])
        pi=index[prod]['instruction']
        if pi['unit']!=3 or pi['qe_mode']!=0:raise ValueError('source producer not GU0')
        later=[pc for pc,n in index.items() if prod<pc<cons and n['instruction'].get('unit')==3 and n['instruction'].get('qe_mode')==0 and n['instruction'].get('pred',0)==0]
        if not later:raise ValueError('no later unconditional source GU0 fence')
        f=max(later)
        if f!=cons-1:raise ValueError('sixedge successor bound requires adjacent ordinary-engine consumer')
        fences.append(dict(producer=prod,consumer=cons,operand=p['operand'],later_GU0=f,
            later_template_sha256=index[f]['template_word_sha256'],
            effective_adapter_idle_sample='F: phase retired visible+capturedcredits before this sample',
            later_GU0_acceptance_min_edge='F+1',consumer_front_acceptance_min_edge='F+7',
            VMvisibility_required='V < F, therefore V < earliest consumer/read',
            conditional_fence_proof_only=True))
    return dict(fences=fences,all12_have_later_GU0=True,
        one_selected_completion_hook='DEFAULT-OFF adapter s_idle input = native_spine_idle && (!phase_active || qualified_visibility_credit_packet_retired)',
        hook_keeps_adapter_S_WAIT_until_publication_retirement=True,
        phase_active_and_retirement_must_match_full169context=True,
        start_with_no_active_debt_permitted=True,
        native_spine_s_ready_not_a_qualified_retirement_fence=True,
        hook_allowedcell_floor=idle_hook_floor(),
        gross_state_and_gate_obligations=dict(retirement_qualified_register_bits=1,
            phase_active_reference_bit=1,active_bit_existing_containment_unproven=True,
            NOT_OR_AND_control_cone='!phase_active OR retire; AND native_idle; fanout to adapter idle +WAIT condition',
            full169comparison_counter_source_credit_CDC_and_faultlogic_not_inside_onebit=True,
            contextual_clock_reset_PG_SSFF_area=None),
        new_SU_per_read_backpressure=False,new_SU_admission_guard_not_selected=True,
        bank_rearm_after_publication_and_source_debt_not_after_SUconsumption=True,
        destination_address_version_lease_stays_until_SUread_tag_fence=True,
        clock='native_core_clk source transition proof only; selectedc9 clock timing/CDC phase not transferred',
        accepted_origin_actual_runtime_word_and_service_enrollment_required=True,
        finite_relative_visibility_deadline_native_edges='strictly before F; first consumer admission/read no earlier than F+7',
        absolute_consumer_first_and_last_time_bound=None,
        ready_hook_is_new_implementation_not_native_guarantee=True,build_admitted=False)

def finite_deadline(events,clock):
    """Exact source-owned per-row deadline, only from enrolled accepted events.
    No ready waveform, delay fit or native->physical clock conversion implied.
    """
    required=('domain','origin_id','period_ps','reset_qualified','accepted_provider_enrolled')
    if any(k not in clock for k in required) or not clock['reset_qualified'] or not clock['accepted_provider_enrolled']:
        raise ValueError('actual accepted clock/origin/reset/provider required')
    period=Fraction(clock['period_ps'])
    if period<=0:raise ValueError('positive clock period')
    if len(events)!=576 or {e['row'] for e in events}!=set(range(576)):raise ValueError('complete actual576 rows')
    slacks=[];credit_times=[];reservations=[]
    for e in events:
        if e['domain']!=clock['domain'] or e['origin_id']!=clock['origin_id']:raise ValueError('no mixed clock origin')
        if e['identity']!=e['consumer_identity'] or e['full_writer_coverage'] is not True or e['native_other_ROM_excluded'] is not True:
            raise ValueError('actual version/phase-wide writer owner exclusion')
        issue=Fraction(e['read_accept_ps']);visible=Fraction(e['VM_visible_ps']);read=Fraction(e['SU_read_ps']);tag=Fraction(e['observed_Xtag_ps']);credit=Fraction(e['captured_credit_ps'])
        if not issue<visible<read or tag!=read+2*period:raise ValueError('actual visibility/consumer/R+2 source edges')
        if not visible<credit or Fraction(e['positive_CDC_return_ps'])<=0 or credit<visible+Fraction(e['positive_CDC_return_ps']):
            raise ValueError('visibility plus positive captured credit')
        slacks.append(read-visible);credit_times.append(credit);reservations.append((issue,credit))
    # Captured credit at T cannot fund the read accepted at T (post-edge).
    peak=max(sum(a<=t<=b for a,b in reservations) for t in {a for a,b in reservations})
    return dict(rows=576,minimum_actual_visibility_to_read_slack_ps=str(min(slacks)),
        actual_consumer_first_ps=str(min(Fraction(e['SU_read_ps']) for e in events)),
        actual_consumer_last_ps=str(max(Fraction(e['SU_read_ps']) for e in events)),
        minimum_source_read_credit_capacity_for_supplied_acceptances=peak,
        physical_credit_station_admission=False)

def model():
    origins=json.loads((OUT/'inputs/origins.json').read_text())
    for n,p in origins.items():
        if hashlib.sha256((OUT/'inputs'/n).read_bytes()).hexdigest()!=p['sha256']:raise ValueError('source input changed')
    c=json.loads((OUT/'inputs/selected_clock.json').read_text());s=json.loads((OUT/'inputs/consumer_source.json').read_text())
    p=wait_proof((OUT/'inputs/core.sv').read_text(),s['accepted_consumer_endpoints']['static_consumers'])
    return dict(verdict='SOURCE_CAUSAL_COMPOSITION_DEADLINE_NOT_YET_ENROLLED',selected_clock_commit=origins['selected_clock.json']['commit'],
        clock_bank=c['selected_selector_clock_construction'],clock_raw_correction_BUF=c['positive_new_relay_and_pad_BUF'],
        clock_cost_already_inside_selected_screen_mm2=c['whole_selector_replacement_screen_mm2'],
        clock_logical_depths=[x['equalized_logical_cell_depth'] for x in c['per_shard_raw_clock_correction_proposals']],
        equal_clock_cell_depth_not_actual_phase_skew_or_CDC=True,clock_parent_phase_reset_union=c['parent_clock_phase_reset_release_control_sink_union'],
        admission_proof=p,lifetimes=lifetime_constraints(p),
        constructive_deadline=constructive_fences(p,json.loads((OUT/'inputs/instruction_slice.json').read_text()),(OUT/'inputs/rom_adapt.sv').read_text()),
        holding_ROM_idle_does_not_prove_all_consumer_admission_fenced=not all(x['explicit_QE_wait'] for x in p),
        GU0_source_unit='QE LINQ through rom_q_go, qe_ready/idle; consumer wait2 names SU not QE4 or ME1',
        conditional_ordinary_engine_dispatch_edges_per_instruction=6,
        I66_to_I70_earliest_acceptance_lower_bound_if_all_intermediate_ordinary_engine_dispatch=24,
        dispatch_lower_bound_is_not_VM_read_deadline_or_service_upper_bound=True,
        not_a_proof_of_current_native_early_read_or_deadlock=True,
        new_guard_if_required='first qualify the selected adapter-idle publication-retirement hook and all12 laterGU0 fences; no additional SU guard selected',
        required_native_ROM_exclusion='intercept all128 native ROM writer inputs during capture phase, not only slot0; source version lease persists through actual SUreads and Xtags',
        c9_historical_exclusive_VM512_policy_not_inherited_for_native_scalar_candidate=True,
        source_credit='actual VMvisibility then positive capturedCDCreturn; source reusable strictly lateredge',
        context='169bit fulluser32; 144header/237command proposal; PC14/Xversion32 need qualified full-context association',
        native_read_Xtag_latency_edges=2,native_single_clk_not_split_domain_qualification=True,
        actual_enrolled_row_events=None,actual_consumer_deadline=None,minimum_C=None,register_stations=None,
        physical_setup_hold_clock_reset_PG_and_typed_forward_provider_closed=False,
        build_admitted=False,new_jobs=False,old_e899_and_1024FAIL_preserved=True,
        next_required_input='current PHW10 accepted vector/read ownership+complete native writer/publication trace or source-derived finite accepted edge calendar, with actual qualified clock/reset origin and positive request/reply/visible/credit service')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);a.add_argument('--verify',action='store_true');args=a.parse_args()
    m=model();paths=[Path(__file__)]+sorted((OUT/'inputs').iterdir());m['source_pins']={**O.pins(),**{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}}
    raw=(json.dumps(m,indent=2,sort_keys=True)+'\n').encode()
    if args.verify:
        if args.out.read_bytes()!=raw:raise SystemExit('FAIL source composition replay')
        print('PASS exact composition; actual consumer deadline unbound/buildfalse')
    else:args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_bytes(raw)
