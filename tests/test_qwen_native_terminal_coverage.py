"""Metadata/capture mutations only. No checkpoint, interpreter or oracle execution."""
import copy
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import qwen_native_terminal_coverage as V

N = json.loads(gzip.decompress(V.pinned(ROOT, V.SOURCE, V.ARTIFACT)))
VALUES = {v['version']: v for v in N['operands']}


def trace():
    rows = []; count = 0
    for op in N['operations']:
        if op['opcode'] not in ('KV_WRITE', 'KV_FENCE', 'KV_READ'):
            count += 1
        rows.append(dict(pc=op['pc'], opcode=op['opcode'], elapsed_s=op['pc'],
                         outputs=[dict(version=v, shape=[1 if n == 'position+1' else n for n in VALUES[v]['shape']], sha256='f'*64) for v in op['writes']],
                         provider=dict(transactions=count, bytes=count*32, byte_ranges=count, read_lease_outstanding=False)))
    return rows


def journal():
    events = []; leases = {}; tags = {}; identity = 0
    for op in N['operations']:
        code = op['opcode']; a = op['attributes']; pc = op['pc']
        if code in ('KV_WRITE', 'KV_FENCE', 'KV_READ'):
            key = (a['layer'], a['die'], 0)
        elif code in ('SCORES', 'PV'):
            fields = VALUES[op['reads'][1]]['name'].split('.')
            key = (int(fields[0][1:]), int(fields[1][1:]), 0)
        else:
            continue
        if code == 'KV_WRITE':
            tags[key] = identity; identity += 1
            events.append(dict(pc=pc, event='write_accept', tag=tags[key], key=list(key)))
        elif code == 'KV_FENCE':
            events.append(dict(pc=pc, event='commit_publish', tag=tags[key], key=list(key)))
        elif code == 'KV_READ':
            leases[key] = identity; identity += 1
            events.append(dict(pc=pc, event='acquire', lease=leases[key], key=list(key)))
        else:
            events.append(dict(pc=pc, event='consumer_done', lease=leases[key], stage=code))
            if code == 'PV':
                events.append(dict(pc=pc, event='release', lease=leases[key]))
    return events


