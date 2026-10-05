import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import pve1_odb_endpoint_audit as audit
import pve1_odb_stage_driver as driver

SDC = (driver.PLAN_DIR / 'new_source_constraint.sdc').read_text()
FINAL_SDC = SDC + 'set_propagated_clock [all_clocks]\n'


def rows():
    return [('odb_port', p) for p in ('clk', 'rst_n', 'x', 'y')] + [
        ('odb_pin', 'reg/D'), ('odb_pin', 'reg/CLK'),
        ('input', 'clk'), ('input', 'rst_n'), ('input', 'x'), ('output', 'y'),
        ('clock_pin', 'reg/CLK', 'core_clk'),
        ('required_endpoint', 'reg/D'), ('required_endpoint', 'y'),
        ('endpoint', 'reg/D'), ('endpoint', 'y'),
        ('check_arc', 'reg/D', 'setup', '0'), ('check_arc', 'reg/D', 'hold', '0'),
        ('master_pin', 'DFF', 'D', 'WC', '1'), ('master_pin', 'DFF', 'D', 'BC', '1'),
        ('startpoint_pair', 'x', 'reg/D'), ('startpoint_pair', 'reg/Q', 'y'),
        ('timing', 'reg/D', 'WC', 'max', '4', '1', '0'),
        ('timing', 'reg/D', 'BC', 'min', '2', '1', '0'),
        ('timing', 'y', 'WC', 'max', '1', '1', '0'),
        ('timing', 'y', 'BC', 'min', '0', '1', '0'),
        ('check_setup', '1'), ('complete', '1')]


class EndpointAuditTests(unittest.TestCase):
    def test_exact_source_contract_and_complete_native_rows(self):
        result = audit.audit(rows(), FINAL_SDC, final=True)
        self.assertEqual(result['endpoint_count'], 2)
        self.assertFalse(result['physical_signoff'])

    def test_canonical_numeric_format_and_pin_load_supported(self):
        text = SDC.replace('set_max_fanout 32', 'set_max_fanout 32.0000').replace('set_load 3.898', 'set_load -pin_load 3.8980')
        audit.audit(rows(), text)

    def test_bus_port_literal_coverage(self):
        audit.replay_sdc(SDC, {'clk', 'rst_n', 'x[0]', 'x[1]'}, {'y[0]', 'y[1]'})

    def test_relaxation_or_broadened_exception_refused(self):
        for old, new in [('1111', '1200'), ('-setup 60', '-setup 0'),
                         ('get_ports rst_n', 'all_inputs'), ('* 0]', '* 0.1]')]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                audit.audit(rows(), SDC.replace(old, new))

    def test_safe_replay_denies_file_and_process_access(self):
        for command in ['exec true', 'open /tmp/unauthorized w', 'set_disable_timing [all_inputs]']:
            with self.subTest(command=command), self.assertRaises(ValueError):
                audit.audit(rows(), SDC + command + '\n')

    def test_missing_or_duplicate_endpoint_rows_refused(self):
        for data in [rows()[:-1], [r for r in rows() if r[:3] != ('timing', 'y', 'BC')], rows() + [('endpoint', 'y')]]:
            with self.assertRaises(ValueError): audit.audit(data, SDC)

    def test_no_generic_nonzero_or_missing_slack_acceptance(self):
        for slack in ('Inf', 'NaN', '1e30'):
            data = [r[:4] + (slack,) + r[5:] if r[0] == 'timing' else r for r in rows()]
            with self.subTest(slack=slack), self.assertRaises(ValueError):
                audit.audit(data, SDC)

    def test_negative_slack_allowed_only_as_intermediate_evidence(self):
        data = [r[:4] + ('-1',) + r[5:] if r[0] == 'timing' else r for r in rows()]
        self.assertFalse(audit.audit(data, SDC)['physical_signoff'])
        with self.assertRaisesRegex(ValueError, 'violation'):
            audit.audit(data, FINAL_SDC, final=True)

    def test_mixed_reset_and_functional_endpoint_not_waived(self):
        data = rows() + [('startpoint_pair', 'rst_n', 'reg/D'), ('reset_reachable', 'rst_n', 'reg/D')]
        data = [r[:4] + ('EXCEPTED_RESET_ONLY', '1', '1') if r[:2] == ('timing', 'reg/D') else r for r in data]
        with self.assertRaisesRegex(ValueError, 'waive functional'):
            audit.audit(data, SDC)

    def test_proven_reset_only_non_graph_endpoint_is_explicit_exception(self):
        data = rows() + [('odb_pin', 'reg/RN'), ('required_endpoint', 'reg/RN'),
            ('non_graph_endpoint', 'reg/RN'), ('startpoint_pair', 'rst_n', 'reg/RN'),
            ('reset_reachable', 'rst_n', 'reg/RN'),
            ('timing', 'reg/RN', 'WC', 'max', 'EXCEPTED_RESET_ONLY', '0', '1'),
            ('timing', 'reg/RN', 'BC', 'min', 'EXCEPTED_RESET_ONLY', '0', '1')]
        self.assertEqual(audit.audit(data, FINAL_SDC, final=True)['reset_only_endpoints'], 1)

    def test_terminal_ideal_clock_refused(self):
        with self.assertRaisesRegex(ValueError, 'propagated clock'):
            audit.audit(rows(), SDC, final=True)

    def test_disabled_checks_and_missing_macro_views_refused(self):
        for added in [('disabled_check', 'reg check'), ('macro', 'memory0'), ('master_pin', 'OTHER', 'D', 'WC', '0')]:
            with self.subTest(added=added), self.assertRaises(ValueError):
                audit.audit(rows() + [added], SDC)

    def test_odb_sta_identity_mismatch_refused(self):
        data = [r for r in rows() if r != ('odb_pin', 'reg/D')]
        with self.assertRaisesRegex(ValueError, 'missing in ODB'):
            audit.audit(data, SDC)

    def test_disabled_arc_requires_native_constant_proof(self):
        data = rows() + [('disabled_arc', 'tie/Y', 'u/A', 'combinational', '0', '0', '1')]
        with self.assertRaisesRegex(ValueError, 'unexplained disabled'):
            audit.audit(data, SDC)
        audit.audit(data + [('disabled_constant_pin', 'tie/Y', 'u/A', 'u/A')], SDC)

    def test_constraint_disabled_arc_cannot_hide_behind_constant(self):
        data = rows() + [('disabled_arc', 'u/A', 'u/Y', 'combinational', '1', '0', '1'),
                         ('disabled_constant_pin', 'u/A', 'u/Y', 'u/A')]
        with self.assertRaisesRegex(ValueError, 'extra timing disable'):
            audit.audit(data, SDC)


