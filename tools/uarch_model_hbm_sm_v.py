"""Source-sized SM closure vehicle for the existing unified SM model.

No area/rate substitution: retain actual routed macro outlines and 32-SM
organisation. The finite-provider bench adds no accelerator hardware.
"""
import math

def source_cost(floorplan, *, measured_added_drain_cycles, measured_added_done_cycles):
    if (floorplan['macros']['count'] != 202 or measured_added_drain_cycles != 12
            or not measured_added_done_cycles or any(c<=0 for c in measured_added_done_cycles)):
        raise ValueError('selected complete SM geometry/measured DS3 latency required')
    nc,sub,lbs,lsb,xd,il,rmax=8,4,2,16,128,8,4096
    leaves=nc*sub
    slice_bits=lbs*266+lsb*16
    fragment_bits=leaves*slice_bits
    beats=math.ceil(fragment_bits/2048)
    tag_bits=int(math.log2(rmax))+1+int(math.log2(il))
    control_bits=6+tag_bits
    write_bits=1+int(math.log2(xd))+beats+2048
    read_address_bits=1+int(math.log2(xd))
    half_count=2
    return dict(
        source='uarch_model.sm_op_cycles/sm_area plus complete source macro floorplan',
        nc=nc,sub=sub,il=il,rmax=rmax,xd=xd,
        issue_items_per_cycle=1,
        peak_macs_per_cycle=dict(bf16=leaves*lsb,fp4=leaves*lbs*32,fp8=leaves*(lbs//2)*32),
        ports=dict(descriptor_bits=56,request_bits=42,response_bits=1098,
                   weight_line_bytes=136,x_write_bytes=256,
                   x_useful_read_bytes=fragment_bits//8,
                   x_physical_macro_read_bytes=128*256//8,
                   result_bytes=nc*4),
        storage=dict(x_logical_bits=fragment_bits*xd,
                     x_physical_bits=128*128*256,
                     ring_logical_bits=1024*1088,ring_physical_bits=10*512*256,
                     outstanding_requests=512,wire_tag_bits=10,
                     credit_fifo_depth=7),
        replicas=dict(leaves=leaves,bf16_macros=leaves,block_dot_macros=leaves,
                      x_macros=128,ring_macros=10,sub_half_groups=sub*half_count,
                      half_to_leaf_fanout=4,x_write_root_fanout=sub),
        cuts=dict(per_sub_half_bits=control_bits+slice_bits+read_address_bits+write_bits,
                  per_quadrant_bits=half_count*(control_bits+slice_bits+read_address_bits+write_bits),
                  gather_bits=leaves*(2+32+tag_bits),
                  routed_track_capacity=None,
                  capacity_authority='actual existing SM route; no synthetic channel count'),
        geometry=dict(die_um=floorplan['die'],core_um=floorplan['core'],
                      complete_macro_area_mm2=floorplan['macro_area_um2']/1e6,
                      complete_element_mm2=floorplan['die_area_um2']/1e6,
                      replicated_32SM_mm2=32*floorplan['die_area_um2']/1e6,
                      complete_HBM_die_fit=False),
        latency=dict(added_drain_cycles=measured_added_drain_cycles,
                     stream_target_period_ns=0.833,
                     added_drain_ns_at_target=measured_added_drain_cycles*0.833,
                     measured_start_to_done_extra_cycles=measured_added_done_cycles,
                     start_to_done_extra_ns_at_target={str(c):c*0.833 for c in measured_added_done_cycles},
                     loaded_SS_FF_qualified=False),
        bench_scope='one complete NC8/RMAX4096 element, seeded BF16 K1004 R3; finite request/ACK/barrier debt',
        accelerator_hardware_changed=False,
        headline_clock_or_rate_credit=False)


def boundary_relocation_cost(floorplan, *, measured_added_done_cycles):
    """Prospective placement-only delta; clock/route admission remains open.

    Reuses all original ports, storage and cells. Zero incremental sequential
    latency is a source fact, not a zero cost assigned to an unknown service.
    """
    model = source_cost(floorplan, measured_added_drain_cycles=12,
                        measured_added_done_cycles=measured_added_done_cycles)
    model['placement_candidate'] = dict(
        hook='physical/hbm_accel_sm_views/sm_v_boundary_regions_r3.tcl',
        enrolment='opt-in POST_PDN; exact NC8/PIO2/202-macro instance census',
        existing_flops=dict(response_capture=1099, result_launch=270,
                            bulkcopy_count_and_credit=8),
        added_flops=0, added_memory_bits=0, changed_port_bits=0,
        added_sequential_cycles=0, incremental_cell_area_mm2=0,
        fences='actual macro-free south/east corridors and ring-group gap',
        storage_and_ports='unchanged complete source_cost above; no receiver or RF ACK bypass',
        clock_load='existing 224842 register sinks plus 202 macro sinks; unchanged',
        macro_clock_latency='retained leaf SS/FF liberty arcs; no clock insertion suppression',
        setup_external_ps=473, output_external_ps=323,
        setup_uncertainty_ps=60, hold_uncertainty_ps=25,
        observed_cts=dict(rv_setup_slack_ps=-4002.18,
                          rv_launch_clock_arrival_ps=3674.45,
                          rv_total_arrival_ps=4452.18,
                          rsp_data_1039_hold_slack_ps=-3598.67,
                          bulkcopy_internal_setup_slack_ps=-2455.22),
        predicted_routed_slack_ps=None, new_clock_supply_admitted=False,
        composed_latency_gain=None, route_admitted=False,
        blockers=['preserve live sm_r2 through terminal',
                  'source-bound clock-tree correction and complete load/routing price',
                  'actual contextual receiver/RF physical placement remains unjoined'],
        expected_effect='shorter existing boundary/count wires; no assumed clock or rate gain')
    return model
