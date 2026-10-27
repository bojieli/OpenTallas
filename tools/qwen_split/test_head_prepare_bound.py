import copy
import json
from pathlib import Path
import unittest
from head_prepare_bound import tuple_age, PREP, DESC

class ActualBoundPrepare(unittest.TestCase):
    def setUp(self):
        self.groups=json.loads((Path(__file__).parent/'testdata/head_prepare_native100.json').read_text())
    def test_actual_landed_ages_not_raw_bus_depth(self):
        self.assertEqual(tuple_age(self.groups,'native59',PREP)[0],5)
        self.assertEqual(tuple_age(self.groups,'sys_face',DESC)[0],2)
    def test_swapped_token_position_rejected(self):
        row=next(r for r in self.groups['landing'][0]['members'] if r['sink_port']=='head_prepare_token')
        row['source']='tt_ctlm.emb_position'
        with self.assertRaises(ValueError):tuple_age(self.groups,'native59',PREP)
    def test_missing_valid_rejected(self):
        self.groups['landing'][0]['members']=[r for r in self.groups['landing'][0]['members'] if r['sink_port']!='head_prepare_v']
        with self.assertRaises(ValueError):tuple_age(self.groups,'native59',PREP)
    def test_missing_generation_bits_rejected(self):
        for r in self.groups['landing'][1]['members']:
            if r['sink_port']=='head_descriptor_generation':r['sink_bits']=[[0,0]]
        with self.assertRaises(ValueError):tuple_age(self.groups,'sys_face',DESC)
    def test_unequal_landed_age_rejected(self):
        for r in self.groups['landing'][0]['members']:
            if r['sink_port']=='head_prepare_user':r['landed_stages']=4
        with self.assertRaises(ValueError):tuple_age(self.groups,'native59',PREP)
    def test_duplicate_member_rejected(self):
        row=next(r for r in self.groups['landing'][0]['members'] if r['sink_port']=='head_prepare_token')
        self.groups['landing'][0]['members'].append(copy.deepcopy(row))
        with self.assertRaises(ValueError):tuple_age(self.groups,'native59',PREP)


class ActualHostJoin(unittest.TestCase):
    def host(self,first=5,last=10,token=123):
        return dict(first_core_edge=first,last_core_edge=last,tag=(16<<43)|(token<<19)|(79<<6),epoch=16,generation=2,fused_capability=True)
    def test_held_host_requires_extra_pending_edge(self):
        from head_prepare_bound import host_join
        self.assertEqual(host_join(5,123,79,self.host())['descriptor_core_edge'],8)
    def test_late_cohort_keeps_actual_date(self):
        from head_prepare_bound import host_join
        self.assertEqual(host_join(5,123,79,self.host(11,11))['descriptor_core_edge'],11)
    def test_early_pulse_cannot_be_reused(self):
        from head_prepare_bound import host_join
        with self.assertRaises(ValueError):host_join(5,123,79,self.host(1,6))
    def test_wrong_token_cannot_join(self):
        from head_prepare_bound import host_join
        with self.assertRaises(ValueError):host_join(5,123,79,self.host(token=124))
    def test_actual_filler_priority_consumes_slot(self):
        from head_prepare_bound import host_join
        self.assertEqual(host_join(5,123,79,self.host(),[8])['descriptor_core_edge'],9)
    def test_no_profile_means_no_date(self):
        from head_prepare_bound import host_join
        with self.assertRaises(ValueError):host_join(5,123,79,None)

if __name__=='__main__':unittest.main()
