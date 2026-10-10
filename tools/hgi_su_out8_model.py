"""Model-first direct-ready OUT8 controller proposal; no adopted rate credit."""
import math


def hgi_su_out8_model(token_cycles=None, records_per_token=None):
    # Eight SECDED64 metadata records protect sector/local-offset, transaction tag,
    # write/read identity and epoch. Protected head/tail/count/epoch are separate.
    ledger_bits=8*64
    control_bits=2*7+8+13
    old_metadata_bits=4*27+2*2+3
    extra_ff=ledger_bits+control_bits-old_metadata_bits
    cases=[]
    for name,total,reads,writes,stage,drain,stall_s,stall_d in [
        ('BF16_GLU',3929,769,384,2134,1158,950,760),
        ('FP32_GLU',3017,577,288,1606,870,710,568)]:
        # Optimistic removal of observed credit-full edges is an upper bound,
        # never a predicted measured total. Bank arbitration/backpressure survive.
        ceiling=stall_s+stall_d
        case=dict(name=name,measured_old_cycles=total,read_sectors=reads,write_sectors=writes,
            measured_stage_cycles=stage,measured_drain_cycles=drain,
            observed_credit_stall_cycles=ceiling,maximum_removable_cycles=ceiling,
            minimum_total_from_stall_bound=total-ceiling,
            direct_body_read_latency_edges=7,local_return_pending_stages=3,
            ideal_read_service_cycles=math.ceil(reads/max(1,min(1,8/7))),
            ideal_drain_service_cycles=math.ceil(writes/min(1,8/(7+3))),
            measured_successor_cycles=None)
        if token_cycles is not None and records_per_token is not None:
            saved=ceiling*records_per_token.get(name,0)
            case['maximum_token_saved_cycles_no_overlap']=saved
            case['possible_rate_gain_ceiling']=token_cycles/(token_cycles-saved)-1 if saved<token_cycles else None
        cases.append(case)
    return dict(schema='opentallas.hgi_su_out8.proposal.v1',default_off=True,qualified=False,
        models=['DeepSeek-V4.1 HBM','Qwen3-8B HBM'],ROM_adoption=False,
        functional_source='199dc0b71',credit_census='4682ff603/c03acbce4',
        VM_source='ccac3e341 (f7e07f1a7/fcf135e87), bank59a9e0b4f',
        replicas_per_die=dict(SU=1,SFU=1),MACs_per_cycle=0,compute_change=0,
        port=dict(request_bits=337,response_bits=273,handshake_bits=4,
            boundary_bits_per_cycle=614,nominal_bytes_per_cycle=32,
            same_bank_physical_II=2,phase_alternating_logical_II=1,
            credits=8,credits_include_pending_local_returns=True,
            response_order='per-client request order',UE='sticky; consumer fails closed while draining'),
        resources=dict(ledger_slots=8,ledger_payload_bits=57,ledger_code_bits=64,
            protected_control_bits=control_bits,extra_flops_vs_old_raw_metadata=extra_ff,
            estimated_extra_sequential_area_um2=extra_ff*.2916,
            area_basis='Unified model DFF0.2916um2; SECDED logic, queue decode and ready/mux cells not yet mapped',
            local_data_bytes=512*1024,dirty_mask_bytes=16*1024,
            additional_data_macros=0,replica_mux_demux=0,
            mux_inputs=8,mux_width=64,metadata_decode_fanout=8),
        routing=dict(assumed_channel_um=64,signal_layers=4,pitch_um=.08,
            tracks_available=3200,packet_tracks=614,physical_slot_fit='pending full controller mapping'),
        cases=cases,admission=dict(plausible_component_gain=True,
            composed_at_least_one_percent='Must supply actual compiler record census and critical-path composition; not established',
            production_equivalence=False,RTL_ready=False,
            reason='Genuine direct-ready body available; protected ledger/direct handshakes and measured fullshape old/new gate required'),
        exact_gate=['default byte-identical old gate','SU/SFU actual numeric and dirty outputs',
            'outstanding8 and ninth stall','tag/epoch mismatch fail closed','pending local return overflow negative',
            'UE drain without publish','fullshape phase/occupancy census old/new'],
        latency='No data arithmetic change; stage/drain use measured direct VM service. No free overlap or headline credit')
