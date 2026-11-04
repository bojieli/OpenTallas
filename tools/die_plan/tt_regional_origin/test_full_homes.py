"""A new-source placement map must not silently accept missing state or changed physical cells."""
import copy
import unittest
from full_homes import native_join


class FullHomesJoin(unittest.TestCase):
    def fixture(self):
        target=dict(model_name='u_bound.u_core.ff',master='DFF',width_um=1.08,height_um=.27,xy=[10.26,10.125],source_identity=None,role='retained_reference_ff')
        intent=dict(status='PASS_ROW_SITE_INTENT_ONLY',target_count=1,net_ff_added=13,cycles_added=0,targets=[target])
        inventory=dict(stage='mapped_preCTS',source_event='tt_regional_origin_13ff',source_sha256='new_source',netlist_sha256='new_netlist',complete_ff_census=True,ff_cells=[dict(model_name=target['model_name'],native_name=target['model_name'],master='DFF',width_um=1.08,height_um=.27)])
        return intent,inventory

    def test_join_is_metadata_only(self):
        p,i=self.fixture();out=native_join(p,i)
        self.assertFalse(out['placement_applied']);self.assertEqual(out['physical_release'],'HELD')

    def test_nonrow_intent_refused(self):
        p,i=self.fixture();p['status']='HELD_NONROW'
        with self.assertRaisesRegex(ValueError,'rows/sites'):native_join(p,i)

    def test_changed_native_master_refused(self):
        p,i=self.fixture();i['ff_cells'][0]['master']='different_size_or_variant'
        with self.assertRaisesRegex(ValueError,'master/footprint'):native_join(p,i)

    def test_missing_or_filtered_native_census_refused(self):
        for kind in ('missing','filtered'):
            p,i=self.fixture()
            if kind=='missing':i['ff_cells']=[]
            else:i['complete_ff_census']=False
            with self.assertRaises(ValueError):native_join(p,i)

    def test_unchanged_ff_cannot_gain_an_alias(self):
        p,i=self.fixture();i['ff_cells'][0]['native_name']='arbitrary_other_ff'
        with self.assertRaisesRegex(ValueError,'renamed/aliased'):native_join(p,i)


if __name__=='__main__':unittest.main()
