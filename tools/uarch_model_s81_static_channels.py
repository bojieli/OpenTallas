
def s81_static_channels_1014_model():
    """Static pass lanes 3..7; FMT1 pacing remains the transport calendar's obligation."""
    return dict(name="s81_static_channels", macs_per_cycle=0,
                physical_lane_map={str(c): c+3 for c in range(5)},
                raw_payload_bits=552, outer_last_bits=1, forward_frame_bits=595,
                codec_pipeline_edges_each_direction=2, gearbox_edges_each_direction=1,
                channel_plus_codec_plus_gearbox_edges_each_direction=4,
                measured_component_calendar=dict(client_transfers=15, physical_lanes=5,
                    source_interval_cycles=16, first_payload_phy_beat_after_source_cycles=3,
                    receive_commit_after_source_cycles=11,
                    note="component cadence only, no production token-rate claim"), aggregate_boundary_bits_per_cycle=5*552,
                vm_payload_bytes_per_cycle=69, wfc_payload_bytes_per_cycle=64,
                host_reply_bytes_per_slot=81/8, memory_ports=0, buffers=0,
                replicas=5, source_mux_inputs=3, singleton_source_max_fanout=5,
                registered_latency_cycles_each_direction=1,
                throughput="one scheduled payload per channel per cycle internally; FMT1 transport calendar limits wire occupancy",
                routing_tracks=2760, channel_capacity_tracks=None,
                floorplan_slot_fit="UNVERIFIED: no contract slot or physical closure claim",
                area="UNMEASURED", token_latency="two channel pin stages per end-to-end hop plus measured transport latency",
                immutable_price="unchanged; no production token-rate qualification before composed calendar")

if __name__ == "__main__":
    import json
    print(json.dumps(s81_static_channels_1014_model(), indent=2, sort_keys=True))
