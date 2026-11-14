"""WF-1 11-14: a job without a live client / container / process for 10+ min is dead (infra-orphan), not an ORPHAN for 3 h."""
import time
import autopilot as A


def job(done_ago, path="/s/k/item"):
    return {"id": "j1", "path": path, "host": "epyc9", "client_done_at": time.time() - done_ago}


def test_dead_after_ten_minutes_with_nothing_alive():
    assert A.orphan_is_dead(job(700), procs=[], remote_alive=lambda j: False)


def test_young_orphan_is_not_dead():
    assert not A.orphan_is_dead(job(120), procs=[], remote_alive=lambda j: False)


def test_live_hub_client_or_remote_container_keeps_it():
    assert not A.orphan_is_dead(job(900), procs=[(1, 5)], remote_alive=lambda j: False)
    assert not A.orphan_is_dead(job(900), procs=[], remote_alive=lambda j: True)


def test_no_client_done_time_is_not_dead():
    j = job(900)
    j.pop("client_done_at")
    assert not A.orphan_is_dead(j, procs=[], remote_alive=lambda j: False)


def test_remote_probe_counts_container_or_process_and_unknown_is_alive(monkeypatch):
    A._REMOTE_ALIVE.clear()
    j = job(900)
    assert not A.job_alive_remote(j, alive_probe=lambda *a, **k: (0, "0\n0\n", ""))
    A._REMOTE_ALIVE.clear()
    assert A.job_alive_remote(j, alive_probe=lambda *a, **k: (0, "1\n0\n", ""))
    A._REMOTE_ALIVE.clear()
    assert A.job_alive_remote(j, alive_probe=lambda *a, **k: (255, "", "ssh failed"))
