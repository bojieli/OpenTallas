#!/usr/bin/env python3
"""Validate W19's existing non-SM inventory and pending resident bounds."""
import argparse
import ast
import hashlib
import json
import math
import subprocess
from pathlib import Path
from types import SimpleNamespace

from w16_measured_calibration import Refusal, require
from w16_w19_address_prerequisite import reservations_fit

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = 'results/rtl/w19_checkpoint_production_20261001/non_SM_source_inventory.json'
PROGRAM = 'results/rtl/w19_hbm_tp96_program_oreduce.json'
CONFIG = 'configs/models/candidates/deepseek-v4.1-flash.json'
ADDRESS = 'results/uarch/w16_w19_address_prerequisite_20261001/prerequisite_r2.json'
OUT = 'results/uarch/w16_w19_resident_bounds_20261001'
SIZES = {'BF16': 2, 'F32': 4, 'F8_E4M3': 1, 'F8_E8M0': 1}


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def inventory_bounds(inv):
    """Validate declared tensor geometry against actual recorded file bounds."""
    names, ranges, totals = set(), {}, {}
    for item in inv['items']:
        name, shard, shape = item['tensor'], item['shard'], item['shape']
        require(name not in names, 'duplicate tensor: ' + name)
        names.add(name)
        require(item['dtype'] in SIZES and shape and all(type(n) is int and n > 0 for n in shape),
                'unknown/invalid tensor geometry')
        size = math.prod(shape) * SIZES[item['dtype']]
        start, end = item['data_offsets']
        require(type(start) is int and type(end) is int and start >= 0 and end - start == size
                and item['stored_bytes'] == size, 'tensor extent mismatch: ' + name)
        base = inv['header_bindings'][shard]['header_bytes'] + 8
        require(item['header_data_base'] == base, 'header data base mismatch')
        require(base + end <= inv['shards'][shard]['bytes'], 'tensor exceeds recorded shard')
        ranges.setdefault(shard, []).append((start, end, name))
        totals[item['group']] = totals.get(item['group'], 0) + size
    for shard, regions in ranges.items():
        end = 0
        for start, stop, name in sorted(regions):
            require(start >= end, 'selected tensor overlap: ' + name)
            end = stop
    require(sum(totals.values()) == inv['stored_bytes'], 'inventory total mismatch')
    return dict(selected_tensors=len(names), selected_shards=len(ranges), stored_bytes_by_group=totals)


def rows_by_rank(n, tp=96, block=8):
    require(type(n) is int and n > 0, 'invalid row count')
    q, rem = divmod(n, tp * block)
    return [q * block + min(block, max(0, rem - r * block)) for r in range(tp)]


def stack_bound(weight_end, regions, required_sizes, aperture=1 << 32):
    """Local necessary bound only; ownership and deployment sizes must be explicit."""
    categories = {'constants', 'embedding', 'Engram', 'KV', 'index'}
    require(isinstance(required_sizes, dict) and set(required_sizes) == categories,
            'missing sourced per-stack deployment bounds')
    require(isinstance(regions, dict) and set(regions) == categories, 'missing resident regions')
    for name in categories:
        size = required_sizes[name]
        require(type(size) is int and size > 0, 'unknown/zero deployment bound: ' + name)
        region = regions[name]
        require(isinstance(region, dict) and type(region.get('bytes')) is int
                and region['bytes'] >= size, 'missing/undersized region: ' + name)
    require(type(weight_end) is int and weight_end > 0 and type(aperture) is int and aperture > weight_end,
            'invalid stack bounds')
    return reservations_fit(weight_end, regions, aperture)


