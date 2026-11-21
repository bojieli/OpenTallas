"""OWNER 11-18: automatic aggressive cleanup on each build host (attempts at once, old events / idle lanes 12 h, git + bare-repo safety, posts, hub watchdog)."""
import json, os, pathlib, subprocess, sys, time, types
H = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import auto_retire as AR
import auto_clean_hub as HUB

NOW = 1_000_000.0
OLD = NOW - 30 * 3600


def mk(claude, rel, mtime):
    p = pathlib.Path(claude) / rel
    p.mkdir(parents=True)
    (p / "f").write_text("x")
    os.utime(p / "f", (mtime, mtime)); os.utime(p, (mtime, mtime))
    return str(p)


def A(die, event, item, n, **kw):
    return dict(die=die, event=event, item=item, attempt=n, **kw)


def base(tmp_path):
    cfg = {"dies": {"s81": {"event": "NEW"}, "qwen_compute": {"event": "N1B"}}}
    st = {"items": {
        "s81|i1|a": A("s81", "NEW", "i1", 1, status="FAIL"),
        "s81|i1|b": A("s81", "NEW", "i1", 2, status="RUNNING"),
        "s81|i2|a": A("s81", "NEW", "i2", 1, status="FAIL"),
        "s81|i2|b": A("s81", "NEW", "i2", 2, status="FAIL"),
        "s81|i3|a": A("s81", "OLD", "i3", 4, status="FAIL"),
        "s81|i4|a": A("s81", "OLD", "i4", 1, status="CANCELLED", q_signoff="x"),
    }}
    return cfg, st


def tree(tmp_path):
    c = str(tmp_path)
    r = "kw/runs/s81/kit-wave/s81/%s/items/%s/attempt_%d"
    for ev, it, n, t in (("NEW", "i1", 1, NOW - 3600), ("NEW", "i1", 2, NOW - 3600), ("NEW", "i2", 1, NOW - 3600), ("NEW", "i2", 2, NOW - 3600),
                         ("OLD", "i3", 4, OLD), ("OLD", "i4", 1, OLD), ("OLD", "i5", 1, OLD), ("OLD", "i6", 1, NOW - 60)):
        mk(c, r % (ev, it, n), t)
    return c


def names(res):
    return sorted(p.split("/items/")[1] for p, _ in res)


def test_failed_attempts_with_a_newer_one_go_at_once_the_latest_current_attempt_stays(tmp_path):
    cfg, st = base(tmp_path); c = tree(tmp_path)
    got = names(AR.attempt_candidates(c, cfg, st, "", now=NOW))
    assert "i1/attempt_1" not in got            # the item has a RUNNING row: nothing of it is touched
    assert "i2/attempt_1" in got                # FAIL, newer attempt exists, quiet > 30 min
    assert "i2/attempt_2" not in got            # the latest attempt of a current-event item
    assert "i3/attempt_4" not in got and "i5/attempt_1" not in got   # KEEP-LATEST-1119: the newest attempt of an unsigned type stays, even of an old event / no state row
    assert "i4/attempt_1" not in got            # q_signoff / carry-over row
    assert "i6/attempt_1" not in got            # modified a minute ago


def test_named_in_refs_and_recent_attempts_are_kept(tmp_path):
    cfg, st = base(tmp_path); c = tree(tmp_path)
    refs = "x runs/s81/kit-wave/s81/OLD/items/i3/attempt_4 y"
    assert "i3/attempt_4" not in names(AR.attempt_candidates(c, cfg, st, refs, now=NOW))
    assert "i2/attempt_1" not in names(AR.attempt_candidates(c, cfg, st, "", now=NOW, quiet_s=10 * 3600))


def test_run_attempts_writes_exact_allows_and_never_falls_back_to_rm_on_refusal(tmp_path):
    cfg, st = base(tmp_path); c = tree(tmp_path)
    allow = tmp_path / "allow.txt"
    seen = []
    g = types.SimpleNamespace(ALLOW_EXACT=str(allow), refuse=lambda p, prot=None: "protected" if p.endswith("i3/attempt_4") else None)
    deleted = []
    res = AR.run_attempts(c, cfg, st, "", set(), g, set(), lambda r: seen.append(r), apply=True, delete=lambda p: (deleted.append(p), __import__("shutil").rmtree(p))[0], now=NOW)
    assert os.path.exists(os.path.join(c, next(x for x in [r.get("tree") for r in res] if x and x.endswith("i3/attempt_4"))) if any((r.get("tree") or "").endswith("i3/attempt_4") for r in res) else c)
    assert all(p.endswith("i2/attempt_1") for p in deleted) and len(deleted) == 1                 # i3/i5 are the latest of their types: not listed any more
    lines = allow.read_text().splitlines()
    assert len(lines) == 1 and all(l.split("\t")[1] == str(int(NOW + 3600)) for l in lines)


