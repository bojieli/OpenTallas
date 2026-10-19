import copy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import gu_hc_contract as hc


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'tail.sv').write_text('exact measured RTL\n')
        self.source_hash = hc._digest(self.root / 'tail.sv')
        self.variant = dict(id='measured', sources={'tail.sv': self.source_hash},
                            native_sources={'tail.sv': self.source_hash},
                            compile_options={'OT_S81_GUNIT_PIN_COPY': 1},
                            lat_n=975, lat_s=973, origin='last HP_N input pin edge',
                            native_audit_sha256=None, gate_result_sha256=None,
                            blocked_reason='native pending')
        self.manifest = self.root / 'manifest.json'
        self.patch = patch.object(hc, 'MANIFEST_PATH', self.manifest)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.gate = dict(schema='opentallas.ref_tile.gate_result.v2', kit='dsdv_gunit_l5',
                         verdict='WARN', cts=True, items=[], source_binding={
                             'remote_archive_verified': True, 'start_commit': 'a' * 40,
                             'files': [dict(path='tail.sv', sha256=self.source_hash)]})
        self.native = dict(schema='opentallas.ref-tile.cts-native-probe.v1',
                           diagnostic_pass=True, measured_reference_coverage=True,
                           launch_over=0, capture_over=0, comb_pins=[],
                           launch={'ps': 200}, capture={'ps': 150},
                           spread_ps={'clk': 50}, ff_spread_ps=49,
                           library_sha256='b' * 64, insertion_sha256='c' * 64,
                           probe_tcl_sha256='d' * 64, clock_refs={'clk': {'src': 'measured'}},
                           gate_source_commit='a' * 40)
        self.write_manifest()

    def write_manifest(self):
        self.manifest.write_text(json.dumps(dict(
            schema='opentallas.s81.gu_hc_contract.v1', variants=[self.variant])))

    def resolve(self, **kwargs):
        return hc.resolve_hc_calendar(self.root,
            compile_options={'OT_S81_GUNIT_PIN_COPY': 1}, **kwargs)

    def pin_receipts(self):
        g, n = self.root / 'gate.json', self.root / 'native.json'
        g.write_text(json.dumps(self.gate))
        self.native['gate_result_sha256'] = hc._digest(g)
        n.write_text(json.dumps(self.native))
        self.variant['gate_result_sha256'] = hc._digest(g)
        self.variant['native_audit_sha256'] = hc._digest(n)
        self.write_manifest()
        return dict(gate_result=g, native_audit=n)

    def test_measured_calendar_blocked_by_default(self):
        c = self.resolve()
        self.assertEqual((c.lat_n, c.lat_s, c.origin), (975, 973, 'last HP_N input pin edge'))
        self.assertFalse(c.admitted)
        with self.assertRaisesRegex(hc.HCContractError, 'native pending'):
            c.require_admitted()

    def test_changed_source_has_no_legacy_fallback(self):
        (self.root / 'tail.sv').write_text('unmeasured RTL')
        with self.assertRaisesRegex(hc.HCContractError, 'no legacy-calendar fallback'):
            self.resolve()
        self.assertEqual((hc.LEGACY_HC_LAT_N, hc.LEGACY_HC_LAT_S), (759, 757))

    def test_missing_source_refused(self):
        (self.root / 'tail.sv').unlink()
        with self.assertRaises(hc.HCContractError):
            self.resolve()

    def test_compile_options_required_exactly(self):
        for options in ({}, {'OT_S81_GUNIT_PIN_COPY': 0},
                        {'OT_S81_GUNIT_PIN_COPY': 1, 'unmeasured': 1}):
            with self.subTest(options=options), self.assertRaises(hc.HCContractError):
                hc.resolve_hc_calendar(self.root, compile_options=options)

    def test_unpinned_pass_file_cannot_unlock(self):
        n = self.root / 'native.json'
        n.write_text(json.dumps(self.native))
        self.assertFalse(self.resolve(native_audit=n).admitted)

    def test_reviewed_complete_matching_receipts_admit_calendar(self):
        self.assertTrue(self.resolve(**self.pin_receipts()).require_admitted().admitted)

    def test_receipts_required_and_exact(self):
        receipts = self.pin_receipts()
        self.assertFalse(self.resolve().admitted)
        receipts['native_audit'].write_text('{}')
        self.assertFalse(self.resolve(**receipts).admitted)

    def test_different_gate_source_refused(self):
        self.gate['source_binding']['files'][0]['sha256'] = '0' * 64
        self.assertFalse(self.resolve(**self.pin_receipts()).admitted)

    def test_native_failures_and_missing_fields_refused(self):
        original = copy.deepcopy(self.native)
        for key, value in [('diagnostic_pass', False), ('launch_over', 1),
                           ('capture_over', 1), ('comb_pins', ['out']),
                           ('measured_reference_coverage', False),
                           ('launch', {'ps': 220.001}), ('capture', {'ps': 190.001}),
                           ('launch', {'ps': float('nan')}), ('ff_spread_ps', None),
                           ('spread_ps', {}), ('ff_spread_ps', 80.001),
                           ('library_sha256', None), ('clock_refs', {}),
                           ('gate_source_commit', 'other')]:
            with self.subTest(key=key, value=value):
                self.native = copy.deepcopy(original)
                self.native[key] = value
                self.assertFalse(self.resolve(**self.pin_receipts()).admitted)

    def test_bad_gate_and_unverified_archive_refused(self):
        original = copy.deepcopy(self.gate)
        for key, value in [('verdict', 'FAIL'), ('cts', False),
                           ('items', [{'severity': 'FAIL'}]), ('kit', 'other')]:
            with self.subTest(key=key):
                self.gate = copy.deepcopy(original)
                self.gate[key] = value
                self.assertFalse(self.resolve(**self.pin_receipts()).admitted)
        self.gate = copy.deepcopy(original)
        self.gate['source_binding']['remote_archive_verified'] = False
        self.assertFalse(self.resolve(**self.pin_receipts()).admitted)


if __name__ == '__main__':
    unittest.main()
