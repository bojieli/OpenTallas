"""Focused allocation admission controls; no tensor reads or numerical replay."""
import copy
import unittest

from w19_resident_contract import build, controller_bytes, map_byte, owned_rows, validate


class ResidentContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=build()

    def test_all_resident_extents_and_capacity(self):
        validate(self.contract)
        self.assertEqual(self.contract['max_stack_end'],3175215616)
        self.assertEqual(self.contract['required_sector_bits_candidate'],27)
        self.assertEqual(self.contract['required_bulk_line_bits_candidate'],25)
        self.assertIsNone(self.contract['full_stack_address_width'])

    def test_26_bit_sector_admission_rejected(self):
        c=copy.deepcopy(self.contract);c['required_sector_bits_candidate']=26
        with self.assertRaises(AssertionError): validate(c)

    def test_overlap_rejected(self):
        c=copy.deepcopy(self.contract)
        c['ranks'][0]['regions'][1]['base'][0]=c['ranks'][0]['regions'][0]['base'][0]
        with self.assertRaises(AssertionError): validate(c)

    def test_insufficient_capacity_rejected(self):
        c=copy.deepcopy(self.contract);c['stack_capacity_bytes_calibration']=2**31
        with self.assertRaises(AssertionError): validate(c)

    def test_no_hc_subset_credit(self):
        c=copy.deepcopy(self.contract);c['hc_compute']['K']=5120
        with self.assertRaises(AssertionError): validate(c)

    def test_striping_byte_conservation_and_roundtrip(self):
        for size in [1,127,128,129,511,512,513,10240]:
            self.assertEqual(sum(controller_bytes(size,s) for s in range(4)),size)
            region={'bytes':size,'base':[0,256,512,768]}
            seen=set()
            for i in range(size):
                s,a=map_byte(region,i)
                self.assertNotIn((s,a),seen);seen.add((s,a))
                local=a-region['base'][s]
                self.assertEqual((local//128)*512+s*128+local%128,i)
            for i in [-1,size]:
                with self.assertRaises(ValueError): map_byte(region,i)

    def test_append_capacity_group_ownership(self):
        for n in [524288,524289,1048576,1048577]:
            counts=[owned_rows(n,r) for r in range(96)]
            self.assertEqual(sum(counts),n)
            self.assertEqual(owned_rows(n+1,(n//8)%96),counts[(n//8)%96]+1)


if __name__=='__main__': unittest.main()