class CoverageTests(unittest.TestCase):
    def test_offline_terminal_packet_open_gates(self):
        # Complete synthetic terminal packet, using actual committed admission and
        # qualification bytes. This never accesses their checkpoint/image paths.
        base = 'results/rtl/qwen_trained_native_PVE1_20261002_r1/'
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp); (d/'native').mkdir()
            for name, origin in [('GO.json', 'GO.json'), ('qualified_images.json', 'qualified_images.json'), ('launcher.py', 'preparation/launcher.py')]:
                (d/name).write_bytes(V.pinned(ROOT, V.GO, base+origin))
            (d/'GO.commit').write_text(V.GO)
            rows = trace(); comparisons = []; byname = {VALUES[o['version']]['name']: o for r in rows for o in r['outputs']}
            for name, size in V.boundaries(N).items():
                array = np.zeros(size, np.float32); np.save(d/'native'/(name+'.npy'), array, allow_pickle=False)
                byname[name]['sha256'] = V.digest(array.tobytes())
                comparisons.append(dict(register=name, values=size, bit_mismatches=0, actual_nonfinite=0, reference_nonfinite=0))
            lock = json.loads(V.pinned(ROOT, V.SOURCE, V.LOCK)); shards = {x['path']: x['sha256'] for x in lock['expected_files'] if x['path'].endswith('.safetensors')}
            reads = []
            for name, shape in V.tensor_shapes(N).items():
                if len(shape) == 1: spans = [(None, None, shape[0]*2)]
                elif name == 'model.embed_tokens.weight': spans = [(9707, 9708, shape[1]*2)]
                else: spans = [(lo, min(lo+256, shape[0]), (min(lo+256, shape[0])-lo)*shape[1]*2) for lo in range(0, shape[0], 256)]
                for lo, hi, size in spans:
                    reads.append(dict(tensor=name, shard=next(iter(shards)), shape=shape, row_start=lo, row_stop=hi, bytes=size, sha256='f'*64))
            reader = dict(checkpoint_revision=lock['revision'], verified_shards=shards, reads=reads, max_source_rows_per_read=256, images_written=False, downloads=False, actual_hardware_memory_provider=False)
            result = dict(status='PASS_BOUNDED_TILED_SOFTWARE', PCs=1737, next_token=0, temporary_HBM_bytes=0)
            byname['next_token']['sha256'] = V.digest(np.array([0], np.uint32).tobytes())
            nt = dict(verdict='PASS_TRAINED_NATIVE_TOKEN_POSTCHECKED', native=result, provider=rows[-1]['provider'], full_checkpoint_native=True, layers=36, input_token=9707, position=0, oracle_callbacks=0, actual_RTL=False, physical_credit=False, token_rate_credit=False, post_execution_comparisons=comparisons)
            raw = json.dumps(nt).encode(); (d/'native/terminal.json').write_bytes(raw)
            log = json.dumps(nt)+'\n'; (d/'actual_native.log').write_text(log)
            terminal = dict(source_commit=V.SOURCE, GO_commit=V.GO, actual_native_log_sha256=V.digest(log.encode()), native_terminal_sha256=V.digest(raw), native_terminal=nt, verdict=nt['verdict'], exit_code=0, termination_reason=None)
            (d/'terminal.json').write_text(json.dumps(terminal))
            (d/'native/native_progress.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            (d/'native/post_execution_comparisons.json').write_text(json.dumps(comparisons))
            (d/'native/reference_source_provenance.json').write_text(json.dumps(reader))
            q = json.loads((d/'qualified_images.json').read_bytes())
            (d/'native/image_manifest_identity.json').write_text(json.dumps(dict(sha256=q['manifest_sha256'])))
            answer = V.verify(d, ROOT, d/'qualified_images.json')
            self.assertFalse(answer['fulltoken_KV_comparison_qualified'])
            self.assertFalse(answer['checkpoint_tensor_shard_mapping_verified'])
            self.assertEqual(answer['ordered_KV_journal'], 'MISSING_NOT_EMITTED_BY_PINNED_DRIVER')
            (d/'native/kv_journal.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in journal()))
            answer = V.verify(d, ROOT, d/'qualified_images.json')
            self.assertEqual(answer['ordered_KV_journal'], 'STRUCTURE_VALID_ORIGIN_UNQUALIFIED_FOR_PINNED_DRIVER')
            self.assertFalse(answer['fulltoken_KV_comparison_qualified'])
            (d/'native/kv_journal.jsonl').write_text('{}\n')
            with self.assertRaisesRegex(ValueError, '432'): V.verify(d, ROOT, d/'qualified_images.json')

    def test_actual_program_metadata(self):
        self.assertEqual(len(N['operations']), 1737)
        self.assertEqual(sum(o['opcode'] in ('KV_WRITE', 'KV_FENCE', 'KV_READ') for o in N['operations']), 216)
        self.assertEqual(sum(V.boundaries(N).values()), 303488)
        V.verify_trace(N, trace())

    def test_trace_mutations(self):
        changes = [
            ('missing PC', lambda r: r.pop(41)),
            ('duplicate PC', lambda r: r[41].update(pc=40)),
            ('wrong opcode', lambda r: r[41].update(opcode='EMBED')),
            ('wrong noncaptured shape', lambda r: r[0]['outputs'][0].update(shape=[1])),
            ('bad digest', lambda r: r[0]['outputs'][0].update(sha256='q'*64)),
            ('NaN elapsed', lambda r: r[50].update(elapsed_s=float('nan'))),
            ('checkpoint read during KV', lambda r: r[10]['provider'].update(bytes=r[9]['provider']['bytes']+1)),
            ('reader lease outstanding', lambda r: r[100]['provider'].update(read_lease_outstanding=True)),
        ]
        for name, change in changes:
            with self.subTest(name=name):
                rows = trace(); change(rows)
                with self.assertRaises(ValueError): V.verify_trace(N, rows)

    def test_capture_extent_and_argmax(self):
        with tempfile.TemporaryDirectory() as temp:
            rows = trace(); comparisons = []
            byname = {VALUES[o['version']]['name']: o for r in rows for o in r['outputs']}
            for name, size in V.boundaries(N).items():
                array = np.zeros(size, np.float32)
                if name == 'head.d1.scaled': array[7] = 2
                np.save(Path(temp)/(name+'.npy'), array, allow_pickle=False)
                byname[name]['sha256'] = V.digest(array.tobytes())
                comparisons.append(dict(register=name, values=size, bit_mismatches=0, actual_nonfinite=0, reference_nonfinite=0))
            winner = N['source_program']['config']['vocab_size']//2+7
            byname['next_token']['sha256'] = V.digest(np.array([winner], np.uint32).tobytes())
            V.verify_captures(N, rows, temp, comparisons, winner)
            with self.assertRaisesRegex(ValueError, 'argmax'): V.verify_captures(N, rows, temp, comparisons, 123)
            # Same total303488, wrong per-register allocation: old collector accepts.
            wrong = copy.deepcopy(comparisons); wrong[0]['values'] -= 1; wrong[1]['values'] += 1
            with self.assertRaisesRegex(ValueError, 'extent'): V.verify_captures(N, rows, temp, wrong, winner)
            wrong = copy.deepcopy(comparisons); wrong[0]['actual_nonfinite'] = 1
            with self.assertRaises(ValueError): V.verify_captures(N, rows, temp, wrong, winner)

    def test_ordered_journal(self):
        self.assertEqual(V.verify_kv_journal(N, journal()), 432)

    def test_journal_mutations(self):
        changes = [
            ('missing event', lambda e: e.pop(4)),
            ('publish before accept', lambda e: e.__setitem__(slice(0, 2), e[:2][::-1])),
            ('wrong layer', lambda e: e[0].update(key=[1, 0, 0])),
            ('stale tag', lambda e: e[1].update(tag=999)),
            ('wrong producer PC', lambda e: e[1].update(pc=10)),
            ('PV before SCORES', lambda e: e[3].update(stage='PV')),
            ('stale consumer lease', lambda e: e[3].update(lease=999)),
            ('duplicate identity', lambda e: e[2].update(lease=e[0]['tag'])),
            ('release wrong lease', lambda e: e[5].update(lease=999)),
            ('fabricated hardware clocks', lambda e: e[0].update(cycles=5)),
        ]
        for name, change in changes:
            with self.subTest(name=name):
                events = journal(); change(events)
                with self.assertRaises(ValueError): V.verify_kv_journal(N, events)

    def test_reader_revision_and_shard_refusal(self):
        lock = json.loads(V.pinned(ROOT, V.SOURCE, V.LOCK))
        reader = dict(checkpoint_revision='wrong', verified_shards={})
        with self.assertRaisesRegex(ValueError, 'identity'): V.verify_reader(reader, N, lock, 9707)

    def test_full_reader_coverage_mutations(self):
        lock = json.loads(V.pinned(ROOT, V.SOURCE, V.LOCK))
        shards = {x['path']: x['sha256'] for x in lock['expected_files'] if x['path'].endswith('.safetensors')}
        shard = next(iter(shards)); rows = []
        shapes = V.tensor_shapes(N)
        index = dict(weight_map={name: shard for name in shapes})
        for name, shape in shapes.items():
            if len(shape) == 1:
                spans = [(None, None, shape[0]*2)]
            elif name == 'model.embed_tokens.weight':
                spans = [(9707, 9708, shape[1]*2)]
            else:
                spans = [(lo, min(lo+256, shape[0]), (min(lo+256, shape[0])-lo)*shape[1]*2) for lo in range(0, shape[0], 256)]
            for lo, hi, size in spans:
                rows.append(dict(tensor=name, shape=shape, shard=shard, row_start=lo, row_stop=hi, bytes=size, sha256='f'*64))
        reader = dict(checkpoint_revision=lock['revision'], verified_shards=shards,
                      max_source_rows_per_read=256, images_written=False, downloads=False,
                      actual_hardware_memory_provider=False, reads=rows)
        self.assertEqual(V.verify_reader(reader, N, lock, 9707, index), len(shapes))
        changes = [
            ('source row gap', lambda r: r['reads'].pop(-2)),
            ('embedding wrong row', lambda r: r['reads'][0].update(row_start=11, row_stop=12)),
            ('wrong read bytes', lambda r: r['reads'][0].update(bytes=1)),
            ('wrong shape', lambda r: r['reads'][0].update(shape=[1])),
            ('wrong shard', lambda r: r['reads'][0].update(shard=list(shards)[1])),
            ('missing tensor', lambda r: r.update(reads=[x for x in r['reads'] if x['tensor'] != 'model.norm.weight'])),
            ('downloaded oracle', lambda r: r.update(downloads=True)),
        ]
        for name, change in changes:
            with self.subTest(name=name):
                changed = copy.deepcopy(reader); change(changed)
                with self.assertRaises(ValueError): V.verify_reader(changed, N, lock, 9707, index)


if __name__ == '__main__':
    unittest.main()
