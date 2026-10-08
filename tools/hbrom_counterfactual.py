#!/usr/bin/env python3
"""Default-off operand, segmented-job, and selected-KV scheduling sensitivities.

No result admits RTL or architectural adoption. Positive control/config costs are
assumptions; native RTL must prove x-state lifetime and segmented-source legality.
The unmodified G0 input and record are retained. Real DAG is scheduled anew.
"""
from __future__ import annotations
import argparse
import copy
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbrom_model as M


def is_gu(node):
    return node.get('kind') == 'weight' and '.ffn.experts_gu' in node.get('parent', '')


def concat_graph(nodes):
    """Coalesce same-K/format/activation jobs, retain every source segment.

    Global flat-row striping is explicitly forbidden: each segment retains its
    source rank/tile row ownership. Service uses SUM of per-segment tile ceilings.
    """
    out = copy.deepcopy(nodes)
    groups = {}
    for n in out:
        if is_gu(n):
            groups.setdefault(n['parent'], []).append(n)
    replacement, fused = {}, []
    for parent, jobs in groups.items():
        if len({(n['format'], n['k'], n['activation_bytes'], n.get('replicated', False)) for n in jobs}) != 1:
            raise ValueError('segmented GU requires identical activation/format/K/ownership mode')
        ids = {n['id'] for n in jobs}
        first = copy.deepcopy(jobs[0])
        first['id'] = parent + ':segmented_gu'
        first['deps'] = list(dict.fromkeys(d for n in jobs for d in n['deps'] if d not in ids))
        first['segments'] = jobs
        for field in ('rows', 'macs', 'weight_bytes', 'result_bytes'):
            first[field] = sum(n[field] for n in jobs)
        first['activation_bytes'] = jobs[0]['activation_bytes']
        for n in jobs:
            replacement[n['id']] = first['id']
        fused.append(first)
    out = [n for n in out if n['id'] not in replacement] + fused
    for n in out:
        n['deps'] = list(dict.fromkeys(replacement.get(d, d) for d in n.get('deps', [])))
    return out


