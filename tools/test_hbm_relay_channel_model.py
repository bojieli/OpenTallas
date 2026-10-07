#!/usr/bin/env python3
import unittest
from hbm_relay_channel_model import channel_path, size_chain, spatial_slices

class ChannelTest(unittest.TestCase):
    def test_spatial_slices_preserve_identity_across_faces(self):
        src=[(0,10),(0,900),(100,20),(100,800)]
        dst=[(200,10),(200,20),(300,900),(300,800)]
        groups=spatial_slices(src,dst,(0,0,100,1000),(200,0,300,1000),max_bits=64)
        self.assertEqual(sorted(i for g in groups for i in g['bit_indices']),list(range(4)))
        self.assertTrue(all(max(g['source_max_pin_distance_um'],g['sink_max_pin_distance_um'])<=100 for g in groups))
        self.assertGreater(len(groups),1)
        with self.assertRaisesRegex(ValueError,'cannot reach'):
            spatial_slices([(500,500)],[(500,500)],(0,0,1000,1000),(0,0,1000,1000))

    def test_routes_around_macro_and_prices_detour(self):
        path=channel_path((10,50),(90,50),[(40,20,60,80)],(100,100),2)
        self.assertEqual(path[0],(10,50))
        self.assertEqual(path[-1],(90,50))
        self.assertEqual(sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(path,path[1:])),144)
        for a,b in zip(path,path[1:]):
            if a[1]==b[1] and 18<a[1]<82:
                self.assertFalse(min(a[0],b[0])<62 and max(a[0],b[0])>38)
            if a[0]==b[0] and 38<a[0]<62:
                self.assertFalse(min(a[1],b[1])<82 and max(a[1],b[1])>18)

    def test_no_legal_route_does_not_place_overlap(self):
        with self.assertRaisesRegex(ValueError,'no obstacle-free'):
            channel_path((10,50),(90,50),[(40,0,60,100)],(100,100),2)

    def test_blocked_endpoint_rejected(self):
        with self.assertRaisesRegex(ValueError,'endpoint'):
            channel_path((50,50),(90,50),[(40,20,60,80)],(100,100),2)

    def test_boundary_detour_and_credit_return(self):
        args=dict(path=[(0,0),(650,0),(650,300)],data_bits=513,slice_bits=64,
                  slice_area_um2=100,slice_width_um=20,slice_height_um=5,
                  channel_tracks=520,period_ps=833.333,reverse_hops=5,
                  consumer_cycles=2,transactions=7)
        rec=size_chain(**args)
        self.assertEqual(rec['station_count'],5)
        self.assertEqual(rec['slices_per_station'],9)
        self.assertEqual(rec['required_receive_beats'],13)
        self.assertEqual(rec['receive_storage_bits'],6669)
        self.assertFalse(rec['channel_capacity_fit'])
        self.assertEqual(rec['token_latency_ps'],7*5*833.333)
        self.assertEqual(rec['required_tracks'],523)
        stream=size_chain(**dict(args,flow_control='fixed_stream',reverse_hops=0,consumer_cycles=0))
        self.assertEqual(stream['required_receive_beats'],0)
        self.assertEqual(stream['boundary_bits_per_cycle'],513)
        self.assertEqual(stream['fanout_per_credit_counter'],0)
        args['path']=[(0,0),(1,1)]
        with self.assertRaisesRegex(ValueError,'rectilinear'):
            size_chain(**args)

if __name__=='__main__':
    unittest.main()
