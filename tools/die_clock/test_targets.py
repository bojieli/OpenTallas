import json
from pathlib import Path
import tempfile
import unittest
from build import load_targets


class Targets(unittest.TestCase):
    def test_supplied_targets_refuse_missing_or_invalid_native_r(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'kit.json'
            p.write_text(json.dumps({'masters': {'leaf': {'insertion_per_clock_pin_ps': {'ck': [140, 90, 120], 'zero': [0,0,0]}}}}))
            target = load_targets(p)
            self.assertEqual(target('leaf','ck'), [140,90,120])
            data = json.loads(p.read_text())
            data['masters']['leaf']['physical_insertion_per_clock_pin_ps'] = {'ck': [130,95,122]}
            p.write_text(json.dumps(data))
            self.assertEqual(load_targets(p)('leaf','ck'), [130,95,122])
            self.assertEqual(target('leaf','zero'), [0,0,0])  # explicit R0 retained for labelled diagnostics
            for master, pin in [('leaf','ckvb'), ('absent','ck')]:
                with self.assertRaisesRegex(ValueError, 'missing native insertion R'):
                    target(master,pin)
            p.write_text(json.dumps({'masters': {'bad': {'insertion_in_arcs_ps': [1, None, 3]}}}))
            with self.assertRaisesRegex(ValueError, 'invalid insertion R'):
                load_targets(p)('bad','ck')

if __name__ == '__main__':
    unittest.main()
