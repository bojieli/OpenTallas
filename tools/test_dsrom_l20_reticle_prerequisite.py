import hashlib
import json
import subprocess
import unittest
from collections import Counter
from pathlib import Path

import dsrom_l20_reticle_prerequisite as m


class ReticlePrerequisite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = m.build()
        cls.c = cls.d['constrained_alternative']

    def test_rotated_envelope_and_independent_dimension_gate(self):
        self.assertTrue(m.fits(26, 33))
        self.assertTrue(m.fits(33, 26))
        self.assertFalse(m.fits(33.001, 25))
        self.assertFalse(m.fits(27, 27))  # area<858 is insufficient
        self.assertFalse(m.fits(26.001, 33))

    def test_both_rejected_drafts_remain_failed(self):
        for key in ('frozen_owner_proposal', 'cited_earlier_proposal'):
            self.assertFalse(self.d[key]['fits_reticle'])
        self.assertAlmostEqual(self.d['cited_earlier_proposal']['area_mm2'], 1015.00323768576)
        self.assertGreater(self.d['frozen_owner_proposal']['area_mm2'], 1015)

    def test_constrained_dimensions_are_inward_grid_and_not_fit_credit(self):
        w,h = self.c['outline_mm']
        self.assertLessEqual(w,33)
        self.assertLessEqual(h,26)
        self.assertAlmostEqual(w*1000/2.16, round(w*1000/2.16))
        self.assertAlmostEqual(h*1000/2.16, round(h*1000/2.16))
        self.assertTrue(self.c['fits_reticle'])
        self.assertFalse(self.c['legal_relocation_complete'])
        self.assertTrue(self.d['no_admission'])

    def test_full_inventory_and_ports_retained(self):
        rows=self.c['original_instances']
        self.assertEqual(len(rows),14370)
        self.assertEqual(len({r[0] for r in rows}),len(rows))
        self.assertEqual(dict(Counter(r[-1] for r in rows)),self.c['source_instance_counts_by_group'])
        self.assertEqual(len(self.c['original_soft_regions']),607)
        p=self.c['all_ports_and_replica_counts']
        self.assertEqual((p['attention_tiles'],p['HBM_reader_PC_ports'],p['collector_banks_1R1W'],p['index_MACs_per_cycle']),(64,128,4,1024))
        self.assertEqual(len(self.c['displaced_instances_requiring_legal_relocation']),2550)
        self.assertTrue({r['name'] for r in self.c['displaced_instances_requiring_legal_relocation']} <= {r[0] for r in rows})

    def test_capacity_shortfall_and_stage_price(self):
        c=self.c
        self.assertGreater(c['required_field_at_unchanged_stages_mm2'],c['usable_field_mm2'])
        self.assertAlmostEqual(c['gross_packing_recovery_needed_to_keep_all_current_stages_mm2'],14.931969452945408)
        self.assertEqual((c['baseline_stages'],c['capacity_sufficient_stages'],c['additional_layer_dies'],c['capacity_sufficient_total_dies']),(41,43,8,216))
        self.assertEqual(c['additional_stage_events'],2)
        self.assertAlmostEqual(c['die_overhead_fraction'],.125)
        self.assertAlmostEqual(c['added_die_overhead_reservation_mm2'],5.3714725168000115)
        self.assertIn('fabric.hop',c['added_event_latency_expression'])
        self.assertFalse(c['added_latency_measured'])
        self.assertFalse(c['token_rate_certified'])

    def test_exact_provider_and_target_mismatch_remain_explicit(self):
        self.assertTrue(self.c['source_8192row_inventory_is_not_current_4096row_product_fit'])
        self.assertIsNone(self.d['package']['numeric_package_max_width_mm'])
        self.assertIsNone(self.d['package']['numeric_package_max_height_mm'])
        self.assertFalse(self.d['package']['package_admission'])
        self.assertIn('seal-ring',self.d['package']['exact_missing_provider'])

    def test_pins_and_failed_evidence_unchanged(self):
        for p in self.d['pins']:
            if 'revision' in p:
                b=subprocess.check_output(['git','show',p['revision']+':'+p['path']],cwd=m.ROOT)
            else:
                b=(m.OUT/p['path']).read_bytes()
            self.assertEqual(hashlib.sha256(b).hexdigest(),p['sha256'])
        original=json.loads((m.OUT/'inputs/model.json').read_bytes())
        self.assertEqual(self.d['retained_FAILUREs'],original['retained_FAILUREs'])
        self.assertEqual((self.d['clock_ps'],self.d['SS_setup_uncertainty_ps'],self.d['FF_hold_uncertainty_ps']),(833,60,25))
        self.assertTrue(self.d['no_RTL_PnR'])

    def test_artifact_byte_identical_regeneration(self):
        self.assertEqual((m.OUT/'model.json').read_bytes(),m.artifact())


if __name__=='__main__':
    unittest.main()
