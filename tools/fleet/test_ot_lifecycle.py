#!/usr/bin/env python3
"""Fixture test for ot-lifecycle plan/apply: positive controls (retained paths stay KEEP) and negative controls (a row added
after the plan stops the apply); hold expiry; cited older attempts; report-only signed trim."""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
LC, TOOL = os.path.join(HERE, "ot-lifecycle.py"), os.path.join(HERE, "ot-autoclean.py")
OLD = time.time() - 72 * 3600


def write(p, n=4096, old=True):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write(os.urandom(n))
    if old:
        os.utime(p, (OLD, OLD))


def kit(d):
    b = f"{d}/run/results/asap7/d/base"
    for n in ("2_1_floorplan.odb", "2_floorplan.odb", "3_3_place_gp.odb", "3_place.odb", "4_1_cts.odb", "4_cts.odb",
              "5_route.odb", "6_final.odb", "6_final.spef"):
        write(f"{b}/{n}", 8192)
    write(f"{d}/run/objects/lib.lib", 8192)
    write(f"{d}/run/logs/asap7/d/base/1.log", 4096)
    write(f"{d}/config.mk", 200)


def run_fixture(W):
    global ROOT
    ROOT = os.path.join(W, "x/claude")
    os.makedirs(ROOT)
    kit(f"{ROOT}/dead-aa/kit1")
    write(f"{ROOT}/dead-aa/.keep", 0)
    os.utime(f"{ROOT}/dead-aa/.keep", (OLD, OLD))
    kit(f"{ROOT}/dead-bb/kit2")
    write(f"{ROOT}/dead-bb/.keep", 0, old=False)
    kit(f"{ROOT}/dead-cc/kit3")
    kit(f"{ROOT}/dead-dd/kit4")
    kit(f"{ROOT}/dead-ee/kit5")
    write(f"{ROOT}/dead-ee/kit5/signoff/signoff.json", 10)
    with open(f"{ROOT}/dead-ee/kit5/signoff/signoff.json", "w") as fh:
        json.dump({"verdict": "SIGNED", "inputs": {"odb": f"{ROOT}/dead-ee/kit5/run/results/asap7/d/base/6_final.odb"}}, fh)
    write(f"{ROOT}/dead-ee/kit5/ARCHIVED.json", 10)
    kit(f"{ROOT}/dead-ff/kit6")
    write(f"{ROOT}/dead-ff/kit6/run/logs/young.log", 10, old=False)
    kit(f"{ROOT}/die-s81-81/kit7")
    with open(f"{ROOT}/die-s81-81/kit7/config.mk", "w") as fh:      # a live lane file names a dead lane's kit
        fh.write(f"export X = {ROOT}/dead-ll/kit10/run\n")
    os.utime(f"{ROOT}/die-s81-81/kit7/config.mk", (OLD, OLD))
    kit(f"{ROOT}/dead-ll/kit10")
    kit(f"{ROOT}/dead-mm.old-kw37-1/kit11")          # a renamed tree is skipped whole (holds are keyed by path)
    kit(f"{ROOT}/dead-gg/kit-wave/s81/p/items/it/attempt_1/gen/it")
    write(f"{ROOT}/dead-hh/loose/file.bin", 4096)
    # incident 11-09: a bind tree reached only through the wave's kit_rtl script and a symlink (bind of record), and one only through a kit record
    write(f"{ROOT}/dead-bt/emit/bind/rtl/top.sv", 64)
    write(f"{ROOT}/dead-bt/emit/bind/rtl/sib.sv", 64)
    os.makedirs(f"{ROOT}/dead-lk/kvov")
    os.symlink(f"{ROOT}/dead-bt/emit/bind", f"{ROOT}/dead-lk/kvov/bind")
    write(f"{ROOT}/dead-sc/kit_rtl_x.sh", 1)
    with open(f"{ROOT}/dead-sc/kit_rtl_x.sh", "w") as fh:
        fh.write(f"python3 bind.py kit-rtl --bind-out {ROOT}/dead-lk/kvov/bind\n")
    os.utime(f"{ROOT}/dead-sc/kit_rtl_x.sh", (OLD, OLD))
    write(f"{ROOT}/dead-nr/src/a.sv", 64)
    write(f"{ROOT}/dead-nr/src/b.sv", 64)
    write(f"{ROOT}/dead-kr/u/rtl/kit_rtl.json", 1)
    with open(f"{ROOT}/dead-kr/u/rtl/kit_rtl.json", "w") as fh:
        json.dump({"sources": [f"{ROOT}/dead-nr/src/a.sv"]}, fh)
    os.utime(f"{ROOT}/dead-kr/u/rtl/kit_rtl.json", (OLD, OLD))
    write(f"{ROOT}/dead-unref/tree/f.bin", 4096)
    # older attempt cited by a signed record elsewhere: whole attempt stays even though it is not the latest
    kit(f"{ROOT}/dead-jj/kit-wave/s81/p/items/it2/attempt_1/gen/it2")
    kit(f"{ROOT}/dead-jj/kit-wave/s81/p/items/it2/attempt_3/gen/it2")
    write(f"{ROOT}/dead-kk/rec/signoff/signoff.json", 10)
    with open(f"{ROOT}/dead-kk/rec/signoff/signoff.json", "w") as fh:
        json.dump({"verdict": "SIGNED", "inputs": {"odb": f"{ROOT}/dead-jj/kit-wave/s81/p/items/it2/attempt_1/gen/it2/run/results/asap7/d/base/6_final.odb"}}, fh)
    write(f"{ROOT}/dead-ii/kit9/keepme.txt", 20)
    kit(f"{ROOT}/dead-rr/dead-word-unit")            # a bare name mention of a dead lane's kit holds nothing
    kit(f"{ROOT}/dead-tt/sub/kit15")
    write(f"{ROOT}/dead-tt/tools/flow.py", 4096)     # tool tree below lane level: stays, as the apply recheck demands
    # live wave config names paths in a dead lane, older than every hold window
    write(f"{ROOT}/dead-wv/wave/src_x/rtl.v", 4096)
    write(f"{ROOT}/dead-wv/wave/plan/p.json", 4096)
    write(f"{ROOT}/dead-wv/wave/plan/sibling.json", 4096)
    write(f"{ROOT}/dead-wv/wave/other/x.bin", 4096)
    write(f"{ROOT}/dead-xy/sub/c.json", 4096)        # one level below the lane: the named file holds its directory
    write(f"{ROOT}/dead-xy/sub/d.json", 4096)
    write(f"{ROOT}/dead-xz/a.json", 4096)            # directly in the lane root: the lane is not held by it
    write(f"{ROOT}/dead-xz/b.bin", 4096)
    kit(f"{ROOT}/dead-wv/wr/kit-wave/s81/p/items/it3/attempt_1/gen/it3")
    kit(f"{ROOT}/dead-wv/wr/kit-wave/s81/p/items/it3/attempt_3/gen/it3")
    write(f"{ROOT}/dead-wv/wr/kit-wave/s81/p/bind_a", 4096)
    for d in ("dead-lo/sub/repo.git", "dead-lp/repo.git"):         # repos without a .git entry
        os.makedirs(f"{ROOT}/{d}/objects"); os.makedirs(f"{ROOT}/{d}/refs")
        write(f"{ROOT}/{d}/HEAD", 40)
    write(f"{ROOT}/dead-lo/sub/other.bin", 4096)
    kit(f"{ROOT}/dead-hh2/tkm")                      # standing COORD hold
    kit(f"{ROOT}/dead-pp/unit1")                     # archived cited unit: only cited files and record names stay
    with open(f"{ROOT}/dead-pp/unit1/ARCHIVED.json", "w") as fh:
        json.dump({"archive": "/archive/x", "verify": "sha256 ok"}, fh)
    os.utime(f"{ROOT}/dead-pp/unit1/ARCHIVED.json", (OLD, OLD))
    write(f"{ROOT}/dead-qq/rec/signoff/signoff.json", 10)
    with open(f"{ROOT}/dead-qq/rec/signoff/signoff.json", "w") as fh:
        json.dump({"verdict": "SIGNED", "inputs": {"odb": f"{ROOT}/dead-pp/unit1/run/results/asap7/d/base/6_final.odb"}}, fh)
    kit(f"{ROOT}/dead-nn/kit12")                     # read-only dir inside: rm -rf would stop half way, so the folder is not started
    os.chmod(f"{ROOT}/dead-nn/kit12/run/objects", 0o555)
    kit(f"{ROOT}/dead-oo/kit13")                     # lane goes live between plan and apply: recheck must skip the row
    # snapshot
    snap = os.path.join(W, "snap")
    os.makedirs(snap)
    with open(f"{snap}/protected.tsv", "w") as fh:
        fh.write(f"{ROOT}/dead-cc/kit3\tfixture\n")
        for i in range(120):
            fh.write(f"/srv/none/claude/lane/x{i}\tpad\n")
    json.dump({"created": time.time(), "created_h": "now"}, open(f"{snap}/meta.json", "w"))
    json.dump({"paths": [], "words": []}, open(f"{snap}/queue.json", "w"))
    json.dump({"attempts": {}, "latest": {f"fix:{ROOT}/dead-jj/kit-wave/s81/p/items/it2": 3, f"fix:{ROOT}/dead-wv/wr/kit-wave/s81/p/items/it3": 3}, "keep": [], "current_di": {}, "created": time.time(), "source": "fix"},
              open(f"{snap}/kitwave.json", "w"))
    life = {"created": time.time(), "live": ["DIE-S81-81"], "lane_last": {},
            "paths48": [f"{ROOT}/dead-dd/kit4"], "words48": ["dead-word-unit"],
            "protected_full": [["fix", f"{ROOT}/dead-cc/kit3", "fixture"]],
            "coord_holds": [{"pattern": "dead-hh2/tkm", "lane": "X", "why": "open"}],
            "kit_union": [], "lane_mentions24": ["dead-word-unit"], "mention_paths24": [],
            "wave_paths": [f"{ROOT}/dead-sc/kit_rtl_x.sh", f"{ROOT}/dead-wv/wave/src_x", f"{ROOT}/dead-wv/wave/plan/p.json", f"{ROOT}/dead-wv/wr", f"{ROOT}/dead-xy/sub/c.json", f"{ROOT}/dead-xz/a.json"]}
    json.dump(life, open(f"{W}/life.json", "w"))
    out = f"{W}/out"
    r = subprocess.run([sys.executable, "-I", LC, "plan", "--tool", TOOL, "--host", "fix", "--lifesnap", f"{W}/life.json", "--out", out,
                        "--state", f"{W}/state", "--snapshot", snap, "--docker", "", "--roots", ROOT], capture_output=True, text=True, timeout=600)
    print(r.stdout[-1500:], r.stderr[-1500:])
    assert r.returncode == 0
    mf = sorted(f for f in os.listdir(out) if f.startswith("PLAN-"))[-1]
    rows = {}
    for ln in open(f"{out}/{mf}").read().splitlines()[1:]:
        c = ln.split("\t")
        rows[c[0].replace(ROOT + "/", "")] = (c[1], c[2])
    for k, v in sorted(rows.items()):
        print(f"{k:50s} {v[0]:26s} {v[1]}")
    expect = {
        "dead-mm.old-kw37-1": ("KEEP-excluded", "KEEP"),
        "dead-nn/kit12": ("KEEP-not-deletable", "KEEP"),
        "dead-oo/kit13": ("DEL-L4-KIT", "DELETE"),
        "dead-ll/kit10": ("KEEP-referenced", "KEEP"),      # positive control of the reference scan
        "dead-rr/dead-word-unit": ("DEL-L4-KIT", "DELETE"),
        "dead-tt/tools": ("KEEP-excluded", "KEEP"),
        "dead-lo/sub": ("KEEP-git-inside", "KEEP"),                         # a loose dir holding a repo is not a LOOSE delete
        "dead-lp/repo.git": ("KEEP-git-error", "KEEP"),                     # a bare repo gets the git check, not a LOOSE row
        "dead-hh2/tkm": ("KEEP-coord-hold", "KEEP"),
        "dead-xy/sub": ("KEEP-wave-config", "KEEP"),
        "dead-xz/a.json": ("KEEP-wave-config", "KEEP"),
        "dead-xz/b.bin": ("DEL-L4-FILE", "DELETE"),
        "dead-wv/wave/src_x": ("KEEP-wave-config", "KEEP"),                 # dead lane, old: the config name holds it
        "dead-wv/wave/plan": ("KEEP-wave-config", "KEEP"),                  # a named file holds its directory
        "dead-wv/wave/other": ("DEL-L4-LOOSE", "DELETE"),                   # not named: the lane state decides
        "dead-wv/wr/kit-wave/s81/p/items/it3/attempt_1": ("DEL-L2-ATTEMPT", "DELETE"),   # older attempt under a work root goes
        "dead-wv/wr/kit-wave/s81/p/items/it3/attempt_3": ("KEEP-wave-config", "KEEP"),   # latest stays
        "dead-wv/wr/kit-wave/s81/p/bind_a": ("KEEP-wave-config", "KEEP"),   # non-attempt content of a work root stays
        "dead-aa/kit1": ("DEL-L4-KIT", "DELETE"),          # expired .keep (72 h, dead lane) released
        "dead-bb": ("KEEP-dotkeep", "KEEP"),               # young .keep at the lane root holds its tree
        "dead-cc/kit3": ("KEEP-protected", "KEEP"),
        "dead-dd/kit4": ("KEEP-queue48", "KEEP"),
        "dead-ff/kit6": ("KEEP-kit-livelane", "KEEP"),      # a file written within 24 h keeps the kit
        "die-s81-81": ("KEEP-livelane-tree", "KEEP"),
        "dead-gg/kit-wave/s81/p/items/it/attempt_1": ("DEL-L4-ATTEMPT-UNKNOWN", "DELETE"),
    }
    bad = 0
    for k, v in expect.items():
        if rows.get(k) != v:
            print("MISMATCH", k, rows.get(k), "expected", v)
            bad += 1
    # cited units: the cited view stays, the rest is gated on the archive (unarchived = PEND, held)
    a1 = "dead-jj/kit-wave/s81/p/items/it2/attempt_1"
    if rows.get(f"{a1}/gen/it2/run/results/asap7/d/base/6_final.odb", ("", ""))[1] != "KEEP" or a1 in rows:
        print("MISMATCH cited view of an older attempt", {k: v for k, v in rows.items() if k.startswith(a1)})
        bad += 1
    if not [k for k, v in rows.items() if k.startswith(a1 + "/") and v == ("PEND-L1-CITED", "KEEP")]:
        print("MISMATCH unarchived cited unit must be PEND/KEEP")
        bad += 1
    if not [k for k, v in rows.items() if k.startswith("dead-pp/unit1/") and v == ("DEL-L1-CITED", "DELETE")]:
        print("MISMATCH archived cited unit members must be DELETE")
        bad += 1
    for k in ("dead-pp/unit1/run/results/asap7/d/base/6_final.odb", "dead-pp/unit1/config.mk", "dead-pp/unit1/ARCHIVED.json"):
        if rows.get(k, ("", ""))[1] != "KEEP":
            print("MISMATCH cited or record-name file must stay", k, rows.get(k))
            bad += 1
    assert not [k for k in rows if k.startswith("dead-bt") and rows[k][1] == "DELETE"], "bind of record tree must survive"
    assert not [k for k in rows if k.startswith("dead-nr") and rows[k][1] == "DELETE"], "kit-record input must survive"
    assert any(v[0] == "KEEP-kit-input" for k, v in rows.items() if k.startswith(("dead-bt", "dead-lk", "dead-nr"))), "guard must have held them"
    assert [k for k in rows if k.startswith("dead-unref") and rows[k][1] == "DELETE"], "negative control: an unnamed tree still goes"
    sg = [k for k in rows if k.startswith("dead-ee/kit5/") and rows[k][1] == "DELETE"]
    print("signed trim rows:", sg)
    if sg:                      # signed trim is report-only until the stub is defined by readers and tested
        print("MISMATCH signed trim must be report-only", sg)
        bad += 1
    print("CONTROLS", "PASS" if not bad else f"FAIL {bad}")
    # apply on the fixture: only DEL-L4-KIT; negative control: a row added to protected after plan must ALERT
    with open(f"{snap}/protected.tsv", "a") as fh:
        fh.write(f"{ROOT}/dead-aa/kit1\tadded after plan (must ALERT)\n")
    json.dump({"created": time.time(), "created_h": "now"}, open(f"{snap}/meta.json", "w"))
    r = subprocess.run([sys.executable, "-I", LC, "apply", "--tool", TOOL, "--host", "fix", "--lifesnap", f"{W}/life.json", "--out", out,
                        "--state", f"{W}/state2", "--snapshot", snap, "--docker", "", "--roots", ROOT, "--manifest", f"{out}/{mf}", "--cats", "DEL-L4-KIT",
                        "--coord-ref", "fixture"], capture_output=True, text=True, timeout=600)
    print(r.stdout[-800:], r.stderr[-800:], "rc", r.returncode)
    assert r.returncode == 3, "added-protected must ALERT and stop"
    assert os.path.exists(f"{ROOT}/dead-aa/kit1/config.mk"), "alerted row must not be deleted"
    life2 = json.load(open(f"{W}/life.json"))           # dead-oo has a live owner after the plan
    life2["live"] = life2["live"] + ["DEAD-OO"]
    json.dump(life2, open(f"{W}/life.json", "w"))
    # remove the fake row, apply really
    lines = open(f"{snap}/protected.tsv").read().splitlines()
    open(f"{snap}/protected.tsv", "w").write("\n".join(lines[:-1]) + "\n")
    r = subprocess.run([sys.executable, "-I", LC, "apply", "--tool", TOOL, "--host", "fix", "--lifesnap", f"{W}/life.json", "--out", out,
                        "--state", f"{W}/state3", "--snapshot", snap, "--docker", "", "--roots", ROOT, "--manifest", f"{out}/{mf}", "--cats", "DEL-L4-KIT",
                        "--coord-ref", "fixture"], capture_output=True, text=True, timeout=600)
    print(r.stdout[-400:], r.stderr[-800:], "rc", r.returncode)
    assert r.returncode == 0 and not os.path.exists(f"{ROOT}/dead-aa/kit1"), "apply must delete the row"
    assert os.path.exists(f"{ROOT}/dead-cc/kit3") and os.path.exists(f"{ROOT}/dead-bb/kit2"), "protected/.keep untouched"
    assert os.path.exists(f"{ROOT}/dead-oo/kit13/config.mk"), "lane live at apply time: row skipped"
    os.chmod(f"{ROOT}/dead-nn/kit12/run/objects", 0o755)     # so pytest can clean up
    print("APPLY CONTROLS PASS")
    assert not bad


