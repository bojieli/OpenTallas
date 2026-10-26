"""A changed placement syntax must not turn measured die hops into missing pins."""
import ast
import contextlib
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from hier_contract.pinreg_audit import hops_qwen_case
from qwen_tp8.reset_tree_plan import load
from kvsys_classify import place
import die_audit


class BulkPlaceConsumers(unittest.TestCase):
    def test_both_syntaxes_keep_actual_hops_and_contract_slots(self):
        rows = [('a', 10, 'R0'), ('b', 1000, 'MY')]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/'elements.lef').write_text('''MACRO leaf
SIZE 10 BY 10 ;
PIN p
LAYER M4 ;
RECT 4 4 6 6 ;
END p
END leaf
''')
            (p/'die.v').write_text('module test ();\n wire [0:0] n;\n leaf a (.p(n));\n leaf b (.p(n));\nendmodule\n')
            contract = {'slots': [{'name': n, 'kind': 'leaf', 'origin': {'x': x, 'y': 0}} for n, x, _ in rows]}
            measured = []
            for bulk in (False, True):
                (p/'place.tcl').write_text('\n'.join(
                    f'lappend _placements [list [$_blk findInst {n}] {x}.000 0.000 {o}]' if bulk else
                    f'ot_mts::place [$_blk findInst {n}] {x}.000 0.000 {o}' for n, x, o in rows)+'\n')
                meta, hops = hops_qwen_case(p, contract, 500)
                self.assertEqual(meta['contract_slots_placed_as_contract'], 2)
                self.assertEqual(meta['nets_without_pin_model'], 0)
                self.assertEqual(len(hops), 1)
                self.assertEqual(hops[0]['um'], 990)
                inst, nets, xy = load(p)
                self.assertEqual(xy('a', 'p'), (15, 5))
                self.assertEqual(xy('b', 'p'), (1005, 5))
                self.assertEqual(len(place(p/'place.tcl')), 2)
                out = p/'audit.json'
                with patch.object(sys, 'argv', ['die_audit', str(p), '--out', str(out)]), contextlib.redirect_stdout(io.StringIO()):
                    die_audit.main()
                report = json.loads(out.read_text())
                self.assertEqual(report['nopin_nets'], 0)
                self.assertEqual(report['hops_over_reach']['nets'], 1)
                measured.append((meta, hops, report))
            self.assertEqual(measured[0], measured[1])

    def test_legacy_explorer_hardcoded_script_reads_both_formats(self):
        # This legacy script runs at import and reads fixed /tmp paths. Exercise its
        # actual parser expression without executing unrelated HBM/S81 exporters.
        tree = ast.parse((ROOT/'tools/chip_explorer_extract_geo.py').read_text())
        exprs = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and n.args and
                 isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str) and 'findInst' in n.args[0].value]
        self.assertEqual(len(exprs), 1)
        code = compile(ast.Expression(exprs[0]), 'explorer-parser', 'eval')
        for ln in ['ot_mts::place [$_blk findInst a] 10.000 20.000 MY',
                   'lappend _placements [list [$_blk findInst a] 10.000 20.000 MY]']:
            self.assertEqual(eval(code, {'re': re, 'ln': ln}).groups(), ('a', '10.000', '20.000', 'MY'))


if __name__ == '__main__':
    unittest.main()
