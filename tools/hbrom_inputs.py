#!/usr/bin/env python3
"""Normalize source-pinned HBROM contributions into a conditional model screen.

A complete released-checkpoint census is not a complete executable bank map.
Unknown implementation costs stay explicit assumptions and qualification blockers.
The default input directory is repository-owned; no /tmp artifacts are required.
"""
from __future__ import annotations
import argparse
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = ROOT / 'results/uarch/hbrom/inputs'
SCHEMA = 'opentallas.hbrom.inputs.v1'


def _read(directory, name):
    path = Path(directory) / f'hbrom-{name}.json'
    if not path.exists():
        path = path.with_suffix('.json.gz')
    raw = path.read_bytes()
    data = gzip.decompress(raw) if path.suffix == '.gz' else raw
    return json.loads(data), path, hashlib.sha256(raw).hexdigest()


def normalize_storage(inventory):
    """Retain ALL source bytes; inactive scopes only lose AR traffic, not capacity.

    Execution duplicates are additional. This avoids assuming source scale/wo_a
    payload deletion before an executable mapping proves exact reconstruction.
    """
    tensors, auxiliary = [], []
    totals = {'mandatory_ar_bytes': 0, 'optional_mtp_bytes': 0,
              'optional_vision_bytes': 0, 'execution_duplicate_bytes': 0}
    scope_key = {'mandatory_ar': 'mandatory_ar_bytes', 'mtp': 'optional_mtp_bytes',
                 'vision': 'optional_vision_bytes'}
    for source in inventory['tensors']:
        scope = source['scope']
        if scope not in scope_key:
            raise ValueError(f'unknown checkpoint scope {scope}')
        size = source['bytes']
        if size <= 0:
            raise ValueError('invalid tensor storage size')
        totals[scope_key[scope]] += size
        if scope != 'mandatory_ar' or source['kind'] == 'engram_table':
            auxiliary.append(dict(name=source['name'], bytes=size, scope=scope,
                                  kind=source['kind']))
            continue
        t = dict(name=source['name'], bytes=size, source_bytes=size,
                 scope=scope, format=source['format'], layer=source.get('layer'),
                 rows=source['rows'], k=source['k'],
                 packing_word_bytes=32, replicated=False)
        if source['kind'] in ('head', 'embedding'):
            t.update(layer=None, stage=source['kind'])
        elif t['layer'] is None:
            t['stage'] = 'head'  # final norm / HC coefficients, retained in head role
        t['replicated'] = ('hc_' in t['name'] or '.indexer.' in t['name'])
        tensors.append(t)
        # Existing BF16 wo_a execution requires full expansion, not native FP8 dot.
        if t['name'].endswith('.attn.wo_a.weight'):
            added = math.prod(source['shape']) * 2
            tensors.append(dict(t, name=t['name'] + ':execution_bf16', bytes=added,
                                source_bytes=0, format='bf16', execution_duplicate=True))
            totals['execution_duplicate_bytes'] += added
    source_sum = sum(totals[k] for k in scope_key.values())
    if source_sum != inventory['checkpoint_bytes']:
        raise ValueError('checkpoint census does not reconcile')
    aux_derived = sum(x['bytes'] for x in inventory['derived_auxiliary_payloads'])
    totals.update(checkpoint_bytes=source_sum, auxiliary_source_bytes=sum(t['bytes'] for t in auxiliary),
                  derived_auxiliary_bytes=aux_derived,
                  mandatory_traffic_scope='all40 layers+Engram/head; MTP/vision have capacity only',
                  implementation_configuration_complete=False,
                  inline_execution_scales='allocator records include perrow scales; archived source scale retained; no third scale copy')
    return tensors, auxiliary, totals


