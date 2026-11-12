"""Default-off coverage for writer metadata and standalone FREG bit placement."""
import json
import re
import subprocess
import unittest
from pathlib import Path
import clock_landings as C
import landing_place as L
import schema as S


class WriterOptinTests(unittest.TestCase):
    def typ(self, **kw):
        return {'clock': {'landing_ring_wreg': dict(buses=['i'], dsrep=8, freg=True, **kw)}}

    def cfg(self, **kw):
        return C.ring_write_reg({'partition_types': {'t': self.typ(**kw)}}, 't', 'i')

    def test_legacy_default_and_explicit64_keep_original_metadata(self):
        old = dict(depth=2, dsrep=8, freg=True)
        self.assertEqual(self.cfg(), old)
        self.assertEqual(self.cfg(write_chunk=64), old)
        # CLAND-SLEW-1: no write rows (legacy 64), but the dsrep 8 select copies are keyed at their 8-bit read groups
        self.assertIn('{u_cland_i} {write 0 read 8}', L._local_chunk_config(self.typ()))
        self.assertIn('{u_cland_i} {write 0 read 8}', L._local_chunk_config(self.typ(write_chunk=64)))
        self.assertNotIn("dict set ::cland_numeric_freg_banks", L._local_chunk_config(self.typ()))

    def test_chunk_does_not_implicitly_enable_numeric_freg(self):
        t = self.typ(write_chunk=8)
        text = L._local_chunk_config(t)
        self.assertIn('{u_cland_i} {write 8 read 8}', text)
        self.assertNotIn('dict set ::cland_numeric_freg_banks', text)
        self.assertNotIn('freg_numeric_order', self.cfg(write_chunk=8))

    def test_only_selected_exact_face_prefix_is_enabled(self):
        t = self.typ(freg_numeric_order=True)
        t['clock']['landing_contract'] = {'bands': {'i': {'instance': 'exact_i'}}}
        text = L._local_chunk_config(t)
        self.assertIn('dict set ::cland_numeric_freg_banks {exact_i.g_freg.u_face} 1', text)
        self.assertNotIn('u_cland_other', text)
        self.assertTrue(self.cfg(freg_numeric_order=True)['freg_numeric_order'])

    def test_bad_flag_and_missing_freg_fail(self):
        for bad in [1, 'true', None]:
            with self.assertRaises(ValueError): self.cfg(freg_numeric_order=bad)
        t = self.typ(freg_numeric_order=True);t['clock']['landing_ring_wreg']['freg'] = False
        with self.assertRaises(ValueError): C.ring_write_reg({'partition_types': {'t': t}}, 't', 'i')

    def test_checked_in_schema_matches_emitter(self):
        self.assertEqual(json.loads(Path(S.__file__).with_name('die_plan.schema.json').read_text()), S.SCHEMA)

    def order(self, enabled, reverse=False, prefix='u_cland_i.g_freg.u_face'):
        text = Path(L.__file__).with_name('landing_placement.tcl').read_text()
        proc = re.search(r'proc cland_freg_rekey \{.*?\n\}\n', text, re.S).group()
        gate = re.search(r'  if \{\$base eq \{\} && \[info exists ::cland_numeric_freg_banks\].*?\{ set base "\$\{prefix\}/q" \}', text, re.S).group()
        body = proc + '\nset base {}\nset prefix {' + prefix + '}\n'
        if enabled: body += 'set ::cland_numeric_freg_banks {u_cland_i.g_freg.u_face 1}\n'
        body += gate + '\nset ffs [list '
        body += ' '.join('[list {u_cland_i.g_freg.u_face/q[' + str(n) + ']$_DFF_P_} ' + str(n) + ']' for n in [100, 2, 0]) + ']\n'
        body += 'if {$base ne {}} {lassign [cland_freg_rekey $ffs $base 128 ' + str(int(reverse)) + '] nf ffs}\n'
        body += 'foreach p [lsort -index 0 $ffs] {puts [lindex $p 1]}\n'
        p = subprocess.run(['tclsh'], input=body, text=True, capture_output=True, check=True)
        self.assertEqual(p.stderr, '')
        return [int(x) for x in p.stdout.split()]

    def test_default_standalone_freg_keeps_old_order(self):
        self.assertEqual(self.order(False), [0, 100, 2])

    def test_selected_standalone_freg_numeric_and_reverse(self):
        self.assertEqual(self.order(True), [0, 2, 100])
        self.assertEqual(self.order(True, True), [100, 2, 0])

    def test_neighbor_freg_never_inherits_selection(self):
        self.assertEqual(self.order(True, prefix='other.g_freg.u_face'), [0, 100, 2])


if __name__ == '__main__':unittest.main()
