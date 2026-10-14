import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pre_route_gate as PG


class SparseGateInputs(unittest.TestCase):
    def test_missing_transitive_committed_hook_rejects_before_admission(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for p, text in [('physical/kit/hook.tcl', 'source /src/physical/deps/hold.tcl\n'),
                            ('physical/deps/hold.tcl', 'puts hold\n')]:
                f = root / p
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(text)
            for args in [('init', '-q'), ('add', 'physical'),
                         ('-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-qm', 'inputs')]:
                subprocess.run(['git', '-C', td, *args], check=True)
            kd = root / 'physical/kit'
            (kd / 'floorplan.json').write_text(json.dumps({'referenced': ['physical/kit/hook.tcl']}))
            with patch.object(PG, 'ROOT', root), patch.object(PG, 'DAEMON_TREE', root / 'daemon'), patch.object(PG, 'SHIP_HELPERS', ()):
                self.assertEqual(PG.absent_working_inputs({'physical/kit/hook.tcl'}), [])
                (root / 'physical/deps/hold.tcl').unlink()
                gate = PG.Gate()
                with patch.object(PG.subprocess, 'run', wraps=subprocess.run) as run:
                    PG.remote(gate, kd, {}, 'auto', 60, 16, True)
                self.assertEqual(gate.verdict, 'FAIL')
                self.assertIn('physical/deps/hold.tcl', gate.items[0]['message'])
                self.assertFalse(any(call.args[0][0] == 'ot-run' for call in run.call_args_list))
                daemon = root / 'daemon'
                (daemon / 'physical/deps').mkdir(parents=True)
                (daemon / 'physical/deps/hold.tcl').write_text('puts overlay\n')
                with patch.object(PG, 'DAEMON_TREE', daemon), patch.object(PG, 'SHIP_HELPERS', ('physical/deps/hold.tcl',)):
                    self.assertEqual(PG.absent_working_inputs({'physical/kit/hook.tcl'}), [])
