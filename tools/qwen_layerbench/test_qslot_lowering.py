"""Compiler mechanism checks; synthetic dates never qualify a production booking."""
import copy
import json
from pathlib import Path
import sys
import unittest
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
                   q_dd_pin_edges=list(range(base + 10, base + 74)), begin_pin_edge=base + 2,
                   q_committed_pin_edge=base + 77, commit_after_last_dd_edges=4,
                   sysface_to_qbank_edges=5, qbank_read_edges=4, svc_codec_to_wire_edges=2,
                   request_capture_edge=base + 100, retire_pin_edge=base + 300,
                   next_begin_pin_edge=base + 400, l_calendar_start_edge=base)
        messages += [dict(seg=seg, src='C', tx_port=0, kind=2, beat=b, wr=base + 200 + b)
                     for b in range(32)]
    return c, messages


class QslotLowering(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
