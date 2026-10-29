"""Current bound station substitutions must reach the frame compiler's GO model."""
import copy
import unittest
import frame_schedule_asb as F

OLD='ot_v41_rom_elem_q_qxpq_w10'
NEW=OLD+'_gb'
TOP='col_h9_l4_lp_asb_x'
HP={NEW:{'GO_BOUNDARY':1}}

class StationVariants(unittest.TestCase):
    def setUp(self):
        self.net={'modules':{TOP:{'cells':{'u_r0.u_e0':{
            'type':OLD,'connections':{'xs_sv':[1],'go':[2],'cfg_v':[3],'r':[4]},
            'port_directions':{'xs_sv':'input','go':'input','cfg_v':'input','r':'output'}}}}}}
        self.die=f'{TOP} #(.INSTANCE("u_f_A")) u_f_A (.x(x));\n{TOP} u_f_B (.x(y));'
        self.man={'substitute_inst':[{'inst':r'u_f_[AB]\.u_r0\.u_e0','module':NEW}]}

    def test_actual_prefix_substitution(self):
        before=copy.deepcopy(self.net)
        out,rows=F.selected_station_variants(self.net,TOP,self.man,self.die,HP)
        cell=out['modules'][TOP]['cells']['u_r0.u_e0']
        self.assertEqual(self.net,before)
        self.assertEqual(cell['type'],NEW)
        self.assertNotIn('xs_sv',cell['connections'])
        self.assertEqual(cell['connections']['r'],[4])
        self.assertEqual(rows[0]['frames'],['u_f_A','u_f_B'])
        # A missing instance-prefix application is the original faulty mutant.
        self.assertNotEqual(before['modules'][TOP]['cells']['u_r0.u_e0']['type'],cell['type'])

    def test_mixed_instance_control(self):
        self.man['substitute_inst'][0]['inst']=r'u_f_A\.u_r0\.u_e0'
        with self.assertRaisesRegex(ValueError,'mixed frame instance'):
            F.selected_station_variants(self.net,TOP,self.man,self.die,HP)

    def test_absent_die_identity_control(self):
        with self.assertRaisesRegex(ValueError,'without actual die instances'):
            F.selected_station_variants(self.net,TOP,self.man,'',HP)

    def test_unmodelled_variant_control(self):
        self.man['substitute_inst'][0]['module']='other'
        with self.assertRaisesRegex(ValueError,'unmodelled station'):
            F.selected_station_variants(self.net,TOP,self.man,self.die,HP)

    def test_wrong_go_parameter_control(self):
        with self.assertRaisesRegex(ValueError,'GO_BOUNDARY=1'):
            F.selected_station_variants(self.net,TOP,self.man,self.die,{NEW:{'GO_BOUNDARY':0}})

    def test_legacy_manifest(self):
        out,rows=F.selected_station_variants(self.net,TOP,{},self.die,{})
        self.assertEqual(out,self.net)
        self.assertEqual(rows,[])

if __name__=='__main__': unittest.main()