def test_lifecycle_fixture():
    # the tool reads record paths only under /srv, /home or /tmp (ABS_RE, the fleet's data roots); a basetemp elsewhere (the merge
    # lane uses /dev/shm) drops every citation, so the fixture always lives under /tmp
    import shutil, tempfile
    W = tempfile.mkdtemp(prefix="ot-lifecycle-fix-", dir="/tmp")
    try:
        run_fixture(W)
    finally:
        for dp, dn, fn in os.walk(W):
            os.chmod(dp, 0o755)
        shutil.rmtree(W, ignore_errors=True)


def test_count_check_lost(tmp_path):
    import importlib.util
    sp = importlib.util.spec_from_file_location("lc", LC)
    lc = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(lc)
    sp2 = importlib.util.spec_from_file_location("ac", TOOL)
    ac = importlib.util.module_from_spec(sp2)
    sp2.loader.exec_module(ac)
    ap = lc.Apply.__new__(lc.Apply)
    ap.m = ac
    root = str(tmp_path)
    kept, ours, theirs = f"{root}/a/keep", f"{root}/b/sub/rec", f"{root}/c/rec"
    assert ap.lost({kept}, {f"{root}/b"}) == []                          # still there
    assert ap.lost({ours}, {f"{root}/b"}) == [ours]                      # gone under a removed path: loss
    assert ap.lost({theirs}, {f"{root}/b"}) == []                        # gone but not under anything this run removed


