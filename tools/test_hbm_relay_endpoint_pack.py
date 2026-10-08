import json
from pathlib import Path
import unittest
from hbm_relay_endpoint_pack import pack

class EndpointPackTest(unittest.TestCase):
    def test_successor_identity_reach_and_joint_separation(self):
        p=json.loads((Path(__file__).resolve().parents[1]/'results/uarch/hbm_relay_endpoint_pack_20261007/successor_endpoint_pack.json').read_text())
        for key in ('source_boxes','sink_boxes'):
            boxes=p[key]
            self.assertEqual(sorted(i for b in boxes for i in b['bit_indices']),list(range(270)))
            for i,a in enumerate(boxes):
                self.assertLessEqual(a['worst_pin_to_any_box_point_um'],100)
                a=a['box_um']
                for b in boxes[i+1:]:
                    b=b['box_um'];g=2.16
                    self.assertTrue(a[2]+g<=b[0]+1e-9 or b[2]+g<=a[0]+1e-9 or a[3]+g<=b[1]+1e-9 or b[3]+g<=a[1]+1e-9)
        # Every source station remains below the actual planned south macro edge.
        self.assertTrue(all(b['box_um'][3]<=-2.16 for b in p['source_boxes']))

    def test_oversized_station_rejected(self):
        with self.assertRaises(ValueError):
            pack([dict(bit_indices=[0],source_face='S',source_portal_um=[0,-25])],[(0,0)],'source',shape=(300,300))

    def test_common_portal_requires_distinct_boxes(self):
        groups=[dict(bit_indices=[i],source_face='S',source_portal_um=[0,-25]) for i in range(3)]
        boxes=pack(groups,[(0,0)]*3,'source')
        self.assertEqual(len({tuple(q['box_um']) for q in boxes}),3)
        self.assertTrue(all(q['box_um'][3]<=-2.16 for q in boxes))

if __name__=='__main__': unittest.main()
