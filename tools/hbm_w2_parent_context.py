#!/usr/bin/env python3
"""Prepare the dedicated source-faithful W2 cut; never dispatch physical work."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'physical/hbm_w2_parent_context_20261005'
TOP = 'ot_hbm_w2_protected_parent_context'
SOURCE = 'physical/hbm_w2_parent_context_20261005/' + TOP + '.sv'
SOURCES = [
    'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
    'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv',
    'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_sector_adapter.sv',
    'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_caller.sv',
    'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_cdc.sv',
    'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_gateway_cdc.sv', SOURCE,
    'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w2_result_sink.sv',
    'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w2_sector_adapter.sv',
    'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_sm0_borrow.sv',
    'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_prior_debt.sv',
    'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_cp_reset.sv',
    'rtl/hbm_accel/sm/wavepack_20261005/ot_hbm_accel_w2_result_join.sv',
    'rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv',
    'rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv',
    'rtl/gpu_sys/ot_gpu_mreq_cdc.sv', 'rtl/gpu_sys/ot_gpu_cdc_fifo.sv',
    'rtl/link/ot_link_afifo.sv',
]


def caller_boundary_contract():
    """Resolve the actual D-side replacement hook; never add duplicate stages.

    This is a source integration check, not an SM implementation or a claim
    that internal nets are exported synthesizable ports in the current caller.
    """
    import re
    pq_rel = 'rtl/hbm_accel/sm/pq_production_20261005/ot_hbm_accel_sm_pq.sv'
    caller_rel = 'rtl/hbm_accel/sm/wavepack_20261005/ot_hbm_accel_w2_caller.sv'
    protected_rel = 'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_caller.sv'
    pq, caller, protected = [(ROOT / p).read_text() for p in [pq_rel, caller_rel, protected_rel]]
    required_pq = ['rv_q <= cv[0]', 'rrow_q <= crow[RW-1:0]; rdata_q <= cy',
        'fault_q <= fault_q | (|cf) | pack_bad_head | pack_xa_fault',
        '.d({h_busy, h_arrive, h_released})', '.d({rv_q, fault_q})', '.d({rrow_q, rdata_q})']
    for fragment in required_pq:
        if fragment not in pq: raise ValueError('Actual PQ pre-capture source changed: ' + fragment)
    if '.ctx_valid(start && sm_ready)' not in caller or 'assign start_ready=sm_ready && ctx_ready' not in caller:
        raise ValueError('Actual caller typed identity admission changed')
    for fragment in ['stage[2][270]', 'stage[2][265:258]', 'stage[2][257:2]',
                     'stage[1][268]', 'stage[1][267]', 'stage[1][266]']:
        if fragment not in protected: raise ValueError('Protected caller code layout changed: '+fragment)
    port_head = caller.split(');', 1)[0]
    exported = bool(re.search(r'output\s+(?:wire\s+)?(?:\[[^]]+\]\s+)?producer_cv\b', port_head))
    return dict(schema='opentallas.w2.actual-caller-replacement-hook.v1',
        source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [pq_rel,caller_rel,protected_rel]},
        shape=dict(NC=8,RMAX=256,RW=8,PIO=2,NCTX=11),
        actual_D_side=dict(producer_cv='native_w2.u_sm.g_pq.cv[0]',
            producer_crow='native_w2.u_sm.g_pq.crow[7:0]', producer_cy='native_w2.u_sm.g_pq.cy[255:0]',
            producer_fault='(|native_w2.u_sm.g_pq.cf) | native_w2.u_sm.g_pq.pack_bad_head | native_w2.u_sm.g_pq.pack_xa_fault | native_w2.req_fault',
            producer_busy='native_w2.u_sm.g_pq.h_busy', producer_arrive='native_w2.u_sm.g_pq.h_arrive',
            producer_released='native_w2.u_sm.g_pq.h_released'),
        identity_admission=dict(caller_start='native_w2.start', caller_sm_ready='native_w2.sm_ready',
            caller_pair='native_w2.op_pack_w2',caller_bound='native_w2.op_bound',caller_rows='native_w2.op_rows[8:0]',
            caller_op_a='native_w2.op_id_a',caller_op_b='native_w2.op_id_b',
            caller_ctx_ready_receiver='native_w2.ctx_ready; replaces u_results readiness once'),
        stages_replaced=['PQ rv_q/fault_q/rrow_q/rdata_q', 'PQ u_prv_o/u_prd_o PIO2',
                         'PQ u_pbz PIO2 status', 'caller u_results NCTX11 identity'],
        stage_count=dict(result_capture=3,status_capture=2,added_against_original=0),
        protected_representation=dict(stage_words=5,identity_words=14,word_bits=72,
            backing='u_caller_cut.protected_caller.u_protected.output_stage[0:2].u_state.code and u_identity.code',
            valid='checked stage[2][270]',row='checked stage[2][265:258]',data='checked stage[2][257:2]',
            permission='all W6 banks normal and identity valid; CE holds, UE refuses; no encode-after-old-output protection claim'),
        post_capture_ports_are_not_producer_inputs=['native_w2.rv','native_w2.rop','native_w2.rrow','native_w2.rdata'],
        upstream_raw_ports_exported=exported, whole_caller_connected=exported,
        remaining_source_owner='Claude SM, with Franklin/Gibbs selected live caller integration',
        required_owner_change='Expose this pre-capture source through an explicit port hook and replace the listed old captures/identity once in the ON branch; preserve the OFF caller byte-for-byte. No hierarchical cross-module net reference is a physical port binding.',
        readyless_callback=True,new_owner_ledgers=0,physical_clock_or_load_qualified=False)


def check_caller_binding(bindings):
    """Reject a post-PIO or incomplete caller join before elaboration/mapping."""
    expected=caller_boundary_contract()['actual_D_side']
    if bindings != expected:
        raise ValueError('W2 producer hook must use actual pre-capture source; post-PIO outputs would duplicate capture/identity stages')
    return True


def prepare():
    from uarch_model import hbm_w2_publication_model
    model = hbm_w2_publication_model()
    contract_path = ROOT / 'results/rtl/hbm_child_contract_20261005/child_reservations.json'
    contract = json.loads(contract_path.read_text())
    child = contract['W2']
    pins = [dict(p, group=c['group'], layer=c['layer'])
            for c in contract['channels'] if c['child'] == 'W2'
            for p in c['pin_track_allocation']]
    assert len(pins) == child['external_signal_bits'] == 1213
    assert len({(p['port'], p['bit']) for p in pins}) == 1213
    parent = 'rtl/hbm_accel/integrated_20261005/ot_ds_hbm_cluster20_integrated.sv'
    caller = 'rtl/hbm_accel/sm/pq_production_20261005/ot_hbm_accel_sm_pq.sv'
    h16 = 'results/uarch/hbm_attn_h16_context_20261005/model.json'
    domains = 'results/rtl/hbm_accel_die_floorplan_20261005/domains.sdc'
    parent_text = (ROOT / parent).read_text()
    for fragment in ['.clk(clk_sm),.por_n(rst_sm_n),.owned(peer_grants[1])',
                     '.clk_s(clk_sm), .rst_s_n(rst_sm_n), .clk_m(clk_mem), .rst_m_n(rst_mem_n)']:
        if fragment not in parent_text:
            raise ValueError('Actual W2 parent clock/owner/crossing changed')
    raw_caller = (ROOT / caller).read_text()
    for fragment in ['.W(RW + NC*32), .D(PIO), .RST(0)',
                     '.W(2), .D(PIO), .RST(1)', '.W(3), .D(PIO), .RST(1)']:
        if fragment not in raw_caller:
            raise ValueError('Actual caller output-register topology changed')
    h16_clock = json.loads((ROOT / h16).read_text())['clock_and_IO']
    # These historical clock numbers are evidence about the rejected hardware,
    # never the selected pipeline's or a shared parent's clock/load binding.
    historical = ROOT / 'results/physical/hbm_w2_sink_registered_terminal_20261005/r1/physical_artifacts/metadata.json'
    old = json.loads(historical.read_text())
    record = dict(
        schema='opentallas.w2.dedicated-source-context.v1', top=TOP,
        parameters=dict(ENABLE=0, PROTECTED_TRANSACTION_PIPELINE=0, PROTECTED_PARENT_BOUNDARY=0),
        qualification_parameters=dict(ENABLE=1, PROTECTED_TRANSACTION_PIPELINE=1, PROTECTED_PARENT_BOUNDARY=1),
        hardware_sources=SOURCES,
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                       for p in SOURCES + [parent, caller, h16, domains,
                                          str(contract_path.relative_to(ROOT))]},
        sized_context=model['dedicated_W2_context'],
        additive_parent_protection=model['additive_parent_protection'],
        station_CE_selector_handoff=dict(model['station_CE_selector_successor'],
            owner='Gauss/Turing own station; central and peer station source untouched',
            optin='Thread BALANCED_CE_SELECT=0 through station/native/frame defaults; ON selects ot_hbm_w2_protected_bank_ce_tree and ot_hbm_w2_protected_cut_ce_tree with BALANCED_CE_SELECT=1',
            alternative_static_consumption='Apply only the balanced first-CE selector block to your static-expanded bank ON source; retain current codec equations and all sequential bytes. No codec replay is needed for an unchanged expansion.',
            current_flags='Retain CURRENT normal/fault/repairing from live protected words and5repair words. Do not register normal or reuse a cached syndrome as authority.',
            remaining='Gauss exact semantic word/bit reverse map of _121746_/_118149_ if preserved; source-local source association proven only to static bank sequential block. Measure changed fullshape station SS60/FF25; existing failures immutable.'),
        actual_caller_replacement_hook=caller_boundary_contract(),
        retained_parent_map='results/physical/hbm_w2_parent_physical_20261006/mapped_r2/terminal.json',
        W2_core_bbox_um=child['core_bbox_um'],
        W2_gross_bbox_um=child['gross_bbox_um'],
        W2_pin_track_allocation=pins,
        W2_receiver_paths=dict(
            result_data_driver='u_caller_cut.protected_caller.u_protected.output_stage[2].u_state/code',
            result_valid_driver='u_caller_cut.protected_caller.u_protected.output_stage[2].u_state/code checked bit270',
            result_identity_driver='u_caller_cut.protected_caller.u_protected.u_identity/code',
            request_capture='g_on.g_die[d].u_shared.u_shared_owner.on.request_hold',
            response_driver='g_on.g_die[d].u_shared.u_shared_owner.on.response_hold',
            owner_driver='g_on.g_die[d].u_shared.u_shared_owner.on.control_code/frame_lo/frame_hi',
            crossing='protected_transport.u_protected_gateway.u_existing_shape_cdc.u_req/u_rsp',
            CP_reset='g_on.g_die[d].u_cp_reset',
            quiet_output_receiver='all_routes_drained positive root-POR/local-CP warm fence'),
        clock_port_map=dict(clk_sm='selected parent clk_sm', clk_mem='selected parent clk_mem',
                            rst_sm_n='root SM reset', rst_mem_n='root memory reset',
                            cp_reset_n='local CP reset only'),
        H16_existing_clock_evidence=h16_clock,
        H16_is_budget_only=(h16_clock['actual_propagated_insertion_ps'] is None),
        rejected_REGISTERED_clock_evidence=dict(
            setup_skew_ps=old['cts__clock__skew__setup'],
            hold_skew_ps=old['cts__clock__skew__hold'], transferable=False),
        actual_parent_mapped_netlist=dict(host='ot-epyc2',
            root='/srv/opentallas-scratch2/codex/w2-parent-retained-map-20261006/donor-map-r2',
            sha256='4cc2d817f9343ed5806b0cbc8794539c28206dd6c5d7c9a34cd8a55b1e526159'),
        actual_parent_ODB=None, actual_parent_SPEF=None,
        actual_parent_clock_and_receiver_binding=None,
        sink_and_context_geometry_are_not_interchangeable=True,
        source_callbacks_have_no_ready=True, independent_owner_ledgers_added=0,
        local_CP_reset_cannot_clear_root_state=True,
        connected_R2_terminal='results/rtl/w2_transaction_pipeline_20261005/connected_r2_PASS/terminal.json',
        connected_R2_gate_passed=model['connected_parent_integration']['connected_gate_passed'],
        extracted_context_gate_passed=True,
        extracted_context_terminal=model['additive_parent_protection']['joined_minimum_terminal'],
        physical_dispatch_admitted=False,
        remaining_bindings=model['additive_parent_protection']['missing_owner_inputs'])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'binding.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f'{TOP}: {len(pins)} finite sink tracks, retained327725-cell parent map bound; actual caller export/CTS/load HOLD')
    return record


if __name__ == '__main__':
    prepare()