def normalize_dag(record):
    """Split mixed formats into finite serial jobs while preserving original joins.

    Dedicated FP32 HC projection remains a priced separate unit, since the HBM
    shared matrix tile has no FP32 matrix mode. Original resource-order edges
    remain conservative; replacing them requires a verified alternate calendar.
    """
    nodes, unknowns = [], []
    for old in record['nodes']:
        n = copy.deepcopy(old)
        layer = n['layer']
        if n['id'].startswith('head.'):
            n.update(layer=None, stage='head')
        elif n['id'] in ('embed', 'token'):
            n.update(layer=None, stage='embedding')
        elif n['id'] == 'token.return':
            n.update(layer=None, stage='head')
        scope = n.get('stage', f'layer_{layer}')
        if n['kind'] != 'weight' or n['format'] == 'fp32':
            if n.get('unknown'):
                unknowns.append(n['id'])
            if n['kind'] == 'weight':
                n['kind'] = 'dedicated_fp32'
                n['resources'] = [scope + ':he']
                n['retained_latency_basis'] = 'existing dedicated HE; shared tile has no FP32 matrix mode'
            elif n['kind'] in ('vector', 'reduce', 'select'):
                n['resources'] = [scope + ':su']
            elif n['kind'] == 'sinkhorn':
                n['resources'] = [scope + ':sinkhorn']
            elif n['kind'] in ('kvscan', 'load'):
                n['resources'] = [scope + ':attention_service']
            elif n['kind'] in ('hop', 'collective'):
                n['resources'] = [scope + ':link']
            else:
                n['resources'] = []
            nodes.append(n)
            continue
        previous = None
        for i, c in enumerate(n['components']):
            name = n['id'] + f':component{i}'
            repeat = c.get('repeat', 1)
            node = dict(id=name, deps=[previous] if previous else list(n['deps']),
                        kind='weight', layer=n['layer'], format=c['format'],
                        rows=c['rows'] * repeat, k=c['k'], macs=c['macs'],
                        weight_bytes=c['weight_bytes'],
                        activation_bytes=c['activation_bytes'] * c.get('groups', 1),
                        result_bytes=c['result_bytes'], replicated=c.get('replicated_on_TP_ranks', False),
                        duration_ns=None, resources=[], logical_component=c,
                        parent=n['id'], unknown=True,
                        activation_group_policy='all distinct grouped operands charged; per-rank subset requires mapping proof')
            if 'stage' in n:
                node['stage'] = n['stage']
            nodes.append(node)
            previous = name
        nodes.append(dict(id=n['id'], deps=[previous], kind='join', layer=n['layer'],
                          duration_ns=0, resources=[], parent_components=True))
    ids = {n['id'] for n in nodes}
    if len(ids) != len(nodes) or any(d not in ids for n in nodes for d in n['deps']):
        raise ValueError('duplicate node or missing dependency after component expansion')
    return nodes, unknowns


