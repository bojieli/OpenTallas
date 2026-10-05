#!/usr/bin/env python3
"""Observed position-zero Qwen KV sectors joined to conditional cache/RMW leases.

Compile archived operator observations only. No execution of numerical golden,
no inferred refill/PHY commands, no software edges promoted to physical cycles.
"""
import argparse
import copy
import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import struct

BASE = Path(__file__).resolve().parents[1] / 'results/uarch/h4_hbm_qwen_observed_kv_cache_20261002'
PIN = 'ee7e6edb39fe3c8547d4b9cea68b03d6eb1f8974f3b0721594bbfeee4256b5e1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def inputs(base=BASE):
    base = Path(base).resolve()
    raw = (base / 'input_manifest.json').read_bytes()
    require(sha(raw) == PIN, 'hard manifest pin')
    result = {}
    for row in json.loads(raw)['inputs']:
        path = (base / row['archive']).resolve()
        require(path.is_relative_to(base / 'inputs'), 'exact archive origin')
        data = path.read_bytes()
        require(len(data) == row['bytes'] and sha(data) == row['sha256'], 'exact archived bytes')
        result[path.name] = data
    return result


def source_functions(data, names):
    tree = ast.parse(data.decode())
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    require({n.name for n in selected} == set(names), 'exact retained functions')
    scope = {'struct': struct, 'hashlib': hashlib}
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<pinned source functions>', 'exec'), scope)
    return scope


