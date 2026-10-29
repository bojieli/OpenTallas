import copy
from types import SimpleNamespace as NS
import unittest

import head_prepare_params as HP


class CoherentParameters(unittest.TestCase):
    def setUp(self):
        cells = [NS(path=path, module=master, ytype=master, params={})
                 for path, master in HP.SELECTED.items()]
        self.ctx = NS(ab={}, F=NS(cells=cells),
                      cell_index=lambda: {c.path:i for i,c in enumerate(cells)},
                      param_defaults={(c.ytype,c.module):{k:'0' for k in HP.REQUIRED[c.path]}
                                      for c in cells})
        self.profile = dict(schema=HP.SCHEMA, selected_masters=dict(HP.SELECTED))

    def test_historical_bind_unchanged_without_selected_profile(self):
        self.assertEqual(HP.regen(self.ctx), ({},None))

    def test_actual_selected_defaults_zero_become_three_explicit_ones(self):
        self.ctx.ab['qwen_head_prepare_profile'] = self.profile
        params, record = HP.regen(self.ctx)
        self.assertEqual(params, HP.REQUIRED)
        self.assertEqual(set(record['original'].values()), {0})
        self.assertEqual(record['native_embedding_terminal_index']['delta'], 20)
        # The binder owns mutation; the helper never rewrites cells or defaults.
        self.assertTrue(all(not c.params for c in self.ctx.F.cells))
        for c in self.ctx.F.cells:
            c.params.update({k:str(v) for k,v in params[c.path].items()})
        self.assertEqual(HP.regen(self.ctx)[0], params)

    def test_wrong_selected_source_is_not_upgraded(self):
        self.ctx.ab['qwen_head_prepare_profile'] = self.profile
        self.ctx.F.cells[1].module='historical_native'
        with self.assertRaisesRegex(ValueError, 'selected master'):
            HP.regen(self.ctx)

    def test_profile_and_actual_declared_parameter_both_required(self):
        self.ctx.ab['qwen_head_prepare_profile'] = copy.deepcopy(self.profile)
        self.ctx.ab['qwen_head_prepare_profile']['selected_masters']['sys_face']='historical_face'
        with self.assertRaisesRegex(ValueError, 'selection'):
            HP.regen(self.ctx)
        self.ctx.ab['qwen_head_prepare_profile'] = self.profile
        self.ctx.param_defaults[('qfd_d2d_static_ovl_sf7_obs1','qfd_d2d_static_ovl_sf7_obs1')]={}
        with self.assertRaisesRegex(ValueError, 'absent/nonboolean'):
            HP.regen(self.ctx)


if __name__ == '__main__':
    unittest.main()