def evaluate(inputs, candidate, mode):
    if mode not in ('operand_residency', 'segmented_gu', 'chained_kv'):
        raise ValueError('unknown counterfactual mode')
    altered = copy.deepcopy(inputs)
    if mode == 'chained_kv':
        import hbrom_floorplan
        extra_area = .25
        altered['physical']['fixed_service_mm2'] += extra_area
        fp = altered['physical_floorplan']
        fp['hub_service_area_mm2'] += extra_area
        fp['hub_um'][0] = math.ceil(fp['hub_service_area_mm2'] * 1e6 / fp['hub_um'][1])
        key = f"{candidate['pairs_per_tile']}:{candidate['tiles_per_cluster']}"
        altered['physical']['cluster_slots_by_geometry'][key] = hbrom_floorplan.placement_geometry(
            altered, candidate['pairs_per_tile'], candidate['tiles_per_cluster'])['slots']
        altered.setdefault('qualification_blockers', []).append('chained selected-KV slot and early transport exact/RTL/port/area gates missing')
        original_transport = M.hbrom_transport.reprice_nodes
        def chained(*args, **kwargs):
            return original_transport(*args, **kwargs, selected_kv_forwarding='chained')
        M.hbrom_transport.reprice_nodes = chained
        try:
            result = M.evaluate(altered, candidate)
        finally:
            M.hbrom_transport.reprice_nodes = original_transport
        result['counterfactual'] = dict(mode=mode, default_enabled=False,
            extra_area_mm2_per_die=extra_area, extra_sram_bytes_per_die=221184,
            storage_basis='27 whole256x256 SRAM macros: three9-bank groups,8 payload plus protection,256B/cycle ports; codec/mux/control allowance inside0.25mm2',
            scope='true selection/gather producer, finite immutable selected-row lease, explicit endpoint/edge/slot resources; query waits visibility',
            physical_floorplan=fp, adoption_allowed=False)
        return result
    # Extra source-held identity+DMR/seal controls and a protected descriptor
    # segment table. Positive proxy, not synthesized area or timing evidence.
    area_per_tile = .001 if mode == 'operand_residency' else .010
    altered['compute']['private_tile_area_mm2'] += area_per_tile
    altered['compute']['area_mm2'] += area_per_tile
    altered.setdefault('qualification_blockers', []).extend([
        mode + ': exact source/control/retained-x RTL gate missing',
        mode + ': area/control-cycle allowances not synthesized or routed',
        mode + ': changed tile rectangle not physically requalified'])
    if mode == 'segmented_gu':
        altered['baseline_dag'] = concat_graph(altered['baseline_dag'])
    original = M.weight_service

    def price(node, geom, compute, macro, network, tp):
        if not is_gu(node):
            return original(node, geom, compute, macro, network, tp)
        local = copy.deepcopy(node)
        if mode == 'segmented_gu':
            tiles = geom['clusters_per_die'] * geom['tiles_per_cluster']
            rows_per_tile = sum(math.ceil(math.ceil(n['rows'] / tp) / tiles) for n in node['segments'])
            # Represent the busiest tile with conservative padded equivalent
            # work, while keeping the original source work in the report.
            local['rows'] = rows_per_tile * tiles * tp
            local['weight_bytes'] = node['segments'][0]['weight_bytes'] / node['segments'][0]['rows'] * local['rows']
            local['result_bytes'] = local['rows'] * 4
            r = original(local, geom, compute, macro, network, tp)
            extra = 2 * len(node['segments'])
            r['cycles'] += extra
            r['duration_ns'] += extra / compute['clock_ghz']
            r.update(segments=len(node['segments']), aligned_owner_rows_per_tile=rows_per_tile,
                     source_actual_rows=node['rows'], source_actual_weight_bytes=node['weight_bytes'],
                     segmented_control_cycles=extra, source_format_mapping='retained per-segment ownership; never global-flat re-stripe')
            return r
        r = original(local, geom, compute, macro, network, tp)
        resident = node.get('selected_expert_slot', 0) != 0 or node.get('matrix_part', 0) != 0
        saved = r['input_cycles'] if resident else 0
        # Every job checks an immutable activation generation before launch.
        r['cycles'] += 1 - saved
        r['duration_ns'] += (1 - saved) / compute['clock_ghz']
        r['input_cycles'] = 0 if resident else r['input_cycles']
        r.update(retained_operand=resident, residency_guard_cycles=1, saved_reload_cycles=saved)
        return r
    M.weight_service = price
    try:
        result = M.evaluate(altered, candidate)
    finally:
        M.weight_service = original
    result['counterfactual'] = dict(mode=mode, default_enabled=False,
        extra_area_mm2_per_tile=area_per_tile,
        scope='same selected experts, exact chunk8 arithmetic and source row ownership; control/operand lifetime unproven',
        adoption_allowed=False)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    raw = a.inputs.read_bytes()
    if a.inputs.suffix == '.gz': raw = gzip.decompress(raw)
    inputs = json.loads(raw)
    baseline = json.loads(a.baseline.read_text())
    rows = []
    for mode in ('operand_residency', 'segmented_gu', 'chained_kv'):
        result = evaluate(inputs, baseline['candidate'], mode)
        if result.get('feasible'):
            result['rate_gain_pct'] = 100 * (baseline['tpot_us'] / result['tpot_us'] - 1)
            result['screen_gain_at_least_one_pct'] = result['rate_gain_pct'] >= 1
        rows.append(result)
    out = dict(schema='opentallas.hbrom.schedule_counterfactual.v1', default_enabled=False,
               baseline_tpot_us=baseline['tpot_us'], baseline_sha256=hashlib.sha256(a.baseline.read_bytes()).hexdigest(),
               inputs_sha256=hashlib.sha256(raw).hexdigest(), rows=rows,
               no_adoption='Analytical sensitivity only; no measured implementation, SS/FF or numerical gate')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2) + '\n')


if __name__ == '__main__':
    main()
