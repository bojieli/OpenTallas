"""Mixed reviewed CDC + static bank windows; source lint and mapped OpenSTA counterexamples.

The pd bank here is a graph fixture. Its declared calendar is not a physical proof for a real tile.
Real tiles retain their behavioural minimum-age / overwrite tests in addition to this structural census.
"""
import unittest
from pathlib import Path

import cdc_sync_constraints as S
import clock_entry_constraints as C
import lint_receipt as R
from test_cdc_sync_constraints import Fixture, FIXTURE, spec, sta_case, YOSYS, STA


def mixed_spec():
    s = spec(6)  # s_out takes pd[0]: an otherwise undeclared related-clock data crossing
    s['seam_windows'] = [dict(name='bank', launch='ck_a', capture='ck_b',
                             **{'from': ['*pd*']}, setup_q=2, hold_q=2,
                             why='Test fixture bank held across the prescribed reader edge')]
    return s


class MixedLint(Fixture):
    def test_receipt_key_covers_window_and_roots(self):
        original = R.key_of(R.components(S.KEY, mixed_spec(), self.root, YOSYS))
        for mutate in [lambda s: s['seam_windows'][0].update(setup_q=3),
                       lambda s: s['seam_windows'][0].update(hold_q=3),
                       lambda s: s['seam_windows'][0].update(**{'from': ['*other_bank*']}),
                       lambda s: s['clock_ports'].reverse()]:
            s = mixed_spec()
            mutate(s)
            with self.subTest(spec=s):
                self.assertNotEqual(original, R.key_of(R.components(S.KEY, s, self.root, YOSYS)))

    def test_positive_dispatch_preserves_seam_constraints(self):
        record = S.lint(mixed_spec(), self.root)
        self.assertEqual(record['seam_windows']['bank'], dict(src='core', dst='serial', setup=2, hold=2))
        self.assertIn('pd[0]', record['seam_roles'])
        text = C.generate(mixed_spec(), self.root)
        self.assertIn('ot_cdc_seam_crossing $start $pin', text)
        self.assertIn('ot_cdc_seam_complete', text)
        self.assertIn('ot_cdc_complete $cells', text)
        self.assertIn('missing finite bounded $kind path', text)
        self.assertIn('OT_SEAM_WINDOW bank', C.landed_sdc(mixed_spec(), self.root))
        for banned in ('set_false_path', 'set_clock_groups', 'set_multicycle_path', 'set_disable_timing'):
            self.assertNotIn(banned, text)

    def test_arbitrary_or_overlapping_crossings_refused(self):
        for mutate, why in [
            (lambda s: s['seam_windows'][0].update(**{'from': ['*no_bank*']}), 'matches 0 windows'),
            (lambda s: s['seam_windows'].append(dict(s['seam_windows'][0], name='duplicate')), 'matches 2 windows'),
            (lambda s: s['seam_windows'][0].update(launch='ck_b', capture='ck_a'), 'matches 0 windows'),
        ]:
            s = mixed_spec()
            mutate(s)
            with self.subTest(why=why), self.assertRaisesRegex(ValueError, why):
                S.lint(s, self.root)

    def test_seam_cannot_cover_bad_synchronizer(self):
        # Keep the actual seam, independently corrupt source, first-stage fanout, or direct chain wiring.
        (self.root / 'cdc_fix.sv').write_text(FIXTURE.replace('wire ev =',
                                           "wire [1:0] bad_source = seq ^ 2'b11; wire ev =")
                                           .replace('x1 <= seq;', 'x1 <= bad_source;'))
        bad_source = mixed_spec()
        bad_source['cdc_synchronizers'][0]['source'] = 'bad_source'
        with self.assertRaisesRegex(ValueError, 'not a single flop Q'):
            S.lint(bad_source, self.root)
        for before, after, why in [
            ('(x1 != x2) : ev', '(x1 != x2) : (x1 != x2)', 'stage-1 flop .* drives more'),
            ('x1 <= seq;', 'x1 <= seq ^ 2\'b01;', 'not a direct flop'),
        ]:
            (self.root / 'cdc_fix.sv').write_text(FIXTURE.replace(before, after))
            with self.subTest(why=why), self.assertRaisesRegex(ValueError, why):
                S.lint(mixed_spec(), self.root)


@unittest.skipUnless(Path(YOSYS).exists() and Path(STA).exists(), 'fleet Yosys and OpenSTA required')
class MixedGraph(Fixture):
    def test_mapped_both_dispatches_and_bad_window_is_timed(self):
        (self.root / 'cdc_fix.sv').write_text(FIXTURE.replace('integer MUT = 0', 'integer MUT = 6'))
        out = self.root / 'sta_mixed'
        out.mkdir()
        check = '''set p [find_timing_paths -from [get_cells -quiet *pd*] -to [get_pins -quiet *s_out*/D] -path_delay max]
if {![llength $p]} {error "MISSING_BANK_PATH"}
set s [get_property [lindex $p 0] slack]
puts "BANK_SLACK $s"
if {!(%s)} {error "BAD_BANK_SLACK $s"}
'''
        rc, log = sta_case(self.root, out, 'mixed', mixed_spec, check % '$s >= 0')
        self.assertEqual(rc, 0, log)
        self.assertIn('OT_CDC_SEAM STRUCTURAL_PASS', log)
        self.assertIn('OT_CDC STRUCTURAL_PASS', log)
        rc, log = sta_case(self.root, out, 'bad_window', mixed_spec, check % '$s < 0', lib_delay_ps=1200)
        self.assertEqual(rc, 0, log)
        self.assertIn('BANK_SLACK -', log)  # window violation remains a real negative STA path

        def rogue_source(m):
            q = m['netnames']['s_out']['bits'][0]
            f = next(c for c in m['cells'].values() if c['type'].startswith('$_DFF')
                     and c['connections']['Q'] == [q])
            f['connections']['D'] = m['netnames']['pv']['bits']
        rc, log = sta_case(self.root, out, 'rogue_source', mixed_spec, mutate_module=rogue_source)
        self.assertNotEqual(rc, 0, log)
        self.assertIn('OT_CDC_SEAM: undeclared crossing', log)
        self.assertNotIn('ACTUAL_CDC_GRAPH_PASS', log)


if __name__ == '__main__':
    unittest.main()
