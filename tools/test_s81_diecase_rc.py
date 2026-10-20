#!/usr/bin/env python3
"""A failed strict bind must stop a shell-driven die chain before physical work."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent / 's81_dv'))
import dv_diecase

class BindExitTests(unittest.TestCase):
    def invoke(self, record):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan = root / 'plan.json'
            plan.write_text(json.dumps(dict(facts=dict(die_um=[100,100]), blocks=[], links=[])))
            argv = ['dv_diecase', '--plan', str(plan), '--out', str(root/'case'), '--bind', 'real']
            with patch.object(sys, 'argv', argv), patch('dv_bind.emit', return_value=record) as emit, contextlib.redirect_stdout(io.StringIO()):
                dv_diecase.main()
                emit.assert_called_once()

    def test_failed_bind_returns_its_failure_to_shell(self):
        with self.assertRaises(SystemExit) as caught:
            self.invoke(dict(port_bind_rc=2))
        self.assertEqual(caught.exception.code,2)

    def test_killed_or_missing_bind_verdict_is_not_success(self):
        for record in (dict(port_bind_rc=-15), {}):
            with self.subTest(record=record), self.assertRaises(SystemExit) as caught:
                self.invoke(record)
            self.assertEqual(caught.exception.code,1)

    def test_successful_bind_remains_successful(self):
        self.invoke(dict(port_bind_rc=0))

if __name__ == '__main__':
    unittest.main()
