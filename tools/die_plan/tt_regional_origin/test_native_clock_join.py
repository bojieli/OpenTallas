"""The adapter must reject wrong-source/name/phase joins and preserve clock logic."""
import copy
import unittest
from native_clock_join import join


class JoinContract(unittest.TestCase):
    def fixture(self):
        ports = ['clk'] + ['clk_t'+str(i) for i in range(1,63)]
        path = [dict(instance='gate',master='ICG',input_pin='CLK',output_pin='GCLK',kind='clock_gate',polarity=1)]
        proposal = dict(clock_ports=ports,clock_port_xy_um={p:[float(i),float(i)] for i,p in enumerate(ports)},reassociated_sinks=51,assignments=[dict(name='q'+str(i),parent_tap='clk_t1',nearest_parent_tap='clk') for i in range(51)],retained_other_cohorts=[])
        inv = dict(source_event='tt_regional_origin_13ff',stage='mapped_preCTS',source_sha256='source',netlist_sha256='mapped',
                   ports={p:dict(cohort='clk',period_ps=833,phase_ps=0,polarity=1,xy_um=[float(i),float(i)]) for i,p in enumerate(ports)},
                   sinks=[dict(model_name='q'+str(i),native_iterm='q'+str(i)+'/CLK',cohort='clk',root_port='clk',edge='negedge',path=copy.deepcopy(path)) for i in range(51)])
        return proposal,inv

    def test_full_path_and_edge_retained(self):
        p,i=self.fixture();result=join(p,i)
        self.assertFalse(result['tree_applied'])
        self.assertEqual(result['assignments'][0]['preserve_path'],i['sinks'][0]['path'])
        self.assertEqual(result['assignments'][0]['edge'],'negedge')

    def regional_fixture(self):
        p,i=self.fixture()
        name='u_bound.u_cland_origin/sf$_DFF_N_'
        p['assignments'][0]['name']=name
        i['sinks'][0].update(model_name=name,rtl_signal='u_bound.u_cland_origin.g_on.sf',rtl_edge='negedge',edge='posedge')
        i['sinks'][0]['path'].append(dict(instance='clock_inv',master='INV',input_pin='A',output_pin='Y',kind='inverter',polarity=-1))
        return p,i

    def test_retained_sf_namespace_and_inversion(self):
        p,i=self.regional_fixture();out=join(p,i)
        self.assertEqual(out['assignments'][0]['source_identity'][1],'negedge')

    def test_retained_sf_wrong_alias_rejected(self):
        p,i=self.regional_fixture();i['sinks'][0]['rtl_signal']='other.sf'
        with self.assertRaisesRegex(ValueError,'source signal/edge'):join(p,i)

    def test_retained_sf_missing_inverter_rejected(self):
        p,i=self.regional_fixture();i['sinks'][0]['path'].pop()
        with self.assertRaisesRegex(ValueError,'inversion/edge'):join(p,i)

    def test_moved_native_clock_entry_rejected(self):
        p,i=self.fixture();i['ports']['clk_t1']['xy_um'][0]+=8.64
        with self.assertRaisesRegex(ValueError,'coordinate differs'):join(p,i)

    def test_wrong_phase_rejected(self):
        p,i=self.fixture();i['ports']['clk_t1']['phase_ps']=416.5
        with self.assertRaisesRegex(ValueError,'phase'):join(p,i)

    def test_missing_actual_endpoint_rejected(self):
        p,i=self.fixture();i['sinks'].pop()
        with self.assertRaisesRegex(ValueError,'endpoint join'):join(p,i)

    def test_old_checkpoint_rejected(self):
        p,i=self.fixture();i['source_event']='old_TT_C'
        with self.assertRaisesRegex(ValueError,'newly generated'):join(p,i)


if __name__=='__main__':unittest.main()
