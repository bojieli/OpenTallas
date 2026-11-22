"""FETCH-RACE (COORD 11-22, QC slw_st_b_v1 cle6023ec2): a sealed place unit was NOT RUN because the kit fetch raced an ECO writer
(remote tar rc 1 'file changed as we read it') and the wave read it as KW_PLACE_RC=99 UNCLASSIFIED, never retried."""
import importlib.machinery
import importlib.util
import io
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "fleet"))
sys.path.insert(0, str(HERE))
import kit_wave as KW  # noqa: E402

LOG = """ot-run-sealed: SEALED on intel2: /srv/x/items/slw_st_b_v1__cle6023ec2/gen/slw_st_b_v1__cle6023ec2 (inputs fetched from epyc7)
tar: slw_st_b_v1__cle6023ec2/eco_20261122_105456_3667962/i1/run/results/asap7/dp/base: file changed as we read it
ot-job: NOT RUN: fetch epyc7:/srv/x/items/slw_st_b_v1__cle6023ec2/gen/slw_st_b_v1__cle6023ec2 failed
ot-run: RAN on localhost (unit oth-ubuntu-1270656-1795362980): exit 99
KW_PLACE_RC=99
"""


def load_job():
    ld = importlib.machinery.SourceFileLoader("ot_job_fr", str(HERE.parent / "fleet" / "ot-job"))
    spec = importlib.util.spec_from_loader("ot_job_fr", ld)
    m = importlib.util.module_from_spec(spec)
    ld.exec_module(m)
    return m


class P1:
    def __init__(self, rc, err):
        self.rc, self.stdout, self.stderr = rc, io.BytesIO(b""), io.BytesIO(err.encode())

    def wait(self):
        return self.rc


def fakes(rcs):
    calls = []

    def popen(argv, **k):
        rc, err = rcs[len(calls)]
        calls.append(argv)
        return P1(rc, err)

    def run(argv, stdin=None):
        return subprocess.CompletedProcess(argv, 0)
    return calls, popen, run


def test_file_changed_is_retried_then_succeeds(tmp_path):
    J = load_job()
    calls, popen, run = fakes([(1, "tar: k/eco_1/x: file changed as we read it\n"), (0, "")])
    slept = []
    got = J.tar_fetch("epyc7", "/srv/w/gen/k", str(tmp_path / "d"), sleep=slept.append, popen=popen, run=run)
    assert got == str(tmp_path / "d" / "k") and len(calls) == 2 and slept == [10]
    assert "--exclude='k/eco_[0-9]*_[0-9]*_[0-9]*'" in calls[0][-1] and "--anchored" in calls[0][-1]


def test_other_failures_are_not_retried_and_the_reason_is_kept(tmp_path):
    J = load_job()
    calls, popen, run = fakes([(2, "tar: k: Cannot open: No such file or directory\n")])
    try:
        J.tar_fetch("epyc7", "/srv/w/gen/k", str(tmp_path / "d"), sleep=lambda s: None, popen=popen, run=run)
        raise AssertionError("no JobError")
    except J.JobError as e:
        assert "remote tar rc 2" in str(e) and len(calls) == 1
    calls, popen, run = fakes([(1, "file changed as we read it")] * 3)
    try:
        J.tar_fetch("epyc7", "/srv/w/gen/k", str(tmp_path / "d2"), sleep=lambda s: None, popen=popen, run=run)
        raise AssertionError("no JobError")
    except J.JobError as e:
        assert "writer is active" in str(e) and len(calls) == 3


def test_wave_reads_an_otjob_fetch_not_run_as_infra_retry(tmp_path):
    assert KW.infra_not_run_line(LOG).startswith("ot-job: NOT RUN: fetch epyc7:")
    (tmp_path / "place.log").write_text(LOG)
    rec = {"status": "FAIL", "dir": str(tmp_path), "reason": "unclassified failure @place (see log): KW_PLACE_RC=99"}
    assert KW.infra_retry_kind(rec) == "not-run"
    (tmp_path / "place.log").write_text(LOG + "ot-job: RAN pid 1\nKW_PLACE_RC=0\n")
    assert KW.infra_retry_kind(rec) == ""
    assert KW.infra_not_run_line("ot-run: RAN on x: exit 1\nKW_PLACE_RC=1\n") is None
