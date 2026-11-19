"""SMALLJOB-1119: a small job (<= 30 GB) is not queued on a saturated host: most admission memory among hosts that admit it now, else queue where it admits soonest."""
import importlib.machinery, importlib.util, pathlib
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_smalljob", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_smalljob", l)); l.exec_module(RUN)


def row(admit, free, load, ncpu=96):
    return dict(ncpu=ncpu, admit_gb=admit, free_gb=free, avail_gb=free, total_gb=1000, load1=load, load=load, committed_threads=0, mem_gb=1000)


def pick(rows, mem):
    RUN.reserved = lambda h, r: r
    RUN.physically_capable = lambda r, m: True
    RUN.load_capped = lambda r, m, t: False          # the host load cap is 0 fleet-wide (owner 11-18); the test must not depend on this host config
    return RUN.choose(rows, mem, 8)


def test_small_job_on_saturated_hosts_goes_where_most_admission_memory_is_free():
    host, queue = pick({"epyc7": row(4, 300, 202), "epyc10": row(513, 513, 120), "epyc8": row(60, 100, 140)}, 24)
    assert (host, queue) == ("epyc10", False)


def test_small_job_that_fits_nowhere_queues_on_the_host_that_admits_most():
    host, queue = pick({"epyc7": row(4, 900, 202), "epyc10": row(20, 100, 150)}, 28)
    assert (host, queue) == ("epyc10", True)          # the old rule queued on epyc7 (most free_gb, load 202)


def test_big_job_keeps_the_old_rule():
    host, queue = pick({"epyc7": row(4, 900, 202), "epyc10": row(20, 100, 150)}, 200)
    assert (host, queue) == ("epyc7", True)