def build():
    inv, program, cfg, address = (read(p) for p in (INVENTORY, PROGRAM, CONFIG, ADDRESS))
    require(inv['programme_sha256'] == sha(PROGRAM), 'inventory program mismatch')
    require(inv['checkpoint_revision'] == cfg['source_revision'], 'checkpoint revision mismatch')
    require(program['tp'] == 96 and program['key_block'] == 8 and program['position'] == 1048575,
            'unmatched context/ownership program')
    bounds = inventory_bounds(inv)
    c = dict(cfg['metadata']['operator_config'], num_layers=cfg['num_layers'])
    row_sizes = {}
    for node in ast.parse((ROOT / 'tools/arch_budget_v41.py').read_text()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ('CKV_ROW_B', 'IDX_KEY_B', 'WIN_ROW_B'):
                row_sizes[node.targets[0].id] = ast.literal_eval(node.value)
    require(row_sizes == dict(CKV_ROW_B=288, IDX_KEY_B=68, WIN_ROW_B=528), 'row encoding changed')
    producer_layers = [layer['layer'] for layer in program['layers'] if any(
        op.get('fn') == 'compressor' for op in layer['ops'])]
    require(producer_layers == c['kv_source_layer_ids'], 'KV/index store producer mismatch')
    kv, keys, stores = [0] * 96, [0] * 96, []
    for layer in producer_layers:
        n = 1048576 // c['compress_ratios'][layer]
        counts = rows_by_rank(n)
        stores.append(dict(layer=layer, rows=n, rank_rows=counts))
        kv = [a + b * 288 for a, b in zip(kv, counts)]
        keys = [a + b * 68 for a, b in zip(keys, counts)]
    window = 40 * c['window_tokens'] * 528
    logical = sum(kv) + sum(keys) + window
    fn = next(n for n in ast.parse((ROOT / 'tools/uarch_model.py').read_text()).body
              if isinstance(n, ast.FunctionDef) and n.name == '_v41_state_user')
    env = {'A': SimpleNamespace(_env=lambda: {'c': c}, **row_sizes)}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), 'source_bound_capacity', 'exec'), env)
    require(env['_v41_state_user']() == logical, 'existing model capacity mismatch')
    aperture = 1 << 32  # 27 sector bits x 32B; candidate address bound only.
    weights = address['placement']['rank_stack_bytes']
    try:
        stack_bound(max(map(max, weights)), inv['physical_stack_reservations'], None, aperture)
    except Refusal as exc:
        refusal = str(exc)
    else:
        raise Refusal('unexpected unsourced actual reservation qualification')
    paths = [INVENTORY, PROGRAM, CONFIG, ADDRESS, 'tools/uarch_model.py', 'tools/arch_budget_v41.py',
             'tools/w19_hbm_tp96_isa.py', 'tools/hdc_golden_v41.py',
             'tools/w16_w19_address_prerequisite.py', 'tools/w16_measured_calibration.py',
             'results/floorplan/hbm_gpu/v41_hbm_die.json',
             'results/rtl/w19_checkpoint_production_20261001/production-scope-correction.json',
             'results/rtl/w19_checkpoint_production_20261001/stopped-compact-offline-campaign.json',
             'tools/w16_w19_resident_bounds.py', 'tests/test_w16_w19_resident_bounds.py']
    return dict(schema='opentallas.w16.w19.resident_bounds.v1',
        base_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        inventory_source=INVENTORY, inventory_validation=bounds,
        inventory_classification='W19 other_text_objects_unclassified retained; no consumer encoding or replication inferred',
        logical_ownership=dict(KV_stores=stores, compressed_KV_bytes_per_rank=kv,
            stored_index_bytes_per_rank=keys, window_bytes_per_rank=window,
            Engram='row id % 96 in reference executor; physical stack mapping remains absent',
            constants=None, embedding=None),
        model_composition=dict(logical_state_bytes=logical,
            program_replicated_window_state_bytes=sum(kv) + sum(keys) + window * 96,
            window_memory_class=None, schedule_latency_ns=None, measured_service_cycles=None),
        candidate_weight_address_bound=dict(sector_bits=27, aperture_bytes=aperture,
            busiest_weight_stack_bytes=max(map(max, weights)),
            minimum_remaining_bytes=aperture - max(map(max, weights)),
            note='Remaining address range only; not available physical memory or a full-fit result'),
        actual_reservations_verdict='REFUSED', refusal_reason=refusal,
        missing=['sourced deployment encoding and consumer ownership for unclassified tensors',
                 'embedding replication/sharding and Engram deployment padding',
                 'KV/index/window per-stack placement and memory class',
                 'per-stack resident bases/extents and region namespace on actual transport',
                 'compressor/index/topk/collective/vector scratch and generated metadata allocations'],
        W19_handoff=dict(owner='Euler / actual accepted256 transport', inventory_commit='92528a5c19457b8389d7c2e9a21183cc82d9c6c9',
            acknowledgement=False, requested='Provide sourced per-stack deployment bounds and resident regions; then run stack_bound. AW27 gate is separately owned; no campaign duplicated.'),
        full_placement_qualified=False, headline_adoption=False,
        pins={p: sha(p) for p in paths})


def check(record):
    for path, digest in record['pins'].items():
        require(sha(path) == digest, 'pin drift: ' + path)
    fresh = build()
    fresh['base_commit'] = record['base_commit']
    require(fresh == record, 'resident bound receipt does not reproduce')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--out', type=Path)
    mode.add_argument('--check', type=Path)
    args = ap.parse_args()
    try:
        if args.check:
            check(json.loads(args.check.read_text()))
        else:
            data = build()
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open('x') as f:
                json.dump(data, f, indent=2, sort_keys=True)
                f.write('\n')
        print('PASS: W19 inventory bounds reproduce; actual resident allocations REFUSED pending sources')
    except (Refusal, FileExistsError) as exc:
        ap.exit(2, 'REFUSED: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