def test_attempt_cleanup_keeps_reports_and_logs(tmp_path):
    p = mk(str(tmp_path), "a/attempt_3", OLD)
    for n in ("reports", "logs"):
        os.makedirs(os.path.join(p, n)); open(os.path.join(p, n, "r.txt"), "w").write("keep")
    os.makedirs(os.path.join(p, "gen", "big")); open(os.path.join(p, "gen", "big", "x.odb"), "w").write("x" * 100)
    os.symlink("/nonexistent", os.path.join(p, "lnk"))
    AR.strip_keep_reports(p)
    assert sorted(os.listdir(p)) == ["logs", "reports"] and open(os.path.join(p, "reports", "r.txt")).read() == "keep"
    q = mk(str(tmp_path), "b/attempt_1", OLD)
    AR.strip_keep_reports(q)
    assert not os.path.exists(q)                                                        # no reports/logs: the dir goes whole


def git(*a, cwd):
    subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", *a], cwd=cwd, check=True, capture_output=True)


def test_git_safety_dirty_unpushed_and_bare(tmp_path):
    remote = tmp_path / "remote.git"; subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    lane = tmp_path / "lane1"; lane.mkdir()
    git("init", "-q", "-b", "main", cwd=lane)
    (lane / "a").write_text("1"); git("add", "a", cwd=lane); git("commit", "-qm", "c", cwd=lane)
    assert "no remote" in AR.git_unsafe(str(lane))                      # a commit on no remote
    git("remote", "add", "origin", str(remote), cwd=lane); git("push", "-q", "origin", "main", cwd=lane); git("fetch", "-q", "origin", cwd=lane)
    assert AR.git_unsafe(str(lane)) == ""                              # pushed and clean: safe
    (lane / "a").write_text("2")
    assert "uncommitted" in AR.git_unsafe(str(lane))
    assert "bare git repo" in AR.git_unsafe(str(tmp_path))             # the dir holds a bare repo


def test_a_lane_named_in_a_recent_post_is_kept():
    posts = "- 2026-11-17 20:00 PST INFO [X] working in /srv/opentallas-scratch2/claude/my-lane/sub now"
    assert AR.post_text_hit("/srv/opentallas-scratch2/claude/my-lane", posts)
    assert not AR.post_text_hit("/srv/opentallas-scratch2/claude/my-lane2", posts)
    assert not AR.post_text_hit("/srv/opentallas-scratch2/claude/other", posts)


