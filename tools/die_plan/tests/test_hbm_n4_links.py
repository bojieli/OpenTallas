import importlib.util
import pathlib
import unittest

SPEC=importlib.util.spec_from_file_location('n4',pathlib.Path(__file__).parents[1]/'hbm_n4_links.py')
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

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
