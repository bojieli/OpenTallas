#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path
import q_readiness as Q
FX = Path(__file__).resolve().parents[2] / 'results/rtl/qwen_layer_tput_1018/fixtures/dv2f18dh2_qready'

class ProductionReadiness(unittest.TestCase):
    def report(self, die=None, lanes=None):
        return Q.inspect(die or FX/'die.v', lanes or FX/'fwd_lanes.json', '0d4c9808f')

    def test_actual_pins_and_ages(self):
        r = self.report()
        self.assertEqual([r['pins'][b]['age_edges'] for b, *_ in Q.PATHS], [20, 2, 2])
        self.assertEqual(r['pins']['dvw_dd_wo']['frames'], 26)
        self.assertEqual(r['verdict'], 'BLOCKED')
        self.assertIsNone(r['producer_ready'])
        Q.require_advance(r, 0)

    def test_unproven_advance_rejected(self):
        with self.assertRaisesRegex(ValueError, 'advance1 rejected.*production PW1024'):
            Q.require_advance(self.report(), 1)

    def test_synthetic_ready_cannot_admit_production(self):
        r = self.report()
        r.update(producer_ready=[0]*32, request_ages=list(range(32)))
        with self.assertRaisesRegex(ValueError, 'advance1 rejected'):
            Q.require_advance(r, 1)

    def test_wrong_straps_rejected(self):
        text = (FX/'die.v').read_text()
        text = text.replace('.k1(n_ftk_dvw_dd_wo_hi)', '.k1(n_ftk_dvw_dd_wo_lo)')
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)/'die.v'; p.write_text(text)
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                self.report(die=p)

    def test_wrong_endpoint_rejected(self):
        text = (FX/'die.v').read_text().replace('.dd_i(n_dvw_dd_wo__r26)', '.dd_i(n_dvw_dd_wo__r25)')
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)/'die.v'; p.write_text(text)
            with self.assertRaisesRegex(ValueError, 'wrong consumer pin'):
                self.report(die=p)

    def test_torn_request_rejected(self):
        rows = json.loads((FX/'fwd_lanes.json').read_text())
        row = next(r for r in rows['lanes'] if r['bid'] == 'sf_q_slot_beat')
        row['E'] += 8  # same K is insufficient to establish equal arrival age
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)/'lanes.json'; p.write_text(json.dumps(rows))
            with self.assertRaisesRegex(ValueError, 'torn Q request'):
                self.report(lanes=p)

if __name__ == '__main__':
    unittest.main(verbosity=2)
