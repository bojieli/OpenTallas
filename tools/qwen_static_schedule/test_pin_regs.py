import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_static_schedule import pin_regs as P
from qwen_static_schedule.calendar import ScheduleError


class PinRegs(unittest.TestCase):
    def kit(self, root, name, recipe, regs=None):
        d = root / 'physical/ref_tile' / name
        d.mkdir(parents=True)
        (d / 'kit.env').write_text(f'RECIPE={recipe}\n')
        if regs is not None:
            (d / 'pin_regs.json').write_text(json.dumps(regs))

    def test_tt_core_to_scale_seam(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            regs = dict(schema='opentallas.ref_tile.pin_regs.v1', enable=True, clock_ports=['clk'], exclude='', reset='',
                        latency_cycles=dict(input=1, output=1))
            self.kit(r, 'core', 3, regs)
            self.kit(r, 'scale', 3, regs)
            self.kit(r, 'legacy', 2)
            self.assertEqual(P.seam_edges('core', 'mx_data', 'scale', 'mx_data', 0, r), 2)    # Q-ELEM fs3: +2
            self.assertEqual(P.seam_edges('core', 'mx_data', 'legacy', 'x', 3, r), 4)
            self.assertEqual(P.port_edges('core', 'clk', 'input', r), 0)
            regs2 = dict(regs, exclude='dbg_.*')
            self.kit(r, 'ex', 3, regs2)
            self.assertEqual(P.port_edges('ex', 'dbg_x', 'output', r), 0)
            self.kit(r, 'missing', 3)
            with self.assertRaises(ScheduleError):
                P.port_edges('missing', 'a', 'input', r)
            with self.assertRaises(ScheduleError):
                P.seam_edges('core', 'a', 'scale', 'b', -1, r)


if __name__ == '__main__':
    unittest.main()
