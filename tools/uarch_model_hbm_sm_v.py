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
