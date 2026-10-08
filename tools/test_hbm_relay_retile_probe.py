import json
from pathlib import Path
import unittest
from hbm_relay_retile_probe import cut_capacity,reserve,Free,clustered_slices,pack_face_batch

class RetileRelayTest(unittest.TestCase):
    def test_actual_pin_outliers_preserve_full_identity(self):
        root=Path(__file__).resolve().parents[1]
        p=json.loads((root/'results/uarch/hbm_relay_endpoint_pack_20261007/sm_successor_planned_pins.json').read_text())
        lookup={p['pin']:p['xy'] for p in p['pins']}
        names=['rv']+[f'rrow[{i}]' for i in range(12)]+[f'rdata[{i}]' for i in range(256)]+['fault']
        e=json.loads((root/'results/uarch/hbm_relay_channel_20261007/rl_sm0_spatial_slices.json').read_text())['endpoints'][1]
        x,y,x1,y1=e['physical_box_um']
        groups=clustered_slices([lookup[n] for n in names],[(a-x,b-y) for a,b in e['physical_pins_um']],
                              (0,0,3075.84,1131.84),(0,0,x1-x,y1-y))
        self.assertEqual(len(groups),6)
        self.assertEqual(sorted(i for g in groups for i in g['bit_indices']),list(range(270)))
        self.assertTrue(all(len(g['bit_indices'])<=64 and max(g['source_max_pin_distance_um'],g['sink_max_pin_distance_um'])<=100 for g in groups))

    def test_joint_face_matching_reserves_escape_aisles(self):
        items=[({},dict(bit_indices=[0],source_face='S',source_portal_um=[250,175]),[(250,200)],'source') for _ in range(6)]
        boxes=pack_face_batch(items,Free([[0,200,500,500]],500,500))
        self.assertEqual(len(boxes),6)
        for i,a in enumerate(boxes):
            for b in boxes[i+1:]:
                self.assertTrue(a[2]+12<=b[0]+1e-8 or b[2]+12<=a[0]+1e-8 or a[3]+12<=b[1]+1e-8 or b[3]+12<=a[1]+1e-8)
        self.assertTrue(all(item[1]['source_station']['worst_pin_to_endpoint_facing_side_um']<=100 for item in items))
        with self.assertRaisesRegex(ValueError,'not an infeasibility proof'):
            pack_face_batch(items*2,Free([[0,200,500,500]],500,500))

    def test_corridor_full_width_overflow_negative(self):
        paths=[dict(groups=[dict(path_um=[[0,50],[100,50]],bit_indices=list(range(1000)))])]
        boxes=[[0,0,100,40],[0,60,100,100]]
        self.assertGreater(cut_capacity(paths,boxes,[100,100])['overflow_cuts'],0)
        paths[0]['groups'][0]['bit_indices']=list(range(270))
        self.assertEqual(cut_capacity(paths,boxes,[100,100])['overflow_cuts'],0)

    def test_independent_buses_share_cut_demand(self):
        paths=[dict(groups=[dict(path_um=[[0,y],[100,y]],bit_indices=list(range(270)))]) for y in (45,48,52,55)]
        c=cut_capacity(paths,[[0,0,100,40],[0,60,100,100]],[100,100])
        self.assertGreater(c['overflow_cuts'],0)
        self.assertEqual(c['worst_cuts'][0]['demand_tracks'],1080)

    def test_fully_blocked_endpoint_rejected(self):
        with self.assertRaisesRegex(ValueError,'greedy endpoint search'):
            reserve(dict(bit_indices=[0],source_face='S',source_portal_um=[50,25]),[(50,50)],'source',Free([[0,0,100,100]],100,100))

    def test_global_reservations_are_distinct(self):
        free=Free([[0,100,200,200]],200,200)
        group=dict(bit_indices=[0],source_face='S',source_portal_um=[100,75])
        a=reserve(group,[(100,100)],'source',free)
        b=reserve(group,[(100,100)],'source',free)
        self.assertNotEqual(a['box_um'],b['box_um'])
        self.assertFalse(free.ok(a['box_um']))
        self.assertFalse(free.ok(b['box_um']))

if __name__=='__main__':unittest.main()