class StageDriverTests(unittest.TestCase):
    def test_default_off_and_terminal_missing_refuse_before_launch(self):
        with patch.object(driver, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'default off'): driver.main([])
            with self.assertRaisesRegex(ValueError, 'complete terminal'):
                driver.main(['--run-admitted-new-source-constraints'])
            run.assert_not_called()

    def test_exact_producer_terminal_refuses_old_timeout(self):
        plan, _ = driver.inputs()
        with self.assertRaisesRegex(ValueError, 'successful terminal'):
            driver.admission(plan, {'exit_code': 0, 'status': 'error'}, {}, {}, '/missing/3_3_place_gp.odb')

    def test_later_stage_knobs_and_odb_sequence(self):
        plan, deps = driver.inputs()
        self.assertEqual(plan['model']['added_cycles'], 0)
        for k, v in driver.KNOBS.items(): self.assertEqual(deps['environment'][k], v)
        self.assertEqual([s[0] for s in driver.STAGES], ['resize', 'detail_place', 'cts', 'global_route', 'detail_route', 'fillcell', 'density_fill', 'final_report'])
        for stage in driver.STAGES:
            text = driver.entrypoint(stage, deps)
            self.assertLess(text.index('load_design '), text.index('/' + stage[0] + '.tcl'))
            self.assertNotIn('2_floorplan.sdc', text)

    def test_prepare_no_native_process_and_existing_bundle_preserved(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(driver, 'run') as run:
            work = Path(tmp) / 'review'
            driver.prepare(work)
            self.assertFalse(json.loads((work / 'preparation.json').read_text())['native_api_verified'])
            self.assertIn('initial.rows', (work / 'prepared/initial.tcl').read_text())
            before = (work / 'preparation.json').read_bytes()
            with self.assertRaises(FileExistsError): driver.prepare(work)
            self.assertEqual(before, (work / 'preparation.json').read_bytes())
            run.assert_not_called()

    def test_native_tcl_is_complete_script(self):
        import tkinter
        text = (ROOT / 'tools/pve1_odb_endpoint_audit.tcl').read_text()
        self.assertTrue(tkinter.Tcl().call('info', 'complete', text))

    def test_run_streams_raw_log_without_timeout(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(driver.subprocess, 'run', return_value=subprocess.CompletedProcess([], 17)) as run:
            self.assertEqual(driver.run(['tool'], log=Path(tmp) / 'raw'), 17)
            self.assertIsNone(run.call_args.kwargs['timeout'])
            self.assertNotIn('capture_output', run.call_args.kwargs)
            self.assertTrue((Path(tmp) / 'raw.capacity.json').exists())

    def test_arbitrary_timeout_refused(self):
        with self.assertRaisesRegex(ValueError, 'caps forbidden'):
            driver.run(['tool'], log='/unused', timeout=1)

    def test_heavy_outputs_refuse_tmpfs_tmp_paths(self):
        with self.assertRaisesRegex(ValueError, 'persistent /home'):
            driver.persistent_output_path('/tmp/proposed-physical-work')
        self.assertEqual(driver.persistent_output_path('/home/ubuntu/future-physical-work'), Path('/home/ubuntu/future-physical-work'))

    def test_hooks_restored_from_exact_source_not_missing_archive_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / 'work'; (work / 'hooks').mkdir(parents=True)
            source = Path(tmp) / 'source'
            path = source / 'physical/abi3/v41x_karb_repair_buffer_cap.tcl'
            path.parent.mkdir(parents=True)
            path.write_bytes(subprocess.check_output(['git', 'show',
                driver.source_contract.SOURCE_COMMIT + ':physical/abi3/v41x_karb_repair_buffer_cap.tcl'], cwd=ROOT))
            _, deps = driver.inputs()
            driver.restore_hooks(work, source, deps)
            for key in ('PRE_CTS_TCL', 'PRE_GLOBAL_ROUTE_TCL'):
                restored = work / deps['environment'][key].removeprefix('/work/')
                self.assertEqual(driver.digest(restored), deps['files'][deps['environment'][key]]['sha256'])
            path.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'hook differs'):
                driver.restore_hooks(work, source, deps)

    def test_fresh_namespace_identity_verifier_checks_actual_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'script.tcl'; path.write_text('original')
            pins = Path(tmp) / 'dependencies.json'
            pins.write_text(json.dumps({str(path): {'sha256': driver.digest(path)}}))
            program = driver.verification_program().replace('/work/dependencies.json', str(pins))
            result = subprocess.run([sys.executable, '-c', program], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            path.write_text('changed')
            self.assertNotEqual(subprocess.run([sys.executable, '-c', program], capture_output=True).returncode, 0)


if __name__ == '__main__': unittest.main()
