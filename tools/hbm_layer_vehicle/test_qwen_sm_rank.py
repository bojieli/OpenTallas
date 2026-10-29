"""Exercise emit -> component lowering with distinct captured-operand ranks."""
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from hbm_layer_vehicle import qwen_layer_images as Q


class RankLoweringTest(unittest.TestCase):
    def test_requested_ranks_reach_sm_operand_compiler(self):
        seen = []
        lowerer = types.ModuleType('hbm_layer_vehicle.sm_slice_lower')

        def compile_sm(kv, layer, sm, *, rank, tags):
            seen.append((rank, layer, sm, tags))
            return {'captured_rank': rank}

        def lower(compile_k, nsm, layer, boundary, **kw):
            value = compile_k(0)
            self.assertIn(f"rank {value['captured_rank']}", kw['provenance'])
            return value, [{'rank': value['captured_rank']}], {'events': 1}

        lowerer.compile_qwen_sm = compile_sm
        lowerer.lower_comps_refresh = lower
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'boundary.json').write_text('{}')
            args = types.SimpleNamespace(ranks='0,5', operands=root / 'operands.npz', stage='L0',
                                         out=root / 'out', boundary=root / 'boundary.json', variant='landed',
                                         safe_calendar=False, sm_kv=root / 'captured', sm_nev=8)

            def compile_rank(stage, rank, vm, out, **kw):
                out.mkdir(parents=True)
                (out / 'replay.json').write_text('{}')
                return {'records': [{'op': 'SM.MATVEC', 'L': 2, 'tag': 'qkv', 'status': 'unlowered'}]}, {'events': []}

            with patch.dict('sys.modules', {'hbm_layer_vehicle.sm_slice_lower': lowerer}), \
                    patch.object(Q, 'SparseVM', return_value=None), patch.object(Q, 'compile_rank', compile_rank):
                Q.cmd_emit(args)
            self.assertEqual(seen, [(0, 2, 0, ('qkv',)), (5, 2, 0, ('qkv',))])
            for rank in (0, 5):
                out = args.out / 'L0' / f'r{rank}'
                replay = json.loads((out / 'sm_L2_qkv/replay.json').read_text())
                manifest = json.loads((out / 'manifest.json').read_text())
                self.assertEqual(replay['captured_rank'], rank)
                self.assertEqual(manifest['records'][0]['sm_record']['rank'], rank)
                self.assertEqual(manifest['counts'], {'emitted': 1})


if __name__ == '__main__':
    unittest.main()
