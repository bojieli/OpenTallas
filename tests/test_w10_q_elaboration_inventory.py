import unittest
from tools.w10_q_elaboration_inventory import inventory

class InventoryTest(unittest.TestCase):
    def test_memory_ports_are_charged_and_no_admission(self):
        m={'modules':{'ot_v41_rom_elem_q_wake_w10':{'ports':{},'cells':{
            'r':{'type':'$dff','connections':{'Q':[1,2],'CLK':[3]}},
            'mem':{'type':'$mem_v2','connections':{'WR_CLK':[3,3]},'parameters':{
                'SIZE':'100','WIDTH':'10','RD_PORTS':'11','WR_PORTS':'10'}}}}}}
        x=inventory(m)
        self.assertEqual(x['conservative_storage_clock_sinks'],10)
        self.assertEqual(x['memory_read_mux2_count'],18)
        self.assertEqual(x['memory_write_mux2_count'],16)
        self.assertFalse(x['physical_admission'])
        self.assertIsNone(x['complete_area_bound_um2'])
        self.assertEqual(x['root_stop_credit'],0)
    def test_distinct_clocks_remain_distinct(self):
        cells={str(i):{'type':'$adff','connections':{'Q':[i],'CLK':[i+10]}}
               for i in range(8)}
        x=inventory({'modules':{'ot_v41_rom_elem_q_wake_w10':{'ports':{},'cells':cells}}})
        self.assertEqual(len(x['storage_bits_by_clock_net']),8)
        self.assertEqual(x['register_bits'],8)
if __name__=='__main__': unittest.main()
