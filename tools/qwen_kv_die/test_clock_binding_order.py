#!/usr/bin/env python3
import unittest
from pathlib import Path
import kv_expand as E
from binding_order import sliced_order

class ClockBindingOrder(unittest.TestCase):
    def test_actual_landing_vector_clock_bits(self):
        binding=E.K.KS.land_binding()
        E.K.BINDINGS['_land_clock_test']=binding
        try:
            widths={f'ck_p{i}':1 for i in range(32)}
            widths.update({f'ck_g{i}':1 for i in range(8)})
            mapping=E.die_to_rtl('_land_clock_test',widths,dict(ck_p=32,ck_g=8))
            for name,count in [('ck_p',32),('ck_g',8)]:
                for bit in range(count):self.assertEqual(mapping[f'{name}{bit}'],[(name,bit)])
        finally:del E.K.BINDINGS['_land_clock_test']
    def test_actual_land32_and_astk64_indices(self):
        for base,n in [('ck_p0',32),('ck_v0',64),('hk_p0',32)]:
            stem=base[:-1]
            self.assertEqual(sliced_order(base,[stem+str(i) for i in range(n)]),[stem+str(i) for i in range(n)])
    def test_existing_data_abi_kept(self):
        self.assertEqual(sliced_order('e0',['e2','e1','e3','e0']),['e0','e1','e2','e3'])

if __name__=='__main__':unittest.main()
