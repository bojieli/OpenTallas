import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).parent/'bf_asbuilt_1101/prepare.py'
s=importlib.util.spec_from_file_location('bf_prepare',p);M=importlib.util.module_from_spec(s);s.loader.exec_module(M)


def source(master):
    ranges=([range(0,5),range(5,10),range(10,15),range(0,5)] if master=='col_h9'
            else [range(0,6),range(6,11),range(11,16),range(0,6)])
    return '\n'.join('module '+master+'_l4_lp_'+part+';\n'+
                     '\n'.join(f'ot_rom_4096x72_m8 u_c{pair}_{bank} ();' for pair in pairs for bank in range(7))+
                     '\nendmodule' for part,pairs in zip(('r0','r1','r2','r0_nx'),ranges))


class CfgCensus(unittest.TestCase):
    def test_distinct_actual_master_bank_sets(self):
        self.assertEqual(list(M.cfg_source_census(source('col_h9'),'col_h9').values()),[35,35,35,35])
        self.assertEqual(list(M.cfg_source_census(source('col_h10'),'col_h10').values()),[42,35,35,42])

    def test_equal_total_but_wrong_partition_identity_is_rejected(self):
        text=source('col_h10').replace('u_c0_0','u_c6_0',1)
        with self.assertRaisesRegex(ValueError,'per-module'):M.cfg_source_census(text,'col_h10')

    def test_duplicate_or_missing_bank_is_rejected(self):
        for text in (source('col_h10').replace('u_c0_0','u_c0_1',1),
                     source('col_h10').replace('ot_rom_4096x72_m8 u_c0_0 ();','',1)):
            with self.assertRaisesRegex(ValueError,'per-module'):M.cfg_source_census(text,'col_h10')


if __name__=='__main__':unittest.main()
