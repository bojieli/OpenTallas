#!/usr/bin/env python3
"""Positive sizing of Ampere's selected periodic boundary, counted once."""
import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BOOK=Path('results/rtl/qwen_rom_stream4_clock_plan_20261005')


def model(root=ROOT):
    root=Path(root)
    source=root/BOOK/'inputs/periodic_source_model.json'
    original=json.loads(source.read_text())
    assert original['clock_ports']['controller_hclk']['period_ps']==1024
    families=original['frontend_fifos']
    assert len(families)==5 and sum(x['replicas'] for x in families)==516
    assert sum(x['storage_bits'] for x in families)==4086432
    # Whole-packet writes: no unchecked partial64-stripe update/RMW shortcut.
    # Actual W6 source construction; registered2encode/3decode is a positive
    # candidate stage budget, not loaded SS/FF closure or probability-zero fault.
    codec=json.loads((root/'results/uarch/dsrom_native_masked_backend_prepare_20261003/model.json').read_text())['SRAM_protection_candidate']['pair_cell_body_um2']
    rows=[];coded=pipe=pairs=mux=0
    for f in families:
        stripes=math.ceil(f['payload_bits']/64)
        width=stripes*72
        state=f['replicas']*width*f['depth']
        pipeline=f['replicas']*width*5
        codecs=f['replicas']*stripes
        selectors=f['replicas']*width*(f['depth']-1)*3
        coded+=state;pipe+=pipeline;pairs+=codecs;mux+=selectors
        rows.append(dict(name=f['name'],replicas=f['replicas'],depth=f['depth'],
            source_domain=f['source_domain'],destination_domain=f['destination_domain'],
            original_payload_bits=f['payload_bits'],coded_packet_bits=width,
            stripes64=stripes,coded_storage_FF=state,encoder_decoder_pairs=codecs,
            encoder2_decoder3_pipeline_FF=pipeline,read_mux_NAND2_estimate=selectors,
            pointer_publication='only after complete encoded packet captured into reserved ring slot',
            delivery='only after checked same-slot payload and full tag, UE holds owner/fault; no unchecked ACK',
            whole_packet_write=True,additional_memory_ports=0,
            minimum_endpoint_II_source_edges=1,
            II_basis='pipelined dedicated per-endpoint encoder/decoder; source preparation, not loaded timing',
            bounded_fault_drain='stop new phase, retain ring and decoder owner; no live reset erasure'))
    control=original['area']['FIFO_pointer_online_reset_bits']
    fault_mailbox_bits=2*16+2*1+15+4 # current Ampere source delta beyondr2 record
    aux=original['area']['mailbox_bits']+fault_mailbox_bits+2
    # Local redundant state/checker: synchronize actual Gray signals, not coded
    # data words mistaken for safe asynchronous pointer transfer.
    control_ff=2*(control+aux)
    compare_nand=3*(control+aux)
    ff_total=coded+pipe+control_ff
    buffers=math.ceil(ff_total/7) # explicit fanout8 distribution proxy
    body=ff_total*.2916+(mux+compare_nand)*.08748+buffers*.10206+pairs*codec
    old_ring_body=4086432*.2916
    reserve=2*body*1.2/1e6
    H=1024;C=833.333
    # Encode before pointer publication; decode after real receiver capture.
    paths=dict(
        descriptor_accept_and_return_ps=4*H+3*C,
        GO_to_stack_sample_ps=5*H,
        RD_to_checked_core_consume_ps=(23+2)*H+(4+3)*C,
        write_to_checked_done_ps=(4+3+17+2)*H+(4+2+3)*C,
        tagged_request_to_checked_response_ps='(4+2+23+2)*1024 + (4+3)*TCLK_period_ps + AQ/split/refresh',
        credit_return_CORE_source_ps=3*C,
        credit_return_HCLK_source_ps=3*H)
    return dict(schema='opentallas.qwen.stream4.periodic_provider_registration.v1',
        selected='Ampere external periodicHCLK1024ps; same2dcbec controller/43b21 stack, protected finite frontend rings',
        functional_source_preparation_allowed=True,default_enabled=False,
        source_model_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_SHA256={str(p):hashlib.sha256((root/p).read_bytes()).hexdigest() for p in
            [BOOK/'inputs/periodic_source_model.json',BOOK/'inputs/periodic_clock_plan.py',
             Path('tools/qwen_rom_periodic_provider_registration.py'),
             Path('results/uarch/dsrom_native_masked_backend_prepare_20261003/model.json')]},
        endpoint_rows=rows,
        protection=dict(original_ring_payload_bits=4086432,coded_ring_bits=coded,
            parity_and_padding_increment_bits=coded-4086432,
            actual_ring_replacement_not_duplicate=True,
            new_pipelined_codec_bits=pipe,codec_pairs=pairs,local_redundant_control_FF=control_ff,
            additional_fault_mailbox_source_state_bits=fault_mailbox_bits,
            fault_mailbox_delta_basis='current copied source; r2 frozen record lacks this53bit delta',
            Gray_pointer_crossing='only firstsyncD exceptions; sourceperiod bus-skew/maxdelay; stage1->stage2 timed',
            payload_crossing='owner slot stable to synchronized pointer; no blanket async/data falsepath',
            nominal_encode_source_edges=2,nominal_decode_receiving_edges=3,
            code_basis='actual retainedW6 64->72 NAND/INV construction',
            partial_packet_lane_write_forbidden=True,loaded_cuts_qualified=False),
        budget=dict(total_FF_realization_bits=ff_total,read_mux_NAND2=mux,
            control_compare_NAND2=compare_nand,fanout8_buffer_estimate=buffers,
            cell_body_estimate_mm2=body/1e6,required_gross_home_mm2=reserve,
            required_home_envelope_um=[4000,4000],
            existing_raw_ring_cell_floor_mm2=old_ring_body/1e6,
            net_cell_increment_over_same_raw_FF_realization_mm2=(body-old_ring_body)/1e6,
            global_clock_cap_estimate_fF=ff_total*1.0,
            cap_basis='positive1fF/sink engineering budget, not actual Liberty clock load',
            HCLK_PC_replicas=128,endpoints=516,
            per_endpoint_tracks={f['name']:f['payload_bits'] for f in families},
            aggregate_read_wire_bits=sum(f['replicas']*f['payload_bits'] for f in families),
            no_global_single_bus_assumed=True,PG_wire_placement_reserve_fraction=.2,
            home_reserved=False,geometry_fit=False,loaded_SSFF_qualified=False),
        causal_paths=paths,
        causal_basis='per transaction, max phase without queue/refresh stall; actual AQ/refresh/split cost adds once',
        pending_domain_binding=dict(CORE_period_ps=C,HCLK_period_ps=H,
            TCLK_actual_source='die.hclk through actual tagged_rows_hook; not automaticallyHCLK nor CORE',
            TCLK_period_selected=False,
            current_pulsed_source_intervals_ps=[833.333,1666.666],
            average_1024_is_not_minimum_interval=True),
        overlap_accounting=dict(
            existing4086432_ring_payload_instances=1,
            not_additive_to_same_landing_write_ring_SRAM_or_FF=True,
            common_advance_slot='17.848841mm2 is separate operand-response/clock/control estimate, not a duplicate backend ring',
            inline_existing_tile_capture1536x1032_count=1,
            common_advance_operand_hold='selected post-read/KV/X operand transaction staging distinct from existingKVmaskedwrite ingress',
            physical_alias_credit='only actual matched instance/protected-role containment permits subtraction',
            no_alias_credit_assumed=True),
        gates=dict(RTL_component_preparation=True,physical_launch=False,SSFF_admitted=False,
            per_token_critical_event_counts_enrolled=False,full_token_latency_ps=None,rate_credit=False),
        pending_source_implementation=['encode before pointerpublish; decoder checkedterminal beforeconsume',
            'coded shadowed control and clock-domain reset/epoch drain, no live reset-asACK',
            'actual macro/payload mux and clock/load/pin/home routes',
            'literal same-program accepted events to expose/max causal paths, not perphase multiply'],
        existing_timer_budgets=original['absolute_HBM_timer_budgets'],
        source_controller_logic_changed=False,no_new_job=True)

if __name__=='__main__':
    out=ROOT/BOOK/'unified_registration.json'
    out.write_text(json.dumps(model(),indent=2,sort_keys=True)+'\n')
