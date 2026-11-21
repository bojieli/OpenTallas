"""ot-oom-age: youngest build processes get the highest oom_score_adj (killed first), old ones decay to 0."""
import importlib.machinery, importlib.util, os, pathlib, shutil, subprocess, sys, tempfile, time, unittest

P = str(pathlib.Path(__file__).with_name("ot-oom-age"))
loader = importlib.machinery.SourceFileLoader("ot_oom_age", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_oom_age", loader))
loader.exec_module(M)


def spawn_openroad(ignore_term=False):
    """a stand-in build process whose comm is `openroad` regardless of argv[0] (a renamed /bin/sleep is a coreutils multicall binary that refuses to run on some hosts)"""
    d = tempfile.mkdtemp(); exe = os.path.join(d, "openroad")
    open(exe, "w").write("#!%s\nimport signal, sys, time\n%ssys.stdout.write('ready\\n'); sys.stdout.flush()\ntime.sleep(120)\n" % (
        sys.executable, "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n" if ignore_term else ""))
    os.chmod(exe, 0o755)
    p = subprocess.Popen([exe, "60"], stdout=subprocess.PIPE, text=True)
    p.stdout.readline()
    time.sleep(0.3)     # start times have 10 ms resolution: keep `now` clearly after the start
    return p, d


class Age(unittest.TestCase):
    def test_target_decays_100_per_hour_to_zero(self):
        self.assertEqual([M.target_adj(s) for s in (0, 3599, 3600, 7200, 8 * 3600, 20 * 3600)], [800, 800, 700, 600, 0, 0])

    def test_only_adj_inside_0_800_is_managed(self):
        self.assertTrue(M.managed(0) and M.managed(800) and M.managed(300))
        self.assertFalse(M.managed(-999) or M.managed(900) or M.managed(1000))

    @unittest.skipIf(os.geteuid() != 0, "lowering oom_score_adj needs CAP_SYS_RESOURCE (root)")
    def test_dummy_pair_young_vs_aged(self):
        (a, _), (b, _) = spawn_openroad(), spawn_openroad()
        try:
            # raising own children above their current adj needs no privilege; lowering does, so start both at 800 and age one
            for p in (a, b):
                open(f"/proc/{p.pid}/oom_score_adj", "w").write("800")
            M.main(["--pid", str(a.pid), "--comm", "openroad", "--now-offset", "14400"])   # a looks 4 h old -> 400 (needs CAP_SYS_RESOURCE)
            M.main(["--pid", str(b.pid), "--comm", "openroad"])                              # b is new -> young band 520 + 10 per GB
            ja, jb = int(open(f"/proc/{a.pid}/oom_score_adj").read()), int(open(f"/proc/{b.pid}/oom_score_adj").read())
            self.assertGreaterEqual(jb, 520)
            self.assertEqual(ja, 400)
            self.assertGreater(int(open(f"/proc/{b.pid}/oom_score").read()), int(open(f"/proc/{a.pid}/oom_score").read()))
        finally:
            a.kill(); b.kill()


class Credit(unittest.TestCase):
    def test_item_key_strips_the_client_pid(self):
        self.assertEqual(M.item_key("dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-760500"), "dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536")
        self.assertIsNone(M.item_key(None))

    def test_resubmitted_job_keeps_the_age_of_its_first_attempt(self):
        first, now = {}, 100000.0
        self.assertEqual(M.credited_age(first, "job", 7200, now), 7200)              # first attempt: 2 h old
        later = now + 3000                                                           # killed, resubmitted: new process only 60 s old
        self.assertEqual(M.credited_age(first, "job", 60, later), 10200)             # credit continues (2 h 50 min), not 60 s
        self.assertEqual(M.target_adj(10200), 600)
        self.assertEqual(M.credited_age(first, None, 60, later), 60)                 # no key: process age

    def test_state_is_pruned_after_a_day(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "s.json")
        M.save_state(p, {"old": {"first": 0, "seen": 1000.0}, "new": {"first": 0, "seen": 90000.0}}, 100000.0)
        self.assertEqual(sorted(M.load_state(p)), ["new"])


class Stage(unittest.TestCase):
    def test_late_stages_get_the_lowest_score(self):
        drt = "openroad -exit /OpenROAD-flow-scripts/flow/scripts/detail_route.tcl -metrics x"
        self.assertEqual(M.stage_adj(drt, 800), 0)                                   # a new job already in DRT is the last victim
        self.assertEqual(M.stage_adj("openroad /x/scripts/fillcell.tcl", 700), 0)
        self.assertEqual(M.stage_adj("openroad /x/scripts/final_report.tcl", 500), 0)

    def test_grt_is_capped_and_early_stages_keep_the_age_value(self):
        grt = "openroad /OpenROAD-flow-scripts/flow/scripts/global_route.tcl"
        self.assertEqual(M.stage_adj(grt, 800), 300)
        self.assertEqual(M.stage_adj(grt, 100), 37)
        self.assertEqual(M.stage_adj(grt, 400), 150)                                   # order kept inside GRT
        self.assertEqual(M.stage_adj("openroad /x/scripts/global_place.tcl", 800), 800)
        self.assertEqual(M.stage_adj("openroad /x/scripts/detail_place.tcl", 600), 600)

    def test_ordering_young_early_first_then_grt_then_drt(self):
        order = sorted([("early_young", M.stage_adj("openroad global_place.tcl", 800)), ("early_old", M.stage_adj("openroad global_place.tcl", 200)),
                        ("grt_young", M.stage_adj("openroad /a/global_route.tcl", 800)), ("drt", M.stage_adj("openroad /a/detail_route.tcl", 800))], key=lambda x: -x[1])
        self.assertEqual([n for n, _ in order], ["early_young", "grt_young", "early_old", "drt"])


class Escalate(unittest.TestCase):
    def line(self, t, pid, comm, cmd):
        return f'{t} host earlyoom[1]: sending SIGTERM to process {pid} uid 0 "{comm}": oom_score 1200, oom_score_adj 800, VmRSS 5 MiB, cmdline "{cmd}"'

    def test_parse_keeps_first_sigterm_per_pid(self):
        txt = self.line(100.5, 7, "openroad", "openroad -x") + "\n" + self.line(110.5, 7, "openroad", "openroad -x") + "\nother line\n"
        self.assertEqual(M.parse_sigterms(txt), {7: (100.5, "openroad", "openroad -x")})

    def test_survivor_gets_one_sigkill_with_guards(self):
        p, d = spawn_openroad(ignore_term=True)     # ignores SIGTERM like the stuck victims, so only SIGKILL ends it
        try:
            now = time.time(); hz = os.sysconf("SC_CLK_TCK"); sent = []
            log = os.path.join(d, "kills.log"); cmd = open(f"/proc/{p.pid}/cmdline").read().replace("\0", " ").strip()
            t_old = now - 120; later = now + 100     # t_old predates the process (a reused pid); `later` makes a SIGTERM at `now` 100 s old
            # process started AFTER the logged SIGTERM (pid reused) -> no kill
            self.assertEqual(M.escalate({p.pid: (t_old, "openroad", cmd)}, now, hz, kill=lambda *a: sent.append(a), log=log), 0)
            # wrong comm / wrong cmdline -> no kill
            self.assertEqual(M.escalate({p.pid: (now, "yosys", cmd)}, later, hz, kill=lambda *a: sent.append(a), log=log), 0)
            self.assertEqual(M.escalate({p.pid: (now, "openroad", "other cmd")}, later, hz, kill=lambda *a: sent.append(a), log=log), 0)
            # SIGTERMed only 30 s ago -> not yet
            self.assertEqual(M.escalate({p.pid: (now, "openroad", cmd)}, now + 30, hz, kill=lambda *a: sent.append(a), log=log), 0)
            self.assertEqual(sent, [])
            # SIGTERM after the start, 100 s old, same comm+cmdline -> killed once; dry run sends nothing
            self.assertEqual(M.escalate({p.pid: (now, "openroad", cmd)}, later, hz, dry=True, kill=lambda *a: sent.append(a), log=log), 1)
            self.assertEqual(sent, [])
            self.assertEqual(M.escalate({p.pid: (now, "openroad", cmd)}, later, hz, log=log), 1)
            p.wait(timeout=5)
            self.assertEqual(p.returncode, -9)     # SIGKILL, not the ignored SIGTERM
            self.assertIn("SIGKILL", open(log).read())
            # gone now -> nothing more
            self.assertEqual(M.escalate({p.pid: (now, "openroad", cmd)}, later, hz, log=log), 0)
        finally:
            if p.poll() is None:
                p.kill()


class PlanBypass(unittest.TestCase):
    def test_markers_of_live_launchers_only(self):
        d = tempfile.mkdtemp()
        for n in (str(os.getpid()), "999999999"):
            open(f"{d}/plan.job.{n}", "w").close()
        open(f"{d}/other.file", "w").close()
        self.assertEqual(M.plan_pids(d), {str(os.getpid())})
        self.assertFalse(os.path.exists(f"{d}/plan.job.999999999"))        # dead launcher: marker removed

    def test_plan_key_from_the_scope_or_the_container_name(self):
        self.assertIsNone(M.plan_key(999999999, {}))
        import builtins
        real = builtins.open
        def fake(path, *a, **k):
            if str(path) == "/proc/4242/cgroup":
                import io
                return io.StringIO("0::/user.slice/user-1000.slice/user@1000.service/app.slice/oth-ubuntu-840192-1794698885.scope\n")
            return real(path, *a, **k)
        builtins.open = fake
        try:
            self.assertEqual(M.plan_key(4242, {}), "840192")
        finally:
            builtins.open = real

    @unittest.skipIf(os.geteuid() != 0, "-1000 needs root")
    def test_marked_job_process_is_set_to_minus_1000(self):
        p, d = spawn_openroad()
        try:
            open(f"{d}/x", "w").close()
            from unittest.mock import patch
            with patch.object(M, "plan_pids", lambda d=None: {"1"}), patch.object(M, "plan_key", lambda pid, names: "1"):
                M.main(["--pid", str(p.pid), "--comm", "openroad"])
            self.assertEqual(int(open(f"/proc/{p.pid}/oom_score_adj").read()), -1000)
        finally:
            p.kill()


class Victim(unittest.TestCase):
    GP = "openroad -exit /flow/scripts/global_place.tcl"
    GRT = "openroad -exit /flow/scripts/global_route.tcl"
    DRT = "openroad -exit /flow/scripts/detail_route.tcl"

    def test_young_early_jobs_rank_by_rss_and_small_ones_go_last(self):
        a = lambda gb: M.victim_adj(self.GP, 600, gb)
        self.assertLess(a(4.4), a(8.0)); self.assertLess(a(8.0), a(20.0)); self.assertLess(a(20.0), a(40.0))
        self.assertLessEqual(a(7.9), 599)                       # under ~8 GB: below every larger young job
        self.assertEqual(a(500.0), 799)                          # capped

    def test_young_beats_old_and_late_stages_keep_stage_protection(self):
        self.assertGreater(M.victim_adj(self.GP, 600, 1.0), M.victim_adj(self.GP, 4 * 3600, 60.0))   # any young before any old
        self.assertLessEqual(M.victim_adj(self.GP, 20 * 3600, 60.0), 0 + 0)
        self.assertEqual(M.victim_adj(self.DRT, 60, 30.0), 0)                                         # DRT / post-GRT: lowest
        self.assertEqual(M.victim_adj(self.GRT, 60, 30.0), 300)                                       # GRT: scaled, as STAGEADJ

    def test_stage_adj_is_back(self):
        self.assertEqual(M.stage_adj(self.DRT, 800), 0)
        self.assertEqual(M.stage_adj(self.GRT, 400), 150)
        self.assertEqual(M.stage_adj(self.GP, 700), 700)


class Guard(unittest.TestCase):
    def test_victim_is_the_largest_young_non_plan_process_and_never_a_protected_one(self):
        procs = [(1, "openroad", 564, 568, 4.4), (2, "openroad", 700, 728, 18.0), (3, "openroad", 0, 30, 45.0), (4, "yosys", 599, 608, 7.9),
                 (5, "openroad", -1000, 0, 90.0), (6, "python3", 800, 820, 20.0)]
        self.assertEqual(M.guard_victim(procs), 2)              # not the 4 GB one, not adj 0 / -1000 (late stage, plan), not a non-build comm
        # FABLE-FLOW-1555 A: the biggest frees the most; equal sizes -> the youngest (highest adj)
        big_old = [(1, "openroad", 120, 130, 40.0), (2, "openroad", 790, 800, 2.0), (3, "openroad", 700, 710, 21.0)]
        self.assertEqual(M.guard_victim(big_old), 3)            # FLEET-WATCH-2000: adj 120 = hours of sunk work, spared while a younger candidate exists
        self.assertEqual(M.guard_victim([(1, "openroad", 75, 80, 18.8), (2, "openroad", 150, 160, 24.0)]), 2)   # only old ones left: the largest still goes (the rail stays)
        tie = [(1, "openroad", 300, 310, 8.0), (2, "openroad", 790, 800, 8.1), (3, "openroad", 100, 110, 8.0)]
        self.assertEqual(M.guard_victim(tie), 2)
        self.assertIsNone(M.guard_victim([(3, "openroad", 0, 30, 45.0)]))

    def test_ancestor_fallback_finds_a_marked_launcher(self):
        self.assertEqual(M.plan_ancestor(os.getpid(), {str(os.getppid())}), str(os.getppid()))
        self.assertIsNone(M.plan_ancestor(os.getpid(), {"999999999"}))

    def test_guard_off_or_no_plan_job_kills_nothing(self):
        from unittest.mock import patch
        mem = lambda: {"MemAvailable": 10, "MemTotal": 1000}
        with patch.object(M, "plan_pids", lambda d=None: set()):
            self.assertEqual(M.guard(0.2, 5.0, kill=lambda *a: self.fail("killed"), sleep=lambda s: time.sleep(0.01), meminfo=mem), 0)
        with patch.object(M, "plan_pids", lambda d=None: {"1"}):
            self.assertEqual(M.guard(0.2, 0, kill=lambda *a: self.fail("killed"), sleep=lambda s: time.sleep(0.01), meminfo=mem), 0)
            hi = lambda: {"MemAvailable": 900, "MemTotal": 1000}
            self.assertEqual(M.guard(0.2, 5.0, kill=lambda *a: self.fail("killed"), sleep=lambda s: time.sleep(0.01), meminfo=hi), 0)



class WaiterAdj(unittest.TestCase):
    """WAITERADJ_1400: earlyoom killed 3-8 tiny ot-heavy / ssh / sleep wrappers (adj 200 = score 800) before any build"""

    def test_waiter_wrappers_get_a_low_adj_and_are_never_raised(self):
        self.assertEqual([M.waiter_adj(c, 200, 3) for c in ("ot-heavy", "ssh", "sleep", "timeout")], [-100] * 4)
        self.assertIsNone(M.waiter_adj("ot-heavy", -1000, 3))          # a plan job stays at -1000
        self.assertIsNone(M.waiter_adj("ot-heavy", -100, 3))
        self.assertIsNone(M.waiter_adj("ot-heavy", 200, 900))          # a big process is judged like any other
        self.assertIsNone(M.waiter_adj("openroad", 200, 3))
        self.assertIsNone(M.waiter_adj("python3", 200, 3))

if __name__ == "__main__":
    unittest.main()


def test_late_eco_containers_rank_late_stage():
    """FABLE-FLOW-1750 C: prd_run.sh containers (late ECO on the routed DB) get adj 0, so PLANGUARD (0 < adj) never picks them"""
    for n in ("prd-gen-i1-1782271", "prd-fin-4242", "prd-count-i1t-77", "prd-preclean-9"):
        assert M.late_eco_container(n)
    for n in (None, "", "dpkit-slice_station__t40-123", "otc-2068972-23088"):
        assert not M.late_eco_container(n)
    assert M.guard_victim([(1, "openroad", 0, 900, 14.5), (2, "openroad", 300, 400, 2.0)]) == 2


def test_victim_ident_names_unit_container_cwd_path():
    import importlib.machinery, importlib.util, os
    ld = importlib.machinery.SourceFileLoader("oomage_vi", os.path.join(os.path.dirname(__file__), "ot-oom-age"))
    sp = importlib.util.spec_from_loader("oomage_vi", ld); m = importlib.util.module_from_spec(sp); ld.exec_module(m)
    out = m.victim_ident(os.getpid(), {})
    assert out.startswith("unit ") and " container " in out and " cwd " in out and " path " in out
    assert m.victim_ident(2**30, {}) == "unit - container - cwd - path -"


def test_routed_final_signoff_inventory_requires_producer_label_and_signoff_name(monkeypatch):
    from types import SimpleNamespace

    out = (
        "a so_1762351_ff_64868 routed-final-signoff\n"
        "b so_1762351_tt_64868 \n"
        "c dpkit-probe-99 routed-final-signoff\n"
        "d prd-fin-4242\n"
    )
    monkeypatch.setattr(M.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=out))
    names, late = M.container_inventory()
    assert names == {"a": "so_1762351_ff_64868", "b": "so_1762351_tt_64868",
                     "c": "dpkit-probe-99", "d": "prd-fin-4242"}
    assert late == {"a"}
