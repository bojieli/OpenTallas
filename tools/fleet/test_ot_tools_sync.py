"""ot-tools-sync (MERGE-QUEUE-1): main@sha becomes a read-only versioned tree, rt/current flips by one rename only after the
smoke test passes, an older version is never touched, and a live edit of the current tree is reported as drift."""
import importlib.machinery, importlib.util, json, os, pathlib, subprocess, sys, tempfile, unittest

P = str(pathlib.Path(__file__).with_name("ot-tools-sync"))


def sh(*a, cwd=None):
    return subprocess.run(list(a), cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Sync(unittest.TestCase):
    def setUp(self):
        d = self.d = pathlib.Path(tempfile.mkdtemp())
        g = self.g = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]
        sh(*g, "init", "-q", "--bare", str(d / "origin.git"))
        sh(*g, "clone", "-q", str(d / "origin.git"), str(d / "dev"))
        dev = self.dev = d / "dev"
        for sub in ("tools/autopilot", "tools/fleet", "tools/die_plan", "physical/common_flow", "rtl"):
            (dev / sub).mkdir(parents=True)
        (dev / "tools/autopilot/kit_wave.py").write_text("print('wave')\n")
        (dev / "tools/fleet/ot-run").write_text("#!/usr/bin/env python3\nprint('ot-run')\n")
        (dev / "tools/die_plan/gen_phys.py").write_text("X = 1\n")
        (dev / "physical/common_flow/grt183_make.sh").write_text("#!/bin/bash\necho grt\n")
        (dev / "rtl/big.sv").write_text("module m; endmodule\n")
        sh(*g, "add", "-A", cwd=dev); sh(*g, "commit", "-qm", "v1", cwd=dev); sh(*g, "push", "-q", "origin", "main", cwd=dev)
        sh(*g, "clone", "-q", str(d / "origin.git"), str(d / "repo"))
        sh("git", "config", "extensions.worktreeConfig", "true", cwd=d / "repo")
        self.env = dict(os.environ, OT_RT_ROOT=str(d / "rt"), MQ_REPO=str(d / "repo"), MQ_HOME=str(d / "mq"), OT_RT_HOSTS="",
                        OT_RT_SMOKE_TESTS="", OT_RT_MIN_FREE_GB="0", OT_RT_LEGACY="", OT_RT_BACKEND_ROOTS="", MQ_COORD=str(d / "coord"), MQ_PYTHON=sys.executable)
        self.env.pop("MQ_SPARSE", None)  # Exercise the runtime default, independent of the gate checkout's sparse scope.

    def run_(self, *a):
        return subprocess.run([sys.executable, "-I", P, *a], env=self.env, capture_output=True, text=True, timeout=300)

    def commit(self, rel, text):
        (self.dev / rel).write_text(text)
        sh(*self.g, "commit", "-qam", rel, cwd=self.dev); sh(*self.g, "push", "-q", "origin", "main", cwd=self.dev)
        return sh("git", "rev-parse", "HEAD", cwd=self.dev)

    def test_sync_flip_readonly_and_old_version_untouched(self):
        v1 = sh("git", "rev-parse", "HEAD", cwd=self.dev)
        r = self.run_("sync", "--no-hosts")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rt = self.d / "rt"
        self.assertEqual(os.readlink(rt / "current"), v1[:12])
        self.assertTrue((rt / "current/tools/autopilot/kit_wave.py").is_file())
        self.assertFalse((rt / "current/rtl").exists())                 # sparse: tools + physical/common_flow only
        self.assertFalse(os.access(rt / "current/tools/autopilot/kit_wave.py", os.W_OK) and os.geteuid() != 0)
        man = json.loads((rt / f"{v1[:12]}.manifest.json").read_text())
        self.assertEqual(man["sha"], v1)
        old_bytes = (rt / v1[:12] / "tools/die_plan/gen_phys.py").read_bytes()
        v2 = self.commit("tools/die_plan/gen_phys.py", "X = 2\n")
        r = self.run_("sync", "--no-hosts")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(os.readlink(rt / "current"), v2[:12])
        self.assertEqual((rt / v1[:12] / "tools/die_plan/gen_phys.py").read_bytes(), old_bytes)
        self.assertIn(f"-> {v2[:12]}", (rt / "history.log").read_text())

    def test_follow_fast_forwards_only_and_is_a_noop_when_current(self):
        v1 = sh("git", "rev-parse", "HEAD", cwd=self.dev)
        self.assertEqual(self.run_("follow", "--no-hosts").returncode, 0)          # no current yet: materializes origin/main
        self.assertEqual(os.readlink(self.d / "rt/current"), v1[:12])
        n = (self.d / "rt/history.log").read_text().count("\n")
        self.assertEqual(self.run_("follow", "--no-hosts").returncode, 0)
        self.assertEqual((self.d / "rt/history.log").read_text().count("\n"), n)
        v2 = self.commit("tools/die_plan/gen_phys.py", "X = 2\n")
        self.assertEqual(self.run_("follow", "--no-hosts").returncode, 0)
        self.assertEqual(os.readlink(self.d / "rt/current"), v2[:12])
        sh(*self.g, "checkout", "-q", "-b", "other", v1, cwd=self.dev)                # a main that does not contain current
        (self.dev / "tools/die_plan/gen_phys.py").write_text("X = 7\n")
        sh(*self.g, "commit", "-qam", "fork", cwd=self.dev)
        sh("git", "push", "-q", "-f", "origin", "other:main", cwd=self.dev)
        r = self.run_("follow", "--no-hosts")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(os.readlink(self.d / "rt/current"), v2[:12])               # stays

    def test_follow_reverts_the_commit_whose_smoke_fails_without_force(self):
        v1 = sh("git", "rev-parse", "HEAD", cwd=self.dev)
        self.assertEqual(self.run_("follow", "--no-hosts").returncode, 0)
        self.commit("tools/die_plan/gen_phys.py", "X = 2\n")
        bad = self.commit("tools/autopilot/kit_wave.py", "def broken(:\n")
        self.commit("tools/die_plan/gen_phys.py", "X = 3\n")
        r = self.run_("follow", "--no-hosts"); self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertEqual(os.readlink(self.d / "rt/current"), v1[:12])                 # running version untouched
        o = self.d / "origin.git"
        self.assertEqual(sh("git", "show", "main:tools/autopilot/kit_wave.py", cwd=o), "print('wave')")
        self.assertIn("Revert", sh("git", "log", "-1", "--format=%s", "main", cwd=o))
        self.assertEqual(subprocess.run(["git", "merge-base", "--is-ancestor", bad, "main"], cwd=o).returncode, 0)   # history kept
        self.assertEqual(sh("git", "show", "main:tools/die_plan/gen_phys.py", cwd=o), "X = 3")                       # later good commit kept
        self.assertEqual(self.run_("follow", "--no-hosts").returncode, 0)
        self.assertEqual(os.readlink(self.d / "rt/current"), sh("git", "rev-parse", "main", cwd=o)[:12])

    def test_smoke_failure_keeps_current(self):
        v1 = sh("git", "rev-parse", "HEAD", cwd=self.dev)
        self.assertEqual(self.run_("sync", "--no-hosts").returncode, 0)
        v2 = self.commit("tools/autopilot/kit_wave.py", "def broken(:\n")
        r = self.run_("sync", "--no-hosts")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertEqual(os.readlink(self.d / "rt/current"), v1[:12])
        self.assertTrue((self.d / f"rt/{v2[:12]}.smoke-failed").is_file())

    def test_live_edit_is_drift(self):
        v1 = sh("git", "rev-parse", "HEAD", cwd=self.dev)
        self.assertEqual(self.run_("sync", "--no-hosts").returncode, 0)
        self.assertEqual([l for l in self.run_("drift").stdout.splitlines() if l.startswith("DRIFT")], [])
        f = self.d / "rt" / v1[:12] / "tools/die_plan/gen_phys.py"
        os.chmod(f, 0o644); f.write_text("X = 99  # live-only\n")
        out = self.run_("drift").stdout
        self.assertIn(f"hub rt/{v1[:12]} changed: tools/die_plan/gen_phys.py", out)