def test_kw_release(tmp_path):
    import importlib.util
    sp = importlib.util.spec_from_file_location("lc", LC)
    lc = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(lc)
    sp2 = importlib.util.spec_from_file_location("ac", TOOL)
    ac = importlib.util.module_from_spec(sp2)
    sp2.loader.exec_module(ac)
    class P(lc.Plan):
        def __init__(self):
            self.m = ac
            self.J = type("J", (), {"paths": type("Pa", (), {"canon": staticmethod(lambda p: p)})})()
        def attempt_verdict(self, d):
            return "finished-old" if d.endswith("attempt_1") else "latest-open"
    p = P()
    base = "/x/claude/w/kit-wave/s81/p/items/it"
    h = ("KEEP-kw-protect", "line", False)
    assert p.kw_release(h, f"{base}/attempt_1") is None                  # older attempt goes
    assert p.kw_release(h, f"{base}/attempt_1/gen/f") is None            # and its members
    assert p.kw_release(h, f"{base}/attempt_3") == h                     # latest stays
    assert p.kw_release(h, "/x/claude/w/src_a/f") == h                   # not an attempt: line still holds
    other = ("KEEP-counted", "line", False)
    assert p.kw_release(other, f"{base}/attempt_1") == other             # counted is never released


def test_wave_config_paths():
    import importlib.util
    sp = importlib.util.spec_from_file_location("lc", LC)
    lc = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(lc)
    cfg = {"work_root": "/srv/opentallas-scratch2/claude/kit-wave", "note": "/srv/opentallas-scratch2/claude/gone/a",
           "dies": {"q": {"plan": "/srv/opentallas-scratch2/claude/qct11/wave/plan/p.json", "src": "/srv/opentallas-scratch2/claude/qct11/wave/src_lfq",
                          "kit_rtl": {"bind_out": "/srv/opentallas-scratch2/claude/qct11/wave/bind_v4nS"},
                          "gen_args": ["--clock-landing", "/srv/opentallas-scratch2/claude/qct11/wave/src_lfq/s.json"],
                          "src_prev_kw1": "/srv/opentallas-scratch2/claude/old/src", "item": "scratch3/claude/kw35/t45ov/bind"}}}
    got = lc.wave_config_paths(cfg)
    for p in ("/srv/opentallas-scratch2/claude/kit-wave", "/srv/opentallas-scratch2/claude/qct11/wave/plan/p.json",
              "/srv/opentallas-scratch2/claude/qct11/wave/src_lfq", "/srv/opentallas-scratch2/claude/qct11/wave/bind_v4nS",
              "/srv/opentallas-scratch3/claude/kw35/t45ov/bind"):
        assert p in got, p
    assert "/srv/opentallas-scratch2/claude/gone/a" not in got and "/srv/opentallas-scratch2/claude/old/src" not in got


