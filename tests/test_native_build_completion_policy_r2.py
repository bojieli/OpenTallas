import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import native_build_completion_policy_r2 as P


class Policy(unittest.TestCase):
    def setUp(self):
        # Test inputs only; no experiment admission or resource claim.
        self.model = dict(scope='native_build', elapsed_time_limit=None,
                          file_size_limit='unlimited', cpu_time_limit=None, per_process_address_space_limit=None,
                          retain_incremental_objects=True, memory_bytes=96 * 2**30,
                          swap_bytes=0, pids=96, workers=24, affinity=list(range(8, 32)),
                          output_bytes=32 * 2**30, host_disk_reserve=32 * 2**30,
                          host_memory_reserve=32 * 2**30,
                          admission_evidence=dict(host_snapshot_sha256='test-snapshot',
                                                  source_inventory_sha256='test-inventory',
                                                  capacity_reservation_basis='test-only'))

    def service(self):
        return dict(RuntimeMaxUSec='infinity', LimitFSIZE='infinity',
                    LimitFSIZESoft='infinity', LimitAS='infinity', LimitASSoft='infinity',
                    LimitCPU='infinity', LimitCPUSoft='infinity',
                    MemoryMax=str(self.model['memory_bytes']), MemorySwapMax='0', TasksMax='96',
                    CPUAffinity='8-31')

    def test_future_properties_preserve_resources_and_remove_time_file_AS_caps(self):
        p = P.future_service_properties(self.model)
        self.assertEqual(p['RuntimeMaxSec'], 'infinity')
        self.assertEqual(p['LimitFSIZE'], 'infinity')
        self.assertEqual(p['LimitAS'], 'infinity')
        self.assertEqual(p['MemoryMax'], str(96 * 2**30))
        self.assertEqual(p['TasksMax'], '96')
        self.assertEqual(p['CPUAffinity'], ' '.join(map(str, range(8, 32))))

    def test_missing_inventory_or_measurement_refused(self):
        for key in self.model['admission_evidence']:
            m = copy.deepcopy(self.model)
            del m['admission_evidence'][key]
            with self.subTest(key=key), self.assertRaises(ValueError): P.validate_model(m)

    def test_old_deadline_AS_and_nonretention_models_refused(self):
        for key, value in [('elapsed_time_limit', 900), ('cpu_time_limit', 900), ('CXX_AS', 3 * 2**30),
                           ('link_AS', 8 * 2**30), ('per_process_address_space_limit', 1),
                           ('retain_incremental_objects', False), ('scope', 'simulation')]:
            m = copy.deepcopy(self.model); m[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): P.validate_model(m)

    def test_live_validation_refuses_hidden_deadlines_or_inherited_caps(self):
        P.validate_execution(self.service(), self.model, process_fsize=(-1, -1), process_as=(-1, -1),
                             process_affinity=self.model['affinity'])
        for kwargs in [dict(subprocess_timeout=900), dict(process_as=(3 * 2**30, -1)),
                       dict(process_fsize=(1, -1)), dict(process_cpu=(900, -1))]:
            args = dict(process_fsize=(-1, -1), process_as=(-1, -1),
                        process_affinity=self.model['affinity']); args.update(kwargs)
            with self.subTest(args=args), self.assertRaises(ValueError):
                P.validate_execution(self.service(), self.model, **args)
        for key, value in [('RuntimeMaxUSec', '900s'), ('LimitCPUSoft', '900'), ('LimitASSoft', '3221225472'),
                           ('MemoryMax', '1'), ('MemorySwapMax', '1'), ('TasksMax', '48'),
                           ('CPUAffinity', '0-31')]:
            s = self.service(); s[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                P.validate_execution(s, self.model, process_fsize=(-1, -1), process_as=(-1, -1),
                                     process_affinity=self.model['affinity'])

    def test_explicit_wrapper_negative_controls(self):
        for argv in [['timeout', '900', 'make'], ['/usr/bin/timeout', '5h', 'make'],
                     ['prlimit', '--as=3221225472', 'g++'], ['prlimit', '--as', '8', 'ld'],
                     ['systemd-run', '-p', 'RuntimeMaxSec=900s', 'make'],
                     ['systemd-run', '-p', 'LimitAS=8G', 'make'],
                     ['ulimit', '-v', '3145728'], ['ulimit', '-t', '900'],
                     ['prlimit', '--cpu=900', 'make'], ['prlimit', '--cpu', '900', 'make'],
                     ['docker', '--ulimit', 'cpu=900:900', 'image', 'make'],
                     ['docker', '--ulimit', 'as=3221225472:3221225472', 'image', 'make'],
                     ['prlimit', '--fsize=512', 'g++']]:
            with self.subTest(argv=argv), self.assertRaises(ValueError): P.validate_native_argv(argv)
        P.validate_native_argv(['prlimit', '--as=unlimited:unlimited', '--fsize=unlimited:unlimited', 'g++'])
        P.validate_native_argv(['g++', '-o', 'timeout', 'input.cc'])

    def test_actual_capacity_and_aggregate_disk_failures_still_refused(self):
        good = dict(available_memory=160 * 2**30, free_disk=128 * 2**30,
                    sampled_output=12 * 2**30, accounted_existing_output=12 * 2**30)
        r = P.validate_admission_headroom(self.model, **good)
        self.assertIn('sampled', r['enforcement'])
        for key, value in [('available_memory', 127 * 2**30), ('free_disk', 51 * 2**30),
                           ('sampled_output', 33 * 2**30)]:
            args = dict(good); args[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                P.validate_admission_headroom(self.model, **args)


if __name__ == '__main__':
    unittest.main()
