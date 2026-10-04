import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class SourceDefaultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Restore only our temporary search path; do not unload canonical
        # modules or relax any pinned runtime identity guard.
        previous=sys.path[:]
        try:
            sys.path.insert(0,str(ROOT/'tools'))
            spec=importlib.util.spec_from_file_location('combined_default_link',ROOT/'tools/qwen_rom_combined_link_source_defaults.py')
            cls.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.m)
        finally:sys.path[:]=previous

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/'top.sv'
        self.source.write_text('module actual_selected_top #(parameter integer NPC = 32,\nparameter integer HBM_LAYERS = 3)(input clk); endmodule\n')
        self.record={'die':['-GG=6144','-GHBM_LAYERS=36'],'source_defaults':{'die':{
            'NPC':{'value':32,'source':'top.sv','source_sha256':self.m.sha(self.source)},
            'HBM_LAYERS':{'value':3,'source':'top.sv','source_sha256':self.m.sha(self.source)}}}}

    def test_actual_default_is_separate_and_cli36_remains(self):
        before=copy.deepcopy(self.record)
        resolved=self.m.resolved_parameters(self.record,'die',self.root)
        self.assertEqual(resolved,{'G':6144,'HBM_LAYERS':36,'NPC':32})
        self.assertEqual(self.record,before)
        self.assertNotIn('-GNPC=32',self.record['die'])

    def test_changed_source_false_default_or_missing_pin_rejected(self):
        for change in ('pin','value','source','missing_pin'):
            r=copy.deepcopy(self.record);e=r['source_defaults']['die']['NPC']
            if change=='pin':e['source_sha256']='0'*64
            if change=='value':e['value']=31
            if change=='source':e['source']='../top.sv'
            if change=='missing_pin':del e['source_sha256']
            with self.subTest(change=change),self.assertRaises((ValueError,KeyError)):
                self.m.resolved_parameters(r,'die',self.root)

    def test_real_selected_top_source_default(self):
        path=ROOT/'rtl/qwen_sys/combined/ot_qwen_rom_combined_die.sv'
        r={'die':['-GHBM_LAYERS=36'],'source_defaults':{'die':{'NPC':{
            'value':32,'source':str(path.relative_to(ROOT)),'source_sha256':self.m.sha(path)}}}}
        self.assertEqual(self.m.resolved_parameters(r,'die')['NPC'],32)
        self.assertEqual(r['die'],['-GHBM_LAYERS=36'])

if __name__=='__main__':unittest.main()