def _lc():
    import importlib.util
    sp = importlib.util.spec_from_file_location("lc", LC)
    lc = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(lc)
    sp2 = importlib.util.spec_from_file_location("ac", TOOL)
    ac = importlib.util.module_from_spec(sp2)
    sp2.loader.exec_module(ac)
    return lc, ac


def test_kept_link_into(tmp_path):
    lc, ac = _lc()
    ap = lc.Apply.__new__(lc.Apply)
    ap.m = ac
    item = tmp_path / "items" / "it"
    (item / "attempt_1" / "gen").mkdir(parents=True)
    (item / "attempt_2" / "gen").mkdir(parents=True)
    (item / "attempt_3" / "gen").mkdir(parents=True)
    (item / "attempt_3" / "gen" / "lnk").symlink_to(item / "attempt_1" / "gen")
    assert "symlink from" in ap.kept_link_into(str(item / "attempt_1"))  # a kept sibling points into it
    assert ap.kept_link_into(str(item / "attempt_2")) is None            # nobody points here
    assert "symlink from" in ap.kept_link_into(str(item / "attempt_1" / "gen"))   # member rows too


def test_git_all_refs(tmp_path):
    lc, ac = _lc()
    env = dict(os.environ, GIT_AUTHOR_NAME="a", GIT_AUTHOR_EMAIL="a@a", GIT_COMMITTER_NAME="a", GIT_COMMITTER_EMAIL="a@a")
    def g(*a, cwd=None):
        subprocess.run(["git", *a], check=True, cwd=cwd, env=env, capture_output=True)
    src = tmp_path / "src"
    g("init", "-q", "-b", "main", str(src))
    (src / "f").write_text("x")
    g("add", "f", cwd=src)
    g("commit", "-q", "-m", "one", cwd=src)
    cl = tmp_path / "cl"
    g("clone", "-q", str(src), str(cl))
    G = lc.Git()
    assert G.check(str(cl)) is None                                      # everything on the remote
    g("checkout", "-q", "-b", "side", cwd=cl)
    (cl / "g").write_text("y")
    g("add", "g", cwd=cl)
    g("commit", "-q", "-m", "local", cwd=cl)
    g("checkout", "-q", "main", cwd=cl)                                  # HEAD is clean and on the remote, a branch is not
    assert lc.Git().check(str(cl)).startswith("git-head-unpushed")
    bare = tmp_path / "b.git"
    g("clone", "-q", "--bare", str(src), str(bare))                      # a bare clone has no remote-tracking refs
    assert lc.Git().check(str(bare)).startswith("git-head-unpushed")


