import importlib.util
import pathlib
import unittest

SPEC=importlib.util.spec_from_file_location('n4',pathlib.Path(__file__).parents[1]/'hbm_n4_links.py')
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

class WrapperTests(unittest.TestCase):
    def test_crosspair_and_width_changes_fail(self):
        import copy
        manifest={'module':'ot_hnx_fused_hub_n4ext','added_cycles':0,
            'proposed_new_plan_instance':'u_mu_fused_root',
            'ports':{'up_nw':['input',271],'up_ne':['input',271],
                     'down_nw':['output',173],'down_ne':['output',173]},
            'port_identity':{'up_nw':'u_native.uq0','up_ne':'u_native.uq2',
                             'down_nw':'u_native.dq0','down_ne':'u_native.dq2'}}
        self.assertEqual(m.wrapper_ports(manifest),'u_mu_fused_root')
        bad=copy.deepcopy(manifest);bad['port_identity']['up_nw']='u_native.uq2'
        with self.assertRaises(ValueError):m.wrapper_ports(bad)
        bad=copy.deepcopy(manifest);bad['ports']['up_nw'][1]=272
        with self.assertRaises(ValueError):m.wrapper_ports(bad)

class RootLotTests(unittest.TestCase):
    def test_actual_bit_bank_is_excluded(self):
        t={'outline_um':[1200,1200], 'ft_slots':[{'regs_um':[[1000,1000]],
             'bit_sites_um':[[[300,300],[700,700]]], 'bit_site_cell_um':[2,2]}]}
        obs=m.obstacles(t)
        self.assertTrue(any(m.intersects([400,400,500,500],r) for _,r in obs))
        # This excludes a whole large bank even though its centre sits elsewhere.
        for lot in m.root_lots(t,size=(100,100),target_y=500):
            self.assertFalse(any(m.intersects(m.box(lot['origin_um'],lot['outline_um'],4.32),r) for _,r in obs))

    def test_no_legal_lot_returns_empty(self):
        t={'outline_um':[500,500], 'hard_cores':[{'inst':'full','origin_um':[0,0],'outline_um':[500,500]}]}
        self.assertEqual(m.root_lots(t),[])

    def test_ft_band_is_reserved_across_partition(self):
        t={'outline_um':[800,800], 'die_ft_bands':[{'dir':'NS','span_um':[200,800]}]}
        self.assertEqual(m.root_lots(t),[])

if __name__=='__main__':
    unittest.main()
