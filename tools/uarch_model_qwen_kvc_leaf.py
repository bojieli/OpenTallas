#!/usr/bin/env python3
"""Source-selected Qwen landing-decode leaf; additive unified-model sizing."""
import json
import uarch_model as unified


def model():
    # 128 independent PCs. Decode expands one 32-byte beat to <=2 compact writes.
    # Input includes the expected sector from the separately required stream sequencer.
    inp = 256 + 17*2 + 13 + 8*2 + 11*2 + 2
    out = 256 + 11*2 + 7*2 + 2*2 + 2 + 1 + 1 + 1 + 1 + 4
    state = inp + 3*out + 64
    area = state*unified.DFF_UM2 + 12000  # logic, clock/hold and pin-driver reservation
    return dict(schema='opentallas.qwen_kvc_leaf.v1', model_precedes_rtl=True,
        status='PROPOSED_NOT_ADOPTED', source_model='tools/uarch_model.py',
        applicable_design='Qwen3-8B ROM', other_designs='unchanged',
        scope='landing decode only; does not replace whole qfd_kvc or qfd_ctrl',
        replicas=128, replicas_per_stack=32, macs_per_cycle=0,
        compute_intensity_macs_per_byte=0, payload_bytes_per_cycle=32,
        memory_ports=[], input_bits_per_cycle=inp+1, output_bits_per_cycle=out+1,
        frame_um=[328.32, 370.44], cell_area_bound_um2=area,
        area_bound_mm2_per_die=area*128/1e6,
        frame_fit_at_55pct=area < 328.32*370.44*.55,
        tracks=dict(required_each_face=max(inp,out)+3,
                    available_per_face=int(370.44/.288), pitch_um=.288),
        replicas_cost=dict(state_bits=state*128, data_mux='one fixed PC; no cross-PC mux',
            demux='two tile destinations per beat; downstream row arbitration separate',
            fanout='register local context; external context broadcast needs separately routed stations'),
        flow=dict(initial_credits=8, receiver_fifo_required=8,
            admission='sender reserves downstream slot before input; pop returns one credit',
            registered_boundaries=True),
        latency=dict(pipeline_edges=4, composed_worst_case_added_token_cycles=4*36,
            base_token_cycles=216713, rate_cost_pct=100*(1-216713/(216713+4*36)),
            overlap_credit=0, cost_scope='decoder only; controller/row arbiters unpriced'),
        remaining=['trusted expected-sector sequencer and descriptor fence',
            'per-row arbitration preserving original rotating grant order',
            'token writeback and readiness aggregation', 'full die connection and die STA'])

if __name__ == '__main__':
    print(json.dumps(model(), indent=2))
