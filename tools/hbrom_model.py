#!/usr/bin/env python3
"""Default-off clustered ROM/shared exact compute analytical screen.

All bytes refer to stored payload (scales included), MAC counts are batch-one.
Inputs use opentallas.hbrom.inputs.v1. Unknown inputs fail closed; conditional
screen feasibility is deliberately distinct from physical/adoption qualification.
Run --inputs INPUT.json --out OUTPUT.json. No RTL or physical jobs are launched.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import gzip
import itertools
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbrom_allocator
import hbrom_transport

SCHEMA = 'opentallas.hbrom.inputs.v1'


def ceildiv(a, b):
    if b <= 0 or a < 0:
        raise ValueError('nonnegative work and positive capacity required')
    return math.ceil(a / b)


def positive(record, name):
    value = record.get(name)
    if not isinstance(value, (float, int)) or isinstance(value, bool) or value <= 0 or not math.isfinite(value):
        raise ValueError(f'missing or invalid positive input: {name}')
    return value


def positive_integer(record, name):
    value = positive(record, name)
    if int(value) != value:
        raise ValueError(f'integer required: {name}')
    return int(value)


def source_pins(paths, root):
    out = {}
    for path in paths:
        file = Path(path)
        if not file.is_absolute():
            file = Path(root) / file
        out[str(path)] = hashlib.sha256(file.read_bytes()).hexdigest()
    return out


def pack_stage(tensors, tp, pairs_per_cluster, clusters_per_die, payload_bytes_per_pair):
    """Whole-tensor shards rounded independently; no aggregate-capacity shortcut.

    Each tensor shard stripes across all clusters, then across all pairs in its
    cluster. Independent allocation is conservative (no subword alias packing).
    A stage is one TP group; exceeding its local capacity rejects the candidate.
    """
    # Assign complete rows to rank then tile; per-row word tails are explicit.
    # No row is fractionally striped across tiles. Each tile's four read lanes
    # stripe a row's words; successive row stripes rotate through storage groups.
    capacity = pairs_per_cluster * payload_bytes_per_pair
    occupancy = [0] * clusters_per_die
    useful = 0
    padded = 0
    tensor_rows = []
    cursor = 0
    for t in tensors:
        size = positive(t, 'bytes')
        replicas = t.get('replicas_per_rank', 1)
        rows = int(t.get('rows') or 1)
        word_bytes = t.get('packing_word_bytes', 32)
        row_bytes = ceildiv(size, rows)
        rank_rows = rows if t.get('replicated', False) else ceildiv(rows, tp)
        row_alloc = ceildiv(row_bytes, word_bytes) * word_bytes
        quotient, remainder = divmod(rank_rows * replicas, clusters_per_die)
        for tile in range(clusters_per_die):
            local_rows = quotient + int((tile - cursor) % clusters_per_die < remainder)
            occupancy[tile] += local_rows * row_alloc
        cursor = (cursor + remainder) % clusters_per_die
        useful += rank_rows * row_bytes * replicas
        allocated = rank_rows * row_alloc * replicas
        padded += allocated
        tensor_rows.append(dict(name=t['name'], rank_rows=rank_rows,
                                full_row_bytes=row_bytes, allocated_bytes=allocated))
    return dict(fits=max(occupancy, default=0) <= capacity,
                useful_bytes_per_rank=useful, allocated_bytes_per_rank=padded,
                capacity_bytes_per_rank=capacity * clusters_per_die,
                max_cluster_bytes=max(occupancy, default=0), tensors=tensor_rows,
                mapping='whole rows; cyclic tile owner; four-lane row-word stripe; storage groups rotate')


def storage_record_lower_bound(tensors, tp):
    """Necessary capacity screen only; admitted rows still run full allocator."""
    records = 0
    for t in tensors:
        fmt = hbrom_allocator.normalize_format(t.get('format', 'raw'))
        k = int(t.get('k') or 0)
        if fmt in ('fp4', 'fp8', 'bf16') and k > 1 and not t.get('is_scale') and not t['name'].endswith('.scale'):
            records_per_row = hbrom_allocator.row_geometry(fmt, k)['records_per_row']
            count = int(t.get('rows') or 1) * records_per_row
        else:
            count = ceildiv(int(t['bytes']), 128)
        records += count * t.get('replicas_per_rank', 1) * (tp if t.get('replicated') else 1)
    return ceildiv(records, tp)


def schedule(nodes):
    """Deterministic finite-resource list schedule, whole-job reservation.

    Only deps permit overlap. Resources are explicit, exclusive service domains.
    Nodes sharing a compute/port resource serialize even when DAG-independent.
    No implicit unlimited-engine overlap or zero-time unknown node is allowed.
    """
    by_id = {n['id']: n for n in nodes}
    if len(by_id) != len(nodes):
        raise ValueError('duplicate node id')
    pending = dict(by_id)
    children = {name: [] for name in by_id}
    indegree = {}
    for name, node in by_id.items():
        deps = node.get('deps', [])
        indegree[name] = len(deps)
        for dep in deps:
            if dep not in children:
                raise ValueError('cyclic graph or missing dependency')
            children[dep].append(name)
    ready = [n for n in nodes if indegree[n['id']] == 0]
    result = {}
    free = {}
    owner = {}
    while pending:
        if not ready:
            raise ValueError('cyclic graph or missing dependency')
        def earliest(n):
            return max([result[d]['finish_ns'] for d in n.get('deps', [])]
                       + [free.get(r, 0) for r in n.get('resources', [])] + [0])
        n = min(ready, key=lambda n: (earliest(n), n['id']))
        duration = n.get('duration_ns')
        if duration is None or not math.isfinite(duration) or duration < 0:
            raise ValueError(f"unknown duration for {n['id']}")
        start = earliest(n)
        predecessors = [(result[d]['finish_ns'], d) for d in n.get('deps', [])]
        predecessors += [(free.get(r, 0), owner.get(r)) for r in n.get('resources', [])]
        pred = max(predecessors, default=(0, None), key=lambda x: x[0])[1]
        result[n['id']] = dict(start_ns=start, finish_ns=start + duration,
                              duration_ns=duration, predecessor=pred,
                              resources=n.get('resources', []), kind=n.get('kind'))
        for r in n.get('resources', []):
            free[r] = start + duration
            owner[r] = n['id']
        del pending[n['id']]
        ready.remove(n)
        for child in children[n['id']]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(by_id[child])
    nonterminal = {d for n in nodes for d in n.get('deps', [])}
    terminal = max((k for k in result if k not in nonterminal),
                   key=lambda k: result[k]['finish_ns'], default=None)
    path = []
    ptr = terminal
    while ptr is not None:
        path.append(ptr)
        ptr = result[ptr]['predecessor']
    return dict(tpot_ns=result[terminal]['finish_ns'] if terminal else 0,
                critical_path=list(reversed(path)), nodes=result,
                policy='earliest-ready lexical tie; whole-job exclusive resource reservation')


def weight_service(node, geom, compute, macro, network, tp):
    """Prices each row at its resident cluster, including finite operand ports.

    No unproven cross-cluster K split. Full rows distributed over local tiles;
    expert multiplicity is included in rows. Golden recurrence bound is provided
    by the compute input, never inferred from aggregate MAC throughput.
    """
    fmt = node['format']
    mac_rate = positive(compute['macs_per_cycle'], fmt)
    rows = ceildiv(positive(node, 'rows'), tp) if not node.get('replicated') else node['rows']
    k = positive(node, 'k')
    tiles = geom['clusters_per_die'] * geom['tiles_per_cluster']
    active = min(rows, tiles)
    row_batches = ceildiv(rows, active)
    row_bytes = positive(node, 'weight_bytes') / positive(node, 'rows')
    rom_Bpc = positive(macro['payload_Bpc'], fmt) * network['output_streams_per_tile']
    weight_Bpc = min(rom_Bpc, positive(compute, 'weight_ingress_Bpc'),
                     positive(network, 'usable_weight_Bpc'))
    chunk = 8 if fmt == 'bf16' else 256
    chunks = ceildiv(k, chunk)
    padded_chunks = 1 << (chunks - 1).bit_length()
    lanes = int(mac_rate) if fmt == 'bf16' else int(mac_rate // 32)
    groups = ceildiv(chunks, lanes)
    padded_k = groups * lanes * chunk
    il = int(compute.get('accumulator_slots', 8))
    # Group slots interleave chunks; tail rounds still occupy full IL calendar.
    compute_cycles = ceildiv(row_batches * groups, il) * il * 8
    # Banks holding one row cannot supply more streams than its stored words.
    resident_streams = min(network['output_streams_per_tile'], max(1, ceildiv(row_bytes, macro['payload_Bpc'][fmt])))
    resident_Bpc = min(weight_Bpc, resident_streams * macro['payload_Bpc'][fmt])
    source_request_cycles = row_batches * groups * 8 + (7 if (row_batches * groups) % 2 else 0)
    weight_cycles = max(row_batches * ceildiv(row_bytes, resident_Bpc), source_request_cycles)
    activation_bytes = positive(node, 'activation_bytes')
    input_cycles = max(ceildiv(activation_bytes, positive(compute, 'activation_load_Bpc')),
                       ceildiv(activation_bytes, positive(geom, 'activation_root_Bpc')))
    input_cycles += geom['activation_broadcast_cycles']
    result_bytes = node.get('result_bytes', rows * 4)
    rank_result_bytes = result_bytes / tp if not node.get('replicated') else result_bytes
    output_cycles = max(ceildiv(rank_result_bytes, positive(compute, 'result_Bpc') * active),
                        ceildiv(rank_result_bytes, geom['result_root_Bpc']))
    # Chunk recurrence runs independently per row; constituent golden additions
    # must still be performed, even when row issue is smaller than recurrence.
    recurrence = compute['golden_recurrence_cycles'].get(fmt)
    if recurrence is None:
        raise ValueError(f'missing recurrence for {fmt}')
    issue = max(compute_cycles, weight_cycles, output_cycles)
    pipeline = positive(compute, 'pipeline_cycles') + positive(network, 'latency_cycles') + positive(macro, 'capture_cycles')
    cycles = input_cycles + max(issue, recurrence) + pipeline + compute.get('descriptor_cycles', 9)
    ghz = positive(compute, 'clock_ghz')
    return dict(duration_ns=cycles / ghz, cycles=cycles, active_tiles=active,
                macs_per_cycle_active=active * mac_rate,
                macs_per_cycle_installed=tiles * mac_rate,
                weight_bytes_per_cycle_active=active * resident_Bpc,
                activation_bytes_per_cycle_per_tile=compute['activation_load_Bpc'],
                result_bytes_per_cycle_per_tile=compute['result_Bpc'],
                compute_cycles=compute_cycles, weight_cycles=weight_cycles,
                source_request_cycles_upper=source_request_cycles,
                input_cycles=input_cycles, output_cycles=output_cycles,
                recurrence_cycles=recurrence, pipeline_cycles=pipeline,
                compute_intensity_MAC_per_weight_byte=k / row_bytes,
                padded_k=padded_k, descriptor_cycles=compute.get('descriptor_cycles', 9),
                mapping='whole output rows striped over tiles; ceil chunk groups; final lane padding, stack internal tree zeros; no K reassociation')


def evaluate(inputs, candidate):
    if inputs.get('schema') != SCHEMA:
        raise ValueError('wrong input schema')
    macro, compute, physical = (inputs[k] for k in ('macro', 'compute', 'physical'))
    tp = positive_integer(candidate, 'tp')
    if tp not in inputs['supported_tp']:
        raise ValueError('TP unsupported by supplied DAG/exactness evidence')
    pairs = positive_integer(candidate, 'pairs_per_tile')
    ntiles = positive_integer(candidate, 'tiles_per_cluster')
    network = inputs['networks'][str(pairs)]
    die_area = positive(physical, 'die_mm2')
    fixed_area = positive(physical, 'fixed_service_mm2')
    if fixed_area >= die_area or not 0 < physical.get('cluster_packing_fraction', 0) <= 1:
        raise ValueError('invalid physical area/fraction envelope')
    pair_area = 2 * positive(macro, 'area_mm2')
    tile_area = positive(compute, 'area_mm2')
    # Compute area includes its local SRAM; network includes capture and mux.
    shared_area = compute.get('shared_service_area_mm2', 0)
    if shared_area:
        tile_area = positive(compute, 'private_tile_area_mm2')
    cluster_area = ntiles * (pairs * pair_area + tile_area + positive(network, 'area_mm2')) + shared_area
    cluster_slot_area = cluster_area / positive(physical, 'cluster_packing_fraction')
    count = math.floor((die_area - fixed_area) / cluster_slot_area)
    geometry_slot_limit = physical.get('cluster_slots_by_geometry', {}).get(f'{pairs}:{ntiles}')
    if geometry_slot_limit is not None:
        count = min(count, int(geometry_slot_limit))
    if physical.get('max_cluster_slots') is not None:
        count = min(count, int(physical['max_cluster_slots']))
    if count < 1:
        return dict(candidate=candidate, feasible=False, rejection=['no cluster fits'])
    geom = dict(clusters_per_die=count, tiles_per_cluster=ntiles,
                pairs_per_cluster=pairs * ntiles, cluster_area_mm2=cluster_area,
                cluster_slot_mm2=cluster_slot_area,
                per_die_area_mm2=fixed_area + count * cluster_slot_area,
                compute_mm2_per_die=count * (ntiles * tile_area + shared_area),
                shared_service_mm2_per_cluster=shared_area,
                rom_mm2_per_die=count * pairs * ntiles * pair_area,
                network_mm2_per_die=count * ntiles * network['area_mm2'],
                local_sram_bytes_per_die=count * (ntiles * positive(compute, 'local_sram_bytes') + compute.get('shared_sram_bytes', 0)),
                activation_root_Bpc=positive(physical, 'activation_root_Bpc'),
                result_root_Bpc=positive(physical, 'result_root_Bpc'),
                activation_broadcast_cycles=max(positive(physical, 'activation_broadcast_cycles'), math.ceil(math.log2(count * ntiles + 1))))
    # Stage assignment is explicit, with actual integer capacity per rank.
    layers_per_stage = positive_integer(candidate, 'layers_per_stage')
    stages = {}
    for t in inputs['tensors']:
        if t.get('layer') is not None and int(t['layer']) >= 0:
            stage = f"layer_{int(t['layer']) // layers_per_stage}"
        else:
            stage = t.get('stage', 'auxiliary')
        stages.setdefault(stage, []).append(t)
    geometry_by_stage = {name: geom for name in stages}
    roles_by_stage = {}
    role_config = inputs.get('roles_config') if candidate.get('role_specific', False) else None
    if candidate.get('role_specific', False) and role_config is None:
        raise ValueError('role-specific candidate requires explicit roles_config')
    if role_config is not None:
        if layers_per_stage != role_config['layers_per_stage']:
            raise ValueError('role ledger not composed for this layers_per_stage')
        geometry_by_stage = {}
        for stage in stages:
            role = role_config['stage_roles'][stage]
            definition = role_config['roles'][role]
            role_physical = definition['physical']
            role_fixed = positive(role_physical, 'fixed_service_mm2')
            role_slots = role_physical['cluster_slots_by_geometry'][f'{pairs}:{ntiles}']
            role_count = min(math.floor((die_area-role_fixed)/cluster_slot_area), int(role_slots))
            if role_count < 1:
                raise ValueError(f'no cluster fits service role {role}')
            role_stacks = role_physical['hbm_stacks_per_compute_die']
            if isinstance(role_stacks,bool) or not isinstance(role_stacks,int) or role_stacks<0:
                raise ValueError('explicit nonnegative integer HBM stack inventory required')
            rg = dict(geom)
            rg.update(clusters_per_die=role_count, role=role, fixed_service_mm2=role_fixed,
                per_die_area_mm2=role_fixed+role_count*cluster_slot_area,
                compute_mm2_per_die=role_count*(ntiles*tile_area+shared_area),
                rom_mm2_per_die=role_count*pairs*ntiles*pair_area,
                network_mm2_per_die=role_count*ntiles*network['area_mm2'],
                local_sram_bytes_per_die=role_count*(ntiles*positive(compute,'local_sram_bytes')+compute.get('shared_sram_bytes',0)),
                activation_broadcast_cycles=max(positive(physical,'activation_broadcast_cycles'),math.ceil(math.log2(role_count*ntiles+1))),
                physical_floorplan=definition['physical_floorplan'],
                hbm_stacks_per_compute_die=role_stacks)
            geometry_by_stage[stage] = rg
            roles_by_stage[stage] = role
        # Compatibility summary is the most compute-constrained installed stage;
        # all timing and capacity below use the actual individual stage geometry.
        geom = min(geometry_by_stage.values(), key=lambda g:g['clusters_per_die'])
    packed = {}
    for name, ts in stages.items():
        stage_count = geometry_by_stage[name]['clusters_per_die']
        rank_capacity_records = (pairs // 4) * 8192 * stage_count * ntiles
        bound = storage_record_lower_bound(ts, tp)
        if bound > rank_capacity_records:
            packed[name] = dict(fits=False, necessary_records_per_rank=bound,
                                capacity_records_per_rank=rank_capacity_records,
                                rejection='aggregate native-record lower bound already exceeds capacity')
        else:
            packed[name] = hbrom_allocator.allocate(ts, tp, stage_count * ntiles, pairs,
                emit_runs=False, emit_summaries=False, layout_mode=candidate.get('layout_mode', 'padded'))
    rejection = []
    if any(not p['fits'] for p in packed.values()):
        rejection.append('stage storage exceeds integer cluster capacity')
    if network.get('tracks_needed', math.inf) > network.get('tracks_available', -1):
        rejection.append('cluster routing channel exceeds track capacity')
    auxiliary_bytes = inputs.get('auxiliary_storage_bytes', 0)
    auxiliary = dict(bytes=auxiliary_bytes, dies=0)
    if auxiliary_bytes:
        aux_pair_area = pair_area + positive(macro, 'capture_area_per_pair_mm2')
        aux_pairs = math.floor((die_area - positive(physical, 'auxiliary_fixed_mm2')) *
                              positive(physical, 'auxiliary_rom_packing_fraction') / aux_pair_area)
        aux_capacity = aux_pairs * positive(macro, 'conservative_pair_capacity_bytes')
        auxiliary.update(pairs_per_die=aux_pairs, bytes_per_die=aux_capacity,
                         dies=ceildiv(auxiliary_bytes, aux_capacity),
                         role='storage-only retained tables and inactive checkpoint payload')
    dies = len(stages) * tp + auxiliary['dies'] + inputs.get('additional_service_dies', 0)
    installed_units = dict(
        compute_tiles=sum(g['clusters_per_die']*ntiles for g in geometry_by_stage.values())*tp,
        compute_role_rom_macros=sum(g['clusters_per_die']*ntiles*pairs*2 for g in geometry_by_stage.values())*tp,
        archive_rom_macros=auxiliary.get('pairs_per_die',0)*2*auxiliary['dies'],
        tile_sram_bytes=sum(g['local_sram_bytes_per_die'] for g in geometry_by_stage.values())*tp,
        compute_role_occupied_area_mm2=sum(g['per_die_area_mm2'] for g in geometry_by_stage.values())*tp,
        logic_die_outline_area_mm2=dies*die_area,
        role_die_counts={r:sum(role==r for role in roles_by_stage.values())*tp for r in sorted(set(roles_by_stage.values()))})
    stacks_per_compute = physical.get('hbm_stacks_per_compute_die')
    hbm_stacks = (sum(g['hbm_stacks_per_compute_die'] for g in geometry_by_stage.values())*tp
                  if role_config is not None else
                  None if stacks_per_compute is None else len(stages)*tp*stacks_per_compute)
    dram_per_stack = physical.get('hbm_dram_dies_per_stack')
    base_per_stack = physical.get('hbm_base_dies_per_stack')
    dram_dies = None if hbm_stacks is None or dram_per_stack is None else hbm_stacks * dram_per_stack
    base_dies = None if hbm_stacks is None or base_per_stack is None else hbm_stacks * base_per_stack
    memory_inventory = dict(hbm_stacks=hbm_stacks, dram_dies=dram_dies, hbm_base_dies=base_dies,
        total_physical_dies=None if dram_dies is None or base_dies is None else dies + dram_dies + base_dies,
        basis=physical.get('hbm_inventory_basis', physical.get('hbm_stack_basis', 'unqualified stack construction assumption')),
        hbm_dram_area_mm2=None, total_silicon_area_mm2=None,
        area_status='HBM DRAM/base actual die areas missing; no iso-total-silicon claim')
    if dies > inputs['max_logic_dies']:
        rejection.append('logic die envelope exceeded')
    if rejection:
        return dict(candidate=candidate, feasible=False, rejection=rejection,
                    geometry=geom, geometry_by_stage=geometry_by_stage, roles_by_stage=roles_by_stage, storage=packed,
                    topology=dict(tp=tp, stages=list(stages), logic_dies=dies,
                                  auxiliary=auxiliary, memory_inventory=memory_inventory, installed_units=installed_units, layers_per_stage=layers_per_stage),
                    qualified=False, default_enabled=False)
    nodes = (hbrom_transport.reprice_nodes(inputs['baseline_dag'], tp, layers_per_stage)
             if 'baseline_dag' in inputs else
             copy.deepcopy(inputs.get('dag_by_tp', {}).get(str(tp), inputs['dag'])))
    if tp != 4 and 'baseline_dag' not in inputs and str(tp) not in inputs.get('dag_by_tp', {}):
        raise ValueError('non-TP4 candidate requires explicit per-TP communication/service DAG')
    services = {}
    for node in nodes:
        if node.get('layer') is not None and 0 <= int(node['layer']) < 40:
            layer = int(node['layer'])
            node['resources'] = [re.sub(r'^stage([0-9]+):', r'layer_\1:',
                                 r.replace(f'layer_{layer}:', f'layer_{layer // layers_per_stage}:'))
                                 for r in node.get('resources', [])]
        if node.get('kind') == 'weight':
            stage = f"layer_{int(node['layer']) // layers_per_stage}" if node.get('layer') is not None and int(node['layer']) >= 0 else node.get('stage', 'auxiliary')
            if stage not in geometry_by_stage:
                raise ValueError(f'weight node {node["id"]} has no resident stage {stage}')
            service = weight_service(node, geometry_by_stage[stage], compute, macro, network, tp)
            service['resident_stage'] = stage
            service['clusters_in_resident_stage'] = geometry_by_stage[stage]['clusters_per_die']
            node['duration_ns'] = service['duration_ns']
            services[node['id']] = service
            stage = f"layer_{int(node['layer']) // layers_per_stage}" if node.get('layer') is not None and int(node['layer']) >= 0 else node.get('stage', 'auxiliary')
            # All weight operations on a stage share its actual arithmetic.
            node.setdefault('resources', []).append(stage + ':compute')
    scheduled = schedule(nodes)
    blockers = list(inputs.get('qualification_blockers', []))
    for gate in ('exact', 'ss_setup', 'ff_hold', 'in_context_route', 'power', 'gain'):
        if inputs.get('gates', {}).get(gate) is not True:
            blockers.append(gate + ' not qualified')
    if role_config is not None:
        blockers.append('role-specific service/PHY geometry and source transport not contextually qualified')
    if shared_area:
        blockers.append('cluster-shared RF/vector service requires finite port implementation gate')
    if inputs.get('auxiliary_storage_bytes', 0):
        blockers.append('auxiliary storage placement/read network provisional')
    if 'baseline_dag' in inputs:
        blockers.append('own row-ownership transport DAG is analytical, not measured integration')
    elif layers_per_stage != 1:
        blockers.append('legacy transport DAG retained; stage-local hop removal not credited')
    if inputs.get('complete_checkpoint') is not True:
        blockers.append('complete storage census unverified')
    if not inputs.get('dag_complete', False):
        blockers.append('full token dependency DAG unverified')
    return dict(candidate=candidate, feasible=not rejection, rejection=rejection,
                geometry=geom, geometry_by_stage=geometry_by_stage, roles_by_stage=roles_by_stage, topology=dict(tp=tp, stages=list(stages),
                logic_dies=dies, auxiliary=auxiliary, memory_inventory=memory_inventory, installed_units=installed_units, layers_per_stage=layers_per_stage,
                links=inputs.get('topology', {})), storage=packed,
                service=services, schedule=scheduled,
                tpot_us=scheduled['tpot_ns'] / 1000,
                qualification_blockers=sorted(set(blockers)),
                qualified=not rejection and not blockers, default_enabled=False,
                power=inputs.get('power', {'total_W': None,
                    'reason': 'unknown power cannot be zero or qualify'}))


def sweep(inputs):
    axes = inputs['sweep']
    rows = []
    for tp, pairs, tiles, layers in itertools.product(axes['tp'], axes['pairs_per_tile'], axes['tiles_per_cluster'], axes['layers_per_stage']):
        candidate = dict(tp=tp, pairs_per_tile=pairs, tiles_per_cluster=tiles, layers_per_stage=layers)
        try:
            rows.append(evaluate(inputs, candidate))
        except (ValueError, KeyError) as error:
            rows.append(dict(candidate=candidate, feasible=False, rejection=[str(error)]))
    feasible = [r for r in rows if r['feasible']]
    best = min(feasible, key=lambda r: (r['tpot_us'], r['topology']['logic_dies']), default=None)
    # Do not replicate 100k tensor allocation rows in every sweep result.
    summaries = []
    for r in rows:
        compact = {k: v for k, v in r.items() if k not in ('schedule', 'service', 'storage')}
        if 'storage' in r:
            compact['storage'] = {s: {k: v for k, v in p.items() if k != 'tensors'} for s, p in r['storage'].items()}
        summaries.append(compact)
    return dict(schema='opentallas.hbrom.sweep.v1', default_enabled=False,
                selection='minimum conditional TPOT within explicit die/capacity/track envelope',
                source_pins=inputs.get('source_pins', {}), candidates=summaries,
                best=best, qualified=bool(best and best['qualified']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    raw = args.inputs.read_bytes()
    if args.inputs.suffix == '.gz':
        raw = gzip.decompress(raw)
    result = sweep(json.loads(raw))
    result['inputs_sha256'] = hashlib.sha256(raw).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
