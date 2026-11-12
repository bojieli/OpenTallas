"""WAVE-BALANCE-1 11-11: waiter migration selection, never moving a started unit, gen host by capacity"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wave_balance as W
import kit_wave as K

NODE = "tolerant-swine"
KIT = "/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/items/t1/attempt_1/gen/t1"


def wrapper(pid, tag_n, kit=KIT, mem=48, age=0):
    tag = f"otrun-{NODE}-{1000 + tag_n}-77"
    return (f"{pid} 1 {age or 900} bash -c export X=1; cd {kit} || {{ exit 96; }}; OT_HEAVY_THREADS=8 /usr/local/bin/ot-heavy "
            f"--mem {mem} --tag {tag} -- bash {kit}/../run_kit.sh {kit} route {mem} 8; rc=$?", tag)


def ps_waiting(pid=100, n=1, kit=KIT):
    w, tag = wrapper(pid, n, kit)
    return w + f"\n{pid + 1} {pid} 900 /bin/bash /usr/local/bin/ot-heavy --mem 48 --tag {tag} -- bash x\n"


def ps_started(pid=100, n=1, kit=KIT):
    w, tag = wrapper(pid, n, kit)
    return w + f"\n{pid + 1} {pid} 900 /bin/bash /usr/local/lib/ot-heavy/ot-heavy-exit oth-u-1 bash -c x\n"


def test_parse_waiters_waiting_vs_started():
    a = W.parse_waiters(ps_waiting(), NODE)
    assert len(a) == 1 and not a[0]["started"] and a[0]["dir"] == KIT and a[0]["mem"] == 48
    assert a[0]["client_pid"] == 1001 and a[0]["heavy"] == [101] and a[0]["wrapper"] == 100
    assert W.parse_waiters(ps_started(), NODE)[0]["started"]
    assert W.parse_waiters(ps_waiting(), "other-hub") == []          # another hub's client is never ours


def row(admit=300, load=20, cores=128, scratch=800, wait_n=0, wait_gb=0):
    return {"admit": admit, "load": load, "cores": cores, "run": 5, "scratch_gb": scratch, "wait_n": wait_n, "wait_gb": wait_gb}


def cand(i, age, host="epyc9", mem=48, thr=8, gb=2.0):
    return {"id": i, "die": "s81", "type": "t" + i, "unit": "ap-" + i + "-a1", "host": host, "mem": mem, "threads": thr,
            "age_s": age, "kit_gb": gb}


STATUS = {"epyc9": row(236, 77, 96, 2610, 29, 582), "epyc2": row(724, 23, 128, 59), "intel1": row(107, 64, 112, 500),
          "localhost": row(425, 41, 112, 900), "epyc7": row(151, 63, 96, 1359), "epyc8": row(20, 80, 96, 2252, 8, 550)}


def test_plan_picks_oldest_first_and_best_target():
    cs = [cand("abcdef"[i], 100 + i * 100) for i in range(6)]
    m, sk = W.plan_moves(cs, STATUS, {"min_wait_s": 0}, hub_names=("intel2",))
    assert [x["cand"]["id"] for x in m] == ["f", "e", "d", "c"]            # oldest first, at most 4 per tick
    assert m[0]["to"] == "intel1"                                            # most free cores x admits among the allowed
    assert all(x["to"] != "localhost" and x["to"] != "intel2" for x in m)
    assert len(sk) == 2 and "max 4 moves" in sk[0][1]


def test_plan_scratch_rule_epyc2_has_59gb():
    m, sk = W.plan_moves([cand("a", 900, gb=2.0)], STATUS, {}, ())
    assert m and m[0]["to"] != "epyc2"                                     # 59 GB <= 2 + 100: epyc2 is out


def test_plan_target_rules():
    for t, v in (("admit", row(admit=20)), ("load", row(load=110, cores=128)), ("scratch", row(scratch=100))):
        st = {"epyc9": STATUS["epyc9"], "x": v}
        m, sk = W.plan_moves([cand("a", 900, gb=5)], st, {}, ())
        assert not m and "no target" in sk[0][1], t
    st = {"epyc9": STATUS["epyc9"], "x": row(), "refused": None}
    st = {k: v for k, v in st.items() if v}
    assert W.plan_moves([cand("a", 900)], st, {}, ())[0][0]["to"] == "x"
    # 80 % rule: 76.8 of 96 cores is the line
    st = {"epyc9": STATUS["epyc9"], "x": row(load=76, cores=96)}
    assert W.plan_moves([cand("a", 900)], st, {}, ())[0]
    st = {"epyc9": STATUS["epyc9"], "x": row(load=77, cores=96)}
    assert not W.plan_moves([cand("a", 900)], st, {}, ())[0]


def test_plan_needs_a_hot_source_and_an_old_waiter():
    st = dict(STATUS); st["epyc9"] = row(236, 77, 96, 2610, 8, 160)            # exactly 8 waiters: not hot (> 8 only)
    m, sk = W.plan_moves([cand("a", 900)], st, {}, ())
    assert not m and "<= 8" in sk[0][1]
    m, sk = W.plan_moves([cand("a", 30)], STATUS, {}, ())
    assert not m and "waited 30" in sk[0][1]
    m, sk = W.plan_moves([cand("a", 900, gb=60)], STATUS, {}, ())
    assert not m and "GB >" in sk[0][1]


def test_plan_charges_the_target():
    st = {"epyc9": STATUS["epyc9"], "x": row(admit=100, load=10, cores=128)}   # takes two 48 GB jobs, not three
    m, _ = W.plan_moves([cand(str(i), 900 + i) for i in range(3)], st, {}, ())
    assert len(m) == 2


def test_excluded_hosts_never_targets():
    st = {"epyc9": STATUS["epyc9"], "intel2": row(), "localhost": row()}
    assert not W.plan_moves([cand("a", 900)], st, {}, hub_names=("intel2",))[0]
    st["epyc3"] = row()
    assert W.plan_moves([cand("a", 900)], st, {"exclude_hosts": ["epyc3"]}, ("intel2",))[0] == []


def test_with_hosts():
    a = ["ot-run", "--mem", "48", "--dir", "K", "--stage", "K", "--", "bash", "r"]
    assert W.with_hosts(a, "epyc2") == ["ot-run", "--mem", "48", "--dir", "K", "--stage", "K", "--hosts", "epyc2", "--", "bash", "r"]
    b = ["ot-run", "--hosts", "epyc9", "--", "bash", "--hosts", "x"]
    assert W.with_hosts(b, "epyc2") == ["ot-run", "--hosts", "epyc2", "--", "bash", "--hosts", "x"]


# ---------------------------------------------------------------------------------------------- apply, with fakes
class FakeAP:
    AP_DIR = None
    HUB_NAME = "intel2"
    HUB_ALIASES = {"intel2": ("intel2", "tolerant-swine")}

    def __init__(self, tmp):
        FakeAP.AP_DIR = tmp
        self.saved = []

    def set_status(self, st, j, status, why=""):
        j["status"] = status
        j.setdefault("history", []).append(["t", status, why])

    def ssh_host(self, h):
        return h


class FakeOps:
    def __init__(self, ps_seq, verify=(), copy_rc=0, dst_exists=False):
        self.ps_seq, self.calls, self.verify_diffs, self.copy_rc, self.dst_exists = list(ps_seq), [], list(verify), copy_rc, dst_exists

    def ps(self, h):
        self.calls.append(("ps", h))
        return self.ps_seq.pop(0) if len(self.ps_seq) > 1 else self.ps_seq[0]

    def py(self, h, code, args, timeout=0):
        self.calls.append(("py", h))
        if "lst" in args:
            return {"lst": "L", "files": 3}
        if code == W.SRC_PROBE:
            return {"bytes": 2 * 2**30, "lst": "L", "files": 3, "skip": [], "unsafe": []}
        return {"exists": [self.dst_exists] * len(args["paths"]), "free_gb": 900, "linked": []}

    def copy(self, s, d, roots):
        self.calls.append(("copy", s, d)); return self.copy_rc, ""

    def verify(self, s, d, roots):
        self.calls.append(("verify",)); return self.verify_diffs

    def stop_unit(self, u):
        self.calls.append(("stop", u)); return 0

    def kill(self, h, pids):
        self.calls.append(("kill", h, tuple(pids))); return 0

    def client_argv(self, pid):
        return ["/bin/bash", "ot-run", "--mem", "48", "--dir", KIT, "--stage", KIT, "--", "bash", "r"]

    def client_unit_ok(self, pid, unit):
        return True

    def launch(self, unit, logf, argv):
        self.calls.append(("launch", unit, str(logf), tuple(argv))); return True

    def names(self):
        return [c[0] for c in self.calls]


def job():
    return {"id": "j1", "die": "s81", "type": "t1", "status": "RUNNING", "unit": "ap-j1-a1", "path": KIT, "host": "epyc9",
            "kit": "epyc9:" + KIT, "runner": KIT + "/../run_kit.sh", "mem_gb": 48, "threads": 8, "attempts": 1,
            "lane": "KIT-WAVE-3", "client_log": "/x/a1.log", "goal": "route"}


def mv(j, ps):
    w = W.parse_waiters(ps, NODE)[0]
    c = {"id": "j1", "die": "s81", "type": "t1", "unit": "ap-j1-a1", "host": "epyc9", "path": KIT, "mem": 48, "threads": 8,
         "age_s": 900, "waiter": w, "kit_gb": 2.0, "job": j, "hub_node": NODE}
    return {"cand": c, "to": "epyc2"}


def test_move_ok_order_and_record(tmp_path):
    ap, j = FakeAP(tmp_path), job()
    (tmp_path / "jobs" / "j1").mkdir(parents=True)
    ops = FakeOps([ps_waiting()])
    ok, note = W.move_one(ap, {"jobs": {"j1": j}}, ops, mv(j, ps_waiting()), lambda s: None)
    assert ok, note
    n = ops.names()
    assert n.index("copy") < n.index("verify") < n.index("stop") < n.index("kill") < n.index("launch")
    launch = [c for c in ops.calls if c[0] == "launch"][0]
    assert launch[1] == "ap-j1-a1" and "--hosts" in launch[3] and launch[3][launch[3].index("--hosts") + 1] == "epyc2"
    assert [c for c in ops.calls if c[0] == "kill"][0][2] == (100, 101)      # the exact waiter pids, no pattern
    assert j["host"] == "epyc2" and j["kit"] == "epyc2:" + KIT and j["moved_from"] == "epyc9"
    assert j["wave_balance"][0]["to"] == "epyc2" and j["client_log"].endswith("a1-wb1.log")


def test_started_waiter_is_never_stopped_or_killed(tmp_path):
    ap, j = FakeAP(tmp_path), job()
    # started when the plan was made: the candidate list drops it
    assert all(w["started"] for w in W.parse_waiters(ps_started(), NODE))
    # admitted between the plan and the stop (checked after the copy): nothing is stopped, killed or launched
    ops = FakeOps([ps_started()])
    ok, note = W.move_one(ap, {"jobs": {"j1": j}}, ops, mv(j, ps_waiting()), lambda s: None)
    assert not ok and "started" in note
    assert not {"stop", "kill", "launch"} & set(ops.names()) and j["host"] == "epyc9"
    # admitted in the instant of the stop: the unit is stopped (client gone) but the running command is NOT killed
    ops = FakeOps([ps_waiting(), ps_started()])
    ok, note = W.move_one(ap, {"jobs": {"j1": j}}, ops, mv(j, ps_waiting()), lambda s: None)
    assert not ok and "admitted during the stop" in note
    assert "kill" not in ops.names() and "launch" not in ops.names() and j["host"] == "epyc9"


def test_candidates_skip_started_and_cold_hosts(tmp_path):
    ap, j = FakeAP(tmp_path), job()
    ap.ssh_host = lambda h: h
    st = {"jobs": {"j1": j}}
    status = {"epyc9": row(wait_n=29), "epyc2": row()}
    assert len(W.candidates(ap, st, FakeOps([ps_waiting()]), status, NODE, {})) == 1
    assert W.candidates(ap, st, FakeOps([ps_started()]), status, NODE, {}) == []         # started: never a candidate
    assert W.candidates(ap, st, FakeOps([ps_waiting()]), {"epyc9": row(wait_n=8)}, NODE, {}) == []   # not hot
    j2 = dict(j, lane="VISLAYOUT2")                                                      # not a kit-wave job
    assert W.candidates(ap, {"jobs": {"j1": j2}}, FakeOps([ps_waiting()]), status, NODE, {}) == []


def test_failed_copy_or_verify_or_existing_target_leaves_job_alone(tmp_path):
    for kw in ({"copy_rc": 23}, {"verify": ["<f+++++++++ x"]}, {"dst_exists": True}):
        ap, j = FakeAP(tmp_path), job()
        ops = FakeOps([ps_waiting()], **kw)
        ok, note = W.move_one(ap, {"jobs": {"j1": j}}, ops, mv(j, ps_waiting()), lambda s: None)
        assert not ok and not {"stop", "kill", "launch"} & set(ops.names()), kw
        assert j["host"] == "epyc9" and "wave_balance" not in j


def test_step_is_inert_unless_enabled(tmp_path):
    ap = FakeAP(tmp_path)
    ap.DRY = False
    assert W.step(ap, {"jobs": {}}) == 0


def test_gen_host_by_capacity():
    cfg = {"dies": {"s81": {"gen_host": "epyc9", "gen_hosts": ["epyc9", "epyc2", "intel1"], "event": "e", "plan": "/p", "src": "/s"}}}
    cfg["_otrun_status"] = {"epyc9": {"admit": 236, "load": 77, "cores": 96, "wait_gb": 582, "scratch_gb": 2610},
                            "epyc2": {"admit": 724, "load": 23, "cores": 128, "scratch_gb": 400},
                            "intel1": {"admit": 107, "load": 64, "cores": 112, "scratch_gb": 500}}
    assert K.host_capacity(cfg["_otrun_status"]["epyc2"]) > K.host_capacity(cfg["_otrun_status"]["intel1"]) > K.host_capacity(cfg["_otrun_status"]["epyc9"])
    assert K.pick_gen_host(cfg, "s81", take=48) == "epyc2"
    cfg["_otrun_status"]["epyc2"]["scratch_gb"] = 30            # under the disk floor: out, however big its capacity
    assert K.pick_gen_host(cfg, "s81", take=48) == "intel1"


def test_waiter_guard_skips_hosts_over_20_waiters():
    def c(hosts, **kw):
        d = {"dies": {"s81": {"gen_host": hosts[0], "gen_hosts": hosts, "event": "e", "plan": "/p", "src": "/s"}}}
        d["_otrun_status"] = {"epyc9": {"admit": 900, "load": 20, "cores": 96, "wait_n": 63, "scratch_gb": 2600},
                              "epyc7": {"admit": 100, "load": 70, "cores": 96, "wait_n": 3, "scratch_gb": 1300},
                              "epyc8": {"admit": 50, "load": 80, "cores": 96, "wait_n": 5, "scratch_gb": 2200}}
        d.update(kw)
        return d
    # epyc9 has the biggest capacity but 63 waiters: the calm gen host wins
    assert K.pick_gen_host(c(["epyc9", "epyc7"]), "s81", take=48) == "epyc7"
    # the only gen host is over the cap: the overflow host (inputs present) takes it, a SRC-INCOMPLETE one does not
    assert K.pick_gen_host(c(["epyc9"], gen_overflow_hosts=["epyc7", "epyc8"]), "s81") == "epyc7"
    assert K.pick_gen_host(c(["epyc9"], gen_overflow_hosts=["epyc7", "epyc8"], _src_incomplete={"epyc7": {"s81": 1}}), "s81") == "epyc8"
    # no overflow configured or no calm host: unchanged; cap 0 = off
    assert K.pick_gen_host(c(["epyc9"]), "s81") == "epyc9"
    assert K.pick_gen_host(c(["epyc9", "epyc7"], gen_waiter_cap=0), "s81", take=48) == "epyc9"