if __name__ == "__main__":
    unittest.main()


class Guard(unittest.TestCase):
    def load(self):
        loader = importlib.machinery.SourceFileLoader("ots", P)
        m = importlib.util.module_from_spec(importlib.util.spec_from_loader("ots", loader)); loader.exec_module(m)
        return m

    def mk(self, names):
        d = pathlib.Path(tempfile.mkdtemp())
        for i, n in enumerate(names):
            (d / n).mkdir(); os.utime(d / n, (1000 + i, 1000 + i)); (d / f"{n}.manifest.json").write_text("{}")
        os.symlink(names[-1], d / "current")
        return d

    def test_prune_keeps_newest_current_protected_and_named(self):
        m = self.load(); names = ["%012x" % i for i in range(1, 9)]
        m.live_reference_text = lambda *a, **k: ""      # RT-HOST-DATA-1124: isolate from the test host's live refs (6.800000000000001 in a job json names "%012x" % 1)
        d = self.mk(names)
        gone = m.prune_snapshots(d, keep=3, protect=(names[1],), text="x " + names[2] + " y")
        self.assertEqual(sorted(gone), sorted([names[0], names[3], names[4]]))   # newest 3 = 6,7,8; protect 2; named 3
        self.assertTrue((d / names[2]).is_dir() and (d / names[1]).is_dir() and (d / names[7]).is_dir())
        self.assertFalse((d / f"{names[0]}.manifest.json").exists())

    def test_prune_keeps_pins_specs_and_recent_launches_clean_aggr_r3(self):
        m = self.load(); names = ["%012x" % ((0x9e3779b97f4a * (i + 3)) % 2**48) for i in range(1, 9)]
        d = self.mk(names)
        m.recent_launch_text = lambda *a, **k: ""
        text = '{"tools_sha": "%s7777"}\n gen_tools_pin: %s\n' % (names[0], names[3][:9])
        self.assertTrue(m.named_in(names[0], text) and m.named_in(names[3], text) and not m.named_in(names[4], text))
        gone = m.prune_snapshots(d, keep=3, text=text)
        self.assertNotIn(names[0], gone); self.assertNotIn(names[3], gone); self.assertIn(names[4], gone)
        j = "Started oth-1.scope - bash -c python3 /srv/x/rt/%s/tools/fleet/ot-run --hosts epyc7\n" % names[1]
        self.assertIn("rt/" + names[1], m.recent_launch_text.__wrapped__(journal=j) if hasattr(m.recent_launch_text, "__wrapped__") else self.load().recent_launch_text(journal=j))
        sp = pathlib.Path(tempfile.mkdtemp())
        (sp / "autopilot/private_specs/L/x").mkdir(parents=True)
        (sp / "autopilot/private_specs/L/x/spec.json").write_text('{"rt": "/srv/opentallas-scratch2/claude/rt/%s"}' % names[2])
        self.assertIn(names[2], self.load().private_spec_text(roots=[sp]))
        self.assertEqual(self.load().private_spec_text(roots=[sp], now=10**12), "")

    def test_prune_off_and_in_use_untouched(self):
        m = self.load(); names = ["%012x" % i for i in range(1, 6)]
        d = self.mk(names)
        self.assertEqual(m.prune_snapshots(d, keep=0, text=""), [])
        m.in_use = lambda p: [1] if pathlib.Path(p).name == names[0] else []
        gone = m.prune_snapshots(d, keep=1, text="")
        self.assertNotIn(names[0], gone); self.assertEqual(len(gone), 1)          # keep=1 is raised to the minimum 3: only names[1] goes (names[0] is in use)

    def test_prune_skips_while_the_same_root_is_locked(self):
        import fcntl
        m = self.load()
        m.live_reference_text = lambda *a, **k: ""      # RT-HOST-DATA-1124: isolate from the test host's live refs (6.800000000000001 in a job json names "%012x" % 1)
        names = ["%012x" % i for i in range(1, 6)]
        d = self.mk(names)
        with (d / ".prune.lock").open("a") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(m.prune_snapshots(d, keep=3, text=""), [])
            self.assertTrue(all((d / name).is_dir() for name in names))
        self.assertEqual(set(m.prune_snapshots(d, keep=3, text="")), set(names[:2]))

    def test_remote_prune_is_parallel_bounded_and_reports_all_hosts(self):
        import threading
        from types import SimpleNamespace

        m = self.load()
        barrier = threading.Barrier(3, timeout=5)
        lock = threading.Lock()
        active = set()
        peaks = []
        calls = []
        logs = []
        m.log = logs.append

        def remote(argv, **kw):
            host = argv[-2]
            with lock:
                calls.append((host, kw["input"], kw["timeout"]))
                active.add(host)
                peaks.append(len(active))
            if host in {"H1", "H2", "H3"}:
                barrier.wait()
            with lock:
                active.remove(host)
            return SimpleNamespace(returncode=1 if host == "H2" else 0, stdout="", stderr="receipt")

        m.run = remote
        pins = "wrapper /rt/1234567890ab/tool.py, full=0123456789abcdef, duplicate=1234567890ab"
        m.prune_build_hosts(pins, hosts=["H1", "H2", "H3", "H3", "H4"])
        self.assertEqual(max(peaks), 3)
        compact = "0123456789abcdef\n1234567890ab"
        self.assertEqual(sorted(calls), [(host, compact, 900) for host in ("H1", "H2", "H3", "H4")])
        self.assertEqual({line.split()[0] for line in logs}, {"H1", "H2", "H3", "H4"})
        self.assertTrue(any(line.startswith("H2 prune") and "rc=1 receipt" in line for line in logs))

    def test_low_disk_refuses_to_write(self):
        m = self.load(); d = pathlib.Path(tempfile.mkdtemp())
        m.RT = d; m.MIN_FREE_GB = 10 ** 9
        with self.assertRaises(RuntimeError) as c:
            m.materialize("a" * 40)
        self.assertIn("OT_RT_MIN_FREE_GB", str(c.exception)); self.assertEqual(list(d.iterdir()), [])


