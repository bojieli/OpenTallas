import hashlib
import json
import unittest
from pathlib import Path

from kv_retained_export import ROOT, DEST, FILES, transform, once


class RetainedExport(unittest.TestCase):
    def test_source_and_emitted_identities(self):
        manifest = json.loads((ROOT / DEST / 'manifest.json').read_text())
        self.assertFalse(manifest['production_selected'])
        self.assertFalse(manifest['native_CDC_qualified'])
        self.assertFalse(manifest['complete_health_retirement_qualified'])
        self.assertEqual({str(p) for p in FILES}, {p['source'] for p in manifest['files']})
        for row in manifest['files']:
            with self.subTest(source=row['source']):
                src = (ROOT / row['source']).read_bytes()
                out = (ROOT / row['output']).read_bytes()
                self.assertEqual(hashlib.sha256(src).hexdigest(), row['source_sha256'])
                self.assertEqual(hashlib.sha256(out).hexdigest(), row['output_sha256'])
                self.assertEqual(transform(Path(row['source']).name, src.decode()).encode(), out)

    def test_export_does_not_change_sequential_equations(self):
        # Each clone may add a wire/port/connection only. The actual POR state
        # update and every original sequential block must remain byte exact.
        import re
        pattern = r'always\s*@.*?(?=\n (?:always|wire|reg|assign|initial)|\nendmodule|\Z)'
        for p in FILES:
            if p.name == 'qkd_host_root_admission.sv':
                continue
            src = (ROOT / p).read_text()
            out = transform(p.name, src)
            self.assertEqual(re.findall(pattern, src, re.S), re.findall(pattern, out, re.S), str(p))

    def test_exact_chain_and_real_state(self):
        d = ROOT / DEST
        su = (d / 'qkd_host_ctrl_token_service_packet_collected_rh.sv').read_text()
        mu = (d / 'qkd_host_ctrl_token_service_packet_collected_mu_rh.sv').read_text()
        rank = (d / 'qkd_host_root_admission_rh.sv').read_text()
        self.assertIn('assign retained_context=retained_request;', su)
        self.assertIn('assign retained_context=retained_request;', mu)
        self.assertIn('wire retained_request=|rr;', mu)
        self.assertIn('.retained_ctx(retained_context)', rank)
        self.assertIn('.recovery_certified(native_recovery_clear)', rank)
        self.assertIn('.por_n(por_n&&pll_locked)', rank)
        self.assertNotIn('.retained_ctx(1\'b0)', rank)
        for name in ('qkd_host_packet_bundle_admission_rh.sv', 'qkd_host_control_packet_admission_rh.sv'):
            self.assertIn('.retained_context(retained_context)', (d / name).read_text())

    def test_shape_drift_refused(self):
        with self.assertRaises(ValueError):
            once('a a', 'a', 'b')
        with self.assertRaises(ValueError):
            transform('unknown.sv', '')


if __name__ == '__main__':
    unittest.main()
