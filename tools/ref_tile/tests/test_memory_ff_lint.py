"""MEMORY-FF gate lint (ROOT 2026-10-17): yosys MEMORY_DFF folding a register into an inferred ROM read port is reported."""
import sys, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parents[1]), str(HERE.parents[1] / 'closure_loop')]
import pre_route_gate as G

LOG = ("GATE_MEMFF Converted 1 switch.\n"
       "GATE_MEMFF Checking read port `$auto$proc_rom.cc:155:do_switch$5'[0] in module `\\t': merging output FF to cell.\n")


class MemoryFF(unittest.TestCase):
    def test_merge_warns_with_module_and_port(self):
        g = G.Gate(); G.check_memory_ff(g, LOG)
        self.assertEqual([(i['severity'], i['check']) for i in g.items], [('WARN', 'memory_ff')])
        self.assertIn('t:$auto$proc_rom.cc:155:do_switch$5[0]', g.items[0]['message'])

    def test_rom_without_merge_is_info_and_silence_is_silent(self):
        g = G.Gate(); G.check_memory_ff(g, "GATE_MEMFF Converted 3 switch.\n")
        self.assertEqual(g.items[0]['severity'], 'INFO')
        g = G.Gate(); G.check_memory_ff(g, "GATE_AREA 12\n")
        self.assertEqual(g.items, [])

    def test_remote_script_emits_marker(self):
        self.assertIn("sed 's/^/GATE_MEMFF /'", (HERE.parent / 'pre_route_gate.py').read_text())


if __name__ == '__main__':
    unittest.main()