class InstalledDiff(unittest.TestCase):
    def test_a_live_only_copy_that_differs_is_an_alert_a_symlinked_one_is_not(self):
        m = Guard.load(Guard())
        import types
        def runner(cmd, **kw):
            return types.SimpleNamespace(stdout=json.dumps({"/usr/local/bin/ot-heavy": "DIFF ot-heavy", "/srv/x/rt/abc/tools/fleet/ot-run": "DIFF ot-run", "/usr/local/bin/ot-ok": "OK"}) + "\n")
        out = m.installed_diffs({"tools/fleet/ot-heavy": "aa"}, hosts=["h1"], runner=runner)
        self.assertEqual(len(out), 2)                       # intel2 + h1, once each: the /rt/ path is in step by construction
        self.assertTrue(all("/usr/local/bin/ot-heavy differs" in l for l in out), out)

    def test_in_step_is_empty(self):
        m = Guard.load(Guard())
        import types
        out = m.installed_diffs({"tools/fleet/ot-heavy": "aa"}, hosts=["h1"], runner=lambda c, **k: types.SimpleNamespace(stdout=json.dumps({"/usr/local/bin/ot-heavy": "OK"}) + "\n"))
        self.assertEqual(out, [])


class HostPrune(unittest.TestCase):
    def test_prune_subcommand_prunes_the_local_rt_and_reads_pins_from_stdin(self):
        d = pathlib.Path(tempfile.mkdtemp()); names = ["%012x" % i for i in range(1, 8)]
        for i, n in enumerate(names):
            (d / n).mkdir(); os.utime(d / n, (1000 + i, 1000 + i))
        os.symlink(names[-1], d / "current")
        env = dict(os.environ, OT_RT_ROOT=str(d), OT_RT_KEEP="2", MQ_HOME=str(d / "mq"), OT_RT_HOSTS="", MQ_COORD=str(d / "coord"))
        r = subprocess.run([sys.executable, "-I", P, "prune"], input="pinned " + names[0], env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        left = sorted(x.name for x in d.iterdir() if x.is_dir() and not x.is_symlink() and len(x.name) == 12)
        self.assertEqual(left, sorted([names[0], names[4], names[5], names[6]]))   # newest 3 (the minimum), pinned 1


class SyncAlert(unittest.TestCase):
    def load(self):
        return Guard.load(Guard())

    def test_first_failure_posts_at_once_repeats_hourly_changes_post_and_recovery_posts_once(self):
        m = self.load(); sf = tempfile.mktemp(); posted = []
        pst = posted.append
        m.current = lambda root=None: "abc123"
        self.assertTrue(m.sync_alert(False, "disk 93 GB < 100", sf, pst, now=1000).startswith("ALERT"))        # first failure: immediately
        self.assertEqual(m.sync_alert(False, "disk 93 GB < 100", sf, pst, now=1300), "")                       # same reason inside the hour: quiet
        self.assertIn("still failing for 60 min", m.sync_alert(False, "disk 93 GB < 100", sf, pst, now=1000 + 3600))
        self.assertTrue(m.sync_alert(False, "smoke failed", sf, pst, now=5000).startswith("ALERT"))             # a new reason posts
        self.assertIn("recovered after", m.sync_alert(True, "", sf, pst, now=7000))
        self.assertEqual(m.sync_alert(True, "", sf, pst, now=7100), ""); self.assertEqual(len(posted), 4)

    def test_sync_guarded_turns_an_exception_into_an_alert_and_a_failing_exit(self):
        m = self.load(); posted = []
        m.sync = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("/rt: 93 GB free < 100 GB (OT_RT_MIN_FREE_GB)"))
        m.sync_alert = lambda ok, reason, *a, **k: posted.append((ok, reason))
        self.assertEqual(m.sync_guarded("", True, False), 1)
        self.assertEqual(posted[0][0], False); self.assertIn("93 GB free", posted[0][1])

    def test_sync_guarded_prints_the_failure_reason_for_the_merge_queue_note(self):
        import io, contextlib
        m = self.load()
        m.sync = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("/rt: 62 GB free < 100 GB (OT_RT_MIN_FREE_GB)"))
        m.sync_alert = lambda *a, **k: None
        m.MQ = pathlib.Path(tempfile.mkdtemp())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            m.sync_guarded("", True, False)
        self.assertIn("SYNC FAILED RuntimeError: /rt: 62 GB free < 100 GB", out.getvalue())


