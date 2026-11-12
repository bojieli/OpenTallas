"""EXPLORER-2: the design node index service (name resolution) and the memory-macro rule of design_index.py."""
import json, os, pathlib, sys, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import design_index, design_service


def _index():
    st = dict(state='signed', label='signed off')
    return dict(schema='opentallas.fleet_viz.design_index.v1', generated=0, states=['signed'], dies=['s81'], nodes={
        's81': dict(id='s81', level='die', die='s81', name='s81', label='S81', children=['s81.t.leaf__t1'], counts={}, status=st,
                    plan=dict(path='p', outline=[10, 10], partitions=[['fW0_p1_b0', 's81.t.leaf__t1', 0, 0, 5, 5, 'R0']])),
        's81.t.leaf__t1': dict(id='s81.t.leaf__t1', level='type', die='s81', name='leaf__t1', status=st, children=['s81.c.ot_vq'],
                               plan=dict(hard_cores=[['u_vq', 's81.c.ot_vq', 'ot_vq', 0, 0, 1, 1, 'R0']])),
        's81.c.ot_vq': dict(id='s81.c.ot_vq', level='core', die='s81', name='ot_vq', status=st, plan=dict(used_by=['s81.t.leaf__t1'])),
    })


class DesignIndexTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        p = pathlib.Path(self.d.name) / 'design_index.json'
        p.write_text(json.dumps(_index()))
        self.old = design_service.INDEX; design_service.INDEX = p
        self.s = design_service.Service(log=lambda *a: None)

    def tearDown(self):
        design_service.INDEX = self.old; self.d.cleanup()

    def test_resolve_names(self):
        self.assertEqual(self.s.resolve('ot_vq'), ['s81.c.ot_vq'])
        self.assertEqual(self.s.resolve('leaf__t1'), ['s81.t.leaf__t1'])
        self.assertEqual(self.s.resolve('fW0_p1_b0'), ['s81.t.leaf__t1'])          # partition instance -> its type
        self.assertEqual(self.s.resolve('kl_ot_vq_rt6e'), ['s81.c.ot_vq'])         # signed view name -> core
        self.assertEqual(self.s.resolve('leaf__t1__cl0123abcd'), ['s81.t.leaf__t1'])  # clone suffix
        self.assertEqual(self.s.resolve('dsfd_svcio_ad'), [])                       # October element: unresolved, not guessed

    def test_node_children_and_users(self):
        n = self.s.node('s81.t.leaf__t1')
        self.assertIn('s81.c.ot_vq', n['children'])
        self.assertEqual(n['placements'][0][0], 'fW0_p1_b0')
        self.assertIn('s81.t.leaf__t1', self.s.node('s81.c.ot_vq')['users'])

    def test_memory_macros_are_not_design_nodes(self):
        self.assertTrue(design_index.is_mem_macro(dict(module='ot_sram_1r1w_512x128_m4_r0c0')))
        self.assertTrue(design_index.is_mem_macro(dict(module='x', lef='physical/asap7_memory_macros/x.lef')))
        self.assertFalse(design_index.is_mem_macro(dict(module='ot_s81sl_vq')))


if __name__ == '__main__':
    unittest.main()
