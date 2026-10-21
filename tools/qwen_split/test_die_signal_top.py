"""Exercise the actual GRT layer selection using a Tcl routing-API stub."""
import os
from pathlib import Path
import subprocess
import unittest


FLOW = Path(__file__).resolve().parents[1] / 'qwen_kv_die' / 'chain'
TEXT = (FLOW / 'grt.tcl').read_text()
BLOCK = TEXT[TEXT.index('set signal_top M8'):TEXT.index('set_global_routing_layer_adjustment')]


def run(top=None):
    env = os.environ.copy()
    env.pop('OT_DIE_SIGNAL_TOP_LAYER', None)
    if top is not None:
        env['OT_DIE_SIGNAL_TOP_LAYER'] = top
    script = 'proc set_routing_layers {args} {puts "ROUTE $args"}\n'
    script += 'if {[catch {\n' + BLOCK + '\n} err]} {puts stderr $err; exit 1}\n'
    return subprocess.run(['tclsh'], input=script, text=True, env=env, capture_output=True)


class SignalTopTest(unittest.TestCase):
    def test_owner_default_m8_keeps_m9_for_clock(self):
        r = run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('ROUTE -signal M4-M8 -clock M4-M9', r.stdout)

    def test_explicit_plan_reaches_routing_api(self):
        r = run('M7')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('ROUTE -signal M4-M7 -clock M4-M9', r.stdout)

    def test_invalid_layer_fails_before_routing(self):
        r = run('wrong')
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn('ROUTE ', r.stdout)


if __name__ == '__main__':
    unittest.main()
