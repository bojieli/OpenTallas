#!/usr/bin/env python3
"""Focused actual HA8 source-forwarding checks; no whole-system lint or simulation."""
import argparse
from pathlib import Path
import re
import unittest
import hbm_accel_epilogue_ha8 as A

PARENT = None


class Forwarding(unittest.TestCase):
    def test_original_ports_arithmetic_and_memory_preserved(self):
        original = (PARENT/A.ENGINE).read_text()
        candidate = (A.ROOT/A.SUCCESSOR).read_text()
        # Entire source, not a sampled pin list: covers all widths/directions,
        # MAC/reducer order, result retirement and the x/scale memory services.
        self.assertEqual(A.original_engine(candidate), original)
        self.assertIn('parameter integer ENABLE_HA3 = 0', candidate)

    def test_default_does_not_select_successors(self):
        selected = A.select_native_engine(installer_root=PARENT)
        self.assertEqual(selected['module'], 'ot_gpu_sm_q')
        self.assertEqual(selected['parameters'], {})
        self.assertEqual(selected['sources'], [str(PARENT/A.ENGINE)])

    def test_actual_installer_sources_forwarded_unchanged(self):
        r = A.forward_installer(installer_root=PARENT, enable_ha3_clock_lookahead=True)
        self.assertEqual(r['installer_sources'], [str(PARENT/p) for p in (PARENT/A.LIST).read_text().splitlines()])
        self.assertTrue(all(A.sha(PARENT/p)==v for p,v in r['installer_source_sha256'].items()))
        selected = r['selected_native_engine']
        self.assertEqual(selected['module'],'ot_hbm_accel_sm_q')
        self.assertEqual(selected['parameters'],{'ENABLE_HA3':1})
        self.assertFalse(r['numerical_fusion'])
        self.assertIsNone(r['measured_real_sm_cycles'])
        self.assertFalse(r['adopted'])

    def test_one_definition_per_forwarded_module(self):
        r = A.forward_installer(installer_root=PARENT, enable_ha3_clock_lookahead=True)
        definitions = {}
        references = set()
        for p in r['candidate_sources']:
            text=Path(p).read_text()
            text=re.sub(r'/\*.*?\*/','',text,flags=re.S)
            text=re.sub(r'//[^\n]*','',text)
            for name in re.findall(r'\bmodule\s+(\w+)',text):
                self.assertNotIn(name,definitions,'duplicate definition '+name)
                definitions[name]=p
            references.update(re.findall(r'^\s*(ot_\w+)\s+(?:#|\w+\s*\()',text,re.M))
        # These undefined modules intentionally trap invalid CUTS overrides.
        # Native engine's existing LAT7 wrappers do not override CUTS=-1.
        guards={'ot_hdc_fp32_add_lat_CUTS_must_match_LAT','ot_hdc_fp32_mul_lat_CUTS_must_match_LAT'}
        missing=references-set(definitions)-guards
        self.assertFalse(missing,'missing module definitions '+str(missing))
        self.assertIn('ot_hbm_accel_sm_q',definitions)
        self.assertNotIn('ot_gpu_sm_q',definitions)
        self.assertIn('ot_gpu_full_sm_service_guarded',definitions)
        # The currently installed guarded SM must stay a separate definition.
        self.assertNotEqual(definitions['ot_hbm_accel_sm_q'],definitions['ot_gpu_full_sm_service_guarded'])

    def test_changed_native_engine_pin_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/A.ENGINE;p.parent.mkdir(parents=True);p.write_text('module changed; endmodule\n')
            with self.assertRaisesRegex(ValueError,'source pin changed'):
                A.select_native_engine(installer_root=Path(d),enable_ha3_clock_lookahead=True)

    def test_extra_arithmetic_change_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            # Keep the real pinned engine and change the caller's arithmetic:
            # the source pin check must refuse before handing over a candidate.
            p=root/A.ENGINE;p.parent.mkdir(parents=True)
            p.write_bytes((PARENT/A.ENGINE).read_bytes().replace(b'.ALAT(7)',b'.ALAT(6)',1))
            with self.assertRaisesRegex(ValueError,'source pin changed'):
                A.select_native_engine(installer_root=root,enable_ha3_clock_lookahead=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--installer-root',type=Path,required=True)
    a=ap.parse_args();PARENT=a.installer_root.resolve()
    unittest.main(argv=['hbm_accel_epilogue_ha8_test.py'])
