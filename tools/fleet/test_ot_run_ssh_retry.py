"""FLOW-21 SSHRETRY 11-01: an ssh connection that fails before any remote output is retried; a refusal is not."""
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock
M = SourceFileLoader('ot_run_ssh_retry', str(Path(__file__).with_name('ot-run'))).load_module()


class FakeP:
    def __init__(self, lines, rc):
        self.stderr = iter(l.encode() for l in lines)
        self.rc = rc

    def wait(self):
        return self.rc

    def kill(self):
        pass


def _run(lines, rc):
    with mock.patch.object(M.subprocess, 'Popen', return_value=FakeP(lines, rc)):
        return M.run('localhost', 4, ['true'], quiet=True)


def test_kex_reset_before_admission_is_connfail():
    assert _run(['kex_exchange_identification: read: Connection reset by peer\n',
                 'Connection reset by ::1 port 22\n'], 255) == (255, False)
    assert M.LAST_RUN['connfail'] is True


def test_remote_refusal_is_not_connfail():
    assert _run(['ot-heavy: NOT RUN: no memory\n'], 75)[1] is False
    assert M.LAST_RUN['connfail'] is False


def test_started_then_dropped_is_not_retried():
    tag = "otrun-%s-7-1000" % M.os.uname().nodename
    with mock.patch.object(M.os, 'getpid', return_value=7), mock.patch.object(M.time, 'time', return_value=1.0):
        rc, ran = _run([f'x OT_RUN_START {tag} oth-1\n', 'Connection reset by peer\n'], 255)
    assert ran is False and M.LAST_RUN['connfail'] is False


def test_place_loop_retries_with_backoff():
    src = Path(__file__).with_name('ot-run').read_text()
    assert 'LAST_RUN["connfail"] and conn_tries < len(SSH_RETRY_BACKOFF_S)' in src
    assert M.SSH_RETRY_BACKOFF_S == (5, 15, 45)