def test_live_kit_inputs(tmp_path):
    lc, ac = _lc()
    root = tmp_path / "s" / "claude"
    att = root / "w" / "kit-wave" / "p" / "items" / "it" / "attempt_2"
    (att / "rtl").mkdir(parents=True)
    (root / "b" / "bind").mkdir(parents=True)
    (att / "rtl" / "kit_rtl.json").write_text(json.dumps({"own": f"{att}/rtl/x.sv", "other": f"{root}/b/bind/y.sv"}))
    (root / "sc").mkdir()
    (root / "sc" / "k.sh").write_text(f"run {root}/sc2/next.json\n")
    (root / "sc2").mkdir()
    (root / "sc2" / "next.json").write_text(json.dumps({"bind": f"{root}/b2/bind"}))
    refs, n = lc.live_kit_inputs([str(root)], [f"{root}/sc/k.sh"])
    assert f"{root}/b/bind/y.sv" in refs                                  # another tree named by a kit record
    assert f"{att}/rtl/x.sv" not in refs                                  # a record does not hold its own attempt
    assert f"{root}/sc2/next.json" in refs and f"{root}/b2/bind" in refs  # two hops through wave-named files
    assert lc.live_kit_inputs([str(tmp_path / "none")], []) == (set(), 0)



def _incident_fleet(W):
    """the 11-09 00:14 epyc5 pass, as a fixture: a dead, old bind lane on one root, reached by live kits only through an alias
    symlink on the other root, a kit_rtl.json, a bind_report.json and a kit_rtl.f (+incdir+ and -v forms)"""
    R2, R3 = os.path.join(W, "s2/claude"), os.path.join(W, "s3/claude")
    os.makedirs(R2); os.makedirs(R3)
    B = f"{R3}/codex-wave-bind-1106"
    for f in ("s81_emitted_v2/bind/rtl/top.sv", "s81_emitted_v2/bind/rtl/sib.sv", "s81_seeded/bind/rtl/a.sv", "s81_seeded/run.sh",
              "kv_sys_phy/bind/inc/defs.svh", "kv_sys_phy/bind/x.sv", "unnamed/f.bin", "late/g.bin",
              "kv_union/bind/u.sv", "kv_union/bind/sib.sv"):
        write(f"{B}/{f}", 64)
    os.symlink(B, f"{R2}/codex-wave-bind-1106")                                   # alias, like kw26-wave-1106 -> scratch2
    att = f"{R2}/kwx/kit-wave/s81/p/items/it/attempt_4/rtl"
    write(f"{att}/own.sv", 64)
    with open(f"{att}/kit_rtl.json", "w") as fh:                                    # names the alias form, realpath is on R3
        json.dump({"own": f"{att}/own.sv", "bound": [f"{R2}/codex-wave-bind-1106/s81_emitted_v2/bind/rtl/top.sv"]}, fh)
    os.makedirs(f"{R2}/kwy/bind_out")
    with open(f"{R2}/kwy/bind_out/bind_report.json", "w") as fh:                   # names a directory: rows inside it stay
        json.dump({"bind_out": f"{B}/s81_seeded/bind"}, fh)
    os.makedirs(f"{R2}/kwz/u")
    with open(f"{R2}/kwz/u/kit_rtl.f", "w") as fh:
        fh.write(f"+incdir+{B}/kv_sys_phy/bind/inc\n-v {B}/kv_sys_phy/bind/x.sv\n")
    kit(f"{R2}/dead-pc/kit1")                                                       # protected, for the plan's own control
    # 11-09 03:08 epyc2: s81-t51-recut (live lane, no lane-name match, old files) was deleted as a dead-lane orphan dir; it is named
    # in a post of the last 24 h, so the whole subtree stays.  dead-mp: only a sub path is named; the rest of that lane still goes
    for f in ("pg/rtl/s81_child_e.v", "fc10/native_ff_pose_e.tcl", "codex_split_copy/mapped_controls/split_clean.json", "eco2/big.bin"):
        write(f"{R3}/s81-t51-recut/{f}", 64)
    write(f"{R2}/dead-mp/sub/keepme/a.bin", 64)
    write(f"{R2}/dead-mp/other/b.bin", 64)
    write(f"{R2}/dead-iso/job1/out/r.bin", 64)                                      # ISOLATE-1 job root: ot-run deletes it, never this tool
    write(f"{R2}/dead-iso/job1/.ot-isolated.json", 2)
    write(f"{R2}/dead-iso/legacy/x.bin", 64)
    # cause 2 (AUTOCLEAN-12 02:13): an older attempt under a live wave work root, named by a kit record elsewhere
    WR = f"{R2}/kw26w/runs/s81"
    kit(f"{WR}/kit-wave/s81/p/items/it5/attempt_1/gen/it5")
    write(f"{WR}/kit-wave/s81/p/items/it5/attempt_1/rtl_bindov/b.sv", 64)
    kit(f"{WR}/kit-wave/s81/p/items/it5/attempt_3/gen/it5")
    kit(f"{WR}/kit-wave/s81/p/items/it6/attempt_1/gen/it6")      # negative control: older attempt nobody names still goes
    kit(f"{WR}/kit-wave/s81/p/items/it6/attempt_2/gen/it6")
    kit(f"{WR}/kit-wave/s81/p/items/it7/attempt_1/gen/it7")      # older attempt whose path a post names: stays
    kit(f"{WR}/kit-wave/s81/p/items/it7/attempt_2/gen/it7")
    kit(f"{WR}/kit-wave/s81/p/items/it8/attempt_3/gen/it8")      # latest, wave says SUPERSEDED: goes
    kit(f"{WR}/kit-wave/s81/p/items/it9/attempt_4/gen/it9")      # latest, only FAILed: a fix may resume from it, stays
    for dp, dn, fn in os.walk(f"{WR}/kit-wave/s81/p/items/it8", topdown=False):     # older than the 24 h resume window
        for x in dn:
            os.utime(os.path.join(dp, x), (OLD, OLD))
    os.utime(f"{WR}/kit-wave/s81/p/items/it8", (OLD, OLD))
    write(f"{R2}/kw26w/notes/n.txt", 64)                          # non-attempt content of a named wave lane: stays
    os.makedirs(f"{R2}/kwz2/u/rtl")
    with open(f"{R2}/kwz2/u/rtl/kit_rtl.json", "w") as fh:
        json.dump({"overlay": f"{WR}/kit-wave/s81/p/items/it5/attempt_1/rtl_bindov/b.sv"}, fh)
    write(f"{R2}/dead-wv/wave/w.json", 64)
    # 11-09 04:3x epyc4 dkv72/pvb/view: a dead lane's view dir whose rtl/ is an interior symlink into another lane; a record names the
    # file through the symlink, so removing view breaks that path although the target survives
    write(f"{R3}/dkv69/wpv/rtl/common/c.sv", 64)
    write(f"{R3}/dkv72/pvb/view/README.md", 64)
    os.symlink(f"{R3}/dkv69/wpv/rtl", f"{R3}/dkv72/pvb/view/rtl")
    write(f"{R3}/dkv72/pvb/scratch/z.bin", 64)
    snap = os.path.join(W, "snap")
    os.makedirs(snap)
    with open(f"{snap}/protected.tsv", "w") as fh:
        fh.write(f"{R2}/dead-pc/kit1\tfixture\n")
        for i in range(120):
            fh.write(f"/srv/none/claude/lane/x{i}\tpad\n")
    json.dump({"created": time.time(), "created_h": "now"}, open(f"{snap}/meta.json", "w"))
    json.dump({"paths": [], "words": []}, open(f"{snap}/queue.json", "w"))
    json.dump({"attempts": {f"fix:{WR}/kit-wave/s81/p/items/it8/attempt_3": {"active": False, "signed": False, "terminal": ["ENQUEUED/FAIL", "stage:SUPERSEDED"]},
                            f"fix:{WR}/kit-wave/s81/p/items/it9/attempt_4": {"active": False, "signed": False, "terminal": ["ENQUEUED/FAIL", "stage:FAIL"]}},
               "latest": {f"fix:{WR}/kit-wave/s81/p/items/it5": 3, f"fix:{WR}/kit-wave/s81/p/items/it6": 2, f"fix:{WR}/kit-wave/s81/p/items/it7": 2,
                          f"fix:{WR}/kit-wave/s81/p/items/it8": 3, f"fix:{WR}/kit-wave/s81/p/items/it9": 4}, "keep": [], "current_di": {},
               "created": time.time(), "source": "fix"}, open(f"{snap}/kitwave.json", "w"))
    json.dump({"created": time.time(), "live": [], "lane_last": {}, "paths48": [], "words48": [],
               "protected_full": [["fix", f"{R2}/dead-pc/kit1", "fixture"]], "coord_holds": [],
               "kit_union": ["codex-wave-bind-1106/kv_union/bind/u.sv",      # named only by a record on another host
                             "dkv72/pvb/view/rtl/common/c.sv"],              # named through an interior symlink
               "lane_mentions24": ["s81-t51-recut", "pg", "fc10", "kw26w"],
               "mention_paths24": ["dead-mp/sub/keepme", "kw26w/runs/s81/kit-wave/s81/p/items/it7/attempt_1"],   # LANE-DIR HOLD cases
               "wave_paths": [f"{R2}/dead-wv/wave/w.json", WR]}, open(f"{W}/life.json", "w"))
    return R2, R3, B, snap