def build_inputs(input_dir=None, *, max_logic_dies=368):
    directory = Path(input_dir) if input_dir is not None else DEFAULT_INPUT_DIR
    records, pins = {}, {}
    for name in ('inventory', 'dag', 'rom-macros', 'compute', 'weight-network',
                 'floorplan', 'power', 'hub', 'config', 'clock'):
        records[name], path, digest = _read(directory, name)
        pins[path.name] = digest
    inv, rom, comp, net, floor = (records[k] for k in
                                ('inventory', 'rom-macros', 'compute', 'weight-network', 'floorplan'))
    tensors, auxiliary, storage = normalize_storage(inv)
    dag, unknown_nodes = normalize_dag(records['dag'])
    macro_area = floor['macro_views']['ot_rom_4096x274_m8']['area_mm2']
    macro = dict(area_mm2=macro_area, conservative_pair_capacity_bytes=262144,
                 payload_Bpc={'fp4':34, 'fp8':33, 'bf16':32, 'fp32':32},
                 capture_cycles=rom['service']['rom_issue_to_captured_word_pipeline_cycles'],
                 capture_area_per_pair_mm2=2 * rom['service']['capture_bare_DFF_area_um2_per_stream']/1e6,
                 source='site-snapped v2 area; conservative256bit capacity; two alternating4096-row macros',
                 capture_area_status='2x bare capture DFF placement allowance; not routed measurement')
    compute = dict(area_mm2=comp['area_mm2'], local_sram_bytes=229376,
                   private_tile_area_mm2=0.334465594474, shared_service_area_mm2=0.984012854014,
                   shared_sram_bytes=589824,
                   sharing_status='source NC1 partition: private x+staging+matrix, shared mirroredRF+scratch+SIMD; protection/control excluded',
                   macs_per_cycle={k:v for k,v in comp['macs_per_cycle_batch1'].items() if v>0},
                   weight_ingress_Bpc=comp['ingress_Bpc'],
                   activation_load_Bpc=comp['activation_external_write_Bpc'], result_Bpc=comp['result_Bpc'],
                   pipeline_cycles=comp['pipeline_cycles']['conservative_drain_budget'],
                   golden_recurrence_cycles={'fp4':64,'fp8':64,'bf16':64},
                   clock_ghz=comp['frequency_ghz'],
                   arithmetic_mode='chunk8', descriptor_cycles=9,
                   area_status=comp['area_scope'],
                   recurrence_status='8 slots x8 cycles allowance; exact K-dependent chunk/tree must be model priced')
    networks = {}
    for row in net['candidates']:
        pairs = row['pairs_per_tile']
        # includes channels, captures/mux/credit SRAM; ROM cells counted separately.
        networks[str(pairs)] = dict(area_mm2=row['network_plus_rom_mm2_proxy']-row['rom_macro_mm2'],
             output_streams_per_tile=4, usable_weight_Bpc=136,
             latency_cycles=row['packed_response_latency_cycles']-macro['capture_cycles'],
             tracks_needed=row['trunk_tracks_need'], tracks_available=row['trunk_tracks_capacity'],
             leaf_tracks_needed=row['leaf_tracks_need'], leaf_tracks_available=row['leaf_tracks_capacity'],
             credit_depth_beats=row['credit_depth_beats'], fifo_beats=128,
             source_status='positive geometry/mux/clock/protection allowance screen, not physical evidence')
    physical = dict(die_mm2=floor['die']['area_mm2'], fixed_service_mm2=100,
                    cluster_packing_fraction=.8, auxiliary_fixed_mm2=100,
                    auxiliary_rom_packing_fraction=.75, activation_root_Bpc=256,
                    activation_broadcast_cycles=8, result_root_Bpc=256,
                    fixed_service_status='assumed100mm2 incl38.601mm2 SU+VM minimum,HE,attention,index,PHY; rectangle fit unproven',
                    cluster_packing_status='assumed80% after explicit local network channel footprint',
                    auxiliary_status='assumed100mm2 service plus75% ROM packing; archive lookup network unqualified',
                    activation_status='256B/cycle root plus8cycle fanout allowance; tree dimension must be checked')
    # Known global matrix templates plus a positive reserve for uncompiled commands.
    config_bytes = 65536 * 42
    storage['implementation_configuration_reserve_bytes'] = config_bytes
    blockers = ['analytical screen only; full shared tile exactness and physical closure absent',
                'incomplete executable bank allocation and row/scale/chunk mapping',
                'configuration reserve is assumed; vector/SFU/service program not compiled',
                'fixed service rectangles, SRAM protection and clock distribution unqualified',
                'nonweight measurements inherited from TP4 S81; new service placement unqualified',
                'all gated domains wake/residency and power unqualified',
                'macro timing is analytical not transistor characterized',
                f'{len(unknown_nodes)} inherited nonweight durations lack direct measurement attribution',
                'retained sequential legacy field-resource edges may overestimate shared-compute path',
                'FP32 dedicated HC exact recurrence and dedicated reservation need contextual validation',
                'sharedRF/SIMD arbitration and mutable SRAM protection area/latency remain unimplemented']
    return dict(schema=SCHEMA, default_enabled=False, source_pins=pins,
                supported_tp=[4], max_logic_dies=max_logic_dies,
                macro=macro, compute=compute, networks=networks, physical=physical,
                tensors=tensors, auxiliary_storage_bytes=storage['auxiliary_source_bytes']+storage['derived_auxiliary_bytes']+config_bytes,
                auxiliary_storage=auxiliary, storage_scopes=storage, dag=dag,
                full_checkpoint_bytes=inv['checkpoint_bytes'],
                complete_checkpoint=inv['complete_checkpoint'], dag_complete=True,
                implementation_configuration_complete=False,
                unknown_nonweight_nodes=unknown_nodes,
                historical_extra_hops=dict(count=records['dag']['baseline_extra_hops'],
                                            ns=records['dag']['baseline_extra_hop_ns'],
                                            policy='old layout only; new topology must reprice placement crossings'),
                sweep=dict(tp=[4],pairs_per_tile=[64,128,256,512,1024],tiles_per_cluster=[1,2,4,8],layers_per_stage=[1,2,4]),
                topology=dict(kind='TP4 groups with direct interstage links; source sharing retained',
                              inherited_hops='S81 DAG hops retained conservatively; not new placement proof'),
                qualification_blockers=blockers, gates={},
                power=dict(total_W=None, reason='new cluster clock/mux/PHY power unknown; never zero',
                           primitives=records['power']['primitives'], qualified=False),
                assumptions=[physical['fixed_service_status'],physical['cluster_packing_status'],
                             physical['auxiliary_status'],physical['activation_status'],
                             compute['area_status'],compute['recurrence_status']])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,default=DEFAULT_INPUT_DIR)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--max-logic-dies',type=int,default=368)
    args=parser.parse_args()
    record=build_inputs(args.input_dir,max_logic_dies=args.max_logic_dies)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(record,indent=2)+'\n')

if __name__=='__main__':
    main()
