"""Mandatory DS1M control identity extension. No original model edits."""
import json
from tools.gpu_sys.ds_hbm_bridge17_model import price as base_price


def price(nd=2,nsm=2):
    original=base_price(nd,nsm)
    dff=original['added_flop_area_um2']/original['added_flops']
    # CP retains launch_pos +4 bits and original external job32/generation4.
    # Completion position and tags are views of those retained registers.
    delta=nd*(4+32+4)
    return dict(schema='opentallas.ds_hbm.token17_pos20_identity.v1',
        unified_model_sha256=original['unified_model_sha256'],
        context_positions=1048576,source_max_position_exclusive=1048576,
        token_bits=17,position_bits=20,uniform_register_bits=32,
        job_tag_bits=32,generation_bits=4,
        doorbell_bits=17+20+32+4,completion_bits=17+20+4+32+32+4,
        added_flops_vs_token17_pos16=delta,added_area_um2=delta*dff,
        added_sram_bytes=0,added_uniform_storage_bits=0,
        source_entry_gate=dict(raw_token_input_bits=32,raw_position_input_bits=32,
            retained_fault_bits=1,range_compare_input_bits_per_die=15+12,
            behavior='reject raw token>=2^17 or position>=2^20 before narrowing; no launch/completion on refusal',
            extra_latency_cycles=0),
        boundary_bits_per_launch_increment_vs_pos16=nd*(4+36+20+36),
        sm_launch_tracks_increment=nd*nsm*4,
        replica_count=dict(cmdproc=nd,sm=nd*nsm),
        fanout='each retained full position feeds actual NSM UR1 inputs; external job/generation retained per CP',
        area_fit='control registers only; in-context SS/FF and routing closure unqualified',
        macs_per_cycle_change=0,memory_bytes_per_cycle_change=0,
        extra_latency_cycles=0,composed_latency='unchanged CP FSM + actual SM, memory and collective service; sequencer adds priced setup/join edges',
        narrowing='cmd_pos32 checked against actual context before driving pos20; no modulo/offset substitution',
        full_context_data_qualified=False,
        full_context_data_requirement='source image/provider must separately prove >=1048576-position state allocation, extents and capacity; reduced CTX32 emitter cannot qualify this',
        memory_tag_namespace='existing memory tags unchanged; job32/gen4 here is command identity, not an HBM owner replacement')


if __name__=='__main__':print(json.dumps(price(),indent=2))
