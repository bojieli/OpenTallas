"""Small geometric checks for relay requests; these do not qualify silicon."""
import unittest
from feedthrough_requests import build, intersection, stations


def pins(a,b,bits=32):
    return {'blocks':{name:{'faces':{'N':{'pins':[dict(link='test',x=p[0],y=p[1],bits=bits)]}}}
                      for name,p in [('source',a),('sink',b)]}}


class GeometryTests(unittest.TestCase):
    def test_spacing_across_turn_is_not_reset(self):
        total,spacing,sites = stations([((0,0),(300,0)),((300,0),(300,300))],480)
        self.assertEqual((total,spacing,len(sites)),(600,300,1))
        self.assertEqual((sites[0]['x'],sites[0]['y']),(300,0))

    def test_short_legs_collectively_need_relay(self):
        _,spacing,sites = stations([((0,0),(200,0)),((200,0),(200,200)),((200,200),(400,200))],480)
        self.assertEqual(len(sites),1)
        self.assertEqual((sites[0]['x'],sites[0]['y']),(200,100))
        self.assertLessEqual(spacing,480)

    def test_reverse_crossing_and_boundary(self):
        rect=dict(x=10,y=10,w=40,h=40)
        cross=intersection((80,30),(0,30),rect)
        self.assertEqual(cross['entry'],(50,30))
        self.assertEqual(cross['exit'],(10,30))
        self.assertIsNone(intersection((0,10),(80,10),rect))

    def test_endpoint_blocks_are_not_skipped(self):
        plan={'source':dict(x=0,y=-20,w=800,h=40),'sink':dict(x=1000,y=-20,w=20,h=40)}
        result=build(pins((0,0),(1000,0)),plan,{'test':{'h':0}})
        self.assertEqual(result['blocks']['source']['relay_sites'],2)
        self.assertEqual(result['blocks']['source']['endpoint_sites'],2)
        self.assertEqual(result['summary']['ff_bits'],64)

    def test_su_column_requires_actual_x_and_axis(self):
        plan={'su_0':dict(x=0,y=0,w=400,h=1200)}
        result=build(pins((50,0),(50,1200)),plan,{'test':{'v':50}})
        self.assertEqual(result['blocks']['su_0']['relay_sites'],2)
        self.assertEqual(result['blocks']['su_0']['su_sites_inside_prose_column'],0)
        result=build(pins((200,0),(200,1200)),plan,{'test':{'v':200}})
        self.assertEqual(result['blocks']['su_0']['su_sites_inside_prose_column'],2)
        self.assertEqual(result['verdict'],'REQUESTED_NOT_PHYSICALLY_QUALIFIED')

    def test_invalid_endpoint_count_is_visible(self):
        result=build(pins((0,0),(10,0)),{}, {'missing':{'h':0}})
        self.assertEqual(len(result['summary']['invalid_links']),1)
        self.assertEqual(result['summary']['emitted_links'],0)


if __name__ == '__main__':
    unittest.main()