def coordinate(address):
    require(type(address) is int and address % 32 == 0 and 0 <= address < 2**34,
            'aligned source Qwen34-bit address')
    line, offset = divmod(address, 128)
    quotient = line // 32
    index = quotient & 2047
    return dict(slice=line % 4, bank=(line // 4) % 8, index=index,
                tag=quotient >> 11, sector_in_line=offset // 32,
                reserved=index >= 2044,
                policy='conditional direct-mapped L2; reserved512B/bank requires explicit bypass')


def compile_directory(data=None):
    data = inputs() if data is None else data
    native = json.loads(gzip.decompress(data['Qwen_tiled.json.gz']))
    verifier = source_functions(data['verify.py'], ['require', 'event_plan', 'verify_event_bindings',
        'verify_transition_state', 'payload_layout', 'decoded_hashes'])
    physical = source_functions(data['provider.py'], ['physical'])['physical']
    events = [json.loads(line) for line in data['kv_journal.jsonl'].splitlines()]
    verifier['verify_event_bindings'](native, events)
    verifier['verify_transition_state'](native, events)
    inventory = [json.loads(line) for line in data['payload_inventory.jsonl'].splitlines()]
    values = {f: {} for f in ('committed_U8.bin', 'read_U8.bin', 'final_U8.bin')}
    cursors = dict.fromkeys(values, 0)
    pcs = {(tuple(e['key']), e['event']): e['pc'] for e in events}
    for row in inventory:
        name, key = row['file'], tuple(row['key'])
        require(name in values and row['offset'] == cursors[name], 'exact contiguous inventory')
        require(row['record_format'] == '<uint64_address,uint8_code>' and row['bytes'] == 9 * row['records'], 'address/U8 codec')
        blob = data[name][row['offset']:row['offset'] + row['bytes']]
        require(len(blob) == row['bytes'] and sha(blob) == row['sha256'], 'payload range hash')
        if name != 'final_U8.bin':
            require(row['pc'] == pcs[(key, 'commit_publish' if name == 'committed_U8.bin' else 'acquire')], 'source payload PC')
        output = values[name].setdefault(key, {})
        layout = verifier['payload_layout'](native, key)
        for address, code in struct.iter_unpack('<QB', blob):
            require(address in layout and address not in output, 'exact source address/unique byte')
            output[address] = code
        cursors[name] += len(blob)
    for name in values:
        require(cursors[name] == len(data[name]), 'no trailing unbound bytes')
    require(values['committed_U8.bin'] == values['read_U8.bin'] == values['final_U8.bin'], 'commit/read/final identical')
    hashes = verifier['decoded_hashes'](native, values['read_U8.bin'])
    prior = json.loads(data['prior_readhash_review.json'])
    require(hashes == prior['decoded_read_hashes'] and prior['actual_decoded_read_hash_binding'] == 'PASS', 'prior native read hashes')
    proposal = json.loads(data['proposal.json'])
    require(sha(data['Qwen_tiled.json.gz']) == proposal['original_source_sha256']['results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz'], 'actual runtime native frame')
    require(sha(data['verify.py']) == next(v for k,v in proposal['additive_source_sha256'].items() if k.endswith('/qwen_kv_observation_verify.py')), 'actual observed verifier source')
    binding = json.loads(data['independent_runner_binding.json'])
    require(binding['status'] == 'PASS_INDEPENDENT_POST_TERMINAL_RUNNER_BINDING', 'independent source/GO provenance')
    milestone = json.loads(data['milestone.json'])
    require(milestone['groups'] == 72 and milestone['events'] == 432 and milestone['original_production_journal'] == 'UNKNOWN_NOT_CAPTURED', 'actual operator archived scope')
    parent = json.loads(data['parent_review.json'])
    require(sha(data['terminal.json']) == parent['terminal_sha256'], 'parent terminal identity')
    require(parent['source_commit'] == '796508cad2877dd42238050e3b66afbd81002879' and parent['GO_commit'] == '88c7435959ad8c7f058458ec3e93ea5f0dcd8695', 'source/GO admission')
    source_ops = {op['pc']: op for op in native['operations']}
    homes_by_version = {}
    for home in native['provider_binding']['version_homes']:
        homes_by_version.setdefault(home['version'], []).append(home)
    groups = []
    for key, payload in sorted(values['committed_U8.bin'].items()):
        layout = verifier['payload_layout'](native, key)
        require(set(payload) == set(layout), 'complete physical payload layout')
        trace = [dict(sequence=i, **e) for i, e in enumerate(events) if tuple(e['key']) == key]
        require([e['event'] for e in trace] == ['write_accept', 'commit_publish', 'acquire', 'consumer_done', 'consumer_done', 'release'], 'six ordered lifecycle events')
        sectors = {}
        for address, code in sorted(payload.items()):
            base = address & ~31
            sector = sectors.setdefault(base, dict(address=base, mask=0, patch=bytearray(32), byte_count=0,
                provider_ref=layout[address]['provider_ref'], kind=layout[address]['kind'],
                producer_version=layout[address]['producer_version'], decoded_read_version=layout[address]['decoded_read_version']))
            require(sector['provider_ref'] == layout[address]['provider_ref'], 'sector belongs to exact extent')
            sector['mask'] |= 1 << (address % 32)
            sector['patch'][address % 32] = code
            sector['byte_count'] += 1
        for sector in sectors.values():
            sector['patch_hex'] = bytes(sector.pop('patch')).hex()
            sector['L2'] = coordinate(sector['address'])
            sector['source_HBM_address'] = physical(sector['address'])
            sector['old_bytes_required'] = sector['mask'] != 0xffffffff
            sector['parent_write_pc'] = trace[0]['pc']
            sector['parent_read_pc'] = trace[2]['pc']
        ext = next(e for e in native['source_program']['memory_allocation'][key[1]]['extents'] if e['name'] == 'KV_provider_state')
        versions = {version for event in trace for version in event['reads'] + event['writes']}
        homes = [home for version in sorted(versions) for home in homes_by_version.get(version, []) if home['rank'] == key[1]]
        op_bindings = [dict(pc=pc, opcode=source_ops[pc]['opcode'], dependencies=source_ops[pc]['dependencies'],
            provider_binding=source_ops[pc]['provider_binding']) for pc in sorted({event['pc'] for event in trace})]
        groups.append(dict(source_RF_control_version_homes=homes, source_operation_bindings=op_bindings,
            RF_visibility_and_mirror_ACK_observations=None, key=list(key), die=key[1], SM=None, writer_tag=trace[0]['tag'], reader_lease=trace[2]['lease'],
            source_events=trace, sectors=list(sectors.values()), state_provider_ref=ext['provider_ref'],
            state_home_range=[ext['base'], ext['base'] + ext['bytes']],
            metadata_scope='actual packed-state snapshots; not observed bus transactions',
            publication_requires=['all sector old-byte preservation and write visibility/reverse receipts',
                'packed record then publication bitmap visible fence receipt'],
            retirement_requires=['all source read bytes captured', 'SCORES and PV consumer receipts', 'reverse lease receipt']))
    require(len(groups) == 72 and sum(len(g['sectors']) for g in groups) == 19584, 'actual72 groups/19584 sectors')
    require(sum(s['byte_count'] for g in groups for s in g['sectors']) == 73728, 'actual73728 payload bytes')
    return dict(schema='QWEN_OBSERVED_KV_CACHE_DIRECTORY_R1', source_commit=parent['source_commit'], GO_commit=parent['GO_commit'],
        observed_archive_commit='f9212629928a027742c12bfcfb4a7423b2f0dfd7',
        original_native_sha256=sha(data['Qwen_tiled.json.gz']), groups=groups,
        scope='observed released-checkpoint position0 KV operator; consumer completion harness-driven',
        production_lifecycle_qualified=False, whole_operator=False, hardware_admitted=False,
        HBM_command_count=None, refill_count=None, physical_cycles=None)


def merge32(old, patch, mask):
    require(type(old) is bytes and len(old) == 32 and type(patch) is bytes and len(patch) == 32,
            'explicit opaque32B old sector and patch')
    require(type(mask) is int and 0 <= mask < 2**32, 'exact byte mask')
    return bytes(patch[i] if mask >> i & 1 else old[i] for i in range(32))


class KVEndpoint:
    """Opt-in causal adapter sharing a caller's actual matrix/cache bank ledger.

    One group/rank and one sector child/rank. External visibility, metadata
    fence and reverse receipts are mandatory. This does not manufacture them.
    """
    def __init__(self, directory, *, banks):
        require(directory == compile_directory(), 'exact observed directory')
        require(type(banks) is dict, 'explicit connected bank ownership table')
        self.banks = banks
        self.groups = {tuple(g['key']): copy.deepcopy(g) for g in directory['groups']}
        self.next_layer = {0: 0, 1: 0}
        self.active = {}
        self.finished = set()

    def begin(self, key):
        key = tuple(key)
        require(key in self.groups and key not in self.finished and key[1] not in self.active, 'one actual group credit/rank')
        require(key[0] == self.next_layer[key[1]], 'retained source layer order/rank')
        self.active[key[1]] = dict(key=key, phase='WRITE', cursor=0, child=None, done=set())

    def _state(self, key):
        key = tuple(key)
        x = self.active.get(key[1])
        require(x is not None and x['key'] == key, 'matching live KV parent')
        return x, self.groups[key]

    def grant(self, key, *, address, bypass=False):
        x, g = self._state(key)
        require(x['phase'] in ('WRITE', 'READ') and x['child'] is None, 'finite single sector child')
        s = g['sectors'][x['cursor']]
        require(address == s['address'], 'exact ordered source sector')
        require(type(bypass) is bool and (not s['L2']['reserved'] or bypass), 'reserved owner L2 requires explicit bypass')
        bank = (g['die'], s['L2']['slice'], s['L2']['bank'])
        require(bank not in self.banks, 'actual matrix/cache bank busy')
        token = ('Qwen_KV', tuple(key), x['phase'], x['cursor'])
        self.banks[bank] = token
        x['child'] = dict(bank=bank, token=token, stage='GRANTED', sector=s)

    def child(self, key, *, event, payload=None):
        x, g = self._state(key)
        c = x['child']
        require(c is not None and self.banks.get(c['bank']) == c['token'], 'same granted child/ownership')
        s = c['sector']
        if x['phase'] == 'WRITE' and c['stage'] == 'GRANTED' and event == 'old_sector_capture':
            c['merged'] = merge32(payload, bytes.fromhex(s['patch_hex']), s['mask'])
            c['stage'] = 'MERGED'
            return c['merged']
        if x['phase'] == 'WRITE' and c['stage'] == 'GRANTED' and event == 'full_sector_write':
            require(not s['old_bytes_required'], 'partial write refuses implicit zero tails')
            c['merged'] = bytes.fromhex(s['patch_hex']); c['stage'] = 'MERGED'
            return c['merged']
        if x['phase'] == 'WRITE' and c['stage'] == 'MERGED' and event == 'backend_write_visible':
            require(payload == c['merged'], 'matching preserved write visibility payload')
            c['stage'] = 'VISIBLE'
        elif x['phase'] == 'READ' and c['stage'] == 'GRANTED' and event == 'read_capture':
            require(type(payload) is bytes and len(payload) == 32, 'explicit physical read capture')
            patch = bytes.fromhex(s['patch_hex'])
            require(all(payload[i] == patch[i] for i in range(32) if s['mask'] >> i & 1), 'actual observed U8 read')
            c['stage'] = 'VISIBLE'
        elif c['stage'] == 'VISIBLE' and event == 'consumer_accept':
            c['stage'] = 'CONSUMED'
        elif c['stage'] == 'CONSUMED' and event == 'validated_reverse_grant':
            del self.banks[c['bank']]
            x['child'] = None; x['cursor'] += 1
            if x['cursor'] == len(g['sectors']):
                x['phase'] = 'FENCE' if x['phase'] == 'WRITE' else 'CONSUMERS'
        else:
            raise ValueError('causal old/visible/consumer/reverse sector order')

    def parent(self, key, *, event, receipt=None):
        x, g = self._state(key)
        trace = g['source_events']
        if event == 'commit_publish' and x['phase'] == 'FENCE':
            wanted = dict(provider_ref=g['state_provider_ref'], writer_tag=g['writer_tag'],
                record_address=trace[1]['state']['record_address'], record_hex=trace[1]['state']['record_hex'],
                bitmap_address=trace[1]['state']['bitmap_address'], bitmap_byte=trace[1]['state']['bitmap_byte'])
            require(receipt == wanted, 'explicit packed record/bitmap visibility fence receipt')
            x['phase'] = 'PUBLISHED'
        elif event == 'acquire' and x['phase'] == 'PUBLISHED':
            require(receipt == g['reader_lease'], 'exact source acquired reader lease')
            x['phase'] = 'READ'; x['cursor'] = 0
        elif event in ('SCORES', 'PV') and x['phase'] == 'CONSUMERS':
            require(event not in x['done'] and (event != 'PV' or 'SCORES' in x['done']), 'source exact consumer order')
            e = trace[3 if event == 'SCORES' else 4]
            require(receipt == dict(pc=e['pc'], lease=g['reader_lease'], reads=e['reads']), 'exact source consumer receipt')
            x['done'].add(event)
        elif event == 'release' and x['phase'] == 'CONSUMERS':
            require(x['done'] == {'SCORES', 'PV'} and receipt == dict(lease=g['reader_lease'], reverse_accepted=True), 'both consumers and explicit reverse lease')
            self.finished.add(tuple(key)); self.next_layer[g['die']] += 1; del self.active[g['die']]
        else:
            raise ValueError('publication/acquire/consumer/retire causal order')


def model(directory):
    sectors = [s for g in directory['groups'] for s in g['sectors']]
    return dict(schema='QWEN_OBSERVED_KV_CACHE_SERVICE_DEMAND_R1', groups=72, source_lifecycle_events=432,
        payload_write_address_sectors32=len(sectors), payload_read_address_sectors32=len(sectors),
        committed_U8_bytes=sum(s['byte_count'] for s in sectors), read_U8_bytes=sum(s['byte_count'] for s in sectors),
        sector_payload_capacity_bytes_each_direction=len(sectors)*32,
        partial_write_sectors=sum(s['old_bytes_required'] for s in sectors),
        preserved_tail_bytes_required=sum(32-s['byte_count'] for s in sectors),
        reserved_L2_bypass_sectors_each_direction=sum(s['L2']['reserved'] for s in sectors),
        address_mapping='exact retained r17 stack/PC/bank/row; conditional cache4slices8banks; no SM inferred',
        HBM_command_count=None, refill_count=None, metadata_bus_transactions=None,
        per_port_bytes_per_cycle=None, boundary_bits_per_cycle=None, physical_cycles=None,
        finite_adapter=dict(parent_credits_per_rank=1, child_credits_per_rank=1, merge_buffer_bytes_per_rank=32,
            rank_replicas=2, minimum_merge_data_bits=512, existing_32SMs_per_die=32,
            area=None, slot_fit=None, mux_tracks=None, fanout=None,
            note='Reuse existing priced cache32B payload buffer if lifetimes admitted; never add area or costs twice'),
        selected_cost_event_counts=dict(KV_sector_old_capture=sum(s['old_bytes_required'] for s in sectors),
            KV_sector_write_visible=len(sectors), KV_sector_read_capture=len(sectors),
            KV_sector_consumer=2*len(sectors), KV_sector_reverse=2*len(sectors),
            KV_state_record_bitmap_fence=72, KV_SCORES_consumer=72, KV_PV_consumer=72, KV_parent_reverse=72),
        cost_count_scope='mandatory proposed endpoint handshakes, not measured source bus/PHY commands',
        cost_event_keys=['KV_sector_old_capture', 'KV_sector_write_visible', 'KV_sector_read_capture',
            'KV_sector_consumer', 'KV_sector_reverse', 'KV_state_record_bitmap_fence',
            'KV_SCORES_consumer', 'KV_PV_consumer', 'KV_parent_reverse'],
        actual_event_intervals=None, software_ticks_used=False, whole_operator=False,
        scope='position0 released KV operator; harness consumer acknowledgments; original full-token lifecycle unknown',
        fundamental_gaps=['partial K old-sector validity/init and refill receipts', 'physical write visibility and reverse receipt backend',
            'installed L2 reservation/bypass and actual bank eligibility', 'actual record/bitmap RMW fence ports',
            'production SCORES/PV consumer DAG and RF mirror ACKs', 'finite physical contender intervals, clock/PG/cuts and service area'],
        hardware_admitted=False, engine_build_ready=False, headline_qualified=False)


def outputs():
    directory = compile_directory()
    return {'directory.json.gz': gzip.compress(canonical(directory), mtime=0), 'model.json': json.dumps(model(directory), indent=2, sort_keys=True).encode()+b'\n'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    generated = outputs()
    if args.verify:
        for name, data in generated.items():
            require((BASE/name).read_bytes() == data, 'byte-exact model replay '+name)
        print('PASS exact observed KV directory and service-demand replay')
    else:
        require(args.output is not None, 'explicit additive output directory')
        args.output.mkdir(parents=True, exist_ok=True)
        for name, data in generated.items():
            (args.output/name).write_bytes(data)


if __name__ == '__main__':
    main()
