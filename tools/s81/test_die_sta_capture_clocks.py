import copy
import sys
import types
import unittest
from pathlib import Path
sys.path[:0] = [str(Path(__file__).parent), str(Path(__file__).parents[1])]
import die_sta as D


class CaptureClocks(unittest.TestCase):
    def model(self):
        return dict(insts=[types.SimpleNamespace(name='cap_a',master='native'), types.SimpleNamespace(name='cap_b',master='native')],
                    buses=[('clk_serial','clock',1,[('pll','serial[0:0]'),('cap_a','ckvb[0:0]'),('cap_b','ckvb[0:0]')])],
                    capture_import=dict(children={'a':'cap_a','b':'cap_b'},counts={'literal_clock_contacts':2},clock_entries=[
                        dict(child=n,pin='ckvb[0]',R_ps={'ss':120,'ff':70,'tt':90}) for n in ('cap_a','cap_b')]))

    def test_means_and_scalar_ranges_use_exact_literal_contacts(self):
        masters={'native':{'insertion_per_clock_pin_ps':{'ckvb[0]':[130,60,95]}}}
        out=D.capture_physical_insertions(self.model(),masters)
        self.assertEqual(out['entries'],2)
        self.assertEqual(masters['native']['physical_insertion_per_clock_pin_ps']['ckvb[0]'],[120,70,90])
        self.assertEqual(masters['native']['insertion_per_clock_pin_ps']['ckvb[0]'],[130,60,95])
        self.assertEqual(D.literal_clock_pin('vm/u/ckv[17:17]'),'vm/u/ckv[17]')
        self.assertEqual(D.clock_sink_key('cap_a','ckvb[0:0]','native',{}),'cap_a/ckvb[0]')
        self.assertEqual(D.clock_sink_key('vm','ckv[17:17]','vm_master',{}),'vm/ckv[17]')
        self.assertEqual(D.literal_clock_pin('ckv[3:0]'),'ckv[3:0]')

    def test_inconsistent_and_missing_native_means_fail(self):
        for mutate in ('conflict','missing_R','missing_entry','missing_child','duplicate'):
            m=self.model();rows=m['capture_import']['clock_entries']
            if mutate=='conflict':rows[1]['R_ps']['ff']=71
            if mutate=='missing_R':rows[1]['R_ps'].pop('tt')
            if mutate=='missing_entry':rows.pop();m['capture_import']['counts']['literal_clock_contacts']=1
            if mutate=='missing_child':m['insts'].pop()
            if mutate=='duplicate':rows[1]['child']=rows[0]['child']
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):
                D.capture_physical_insertions(m,{'native':{}})

if __name__=='__main__':unittest.main()
