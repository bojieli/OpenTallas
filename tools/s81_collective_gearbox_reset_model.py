"""Model-before-RTL removal of provably dead gearbox RX payload reset loads."""
import json
from s81_collective_gearbox_pipeline_model import model as pipeline_model

def model():
    m=pipeline_model()
    m.update(schema='opentallas.s81.collective_gearbox_reset.v1',
        mechanism='Keep the priced partitioned TX; omit async reset from RX bg and racc payload, retaining reset on valid, hunt, counts, visible outputs and fault.',
        rtl_payload_reset_bits_removed_per_lane=456+1052,
        rtl_payload_reset_bits_removed_eight_lanes=8*(456+1052),
        mapped_reset_sink_count='PENDING synthesis; optimized-away payload bits do not count as physical sinks.',
        reset_replica_flops_added=0,
        reset_dependency=dict(bg='Read only while bv is true; bv resets false and captures with bg.',
                              racc='Read in locked hunt state only; entering locked state writes racc from current marker beat before its first read.',
                              reacquire='Alignment loss still clears racc, and every new lock initializes from its marker.'),
        latency=dict(added_cycles=2, one_way_added_ns=2/1.2, roundtrip_added_cycles=4,
                     reset_cleanup_added_cycles=0, reset_cleanup_token_delta_ns=0,
                     token_latency_delta_ns_per_traversed_lane=2/1.2),
        baseline_reset_recovery=dict(job='s81ph-dsfd_coll_lane_e-ac313d866-wide',
                                     slack_ps=-40.04, source_q_arrival_ps=603.81,
                                     sink_reset_arrival_ps=1340.56, tree_delay_ps=736.75,
                                     note='Predecessor measurement; no numerical timing gain inferred from sink reduction.'),
        area_allowance_note='Retain pipeline conservative area allowance and outline; no area saving claimed before mapping.',
        exactness='Cycle equality with original for visible outputs after any reset and re-lock, with priced two-cycle TX; deliberately omit marker accumulator initialization as negative control.',
        opt_in='TRIM_RX_RESET=0 default; physical candidate uses PIPE_TX=1 and TRIM_RX_RESET=1.',
        adoption='Requires exact/negative gates, actual SS recovery/removal and all setup/hold >=15ps, DRC0, and die-context STA. No reset false paths added.')
    return m

if __name__=='__main__':print(json.dumps(model(),indent=2))
