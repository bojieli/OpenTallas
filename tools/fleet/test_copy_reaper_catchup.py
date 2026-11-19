"""COPY-REAPER-1119 / CATCHUP-1119: the reaper script is exact-PID only; catchup retries only hosts that are behind, in parallel, with backoff."""
import importlib.machinery, importlib.util, json, os, pathlib, time
H = pathlib.Path(__file__).parent


def load():
    ld = importlib.machinery.SourceFileLoader("ots_cu", str(H / "ot-tools-sync"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader("ots_cu", ld)); ld.exec_module(m); return m


def test_reaper_script_only_touches_rsync_server_by_exact_pid():
    s = (H / "rsync_reaper.sh").read_text()
    assert 'case "$a" in "rsync --server"*)' in s and "pgrep -x rsync" in s and "kill -TERM $p" in s
    assert ("pk" + "ill") not in s and ("kill" + "all") not in s and "[ $b -ge 100 ]" in s
    assert "$2==$4 && $5>=m" in s                                                   # unchanged IO over the window AND old enough


def test_catchup_pushes_only_hosts_behind_in_parallel_and_backs_off_failures(tmp_path):
    m = load()
    m.current = lambda: "newrev"
    m.log = lambda s: None
    cur = {"a": "newrev", "b": "old", "c": "old", "d": "old"}
    pushed = []

    def fn(h, name, prev):
        time.sleep(0.3); pushed.append((h, prev))
        if h == "c":
            return False, "ssh: refused"
        return True, "ok"
    sf = tmp_path / "cu.json"
    t0 = time.time()
    res = m.catchup(hosts=list(cur), state=sf, now_fn=lambda: 1000.0, host_cur=lambda h: cur[h], fn=fn)
    assert time.time() - t0 < 0.8                                                   # b, c, d in parallel
    assert sorted(h for h, _ in pushed) == ["b", "c", "d"] and ("b", "old") in pushed          # a is current: untouched
    assert {r[0]: r[1] for r in res} == {"b": True, "c": False, "d": True}
    st = json.loads(sf.read_text())
    assert st["c"]["fails"] == 1 and st["c"]["next"] == 1300.0 and "b" not in st
    pushed.clear()
    m.catchup(hosts=list(cur), state=sf, now_fn=lambda: 1100.0, host_cur=lambda h: cur[h], fn=fn)   # c is in backoff until 1300
    assert [h for h, _ in pushed] == ["b", "d"]