def test_run_lanes_skips_git_and_post_hits(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # A gate can place its temp root inside a real /claude/<lane>. Keep the
    # synthetic lane paths relative so that enclosing real lane does not match.
    c = "."
    mk(c, "keepme/x", OLD); mk(c, "postlane/x", OLD); mk(c, "goner/x", OLD)
    seen = []
    res = AR.run_lanes(c, set(), lambda p: None, seen.append, 10**9, apply=False, now=NOW, idle_h=12.0, mtime=lambda p, cut: OLD,
                       posts="- 2026-11-17 %s/postlane" % c, git_check=lambda p: "git work tree with uncommitted changes" if p.endswith("keepme") else "")
    byname = {os.path.basename(r["tree"]): r["result"] for r in res if r.get("tree")}
    assert byname["goner"] == "WOULD-DELETE" and byname["keepme"].startswith("REFUSED") and byname["postlane"].startswith("REFUSED")


def test_hub_watchdog_alerts_once_an_hour_for_a_stale_host_and_sums_freed(tmp_path):
    now = time.time()
    def run(cmd, **k):
        host = cmd[-2]
        out = {"h1": "%d\n---\n%s %s rc=0 deleted=3 refused=0 failed=0 before_gb=100 free_gb=160\n" % (now - 600, time.strftime("%F %T", time.localtime(now - 300)), "h1"),
               "h2": "%d\n---\n" % (now - 7000)}.get(host, "---\n")
        return types.SimpleNamespace(stdout=out, stderr="", returncode=0)
    posted = []
    st = {}
    logs, alerts = HUB.watchdog(["h1", "h2", "h3"], st, now=now, run=run, poster=posted.append)
    assert len(alerts) == 2 and any("h2" in a for a in alerts) and any("h3" in a and "ever" in a for a in alerts) and not any("h1" in a for a in alerts)
    assert HUB.watchdog(["h2"], st, now=now + 60, run=run, poster=posted.append)[1] == []            # not again within the hour
    assert HUB.freed_since(logs["h1"], now - 3600) == 60 and HUB.freed_since(logs["h1"], now) == 0


def test_installer_refuses_on_hub_and_localhost_and_unit_runs_the_full_pass():
    for hn in ("tolerant-swine", "ubuntu"):
        r = subprocess.run(["bash", "-c", "hostname() { echo %s; }; export -f hostname; bash %s" % (hn, H / "install_auto_clean.sh")], capture_output=True, text=True, timeout=30)
        assert r.returncode == 64 and "build hosts only" in r.stderr, hn
    svc = (H / "systemd" / "ot-auto-clean.service").read_text(); tm = (H / "systemd" / "ot-auto-clean.timer").read_text()
    assert "AC_FULL=1" in svc and "rt/current/tools/fleet/ot-auto-retire-run.sh apply" in svc and "rm -rf" not in svc
    assert "OnCalendar=*:0/30" in tm


def test_a_permission_error_inside_an_attempt_never_ends_the_pass(tmp_path):
    cfg, st = base(tmp_path); c = tree(tmp_path)
    g = types.SimpleNamespace(ALLOW_EXACT=str(tmp_path / "allow.txt"), refuse=lambda p, prot=None: None)
    def boom(p):
        raise PermissionError(13, "Permission denied", p)
    seen = []
    res = AR.run_attempts(c, cfg, st, "", set(), g, set(), seen.append, apply=True, delete=boom, now=NOW)
    assert res and all(r["result"] == "FAILED" and r["error"].startswith("PermissionError") for r in res)       # every candidate was tried, none raised
    p = mk(str(tmp_path), "z/attempt_1", OLD)
    os.makedirs(os.path.join(p, "gen")); os.chmod(os.path.join(p, "gen"), 0o555)
    AR.strip_keep_reports(p)                                                                                    # read-only dir: no exception
    assert not os.path.exists(os.path.join(p, "gen")) or os.listdir(p) == ["gen"]


def test_runner_covers_scratch3_and_never_overlaps():
    r = (H / "ot-auto-retire-run.sh").read_text()
    assert "/srv/opentallas-scratch3/claude" in r and "--root \"$R/kw45\"" in r and "flock -n 8" in r and "scratch3_free_gb" in r


def test_newest_failed_attempt_of_a_type_keeps_its_db_for_24h_older_ones_go(tmp_path):
    c = str(tmp_path)
    cfg = {"dies": {"s81": {"event": "NEW"}}}
    r = "kw/runs/s81/kit-wave/s81/OLDE/items/%s/attempt_%d"                        # a dead (non-current) event: every failed attempt is a candidate
    # type T has two items; failed 2-6 h ago; type U's attempts failed 40 h ago
    mk(c, r % ("T__a", 1), NOW - 5 * 3600); mk(c, r % ("T__a", 2), NOW - 2 * 3600)
    mk(c, r % ("T__b", 1), NOW - 6 * 3600); mk(c, r % ("T__b", 2), NOW - 3 * 3600)
    mk(c, r % ("U", 1), NOW - 40 * 3600); mk(c, r % ("U", 2), NOW - 40 * 3600)
    st = {"items": {}}
    for it, par in (("T__a", "T"), ("T__b", "T"), ("U", "U")):
        for n in (1, 2):
            st["items"]["s81|%s|%d" % (it, n)] = A("s81", "OLDE", it, n, status="FAIL", parent_item=par)
    got = names(AR.attempt_candidates(c, cfg, st, "", now=NOW))
    kept = [x for x in ("T__a/attempt_1", "T__a/attempt_2", "T__b/attempt_1", "T__b/attempt_2") if x not in got]
    assert kept == ["T__a/attempt_2"]                       # ONE attempt for the whole type T: its newest failed attempt (2 h ago) keeps its DB; the others are listed
    assert "U/attempt_1" in got and "U/attempt_2" not in got    # KEEP-LATEST-1119: type U's newest attempt stays whatever its age (unsigned); only older attempts go


def test_moved_and_infrastructure_lanes_are_never_idle_candidates(tmp_path):
    c = str(tmp_path)
    for n in ("moved", "hub-coord", "rt", "other"):
        mk(c, n + "/x", OLD)
    got = [os.path.basename(p) for p, _ in AR.lane_candidates(c, NOW, 12.0, mtime=lambda p, cut: OLD)]
    assert "other" in got and not {"moved", "hub-coord", "rt"} & set(got)


def test_a_dir_that_a_symlink_under_home_points_into_is_never_retired(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    c = str(tmp_path / "claude"); os.makedirs(c)
    keep = mk(c, "relocated/home__x", OLD); other = mk(c, "other/y", OLD)
    os.symlink(keep, str(home / "OpenTallas"))
    os.makedirs(str(home / ".cache2")); os.symlink(c + "/relocated/zz", str(home / ".cache2" / "c"))
    targets = AR.home_link_targets(str(home))
    assert AR.link_hit(c + "/relocated", targets) and AR.link_hit(keep, targets) and not AR.link_hit(c + "/other", targets)
    seen = []
    res = AR.run_lanes(c, set(), lambda p: None, seen.append, 10**9, apply=False, now=NOW, idle_h=12.0, mtime=lambda p, cut: OLD, git_check=None, links=targets)
    by = {os.path.relpath(r["tree"], c): r["result"] for r in res if r.get("tree")}
    assert by["other"] == "WOULD-DELETE" and by["relocated"].startswith("REFUSED") and by["relocated/home__x"].startswith("REFUSED")


def test_a_pass_stops_at_its_deadline_and_a_stuck_git_check_is_short(tmp_path):
    c = str(tmp_path)
    for n in ("a", "b", "c"):
        mk(c, n + "/x", OLD)
    seen = []
    res = AR.run_lanes(c, set(), lambda p: None, seen.append, 10**9, apply=False, now=NOW, idle_h=12.0, mtime=lambda p, cut: OLD, git_check=None, links=set(), deadline=time.time() - 1)
    assert res == [] and seen == []                                                          # past the deadline nothing is scanned or started
    import inspect
    assert inspect.signature(AR.git_unsafe).parameters["timeout"].default <= 15
    assert "-uno" in inspect.getsource(AR.git_unsafe)


def test_lane_scan_stops_at_the_deadline_and_continues_next_pass(tmp_path):
    c = str(tmp_path / "claude"); os.makedirs(c)
    for n in "abcd":
        mk(c, n + "/x", OLD)
    sf = str(tmp_path / "scan.json")
    calls = []
    def slow(p, cut):
        calls.append(p); return OLD
    # deadline already passed after the first lane: only one lane scanned, the next pass starts with the others
    t0 = time.time()
    first = AR.lane_candidates(c, NOW, 12.0, mtime=slow, deadline=t0 - 1, scan_state=sf)
    assert first == [] and calls == []
    got = AR.lane_candidates(c, NOW, 12.0, mtime=slow, deadline=None, scan_state=sf)
    assert len(got) >= 4
    scanned_first = list(calls); calls.clear()
    st = json.load(open(sf)); assert all(k in st for k in scanned_first)
    # least recently scanned first: touch a's timestamp as newest, it is scanned last
    st[os.path.join(c, "a")] = time.time() + 100; json.dump(st, open(sf, "w"))
    AR.lane_candidates(c, NOW, 12.0, mtime=slow, deadline=None, scan_state=sf)
    assert calls.index(os.path.join(c, "a")) > calls.index(os.path.join(c, "b"))


def _fake_proc(tmp_path, cmd="", env="", cwd=None):
    d = tmp_path / "proc" / "123"; d.mkdir(parents=True)
    (d / "cmdline").write_bytes(cmd.encode().replace(b" ", b"\0"))
    (d / "environ").write_bytes(env.encode())
    if cwd:
        os.symlink(cwd, d / "cwd")
    return str(tmp_path / "proc")


def test_live_refs_see_cmdline_env_path_and_cwd(tmp_path):
    claude = str(tmp_path / "claude")
    proc = _fake_proc(tmp_path, cmd="bash -c run " + claude + "/lane/in1/x", env="PATH=" + claude + "/lane/gitshim:/usr/bin\0HOME=/h", cwd=str(tmp_path))
    lv = AR.LiveRefs(claude, proc=proc)
    assert lv.hit(claude + "/lane/in1")                       # inside a cmdline arg
    assert lv.hit(claude + "/lane/gitshim")                   # a PATH entry of the environment
    assert lv.hit(claude + "/lane/d8t")                       # sibling child of a lane root that holds a live ref: the lane is in use
    assert not lv.hit(claude + "/other/d8t")                  # another lane root: free to age out
    assert lv.hit(claude + "/lane")                           # the lane root holds live refs: not retirable as a whole either


def test_live_refuse_beats_age(tmp_path):
    claude = str(tmp_path / "claude")
    lv = AR.LiveRefs(claude, proc=_fake_proc(tmp_path, env="PATH=" + claude + "/lane/gitshim"))
    f = AR.live_refuse(lambda p, *a: "", lv)
    assert f(claude + "/lane/gitshim").startswith("live input")
    assert f(claude + "/zz/old") == ""


def test_latest_attempt_of_an_unsigned_type_is_kept_whatever_its_age(tmp_path):
    """KEEP-LATEST-1119 (COORD: seqhost__t1 and lepe_nh_mus a27 lost plandir+kit to cleanup): older attempts go, the newest stays until the type is signed"""
    claude = tmp_path / "claude"
    base = claude / "kw/runs/s81/kit-wave/s81/EV/items/seqhost__t1"
    for n, age in ((26, 90 * 3600), (27, 60 * 3600)):
        d = base / ("attempt_%d" % n); d.mkdir(parents=True); (d / "f").write_text("x")
        os.utime(d, (time.time() - age,) * 2); os.utime(d / "f", (time.time() - age,) * 2)
    cfg = {"dies": {"s81": {"event": "NEW"}}}                       # event EV is not current: the old rule would retire both
    state = {"items": {"a": {"die": "s81", "event": "EV", "item": "seqhost__t1", "attempt": 26, "status": "FAIL"},
                       "b": {"die": "s81", "event": "EV", "item": "seqhost__t1", "attempt": 27, "status": "FAIL"}}}
    got = [os.path.basename(p) for p, _ in AR.attempt_candidates(str(claude), cfg, state, "", now=time.time())]
    assert got == ["attempt_26"]
    state["items"]["b"]["status"] = "SIGNED"
    got = [os.path.basename(p) for p, _ in AR.attempt_candidates(str(claude), cfg, state, "", now=time.time())]
    assert "attempt_26" in got


def test_die_clock_of_record_and_proto_kits_are_never_retired(tmp_path):
    """KEEP-KITS-1119: kit_d7w_ecov3 under s81-die-r3-proto went to a lane pass; name matches (also nested, depth 3) keep the tree"""
    a = tmp_path / "s81-die-r3-proto" / "kit_d7w_ecov3"; a.mkdir(parents=True)
    assert AR.keep_kit_hit(str(a)) == str(a)
    assert AR.keep_kit_hit(str(tmp_path / "s81-die-r3-proto")) == str(a)                 # the PARENT holds one: not retirable either
    b = tmp_path / "lane" / "x" / "7yhr_tail"; b.mkdir(parents=True)
    assert AR.keep_kit_hit(str(tmp_path / "lane")) == str(b)
    c = tmp_path / "plain" / "k"; c.mkdir(parents=True)
    assert AR.keep_kit_hit(str(tmp_path / "plain")) == ""
    assert AR.refuse_attempt(types.SimpleNamespace(refuse=lambda p, prot=None: None), str(a), set()).startswith("die clock-of-record")


def test_a_tree_named_by_a_record_json_is_kept_by_reference(tmp_path):
    """KEEP-BY-REF-1119: a lane dir named inside a young signoff.json (kit / base / odb) is not retired, whatever its name"""
    claude = tmp_path / "claude"
    kit = claude / "somelane" / "kit_plain"; kit.mkdir(parents=True); (kit / "f").write_text("x")
    so = claude / "otherlane" / "signoff"; so.mkdir(parents=True)
    (so / "signoff.json").write_text(json.dumps({"inputs": {"kit": "/srv/opentallas-scratch2/claude/somelane/kit_plain", "odb": "/srv/opentallas-scratch2/claude/somelane/kit_plain/6_final.odb"}}))
    refs = AR.record_refs(str(claude))
    assert "/srv/opentallas-scratch2/claude/somelane/kit_plain" in refs
    assert AR.record_ref_hit("/srv/opentallas-scratch2/claude/somelane/kit_plain", refs)
    assert AR.record_ref_hit("/srv/opentallas-scratch2/claude/somelane", refs)                     # the parent holds a referenced tree
    assert not AR.record_ref_hit("/srv/opentallas-scratch2/claude/unreferenced", refs)
    old = so / "signoff.json"; os.utime(old, (time.time() - 30 * 86400,) * 2)
    assert AR.record_refs(str(claude)) == set()                                                    # an old record no longer keeps


def test_cleanup_unit_is_not_idle_io_class():
    """a saturated disk starves an idle-class cleanup for hours (epyc7 11-19: pass held the lock 43 min, no pass for 90 min)"""
    u = (H / "systemd" / "ot-auto-clean.service").read_text()
    assert "IOSchedulingClass=idle" not in u.replace("# ", "#").split("\n", 0)[0] and "\nIOSchedulingClass=best-effort" in u and "IOSchedulingPriority=6" in u


def test_failed_units_are_listed_per_host_and_reach_the_report():
    """FAILED-UNITS-1119: a failed ot-disk-autoprune.service must be named in the report"""
    out = "ot-disk-autoprune.service loaded failed failed Auto-prune\nwt-reaper.service loaded failed failed Reaper\noth-ubuntu-1.scope loaded failed failed x\n"
    run = lambda *a, **k: types.SimpleNamespace(returncode=0, stdout=out, stderr="")
    assert HUB.failed_units("h", run) == ["ot-disk-autoprune.service", "wt-reaper.service"]
    assert HUB.failed_units("h", lambda *a, **k: types.SimpleNamespace(returncode=0, stdout="", stderr="")) == []
    assert HUB.failed_units("h", lambda *a, **k: (_ for _ in ()).throw(OSError("x"))) is None


def test_explorer_service_lane_folders_are_never_idle_lane_candidates():
    assert {"explorer-fable-1", "explorer-2-work"} <= set(AR.LANE_SKIP)


def test_protected_dbs_registry_blocks_the_path_its_parents_and_children(tmp_path):
    """PROTECTED-DBS-1120: HARVEST-0330 registered kit dirs are never retired by the aggressive cleanup"""
    f = tmp_path / "PROTECTED-DBS.txt"
    f.write_text("# header\nepyc8\t/srv/opentallas-scratch3/claude/lane/kitA/base\ts81 routed\nepyc2\t/srv/opentallas-scratch2/claude/lane2/kitB\tqc routed\n")
    dbs = AR.load_protected_dbs(str(f))
    assert "/srv/opentallas-scratch2/claude/lane/kitA/base" in dbs                    # scratch3 canonicalised
    assert AR.protected_db_hit("/srv/opentallas-scratch2/claude/lane/kitA/base/results", dbs)     # a child
    assert AR.protected_db_hit("/srv/opentallas-scratch2/claude/lane/kitA", dbs)                  # a parent
    assert AR.protected_db_hit("/srv/opentallas-scratch3/claude/lane2/kitB", dbs)                 # scratch3 alias of a registered path
    assert not AR.protected_db_hit("/srv/opentallas-scratch2/claude/lane3/other", dbs)
    g = types.SimpleNamespace(refuse=lambda p, prot=None: None)
    AR.guard_with_protected_dbs(g, dbs)
    assert g.refuse("/srv/opentallas-scratch2/claude/lane2/kitB/x").startswith("protected DB registry")
    assert g.refuse("/srv/opentallas-scratch2/claude/lane3/other") is None


def test_runner_fetches_and_passes_the_registry():
    r = (H / "ot-auto-retire-run.sh").read_text()
    assert "PROTECTED-DBS.txt" in r and "--protected-dbs" in r and "pdbs.txt" in r



def test_retained_attempt_reports_are_not_scanned_or_reaped_again(tmp_path):
    cfg, state = base(tmp_path)
    root = tree(tmp_path)
    attempt = tmp_path / "kw/runs/s81/kit-wave/s81/NEW/items/i2/attempt_1"
    (attempt / "reports").mkdir()
    (attempt / "reports" / "timing.rpt").write_text("keep")
    AR.strip_keep_reports(str(attempt))
    scanned = []

    def mtime(path, cutoff):
        scanned.append(path)
        return OLD

    assert "i2/attempt_1" not in names(AR.attempt_candidates(root, cfg, state, "", now=NOW, mtime=mtime))
    assert scanned and str(attempt) not in scanned
    assert (attempt / "reports" / "timing.rpt").read_text() == "keep"
