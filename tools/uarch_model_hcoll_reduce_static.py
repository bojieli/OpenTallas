"""Sizing for fixed-calendar 16-lane collective reduction and publication."""
def model():
    return dict(fp32_lanes=16, tags=16, state_roots=16,
                state_flops_per_root=16*32+4*32,
                add_roots=16, add_flops_per_root=676,
                control_root_flops_upper_bound=1000,
                ingress_bits_per_cycle=545, ingress_payload_bytes_per_cycle=64,
                state_read_bytes_per_cycle=64, state_write_bytes_per_cycle=64,
                publication_bits_per_cycle=545, macs_per_cycle=0, fp32_adds_per_cycle=16,
                replicas=1, tag_control_fanout=16, add_read_to_issue_edges=1,
                add_issue_to_writeback_edges=8, earliest_dependent_read_after_issue_edges=9,
                publication_read_to_pin_edges=1,
                quarter_flits=16, groups=12, group_ranks=8,
                pairwise_tree_adds_per_flit=7, full_workload_fp32_adds=12*16*7*16,
                bf16_publication_values=32,
                routing_tracks_required=545, channel_capacity_tracks=None,
                area_slot_fit='16 real state leaves +16 native add leaves; physical slot unqualified',
                latency='distributed pairwise tree: three dependent add stages; each read+issue+WB then next read only after WB',
                status='SIZED; behavioral component gate only; physical and G96 token qualification pending')
if __name__=='__main__':
 import json
 print(json.dumps(model(),indent=2))
