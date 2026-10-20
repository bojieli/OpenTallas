"""ROOT-RST 2026-10-19: reset landing -- the ref_tile kit option (ot_pin_regs.tcl OT_RST_LAND), its role audit
(port_latency.validate_roles), the gate record / args (pre_route_gate) and the Gate-Rule requirement (source_binding)."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/ref_tile'))
import ref_tile as RT  # noqa: E402
import port_latency as PL  # noqa: E402
import pre_route_gate as PG  # noqa: E402
import source_binding as SB  # noqa: E402

PORTS = '''input [0:0] ck
input [0:0] rst_n
input [7:0] d
output [7:0] q'''


def generate(path, pin_regs=True, land=True, stages=None):
    env = ''.join([
        'set ::env(OT_PIN_REGS) 1\n' if pin_regs else '',
        'set ::env(OT_RST_LAND) 1\n' if land else '',
        f'set ::env(OT_RST_LAND_STAGES) {stages}\n' if stages is not None else ''])
    script = '''set ::env(DESIGN_NAME) example
set ::env(OT_PIN_REGS_CLOCK) ck
set ::env(OT_PIN_REGS_RESET_PORTS) rst_n
set ::env(RESULTS_DIR) {%s}
%s
proc yosys {args} {
 if {[lindex $args 0] eq "tee"} {
  set f [open [lindex $args 3] w]
  puts $f {%s}
  close $f
 }
}
if {[catch {source {%s}} message]} {puts stderr $message; exit 1}
''' % (path, env, PORTS, ROOT / 'physical/common_flow/ot_pin_regs.tcl')
    return subprocess.run(['tclsh'], input=script, text=True, capture_output=True)


SPEC = dict(top='example', clock_port='ck', reset_ports=['rst_n'], pin_regs=dict(enable=True),
            reset_landing=dict(enable=True, stages=2))


class Wrapper(unittest.TestCase):
    def test_pin_regs_plus_landing(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            r = generate(path)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('OT_RST_LAND example: 1 reset port(s) landed in 2 registered stage(s)', r.stdout)
            w = (path / 'ot_pin_regs_wrapper.v').read_text()
            self.assertIn('always @(posedge ck) rst_n__ot_rl0 <= rst_n;', w)
            self.assertIn('always @(posedge ck) rst_n__ot_rl1 <= rst_n__ot_rl0;', w)
            self.assertIn('.rst_n(rst_n__ot_rl1)', w)
            self.assertIn('(* keep *) reg [0:0] rst_n__ot_rl0;', w)
            self.assertIn('.d(d__ot_pr)', w)                       # data pins still registered
            self.assertIn('rst_n\tinput\t1\t0\treset', (path / 'ot_pin_regs.tsv').read_text())
            self.assertEqual((path / 'ot_rst_land.tsv').read_text().splitlines()[1], 'rst_n\t1\t2\tck')
            rep = PL.export(path / 'ot_pin_regs.tsv', path / 'ot_pin_regs_wrapper.v', 'example', 'a' * 40)
            roles = PL.validate_roles(rep, path / 'ot_pin_regs_wrapper.v', SPEC, lambda _: None)
            self.assertEqual(roles['reset_landing'], {'rst_n': 2})
            # a landed reset the spec did not ask for is not accepted as a reset role
            with self.assertRaisesRegex(ValueError, 'not direct'):
                PL.validate_roles(rep, path / 'ot_pin_regs_wrapper.v', dict(SPEC, reset_landing=None), lambda _: None)

    def test_landing_only_passes_data_through(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            r = generate(path, pin_regs=False, stages=3)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((path / 'ot_pin_regs.tsv').exists())
            self.assertFalse((path / 'ot_pin_regs_wrapper.v').exists())
            w = (path / 'ot_rst_land_wrapper.v').read_text()
            self.assertIn('(OT_RST_LAND=1)', w)
            self.assertIn('.d(d)', w)
            self.assertIn('.q(q)', w)
            self.assertIn('.rst_n(rst_n__ot_rl2)', w)
            self.assertNotIn('__ot_q', w)

    def test_without_landing_reset_stays_direct(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            self.assertEqual(generate(path, land=False).returncode, 0)
            w = (path / 'ot_pin_regs_wrapper.v').read_text()
            self.assertIn('.rst_n(rst_n)', w)
            self.assertNotIn('__ot_rl', w)
            self.assertFalse((path / 'ot_rst_land.tsv').exists())

    def test_bad_stage_count_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertNotEqual(generate(Path(td), stages=9).returncode, 0)


class KitOption(unittest.TestCase):
    def spec(self, **kw):
        s = dict(top='example', kind='tile', clock_port='ck', reset_ports=['rst_n'], route={})
        s.update(kw)
        return s

    def test_recipe3_default_on_with_resets(self):
        s = RT.apply_recipe(self.spec(), 3)
        self.assertEqual(s['reset_landing'], {'enable': True, 'stages': 2})
        self.assertNotIn('reset_landing', RT.apply_recipe(self.spec(reset_ports=[]), 3))
        c = RT.apply_recipe(self.spec(kind='cluster'), 3)                 # clusters too (kp4_dec)
        self.assertTrue(c['reset_landing']['enable'])

    def test_vars(self):
        s = self.spec(pin_regs={'enable': True}, reset_landing={'enable': True, 'stages': 2})
        self.assertEqual(RT.reset_landing_vars(s), ['--orfs-var OT_RST_LAND=1', '--orfs-var OT_RST_LAND_STAGES=2'])
        lo = self.spec(pin_regs={'enable': False, 'reason': 'RTL registers pins'}, reset_landing={'enable': True})
        v = RT.reset_landing_vars(lo)
        self.assertIn("--orfs-var OT_PIN_REGS_RESET_PORTS='rst_n'", v)
        self.assertTrue(any(x.startswith('--orfs-var OT_PIN_REGS_CLOCK=') for x in v))
        self.assertEqual(RT.reset_landing_vars(self.spec(reset_landing={'enable': False, 'reason': 'RTL rst_l0/rst_l1'})), [])

    def test_spec_errors(self):
        for bad in ({'enable': False}, {'enable': True, 'stages': 0}, 'yes'):
            with self.assertRaises(RT.SpecError):
                RT.reset_landing_plan(self.spec(reset_landing=bad))
        with self.assertRaises(RT.SpecError):
            RT.reset_landing_plan(self.spec(reset_ports=[], reset_landing={'enable': True}))


class GateRecord(unittest.TestCase):
    OUT = ('GATE_TB textbook_lint: INFO reset_landing {"max":2,"ports":[{"port":"rst_n","sinks":4,"flops":0,"macros":4}]}\n'
           'GATE_TB textbook_lint: REFUSE reset_landing: reset port rst_n: 4 sinks\n')

    def test_record_and_requirement(self):
        rec = PG.reset_landing_record(self.OUT)
        self.assertEqual(rec['over'], ['rst_n'])
        self.assertFalse(rec['ok'])
        ok, rows = SB.relaxed_rule_requirement(['reset_landing'], {}, {'reset_landing': rec})
        self.assertFalse(ok)
        ok, rows = SB.relaxed_rule_requirement(['reset_landing'], {}, {'kit': 'x'})        # predates the rule
        self.assertTrue(ok and rows[0]['predates'])
        landed = PG.reset_landing_record(self.OUT.replace('"sinks":4', '"sinks":1').split('\n')[0])
        self.assertTrue(SB.relaxed_rule_requirement(['reset_landing'], {}, {'reset_landing': landed})[0])
        waived = PG.reset_landing_record(self.OUT.replace('REFUSE reset_landing', 'WAIVED reset_landing'))
        self.assertTrue(waived['ok'] and waived['waived'])
        self.assertIsNone(PG.reset_landing_record('GATE_TB textbook_lint: PASS top cells 1'))

    def test_args_and_refuse_list(self):
        self.assertIn('reset_landing', PG.GATE_REFUSE)
        self.assertEqual(PG.reset_landing_args({}), '')
        self.assertEqual(PG.reset_landing_args({'reset_landing': {'enable': True}}), '')
        self.assertEqual(PG.reset_landing_args({'reset_landing': {'waive': 'CDC leaf'}}), ' --waive reset_landing')
        self.assertEqual(PG.reset_landing_args({'reset_landing': {'enable': False, 'reason': 'r', 'max_sinks': 4}}),
                         ' --set rst_land_max=4')
        self.assertEqual(PG.reset_landing_args({'reset_landing': {'max_sinks': 4}}), '')       # no reason: default
        self.assertTrue(re.search(r'reset_landing', PG.TEXTBOOK_FIX['reset_landing']))


if __name__ == '__main__':
    unittest.main()


class PlaceFollowsWrapper(unittest.TestCase):
    """ROOT 10-19 (S81-XG): pin_regs off + reset_landing on wraps the top (core instance u_ot_pr_core), so the spec's
    macro instance patterns must match the wrapped names; kits without a wrapper keep a byte-identical place.tcl."""
    BLOCKS = [dict(master='ram', inst='u_s.g_bank[0].u_mem', x=10, y=0, orient='R0'),
              dict(master='ram', inst='u_s.g_bank[1].u_mem', x=60, y=0, orient='MY')]

    def spec(self, **kw):
        s = dict(name='xg', top='example', kind='tile', clock_port='ck', reset_ports=['rst_n'], route={})
        s.update(kw)
        return s

    def run_place(self, tcl, names):
        objs = ''.join(f'proc i{k} {{args}} {{ switch [lindex $args 0] {{ getMaster {{return m}} getName {{return {{{n}}}}}'
                       f' default {{return}} }} }}\n' for k, n in enumerate(names))
        harness = ('namespace eval ord {}\nproc ord::get_db_block {} {return B}\nproc ord::get_db_tech {} {return T}\n'
                   'proc T {args} {return 1000}\nproc m {args} { switch [lindex $args 0] { isBlock {return 1} '
                   'getName {return ram} } }\n'
                   f'proc B {{args}} {{ return {{{" ".join(f"i{k}" for k in range(len(names)))}}} }}\n' + objs)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'place.tcl').write_text(tcl)
            harness += f'if {{[catch {{source {{{d}/place.tcl}}}} m]}} {{puts stderr $m; exit 1}}\nexit 0\n'
            return subprocess.run(['tclsh'], input=harness, capture_output=True, text=True, timeout=30)

    def test_landing_only_wrapper_matches_macros(self):
        s = self.spec(pin_regs={'enable': False, 'reason': 'RTL registers pins'}, reset_landing={'enable': True})
        self.assertTrue(RT.pin_wrapper(s))
        tcl = RT.gen_place(s, self.BLOCKS)
        wrapped = ['u_ot_pr_core.u_s.g_bank[1].u_mem', 'u_ot_pr_core.u_s.g_bank[0].u_mem']
        r = self.run_place(tcl, wrapped)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('REF_TILE place: u_ot_pr_core.u_s.g_bank[0].u_mem ram at 10 0 R0', r.stdout)
        self.assertIn('REF_TILE place: u_ot_pr_core.u_s.g_bank[1].u_mem ram at 60 0 MY', r.stdout)
        self.assertEqual(self.run_place(tcl, ['u_s.g_bank[0].u_mem', 'u_s.g_bank[1].u_mem']).returncode, 0)

    def test_pre_fix_place_fails_on_wrapped_names(self):
        s = self.spec(pin_regs={'enable': False, 'reason': 'RTL registers pins'}, reset_landing={'enable': True})
        old = RT.gen_place(self.spec(pin_regs={'enable': False, 'reason': 'x'},
                                     reset_landing={'enable': False, 'reason': 'RTL lands'}), self.BLOCKS)
        r = self.run_place(old, ['u_ot_pr_core.u_s.g_bank[0].u_mem', 'u_ot_pr_core.u_s.g_bank[1].u_mem'])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('no unplaced instance of ram', r.stderr + r.stdout)
        self.assertNotEqual(old, RT.gen_place(s, self.BLOCKS))

    def test_no_wrapper_byte_identical(self):
        s = self.spec(pin_regs={'enable': False, 'reason': 'x'}, reset_landing={'enable': False, 'reason': 'RTL lands'})
        self.assertFalse(RT.pin_wrapper(s))
        self.assertNotIn('ot_ref_wrapped_match', RT.gen_place(s, self.BLOCKS))
        on = self.spec(pin_regs={'enable': True}, reset_landing={'enable': True})
        self.assertNotIn('ot_ref_wrapped_match', RT.gen_place(on, [dict(b, inst='') for b in self.BLOCKS]))
