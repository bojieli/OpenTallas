"""Owner's M5 scope: die horizontal capacity, direct placed tiles only."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'reroute_batch.py'
spec = importlib.util.spec_from_file_location('reroute_batch', MODULE)
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)


class ScopeTests(unittest.TestCase):
    def test_cluster_child_and_vertical_cut_do_not_qualify(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cuts = root / 'cuts.json'
            cuts.write_text(json.dumps({'fine': [
                {'ax': 'x', 'pos': 5, 'win': [0, 10], 'util': .7},
                {'ax': 'y', 'pos': 5, 'win': [20, 30], 'util': .8}]}))
            placement = root / 'rom_tp8b.json'
            placement.write_text(json.dumps({'insts': [
                {'m': 'cluster', 'x': 0, 'y': 0, 'w': 10, 'h': 10},
                {'m': 'vertical_only', 'x': 20, 'y': 0, 'w': 10, 'h': 10}]}))
            cfg = root / 'physical/qwen_die_masters/cfg'
            cfg.mkdir(parents=True)
            (cfg / 'cluster.env').write_text('EXTRA=(--macro-view child=physical/child)')
            with patch.object(rr, 'ROOT', root):
                scope = rr.window_scope(cuts, placement, [], .6)
            self.assertEqual(set(scope), {'cluster'})
            self.assertEqual(scope['cluster'][0]['frees'], 'M6')

    def test_grt_contract_excludes_hardened_children(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            placement = root / 'contract.json'
            placement.write_text(json.dumps({'slots': [
                {'name': 'die', 'kind': 'die'},
                {'name': 'c', 'parent': 'die', 'cell': 'cluster',
                 'origin': {'x': 0, 'y': 0}, 'outline': {'w': 10, 'h': 10}},
                {'name': 'child', 'parent': 'c', 'cell': 'child',
                 'origin': {'x': 1, 'y': 1}, 'outline': {'w': 5, 'h': 5}}]}))
            report = root / 'overflow.json'
            report.write_text(json.dumps({'boxes': [{'rect': [0, 0, 10, 10], 'layer': 'M6'}]}))
            scope = rr.window_scope(None, None, [f'{report}:{placement}'], .6)
            self.assertEqual(set(scope), {'cluster'})

    def test_stale_committed_kit_cannot_bypass_scope_at_submit(self):
        with patch.object(rr, 'records', return_value=({}, {}, set())), patch.object(rr, 'log'):
            rr.submit({'tiles': {'child': {'state': 'committed'}}}, {})
            # No kit or intake is touched: stale state has no current die evidence.


if __name__ == '__main__':
    unittest.main()
