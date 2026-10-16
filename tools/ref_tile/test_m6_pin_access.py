import copy,unittest
import ref_tile as RT

GRANT={'schema':'opentallas.m6_pin_grant.v1','master':'dut','granted_by':'test die lead','reason':'exact local contacts',
       'source_commit':'1'*40,'source_spec_sha256':'2'*64,
       'ports':[{'name':'d[0]','face':'W','span_um':[0.9,1.1],'max_depth_um':.384,'max_area_um2':.024576}]}

class M6PinAccess(unittest.TestCase):
    """Q-XSLEAF 2026-10-16: M6 face pins above an M5 cap route M2-M6 with M6 confined to the E/W pin stubs."""
    def spec(self,**kw):
        s={'name':'dut','top':'dut','kind':'tile','m6_pin_grant':copy.deepcopy(GRANT),'pin_access':{'m6_stub_um':0.384},'route':{}}
        s.update(kw);return s
    def test_stub_routes_m6_and_hooks_both_ways(self):
        lc=RT.layer_contract(self.spec(),None)
        self.assertEqual(('M2','M6'),lc['rlayers']);self.assertEqual('M5',lc['pg_layer']);self.assertEqual(0.384,lc['m6_pin_access_stub_um'])
    def test_no_stub_keeps_m5_cap(self):
        s=self.spec();s.pop('pin_access')
        self.assertEqual(('M2','M5'),RT.layer_contract(s,None)['rlayers'])
    def test_stub_needs_grant_and_fits_grant_depth(self):
        s=self.spec();s.pop('m6_pin_grant')
        with self.assertRaises(RT.SpecError):RT.layer_contract(s,None)
        with self.assertRaises(RT.SpecError):RT.layer_contract(self.spec(pin_access={'m6_stub_um':0.5}),None)
    def test_hook_file_is_a_referenced_source(self):
        s=self.spec(sources=[],macros=[],children=[],clock_port='clk',reset_ports=[],pins={})
        self.assertIn(RT.M6_PIN_ACCESS_TCL,RT.referenced_paths(s,'physical/ref_tile/dut'))

if __name__=='__main__':unittest.main()
