"""Portable source/probe contract tests. Synthetic coupons remain component-only."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
FIX = HERE / 'head37_witness_fixtures'


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P = load('prepare_head37_tt_witness_source')
E = load('head37_observation_events')
MASTER = 'qfd_tt_ctlm_dv_wtn_head37_prod_0123456789abcdef_e8'


class TTWitnessSourceTests(unittest.TestCase):
    def test_default_body_and_hierarchy_preserved(self):
        before = (FIX / 'head37_tt_parent_fragment.sv').read_text()
        after = P.rewrite_parent(before, MASTER)
        begin = '    generate if (F16WTN != 0) begin : g_wtn\n'
        newbegin = '    generate if (F16WTN != 0 && HEAD_STAGE37 == 0) begin : g_wtn\n'
        end = '    end else begin : g_no_wtn\n'
        self.assertEqual(before.split(begin)[1].split(end)[0],
                         after.split(newbegin)[1].split('    end else if')[0])
        self.assertEqual(before[:before.index(begin)], after[:after.index(newbegin)])
        self.assertEqual(before[before.index(end):], after[after.index(end):])
        self.assertIn('begin : g_wtn_head37\n        ' + MASTER + ' u_wtn', after)
        self.assertRaises(ValueError, P.rewrite_parent, before.replace('HEAD_STAGE37 = 0', 'HEAD_STAGE37 = 1'), MASTER)

    def test_real_component_receipt_refused_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'output'
            with self.assertRaisesRegex(ValueError, 'production witness receipt required'):
                P.prepare(FIX / 'head37_tt_parent_fragment.sv', FIX / 'component_receipt.json',
                          FIX / 'component_profile.json', Path('NOT_READ'), Path('NOT_READ'), out)
            self.assertFalse(out.exists())

    def test_probe_bootstrap_does_not_need_profile_or_drive_inputs(self):
        before = (FIX / 'head37_tt_parent_fragment.sv').read_text()
        after = P.trace_parent(before)
        self.assertIn('OT_HEAD37_WITNESS_TRACE', after)
        self.assertIn('.start({u_start, 2\'(u_user), u_stage, u_tokid}), .obs(f16_obs)', after)
        self.assertIn('generate if (F16WTN != 0) begin : g_wtn', after)
        self.assertRaises(ValueError, P.trace_parent, after)

    def test_48_event_extraction_retains_component_scope_and_rejects_bad_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'synthetic_source.txt'
            source.write_text('TEST_ONLY synthetic contract coupon\n')
            rows = ['HEAD37_TRACE_V1 RECEIVER_FACE_PRE_NBA']
            for u in range(4):
                start = 100 * u
                rows.append(f'HEAD37_START {start} {u} 37 {16+u}')
                for sl in range(12):
                    rows.append(f'HEAD37_OBS {start+10+sl} {u} {sl} {16+128*u} 37 {16+u}')
            trace = root / 'synthetic.trace'
            trace.write_text('\n'.join(rows) + '\n')
            receipt = root / 'execution.json'
            r = dict(schema='opentallas.qwen.head37-witness-execution.v1',
                     status='PASS_SOURCE_SELECTED_COMMAND_TRANSPORT_REPLAY',
                     trace_sha256=E.sha(trace), component_only=True, rank=0,
                     selected_source_files={name: dict(path=source.name, sha256=E.sha(source))
                                            for name in ['calendar', 'tt_parent', 'observer_transport']},
                     command_edge_authority='TEST synthetic coupon only',
                     context_start_authority='TEST synthetic coupon only')
            receipt.write_text(json.dumps(r))
            output = root / 'events.json'
            result = E.extract(trace, receipt, output)
            self.assertTrue(result['component_only'])
            self.assertEqual(result['status'], 'COMPONENT_SOURCE_SELECTED_EXECUTION_DATES')
            self.assertTrue(result['unresolved'])
            self.assertEqual(len(result['events']), 48)
            self.assertEqual(result['events'][2]['pidx'], 272)
            for name in ['partial', 'duplicate', 'wrong_pc', 'source_drift']:
                with self.subTest(name=name):
                    content = trace.read_text()
                    if name == 'partial': content = '\n'.join(content.splitlines()[:-1]) + '\n'
                    if name == 'duplicate': content += content.splitlines()[-1] + '\n'
                    if name == 'wrong_pc': content = content.replace('0 0 16 37 16', '0 0 17 37 16', 1)
                    bad = root / (name + '.trace')
                    bad.write_text(content)
                    r['trace_sha256'] = E.sha(bad)
                    receipt.write_text(json.dumps(r))
                    if name == 'source_drift': source.write_text('changed selected source\n')
                    self.assertRaises(ValueError, E.extract, bad, receipt, root / (name + '.json'))
            with self.assertRaisesRegex(ValueError, 'never overwritten'):
                E.extract(trace, receipt, output)

    @unittest.skipUnless(shutil.which('iverilog') and shutil.which('vvp'), 'iverilog/vvp unavailable')
    def test_passive_probe_packing_and_existing_trace_refusal(self):
        tb = '''module tb;
reg ck=0;always #5 ck=~ck;
reg rst_n=0;reg[24:0]start=0;reg[37:0]obs=0;
qfd_head37_witness_trace d(ck,rst_n,start,obs);
initial begin #2;rst_n=1;start={1'b1,2'd2,6'd37,16'd9};
#10;start=0;obs={1'b1,2'd2,4'd3,9'd272,6'd37,16'd9};
#10;obs=0;#10;$finish;end endmodule\n'''
        probe = HERE.parents[1] / 'rtl/test/qwen_dv/qfd_head37_witness_trace.sv'
        if not probe.is_file():
            probe = HERE / 'qfd_head37_witness_trace.sv'  # standalone source package
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'tb.sv').write_text(tb)
            subprocess.run(['iverilog', '-g2012', '-s', 'tb', '-o', str(root / 'sim'),
                            str(probe), str(root / 'tb.sv')], check=True, capture_output=True)
            command = ['vvp', str(root / 'sim'), '+HEAD37_WITNESS_TRACE=' + str(root / 'actual.trace')]
            subprocess.run(command, check=True, capture_output=True)
            original = (root / 'actual.trace').read_text()
            self.assertEqual(original.splitlines(), ['HEAD37_TRACE_V1 RECEIVER_FACE_PRE_NBA',
                                                     'HEAD37_START 0 2 37 9',
                                                     'HEAD37_OBS 1 2 3 272 37 9'])
            refused = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn('existing actual HEAD37 witness trace refused', refused.stdout)
            self.assertEqual((root / 'actual.trace').read_text(), original)


if __name__ == '__main__':
    unittest.main()
