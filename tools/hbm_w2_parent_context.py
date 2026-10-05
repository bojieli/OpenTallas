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
    'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv', SOURCE,
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
        parameters=dict(ENABLE=0, PROTECTED_TRANSACTION_PIPELINE=0),
        qualification_parameters=dict(ENABLE=1, PROTECTED_TRANSACTION_PIPELINE=1),
        hardware_sources=SOURCES,
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                       for p in SOURCES + [parent, caller, h16, domains,
                                          str(contract_path.relative_to(ROOT))]},
        sized_context=model['dedicated_W2_context'],
        W2_core_bbox_um=child['core_bbox_um'],
        W2_gross_bbox_um=child['gross_bbox_um'],
        W2_pin_track_allocation=pins,
        W2_receiver_paths=dict(
            result_data_driver='native_w2.u_sm.g_pq.u_prd_o.g_s[1].g_n.u/q',
            result_valid_driver='native_w2.u_sm.g_pq.u_prv_o.g_s[1].g_r.u/q[0]',
            result_identity_driver='native_w2.u_results.g_restore.qa/qb/qrows/qpair/qbound',
            request_capture='g_on.g_die[d].u_shared.u_shared_owner.on.request_hold',
            response_driver='g_on.g_die[d].u_shared.u_shared_owner.on.response_hold',
            owner_driver='g_on.g_die[d].u_shared.u_shared_owner.on.control_code/frame_lo/frame_hi',
            crossing='g_on.g_die[d].g_cdc[0].u_x',
            CP_reset='g_on.g_die[d].u_cp_reset',
            quiet_output_receiver=None),
        clock_port_map=dict(clk_sm='selected parent clk_sm', clk_mem='selected parent clk_mem',
                            rst_sm_n='root SM reset', rst_mem_n='root memory reset',
                            cp_reset_n='local CP reset only'),
        H16_existing_clock_evidence=h16_clock,
        H16_is_budget_only=(h16_clock['actual_propagated_insertion_ps'] is None),
        rejected_REGISTERED_clock_evidence=dict(
            setup_skew_ps=old['cts__clock__skew__setup'],
            hold_skew_ps=old['cts__clock__skew__hold'], transferable=False),
        actual_parent_mapped_netlist=None, actual_parent_ODB=None, actual_parent_SPEF=None,
        actual_parent_clock_and_receiver_binding=None,
        sink_and_context_geometry_are_not_interchangeable=True,
        source_callbacks_have_no_ready=True, independent_owner_ledgers_added=0,
        local_CP_reset_cannot_clear_root_state=True,
        connected_R2_terminal='results/rtl/w2_transaction_pipeline_20261005/connected_r2_PASS/terminal.json',
        connected_R2_gate_passed=model['connected_parent_integration']['connected_gate_passed'],
        extracted_context_gate_passed=False, physical_dispatch_admitted=False,
        remaining_bindings=[
            'Turing: actual mapped W2 boundary source/receiver objects and inherited-register allocations',
            'Turing: source clk_sm/clk_mem/reset roots, periods/relations and propagated SS/FF clock evidence',
            'Turing: per-net SS/FF receiver pins plus extracted wire loading from selected parent',
            'Selected-parent/caller owner: installed/priced gateway transport and inherited control/CDC protection',
        ])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'binding.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f'{TOP}: {len(pins)} finite sink tracks, source cut prepared; physical dispatch HOLD')
    return record


if __name__ == '__main__':
    prepare()
