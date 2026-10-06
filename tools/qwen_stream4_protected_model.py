#!/usr/bin/env python3
"""Exact pre-build inventory of the selected three-ring STREAM4 interface.

This replaces the corresponding raw rings, not the other two tagged-port
families in the historical periodic-provider estimate. No ROM ECC is added.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = Path('results/rtl/qwen_stream4_protected_20261005')


def model(root=ROOT):
    root = Path(root)
    pair = json.loads((root / 'results/uarch/dsrom_native_masked_backend_prepare_20261003/model.json').read_text())['SRAM_protection_candidate']['pair_cell_body_um2']
    rows = []
    for name, width, depth, source, destination, kind in (
        ('landing', 281, 64, 'HCLK', 'CLK', 0),
        ('write', 289, 16, 'CLK', 'HCLK', 1),
        ('write_done', 9, 64, 'HCLK', 'CLK', 2),
        ('descriptor', 30, 4, 'CLK', 'HCLK', 3),
        ('GO', 3, 4, 'CLK', 'HCLK', 4),
    ):
        a = int(math.log2(depth)); p = a + 1
        # The wrap bit travels with the payload. Every 44-bit piece has the
        # existing W2/W6 static PC7/word10/kind3 seal, encoded as Hamming72.
        n = math.ceil((width + 1) / 44); cw = 72 * n
        enc1 = n * (64 + 5 * 8) + p + 1
        dec = [cw + p + 1, cw + n * 5 * 8 + p + 1,
               cw + n * 8 + p + 1, width + 1 + p + 1]
        controls = 22 * p + 4  # seven DMR pointers (including delivered debt), dual-rail SYNC2, two DMR faults
        reset = 8             # two existing reset synchronizers per domain
        pipeline = 2 * (enc1 + sum(dec))
        cache = 2 * depth * (width + p + 1) if name == 'write' else 0
        extra = (2 * (2 * p + 25 + width + 1 + 1) if name == 'write'
                 else 2 * (p + 3) if name == 'landing' else 0)
        ff = depth * cw + controls + reset + pipeline + cache + extra
        mux = cw * (depth - 1) * 3
        if name == 'write':
            mux += 2 * (width + p + 1) * (depth - 1) * 3
            extra += 8  # two DMR sticky protocol bits + duplicate warm release SYNC2
            ff += 8
        checker = 3 * (pipeline // 2 + controls // 2 + cache // 2 + extra // 2)
        semantic = 3*(2*7+24+8) if name == 'write' else 3*30 if name == 'descriptor' else 0
        checker += semantic
        buffers = math.ceil(ff / 7)
        body = ff * .2916 + (mux + checker) * .08748 + buffers * .10206 + n * pair
        rows.append(dict(name=name, payload_bits=width, depth=depth, pointer_bits=p,
            source_domain=source, destination_domain=destination, kind=kind,
            replicas=128 if name in ('landing', 'write', 'write_done') else 1, source_payload_bytes_per_edge=width/8,
            coded_memory_write_bytes_per_edge=cw/8, coded_memory_read_bytes_per_edge=cw/8,
            compute_intensity_MAC_per_byte=0,
            communication_intensity='one payload per accepted source edge; one coded read per fetched destination edge',
            destination_payload_bytes_per_edge=width/8,
            source_clock_Hz=1e12/(1024 if source == 'HCLK' else 833.333),
            MACs_per_edge=0, arithmetic_reordering=False,
            pieces44=n, sealed_word_bits=cw, wrap_identity_bits=1,
            seal='PC7 + physical word10(slot*pieces+piece) + ring kind3; padding zero; wrap bit in protected payload',
            coded_memory_FF=depth*cw, encode_stage1_DMR_bits=2*enc1,
            decoder_DMR_stage_bits=[2*x for x in dec],
            pointer_counter_fault_DMR_and_sync_FF=controls,
            POR_release_synchronizer_FF=reset, total_pipeline_FF=pipeline,
            checked_HCLK_write_cache_DMR_FF=cache, port_credit_extra_DMR_FF=extra,
            total_FF=ff, read_mux_NAND2=mux, check_NAND2=checker, semantic_guard_NAND2=semantic,
            fanout8_buffer_estimate=buffers, codec_pairs=n,
            estimated_cell_area_mm2=body/1e6,
            read_ports=1, write_ports=1, cache_read_ports=2 if name=='write' else 0,
            mux='one depth:1 code read; write cache has distinct handoff/completion heads',
            clock_reset_fanout_sinks=ff, new_global_bus_bits=0,
            boundary_bits_per_source_edge=width, boundary_bits_per_destination_edge=width,
            local_coded_read_tracks=cw,
            II_edges=1, encoder_capture_stages=2, accept_to_publication_source_edges=1,
            pointer_visibility_destination_edges=2, decoder_capture_stages=4,
            publication_to_output_max_destination_edges=6,
            decoder_cuts='code capture; five partial syndrome groups; syndrome combine; correction/extract/seal + protected output',
            publication='reserve on accept, publish only on complete encoded slot write',
            reclamation='landing/ACK at checked output consumption; write ONLY at matching WR completion, never at handoff',
            warm_reset='inhibit new write-request admission, retain all accepted encoder/ring/decoder/cache debt; landing and ACK returns still admitted as old-controller debt',
            pointer_CDC='dual-rail Gray through SYNC2; mismatch suspends pointer use, no transient mismatch treated as ACK; each rail source-period max-delay/skew bound',
            fault='UE/seal/wrap/control mismatch quarantines new grants and invalid retire; existing owned records stay until POR or explicit repair',
            fault_model='single mutable-state upset detected or corrected; SECDED payload double-bit UE detected; correlated faults affecting both DMR rails are not claimed'))
    shared_rows=rows[3:]; rows=rows[:3]
    cell = sum(x['estimated_cell_area_mm2'] for x in rows)
    # A positive per-PC home rather than an undersized repeated instance. The
    # raw r5 routes measured 0.0169 mm2 cell area; no old mapped-area credit.
    util = .30
    core = cell/util
    width = 500
    height = math.ceil(core*1e6/width/2.16)*2.16
    shared_extra_ff=28+4+4  # source/destination owner/sticky DMR; duplicate warm release; dual-rail sticky H fault SYNC2
    shared_extra_area=(shared_extra_ff*.2916 + 3*shared_extra_ff/2*.08748 + math.ceil(shared_extra_ff/7)*.10206)/1e6
    shared_cell=sum(x['estimated_cell_area_mm2'] for x in shared_rows)+shared_extra_area
    shared = dict(rings=shared_rows, extra_control_FF=shared_extra_ff,
        total_FF=sum(x['total_FF'] for x in shared_rows)+shared_extra_ff,
        cell_area_mm2=shared_cell, required_home_um=[200,math.ceil(shared_cell/util*1e6/200/2.16)*2.16],
        descriptor_payload_bits=30, GO_payload_bits=3,
        descriptor_ring_depth=4, GO_ring_depth=4,
        descriptor_sealed_bits=72, GO_sealed_bits=72,
        maximum_outstanding_descriptors=1, maximum_outstanding_GO=1,
        protection='same sealed pipeline/control primitive; completion acknowledged only after real destination consumption',
        ordering='GO carries source descriptor ordinal3; checked source issued and destination consumed counters bind GO to matching descriptor. Delivery only when all real controllers accepted descriptor and busy_all.',
        GO_identity_bits=3, source_control_DMR_bits=14, destination_control_DMR_bits=14,
        configuration_bounds='descriptor row < MEM_WORDS/131072, count1..1024; write sector < MEM_WORDS and payload port identity == PC_ID; landing row/port same bounds',
        cold_reset='rst_n/POR erases; warm_rst_n only gates fresh admission through duplicated local release, never resets ring, cache, controller or simulator due queues',
        producer_clock='CLK833.333', consumer_clock='HCLK1024',
        descriptor_visibility_bound_ps=833.333+6*1024,
        GO_visibility_bound_ps=833.333+6*1024,
        control_inventory='source and destination counters, owner-valid, returned consumption pointer, fault/online bits all DMR; no unchecked toggle mailbox',
        note='Descriptor/GO protection must bind before whole-wrapper qualification; per-PC ring result alone is insufficient')
    # Cost expose-once at the service boundary; the unchanged posted chain
    # actually measured B_fill_exposed=0, so do not multiply by 36 layers.
    causal = dict(RD_to_checked_landing_ps=23*1024+1024+6*833.333,
        write_accept_to_handoff_ps=833.333+8*1024,
        WR_to_checked_write_done_ps=17*1024+1024+6*833.333,
        landing_added_vs_r5_ps=1024+3*833.333,
        write_added_vs_r5_before_handoff_ps=833.333+5*1024,
        completion_added_vs_r5_ps=1024+3*833.333,
        source_program='results/rtl/qwen_plain_ar_stream4_P8191_20261005',
        composed_service_delta='max(exposed landing path, ordered token write->actualWR->checkedwrite_done path); queue/refresh and measured source stalls retained once',
        full_token_delta_measured=False, fixed_whole_token_edge_charge=None,
        per_user_rate_credit=False)
    paths=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
           'rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv',
           'rtl/lib/ot_reset_sync.sv',
           'results/rtl/qwen_stream4_cdc_20261005/takeover_r5/source/ot_qwen_stream4_cdc_pc.sv',
           'results/rtl/qwen_stream4_cdc_20261005/takeover_r5/source/ot_qwen_hbm_stream4_cdc.sv',
           'results/rtl/qwen_rom_stream4_clock_plan_20261005/selected_P0_clock_boundary_r5.json']
    result = dict(schema='opentallas.qwen.stream4.mutable-interface.prebuild.v1',
        PROTECTED=0, selected_candidate_only=True, ROM_ECC=False,
        original_raw_source='6fc28b155c419ee79da72f1eb084aae2141f1f64',
        rings=rows, shared_descriptor_GO=shared, causal_paths=causal,
        cell_area_per_PC_mm2=cell, required_per_PC_home_um=[width,height],
        per_PC_core_area_mm2=core, utilization=util,
        replicated_PC_core_area_mm2=128*core,
        complete_interface_core_area_mm2=128*core+shared_cell/util,
        parent_slot_fit=None, slot_reason='Pinned preceding clock-boundary model has physical_slot_fit=null; no actual parent allocation is available. Required positive homes are priced, not silently fitted to a guessed slot.',
        previous_slot_source='results/rtl/qwen_rom_stream4_clock_plan_20261005/selected_P0_clock_boundary_r5.json',
        replicated_PC_array_um=[8*width,16*height],
        local_routing=dict(layers=['M2','M3','M4','M5','M6','M7'],
            channel_width_um=40, pitch_um=.048, tracks_per_layer=int(40/.048),
            capacity_tracks=int(40/.048)*3,
            peak_packet_tracks=sum(x['sealed_word_bits'] for x in rows) + 2*289,
            simultaneous_paths='three code reads plus two independent write-cache heads',
            no_remote_payload_redistribution=True),
        physical_admission=False, implementation_admission=True,
        implementation_scope='all128PC selected interface + one shared descriptor/GO boundary; actual parent phase/skew and placement remain qualification gates', adopted=False,
        physical_gates=['exact32 changed-source + CE/UE/seal/control/warm-held-debt gate',
                        'actual source-cell shadow retention census',
                        'contextual SS60 setup + FF25 hold, slew/cap/fanout/DRC clean',
                        'shared descriptor/GO protected boundary and actual parent slot'],
        actual_parent_clock_relation=dict(service_clock='actual core service clk',
            HCLK_ps=1024, CLK_ps=833.333,
            gated_u_me_clk='separate parent gated domain; not assumed equal to service clk',
            source_phase_and_loaded_skew_qualified=False,
            core_ref_closes_is_not_parent_signoff=True,
            asynchronous_budget_ps=833.333-60, asynchronous_min_ps=0,
            no_blanket_clock_group_or_payload_falsepath=True),
        source_SHA256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})
    from qwen_stream4_die_allocation import allocation
    die = allocation(result, root)
    from qwen_stream4_transport_model import transport
    link = transport(die, result, root)
    result.update(parent_slot_fit=None, endpoint_slot_fit=die['slot_fit'],
        slot_reason='Endpoint homes alone fit. Selected finite transport adds its complete positive area charge; central ingress/local legs/PHY and loaded clock homes still require nonoverlapping actual allocation. Scalar area fit is not complete system fit.',
        selected_transport=link,
        die_allocation=die)
    result['actual_parent_clock_relation'].update(die['source_clocks'])
    result['actual_parent_clock_relation']['service_clock']='selected top free-running clk -> u_kv.clk'
    result['physical_gates'].append('full-width protected service transport and real PHY adapter/clock endpoint budgets')
    # Owner-approved functional r9 reuse: substitute only the landing read
    # mux, retaining the existing protected D0 capture and all four cuts.
    # Each owner r9 column selects at most29 coded bits, not51 unpriced bits.
    groups=math.ceil(504/29)
    selector_ff=2*64*groups*128
    selector_checks=3*64*groups*128*2
    selector_buffers=math.ceil(selector_ff/7)
    selector_cell=(selector_ff*.2916+selector_checks*.08748+selector_buffers*.10206)/1e6
    result['r9_protected_landing_read_candidate']=dict(
        parameter='LANDING_RSEL=1',default=0,owner_source='c8ba43664 RSEL1',
        functional_runtime_owner_authorized=True,physical_admission=False,adopted=False,
        protected_code_bits=504,depth=64,groups=groups,max_group_bits=29,replicas=128,
        selector_DMR_FF=selector_ff,selector_check_NAND2=selector_checks,
        buffer_estimate=selector_buffers,added_cell_mm2=selector_cell,
        added_core_mm2=selector_cell/util,
        composed_die_mm2=link['conservative_area_charge_die_mm2']+selector_cell/util,
        scalar_fit_is_not_slot_or_clock_qualification=True,
        group_valid_FF_added=0,
        held_capture='reuse existing checked u_d0 1024FF and valid/owner; en=advance for every group, never unconditional raw reload',
        mechanism='same owner r9 kept per-group onehot and continuous AND/OR column mux; checked-state primary/inverse adds selector protection',
        ports='existing sealed landing mem -> existing u_d0; no new external ABI or pop authority',
        MACs_per_edge=0,read_bytes_per_edge=63,boundary_coded_bits_per_edge=504,
        extra_global_tracks=0,local_selector_input_pins_per_group_max=64*29,
        existing_decoder_cuts=4,added_latency_edges=None,
        latency_gate='changed-source golden held/refill comparison required; do not assume zero added cycles',
        warm='no warm reset on selector or D0; existing reservation/retirement debt unchanged',
        bandwidth='four global return frames/core/rank unchanged')
    from qwen_stream4_parallel_pc_model import model as parallel_pc_model
    result['parallel_protected_PC_candidate']=parallel_pc_model(root)
    return result


if __name__ == '__main__':
    out=ROOT/BOOK/'prebuild_model.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(model(),indent=2)+'\n')
