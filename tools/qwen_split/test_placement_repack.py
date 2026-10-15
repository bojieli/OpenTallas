"""Independent geometry guard checks for the advisory placement search."""
import unittest
import copy
from types import SimpleNamespace
from placement_repack import gap, overlap, relays, validate, propose, apply


class GeometryGuards(unittest.TestCase):
    @staticmethod
    def fixture():
        rows = [('sp_band_lanes_0',12742.272,4423.68,881.28,1131.84),
                ('sp_port_tiles_0',12664.512,5559.84,1036.776,2462.376),
                ('sp_res_ser_0',12794.112,8026.56,777.576,518.376),
                ('sp_port_tiles_0_f1',13705.632,5559.84,1036.776,2462.376),
                ('sp_band_lanes_1',12742.272,9612,881.28,1131.84),
                ('sp_port_tiles_1',12664.512,10748.16,1036.8,2462.4),
                ('sp_port_tiles_1_f1',13705.632,10748.16,1036.8,2462.4),
                ('sp_res_ser_1',12794.112,13214.88,777.6,518.4),
                ('sp_band_lanes_2',12742.272,19355.76,881.28,1131.84),
                ('sp_vector_memory',14828.832,11962.08,4708.776,2203.176),
                ('tt_up4_0',14828.832,14597.28,345.576,388.776)]
        return dict(die=dict(w=32413.392,h=25937.28),insts=[
            dict(n=n,m=n,x=x,y=y,w=w,h=h,o='R0') for n,x,y,w,h in rows])

    def test_repeated_application_preserves_mirrored_stack_and_candidate(self):
        d = self.fixture()
        model = dict(die=d['die'],insts=[SimpleNamespace(
            name=i['n'],master=i['m'],x=i['x'],y=i['y'],w=i['w'],h=i['h'],orient=i['o']) for i in d['insts']])
        first = apply(None,model)
        old = copy.deepcopy([(i.name,i.x,i.y,i.orient) for i in model['insts']])
        second = apply(None,model)
        self.assertEqual(first['candidate_leaves'],second['candidate_leaves'])
        self.assertEqual(old,[(i.name,i.x,i.y,i.orient) for i in model['insts']])
        self.assertIn('tt_up4_0',[i.name for i in model['insts']])
        self.assertEqual(second['candidate_geometry_errors'],[])
        self.assertTrue(second['band1_mirrored'])
        self.assertEqual(next(i for i in model['insts'] if i.name=='sp_band_lanes_1').orient,'MX')
        self.assertIs(model['placement_repack'],second)

    def test_missing_west_channel_fails_before_application(self):
        d = self.fixture()
        next(i for i in d['insts'] if i['n']=='sp_port_tiles_0_f1')['x']=19000
        with self.assertRaisesRegex(ValueError,'west VM channel too narrow'):
            propose(d)

    def test_contact_is_legal_but_positive_area_overlap_is_not(self):
        a = dict(n='a', x=0, y=0, w=10, h=20)
        b = dict(n='b', x=10, y=0, w=10, h=20)
        self.assertFalse(overlap(a, b))
        b['x'] = 9.999
        self.assertEqual(validate([a, b], dict(w=100, h=100)), [['overlap', 'a', 'b']])

    def test_outside_and_manhattan_reach(self):
        a = dict(n='a', x=0, y=0, w=10, h=20)
        b = dict(n='b', x=500, y=510, w=10, h=20)
        self.assertEqual(gap(a, b), 980)
        self.assertEqual(relays(a, b), 1)
        b['x'] += .001
        self.assertEqual(relays(a, b), 2)
        self.assertIn(['outside', 'b'], validate([a, b], dict(w=500, h=500)))


if __name__ == '__main__':
    unittest.main()
