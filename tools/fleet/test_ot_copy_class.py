"""COPY CLASS (COORD 11-24): a cross-host tree copy as an admitted, slotted, leased ot-run job; every other form is refused and every other job
keeps the ISOLATION step 3 guard as it was."""
import importlib.machinery, importlib.util, os, pathlib, subprocess, sys
import pytest
H = pathlib.Path(__file__).parent
sys.path.insert(0, str(H))
import ot_copy_class as C  # noqa: E402
import ot_lease  # noqa: E402


def load(n):
    l = importlib.machinery.SourceFileLoader("cc_" + n.replace("-", "_"), str(H / n))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(l.name, l)); l.exec_module(m)
    return m


L = load("ot-run-lane-declare")
S2 = "/srv/opentallas-scratch2/claude"
FORK, REPL = f"{S2}/rt/current/tools/fleet/ot-tree-fork", f"{S2}/rt/0123456789ab/tools/autopilot/src_manifest.py"
D, SRC, DST = f"{S2}/LANE-A/in", f"{S2}/kw45/qc_ev", f"{S2}/LANE-A/in/ev"
ENV = {"OT_LANE": "LANE-A"}


def fork(src=SRC, dst=DST, stage=f"epyc7:{SRC}", d=D, hosts="epyc11", tool=FORK, extra=(), head=(), pre=(), sh="epyc7"):
    return (["--mem", "8", "--hosts", hosts, "--dir", d] + (["--stage", stage] if stage else []) + list(head) + ["--"] + list(pre)
            + ["python3", "-I", tool, src, dst, "--src-host", sh] + list(extra))


def repl(tree=f"{D}/t", hosts="epyc7", to="epyc11", extra=()):
    return ["--mem", "8", "--hosts", hosts, "--dir", D, "--stage", f"epyc7:{tree}", "--", "python3", "-I", REPL, "replicate", tree, "--hosts", to] + list(extra)


def no(argv, text, env=ENV):
    with pytest.raises(C.Refused, match=text):
        C.parse(argv, env)


def test_accepts_the_two_forms(monkeypatch):
    j = C.parse(fork(pre=["env", "OT_TREE_FORK_STREAMS=12"], extra=["--jobs", "8"], head=["--disk", "80", "--threads", "4"]), ENV)
    assert (j["src_host"], j["src"], j["dst_host"], j["dst"], j["run_host"]) == ("epyc7", SRC, "epyc11", DST, "epyc11")
    r = C.parse(repl(extra=["--tar"]), ENV)
    assert (r["tool"], r["dst"], r["dst_host"], r["run_host"]) == ("replicate", f"{D}/t", "epyc11", "epyc7")
    monkeypatch.setenv("OT_LANE", "LANE-A")
    assert L.check(fork()) == [] and L.check(repl()) == []
    assert C.lane_dir_ok(f"{S2}/lane-a-run2/x", "LANE-A") and not C.lane_dir_ok(f"{S2}/lane-ab/x", "LANE-A")


def test_refuses_kw45_event_and_foreign_destinations():
    for d in (f"{S2}/kw45/ev/x", f"{S2}/kw45", f"{S2}/rt/current", f"{S2}/kv-plan-r6/bind", f"{S2}/LANE-B/in", f"{S2}", "/home/ubuntu/LANE-A"):
        no(fork(d=d, dst=d + "/y"), "not inside the lane dir")
    no(fork(dst=f"{S2}/kw45/ev"), "not inside --dir")
    no(fork(dst=f"{S2}/LANE-A/other"), "not inside --dir")
    no(fork(dst=D), "not inside --dir")
    no(fork(dst=f"{D}/../../kw45/ev"), "normalised")
    no(repl(tree=f"{S2}/kw45/ev"), "not inside --dir")


def test_refuses_undeclared_source():
    no(fork(src=f"{S2}/kw45/other"), "not the declared")
    no(fork(stage=None), "--stage is required")
    no(fork(stage=SRC), "exactly one")
    no(fork(stage=f"epyc7:{SRC},epyc7:{S2}/x/y"), "exactly one")
    no(fork(head=["--stage", f"epyc8:{SRC}"]), "twice")
    no(fork(sh="epyc9"), "src-host")
    no(fork(stage="epyc7:/home/ubuntu/x", src="/home/ubuntu/x"), "source is a tree")
    no(fork(hosts="epyc7"), "both on epyc7")
    no(repl(to="epyc11,epyc9"), "one host")
    no(repl(hosts="epyc9"), "where the tree is")


def test_refuses_other_commands_and_options():
    base = fork()
    i = base.index("--") + 1
    for c in (["rsync", "-a", SRC, DST], ["bash", "-c", f"python3 -I {FORK} {SRC} {DST}"], ["cp", "-a", SRC, DST],
              ["python3", FORK, SRC, DST, "--src-host", "epyc7"]):
        no(base[:i] + c, "python3 -I")
    no(fork(tool=f"{S2}/LANE-A/ot-tree-fork"), "only ot-tree-fork")
    no(fork(tool=f"{S2}/rt/current/tools/fleet/../../../x"), "only ot-tree-fork")
    no(fork(extra=["--materialize"]), "not allowed"); no(fork(extra=["--host", "epyc2"]), "not allowed")
    no(fork(extra=["; rm"]), "normalised"); no(fork(dst=f"{D}/$(id)"), "normalised")
    no(fork(pre=["env", "OT_TREE_COPY_SLOTS=9"]), "env sets only")
    no(fork(hosts="epyc11,epyc9"), "exactly one host")
    for h in (["--direct"], ["--crit"], ["--priority", "die"], ["--job", "/x"], ["--replicate", "/x"], ["--plan-job", "bind"]):
        no(fork(head=h), "a copy job takes only")
    r = repl(); r[r.index("replicate")] = "publish"
    no(r, "only replicate"); no(repl(extra=["--link-from", "x"]), "not allowed")


