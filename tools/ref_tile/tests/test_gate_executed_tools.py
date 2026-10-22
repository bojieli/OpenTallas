"""ROOT8-CONSUMED (AGENT-QUEUE 10-20 08:52, owner 09:05 "no regates forced by unrelated tool changes"): at submit the
gate is bound only to the TOOL files (tools/**) the gate executed -- the closure over the gate-run seeds (kit directory,
spec sources, floorplan referenced, child/macro views, GATE_TOOLS and the shipped overlays) -- not to tool files staged
only because the job's source.extra_paths name a tools/ directory (route / bench inputs: pv_join P216, lane8, sh_lk,
sf7w carried tools/qwen_split etc., whose import closure swept ~390 unrelated tools/*.py into the recorded consumed set,
so any main tool commit forced a 1-4 h regate).
Negatives: a gate-executed tool, a module it imports, a tool a kit hook names, and a shipped overlay still refuse."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE), str(HERE.parent / 'closure_loop')]
import helper_overlay as HO
import pre_route_gate as PG
import source_binding as SB

OVL = 'tools/textbook_lint.py'
GATE_TOOL = 'tools/closure_loop/ck_insertion.py'          # in SB.GATE_TOOLS: the remote gate runs it
GATE_DEP = 'tools/closure_loop/ck_helper.py'              # imported by GATE_TOOL
HOOK_TOOL = 'tools/ref_tile/kit_hook_tool.sh'             # named by the kit hook
EXTRA_TOOL = 'tools/qwen_split/bench_lane.py'             # under the job's extra_paths (bench input only)
EXTRA_DEP = 'tools/uarch_model.py'                        # imported by EXTRA_TOOL only
RTL = 'rtl/physical/ot_lane.sv'
KIT = 'physical/ref_tile/qkd_lane_x'


class GateExecutedTools(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root, self.daemon = Path(self.tmp.name) / 'repo', Path(self.tmp.name) / 'daemon'
        for d in ('tools/closure_loop', 'tools/ref_tile', 'tools/qwen_split', 'rtl/physical', KIT):
            (self.root / d).mkdir(parents=True, exist_ok=True)
        (self.daemon / 'tools').mkdir(parents=True)
        self.git('init')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.com')
        self.spec = {'name': 'qkd_lane_x', 'top': 'ot_lane', 'kind': 'tile', 'sources': [RTL],
                     'macros': [], 'children': []}
        self.tip = self.commit({
            OVL: b'# lint v1\n', GATE_TOOL: b'import ck_helper\n', GATE_DEP: b'X = 1\n',
            HOOK_TOOL: b'echo hook v1\n', EXTRA_TOOL: b'import uarch_model\n', EXTRA_DEP: b'M = 1\n',
            RTL: b'module ot_lane; endmodule\n',
            f'{KIT}/spec.json': json.dumps(self.spec).encode(),
            f'{KIT}/pre_gpl.tcl': f'exec sh $::env(SRC)/{HOOK_TOOL}\n'.encode(),
            f'{KIT}/job.json': json.dumps({'source': {'extra_paths': ['tools/qwen_split']}}).encode()})
        (self.daemon / OVL).write_bytes(b'# lint v1\n')
        self.stack = [patch.object(PG, 'ROOT', self.root), patch.object(PG, 'DAEMON_TREE', self.daemon),
                      patch.object(PG, 'SHIP_HELPERS', (OVL,)), patch.object(HO, 'HELPERS', ('../textbook_lint.py',))]
        for p in self.stack:
            p.start()
        plan, payloads = HO.capture_plan(self.daemon, self.root)
        data = PG.ship_tar({'tools', 'rtl', 'physical'}, payloads, {f['path']: f['mode'] for f in plan['files']})
        self.binding = SB.snapshot(data, self.root, self.tip, self.daemon, None, (OVL,))
        self.binding.update(route_overlay_plan=plan, remote_archive_verified=True)
        self.binding['consumed'] = PG.gate_consumed(data, self.root / KIT, self.spec, [], self.binding['files'])
        (self.root / KIT / 'gate_result.json').write_text(json.dumps(
            {'source_binding': self.binding, 'clock': {'max_root_sinks': 9000, 'verdict': 'PASS'}}))

    def tearDown(self):
        for p in reversed(self.stack):
            p.stop()
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.DEVNULL).decode().strip()

    def commit(self, files, rm=()):
        for rel, data in files.items():
            (self.root / rel).write_bytes(data)
        if files:
            self.git('add', *files)
        if rm:
            self.git('rm', '-q', *rm)
        self.git('commit', '-m', 'update')
        return self.git('rev-parse', 'HEAD')

    def evidence(self, commit):
        g = PG.Gate()
        PG.check_clock_evidence(g, self.root / KIT, source_commit=commit)
        return [i for i in g.items if i['check'] == 'source_binding']

    def test_recorded_consumed_set_sweeps_in_extra_path_tools(self):
        # the gate-time record is unchanged (immutable): it still lists the extra_paths tools and their imports
        used = set(self.binding['consumed']['paths'])
        self.assertTrue({EXTRA_TOOL, EXTRA_DEP, GATE_TOOL, GATE_DEP, HOOK_TOOL, OVL} <= used, used)
        ex = PG.gate_executed_tools(self.binding, self.root / KIT)
        self.assertEqual(ex & {EXTRA_TOOL, EXTRA_DEP}, set())
        self.assertTrue({GATE_TOOL, GATE_DEP, HOOK_TOOL, OVL} <= ex, ex)

    def test_unrelated_tool_change_accepts(self):
        later = self.commit({EXTRA_DEP: b'M = 2\n', EXTRA_TOOL: b'import uarch_model  # v2\n'})
        self.assertFalse(SB.validate(self.binding, self.root, self.daemon, later)[0])   # the recorded set alone refused
        sb = self.evidence(later)
        self.assertNotIn('FAIL', [i['severity'] for i in sb], sb)
        self.assertTrue(any(EXTRA_DEP in i['message'] and 'not refused' in i['message'] for i in sb), sb)

    def test_unrelated_tool_deleted_is_not_blob_unknown(self):
        later = self.commit({}, rm=[EXTRA_DEP])
        sb = self.evidence(later)
        self.assertNotIn('FAIL', [i['severity'] for i in sb], sb)
        self.assertFalse(any('blob unknown' in i['message'] for i in sb), sb)

    def assert_refused(self, rel, data):
        later = self.commit({rel: data, EXTRA_DEP: b'M = 3\n'})
        fail = [i for i in self.evidence(later) if i['severity'] == 'FAIL']
        self.assertTrue(fail and rel in fail[0]['message'], fail)

    def test_gate_executed_tool_change_refuses(self):
        self.assert_refused(GATE_TOOL, b'import ck_helper\nY = 2\n')

    def test_imported_module_of_gate_tool_change_refuses(self):
        self.assert_refused(GATE_DEP, b'X = 2\n')

    def test_kit_hook_named_tool_change_refuses(self):
        self.assert_refused(HOOK_TOOL, b'echo hook v2\n')

    def test_consumed_tool_deleted_refuses(self):
        later = self.commit({}, rm=[GATE_DEP])
        fail = [i for i in self.evidence(later) if i['severity'] == 'FAIL']
        self.assertTrue(fail and GATE_DEP in fail[0]['message'], fail)

    def test_shipped_overlay_change_refuses(self):
        (self.daemon / OVL).write_bytes(b'# lint v2\n')
        self.commit({OVL: b'# lint v2\n'})
        fail = [i for i in self.evidence(self.tip) if i['severity'] == 'FAIL']
        self.assertTrue(fail and OVL in fail[0]['message'], fail)

    def test_narrowed_record_is_self_consistent(self):
        b = PG.narrow_consumed_tools(self.binding, PG.gate_executed_tools(self.binding, self.root / KIT))
        c = b['consumed']
        self.assertEqual(c['digest'], SB.canonical_digest(c['paths']))
        self.assertEqual(c['count'], len(c['paths']))
        self.assertNotIn(EXTRA_DEP, c['paths'])
        self.assertIn(RTL, c['paths'])
        self.assertEqual(c['tools_not_executed'], 2)
        self.assertIs(PG.narrow_consumed_tools(self.binding, None), self.binding)


if __name__ == '__main__':
    unittest.main()
