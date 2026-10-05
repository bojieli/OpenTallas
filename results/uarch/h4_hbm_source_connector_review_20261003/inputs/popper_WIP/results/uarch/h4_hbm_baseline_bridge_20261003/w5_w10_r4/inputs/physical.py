#!/usr/bin/env python3
"""Concrete Qwen provider references; no arithmetic executor or timing oracle."""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

from qwen_hbm_reverse_spill_model_r16 import model as spill_model

ROOT = Path(__file__).resolve().parents[1]
PIN = '400d3d0c0f9caaf5e16392b71da21d6a135d3a6d'


def load(path, pins):
    raw = subprocess.check_output(['git', 'show', PIN + ':' + path], cwd=ROOT)
    pins.append({'commit': PIN, 'path': path, 'sha256': hashlib.sha256(raw).hexdigest()})
    return json.loads(gzip.decompress(raw) if path.endswith('.gz') else raw)


def physical(byte):
    if not isinstance(byte, int) or byte < 0 or byte >= 4 * 20250000000:
        raise ValueError('global address aperture')
    local = (byte // 512) * 128 + byte % 128
    sector = local // 32
    if sector >= 2**31:
        raise ValueError('AW31 local sector aperture')
    row = sector >> 15
    return {'stack': (byte // 128) % 4, 'local_sector31': sector,
            'byte_in_sector': local % 32, 'system_sector34': byte // 32,
            'PC': ((sector >> 2) ^ (sector >> 7) ^ (sector >> 12)) & 31,
            'bank': ((((sector >> 12) ^ (row >> 2)) & 7) << 2) | ((sector ^ row) & 3),
            'row': row, 'provider_calendar_source': 'retained r15 pc_of/bank_of'}


def kv_offset(kind, head, position, dim, context=8192, hd=128, heads=4):
    if kind not in ('K', 'V') or not (0 <= head < heads and 0 <= position < context and 0 <= dim < hd):
        raise ValueError('KV coordinates')
    return (((head * (context // 16) + position // 16) * hd + dim) * 16 + position % 16
            if kind == 'K' else (head * context + position) * hd + dim)


def rf_address(slot, lane):
    if not 32 <= slot < 512 or not 0 <= lane < 128:
        raise ValueError('RF allocation aperture')
    return {'page': slot >> 7, 'row': slot & 127, 'bank': lane // 8,
            'bit_offset': (lane % 8) * 32, 'width_bits': 32,
            'physical_mirrors': 2, 'mirrored_ACK_required': True}


def packet_identity(session, pc, chunk, ordinal, client, irs_slot, irs_serial, rank, byte):
    """Actual retained192-bit identity fields; allocator supplies wire tag separately."""
    widths = [(session, 64), (pc, 11), (chunk, 21), (ordinal, 5),
              (client, 6), (irs_slot, 5), (irs_serial, 32), (rank, 1)]
    if any(not isinstance(value, int) or not 0 <= value < 1 << width for value, width in widths):
        raise ValueError('identity aperture')
    addr = physical(byte)
    return {'die': rank, 'stack': addr['stack'], 'sector': addr['local_sector31'],
            'producer': session, 'transport': pc << 21 | chunk, 'caller': ordinal,
            'client': client, 'irs_slot': irs_slot, 'irs_serial': irs_serial}


def codec(extent, config):
    name = extent['name']; h = config['hidden_size']; v = config['vocab_size']
    if name == 'embedding':
        return {'data': 'signed_INT8_row_major', 'code_byte': 'base+token*hidden+column',
                'scale': 'BF16_little_endian', 'scale_byte': 'base+vocab*hidden+2*token',
                'code_bytes': v * h, 'scale_bytes': v * 2}
    if name.endswith('.codes'):
        return {'data': 'signed_INT8_row_major', 'byte': 'base+local_output_row*K+local_input_column',
                'recipe': 'Retained full-row W8 quantization before TP input-column slicing; no re-quantization of shards'}
    if name.endswith('.scales'):
        return {'data': 'BF16_little_endian', 'byte': 'base+2*local_output_row'}
    if name.endswith('.qk_norm'):
        return {'data': 'BF16_little_endian', 'byte': 'base+2*(kind_index*head_dim+dimension)',
                'kind_index': {'q': 0, 'k': 1}}
    if name.endswith('.K') or name.endswith('.V'):
        return {'data': 'FP8_E4M3FN_byte', 'decoded_transient': 'FP32',
                'byte_offset': '((head*(8192/16)+position//16)*128+dimension)*16+position%16'
                    if name.endswith('.K') else '(head*8192+position)*128+dimension',
                'source': 'tools/qwen_hbm_controller_calendar_r2.py:kv_rows; tools/qwen_hbm_complete_executor.py:PersistentMemory._address',
                'read_before_write': 'Sector RMW must preserve every other token byte; publication follows backing-visible ACK and reverse ownership'}
    if name == 'rope_table':
        return {'data': 'FP32_little_endian', 'byte': 'base+4*(position*128+component*64+j)',
                'component': {'cos': 0, 'sin': 1}, 'j_range': [0, 64],
                'software_layout_defined_here': True,
                'value_recipe': 'Source executor FP32 inverse frequency and angle, float64 cos/sin rounded to FP32; source arithmetic retained, no table payload generated',
                'codec_numeric_execution_qualified': False}
    if name == 'final_norm':
        return {'data': 'BF16_little_endian', 'byte': 'base+2*dimension'}
    if name == 'activation_scratch':
        return {'data': 'FP32_little_endian', 'byte': 'base+SM*1048576+version_byte_offset+4*local_word',
                'vector_bytes': 512, 'sector_bytes': 32, 'SM_extent_bytes': 1048576}
    if name == 'KV_provider_state':
        return {'data': 'software_provider_packed_state', 'publication_bitmap': {'offset': 0, 'bytes': 36864,
            'bit_index': 'layer*8192+position'}, 'lease_records': {'offset': 36864, 'slots': 36, 'bytes_each': 16,
            'fields_bits': {'position': 13, 'session': 64, 'producer_pc': 11, 'consumer_done': 2, 'status': 2, 'reserved': 36}},
            'session_header': {'offset': 37440, 'bytes': 64}, 'sector_RMW_and_visible_ACK_required': True,
            'placement': 'Additional explicitly charged HBM extent; no assumed RF/shared-memory free space'}
    raise ValueError('unclassified extent ' + name)


def build():
    pins = []
    graph = load('results/uarch/h3_versioned_lowering_20261002/Qwen.json.gz', pins)
    distributed = load('results/uarch/h3_distributed_norm_endpoint_20261002/Qwen.json.gz', pins)
    config = load('compiler/models/qwen3-8b/config.json', pins)
    for path in ['tools/qwen_hbm_complete_program.py', 'tools/qwen_hbm_complete_executor.py',
                 'tools/qwen_hbm_controller_calendar_r2.py', 'rtl/model_ready_hbm_r15/ot_hbm_r15_tag_owner.sv']:
        # r15 is pinned by this isolated branch; original numerical/address sources by H3.
        commit = PIN if not path.startswith('rtl/model_ready') else '693bba78d04ec371d9fb8dc8eb9e0d19437dddaf'
        raw = subprocess.check_output(['git', 'show', commit+':'+path], cwd=ROOT)
        pins.append({'commit': commit, 'path': path, 'sha256': hashlib.sha256(raw).hexdigest()})
    scalar_commit = 'e03c40e40cbaad54a3d3389195516fc4bfad2c4f'
    scalar_path = 'tools/h3_exact_scalar_contract.py'
    raw = subprocess.check_output(['git', 'show', scalar_commit+':'+scalar_path], cwd=ROOT)
    pins.append({'commit': scalar_commit, 'path': scalar_path, 'sha256': hashlib.sha256(raw).hexdigest()})
    smodel = spill_model()
    allocations = []
    ext = {}
    for candidate in smodel['extent_candidates']:
        rank = candidate['rank']; residents = candidate['all_extents']
        cursor = (candidate['allocated_global_end_bytes'] + 127) // 128 * 128
        # Explicit new ownership/publication-state extent, after the full spill reservation.
        residents = residents + [{'name': 'KV_provider_state', 'base': cursor, 'bytes': 37504,
                                  'role': 'software_KV_publication_and_reader_lease_state'}]
        for i, e in enumerate(residents):
            if i and residents[i-1]['base'] + residents[i-1]['bytes'] > e['base']:
                raise ValueError('extent collision')
            ref = f'Qwen.rank{rank}.extent.{e["name"]}'
            record = dict(e, rank=rank, provider_ref=ref, codec=codec(e, config),
                first_physical=physical(e['base']), last_physical=physical(e['base']+e['bytes']-1))
            ext[rank, e['name']] = record
        end = residents[-1]['base'] + residents[-1]['bytes']
        stack_bytes = ((end+127)//128+3)//4*128
        assert stack_bytes <= candidate['stack_capacity_bytes']
        allocations.append({'rank': rank, 'global_allocated_end_bytes': end,
            'max_stack_allocated_bytes': stack_bytes, 'capacity_bytes_per_stack': candidate['stack_capacity_bytes'],
            'capacity_fit': True, 'activation_scratch_growth_bytes': candidate['growth_bytes'],
            'provider_state_added_bytes': 37504, 'extents': [ext[rank, e['name']] for e in residents]})
    operands = {v['id']: v for v in graph['operands']}
    homes = []; by_version = defaultdict(list)
    for h in distributed['homes']:
        v = operands[h['version']]
        for rank in h['rank_group']:
            ref = f'Qwen.{h["version"]}.rank{rank}.SM{h["SM"]}'
            home = dict(h['home'])
            if home['class'] == 'RF':
                assert home['slot_first']+home['vectors'] <= 512
                home.update(first_word=rf_address(home['slot_first'], 0),
                    last_word=rf_address(home['slot_first']+(h['word_count']-1)//128, (h['word_count']-1)%128),
                    word_recipe='slot=slot_first+local_word//128;lane=local_word%128')
            else:
                e = ext[rank, 'activation_scratch']; base = e['base'] + h['SM']*1048576 + home['byte_offset']
                assert home['byte_offset']+home['bytes'] <= 1048576
                home.update(global_byte_base=base, byte_end_exclusive=base+home['bytes'],
                    provider_extent=e['provider_ref'], sector_count=home['bytes']//32,
                    first_physical=physical(base), last_physical=physical(base+home['bytes']-1),
                    sector_recipe='global_byte_base+32*sector_index; apply shared128B four-stack stripe',
                    byte_mask='0xffffffff for each aligned full sector', decode='FP32_little_endian')
            item = {'provider_ref': ref, 'version': h['version'], 'rank': rank, 'SM': h['SM'],
                    'home': home, 'word_count': h['word_count'], 'birth_pc': h['birth_pc'],
                    'retire_pc': h['retire_pc'], 'consumers': v['consumers'],
                    'publication_event': f'PUBLISH:{h["version"]}:r{rank}:s{h["SM"]}',
                    'release_event': f'RELEASE:{h["version"]}:r{rank}:s{h["SM"]}',
                    'release_requires': ['all listed actual consumers done', 'held completion accepted', 'all reverse validated grants accepted']}
            homes.append(item); by_version[h['version']].append(ref)
    controls = []
    for v in graph['operands']:
        if v['id'] not in by_version:
            if v['bits_per_element'] != 0:
                raise ValueError('unbound data version '+v['id'])
            for rank, count in enumerate(v['elements_per_rank']):
                if count:
                    ref = f'Qwen.control.{v["id"]}.rank{rank}'
                    by_version[v['id']].append(ref)
                    controls.append({'provider_ref': ref, 'version': v['id'], 'rank': rank,
                        'birth_pc': v['birth_pc'], 'consumers': v['consumers'],
                        'state_extent': ext[rank, 'KV_provider_state']['provider_ref'],
                        'ticket_or_fence': v['name'].split('.')[-1],
                        'representation': 'identity-bearing publication event, not zero-byte data masquerading as free storage',
                        'visibility': 'All sector backing-visible, consumer retire and reverse grants before fence publication'})
    # Conservative software dependency edges: retain leases until actual release;
    # a new version cannot borrow storage at its old syntactic retire PC alone.
    reuse = []; groups = defaultdict(list)
    for h in homes:
        groups[h['rank'], h['SM'], h['home']['class']].append(h)
    for entries in groups.values():
        latest = {}
        for h in sorted(entries, key=lambda x:(x['birth_pc'], x['version'])):
            p = h['home']; lo = p.get('slot_first', p.get('global_byte_base')); size = p.get('vectors', p.get('bytes'))
            quantum = 1 if p['class']=='RF' else 512
            # The source spill base is128B-aligned, not512B-aligned. All local
            # vector allocations share that residue; each512B interval still
            # contains16 complete32B sectors and crosses four real stack stripes.
            assert (p['class']=='RF' or lo % quantum == ext[h['rank'], 'activation_scratch']['base'] % quantum)
            assert size % quantum == 0
            units = range(lo//quantum, (lo+size)//quantum)
            predecessors = {latest[u]['provider_ref']: latest[u] for u in units if u in latest}
            for old in predecessors.values():
                if old['retire_pc'] >= h['birth_pc']:
                    raise ValueError('simultaneous version storage alias')
                reuse.append({'new_home': h['provider_ref'], 'wait_release': old['release_event']})
            for u in units:
                latest[u] = h
    operations = []
    for o in graph['operations']:
        attrs = o['source']['attributes']; external = []; desc = o.get('external_bindings', {}).get('immutable_weight_descriptor')
        if desc:
            prefix = 'head' if desc['layer'] is None else f'L{desc["layer"]}.{desc["name"]}'
            suffixes = ('codes',) if o['opcode']=='MATRIX' else ('scales',)
            for suffix in suffixes:
                external.append({'provider_ref': ext[desc['die'], prefix+'.'+suffix]['provider_ref'],
                    'rows': desc['rows'], 'K': desc['K'], 'weight_descriptor': desc,
                    'ordered_address_iteration': 'output_row then input_column; preserve source split/tree/rounding, do not infer order from arrival'})
        if o['opcode'] in ('EMBED', 'FINAL_NORM', 'ROPE', 'HEAD_NORM'):
            name = 'embedding' if o['opcode']=='EMBED' else 'final_norm' if o['opcode']=='FINAL_NORM' else 'rope_table' if o['opcode']=='ROPE' else f'L{attrs["layer"]}.qk_norm'
            for rank in o['participants']:
                external.append({'provider_ref': ext[rank, name]['provider_ref'], 'selector': attrs})
        if o['opcode'] in ('KV_WRITE', 'KV_READ', 'KV_FENCE'):
            rank = attrs['die']; layer = attrs['layer']
            for kind in ('K', 'V'):
                external.append({'provider_ref': ext[rank, f'L{layer}.{kind}']['provider_ref'],
                    'coordinates': {'head': [0, 4], 'position': [0, 8192], 'dimension': [0, 128]},
                    'prefix_rule': 'read positions0..position after every corresponding publication fence',
                    'partial_sector_RMW': kind=='K'})
            external.append({'provider_ref': ext[rank, 'KV_provider_state']['provider_ref'],
                             'publication_bit': f'{layer}*8192+position', 'reader_lease_slot': layer})
        operations.append({'pc': o['pc'], 'opcode': o['opcode'], 'participants': o['participants'],
            'source_dependencies': o['dependencies'], 'golden_contract': o['golden_contract'],
            'inputs': {v: by_version[v] for v in o['reads']}, 'outputs': {v: by_version[v] for v in o['writes']},
            'external_providers': external, 'accept_requires': ['input version publications', 'destination leases', 'finite issue/sector/ACK credits'],
            'retire_requires': ['actual output provider publication', 'actual input consumers done', 'reverse grants'],
            'native_steps_owner': 'Popper lowering; provider record does not substitute high-level arithmetic execution',
            'scalar_contract_ref': scalar_commit+':'+scalar_path,
            'latency_terms': ['provider_request_service', 'codec_decode', 'RF_or_spill_delivery', 'consumer_retire', 'reverse_CDC_grant'],
            'latency_status': 'PROVISIONAL_NONZERO_PARAMETERS_REQUIRED_BY_CALENDAR', 'hardware_qualified': False})
    assert len(operations)==1737 and len(Counter(o['opcode'] for o in operations))==21
    assert set(by_version)==set(operands)
    return {'schema': 'opentallas.Qwen.provider-binding.v1', 'source_pins': pins,
        'status': 'ALL_SOURCE_VERSIONS_AND_PCS_PROVIDER_REFERENCED_SOFTWARE_CANDIDATE',
        'coverage': {'PCs': len(operations), 'opcode_classes': 21, 'versions': len(operands),
                     'data_homes': len(homes), 'control_homes': len(controls), 'unbound_versions': 0},
        'allocation': allocations, 'version_homes': homes, 'control_homes': controls,
        'reuse_dependencies': reuse, 'operations': operations,
        'resource_contract': {'SMs_per_rank': 32, 'RF_slots_per_SM': 512, 'RF_workspace_slots': [0, 32],
            'RF_transaction_lease': 1, 'RF_reads_bits': 8192, 'RF_mirrored_write_bits': 4096,
            'HBM_stacks_per_rank': 4, 'PCs_per_stack': 32, 'banks_per_PC': 32,
            'request_QD': 64, 'return_RQD': 32, 'physical_tags_per_stack': 4096,
            'CAM_contexts_per_PC': 128, 'WR_residence_per_stack': 4,
            'source_stage_sector_credits_per_rank': 4, 'source_stage_reader_records_per_rank': 4,
            'source_stage_ACK_capture_records_per_rank': 4,
            'spill_vectors_inflight': 1, 'spill_sector_issue_inflight': 1,
            'logical_KV_reader_leases_per_rank': 36, 'logical_KV_publication_positions_per_layer': 8192,
            'logical_state_storage_bytes_per_rank': 37504,
            'physical_tag_binding': {'source': 'ot_hbm_r15_tag_owner allocated_tag handshake',
                'wire_tag_bits': 16, 'allocated_context_bits': 12,
                'immutable_context_identity_bits': 192, 'context_macro_word_bits': 256,
                'logical_owner': '(token_session64,transport32,PC,version,rank,SM,sector_ordinal)',
                'identity_recipe': 'producer=token_session64;transport=(PC<<21)|chunk_index;caller=sector ordinal%32;client=provider class;IRSslot/serial actual opcode acceptance',
                'transport_fields': {'PC_bits': 11, 'chunk_index_bits': 21},
                'client_classes': {'KV_WR': 1, 'KV_RD': 2, 'RMW_RD': 3, 'SPILL_WR': 4,
                    'SPILL_RD': 5, 'IMMUTABLE_RD': 6, 'STATE_RMW': 7, 'CONSTANT_RD': 8},
                'quarantine_until': 'All native owned returns consumed, all sector retire events and validated reverse grants accepted; no reuse at response arrival',
                'chunk_rule': 'At most32sectors per allocated root; caller16 must not encode whole large tensor ordinal; chunk identity in admitted transport/producer context',
                'reset_reuse': 'Requires coordinated provider drain/reset fence; no timeout-derived safety'},
            'ownership_event_order': ['reserve', 'request_accept', 'actual_owned_return_or_WR_visible',
                'consumer_accept', 'sector_retire', 'reverse_credit_accept', 'validated_held_grant_accept', 'release'],
            'owner_lookup_bound': {'source_CORE_period_ps': 1000, 'serialized_lookup_edges': 12,
                'minimum_held_accept_edges': 1, 'lookups_per_delivered_and_retired_sector': 2,
                'optimistic_sectors_per_CORE_edge_per_stack': '1/26',
                'optimistic_bytes_per_second_per_stack_at_source1GHz': 32000000000/26,
                'scope': 'Arithmetic service ceiling before command/CDC/backpressure/PHY. Not measured bandwidth or clock admission; queues cannot remove this source serialization.',
                'mandatory_repair_model_owner': 'Maxwell/Kepler: price per-PC context read pipelines, held outputs, return/grant arbitration and exact once root retirement before RTL; no inherited HBM bandwidth'},
            'provisional_latency_policy': 'Every provider/codec/CDC cost supplied as positive explicit calendar parameter; missing measurements never zero or qualification'},
        'integration_owners': {'Popper': '01a0fc12-35b5-7621-9d9d-7837163c53b0',
            'Dewey': '01a0fc12-35e2-71f0-873e-d6aa6ab2d24e',
            'Kepler': '01a0f9c6-fde3-7111-8b3c-a4a505b9a010',
            'Peirce_DS': '01a0f95d-badc-74d3-bde3-f3eb28f089b8'},
        'remaining_runtime_gates': ['actual codec values and native arithmetic execution',
            'actual PHY backing visibility and reset fence', 'H2 reverse repair connected RTL gate',
            'actual RF internal routing and endpoint SSFF', 'full finite calendar composition'],
        'DS_binding_transferred': False, 'adopted': False, 'runtime_visibility_measured': False,
        'consumer_address_update_rule': 'All consumers resolve (version,rank,SM) through version_homes, or external provider_ref through allocation.extents. Source H3 inline old spill refusal/extent is superseded only by this candidate lookup; pinned input files remain byte-identical.',
        'physical_QTP4_transport_qualification_transferred': False,
        'QROM_refill_scope': 'Euclid e26442d73 single-outstanding32B refill remains separate; no throughput/concurrency/burst credit from logical homes or generic r14/r15 provider',
        'hardware_or_rate_qualified': False, 'jobs': []}


def emit(output):
    output.mkdir(parents=True, exist_ok=False)
    result = build()
    raw = (json.dumps(result, sort_keys=True, separators=(',', ':'))+'\n').encode()
    packed = gzip.compress(raw, mtime=0)
    (output/'Qwen_provider_binding.json.gz').write_bytes(packed)
    handoff = {k: result[k] for k in ['schema', 'status', 'source_pins', 'coverage', 'resource_contract',
                                    'integration_owners', 'remaining_runtime_gates']}
    handoff['binding_SHA256'] = hashlib.sha256(packed).hexdigest()
    handoff['uncompressed_bytes'] = len(raw)
    handoff['compressed_bytes'] = len(packed)
    handoff['allocation_summary'] = [{k: x[k] for k in x if k!='extents'} for x in result['allocation']]
    handoff['reuse_dependency_count'] = len(result['reuse_dependencies'])
    (output/'handoff.json').write_text(json.dumps(handoff, indent=2, sort_keys=True)+'\n')
    print(json.dumps(handoff['coverage']))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    emit(p.parse_args().output)
