"""Aligned head transport sizing before the minimum one-bundle RTL vehicle."""
def model(head_dies=12, stages=4):
    """Aligned hbglue-to-A pin transport, sized before the one-bundle RTL vehicle.

    Four stages are a proposal, not a timing-qualified choice.  Data, launch,
    row identity, and B-root join inputs incur the same delay at every A.
    """
    import math
    assert head_dies > 0 and stages > 0
    bundles = math.ceil(129280/(128*head_dies))
    elements = 4*bundles
    packet = 256+17+1+1+32
    bits = elements*stages*packet
    cell_floor = bits*0.2916  # existing ASAP7 DFFHQN proxy in this model
    return dict(schema='opentallas.dsrom.head-input-staging.v1',
                default_enabled=False, adopted=False,
                source='rtl/v41rom/ot_dsrom_head_bundle.sv and head_elem A input ABI',
                sizing=dict(head_dies=head_dies, bundles_per_die=bundles,
                            A_elements_per_die=elements, stages_per_A=stages,
                            bits_per_stage=packet, registered_bits_per_die=bits),
                MACs_per_cycle_unchanged=True,
                compute_intensity_unchanged=True,
                ports_bytes_per_cycle=dict(x_per_A=32, other_per_A=(packet-256)/8),
                boundary_bits_per_cycle=dict(each_A=packet, per_bundle=4*packet),
                replicas=dict(A_input_pipeline=elements, stage_groups=elements*stages),
                mux_demux_added=0,
                fanout=dict(source_A_receivers_per_bundle=4,
                            purpose='independent aligned landings beside actual A pin groups'),
                routing=dict(per_A_tracks=packet, pin_segment_target_um=100,
                             capacity='requires extracted A LEF faces and one-bundle route'),
                area=dict(register_cell_floor_um2_per_die=cell_floor,
                          register_slot_floor_mm2_at_55pct=cell_floor/.55/1e6,
                          buffer_CTS_hold_area_unmeasured=True,
                          floorplan_slot_fit=False),
                latency=dict(added_cycles_per_head_pass=stages,
                             added_verify_AR_us=stages/1200,
                             added_draft_5passes_us=5*stages/1200,
                             added_verify_6pass_stage_busy_us=6*stages/1200,
                             II_effect='price new head busy against actual stage limiter'),
                qualification='proposed structural budget; exactness and routed timing required')
