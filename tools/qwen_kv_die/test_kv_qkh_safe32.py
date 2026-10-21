"""Source selection and causal refusal controls; no manufactured native PASS."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import head_st_rtl as H
import head_qkh_safe32_rtl as G
import kv_expand_parameters as EP
import kv_qkh_safe32 as Q


class Safe32Selection(unittest.TestCase):
    def test_default_preserves_both_existing_head_snapshots(self):
        with patch.dict(os.environ, {Q.FLAG: '0'}):
            views, rtl = {'old': 'view'}, {'old': 'source'}
            Q.configure(views, rtl)
            self.assertEqual(views, {'old': 'view'})
            self.assertEqual(rtl, {'old': 'source'})
        self.assertEqual(H.generate(), H.OUT.read_text())
        self.assertEqual(H.generate_lk(), H.OUT_LK.read_text())

    def test_successor_preserves_all_connections_and_clock_homes(self):
        txt = G.generate()
        self.assertEqual(txt, G.OUT.read_text())
        for new, old in (
                ('ot_qkh_lane8_nc32c u_l8', 'ot_qkh_lane8 u_l8'),
                ('ot_qkh_ktree_lk_nc32c u_kt', 'ot_qkh_ktree_lk u_kt'),
                ('module ot_qkh_head_native_r4_s_lk_nc32c #(', 'module ot_qkh_head_native_r4_s_lk #('),
                ('module ot_qkh_head_native_r4_ft_s_lk_nc32c #(', 'module ot_qkh_head_native_r4_ft_s_lk #(')):
            txt = txt.replace(new, old)
        self.assertEqual(txt, H.generate_lk())

    def test_missing_profile_refuses_even_with_diagnostic_environment(self):
        with patch.dict(os.environ, {'OT_KV_PARAM_DIAG': '1'}):
            with self.assertRaisesRegex(ValueError, 'missing exact safe32'):
                Q.require_profiles(H.ROOT, {})

    def test_wrong_unsigned_scale_refuses(self):
        profiles = {m: {'parameters': dict(t['parameters'])} for m, t in Q.TARGETS.items()}
        profiles['ot_qkh_lane8_nc32c']['parameters']['LTW'] = 11
        with self.assertRaisesRegex(ValueError, 'missing exact safe32'):
            Q.require_profiles(H.ROOT, profiles)
        profiles['ot_qkh_lane8_nc32c']['parameters']['LTW'] = 12
        # Validate the scale entry directly by putting it first; no native view is fabricated.
        kt = 'ot_qkh_ktree_lk_nc32c'
        profiles[kt]['parameters']['SCALE'] += 1
        with patch.dict(Q.TARGETS, {kt: Q.TARGETS[kt]}, clear=True):
            with self.assertRaisesRegex(ValueError, 'missing exact safe32'):
                Q.require_profiles(H.ROOT, profiles)

    def test_unqualified_artifacts_refuse_diagnostic_bypass_and_stale_bytes(self):
        # Byte fixtures exercise refusal only. There is no frozen receipt or native PASS.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            profiles = {}
            for module, target in Q.TARGETS.items():
                src = root / target['rtl']
                src.parent.mkdir(parents=True, exist_ok=True)
                src.write_bytes((H.ROOT / target['rtl']).read_bytes())
                vd = root / target['view']
                vd.mkdir(parents=True)
                for name in (module + '.lef', module + '_tt.lib', module + '_ff.lib', 'insertion.json'):
                    (vd / name).write_text('UNQUALIFIED REFUSAL FIXTURE\n')
                profiles[module] = {'parameters': target['parameters'],
                                    'identity': EP.artifact_identity(root, target['view'], target['rtl'])}
            with patch.dict(os.environ, {'OT_KV_PARAM_DIAG': '1'}):
                with self.assertRaisesRegex(ValueError, 'qualification missing'):
                    Q.require_profiles(root, profiles)
            first = next(iter(Q.TARGETS.values()))
            (root / first['view'] / 'insertion.json').write_text('CHANGED\n')
            with self.assertRaisesRegex(ValueError, 'profile/source/view mismatch'):
                Q.require_profiles(root, profiles)


    def test_diag_missing_opt_in_needs_both_flags_and_checks_supplied(self):
        with patch.dict(os.environ, {'OT_KV_PARAM_DIAG': '0', Q.DIAG_FLAG: '1'}):
            with self.assertRaisesRegex(ValueError, 'missing exact safe32'):
                Q.require_profiles(H.ROOT, {}, allow_missing=True)
        with patch.dict(os.environ, {'OT_KV_PARAM_DIAG': '1', Q.DIAG_FLAG: '1'}):
            self.assertEqual(Q.require_profiles(H.ROOT, {}, allow_missing=True), list(Q.TARGETS))
            bad = {'ot_qkh_lane8_nc32c': {'parameters': {'ADD_LAT': 7, 'LTW': 11}}}
            with self.assertRaisesRegex(ValueError, 'missing exact safe32'):
                Q.require_profiles(H.ROOT, bad, allow_missing=True)


if __name__ == '__main__':
    unittest.main()
