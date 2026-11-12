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


class HardIpAndTimingTest(unittest.TestCase):
    def test_hard_ip_rule_matches_release_tree(self):
        T = {'phy__t1': dict(hard=True, contents=[dict(module='m', status='reuse', lib='x_tt.lib')]),
             'phy_rework': dict(hard=True, contents=[dict(module='m', status='new', lib='x_tt.lib')]),
             'kv3_phy': dict(hard=True, contents=[dict(module='m', status='reuse', lib='x.lib')], ft_slots=[{}]),
             'soft': dict(hard=False, contents=[dict(module='m', status='reuse', lib='x.lib')])}
        self.assertEqual(sorted(design_index.hard_ip_types(T)), ['phy__t1'])

    def test_sta_setup_from_signoff_session(self):
        import design_export
        sess = '\n'.join(['proc so {k args} { puts "SO $k" }', 'proc ot_lib_load {c r} {', '  read_liberty x', '}', 'ot_lib_load TT /out/libraries.json',
                           'read_db /base/6_final.odb', 'set so_pg 0', 'foreach so_i [list] {', '  incr so_pg', '}', 'so PG 0',
                           'read_spef /base/6_final.spef', 'read_sdc /sdc/golden.sdc', '', 'set_propagated_clock [all_clocks]', 'so CORNER TT',
                           'report_checks'])
        out = design_export.sta_setup(sess, '5_2_route.odb').splitlines()
        self.assertIn('ot_lib_load TT /out/libraries.json', out)
        self.assertEqual(out[-4:], ['read_db /base/5_2_route.odb', 'read_spef /base/6_final.spef', 'read_sdc /sdc/golden.sdc', 'set_propagated_clock [all_clocks]'])
        self.assertNotIn('so PG 0', out); self.assertNotIn('  incr so_pg', out)
        self.assertIsNone(design_export.sta_setup('read_db /base/x.odb\nso CORNER TT', 'x.odb'))   # no SPEF: no STA


class TokenMapTest(unittest.TestCase):
    def test_class_rules_join_current_nodes(self):
        import token_design_map as M
        st = dict(state='signed', label='signed off')
        idx = dict(nodes={'s81.c.ot_dsrom_su_hcpost_lane_pr': dict(id='s81.c.ot_dsrom_su_hcpost_lane_pr', level='core', die='s81', name='ot_dsrom_su_hcpost_lane_pr', status=st),
                          's81.t.serdes__t3': dict(id='s81.t.serdes__t3', level='type', die='s81', name='serdes__t3', status=dict(state='failed'))})
        tok = dict(classes=[dict(id='su'), dict(id='hop'), dict(id='head')], nodes=[dict(id='a', cls='su', cycles=30), dict(id='b', cls='hop', cycles=60), dict(id='c', cls='head', cycles=10)])
        rules = dict(designs=dict(ds_rom=dict(dies=['s81'], classes=dict(su=dict(rules=[['s81', '^ot_dsrom_su_.*$']], confidence='named'),
                                                                          hop=dict(rules=[['s81', '^serdes(__.*)?$']], confidence='named')))))
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / 'ds_rom.json').write_text(json.dumps(tok))
            r = M.build(idx, d, rules)['designs']['ds_rom']
        self.assertEqual(r['classes']['su']['nodes'], ['s81.c.ot_dsrom_su_hcpost_lane_pr'])
        self.assertEqual(r['classes']['hop']['types'], 1)
        self.assertEqual(r['unmapped'], ['head'])
        self.assertAlmostEqual(r['coverage']['mapped'], 0.9)


if __name__ == '__main__':
    unittest.main()
