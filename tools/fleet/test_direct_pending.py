import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('direct_pending', str(Path(__file__).with_name('ot-direct-pending')))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


class DirectPending(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.scope = self.root / 'job.scope'
        self.scope.mkdir()
        (self.scope / 'memory.current').write_text(str(2 * m.GB))
        (self.scope / 'cgroup.procs').write_text('42\n')
        self.proc = self.root / 'proc'
        (self.proc / '42').mkdir(parents=True)
        self.argv = ['docker', 'run', '--name', 'kit', '-v', '/kit:/work', 'image', 'bash', 'run.sh']
        (self.proc / '42' / 'cmdline').write_text('\0'.join(self.argv) + '\0')
        self.container = dict(Id='abc', Name='/kit', State=dict(Running=True),
                              Config=dict(Cmd=['bash', 'run.sh'], Image='image'), HostConfig=dict(Binds=['/kit:/work']))
        self.cg = self.root / 'system.slice' / 'docker-abc.scope'
        self.cg.mkdir(parents=True)
        (self.cg / 'memory.current').write_text(str(14 * m.GB))
        self.addCleanup(self.tmp.cleanup)

    def usage(self, containers=None, credited=None):
        return m.live_usage(self.scope, [self.container] if containers is None else containers,
                            set() if credited is None else credited, self.root, self.proc)

    def test_physical_plus_unused_counts_docker_once(self):
        used = self.usage()
        self.assertEqual(used, 16 * m.GB)
        self.assertEqual(m.unused_gb(32, used), 16)
        # 100 physical includes these 16; only the remaining 16 is added.
        self.assertEqual(100 + m.unused_gb(32, used), 116)

    def test_unknown_or_ambiguous_identity_never_credits_docker(self):
        self.assertEqual(self.usage([]), 2 * m.GB)
        self.assertEqual(self.usage([self.container, dict(self.container)]), 2 * m.GB)
        self.container['Name'] = '/other'
        self.assertEqual(self.usage(), 2 * m.GB)

    def test_stopped_container_or_vanished_client_gets_no_credit(self):
        self.container['State']['Running'] = False
        self.assertEqual(self.usage(), 2 * m.GB)
        self.container['State']['Running'] = True
        (self.proc / '42' / 'cmdline').unlink()
        self.assertEqual(self.usage(), 2 * m.GB)

    def test_same_container_is_not_credited_twice(self):
        credited = set()
        self.assertEqual(self.usage(credited=credited), 16 * m.GB)
        self.assertEqual(self.usage(credited=credited), 2 * m.GB)

    def test_live_read_over_stale_usage_file(self):
        (self.root / 'use.job').write_text('999')
        (self.cg / 'memory.current').write_text(str(3 * m.GB))
        self.assertEqual(self.usage(), 5 * m.GB)
        (self.cg / 'memory.current').unlink()
        self.assertEqual(self.usage(), 2 * m.GB)

    def test_fractional_remaining_rounded_up_and_never_negative(self):
        self.assertEqual(m.unused_gb(32, m.GB // 2), 32)
        self.assertEqual(m.unused_gb(32, 99 * m.GB), 0)

    def test_full_fresh_and_unknown_reservations(self):
        (self.root / 'direct.job').write_text('job 64')
        def run(*args):
            if args[0] == 'docker':
                return ''
            return 'ActiveState=inactive\nControlGroup=\n'
        with patch.object(m, 'run', run):
            self.assertEqual(m.pending(self.root), 64)
        with patch.object(m, 'run', side_effect=OSError('bus down')):
            self.assertEqual(m.pending(self.root), 64)

    def test_launcher_admits_on_real_memavailable_with_fresh_claims(self):
        # DIRECT_MEMAVAIL_1110 (COORD 11-10): --direct admits on real MemAvailable >= MEM + 32 GB.  An earlier direct
        # job's request is charged only while its claim is fresh (< DIRECT_FRESH_S, 300 s): after that its memory is
        # already in MemAvailable.  ot-heavy no longer subtracts ot-direct-pending's unused-request estimate.
        # Behaviour: test_ot_run_direct.py FreshOnly.
        script = Path(__file__).with_name('ot-heavy').read_text()
        self.assertNotIn('ot-direct-pending', script)
        self.assertIn("_avail=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo)", script)
        self.assertIn('_avail - _pend )) -ge $(( MEM + 32 ))', script)
        self.assertIn('[ $_age -lt "${DIRECT_FRESH_S:-300}" ] && _pend=$(( _pend + _m ))', script)
        self.assertIn('echo "$UNIT $MEM" > "$D/direct.$UNIT"', script)


if __name__ == '__main__':
    unittest.main()