def _lc_run(W, lc, cmd, R2, R3, snap, *extra):
    return subprocess.run([sys.executable, "-I", lc, cmd, "--tool", TOOL, "--host", "fix", "--lifesnap", f"{W}/life.json", "--out", f"{W}/out",
                           "--state", f"{W}/state-{cmd}", "--snapshot", snap, "--docker", "", "--roots", R2, R3, *extra],
                          capture_output=True, text=True, timeout=600)


def _mutant(W, old, new):
    src = open(LC).read()
    assert src.count(old) == 1, old
    p = os.path.join(W, "mutant-lifecycle.py")
    open(p, "w").write(src.replace(old, new))
    return p


def test_incident_0014_live_kit_inputs(tmp_path):
    W = str(tmp_path)
    R2, R3, B, snap = _incident_fleet(W)
    r = _lc_run(W, LC, "plan", R2, R3, snap)
    print(r.stdout[-2000:], r.stderr[-1500:])
    assert r.returncode == 0
    mf = sorted(f for f in os.listdir(f"{W}/out") if f.startswith("PLAN-"))[-1]
    rows, raw = {}, []
    for ln in open(f"{W}/out/{mf}").read().splitlines()[1:]:
        c = ln.split("\t")
        rows[os.path.realpath(c[0])] = (c[1], c[2])
        if c[2] == "DELETE":
            raw.append(os.path.normpath(c[0]))
    V = f"{R3}/dkv72/pvb/view/rtl"
    assert not [p for p in raw if p == V or V.startswith(p + "/")], ("interior-symlink alias path broken", [p for p in raw if "dkv72" in p])
    assert any(p.startswith(f"{R3}/dkv72/pvb/scratch") for p in raw), "negative control: the unnamed part of dkv72 still goes"
    named = [f"{B}/s81_emitted_v2/bind/rtl/top.sv", f"{B}/s81_seeded/bind/rtl/a.sv", f"{B}/kv_sys_phy/bind/inc/defs.svh", f"{B}/kv_sys_phy/bind/x.sv", f"{B}/kv_union/bind/u.sv"]
    for p, (cat, act) in rows.items():                       # no DELETE row is, contains or sits inside a named input (realpath both sides)
        if act == "DELETE":
            assert not [n for n in named if n == p or n.startswith(p + "/") or p.startswith(os.path.dirname(n) + "/")], (p, cat)
    assert rows.get(f"{B}/unnamed", ("", ""))[1] == "DELETE", "negative control: an unnamed dir of the dead lane still goes"
    assert any(v[0] == "KEEP-kit-input" for v in rows.values()), "the guard, not some other hold, kept them"
    t51 = f"{R3}/s81-t51-recut"
    assert not [p for p, v in rows.items() if v[1] == "DELETE" and (p == t51 or p.startswith(t51 + "/"))], "LANE-DIR HOLD: mentioned lane dir stays"
    assert rows.get(t51, ("", ""))[0] == "KEEP-lane-mention", rows.get(t51)
    assert not [p for p, v in rows.items() if v[1] == "DELETE" and (p.startswith(f"{R2}/dead-mp/sub/keepme") or f"{R2}/dead-mp/sub/keepme".startswith(p + "/"))]
    assert rows.get(f"{R2}/dead-mp/other", ("", ""))[1] == "DELETE", "negative control: the unnamed part of a lane goes"
    assert not [p for p, v in rows.items() if v[1] == "DELETE" and (p == f"{R2}/dead-iso" or p.startswith(f"{R2}/dead-iso/job1"))], "isolated job left to ot-run"
    assert rows.get(f"{R2}/dead-iso/legacy", ("", ""))[1] == "DELETE", "legacy dir beside an isolated job is still this tool's"
    WR = f"{R2}/kw26w/runs/s81/kit-wave/s81/p/items"
    nb = WR + "/it5/attempt_1/rtl_bindov"
    assert not [p for p, v in rows.items() if v[1] == "DELETE" and (p == nb or nb.startswith(p + "/") or p.startswith(nb + "/"))], \
        "kit input check must run before the work-root release of older attempts"
    assert os.path.exists(nb + "/b.sv")
    assert rows.get(WR + "/it6/attempt_1", ("", ""))[1] == "DELETE", "finished superseded attempt of a NAMED wave lane is released (07:2x)"
    assert rows.get(WR + "/it8/attempt_3", ("", ""))[1] == "DELETE", ("latest attempt the wave SUPERSEDED goes (07:1x)", {p: v for p, v in rows.items() if "/it8" in p or "/it9" in p or p.endswith("/items")})
    assert not [p for p, v in rows.items() if v[1] == "DELETE" and p.startswith(WR + "/it9/")], "latest attempt that only FAILed stays (resume)"
    assert not [p for p, v in rows.items() if v[1] == "DELETE" and (p.startswith(WR + "/it6/attempt_2") or p.startswith(WR + "/it7/attempt_1")
                or p.startswith(f"{R2}/kw26w/notes") or (WR + "/it6/attempt_2").startswith(p + "/"))], "latest, path-named and non-attempt content stay"
    for n in named:
        assert os.path.exists(n)
    # mutant L: an empty mention list releases s81-t51-recut (the test sees the incident); a missing list refuses
    life = json.load(open(f"{W}/life.json")); keep = (life["lane_mentions24"], life["mention_paths24"])
    life["lane_mentions24"], life["mention_paths24"] = [], []; json.dump(life, open(f"{W}/life.json", "w"))
    r = _lc_run(W, LC, "plan", R2, R3, snap)
    mf2 = sorted(f for f in os.listdir(f"{W}/out") if f.startswith("PLAN-"))[-1]
    gone = [ln for ln in open(f"{W}/out/{mf2}").read().splitlines()[1:] if "s81-t51-recut" in ln and "\tDELETE\t" in ln]
    assert r.returncode == 0 and gone, "without the hold the incident tree is DELETE (positive control of the test)"
    del life["lane_mentions24"]; json.dump(life, open(f"{W}/life.json", "w"))
    r = _lc_run(W, LC, "plan", R2, R3, snap)
    assert r.returncode != 0 and "lane_mentions24" in (r.stdout + r.stderr)
    life["lane_mentions24"], life["mention_paths24"] = keep; json.dump(life, open(f"{W}/life.json", "w"))
    time.sleep(1.1)
    # mutant 0: without the fleet list the plan refuses
    life = json.load(open(f"{W}/life.json")); ku = life.pop("kit_union"); json.dump(life, open(f"{W}/life.json", "w"))
    r = _lc_run(W, LC, "plan", R2, R3, snap)
    assert r.returncode != 0 and "kit_union" in (r.stdout + r.stderr)
    life["kit_union"] = ku; json.dump(life, open(f"{W}/life.json", "w"))
    # mutant 1: guard matching nothing -> the plan's positive control must refuse
    mp = _mutant(W, "kh = self.kit.hit(f) or self.kit_lit.hit(f)", "kh = None")
    r = _lc_run(W, mp, "plan", R2, R3, snap)
    assert r.returncode != 0 and "live kit input" in (r.stdout + r.stderr), "positive control must catch a dead guard"
    # a kit record written after the plan names late/: the apply recheck must skip that row
    os.makedirs(f"{R2}/kwq/v/rtl")
    with open(f"{R2}/kwq/v/rtl/kit_rtl.json", "w") as fh:
        json.dump({"bound": [f"{R2}/codex-wave-bind-1106/late/g.bin"]}, fh)
    assert rows.get(f"{B}/late", ("", ""))[1] == "DELETE"
    lm = f"{W}/late.tsv"
    with open(lm, "w") as fh:
        fh.write("path\tcategory\taction\treason\tbytes\tfiles\n")
        fh.write(f"{B}/late\t{rows[B + '/late'][0]}\tDELETE\tfixture\t64\t1\n")
    # mutant 2: the recheck without the kit-input check deletes it (proves the test sees the gap)
    # mutant 3: canonical set only (the 04:3x tool): the dir holding the alias goes DELETE, so the test sees the gap
    mp3 = _mutant(W, "kh = self.kit.hit(f) or self.kit_lit.hit(f)", "kh = self.kit.hit(f)")
    r = _lc_run(W, mp3, "plan", R2, R3, snap)
    mf3 = sorted(f for f in os.listdir(f"{W}/out") if f.startswith("PLAN-"))[-1]
    raw3 = [os.path.normpath(ln.split("\t")[0]) for ln in open(f"{W}/out/{mf3}").read().splitlines()[1:] if "\tDELETE\t" in ln]
    assert r.returncode == 0 and [p for p in raw3 if V.startswith(p + "/")], ("mutant 3 must break the alias", r.stdout[-600:], r.stderr[-600:])
    time.sleep(1.1)
    mp2 = _mutant(W, '        kh = P.kit_hit(sorted({path, real} | set(J.paths.forms(path))))',
                  '        kh = None')
    r = _lc_run(W, mp2, "apply", R2, R3, snap, "--manifest", lm, "--coord-ref", "fixture", "--dry")
    out = open(sorted(os.path.join(f"{W}/out", f) for f in os.listdir(f"{W}/out") if f.startswith("APPLY-"))[-1]).read()
    assert r.returncode == 0 and "\tWOULD\t" in out, (r.stdout[-800:], r.stderr[-800:], out)
    time.sleep(1.1)                                          # APPLY manifests are named by the second
    r = _lc_run(W, LC, "apply", R2, R3, snap, "--manifest", lm, "--coord-ref", "fixture")
    out = open(sorted(os.path.join(f"{W}/out", f) for f in os.listdir(f"{W}/out") if f.startswith("APPLY-"))[-1]).read()
    print(r.stdout[-800:], r.stderr[-800:], out)
    assert r.returncode == 0 and "live kit input" in out and os.path.exists(f"{B}/late/g.bin"), "recheck must hold a record written after the plan"


