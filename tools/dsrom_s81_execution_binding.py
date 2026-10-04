"""Join Arendt's frozen S81 allocation to the existing source/compiler APIs.

No payload reads or arithmetic execution. Factories are supplied by the actual
caller, so this module does not import a different checkout's cached compiler.
"""
import gzip
import hashlib
import json
from pathlib import Path

CANONICAL = 'results/uarch/dsrom_s81_released_binding_20261004/canonical'
SOURCE = 'results/uarch/dsrom_native_weight_address_join_20261002'
HASHES = {
    'inventory.json': '0b8d8f6fddf7a427941b7a235aeb80e0ee370c51cafddba6427fa61d3ff99480',
    'stage_map.json': '47ea9eb0ba0b404f629a4bc758d28d8ac1fe28dcb31de3e5816517fa1d097815',
    'matrix_map.jsonl.gz': '985a9ee7ea26d2a7bb1aebadc5151252836eacf8181e8794b1ef6d7819db0326',
}


class CanonicalS81Execution:
    def __init__(self, owner, *, source_execution_factory, stage_join_factory):
        self.owner = Path(owner).resolve()
        base = self.owner / CANONICAL
        raw = {}
        for name, expected in HASHES.items():
            raw[name] = (base / name).read_bytes()
            if hashlib.sha256(raw[name]).hexdigest() != expected:
                raise ValueError(f'canonical S81 source changed: {name}')
        inventory = json.loads(raw['inventory.json'])
        stage_map = json.loads(raw['stage_map.json'])
        if (inventory['pairs_per_rank_die'], inventory['BF_dual_pairs'], inventory['TP'],
                len(stage_map['PHW_required_by_stage'])) != (2417,519,4,81):
            raise ValueError('canonical S81 geometry mismatch')
        matrices = [json.loads(line) for line in gzip.decompress(raw['matrix_map.jsonl.gz']).splitlines()]
        if len(matrices) != 46671:
            raise ValueError('canonical S81 fragment extent mismatch')
        source = self.owner / SOURCE
        demand_raw = (source / 'inputs/demand-r5.json.gz').read_bytes()
        bindings_raw = (source / 'r3/node_bindings.jsonl.gz').read_bytes()
        demand = json.loads(gzip.decompress(demand_raw))
        bindings = [json.loads(line) for line in gzip.decompress(bindings_raw).splitlines()]
        # The owner API checks literal node/template hashes and dimensions;
        # Popper's compiler supplies the same unique fragment key/CFG mapping.
        self.source = source_execution_factory(matrices, bindings, demand)
        self.stage_join = stage_join_factory(matrices, stage_map, pairs=2417,
                                             BF_pairs=519, stage_count=81)
        self.input_sha256 = {str(Path(CANONICAL)/n): hashlib.sha256(b).hexdigest()
                             for n,b in raw.items()}
        self.input_sha256.update({str(Path(SOURCE)/n): hashlib.sha256(b).hexdigest()
                                 for n,b in [('inputs/demand-r5.json.gz',demand_raw),
                                             ('r3/node_bindings.jsonl.gz',bindings_raw)]})

    def dispatch(self, node, rank, *, expert_ids=None):
        return self.stage_join.compile_operation(self.source, node, rank, expert_ids=expert_ids)

    def emit_programs(self, requests, out, *, program_address_bits=14):
        """Requests contain real source node/rank and live EIDs for expert ops.

        No cached reduced instruction widening or allocation-stage substitution.
        Caller still supplies actual context restore, input visibility, gather
        and retirement. Returned entries are the native program entry points.
        """
        dispatches = [self.dispatch(r['node'], r['rank'], expert_ids=r.get('expert_ids'))
                      for r in requests]
        return self.stage_join.emit_programs(dispatches, out,
                                             program_address_bits=program_address_bits)

    def emit_stage(self, stage, rank, out):
        return self.stage_join.emit_stage(stage, rank, out)
