"""Compiler mechanism checks; synthetic dates never qualify a production booking."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest import mock
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import layer_compile as LC
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qwen_split'))
import sys_face_image as SFI


def fixture():
    c = json.loads(Path(__file__).with_name('qslot_contract.template.json').read_text())
    c['status'] = 'SYNTHETIC_COMPILER_TEST'
    for proof in c['proofs'].values():
        proof.update(path='synthetic-test-only.json', sha256='a' * 64)
    messages = []
    for row in c['segments']:
        seg = row['segment']; base = 1000 * seg
        row.update(context_identity=f'synthetic-context-seg{seg}', commit_id=f'synthetic-commit-seg{seg}',
                   identity=dict(epoch=9, generation=0, user=0, layer=seg, token=123457, position=8191),
                   q_dd_pin_edges=list(range(base + 10, base + 74)), begin_pin_edge=base + 2,
                   q_committed_pin_edge=base + 77, commit_after_last_dd_edges=4,
                   sysface_to_qbank_edges=5, qbank_read_edges=4, svc_codec_to_wire_edges=2,
                   request_capture_edge=base + 100, retire_pin_edge=base + 300,
                   next_begin_pin_edge=base + 400, l_calendar_start_edge=base,
                   paired_segment_start_epoch_edge=100, l_start_decode_edges=1,
                   l_start_driver_event=[base + 99, 0, 65 if seg == 1 else 66])
        messages += [dict(seg=seg, src='C', tx_port=0, kind=2, beat=b, wr=base + 200 + b)
                     for b in range(32)]
    return c, messages


class QslotLowering(unittest.TestCase):
    def authority_fixture(self, root):
        c, messages = fixture()
        c['status'] = 'QUALIFIED_SOURCE_GEN_EDGES'
        c['source_revision'] = 'b' * 40
        gen = root / 'die.v'; gen.write_text('// synthetic compiler test GEN, never deployment evidence\n')
        params = root / 'params.json'
        params.write_text(json.dumps({'masters': {'qfd_native59_dv_headprep_obs1': c['params'],
                                                         c['l_player']['master']: {'L_CONTEXTS': 0}}}))
        c['gen_sha256'] = LC.sha(gen); c['gen_params_sha256'] = LC.sha(params)
        sources = dict(qbank='rtl/qwen_split/qfd_native59_qbank.sv',
                       wrapper='rtl/qwen_split/qfd_native59_dv_headprep_obs1.sv',
                       service='rtl/qwen_split/qfd_native59_svc_obs1.sv',
                       macro='physical/asap7_memory_macros/ot_sram_1r1w_32x512_m1/ot_sram_1r1w_32x512_m1.v',
                       sysface='rtl/qwen_split/qfd_sys_face_ovl_fault1.sv')
        text = {p: '// synthetic test source ' + p + '\n' for p in sources.values()}
        c['source_sha256'] = {k: hashlib.sha256(text[v].encode()).hexdigest() for k, v in sources.items()}
        metadata = ('source_revision', 'gen_sha256', 'gen_params_sha256', 'source_sha256',
                    'clock', 'origin', 'params', 'endpoint_bundle', 'l_player')
        proofs = {}
        for name in c['proofs']:
            if name == 'qbank_read':
                p = dict(schema='opentallas.qwen.qbank-pin-edges.v1',
                         status='QUALIFIED_COMPONENT_SOURCE_PIN_EDGES_ONLY',
                         qbank_sha256=c['source_sha256']['qbank'], macro_sha256=c['source_sha256']['macro'],
                         params=dict(QB_ALIGN=1, QB_LOCAL32=c['params']['QB_LOCAL32']),
                         slot_to_emit_edges=4, last_dd_to_committed_edges=4)
            else:
                p = {k: copy.deepcopy(c[k]) for k in metadata}
                p.update(schema='opentallas.qwen.qslot-authority.v1', authority=name,
                         status='QUALIFIED_SOURCE_GEN_EDGES', segments=copy.deepcopy(c['segments']))
                for row in p['segments']:
                    row['d2d_write_capture_edges'] = [m['wr'] for m in messages if m['seg'] == row['segment']]
            proofs[name] = p
        contract_path = root / 'contract.json'

        def write():
            for name, p in proofs.items():
                path = root / (name + '.json'); path.write_text(json.dumps(p, sort_keys=True))
                c['proofs'][name] = dict(path=path.name, sha256=LC.sha(path))
            contract_path.write_text(json.dumps(c))

        def read():
            with mock.patch.object(LC.subprocess, 'check_output', return_value=c['source_revision'] + '\n'), \
                    mock.patch.object(LC, 'git_show', side_effect=lambda _, p: text[p]):
                return LC.read_qslot_contract(contract_path, 'synthetic-source', params, gen)
        write()
        return c, messages, proofs, write, read

    def test_contiguous_booking_enters_existing_rtl_calendar_format(self):
        c, messages = fixture()
        booking = LC.lower_qslots(c, messages, allow_test=True)
        for row in booking['bookings']:
            self.assertEqual(row['cadence'], 1)
            self.assertEqual(row['extra_idle_edges'], 0)
            self.assertEqual([b for _, _, b in row['events']], list(range(32)))
            words = SFI.compile_cal('L', row['events'])
            self.assertEqual(len(words), 1)
            word = words[0]
            self.assertEqual((word >> 14) & 7, 2)
            self.assertEqual((word >> 5) & 31, 0)
            self.assertEqual(word & 31, 31)
            self.assertEqual([v + c['segments'][row['segment']]['svc_codec_to_wire_edges']
                              for v in row['qbank_emit_edges']], row['d2d_write_capture_edges'])

    def test_production_rejects_synthetic_dates_and_incomplete_template(self):
        c, m = fixture()
        with self.assertRaisesRegex(ValueError, 'qualification required'):
            LC.lower_qslots(c, m)
        incomplete = json.loads(Path(__file__).with_name('qslot_contract.template.json').read_text())
        with self.assertRaises(ValueError):
            LC.lower_qslots(incomplete, m)
        with self.assertRaisesRegex(ValueError, 'actual source/GEN'):
            LC.read_qslot_contract(Path(__file__).with_name('qslot_contract.template.json'), 'HEAD', None)

    def test_missing_ages_identity_and_proofs_fail_closed(self):
        c, m = fixture()
        for key in ('q_committed_pin_edge', 'sysface_to_qbank_edges', 'qbank_read_edges',
                    'svc_codec_to_wire_edges', 'retire_pin_edge', 'commit_id', 'context_identity'):
            bad = copy.deepcopy(c); bad['segments'][0][key] = None
            with self.subTest(key=key), self.assertRaises(ValueError):
                LC.lower_qslots(bad, m, allow_test=True)
        for proof in c['proofs']:
            bad = copy.deepcopy(c); del bad['proofs'][proof]
            with self.subTest(proof=proof), self.assertRaises(ValueError):
                LC.lower_qslots(bad, m, allow_test=True)

    def test_early_commit_request_retire_and_noncontiguous_burst_rejected(self):
        c, m = fixture()
        edits = [('q_committed_pin_edge', 76), ('request_capture_edge', 77),
                 ('retire_pin_edge', 230), ('next_begin_pin_edge', 220)]
        for key, value in edits:
            bad = copy.deepcopy(c); bad['segments'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                LC.lower_qslots(bad, m, allow_test=True)
        bad = copy.deepcopy(m); bad[5]['wr'] += 1
        with self.assertRaisesRegex(ValueError, 'contiguous'):
            LC.lower_qslots(c, bad, allow_test=True)
        bad = copy.deepcopy(c); bad['params']['QB_ALIGN'] = 0
        with self.assertRaisesRegex(ValueError, 'aligned'):
            LC.lower_qslots(bad, m, allow_test=True)

    def test_dual_l_composition_books_each_context_in_its_own_origin(self):
        c, messages = fixture()
        c['l_player'] = dict(master='qfd_sys_face_ovl_lctx1',
                            source='rtl/qwen_split/qfd_sys_face_ovl_lctx1.sv', contexts=1)
        c['segments'][0]['paired_segment_start_epoch_edge'] = 2200
        c['segments'][0]['l_start_driver_event'][0] = 2199
        for m in messages:
            if m['seg'] == 1: m['wr'] += 2
        booking = LC.lower_qslots(c, messages, allow_test=True)
        for seg in (0, 1):
            base = 1000 * seg
            messages += [dict(seg=seg, src='C', tx_port=3, kind=4, beat=b, cyc=base+300+10*b)
                         for b in range(4)]
            messages += [dict(seg=seg, src='K', tx_port=0, kind=3, beat=b,
                              cyc=base+400+b, arrive=base+400+b) for b in range(32)]
        program = dict(program=dict(layers=[dict(start=1096)], emb_send=[10]), messages=messages)
        starts = sum((0 if i == 0 else 2196 if i == 1 else 2300+100*i) << (20*i) for i in range(36))
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / 'calendar.svh'
            image.write_text("D2D_TOKEN_PERIOD = 10000; D2D_FIRST_TOKEN = 1000; " +
                             "D2D_CAL_START = 720'h" + format(starts, 'x') + ';')
            result = LC.sys_face_events(program, image, dict(CS_X3S=3, CS_RXV=2), {}, 0, 8, booking)
        self.assertNotIn('L', result)
        self.assertNotIn('L_compiled', result)
        self.assertEqual(result['L0'][0][0], result['L1'][0][0] + 2)
        _, record = SFI.build(result, SFI.bench_program())
        self.assertEqual(record['l_contexts']['segment1_base'], 7)
        bad = copy.deepcopy(booking); bad['bookings'][0]['l_start_driver_event'][0] += 1
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / 'calendar.svh'
            image.write_text("D2D_TOKEN_PERIOD = 10000; D2D_FIRST_TOKEN = 1000; " +
                             "D2D_CAL_START = 720'h" + format(starts, 'x') + ';')
            with self.assertRaisesRegex(ValueError, 'executing T programme'):
                LC.sys_face_events(program, image, dict(CS_X3S=3, CS_RXV=2), {}, 0, 8, bad)

    def test_l_start_requires_explicit_stage_and_matching_origin(self):
        c, messages = fixture()
        for change in ('mark', 'origin', 'stage'):
            bad = copy.deepcopy(c)
            if change == 'mark': bad['segments'][0]['l_start_driver_event'][1] = 5
            elif change == 'origin': bad['segments'][0]['paired_segment_start_epoch_edge'] += 1
            else: bad['segments'][1]['l_start_driver_event'][2] = 66
            with self.subTest(change=change), self.assertRaises(ValueError):
                LC.lower_qslots(bad, messages, allow_test=True)

    def test_dual_l_encoder_uses_shared_store_and_explicit_base(self):
        # One compressed Q burst plus four KV and two visibility entries each.
        def pattern(start):
            return ([[start + b, 2, b] for b in range(32)] +
                    [[start + 40 + 2*k, 3, k] for k in range(4)] +
                    [[start + 60, 4, 0], [start + 70, 4, 1]])
        events = dict(first_token=1000, T=[], E=[], L0=pattern(10), L1=pattern(20))
        _, record = SFI.build(events, SFI.bench_program())
        self.assertEqual(record['l_contexts']['L0_entries'], 7)
        self.assertEqual(record['l_contexts']['L1_entries'], 7)
        self.assertEqual(record['l_contexts']['segment1_base'], 7)
        self.assertIn(dict(target=4, addr=128, data=7), record['cfg_writes'])
        self.assertEqual(len(record['calendars']['L']), 14)
        with self.assertRaisesRegex(ValueError, 'ambiguous L alias'):
            SFI.build(dict(events, L=events['L0']), SFI.bench_program())
        too_big = dict(events, L0=[[10+4*k, 4, k % 2] for k in range(20)],
                       L1=[[10+4*k, 4, k % 2] for k in range(20)])
        with self.assertRaisesRegex(ValueError, 'shared NE32'):
            SFI.build(too_big, SFI.bench_program())

    def test_typed_authorities_bind_source_gen_clock_epoch_context_and_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, messages, proofs, write, read = self.authority_fixture(Path(tmp))
            validated = read()
            self.assertEqual(len(LC.lower_qslots(validated, messages)['bookings']), 2)
            date_keys = dict(commit_identity='q_committed_pin_edge', sysface_bundle='sysface_to_qbank_edges',
                             svc_codec_wire='svc_codec_to_wire_edges', tx_retire='retire_pin_edge')
            for name, date_key in date_keys.items():
                original = copy.deepcopy(proofs[name])
                for change in ('date', 'epoch', 'context', 'source', 'gen', 'clock', 'status', 'bundle', 'l_player'):
                    proofs[name] = copy.deepcopy(original); p = proofs[name]
                    if change == 'date': p['segments'][0][date_key] += 1
                    elif change == 'epoch': p['segments'][0]['identity']['epoch'] += 1
                    elif change == 'context': p['segments'][0]['context_identity'] += '-another-context'
                    elif change == 'source': p['source_sha256']['service'] = '9' * 64
                    elif change == 'gen': p['gen_sha256'] = '9' * 64
                    elif change == 'clock': p['clock'] = 'ck_hr'
                    elif change == 'status': p['status'] = 'COMPILED_NOT_QUALIFIED'
                    elif change == 'bundle': p['endpoint_bundle']['members'] = ['q_slot']
                    elif change == 'l_player': p['l_player']['contexts'] = 1
                    # Deliberately recompute the file hash: content authority,
                    # not a stale digest, must reject each changed claim.
                    write()
                    with self.subTest(authority=name, change=change), self.assertRaises(ValueError):
                        read()
                proofs[name] = original; write()
            proofs['svc_codec_wire']['segments'][0]['d2d_write_capture_edges'][0] += 1
            write()
            with self.assertRaisesRegex(ValueError, 'executing paired Q programme'):
                LC.lower_qslots(read(), messages)


if __name__ == '__main__':
    unittest.main()
