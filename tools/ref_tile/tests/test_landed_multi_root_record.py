"""ROOT-INF21 10-19 (coordinator INF.21.1): landed-parent hard children whose CLOSED record is a MULTI-ROOT sign-off.

pgslice_lg's children (KIND0 kind0_l4_leaf1: 7 CTS roots, 5 without boundary flops; bank6_clock7: 3 CTS roots, clk_ws
without boundary flops, + 6 direct SRAM entries) closed with pin registers OFF, so (a) no port_latency.json existed and
(b) landed_raw_pins only knew the one-root hybrid-entries record.  The multi-root record co-times EVERY clock pin to one
phase (latency = phi - wire - R, R per root = boundary mean, else all-internal mean; direct rows R 0), so the parent:
  - generates port_latency.json from the closed record + the ROUTED-view STA (insertion.json), never an invented value;
  - judges each raw pin (and each other boundary root) against the boundary root with the largest R, tolerance = the
    record's per-pair hold uncertainty - rule H1 margin;
  - taps every pin except the anchor (largest R) by R(anchor) - R(p): a delay-only tap on the RAW pin cannot make it
    EARLIER than its boundary ref (bank clk_ws 151 vs clk_rd 85), so the boundary pins are delayed instead.
Hybrid-entries kits stay byte-identical (test_landed_raw_child_pins)."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import clock_entry_constraints as CE  # noqa: E402
import port_latency as PL  # noqa: E402
import pre_route_gate as G  # noqa: E402
import ref_tile as RT  # noqa: E402
import test_landed_cluster_kit as K  # noqa: E402
import test_landed_raw_child_pins as H  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
REPO = ROOT
JOB = H.JOB

# the record lines landed_record_pins reads, as the multi-root leaf sign-off (bank6_clock7 r12) writes them
SIGNOFF = '''set ::ot_ce_cts_roots {{CLK} {CKP}}
set ::ot_ce_ports {{CLK} {CKP}}
    if {![llength $boundary]} { set boundary $pins; set scope all_internal_only }
    lappend rows [list [get_ports $name] [lindex $pins 0] 0 $lo $mean $hi $clock $mean $domain]
    set latency [expr {$ref - $wire - $mean}]
      set_clock_uncertainty -setup [expr {($an in $ot_ce_high || $bn in $ot_ce_high) ? 210 : 150}] -from $a -to $b
      set_clock_uncertainty -hold HOLD -from $a -to $b
'''


def leaf(root, r_int=170.0, hold='100', clocks=('CLK', 'CKP'), sdc=SIGNOFF, measured=True, ckp_macro=False):
    """closed MULTI-ROOT leaf 'hard': CLK = CTS root with boundary flops (R 100); CKP = CTS root WITHOUT boundary flops
    (all-internal R r_int, larger than CLK's: CKP is the anchor, CLK must be delayed)"""
    v = H.leaf(root, hold=hold, clocks=clocks)
    (root / 'results' / 'rtl' / 'ref_tile' / 'leaf' / JOB / 'signoff.sdc').write_text(sdc.replace('HOLD', hold))
    ins = json.loads((v / 'insertion.json').read_text())
    a = dict(n=40, min=r_int - 10, mean=r_int, max=r_int + 10)
    ins['clock_measurements']['CKP'] = {c: dict(boundary=None, all=a, errors=[],
                                                **(dict(macros=dict(n=1)) if ckp_macro else dict(macros=None)))
                                        for c in CE.CORNERS}
    (v / 'insertion.json').write_text(json.dumps(ins))
    if measured:
        pl = json.loads((v / 'port_latency.json').read_text())
        pl['clock_reference'] = {'CLK': {c: dict(mean=100.0) for c in CE.CORNERS},
                                 'CKP': {c: dict(mean=r_int) for c in CE.CORNERS}}
        (v / 'port_latency.json').write_text(json.dumps(pl))
    return v


class MultiRootRecord(unittest.TestCase):
    def test_reference_anchor_and_tolerance_from_the_record(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rec = CE.landed_record_pins(leaf(root), root)
            self.assertEqual(rec['model'], 'multi_root')
            self.assertEqual(sorted(rec['raw']), ['CKP'])
            self.assertEqual((rec['raw']['CKP']['ref'], rec['raw']['CKP']['tol']), ('CLK', 50.0))
            self.assertEqual(rec['raw']['CKP']['refs']['tt'], [160.0, 170.0, 180.0])    # routed all-internal sinks
            self.assertEqual(rec['anchor'], 'CKP')
            self.assertEqual(rec['cotimed'], {})                                        # one boundary root = the ref
            self.assertEqual(CE.landed_raw_pins(root / 'hard', root), rec['raw'])

    def test_hybrid_record_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rec = CE.landed_record_pins(H.leaf(root), root)
            self.assertEqual((rec['model'], rec['anchor'], rec['cotimed']), ('hybrid', None, {}))

    def test_refusals_fail_closed(self):
        cases = {
            'no all-internal reference scope in the record': dict(sdc=SIGNOFF.replace('set scope all_internal_only', '')),
            'no per-root measured row': dict(sdc=SIGNOFF.replace('lappend rows [list [get_ports $name]', 'lappend x [list')),
            'no entry compensation': dict(sdc=SIGNOFF.replace('set latency', 'set lat')),
            'no die-skew tolerance': dict(hold='50'),
            'record roles differ': dict(clocks=('CLK',)),
            'internal root measured as a macro pin': dict(ckp_macro=True),
            'no boundary root to co-time with': dict(sdc=SIGNOFF.replace('{{CLK} {CKP}}\nset ::ot_ce_ports', '{{CKP} {CLK}}\nset ::ot_ce_ports')
                                                     .replace('set ::ot_ce_ports {{CLK} {CKP}}', 'set ::ot_ce_ports {{CLK} {CKP}}')),
        }
        # the last case keeps both roots; make CLK lose its boundary instead
        for why, kw in cases.items():
            with tempfile.TemporaryDirectory() as d, self.subTest(why=why):
                root = Path(d)
                v = leaf(root, **kw)
                if why.startswith('no boundary root'):
                    ins = json.loads((v / 'insertion.json').read_text())
                    for c in CE.CORNERS:
                        ins['clock_measurements']['CLK'][c]['boundary'] = None
                    (v / 'insertion.json').write_text(json.dumps(ins))
                with self.assertRaises(ValueError):
                    CE.landed_record_pins(v, root)

    def test_generated_reference_must_match_the_routed_view(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            v = leaf(root)
            pl = json.loads((v / 'port_latency.json').read_text())
            pl['clock_reference']['CKP']['ff']['mean'] = 120.0
            (v / 'port_latency.json').write_text(json.dumps(pl))
            with self.assertRaisesRegex(ValueError, 'clock_reference CKP/ff'):
                CE.landed_record_pins(v, root)

    def test_tap_delays_the_boundary_pin_to_the_anchor(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            leaf(root)
            s = K.load(root, H.spec(root))
            tg = CE.landed_tap_targets(s, root)
            self.assertEqual(sorted(tg), ['hard/CLK'])
            self.assertEqual((tg['hard/CLK']['ref'], tg['hard/CLK']['tt']), ('CKP', 70.0))   # R(CKP) 170 - R(CLK) 100
            self.assertEqual(CE.landed_tap_targets(s, root), CE.landed_tap_targets(s, root))
            self.assertEqual(CE.landed_raw_tcl(s, root)[0], 'set ::ot_lrt_targets [dict create {hard/CLK} {ref CKP tt 70 ff 70 ss 70}]')
            # the pre-CTS admission dict still names only the RAW pin (CLK stays an ordinary register sink)
            self.assertEqual(CE.landed_pre_cts_tcl(s, root)[1], 'set ::ot_ce_landed_raw [dict create {hard/CKP} {ref CLK}]')
            text = CE.generate(s, root)
            self.assertIn('set ::ot_ce_landed_raw [dict create {hard/CKP} {ref CLK tol 50', text)
            self.assertNotIn('ot_ce_landed_cotimed', text)               # one boundary root: nothing else to co-time
            self.assertIn('{hard/CKP} {tt {160.0 170.0 180.0}', text)

    def test_second_boundary_root_is_co_timed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            v = leaf(root)
            rec = CE.landed_record_pins(v, root)
            body = CE.landed_raw_body(CE.LANDED_BODY, True)
            self.assertIn('OT_LANDED COTIMED_PIN', body)
            self.assertNotIn('COTIMED_PIN', CE.landed_raw_body(CE.LANDED_BODY))
            self.assertEqual(rec['cotimed'], {})


class Unregistered(unittest.TestCase):
    """port_latency.py --unregistered-view on the two real pgslice_lg children (committed closed records)"""
    VIEWS = {
        'hbm_su_static_kind0_l4_leaf1_1015-r2-18978c835':
            'physical/ref_tile/hbm_su_static_kind0_l4_leaf1_1015/views/ot_hbm_su_static_kind0_lat4_leaf1_physical',
        'hbm_su_static_bank6_clock7_1015-r12-0a5f7732e':
            'physical/ref_tile/hbm_su_static_bank6_clock7_1015/views/ot_hbm_su_static_bank6_clock_physical',
    }

    def setUp(self):
        if not all((REPO / v / 'insertion.json').is_file() for v in self.VIEWS.values()):
            self.skipTest('pgslice_lg child views not checked out')
        if subprocess.run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], capture_output=True).returncode:
            self.skipTest('no git history (closing kit.env is read at the source commit)')

    def test_committed_files_are_the_generator_output_and_bind(self):
        for job, v in self.VIEWS.items():
            with self.subTest(job=job):
                rep = PL.export_unregistered(REPO / v, job, REPO)
                self.assertEqual(rep, json.loads((REPO / v / 'port_latency.json').read_text()))
                self.assertFalse(rep['pin_registers'])
                rec = CE.landed_record_pins(REPO / v, REPO)
                self.assertEqual(rec['model'], 'multi_root')
                a = rec['anchor']
                for p, r in rec['R'].items():
                    self.assertGreaterEqual(r['tt'], 0)
                    self.assertLessEqual(r['tt'], rec['R'][a]['tt'])

    def test_real_references(self):
        rec = CE.landed_record_pins(REPO / self.VIEWS['hbm_su_static_bank6_clock7_1015-r12-0a5f7732e'], REPO)
        self.assertEqual(rec['anchor'], 'clk_ws')                          # internal-only root, R 151.1 TT
        self.assertEqual(rec['raw']['clk_ws']['ref'], 'clk_rd')            # largest boundary R (84.9 TT)
        self.assertEqual(sorted(rec['cotimed']), ['clk'])
        self.assertEqual(rec['raw']['clk_ws']['tol'], 50.0)
        k0 = CE.landed_record_pins(REPO / self.VIEWS['hbm_su_static_kind0_l4_leaf1_1015-r2-18978c835'], REPO)
        self.assertEqual((k0['anchor'], sorted(k0['cotimed'])), ('clk_stage_0', ['clk_stage_7']))
        self.assertEqual(sorted(k0['raw']), ['clk_stage_1', 'clk_stage_2', 'clk_stage_3', 'clk_stage_5', 'clk_stage_6'])

    def test_refuses_registered_or_foreign_view(self):
        job, v = next(iter(self.VIEWS.items()))
        other = list(self.VIEWS.values())[1]
        with self.assertRaisesRegex(ValueError, 'not the record view directory'):
            PL.export_unregistered(REPO / other, job, REPO)


class MultiRootGate(unittest.TestCase):
    """pre_route_gate.root_child_flops: the internal-only root judged vs the boundary ref at its routed all-internal R"""

    def judge(self, ckp_arr, clk_arr=20.0):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            leaf(root)
            pins = [dict(pin='h/CLK', arr=clk_arr), dict(pin='h/CKP', arr=ckp_arr)]
            dom = dict(source='ck_ra', **{c: dict(all=dict(n=8, min=110, max=130), macros=dict(n=2, pins=pins),
                                                  child_flop=dict(soft=dict(all=dict(n=6, min=110, max=130))))
                                          for c in ('tt', 'ff')})
            old = G.ROOT
            G.ROOT = root
            try:
                return G.root_child_flops(dom, dict(children=[dict(view='hard', inst='h')]), None)
            finally:
                G.ROOT = old

    def test_tapped_clk_passes_equal_pin_arrival_fails(self):
        self.assertNotIn('raw_pin_fail', self.judge(20.0, clk_arr=90.0))   # CLK tapped +70: 90+100 == 20+170
        out = self.judge(20.0)                                              # TritonCTS alone: CKP 70 late
        self.assertRegex(out['raw_pin_fail'][0], r'TT raw child clock pin h/CKP \+70\.0 ps vs h/CLK')


@unittest.skipUnless(K.available(), 'real OpenROAD ORFS image required')
class MultiRootOpenroad(unittest.TestCase):
    """TritonCTS + clock_entries.tcl + tap + generated SDC on the multi-root fixture: the tap delays the BOUNDARY pin
    CLK by R(CKP) - R(CLK) = 70 so the internal root CKP (raw, no ETM arcs) co-times with CLK's flops; without the
    tap the raw check fails (+70 > 50)."""

    def run_flow(self, mutant=''):
        with tempfile.TemporaryDirectory() as d:
            w = Path(d)
            leaf(w)
            s = H.spec(w)
            s['children'][0]['view'] = 'hard'
            s['landed_record'] = 'top_lp_record.json'
            rtl = H.RTL.replace('u_lpl_0_w.bank_reg', '\\u_lpl_0_w.bank_reg ').replace('u_lpl_0_r.o_reg', '\\u_lpl_0_r.o_reg ')
            (w / 't.v').write_text(rtl)
            entries = 'set ::ot_ce_require_wire 1\n' + CE.generate(s, w) + CE.landed_sdc(s, w)
            (w / 'clocks.tcl').write_text(CE.clocks(s, 833.333))
            (w / 'entries.tcl').write_text(entries)
            hand = 'set ::ot_ce_counts [dict create hard 1]\n'
            flow = Path(K.__file__).read_text().split("flow = r\'\'\'", 1)[1].split("\'\'\'", 1)[0]
            pre = CE.landed_pre_cts_tcl(s, w)
            flow = flow.replace(hand, '').replace('FLAG', 'set ::ot_ce_landed_cluster 1\n' + '\n'.join(pre) + '\n')
            if mutant != 'no_tap':
                hook = 'source /src/physical/common_flow/clock_entries.tcl\n'
                flow = flow.replace(hook, hook + '\n'.join(CE.landed_raw_tcl(s, w)) + '\n')
            flow = flow.replace('READ_CLOCKS', 'source /w/clocks.tcl').replace('READ_ENTRIES', 'source /w/entries.tcl')
            (w / 'run.tcl').write_text(flow)
            proc = subprocess.run(['docker', 'run', '--rm', '-v', f'{w}:/w', '-v', f'{ROOT}:/src:ro',
                                   K.IMAGE, K.OR, '-no_init', '-exit', '/w/run.tcl'], capture_output=True, text=True, timeout=180)
            return proc.returncode, proc.stdout + proc.stderr

    RAW = r'OT_LANDED RAW_PIN tt ck_ra h/CKP wire=(\S+) R=170(?:\.0)? eff=(\S+) co_timed=h/CLK eff_ref=(\S+) skew=(\S+) tol=(\S+) (PASS|FAIL)'

    def test_tap_on_the_boundary_pin(self):
        rc, out = self.run_flow()
        self.assertEqual(rc, 0, out[-6500:])
        m = re.search(self.RAW, out)
        self.assertIsNotNone(m, out[-6500:])
        print(f'\nmulti-root RAW_PIN with tap: {m[0]}\n' + '\n'.join(re.findall(r'^OT_LRT DONE.*$', out, re.M)))
        self.assertEqual(m[6], 'PASS')
        self.assertRegex(out, r'OT_LRT DONE tt h/CLK buffers=[1-9]\d* raw-ref=\S+ target=70')
        self.assertIn('LANDED_RESULT PASS', out)

    def test_without_tap_fails(self):
        rc, out = self.run_flow('no_tap')
        m = re.search(self.RAW, out)
        self.assertIsNotNone(m, out[-6500:])
        self.assertEqual(m[6], 'FAIL')
        self.assertGreater(float(m[4]), 50)
        self.assertNotEqual(rc, 0)


if __name__ == '__main__':
    unittest.main()
