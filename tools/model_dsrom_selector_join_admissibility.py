"""One fixed selector/station ledger and read-only backend/context review.

No HDL frontend, simulation, synthesis or physical job. Official cell and
backend sources remain unchanged; this tool emits analytical evidence only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import uarch_topk_buffered_station_source_model as M

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/dsrom_selector_join_admissibility_20261002'
PATHS = {
    'core': 'results/rtl/dsrom_balanced_selector_candidate_prepare_20261002/implementation_model.json',
    'cuts': 'results/rtl/dsrom_selector_allowed_cut_prepare_20261002/model.json',
    'allowed': 'results/uarch/dsrom_selector_allowed_terminal_model_20261002/model.json',
    'station': 'results/uarch/topk_buffered_station_source_model_20261002/model_r2.json',
    'track': 'results/uarch/topk_finite_track_turn_model_20261002/model_r2.json',
    'seq': 'results/rtl/dsrom_selector_allowed_cut_prepare_20261002/inputs/asap7sc7p5t_SEQ_RVT_TT_220101.v',
    'tool': 'results/rtl/dsrom_balanced_selector_candidate_prepare_20261002/compile_proposal.json',
    'literal': 'tools/rtl_templates/ot_topk_allowed_cut_packet_prepare.sv',
    'caller': 'results/rtl/dsrom_selector_allowed_cut_prepare_20261002/package_r2/candidate/ot_w15_coll_dma_balanced_allowed_cut_prepare.sv',
}


def sha(data): return hashlib.sha256(data).hexdigest()


def rows(source, primitive):
    body = re.search(r'primitive '+primitive+r'\s*\(.*?endprimitive', source, re.S)[0]
    table = re.search(r'\btable\b(.*?)endtable', body, re.S)[1]
    table = re.sub(r'//[^\n]*', '', table)
    result = []
    for row in table.split(';'):
        if not row.strip(): continue
        ins, current, out = row.split(':')
        result.append((re.findall(r'\([^)]*\)|[^\s]+', ins), current.strip(), out.strip()))
    return result


def matches(token, old, new):
    if token.startswith('('):
        a, b = token[1:-1]
        return old != new and matches(a, old, old) and matches(b, new, new)
    if token == '*': return old != new
    if token in ('?', 'b'): return True
    return token == str(new)


def udp_step(table, old, new, q):
    # Exact known-binary rows only; no X/notifier/timing-violation credit.
    results = set()
    for ins, current, out in table:
        if len(ins) != len(new): raise ValueError('UDP input count changed')
        if matches(current, q, q) and all(matches(t, a, b) for t, a, b in zip(ins, old, new)):
            if out == '-': results.add(q)
            elif out in ('0', '1'): results.add(int(out))
            else: raise ValueError('unknown output in known-binary contract')
    if not results: return q
    if len(results) != 1: raise ValueError('conflicting UDP binary rows')
    return results.pop()


def primitive_review(seq, width_source, udp_source, language):
    # 5.050 has an explicit exception to its general "timing checks ignored"
    # documentation: delayed reference/data outputs become assignments.
    for anchor in ['visit(AstSetuphold*', 'nodep->refevp(), nodep->delrefp()',
                   'nodep->dataevp(), nodep->deldatap()', 'new AstAssignW']:
        if anchor not in width_source: raise ValueError('delayed-output support absent')
    for anchor in ['visit(AstUdpTable*', 'visit(AstUdpTableLine*', 'valName == "01"', 'valName == "10"']:
        if anchor not in udp_source: raise ValueError('UDP backend support absent')
    if 'primitive (UDP) tables are\nsupported.' not in language: raise ValueError('version UDP documentation changed')
    count = 0
    for name, asr in [('altos_dff', False), ('altos_dff_sr_0', True)]:
        table = rows(seq, name)
        for clk0 in (0, 1):
            for clk1 in (0, 1):
                for d0 in (0, 1):
                    for d1 in (0, 1):
                        for rst0 in ((0, 1) if asr else (1,)):
                            for rst1 in ((0, 1) if asr else (1,)):
                                for q in (0, 1):
                                    # Source read-only truth review isolates input events.
                                    # Multiple inputs changing in one delta is a separate
                                    # backend event-order contract, not silently qualified.
                                    if sum((clk0 != clk1, d0 != d1, rst0 != rst1)) > 1: continue
                                    old = [0, clk0, 1-d0] + ([1-rst0, 0] if asr else []) + [0]
                                    new = [0, clk1, 1-d1] + ([1-rst1, 0] if asr else []) + [0]
                                    expected = 1 if not rst1 else 1-d1 if clk0 == 0 and clk1 == 1 else q
                                    # Reset has already forced state when both old/new reset active.
                                    if asr and not rst0 and q != 1: continue
                                    if udp_step(table, old, new, q) != expected:
                                        raise ValueError('official UDP binary transfer differs from Liberty contract')
                                    count += 1
    for master in ('DFFHQNx1_ASAP7_75t_R', 'DFFASRHQNx1_ASAP7_75t_R'):
        body = re.search(r'module '+master+r'\s*\(.*?endmodule', seq, re.S)[0]
        if 'delayed_CLK, delayed_D' not in body: raise ValueError('official FF delayed pins changed')
    return dict(status='SOURCE_SUPPORTED_KNOWN_BINARY_CONDITIONAL_NOT_EXECUTED',
                official_UDP_binary_transition_cases=count, UDP_tables_supported=True,
                delayed_setuphold_outputs_lowered_to_assignments=True,
                physical_timing_checks_enforced=False, four_state_or_metastability_qualified=False,
                notifier_unchanged_required=True, SETN_one_sink_tie1_required=True,
                isolated_known_binary_events_only=True, simultaneous_input_delta_events_qualified=False,
                official_sources_unmodified=True, behavioral_cell_replacement=False,
                HDL_frontend_executed=False, mappedprimitive_runtime_PASS=False,
                binary_source_build_reproducibility_proven=False,
                remaining='Reviewed functional frontend gate/warning dispositions under fresh GO; no timing-check, X-propagation or SSFF credit')


def build():
    pins = json.loads((BASE/'source_pins.json').read_text())
    for p, h in pins.items():
        if sha((ROOT/p).read_bytes()) != h: raise ValueError('source pin changed: '+p)
    origins = json.loads((BASE/'input_manifest.json').read_text())
    for name, e in origins.items():
        data = (BASE/'inputs'/name).read_bytes()
        if len(data) != e['bytes'] or sha(data) != e['sha256']: raise ValueError('archive pin changed: '+name)
    raw = {k:(ROOT/v).read_text() for k,v in PATHS.items()}
    core, cut, allowed, station, track = [json.loads(raw[k]) for k in ('core','cuts','allowed','station','track')]
    helpers = cut['helpers']
    data = sum(h['WIDTH']*h['EDGES'] for h in helpers)
    present = sum(h['EDGES'] for h in helpers)
    repeated = 2*sum((h['WIDTH']+1)*(h['EDGES']+1) for h in helpers)
    if (data,present,repeated) != (475954,226,965012): raise ValueError('full cut geometry changed')
    if (core['state_bits_model_gross'], core['added_state_bits_vs_original_model']) != (698354,127140): raise ValueError('core state changed')
    # The historical 48007 tree uses ONLY cut FF input loads, not core FFs.
    cells = station['cell_facts']
    def cap(label, port): return max(cells[c][label]['input_cap_fF'][port] for c in ('SS','FF'))
    bcap = cap('BUF','A')
    cutclock = M.clock_tree(data*cap('data_FF','CLK')+present*cap('valid_FF','CLK'),5.76,bcap)
    if cutclock['BUF_cells'] != 48007: raise ValueError('station-only clock floor changed')
    # Conservative core pin ceiling assumes all core bits have the larger CLK
    # pin. A separate finite fanout floor is priced, not physically allocated.
    coreclock = M.clock_tree(core['state_bits_model_gross']*max(cap('data_FF','CLK'),cap('valid_FF','CLK')),5.76,bcap)
    guard = 19*0.08748*2/1e6
    core_debit = core['async_reset_master_debit']['total_additional_reserve_with_ties_mm2_at50pct']
    cut_ties = cut['new_tie_reserve_mm2_at50pct']
    subtotal = core['area']['proposed_source_50pct_proxy_core_mm2']+allowed['cost']['station_reservation_mm2_at50pct']+guard+core_debit+cut_ties
    coreclock_area = coreclock['BUF_cells']*0.10206*2/1e6
    source_instances = ['g_topk.g_station.u_input', 'g_topk.g_station.u_return', 'g_write_station.u_write']
    for name in ('u_input', 'u_return', 'u_write'):
        if not re.search(r'\)\s*'+name+r'\s*\(',raw['caller']): raise ValueError('source cut instance missing')
    backend = primitive_review(raw['seq'],(BASE/'inputs/V3Width.cpp').read_text(),
                               (BASE/'inputs/V3Udp.cpp').read_text(),(BASE/'inputs/languages.rst').read_text())
    box = track['selector_slot_DBU']
    slot = (box[2]-box[0])*(box[3]-box[1])/1e12
    return dict(schema='opentallas.selector.joined-admissibility.v1', candidate='DS4096-TP4-S58-PAR2-NP2048',
        geometry='N4 NMAX2048 LDW4 P64 PF64 DIG8 CB14',
        verdict='REFUSE_INTEGRATED_PHYSICAL_AND_RUNTIME_ADMISSION',
        state=dict(existing_core_model_bits=571214, incremental_core_bits=127140, proposed_core_gross_bits=698354,
                   existing_cut_bits=0, incremental_cut_payload_bits=data, incremental_cut_present_bits=present,
                   proposed_cut_gross_bits=data+present, total_proposed_core_plus_cut_bits=698354+data+present,
                   total_incremental_core_plus_cut_bits=127140+data+present,
                   existing_core_removed_not_recharged=True, no_array_alias_or_optimization_credit=True,
                   baseline_core_async_master_census_pending=True, core_model_gross_not_mapped_netlist_count=True),
        station_cells=cut['instance_ledger'],
        area=dict(unit='mm2; 50pct analytical reservation, not occupied placed area',
                  complete_replacement_core=core['area']['proposed_source_50pct_proxy_core_mm2'],
                  allowed_station_including_station_clock_floor=allowed['cost']['station_reservation_mm2_at50pct'],
                  explicit_control_guards=guard, core35_ASR_plus_ties_debit=core_debit, cut229_ties=cut_ties,
                  combined_existing_priced_subtotal=subtotal,
                  additional_separate_core_clock_fanout_floor=coreclock_area,
                  proposed_finite_cell_reservation_with_core_clock_floor=subtotal+coreclock_area,
                  actual_combined_occupied_area=None, full_clock_reset_PG_pin_access_wire_hold_repair_reservation=None,
                  original_station_and_original_core_replaced_once=True,
                  no_station_core_or_Arch1100_sink_tree_double_credit=True),
        slot=dict(current_selector_bbox_DBU=box, current_selector_slot_mm2=slot,
                  core_plus_ASR_debit_mm2=core['area']['proposed_source_50pct_proxy_core_mm2']+core_debit,
                  core_clock_floor_home=None,
                  deficit_if_all_core_clock_floor_colocated_mm2=max(0,core['area']['proposed_source_50pct_proxy_core_mm2']+core_debit+coreclock_area-slot),
                  clock_floor_may_not_borrow_signal_corridor_without_site_and_track_union=True,
                  whole_reticle_area_delta=None, existing_parent_inclusion_ledger_not_proven=True),
        clock=dict(station_sinks=476180,core_model_sinks=698354,combined_model_sinks=1174534,
                   station_fanout_floor=cutclock, additional_core_fanout_floor=coreclock,
                   conditional_independent_floor_roots=2, actual_parent_root_count=None,
                   named_tree_sites_and_spatial_distribution=None, clock_buffer_floor_sum=cutclock['BUF_cells']+coreclock['BUF_cells'],
                   Arch73_nodes1100_element_sinks_are_separate_no_transfer=True,
                   period_ps=833,setup_uncertainty_ps=60,hold_uncertainty_ps=25, matched_skew_ceiling_ps=25),
        fanout=dict(payload_local_driver_consumers=1, SETN_providers_cut=226, source_present_ties=3,
                    core_incremental_SETN_providers=35, SETN_each_fanout=1,
                    unconstructed_raw_cut_clock_fanout=476180,
                    cut_RESETN_FF_sinks=226, cut_reset_guard_AND_sinks=7, incremental_core_RESETN_FF_sinks=35,
                    baseline_core_RESETN_sinks=None, permitted_AND_fanout_by_helper=[2,5,5],
                    clock_and_reset_native_route_extraction=None),
        station_binding=dict(actual_source_instances=source_instances,old_write_alias='u_write28 is not literal source hierarchy',
                             edge_counts=[99,99,28], helper_widths=[2122,2088,2113],
                             terminal_width_DBU=378, extra_terminal_width_DBU=108,
                             named_legal_disjoint_cell_sites=None, PG_body_OBS_escape_union=None,
                             actual_CLK_RESETN_SETN_pin_access=None,
                             final_sink_has_no_extra_terminal=True, intermediate_hold_screen_not_sink_endpoint_credit=True),
        tracks=dict(external_plus_clock_reset=4212, additional_internal_present_conductors=2,
                    proposed_main_corridor_total=4214, horizontal_capacity=4242,vertical_capacity=4252,
                    horizontal_remaining=28,vertical_remaining=38,
                    formed_write_bits_plus_present=2114, formed_write_capacity=None,
                    PG_clock_branch_via_turn_and_escape_tracks_required=None,
                    actual_remaining_tracks_after_all_physical_obstructions=None, physical_fit=False),
        deadline=dict(service_increment=142, transport_increment=226,per_call_increment=368,nine_call_increment=3312,
                      source_nine_call_comment_envelope=6333,source_consumer_dependency='blocking COLL busy fence -> subsequent SELG/CAND fetch',
                      formed_write_done_packet_same_as_original=True,new_ACK=False,
                      VM_ALWAYS_READY1_source_precondition=True, actual_consumer_ready_credit_receipt=None,
                      accepted_first_input_edge=None,accepted_last_input_edge=None,actual_last_VM_write_edge=None,
                      root_home_visibility_edge=None, actual_consumer_deadline=None,implemented_CDC=None,
                      capture_e899_FAIL_preserved=True,capture_conditional425_1000_not_accepted_trace=True,
                      default1024_timeout_FAIL_preserved=True, timeout4096_not_adopted=True),
        backend=backend, owner_archives=origins,
        owner_actions={'Arch':'Allocate literal378DBU terminals and named CLK/reset/SETN/PG sites; do not transfer element73 clock union to selector.',
                      'Maxwell':'Replace core+station once and price additional core clock floor; bind two shard homes, PG cuts and finite consumer route.',
                      'Nash_Hubble':'Provide accepted input origin, actual VM-ready/lease, last formed write/home visibility and consumer deadline; no offered-only acceptance.'},
        admissions=dict(frontend=False,simulation=False,PR=False,integrated_parent=False,SSFF=False,fulltoken=False),
        live1950286='untouched',new_jobs=[], source_pins=pins)


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists(): raise ValueError('fresh output required')
    a.out.write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