class PruneRefs(unittest.TestCase):
    def load(self):
        return Guard.load(Guard())

    def fake_proc(self, procs):
        d = tempfile.mkdtemp()
        for pid, (cmd, cwd) in procs.items():
            os.makedirs(f"{d}/{pid}"); open(f"{d}/{pid}/cmdline", "wb").write(cmd.replace(" ", "\0").encode())
            if cwd: os.symlink(cwd, f"{d}/{pid}/cwd")
        return d

    def test_reference_text_has_cmdlines_script_bodies_and_the_admission_log(self):
        m = self.load(); t = tempfile.mkdtemp(); sc = t + "/launch.sh"; open(sc, "w").write("python3 /srv/x/rt/24c7347cc887/tools/autopilot/src_manifest.py delta-apply\n")
        lg = t + "/admit.log"; open(lg, "w").write("2026-11-17 unit1 mem 8G: bash /srv/x/rt/aaaaaaaaaaaa/tools/fleet/ot-run\n")
        proc = self.fake_proc({101: ("bash " + sc, None), 102: ("bash -c while pgrep -f x; do sleep 5; done; python3 /srv/x/rt/bbbbbbbbbbbb/tools/y.py", None), 103: ("sleep 1", t)})
        txt = m.live_reference_text(proc=proc, admit_logs=(lg,))
        for sha in ("24c7347cc887", "aaaaaaaaaaaa", "bbbbbbbbbbbb"):
            self.assertIn(sha, txt)                       # script body, admission log, armed waiter cmdline

    def test_prune_keeps_snapshots_named_by_a_live_script_or_waiter_and_the_last_three(self):
        m = self.load(); names = ["%012x" % i for i in range(1, 10)]
        d = pathlib.Path(tempfile.mkdtemp())
        for i, n in enumerate(names):
            (d / n).mkdir(); os.utime(d / n, (1000 + i, 1000 + i))
        os.symlink(names[-1], d / "current")
        sc = tempfile.mktemp(suffix=".sh"); open(sc, "w").write("run /srv/x/rt/%s/tools/z\n" % names[1])
        m.live_reference_text = lambda *a, **k: "bash " + sc + " " + open(sc).read()
        gone = m.prune_snapshots(d, keep=1, text="")
        self.assertNotIn(names[1], gone)                                          # named by the launch script body
        self.assertEqual({n for n in names[-3:]} & set(gone), set())               # OT_RT_KEEP=1 still keeps the newest three
        self.assertIn(names[0], gone)


