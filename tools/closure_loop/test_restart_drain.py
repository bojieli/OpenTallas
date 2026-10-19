"""DAEMON-FIX2 (2026-10-19): a daemon restart (SIGTERM from systemctl restart) drains in-flight job steps -- each step
finishes and saves its job -- instead of killing them mid-step; queued steps never start."""
import os
import signal
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('CL_STATE', tempfile.mkdtemp(prefix='restart-drain-tests-'))
sys.path[:0] = [str(Path(__file__).resolve().parent)]
import closure_loop as CL  # noqa: E402


class RestartDrain(unittest.TestCase):
    def setUp(self):
        self.stack = [patch.object(CL, 'log'), patch.object(CL, '_STOP', threading.Event()),
                      patch.object(CL, '_STOP_SIG', []), patch.object(CL, '_FUTS', {}),
                      patch.object(CL, '_INFLIGHT', set()), patch.object(CL, '_RECOVERY_FUTURE', None),
                      patch.object(CL, '_DEFERRED_MERGE_FUTURE', None)]
        for p in self.stack:
            p.start()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.stack.append(patch.object(CL, '_POOL', self.pool))
        self.stack[-1].start()

    def tearDown(self):
        for p in reversed(self.stack):
            p.stop()
        self.pool.shutdown(wait=True, cancel_futures=True)

    def test_sigterm_mid_step_saves_the_step_and_starts_no_new_one(self):
        started = threading.Event()

        def advance(name, _fleet):
            j = CL.load_job(name)
            started.set()
            j['remote_effect'] = 'shipped'           # a step that changed a remote host ...
            time.sleep(0.5)                           # ... is still running when SIGTERM arrives
            j['status'] = 'RUNNING'
            CL.save_job(j)
        for n in ('df2-drain-a', 'df2-drain-b'):
            CL.save_job({'name': n, 'status': 'READY'})
        with patch.object(CL, 'advance_job', advance):
            for n in ('df2-drain-a', 'df2-drain-b'):
                CL._INFLIGHT.add(n)
                CL._FUTS[n] = self.pool.submit(CL._advance_and_release, n, None)
            self.assertTrue(started.wait(5))
            old = signal.signal(signal.SIGTERM, CL.request_stop)
            try:
                os.kill(os.getpid(), signal.SIGTERM)    # what systemctl restart sends (KillMode=process)
                time.sleep(0.05)
            finally:
                signal.signal(signal.SIGTERM, old)
            self.assertTrue(CL._STOP.is_set())
            self.assertTrue(CL.drain(log_every=0.2))
        a, b = CL.load_job('df2-drain-a'), CL.load_job('df2-drain-b')
        self.assertEqual((a['status'], a.get('remote_effect')), ('RUNNING', 'shipped'))   # finished + saved
        self.assertEqual((b['status'], b.get('remote_effect')), ('READY', None))           # queued: never started
        self.assertEqual(CL._INFLIGHT, set())

    def test_tick_starts_nothing_while_stopping(self):
        CL._STOP.set()
        with patch.object(CL, 'ingest', side_effect=AssertionError('tick ran while stopping')), \
                patch.object(CL, 'restart_if_requested', return_value=False):
            CL.tick(None)

    def test_inprocess_sync_restart_drains_instead_of_exiting(self):
        with patch.object(CL, '_RESTART', {'why': 'test'}), patch.object(CL, '_HOUSE_FUTURE', None):
            self.assertTrue(CL.restart_if_requested())
        self.assertTrue(CL._STOP.is_set())


if __name__ == '__main__':
    unittest.main()
