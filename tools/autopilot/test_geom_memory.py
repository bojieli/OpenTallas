import tempfile
import unittest
from pathlib import Path
import geom_rules as R

LIB='''library(test) {cell(ram) {memory(){type:ram;} pin(clk){direction:input;clock:true;} pin(d){direction:input;timing(){related_pin:"clk";timing_type:setup_rising;}timing(){related_pin:"clk";timing_type:hold_rising;}} pin(q){direction:output;timing(){related_pin:"clk";timing_type:rising_edge;}}}}'''
DUMP='''D\t0\t0\t600\t100
C\t1\tS\tDFF\t0\t0\t2\t2\tlaunch
C\t2\tM\tram\t390\t0\t420\t50\tmem
C\t3\tS\tDFF\t500\t0\t502\t2\tcapture
I\tram\tclk:INPUT\td:INPUT\tq:OUTPUT
N\tSIGNAL\ti1\ti2
N\tSIGNAL\ti2\ti3
'''

class TypedMemory(unittest.TestCase):
    def run_model(self,lib=LIB,dump=DUMP):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'g.tsv').write_text(dump);(p/'m.lib').write_text(lib or '')
            return R.r2r_metrics(R.Design(p/'g.tsv',[p/'m.lib'] if lib else [],memory_reach=True))
    def test_real_synchronous_boundary_uses_full_macro_pin_bound(self):
        m=self.run_model();self.assertEqual(m['r2r_memory_instances'],1);self.assertEqual(m['r2r_captures'],2)
        self.assertEqual(m['r2r_max'],468);self.assertEqual(m['r2r_captures_gt405'],1);self.assertFalse(m['r2r_incomplete_macros'])
    def test_missing_model_never_silently_passes_flop_only(self):
        self.assertTrue(self.run_model(None)['r2r_incomplete_macros'])
    def test_missing_metadata_makes_existing_r2r_rule_na(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'g.tsv';p.write_text(DUMP)
            metrics=R.metrics(p,odb='3_place.odb',memory_reach=True)
            rules,_=R.judge(metrics,None,[600,100])
            self.assertEqual([r['status'] for r in rules if r['rule']=='r2r'],['NA'])
    def test_unknown_memory_without_clocked_output_is_incomplete(self):
        m=self.run_model(LIB.replace('timing_type:rising_edge;','timing_type:combinational;'))
        self.assertEqual(m['r2r_memory_instances'],0);self.assertTrue(m['r2r_incomplete_macros'])
    def test_missing_actual_master_inventory_is_incomplete(self):
        self.assertTrue(self.run_model(dump=DUMP.replace('I\tram\tclk:INPUT\td:INPUT\tq:OUTPUT\n',''))['r2r_incomplete_macros'])
    def test_extra_physical_port_cannot_hide_incomplete_timing(self):
        self.assertTrue(self.run_model(dump=DUMP.replace('q:OUTPUT','q:OUTPUT\textra:INPUT'))['r2r_incomplete_macros'])
    def test_explicit_nonmemory_macro_is_not_reclassified(self):
        m=self.run_model('library(test){cell(ram){pin(a){direction:input;}}}')
        self.assertEqual(m['r2r_memory_instances'],0);self.assertFalse(m['r2r_incomplete_macros'])

    def test_default_off_keeps_flop_only_r2r(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'g.tsv').write_text(DUMP);(p/'m.lib').write_text(LIB)
            m=R.r2r_metrics(R.Design(p/'g.tsv',[p/'m.lib']))
            self.assertEqual(m['r2r_memory_instances'],0);self.assertFalse(m['r2r_incomplete_macros'])
            self.assertLessEqual(m['r2r_max'],405)
            rules,_=R.judge(R.metrics(p/'g.tsv',odb='3_place.odb'),None,[600,100])
            self.assertNotIn('complete sequential reach',str([r for r in rules if r['rule']=='r2r']))
    def test_geom_check_passes_memory_flags_only_when_opted_in(self):
        s=Path(__file__).with_name('geom_check.sh').read_text()
        self.assertIn('OT_GEOM_MEMORY_REACH:-0',s);self.assertIn('GA+=(--memory-reach)',s)

if __name__=='__main__':unittest.main()