def test_sync_checks_updated_hosts_but_not_deliberate_low_disk_skips(tmp_path):
    m = Guard.load(Guard())
    full = "a" * 40
    name = full[:12]
    m.RT = tmp_path
    m.log = lambda message: None
    m.git = lambda *args, **kwargs: full
    m.current = lambda: name
    m.materialize = lambda sha: tmp_path / name
    (tmp_path / f"{name}.manifest.json").write_text('{"files": {}}')

    def sync_hosts(name, previous, record):
        record("epyc8", False, True, "SKIP 46 GB free")
        record("epyc9", True, False, "ok")
        return ["epyc8:SKIP 46 GB free", "epyc9:ok"]

    def no_drift(files, hosts):
        assert hosts == ["epyc9"]
        return []

    m.sync_hosts = sync_hosts
    m.installed_diffs = no_drift
    assert m.sync(full) == 0
    assert "epyc8 SKIPPED (low disk) 46 GB free" in (tmp_path / "history.log").read_text()

    m.installed_diffs = lambda files, hosts: ["epyc9: installed ot-run differs"]
    assert m.sync(full) == 4


def test_hosts_are_pushed_in_parallel_with_one_result_line_each():
    """PARALLEL-SYNC-1119: four 0.4 s pushes finish in about 0.4 s, not 1.6 s; a failing host does not stop the others"""
    import importlib.machinery, importlib.util, os, time
    ld = importlib.machinery.SourceFileLoader("ots_par", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ot-tools-sync"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader("ots_par", ld)); ld.exec_module(m)
    lines = []
    m.log = lambda s: lines.append(s)
    def fake(h, name, prev):
        time.sleep(0.4)
        if h == "h3":
            raise RuntimeError("ssh refused")
        return (h != "h2"), ("SKIP low disk" if h == "h2" else "ok")
    t0 = time.time()
    notes = m.sync_hosts("abc", "", hosts=["h1", "h2", "h3", "h4"], fn=fake)
    assert time.time() - t0 < 1.0
    assert notes[0] == "h1:ok" and notes[1].startswith("h2:SKIP") and notes[2].startswith("h3:FAIL") and notes[3] == "h4:ok"
    assert sum(1 for l in lines if l.startswith(("h1:", "h2:", "h3:", "h4:"))) == 4


def test_one_push_per_host_at_a_time_second_waits_and_a_stuck_one_gives_up(tmp_path):
    """HOST-LOCK-1119: two threads pushing the same host never overlap; different hosts do; a held lock past the wait returns busy"""
    import importlib.machinery, importlib.util, os, threading, time
    ld = importlib.machinery.SourceFileLoader("ots_lock", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ot-tools-sync"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader("ots_lock", ld)); ld.exec_module(m)
    live, peak, lock = [], [0], threading.Lock()
    def inner(h, name, prev, flip, smoke):
        with lock:
            live.append(h); peak[0] = max(peak[0], live.count(h))
        time.sleep(0.3)
        with lock:
            live.remove(h)
        return True, "ok"
    ts = [threading.Thread(target=lambda: m.host_sync("hA", "n", "", lock_dir=tmp_path, _inner=inner)) for _ in range(3)]
    ts.append(threading.Thread(target=lambda: m.host_sync("hB", "n", "", lock_dir=tmp_path, _inner=inner)))
    [t.start() for t in ts]; [t.join(30) for t in ts]
    assert peak[0] == 1                                                     # never two pushes of hA at once
    import fcntl
    held = open(tmp_path / ".hostsync.hC.lock", "w"); fcntl.flock(held, fcntl.LOCK_EX)
    m.HOST_LOCK_WAIT_S = 1.2
    ok, note = m.host_sync("hC", "n", "", lock_dir=tmp_path, _inner=inner)
    assert not ok and note.startswith("busy")


def test_a_partial_dir_in_use_is_set_aside_not_refused(tmp_path):
    """MATERIALIZE-FRESH-1119"""
    import importlib.machinery, importlib.util, os
    ld = importlib.machinery.SourceFileLoader("ots_ma", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ot-tools-sync"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader("ots_ma", ld)); ld.exec_module(m)
    d = tmp_path / "abc123"; d.mkdir(); (d / "f").write_text("x")
    assert m.set_aside_partial(d, in_use_fn=lambda p: [], rt=tmp_path) is None and d.exists()        # unused: caller removes it as before
    st = m.set_aside_partial(d, in_use_fn=lambda p: [1234], rt=tmp_path)                              # in use: renamed aside, name is free again
    assert st is not None and st.name.startswith(".stale-abc123-") and (st / "f").exists() and not d.exists()
