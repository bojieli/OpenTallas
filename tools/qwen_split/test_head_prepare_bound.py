import copy
import json
from pathlib import Path
import unittest
import tempfile
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
        return dict(first_core_edge=first,last_core_edge=last,tag=(16<<43)|(token<<19)|(79<<6),epoch=16,generation=2,fused_capability=True,interval_basis='pre_edge_sampling')
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



class ActualHostTransport(unittest.TestCase):
    def setUp(self):
        from head_prepare_bound import HOST
        self.component=dict(landed_fields=dict(host={p:2 for p in HOST}),edges=dict(host_to_native=2,native_host_capture=1))
    def source(self):
        return dict(endpoint='sys_face.host_tuple',interval_basis='post_edge_publication',first_core_edge=5,last_core_edge=7,tag=(16<<43)|(123<<19)|(79<<6),epoch=16,generation=2,fused_capability=True)
    def test_transport3_then_consumer_capture1(self):
        from head_prepare_bound import host_core_interval,host_join
        row=host_core_interval(self.source(),self.component)
        self.assertEqual((row['first_core_edge'],row['last_core_edge']),(8,10))
        self.assertEqual(host_join(2,123,79,row)['descriptor_core_edge'],9)
    def test_wrong_field_age_refused(self):
        from head_prepare_bound import host_core_interval
        self.component['landed_fields']['host']['host_generation']=1
        with self.assertRaises(ValueError):host_core_interval(self.source(),self.component)
    def test_unknown_source_publication_refused(self):
        from head_prepare_bound import host_core_interval
        with self.assertRaises(ValueError):host_core_interval(None,self.component)
    def test_interval_basis_never_guessed(self):
        from head_prepare_bound import host_core_interval
        r=self.source();r.pop('interval_basis')
        with self.assertRaises(ValueError):host_core_interval(r,self.component)

if __name__=='__main__':unittest.main()


class SelectedChild(unittest.TestCase):
    def select(self, text):
        from head_prepare_bound import selected
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'rtl').mkdir()
            (root/'rtl/part.sv').write_text(text)
            return selected(root, 'part.sv', 'u_core')

    def test_current_parameterized_native_and_nested_parameters(self):
        for args in ('', '#(.ROPE(1))', '#(.N(f(2, g(3))))'):
            self.assertEqual(self.select(f'qfd_native59_dv_headprep_obs1 {args} u_core (.clk(clk));'),
                             'qfd_native59_dv_headprep_obs1')

    def test_comment_does_not_select_a_second_master(self):
        self.assertEqual(self.select('// qfd_old u_core ();\nqfd_actual #(.N(1)) u_core ();'), 'qfd_actual')

    def test_duplicate_or_missing_instance_refused(self):
        for text in ('qfd_actual #(.N(1)) other ();',
                     'qfd_a u_core (); qfd_b #(.N(1)) u_core ();'):
            with self.assertRaisesRegex(ValueError, 'unique actual selected child'):
                self.select(text)
