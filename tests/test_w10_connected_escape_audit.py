import importlib.util
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w10_connected_escape_audit as a

class EscapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=[(ROOT/p).read_text() for p in [a.prior.LEF,a.prior.DIR/'inspection.log',a.OUT/'actual_db.lef',a.OUT/'applicable_rules.log']]
        cls.result=a.evaluate(*cls.inputs)

    def test_all_ports_connected_without_claiming_legality(self):
        self.assertEqual(len(self.result['records']),1152)
        self.assertEqual(self.result['classifications']['pin_connected_positive_overlap'],{'PROVABLE':1152})
        self.assertEqual(self.result['classifications']['M5_patch_area'],{'PROVABLE':1152})
        self.assertFalse(self.result['full_legal_access_proved'])

    def test_one_lane_negative_catches_adjacent_pad_ends(self):
        result=a.evaluate(*self.inputs,lanes=1)
        self.assertGreater(result['classifications']['M5_peer_PDN_spacing_bound'].get('REFUTED',0),0)
        examples=[c for r in result['records'] for c in r['constraints']['M5_peer_PDN_spacing_bound']['witness']['conflicts'] if c['peer'].startswith('g_mac')]
        self.assertTrue(any(c['gap_nm']==12 for c in examples))

    def test_short_pad_negative_fails_minarea(self):
        result=a.evaluate(*self.inputs,pad_length=46)
        self.assertEqual(result['classifications']['M5_patch_area'],{'REFUTED':1152})

    def test_zero_overhang_negative_fails_ordinary_enclosure(self):
        result=a.evaluate(*self.inputs,pad_length=24)
        self.assertEqual(result['classifications']['M5_ordinary_Vx_enclosure_overhang'],{'REFUTED':1152})

    def test_enclosure_source_mutant_is_rejected(self):
        mutant=self.inputs[2].replace('ENCLOSURE CUTCLASS Vx 0.011 0.0','ENCLOSURE CUTCLASS Vx 0.012 0.0')
        with self.assertRaisesRegex(ValueError,'ordinary enclosure'):
            a.evaluate(self.inputs[0],self.inputs[1],mutant,self.inputs[3])

    def test_wide_PDN_uses_PRL_row_not_scalar(self):
        rules=a.parse_rules(self.inputs[2])
        self.assertEqual(a.prl_spacing((0,0,24,100),(50,0,170,100),rules['M5']),72)
        self.assertEqual(a.prior.gap((0,0,24,100),(50,0,170,100)),26)

    def test_rule_source_mutant_is_rejected(self):
        mutant=self.inputs[2].replace('ENDTOEND 0.04','ENDTOEND 0.039')
        with self.assertRaisesRegex(ValueError,'changed EOL'):
            a.evaluate(self.inputs[0],self.inputs[1],mutant,self.inputs[3])

    def test_cut_default_is34_not_zero(self):
        self.assertEqual(self.result['rules']['V4']['default_edge_spacing_nm'],34)
        mutant=self.inputs[2].replace('DEFAULT 0.034','DEFAULT 0.0')
        with self.assertRaisesRegex(ValueError,'cut source'):
            a.evaluate(self.inputs[0],self.inputs[1],mutant,self.inputs[3])

    def test_mirrored_union_is_not_rectangle_diagnostic(self):
        self.assertEqual(self.result['classifications']['patch_pin_union_rectangle_diagnostic'],
                         {'PROVABLE':576,'REFUTED':576})

    def test_explicit_cut_table_override_rejects_default_only_evaluator(self):
        mutant=self.inputs[2].replace('Vx       -', 'Vx       0.035')
        with self.assertRaisesRegex(ValueError,'explicit cut'):
            a.parse_rules(mutant)

    def test_EOL_enclosure_and_union_semantics_remain_missing(self):
        for r in self.result['records']:
            self.assertEqual(r['constraints']['Vx_EOL_enclosure_applicability']['classification'],'MISSING')
            self.assertEqual(r['constraints']['pin_union_corner_keepout_rectonly']['classification'],'MISSING')

if __name__=='__main__': unittest.main(verbosity=2)