def test_refuses_missing_lease(tmp_path, monkeypatch):
    for k in C.NO_ENV:
        no(fork(), k, dict(ENV, **{k: "1"}))
    no(fork(), "OT_LANE", {})
    monkeypatch.setenv("OT_LEASE_DIR", str(tmp_path))
    j = C.parse(fork(), ENV)
    with pytest.raises(C.Refused, match="no live lease"):
        C.check_leases(j, "LANE-A/x", ot_lease.leases())
    for p in C.lease_list(j):
        ot_lease.take(p, "LANE-B/x")
    with pytest.raises(C.Refused, match="no live lease"):
        C.check_leases(j, "LANE-A/x", ot_lease.leases())                # another owner's lease is not this client's
    for p in C.lease_list(j)[:2]:
        ot_lease.take(p, "LANE-A/x")
    with pytest.raises(C.Refused, match=DST):
        C.check_leases(j, "LANE-A/x", ot_lease.leases())
    ot_lease.take(DST, "LANE-A/x")
    C.check_leases(j, "LANE-A/x", ot_lease.leases())


def test_host_checks_fail_closed():
    j = C.parse(fork(), ENV)
    good = {"epyc7": "OK " + SRC, "epyc11": "OK " + D}
    C.check_hosts(j, lambda h, c, a: good[h])
    for bad, t in (({"epyc7": ""}, "did not answer"), ({"epyc7": "NO x is not a directory here"}, "not a directory"), ({"epyc7": "OK /home/ubuntu/x"}, "outside"),
                   ({"epyc11": ""}, "did not answer"), ({"epyc11": "NO into event tree"}, "event tree"), ({"epyc11": f"OK {S2}/kw45/ev"}, "outside the lane dir")):
        with pytest.raises(C.Refused, match=t):
            C.check_hosts(j, lambda h, c, a: dict(good, **bad)[h])


def dst_probe(d, dst, roots=""):
    r = subprocess.run([sys.executable, "-I", "-c", C.DST_PY, str(H / "ot-tree-fork"), str(d), str(dst)], capture_output=True, text=True,
                       env=dict(os.environ, OT_EVENT_TREE_ROOTS=str(roots)))
    return r.stdout.strip() or r.stderr


def test_destination_probe_resolves_links_and_event_trees(tmp_path):
    d = tmp_path / "lane"; d.mkdir()
    ev = tmp_path / "kw45" / "ev"; ev.mkdir(parents=True)
    out = tmp_path / "out"; out.mkdir()
    assert dst_probe(d, d / "new") == "OK " + str(d)
    (d / "l").symlink_to(ev); (d / "o").symlink_to(out); (d / "have").mkdir()
    assert "event tree" in dst_probe(d, d / "l" / "x")
    assert "outside --dir" in dst_probe(d, d / "o" / "x")
    assert "exists" in dst_probe(d, d / "have")
    assert "not a directory" in dst_probe(tmp_path / "none", tmp_path / "none" / "x")
    (tmp_path / "dl").symlink_to(ev)
    assert "event tree" in dst_probe(tmp_path / "dl", tmp_path / "dl" / "x")
    assert "event tree" in dst_probe(d, d / "new", roots=tmp_path)
    ro = tmp_path / "ro"; ro.mkdir(); (ro / ".src-manifest.json").write_text("{}"); ro.chmod(0o555)
    try:
        assert "event tree" in dst_probe(ro, ro / "x")
    finally:
        ro.chmod(0o755)


def test_guard_unchanged_for_everything_else(monkeypatch):
    monkeypatch.setenv("OT_LANE", "LANE-A")
    for argv in (fork(stage=None), fork(stage=SRC, d=f"{S2}/LANE-A/in2"), fork(src=f"{S2}/kw45/other"), fork(d=f"{S2}/kw45/ev", dst=f"{S2}/kw45/ev/x"),
                 ["--mem", "8", "--dir", D, "--stage", f"epyc7:{SRC}", "--", "rsync", "-a", f"epyc7:{SRC}/", DST],
                 ["--mem", "8", "--dir", D, "--", "cat", SRC + "/a"]):
        assert L.check(argv), argv
    monkeypatch.delenv("OT_LANE")
    assert L.check(fork())
    assert not C.wanted(["--mem", "8", "--dir", D, "--stage", SRC, "--", "cat", "epyc7:/x"])   # only --stage values count


def test_ot_run_refuses_before_any_host_is_asked(tmp_path):
    e = {k: v for k, v in os.environ.items() if not k.startswith("OT_RUN_")}
    e.update(OT_LANE="LANE-A", OT_LEASE_DIR=str(tmp_path), HOME=str(tmp_path))
    for argv in (fork(d=f"{S2}/kw45/ev", dst=f"{S2}/kw45/ev/x"), fork(src=f"{S2}/kw45/o"), fork(extra=["--materialize"])):
        r = subprocess.run([sys.executable, str(H / "ot-run")] + argv, env=e, capture_output=True, text=True, timeout=60)
        assert r.returncode and "REFUSED (COPY CLASS)" in r.stderr, r.stderr
    e["OT_RUN_NO_LEASE"] = "1"
    r = subprocess.run([sys.executable, str(H / "ot-run")] + fork(), env=e, capture_output=True, text=True, timeout=60)
    assert r.returncode and "OT_RUN_NO_LEASE" in r.stderr
    assert not list(tmp_path.glob("*.json"))
