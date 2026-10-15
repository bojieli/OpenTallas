"""IO proposal guards: real envelopes survive and incomplete PHY joins stay open."""
import unittest
from io_placement import propose


class IOPlacement(unittest.TestCase):
    def fixture(self):
        rows=[('io_serdes_2',0,2560),('io_serdes_1',2564.32,2560),
              ('io_collective',5128.64,3453.384),('io_xfifo',8586.344,700.248),
              ('io_ucie',9290.912,6394.872),('io_serdes',15690.104,2560)]
        d=dict(insts=[dict(n=n,m=n,x=x,y=21.6,w=w,h=1563.816) for n,x,w in rows])
        s=dict(top='qfd_io_collective_static',outline=dict(w=864.0,h=950.4),
               pins=dict(W=['sx1_rec'],E=['sx0_rec'],N=['in_data']),
               pin_ranges=dict(sx1_rec=[533.04,613.04],sx0_rec=[230.04,310.04],in_data=[278.4,398.4]))
        return d,s,dict(w=20000,h=2000)

    def test_envelopes_preserved_and_actual_faces_assigned(self):
        d,s,die=self.fixture()
        out=propose(d,s,die)
        self.assertEqual([p['n'] for p in out['placements']],['io_serdes_2','io_serdes_1','io_collective','io_serdes','io_ucie'])
        self.assertEqual(out['placements'][-1]['w'],6394.872)
        self.assertEqual(out['placements'][2]['w'],864)
        self.assertFalse(out['cut_diagnostic']['qualification'])
        self.assertTrue(all(p['remote_physical_endpoint'] is None for p in out['actual_collective_face_assignments']))
        self.assertEqual(out['static_graph'][-1]['codec_phy_frame_bits'],597)
        self.assertEqual(out['static_graph'][1]['codec_phy_frame_bits'],565)

    def test_source_outline_and_geometry_rejected(self):
        d,s,die=self.fixture()
        with self.assertRaisesRegex(ValueError,'invalid'):
            propose(d,s,dict(w=100,h=100))
        s['outline']['w']=1105.92
        with self.assertRaisesRegex(ValueError,'exact static S2'):
            propose(d,s,die)


if __name__=='__main__':
    unittest.main()
