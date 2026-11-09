"""Native selected kits retain every physical input without an unused die top."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys as GP
import gen_rtl as GR


def readset(directory, root):
    return {str(p.relative_to(directory)): p.read_bytes().replace(str(root).encode(), b'<OUT>')
            for p in directory.rglob('*') if p.is_file()}


class NativeKitOnly(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.raw = json.loads((HERE / 'examples/tiny_plan.json').read_text())

    def tearDown(self):
        self.temp.cleanup()

    def emit(self, out, **kwargs):
        return GP.write_phys(self.raw, out, trial=True, skip_ir=True, rc_cal=False, **kwargs)

    def test_selected_actual_kit_readset_matches_full_top_baseline(self):
        baseline, fast = self.root / 'baseline', self.root / 'selected'
        original = GR.write_rtl

        def force_top(*args, **kwargs):
            kwargs['emit_die_top'] = True
            return original(*args, **kwargs)

        with patch.object(GR, 'write_rtl', force_top):
            self.emit(baseline, types=['mid'])
        with patch.object(GR, 'die_top', side_effect=AssertionError('unused whole-die top')):
            self.emit(fast, types=['mid'])
        before, after = readset(baseline / 'mid', baseline), readset(fast / 'mid', fast)
        self.assertEqual(before, after)
        self.assertTrue({'config.mk', 'constraint.sdc', 'freeze.json', 'plan_pins.json',
                         'clock_taps.tcl', 'reset_taps.tcl'} <= before.keys())
        self.assertTrue(list((baseline / '_rtl').glob('*_top.sv')))
        self.assertFalse(list((fast / '_rtl').glob('*_top.sv')))
        wrapper = 'tiny_mid_part.sv'
        self.assertEqual((baseline / '_rtl' / wrapper).read_bytes(),
                         (fast / '_rtl' / wrapper).read_bytes())
        self.assertEqual((baseline / 'run_kit.sh').read_bytes(), (fast / 'run_kit.sh').read_bytes())
        print('NATIVE_ONLY_IDENTICAL selected_kit_files=' + str(len(before)))

    def test_unselected_full_die_call_retains_top(self):
        out = self.root / 'all'
        self.emit(out)
        self.assertTrue(list((out / '_rtl').glob('*_top.sv')))
        self.assertTrue((out / 'mid' / 'config.mk').is_file())

    def test_invalid_plan_retains_validation(self):
        self.raw['die']['period_ps'] = 0
        with self.assertRaisesRegex(GR.GenError, 'plan invalid'):
            self.emit(self.root / 'invalid', types=['mid'])
        self.assertFalse((self.root / 'invalid' / 'mid').exists())


if __name__ == '__main__':
    unittest.main()
