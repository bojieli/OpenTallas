"""Physical sizing and latency contract for the opt-in S81 OQPIPE core."""
import math


def model(width=540.0, vm_pin_step=4):
    old_width, height, lane_width = 507.384, 1360.8, 345.6
    if not math.isfinite(width) or width < old_width or vm_pin_step < 1:
        raise ValueError('Preserve core area and use a positive integral track stride')
    vm_bits, pitch = 2695, .048 * vm_pin_step
    if 4.8 + vm_bits * pitch >= width - 1:
        raise ValueError('Native VM interface does not fit the proposed edge')
    return dict(
        schema='opentallas.s81.collective_core_sizing.v1',
        status='CANDIDATE_NOT_ADOPTED',
        source_commit='3abd84e2c0faf561e8a1da8238c50799dadf3e03',
        measured_predecessor=dict(core_um2=689900.2, std_um2=68475.0,
                                  macro_um2=170324.3, flops=94223,
                                  south_pins_per_100_um=2084),
        core_um=[width, height], area_um2=width * height,
        area_delta_um2=(width-old_width)*height,
        slab_um=[round(2*lane_width+width+.192, 4), 1369.416],
        replicas=1, macs_per_cycle=0, compute_intensity=0,
        memory_ports=dict(macros=24, macro_width_bits=256,
                          read_capacity_bytes_per_cycle=768,
                          write_capacity_bytes_per_cycle=768,
                          note='Physical capacity; finite queues and existing schedule unchanged'),
        boundaries_bits_per_cycle=dict(vm_in=592, vm_out=2100, time_slice=3,
                                        lane_send=8*553, lane_receive=8*553),
        routing=dict(vm_layer='M5', track_pitch_um=.048,
                     track_stride=vm_pin_step, vm_bits=vm_bits,
                     span_um=vm_bits*pitch, available_um=width-5.8,
                     pins_per_100_um_upper=math.ceil(100/pitch)+1,
                     gate_pins_per_100_um=1200, target_pins_per_100_um=600),
        replication_cost='Existing eight lane handshakes and output queue fanout; no new mux, demux or storage',
        latency=dict(physical_footprint_added_cycles=0,
                     existing_oqpipe_visibility_edges_per_collective=1,
                     pipeline_ii_added_cycles=0,
                     cost_row='coll_core_oqpipe in dsrom_closure_cost_ledger.CANDIDATES',
                     condition='Die boundary wire/station latency must be composed separately'),
        admission=dict(calibrate_ram_gb=12, route_ram_gb=112,
                       route_peak_measured=False,
                       basis='W DRT14,533,068KB scaled by core/W area6.25 plus20% inventory allowance; own core floorplan2,854,364KB'),
        gate='TT setup>=0,FF hold>=0,DRC0,current routed reference; SS sensitivity; die context required')