def test_kit_union_merge(tmp_path):
    lc, ac = _lc()
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    lc.write_kitscan(str(a), {"/srv/opentallas-scratch3/claude/x/bind/y.sv"}, 1)
    lc.write_kitscan(str(b), {"/srv/opentallas-scratch2/claude/z/k.sh"}, 1)
    ku, miss = lc.merge_kitscans({"h1": str(a), "h2": str(b)}, ["h1", "h2"])
    assert ku == ["x/bind/y.sv", "z/k.sh"] and miss == []
    assert lc.merge_kitscans({"h1": str(a)}, ["h1", "h2"]) == (None, ["h2"])           # a host without a scan: no union, hosts refuse
    d = json.load(open(b)); d["created"] -= 25 * 3600; json.dump(d, open(b, "w"))
    assert lc.merge_kitscans({"h1": str(a), "h2": str(b)}, ["h1", "h2"]) == (None, ["h2"])   # stale scan counts as missing


def test_mention_tokens():
    lc, ac = _lc()
    post = ("Where they were: epyc2 /srv/opentallas-scratch3/claude/s81-t51-recut/{pg,fc10,fc8,eco,kits_b} was deleted; "
            "[CHECKED epyc2 s81-t51-recut/probe_r2/sl_{w,e}/slew.{rpt,tsv}] and intel1 codex-s81-split-1106 is gone.")
    names, tails = lc.mention_tokens(post)
    assert {"s81-t51-recut", "codex-s81-split-1106", "pg", "fc10"} <= names
    assert {"s81-t51-recut/pg", "s81-t51-recut/kits_b", "s81-t51-recut/probe_r2/sl_w/slew.rpt"} <= tails, sorted(tails)


