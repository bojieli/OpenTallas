from pathlib import Path
import unittest
from unittest.mock import patch

import v16_views as views


class SparseSuViewTest(unittest.TestCase):
    def choose(self, requested, specs):
        candidates = [(Path('/fixture') / str(i), f'{i}.lef', f'{i}.tt', f'{i}.ff') for i in range(len(specs))]
        with patch.object(views, 'real_views', return_value=candidates), \
             patch.object(views, 'lef_ports', return_value={'clk': 1}), \
             patch.object(views, 'spec_params', side_effect=lambda p: specs[int(p.name)]):
            return views.real_view('ot_hbm_static_cfg_collar', ports={'clk': 1}, params=requested)

    def test_sparse_contract_rejects_nonempty_legacy_dense_spec(self):
        self.assertIsNone(self.choose({'PAGE_W': 12, 'SPARSE_SU': 1}, [{'PAGE_W': 12, 'NS': 1}]))

    def test_dense_contract_keeps_legacy_view(self):
        self.assertEqual(self.choose({'PAGE_W': 12}, [{'PAGE_W': 12, 'NS': 1}])[0], Path('/fixture/0'))

    def test_sparse_contract_selects_explicit_sparse_successor(self):
        got = self.choose({'PAGE_W': 12, 'SPARSE_SU': 1}, [{'PAGE_W': 12}, {'PAGE_W': 12, 'SPARSE_SU': 1}])
        self.assertEqual(got[0], Path('/fixture/1'))

    def test_default_dense_contract_rejects_sparse_only_view(self):
        self.assertIsNone(self.choose({'PAGE_W': 12}, [{'PAGE_W': 12, 'SPARSE_SU': 1}]))


if __name__ == '__main__':
    unittest.main()
