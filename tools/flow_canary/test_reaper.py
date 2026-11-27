import json, os, stat, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reaper as R

H = 3600


def mk(root, name, die, age_h=None, src=None, submitted=0, keep=False, approval=False, unit=None):
    d = root / name
    d.mkdir(parents=True)
    meta = {"spec": {"die": die}, "submitted_at": submitted, "src": str(src) if src else ""}
    if unit:
        meta["client_unit"] = unit
    (d / "canary_meta.json").write_text(json.dumps(meta))
    if age_h is not None:
        c = d / "canary.json"
        c.write_text("{}")
        t = time.time() - age_h * H
        os.utime(c, (t, t))
    if keep:
        (d / ".keep").write_text("x")
    if approval:
        (d / "harness").mkdir()
        (d / "harness/route_approval.json").write_text("{}")
    return d


def mksrc(base, name, age_h):
    s = base / "sources" / name
    s.mkdir(parents=True)
    t = time.time() - age_h * H
    os.utime(s, (t, t))
    return s


def fake(tmp):
    f = tmp / "fake-ot-delete"
    f.write_text("import sys,shutil,os\nfor a in sys.argv[1:]:\n    if a.startswith('-'): continue\n    shutil.rmtree(a) if os.path.isdir(a) else os.remove(a)\n")
    return f


def setup(tmp):
    base = tmp / "fc"
    root = base / "runs"
    root.mkdir(parents=True)
    return base, root


def go(root, f, **kw):
    return R.reap(str(root), f, unit_alive=lambda u: False, **kw)


def test_closed_old_deleted_closed_new_kept(tmp_path):
    base, root = setup(tmp_path)
    mk(root, "newest", "d1", 50, submitted=9)           # newest per die: kept
    old = mk(root, "old", "d1", 30, submitted=1)
    new = mk(root, "recent", "d1", 2, submitted=2)
    go(root, fake(tmp_path))
    assert not old.exists() and new.exists() and (root / "newest").exists()


def test_open_and_route_approval_kept(tmp_path):
    base, root = setup(tmp_path)
    mk(root, "n", "d1", 1, submitted=9)
    op = mk(root, "open", "d1", None, submitted=1)
    os.utime(op, (1, 1))
    ra = mk(root, "appr", "d1", None, submitted=2, approval=True)
    kp = mk(root, "kept", "d1", 40, submitted=3, keep=True)
    go(root, fake(tmp_path))
    assert op.exists() and ra.exists() and kp.exists()


def test_live_unit_kept(tmp_path):
    base, root = setup(tmp_path)
    mk(root, "n", "d1", 1, submitted=9)
    live = mk(root, "live", "d1", 40, submitted=1, unit="u")
    R.reap(str(root), fake(tmp_path), unit_alive=lambda u: True)
    assert live.exists()


def test_sources(tmp_path):
    base, root = setup(tmp_path)
    s_old, s_new, s_ref, s_top = (mksrc(base, n, a) for n, a in (("aaa", 20), ("bbb", 1), ("ccc", 20), ("ddd", 0.5)))
    mk(root, "n", "d1", 1, submitted=9, src=s_top)
    mk(root, "open", "d1", None, submitted=1, src=s_ref)   # open run references ccc
    go(root, fake(tmp_path))
    assert not s_old.exists() and s_new.exists() and s_ref.exists() and s_top.exists()


def test_prune_keeps_odb_reports(tmp_path):
    base, root = setup(tmp_path)
    mk(root, "n", "d1", 1, submitted=9)
    r = mk(root, "r", "d1", 2, submitted=1)
    odb = r / "gen/k/run/results/asap7/t/base/3_place.odb"
    big = r / "gen/k/run/results/asap7/t/base/2_floorplan.odb"
    rep = r / "gen/k/run/reports/big.rpt"
    for p in (odb, big, rep):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * (R.BIG + 1))
    go(root, fake(tmp_path))
    assert odb.exists() and rep.exists() and not big.exists() and (r / R.MARK).exists()


def test_prune_worktrees_after_source_delete(tmp_path):
    import shutil
    import subprocess
    import reaper
    repo = tmp_path / "repo"
    repo.mkdir()
    env = ["-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), *env, "commit", "-q", "--allow-empty", "-m", "x"], check=True)
    wt = tmp_path / "src1"
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(wt)], check=True)
    owner = reaper.owner_common_dir(wt)
    assert owner == repo / ".git"
    shutil.rmtree(wt)
    assert "src1" in subprocess.run(["git", "-C", str(repo), "worktree", "list"], capture_output=True, text=True).stdout
    assert reaper.prune_worktrees([owner, None, tmp_path / "nonexistent"]) >= 1
    assert "src1" not in subprocess.run(["git", "-C", str(repo), "worktree", "list"], capture_output=True, text=True).stdout