def test_tmp_rule(tmp_path):
    lc, ac = _lc()
    B = str(tmp_path)
    for p in ("tmpold/a/f", "tmpnew/f", "tmpopen/f", "pytest-of-u/pytest-3/x", "pytest-of-u/pytest-9/y", "kw35rd/big/f", "r8t/f"):
        write(os.path.join(B, p), 8, old=p not in ("tmpnew/f", "pytest-of-u/pytest-9/y"))
    for p in ("tmpold", "tmpold/a", "tmpold/a/f", "tmpopen", "tmpopen/f", "pytest-of-u/pytest-3", "pytest-of-u/pytest-3/x", "kw35rd", "kw35rd/big", "kw35rd/big/f", "r8t", "r8t/f"):
        os.utime(os.path.join(B, p), (OLD, OLD))
    os.utime(os.path.join(B, "pytest-of-u/pytest-9"), (OLD, OLD))                # dir old, file inside young: newest mtime decides
    fh = open(os.path.join(B, "tmpopen/f"))                                         # an open handle keeps an old entry
    try:
        rows, d, f = lc.tmp_pass(B, apply=True, out=os.path.join(B, "m.tsv"))
    finally:
        fh.close()
    assert not os.path.exists(f"{B}/tmpold") and not os.path.exists(f"{B}/pytest-of-u/pytest-3")
    for p in ("tmpnew", "tmpopen", "pytest-of-u/pytest-9", "kw35rd", "r8t"):
        assert os.path.exists(os.path.join(B, p)), p                                # young, open, and named lane dirs stay
    assert d == 2 and open(f"{B}/m.tsv").read().count("\tDELETE\t") == 2


def test_mention_posts_skip_cleanup_tables():
    lc, ac = _lc()
    now = time.time()
    posts = [{"t": now - 60, "auth": "AUTOCLEAN-13", "text": "TABLE DELETE hbm-gaps-2 35.4"},
             {"t": now - 60, "auth": "DIE-HBM-97", "text": "rerun in die-hbm-63/eco"},
             {"t": now - 60, "auth": None, "text": "KIT-WAVE launched kw44"},
             {"t": now - 25 * 3600, "auth": "DIE-KV-97", "text": "old dkv66"}]
    got = [p["text"] for p in lc.mention_posts(posts, now)]
    assert got == ["rerun in die-hbm-63/eco", "KIT-WAVE launched kw44"], got     # cleanup tables and >24 h posts do not hold


def test_alternates_targets_guarded(tmp_path):
    """COORD 11-09 13:1x: the store a repo borrows from (objects/info/alternates) is a live kit input on every host, so no plan deletes it.
    Incident: codex-wave-1105/{src,src_2c705} went missing and 409 wave src repos lost objects."""
    lc, ac = _lc()
    root = tmp_path / "s" / "claude"
    (root / "cw" / "src" / ".git" / "objects" / "pack").mkdir(parents=True)
    (root / "cw" / "src_2c705" / ".git" / "objects").mkdir(parents=True)
    info = root / "kw41" / "src_hbmf4" / ".git" / "objects" / "info"
    info.mkdir(parents=True)
    (info / "alternates").write_text(f"{root}/cw/src/.git/objects\n../../../../cw/src_2c705/.git/objects\n# note\n")
    refs, n = lc.live_kit_inputs([str(root)], [])
    assert f"{root}/cw/src/.git/objects" in refs                               # absolute entry
    assert f"{root}/cw/src_2c705/.git/objects" in refs                         # relative entry resolves against the borrowing objects dir
    tails = lc.kit_tails(refs)
    assert "cw/src/.git/objects" in tails and "cw/src_2c705/.git/objects" in tails    # tails reach the fleet kit_union, any host
    # mutant: a scan without the alternates step loses both targets (the test sees the gap)
    saved = lc.alternates_targets_under
    lc.alternates_targets_under = lambda r: set()
    try:
        refs2, _ = lc.live_kit_inputs([str(root)], [])
    finally:
        lc.alternates_targets_under = saved
    assert f"{root}/cw/src/.git/objects" not in refs2


def test_never_touch_main_git():
    """COORD 11-09: /home/ubuntu/OpenTallas/.git is the alternates store of live wave srcs on every host; no row is, holds or sits inside it"""
    lc, ac = _lc()
    class P: pass
    p = P(); p.kit = p.kit_lit = type("E", (), {"hit": staticmethod(lambda f: None)})()
    kh = lambda ps: lc.Plan.kit_hit(p, ps)
    assert kh(["/home/ubuntu/OpenTallas/.git/objects/pack"]) and kh(["/home/ubuntu/OpenTallas/.git"]) and kh(["/home/ubuntu/OpenTallas"])
    assert kh(["/home/ubuntu/OpenTallas-x/.git"]) is None and kh(["/srv/opentallas-scratch2/claude/x"]) is None
