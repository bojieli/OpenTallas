"""RF visibility-fence fanout successor sized before RTL; no adoption claim."""
import math

def model():
    widths=[4114,4105]
    banks=[math.ceil(w/64) for w in widths]
    old_control=3*len(widths)
    new_control=3*sum(banks)
    return dict(schema='opentallas.hbm.rf_fence_cx.v1',default_enabled=False,
        source_failure='d30fa5f390491bf8059e4af8d7d7ea7ce383d33a: host_wr_ready to u_hw.s_d[3752], TT-229.54ps, R2R+12.20ps, output+67.50ps',
        MACs_per_cycle=0,compute_intensity=0,memory_bytes_per_cycle=0,
        capture_bytes_per_cycle=512,host_write_bytes_per_cycle=512,
        boundary_bits_per_cycle=dict(capture=4114,host_write=4105),
        replicas=dict(wide_skids=2,banks_per_skid=banks,bank_data_bits=64),
        control_fanout='Each bank local output-hold select drives at most64 bits; external ready reaches65 bank-local logic groups, not one4096-bit enable tree',
        multiplexer_cost='unchanged two payload registers and 2-way data select per bit; spare capture uses !s_v only, removing ready from spare data enable',
        register_bits=dict(payload=2*sum(widths),old_control=old_control,new_control=new_control,extra=new_control-old_control),
        area=dict(extra_sequential_um2=(new_control-old_control)*.2916,
            payload_DFF_lower_bound_um2=2*sum(widths)*.2916,
            mapped_combinational_um2=None,die_slot_um=[300,300],core_um=[288,288],
            placement_density=.55,actual_mapped_fit_required=True),
        routing=dict(signal_face_capacity_raw_tracks=4*300/.096,
            payload_boundary_tracks=4114+4105,local_select_max_load_bits=64,
            external_ready_local_groups=65,existing_ports_unchanged=True),
        latency=dict(extra_pipeline_cycles=0,capture_to_host_write_extra_cycles=0,
            true_ACK_visibility_extra_cycles=0,fence_extra_cycles=0,
            token_composition='same existing RF write/trueACK/fence order and serial latency; enables physical timing closure rather than claiming decode-rate gain'),
        physical=dict(preserve_bank_hierarchy_required=True,mapped_bank_topology_qualified=False,
            TT_setup_target_ps=0,FF_hold_target_ps=0,DRC_target=0,SS='sensitivity'),
        reliability='existing fault-free FF payload pathfinding; no new control protection, mirroring, lease, debt or authentication',
        adopted=False)
