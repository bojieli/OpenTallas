"""Execute the real runner's CTS/GRT tail with synthetic external tools."""
import ast
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def runner(text):
    return next(ast.literal_eval(n.value) for n in ast.parse(text).body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'RUN_KIT' for t in n.targets))


class GrtGoalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.new = runner((ROOT / 'tools/die_plan/gen_phys.py').read_text())
        cls.old = runner(subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                                  '66d55c026ad:tools/die_plan/gen_phys.py'], text=True))

    def execute(self, source, goal, margin='', fail_hold=False, fail_policy=False, fail_pg=False):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td);k = d / 'kit';b = d / 'bin';b.mkdir();k.mkdir()
            result = k / 'run/results/asap7/test/base';result.mkdir(parents=True)
            for n in ['4_cts.odb', '4_cts.sdc']:(result / n).write_text('checkpoint')
            (k / 'config.mk').write_text('export OT_PREGRT_FF_HOLD = 1\nexport OT_POSTCTS_BAND_GATE = 1\n')
            (b / 'make').write_text('''#!/bin/bash
for a in "$@"; do
 case "$a" in
 print-OT_HOLD_FF_MARGIN) [ -z "$MARGIN" ] || echo "OT_HOLD_FF_MARGIN = $MARGIN"; exit 0;;
 print-BC_LIB_FILES) echo 'BC_LIB_FILES = fixture.lib'; exit 0;;
 print-TC_LIB_FILES) echo 'TC_LIB_FILES = fixture_tt.lib'; exit 0;;
 esac
done
printf 'make %s\\n' "$*" >> "$TRACE"
for a in "$@"; do case "$a" in grt) touch "$RESULTS/5_1_grt.odb";; route) touch "$RESULTS/5_route.odb";; do-finish) touch "$RESULTS/6_final.odb";; esac; done
''')
            (b / 'openroad').write_text('''#!/bin/bash
printf 'openroad %s\\n' "${*: -1}" >> "$TRACE"
case "$*" in
 *hold_gate.tcl*) if [ "$FAIL_HOLD" = 1 ]; then echo 'OT_HOLD_GATE FAIL';exit 1;else echo 'OT_HOLD_GATE PASS';fi;;
 *postcts_gate.tcl*) echo 'OT_POSTCTS_GATE PASS';;
 *pregrt_ff_hold.tcl*) [ "${FAIL_PG:-0}" != 1 ] || exit 139;;
esac
exit 0
''')
            (b / 'python3').write_text('''#!/bin/bash
printf 'python %s\\n' "$*" >> "$TRACE"
case "$*" in *legacy_gate.py*) [ "$FAIL_POLICY" != 1 ] || exit 1;; esac
exit 0
''')
            for p in b.iterdir():p.chmod(0o755)
            start = source.index('  if [ \\$rc = 0 ] && { [ $GOAL = cts ]')
            end = source.index(' > "$K/run_$GOAL.log"', start)
            body = source[start:end]
            assert body.endswith('exit \\$rc"')
            body = body[:-1].replace('\\\n', '\n').replace('\\$', '$').replace('\\"', '"')
            body = body.replace('/work', str(k)).replace('chown -R $HUID:$HGID', 'true')
            trace = d / 'trace'
            env = dict(os.environ, PATH=str(b) + ':' + os.environ['PATH'], TRACE=str(trace),
                       RESULTS=str(result), GOAL=goal, MARGIN=margin, FAIL_HOLD=str(int(fail_hold)),
                       FAIL_POLICY=str(int(fail_policy)), FAIL_PG=str(int(fail_pg)), NAME='fixture', HUID=str(os.getuid()), HGID=str(os.getgid()))
            p = subprocess.run(['bash', '-c', 'set -uo pipefail; rc=0; M=make; ' + body], env=env,
                               text=True, capture_output=True)
            lines = trace.read_text().replace(str(k), 'KIT').splitlines() if trace.exists() else []
            return p.returncode, lines, p.stderr

    def test_existing_goal_execution_is_unchanged(self):
        for goal in ['cts', 'route', 'finish']:
            for margin in ['', '0']:
                with self.subTest(goal=goal, margin=margin):
                    old = self.execute(self.old, goal, margin)
                    new = self.execute(self.new, goal, margin)
                    self.assertEqual(new[:2], old[:2])
                    self.assertEqual(new[0], 0, new)

    def test_grt_runs_standard_gates_without_detail_route(self):
        for margin in ['', '0']:
            with self.subTest(margin=margin):
                rc, lines, err = self.execute(self.new, 'grt', margin)
                self.assertEqual(rc, 0, (lines, err))
                makes = [x for x in lines if x.startswith('make ')]
                self.assertEqual(sum('grt' in x.split() for x in makes), 1, lines)
                self.assertTrue(any('hold_gate.tcl' in x for x in lines), lines)
                self.assertTrue(any('pregrt_ff_hold.tcl' in x for x in lines), lines)
                self.assertTrue(any('legacy_gate.py' in x and x.endswith('grt') for x in lines), lines)
                self.assertFalse(any(x in ' '.join(makes) for x in ['route', 'do-finish', 'do-generate_abstract']))
                self.assertFalse(any('pin_audit.py' in x for x in lines))

    def test_hold_build_failure_is_advisory(self):
        # R-CLOCK (HOLD-TAP-1 11-13): a crashed pre-GRT hold build keeps 4_cts.odb and the kit goes on to GRT
        rc, lines, err = self.execute(self.new, 'grt', fail_pg=True)
        self.assertEqual(rc, 0, (lines, err))
        self.assertTrue(any('pregrt_ff_hold.tcl' in x for x in lines), lines)
        self.assertEqual(sum('grt' in x.split() for x in lines if x.startswith('make ')), 1, lines)

    def test_structural_failure_stops_before_grt(self):
        rc, lines, _ = self.execute(self.new, 'grt', fail_hold=True)
        self.assertEqual(rc, 4)
        self.assertFalse(any(x == 'make grt' for x in lines), lines)

    def test_grt_policy_failure_stops_with_existing_code(self):
        rc, lines, _ = self.execute(self.new, 'grt', fail_policy=True)
        self.assertEqual(rc, 6)
        self.assertTrue(any('legacy_gate.py' in x for x in lines))
        self.assertFalse(any('make route' in x or 'do-finish' in x for x in lines))

    def test_resumed_grt_goal_is_accepted_without_changing_prior_steps(self):
        import json
        with tempfile.TemporaryDirectory() as td:
            k = Path(td)
            (k / 'resume.json').write_text(json.dumps(dict(start='grt', reused_steps=['synth', 'floorplan', 'place', 'cts'],
                source=dict(host='fixture', kit='source'))))
            def entry(text):
                block = text[text.index('RS=0; KWRS_M='):text.index('# KW-FIX-5 11-04')]
                return subprocess.run(['bash', '-c', 'set -uo pipefail; K="$1"; GOAL=grt; ' + block,
                                       'fixture', str(k)], text=True, capture_output=True)
            old, new = entry(self.old), entry(self.new)
            self.assertEqual(old.returncode, 10)
            self.assertEqual(new.returncode, 0, new.stderr)
            self.assertIn('start step 4', new.stdout)
            self.assertTrue((k / 'kwrs_make.sh').is_file())


if __name__ == '__main__':unittest.main()
