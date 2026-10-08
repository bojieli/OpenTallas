import copy
import gzip
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hbm_accel_die_fp as H
import hbm_sm_result_store_reservation as R


class ResultStoreReservation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=ROOT/'results/uarch/hbm_sm_result_store_reservation_20261007'
        cls.placement=json.loads(gzip.decompress((cls.directory/'source_placement.json.gz').read_bytes()))
        cls.provider=json.loads((cls.directory/'provider_model.json').read_text())

    def test_complete_macro_inventory_and_conflicts(self):
        model=R.build(self.placement,self.provider)
        self.assertEqual(model['macro_count'],1280)
        self.assertEqual(model['waypoint_relocations_required'],['w117_rgSE2','w186_xmNW1b','w268_xmNE2b'])
        self.assertFalse(model['physical_admitted'])

    def test_changed_shape_fails_closed(self):
        p=copy.deepcopy(self.placement)
        next(i for i in p['insts'] if i['name']=='sm0')['w']+=1
        with self.assertRaises(ValueError):R.build(p,self.provider)

    def test_successor_relocates_without_losing_logical_paths(self):
        before=H.build(H.R24SM3VOCEU,network_probe=True)
        after=H.build(H.R24SM3VOCEUR,network_probe=True)
        self.assertEqual(set(before['paths']),set(after['paths']))
        fixed=lambda m:{i.name:(i.master,i.box()) for i in m['insts'] if i.kind!='waypoint'}
        self.assertEqual(fixed(before),fixed(after))
        self.assertEqual(H.legality(after)['overlaps'],0)
        self.assertEqual(H.legality(after)['outside'],0)
        self.assertEqual(len(after['native_result_store_bays']),32)
        for bay in after['native_result_store_bays']:
            self.assertFalse(any(R.overlap(bay['box_um'],i.box()) for i in after['insts']))


if __name__=='__main__':unittest.main()
