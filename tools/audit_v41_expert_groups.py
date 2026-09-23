#!/usr/bin/env python3
"""Necessary expert-group service bounds; no routing or hardware simulation."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def group_bound(experts, selected, expert_bytes, group_size, users=1,
                port_bytes=256, clock_hz=1e9, delivery=0.65, budget_us=1):
    """Distinct top-k within a user; arbitrary repeated routes across users.

    Every group is independently provisioned for its own worst-case load.
    Summing installed ports does not mean all groups are concurrently hot.
    No inter-user weight reuse is credited.
    """
    if not (1 <= selected <= experts and 1 <= group_size <= experts and users >= 1):
        raise ValueError('Invalid expert geometry or concurrency')
    if min(port_bytes, clock_hz, budget_us) <= 0 or not 0 < delivery <= 1:
        raise ValueError('Invalid port service assumption')
    sizes = [min(group_size, experts - i) for i in range(0, experts, group_size)]
    bytes_per_port = port_bytes * clock_hz * delivery * budget_us * 1e-6
    demands = [users * min(selected, size) for size in sizes]
    ports = [math.ceil(d * expert_bytes / bytes_per_port) for d in demands]
    return {
        'experts_per_group': group_size, 'groups_per_layer': len(sizes),
        'simultaneous_users': users,
        'max_expert_jobs_per_group': max(demands),
        'max_group_rom_bytes': max(sizes) * expert_bytes,
        'max_group_ports_required': max(ports),
        'installed_ports_per_layer_for_arbitrary_routes': sum(ports),
        'max_group_weight_TB_s_required': max(demands) * expert_bytes / budget_us / 1e6,
        'single_expert_capacity_queue_waves': max(demands),
    }


def main():
    model_path = 'configs/models/candidates/deepseek-v4.1-flash.json'
    m = json.loads((ROOT / model_path).read_text())
    layers, experts, selected = m['num_layers'], m['num_experts'], m['experts_per_token']
    assert m['routed_weight_bytes'] % (layers * experts) == 0
    expert_bytes = m['routed_weight_bytes'] // (layers * experts)
    rows = [group_bound(experts, selected, expert_bytes, size, users)
            for users in (1, 4, 16) for size in (1, 2, 4, 6, 16, 64, 384)]
    out = {
        'schema': 'opentallas.v41-expert-groups.v1',
        'status': 'necessary_service_bounds_only_not_feasible_architecture',
        'model': m['name'], 'packed_expert_bytes': expert_bytes,
        'assumptions': {'port_bytes_per_cycle': 256, 'clock_hz': 1e9,
                        'delivered_fraction': .65, 'expert_layer_budget_us': 1,
                        'independent_layer_groups': layers,
                        'inter_user_weight_reuse': False},
        'rows': rows,
        'limits': [
            'Packed profile bytes include its storage accounting; no additional scale charge or BF16 expansion is assumed.',
            'Port means an independent equivalent read service, not a characterized physical ROM macro.',
            'Group pooling assumes every expert can access the entire provisioned service through conflict-free striping.',
            'Queue waves apply to a group with capacity for one expert job per service interval; they are not a prediction for a wider group.',
            'Multiple-user demand is an unbatched service scenario. Batching can reuse weights but still requires separate arithmetic and latency accounting.',
            'Recurrence, reduction, nonlinear work, dispatch, merge, bank conflicts and physical timing can only worsen this byte-service screen.',
        ],
        'input_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                         for p in (model_path, 'tools/audit_v41_expert_groups.py')},
    }
    target = ROOT / 'results/architecture/v41_expert_groups.json'
    target.write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    for row in rows[:7]:
        print(json.dumps(row))


if __name__ == '__main__':
    main()
