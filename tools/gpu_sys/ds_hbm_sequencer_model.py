"""Opt-in analytical extension of uarch_model's physical constants.

Prices the shared-SM-edge DS control entry: token 17, position 16, unchanged
32-bit uniform registers/result payload and existing memory/collective CDC.
This is mandatory correctness plumbing, not an optional performance lever.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def price(nd=2,nsm=2):
    source=ROOT/'tools/uarch_model.py'
    tree=ast.parse(source.read_text())
    dff=next(ast.literal_eval(node.value) for node in tree.body
             if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DFF_UM2' for t in node.targets))
    added_cp_bits=nd*2  # retained launch_token and completion_token
    wires=nd*(2+nsm)  # db -> CP, CP -> SM, completion return
    replay_bits=nsm*(1024+8+16+16+1)+9+8+3
    return dict(schema='opentallas.ds_hbm.shared_edge_token17.v1',
        unified_model_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        topology=dict(dies=nd,sms_per_die=nsm),token_bits=17,position_bits=16,
        unsigned_token_extent=131072,command_bits=64,uniform_register_bits=32,
        result_bits=32,doorbell_payload_bits=33,completion_payload_bits=53,
        added_flops=added_cp_bits,added_sram_bytes=0,
        added_flop_area_um2=added_cp_bits*dff,
        added_mux_bits=nd*nsm,added_boundary_tracks=wires,
        routing_capacity='existing local command wires; absolute routed capacity unmeasured',
        area_fit='no SM storage enlargement; in-context physical closure pending',
        macs_per_cycle_change=0,memory_bytes_per_cycle_change=0,
        communication_bits_per_launch_increment=2*nd,
        added_latency_cycles=0,
        composed_latency='original command processor FSM + actual SM service + existing memory/collective CDC; width adds no edges',
        replicas=dict(cmdproc=nd,sm=nd*nsm),
        host_ring='not connected: legacy host_if token16 must not carry this path',
        clock='external controller/cmdproc share clk_sm; no new CDC or clock relaxation',
        ss_ff_qualified=False,
        ordered_sequencer=dict(held_command_bits=4+8+4+32+17+8*17,
            cursor_bits=3+3+1,state_bits=3+1,die_completion_bits=nd*(17+2),
            result_output_bits=17+2,
            register_bits=4+8+4+32+17+8*17+7+4+17+2+nd*19,
            area_um2=(4+8+4+32+17+8*17+7+4+17+2+nd*19)*dff,
            entry_configuration_bits=11*32,entry_configuration='external source-pinned wires, not added SRAM',
            command_output_bits_per_die=64+8+1+17+16+2,
            min_control_cycles_per_launch=4,
            composed_cycles='4 setup/join cycles per actual kernel launch + actual CP/SM/memory/collective service + all actual ready stalls',
            compute_macs_per_cycle=0,replicas=1,
            mask_replicas=nd,wire_load='ND command processors; eleven-entry selection mux',
            routing_tracks=11*32+nd*(64+8+1+17+16+2),
            routed_slot_fit='unmeasured; static functional gate only, no timing/area signoff',
            numerical_order='identical original D.expand kernel order'),
        expert_union_replay=dict(columns=8,weight_line_bytes=128,
            per_sm_payload_bytes=128,total_payload_bytes=nsm*128,
            register_bits=replay_bits,register_area_um2=replay_bits*dff,
            shared_scratch_extra_bytes=0,whole_expert_cache=False,
            hbm_weight_bytes_per_line=128,
            consumer_bytes_per_line='128 * popcount(actual column mask)',
            max_output_bytes_per_cycle_per_sm=128,
            input_line_cycles_lower_bound='1 capture + popcount(mask) actual consumer handshakes',
            one_expert_in_flight=True,
            resident_fetch_ring='reuses actual ot_gpu_expert_fetch; this extension does not add its staging twice',
            actual_fetch_sizing='DEPTH16, MAX_OUT8, DQ2 per SM; 2048B staging/SM, finite run4; price original fetch separately',
            end_to_end_latency='sum actual per-line HBM service + replay consumer stalls + fetch idle retirement; TC column-context service still required',
            tracks_per_sm=1024+3+16+9+4,
            numerical_order='same original line sequence for each selected column; ascending expert input; no reduction reassociation',
            full_kernel_weight_reuse=False))


if __name__=='__main__': print(json.dumps(price(),indent=2))
