import unittest
from hbm_sm_control_path_probe import portal, price_path, probe

class ControlPaths(unittest.TestCase):
    def test_orientation(self):
        b=[20,40,80,100]
        for orient in ('R0','MX'): self.assertEqual(portal(b,orient,12),(8,70))
        for orient in ('MY','R180'): self.assertEqual(portal(b,orient,12),(92,70))
        with self.assertRaises(ValueError): portal(b,'R90',12)

    def test_hops_ack_and_dual_copy(self):
        p=price_path([(0,0),(600,0),(600,450)])
        self.assertEqual(p['registered_links'],4)
        self.assertEqual(p['descriptor_bridge_HOPS'],5)
        self.assertEqual(p['earliest_consumed_ack_edges'],12)
        self.assertEqual(p['flight_register_bits'],600)
        self.assertEqual(p['destination_fifo_depth_per_copy'],2)

    def test_reject_bad_flight(self):
        for p in ([],[(0,0)],[(0,0),(1,1)],[(0,0),(0,0)]):
            with self.assertRaises(ValueError):price_path(p)

    def test_bays_obstruct_and_preserve_identity(self):
        data=dict(insts=[dict(name='sm0',x=200,y=100,w=100,h=100,orient='R0')],
                  geo=dict(W=1000,H=1000),
                  native_owner_bays=[dict(sm='sm0',box_um=[200,220,250,260])],
                  native_descriptor_bays=[dict(sm='sm0',box_um=[200,40,250,80])],
                  result_pin_bays=[])
        p=probe(data)
        self.assertEqual(p['obstacle_count'],3)
        self.assertEqual(p['successful_paths'],1)
        row=p['rows'][0]
        self.assertEqual(row['sm'],'sm0')
        self.assertEqual(row['reverse_path_um'],list(reversed(row['path_um'])))
        # Another reserved bay swallowing a flight portal must fail, not be exempted.
        data['result_pin_bays']=[dict(sm='sm0',box_um=[170,220,200,260])]
        q=probe(data)
        self.assertEqual(q['successful_paths'],0)
        self.assertIn('result_pin_bays:sm0',q['rows'][0]['portal_obstacles']['source'])
        data['native_result_store_bays']=data.pop('result_pin_bays')
        data['result_pin_bays']=[]
        q=probe(data)
        self.assertEqual(q['successful_paths'],0)
        self.assertIn('native_result_store_bays:sm0',q['rows'][0]['portal_obstacles']['source'])
        data['native_descriptor_bays'][0]['sm']='sm1'
        with self.assertRaises(ValueError):probe(data)

if __name__=='__main__':unittest.main()
