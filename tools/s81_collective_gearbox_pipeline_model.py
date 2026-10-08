"""Model-before-RTL two-stage partition of the collective gearbox shift."""
import json
from s81_collective_gearbox_model import model as head_model

def model():
    m=head_model()
    m.update(schema='opentallas.s81.collective_gearbox_pipeline.v1',
        mechanism='Registered FIFO head; split insertion shift into low 4 and upper shift bits with independent registers; accumulate and emit in third stage.',
        added_pipeline_flops=2*1052+2*(53+3)+2+7,
        pipeline_flops_basis='Two 1052-bit insertion registers, two 56-bit reverse/idle/marker records, two valid bits and seven upper-shift control bits (CB=11).',
        added_flops_per_lane=595+2*1052+2*56+2+7,
        added_flops_eight_lanes=8*(595+2*1052+2*56+2+7),
        area_allowance_um2_per_lane=2*(595+2*1052+2*56+2+7),
        estimated_cell_area_um2=67535+2*(595+2*1052+2*56+2+7),
        estimated_utilization=(67535+2*(595+2*1052+2*56+2+7))/(345.6*(340.2-1.08)),
        lane_um=[365.04,340.2], area_um2=365.04*340.2,
        replication_cost='Eight lanes each add head and two insertion pipeline registers; local mux/shift stages replace serial selection-plus-shift.',
        area_allowance_basis='Conservative 2 um2 per added register bit including mux, shift and local drive allowance; replace with synthesized area.',
        added_local_wires_bits=595+2*1052,
        topology='595-bit head to low shift, 1052-bit low-to-high shift, 1052-bit high shift to accumulator/output; registered local boundaries.',
        local_routing_screen=dict(insertion_bus_bits=1052, track_pitch_um=0.048,
                                 single_bus_track_span_um=50.496, outline_width_um=365.04,
                                 note='Track lower-bound screen only; competing stage buses and pin access require routed proof. M8/M9 remain reserved.'),
        slab_um=[1237.656,1369.416],
        slab_area_added_vs_head_um2=(1237.656-1198.776)*1369.416,
        physical_outline_note='Increase from 345.6 to 365.04 um to keep conservative cell allowance below 60%; new pin contract required before route.',
        latency=dict(added_cycles=2, one_way_added_ns=2/1.2, roundtrip_added_cycles=4,
                     token_latency_delta_ns_per_traversed_lane=2/1.2,
                     composition='Multiply by actual serial lane traversals in each priced collective; no performance credit assumed.',
                     reverse_delta_cycles=2),
        flow=dict(original_fifo_slots=4, pipeline_insertion_records=2, peak_records_per_cycle=1,
                  added_link_roundtrip_credits_ceiling=4,
                  timeout_implementation='Isolated lane passes CH_UCIE+2 and CH_BOARD+2 into endpoint timeout calculation, increasing actual ATO/ATOB by four clocks.',
                  note='Fixed-rate pipeline cannot stall; no queue capacity removed. Existing endpoint pacing and 512 credits retained; throughput may become credit-limited four clocks earlier.'),
        reset='Pipeline valid bits reset; no mandatory reset fanout to payload registers.',
        timing_risk='Each shift stage has fewer mux levels; SS/FF setup, reset recovery and output hold still require full-lane route.',
        opt_in='PIPE_TX=0 default; PIPE_TX=1 candidate only.',
        exactness='Beat and reverse stream equal original delayed by exactly two clocks after reset; receiver outputs unchanged for identical external input; mutation of upper shift must fail.')
    m['estimated_utilization']=m['estimated_cell_area_um2']/(365.04*(340.2-1.08))
    return m

if __name__=='__main__': print(json.dumps(model(),indent=2))
