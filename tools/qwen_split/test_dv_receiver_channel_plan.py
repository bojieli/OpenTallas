import unittest
from dv_receiver_channel_plan import plan


class ChannelPlanTest(unittest.TestCase):
    def setUp(self):
        self.source = dict(insts=[dict(n='service', x=0., y=0, w=100, h=100),
                                 dict(n='dvs_E0', x=500., y=0, w=500., h=200),
                                 dict(n='dvs_E1', x=1000., y=0, w=500., h=200),
                                 dict(n='c16_E1_0', x=1000., y=300, w=450., h=200)])

    def test_receiver_and_cluster_move_together_services_stay(self):
        out = plan(self.source, 'dvs_E1', 129.6, 43.2, 32893.776, 24267.224)
        self.assertEqual([i['x'] for i in out['insts']], [0., 456.8, 1086.4, 1086.4])
        self.assertEqual(self.source['insts'][2]['x'], 1000.)
        self.assertEqual(out['receiver_channel_plan']['proposed_die_um'][0], 32980.176)

    def test_uncompensated_growth_fails_reticle(self):
        with self.assertRaisesRegex(ValueError, 'reticle'):
            plan(self.source, 'dvs_E1', 129.6, 0, 32893.776, 24267.224)

    def test_nonlattice_shift_rejected(self):
        with self.assertRaisesRegex(ValueError, '43.2'):
            plan(self.source, 'dvs_E1', 129.6, 24., 32893.776, 24267.224)

    def test_duplicate_channel_rejected(self):
        self.source['insts'][2]['x'] += 129.6
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            plan(self.source, 'dvs_E1', 129.6, 43.2, 32893.776, 24267.224)


if __name__ == '__main__':
    unittest.main()
