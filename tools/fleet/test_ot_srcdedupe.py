import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("srcdedupe", Path(__file__).with_name("ot-srcdedupe.py"))
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)


def tree(p, files):
    p.mkdir(parents=True)
    env = dict(os.environ, GIT_AUTHOR_NAME="a", GIT_AUTHOR_EMAIL="a@a", GIT_COMMITTER_NAME="a", GIT_COMMITTER_EMAIL="a@a")
    subprocess.run(["git", "init", "-q", str(p)], check=True, env=env)
    for n, body in files.items():
        (p / n).parent.mkdir(parents=True, exist_ok=True)
        (p / n).write_bytes(body)
    subprocess.run(["git", "-C", str(p), "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(p), "commit", "-qm", "x"], check=True, env=env)
    return p


BODY = b"x" * 20000


@pytest.fixture(autouse=True)
def no_docker(monkeypatch):
    monkeypatch.setattr(D, "container_mounts", lambda: set())


def setup(tmp_path):
    a = tree(tmp_path / "a", {"big/f.bin": BODY, "tools/run.sh": BODY + b"s"})
    b = tree(tmp_path / "b", {"big/f.bin": BODY, "tools/run.sh": BODY + b"s"})
    lst = tmp_path / "trees.txt"
    lst.write_text(f"{a}\n{b}\n")
    return a, b, lst


def ino(p):
    return os.lstat(p).st_ino


def run(capsys, *argv):
    assert D.main(list(argv)) == 0
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def test_dry_run_changes_nothing(tmp_path, capsys):
    a, b, lst = setup(tmp_path)
    before = (ino(a / "big/f.bin"), ino(b / "big/f.bin"))
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1")
    assert r["rows"] == 2 and r["applied"] == 0
    assert (ino(a / "big/f.bin"), ino(b / "big/f.bin")) == before


def test_apply_links_and_keeps_bytes(tmp_path, capsys):
    a, b, lst = setup(tmp_path)
    m = tmp_path / "m.tsv"
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1", "--apply", "--manifest", str(m))
    assert r["applied"] == 2
    assert ino(a / "big/f.bin") == ino(b / "big/f.bin")
    assert (b / "big/f.bin").read_bytes() == BODY
    assert not os.stat(a / "big/f.bin").st_mode & 0o222    # in-place writes through any link fail
    assert m.read_text().count("\n") == 3


def test_apply_needs_manifest(tmp_path):
    a, b, lst = setup(tmp_path)
    with pytest.raises(SystemExit):
        D.main(["--trees", str(lst), "--apply"])


def test_recent_tree_refused(tmp_path, capsys):
    a, b, lst = setup(tmp_path)
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "6", "--min-size", "1")
    assert r["refused"] == 2 and r["rows"] == 0


def test_symlink_tree_refused(tmp_path, capsys):
    a, b, lst = setup(tmp_path)
    (tmp_path / "ln").symlink_to(a)
    lst.write_text(f"{tmp_path / 'ln'}\n{b}\n")
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1")
    assert r["refused"] == 1 and r["rows"] == 0


def test_dirty_file_not_linked(tmp_path, capsys):
    a, b, lst = setup(tmp_path)
    (b / "big/f.bin").write_bytes(b"y" * len(BODY))
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1", "--apply", "--manifest", str(tmp_path / "m"))
    assert ino(a / "big/f.bin") != ino(b / "big/f.bin")
    assert (b / "big/f.bin").read_bytes() == b"y" * len(BODY)


def test_same_stat_different_bytes_refused(tmp_path, capsys):
    a, b, lst = setup(tmp_path)
    f = b / "big/f.bin"
    st = os.stat(f)
    f.write_bytes(b"z" * len(BODY))        # same size, restored mtime: only the byte compare catches it
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1", "--apply", "--manifest", str(tmp_path / "m"))
    assert r["skipped"].get("bytes-differ") == 1
    assert f.read_bytes() == b"z" * len(BODY)


def test_exec_bit_groups_apart(tmp_path, capsys):
    a = tree(tmp_path / "a", {"f": BODY})
    b = tree(tmp_path / "b", {"f": BODY})
    os.chmod(b / "f", 0o755)
    subprocess.run(["git", "-C", str(b), "add", "-A"], check=True)
    lst = tmp_path / "t"
    lst.write_text(f"{a}\n{b}\n")
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1")
    assert r["rows"] == 0


def test_readonly_dir_skipped_without_flag(tmp_path, capsys):
    a, b, lst = setup(tmp_path)
    os.chmod(a / "big", 0o555)
    os.chmod(b / "big", 0o555)
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1", "--apply", "--manifest", str(tmp_path / "m"))
    assert r["skipped"].get("dir-readonly") == 1 and r["applied"] == 1
    os.chmod(a / "big", 0o755)
    os.chmod(b / "big", 0o755)


def test_inode_with_outside_link_frees_nothing():
    # inode 2 has two links but only one is in the listed trees: replacing it frees no bytes
    g = {(1, b"s" * 20, False, 100): [(b"/a", 1, 3, 1.0), (b"/b", 2, 2, 2.0)],
         (1, b"t" * 20, False, 50): [(b"/c", 3, 3, 1.0), (b"/d", 4, 1, 2.0)]}
    rows, freed, out = D.plan(g, D.MAX_NLINK)
    assert len(rows) == 2
    assert freed[1] == 50 and out[1] == 100


def test_container_mount_refused(tmp_path, capsys, monkeypatch):
    a, b, lst = setup(tmp_path)
    monkeypatch.setattr(D, "container_mounts", lambda: {str(a / "big")})
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1")
    assert r["refused_by"] == {"container-mount": 1} and r["rows"] == 0


def test_tree_under_a_mount_refused(tmp_path, capsys, monkeypatch):
    a, b, lst = setup(tmp_path)
    monkeypatch.setattr(D, "container_mounts", lambda: {str(tmp_path)})
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1")
    assert r["refused"] == 2


def test_unreadable_docker_refuses_all(tmp_path, capsys, monkeypatch):
    a, b, lst = setup(tmp_path)
    monkeypatch.setattr(D, "container_mounts", lambda: None)
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1")
    assert r["refused_by"] == {"docker-unreadable": 2}


@pytest.mark.parametrize("sub", ["kits/x", "items/y", "work/run/results", "a/6_final.odb"])
def test_kit_or_run_under_tree_refused(tmp_path, capsys, sub):
    a, b, lst = setup(tmp_path)
    if sub.endswith(".odb"):
        (a / sub).parent.mkdir(parents=True)
        (a / sub).write_bytes(b"x")
    else:
        (a / sub).mkdir(parents=True)
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1")
    assert r["refused_by"] == {"kit-or-run": 1}


def test_git_lock_refused(tmp_path, capsys):
    a, b, lst = setup(tmp_path)
    (a / ".git/index.lock").write_text("")
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1")
    assert r["refused_by"] == {"git-lock": 1}


def test_wave_src_refused():
    assert D.WAVE_SRC.search("/srv/opentallas-scratch2/claude/kw35/src_e2rd_lf")
    assert D.WAVE_SRC.search("/srv/opentallas-scratch3/claude/kw-fix-8/src_q")
    assert D.WAVE_SRC.search("/srv/opentallas-scratch3/claude/codex-wave-1105/src_7da_ad")
    assert not D.WAVE_SRC.search("/srv/opentallas-scratch2/claude/die-hbm-92/wt")


def test_mentioned_tree_refused(tmp_path, capsys):
    a, b, lst = setup(tmp_path)
    m = tmp_path / "mentions"
    m.write_text(f"{a}/big/f.bin\n")
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1", "--mentions", str(m))
    assert r["refused_by"] == {"mentioned": 1}


def test_lane_mention_holds_trees_below(tmp_path):
    assert D.lane_held({"/srv/s2/claude/lane"}, {"/srv/s2/claude/lane/wt"}) == {"/srv/s2/claude/lane/wt"}
    assert D.lane_held({"/srv/s2/claude"}, {"/srv/s2/claude/lane/wt"}) == set()


def test_exclude_keeps_the_file_out_on_both_sides(tmp_path, capsys):
    a, b, lst = setup(tmp_path)
    ex = tmp_path / "union"
    ex.write_text(f"h\t{a}/big\tprotected: x\n")
    before = ino(b / "big/f.bin")
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1", "--exclude", str(ex),
            "--apply", "--manifest", str(tmp_path / "m"))
    assert ino(b / "big/f.bin") == before and ino(a / "big/f.bin") != before
    assert r["applied"] == 1                     # tools/run.sh only


def test_record_files_never_linked(tmp_path, capsys):
    a = tree(tmp_path / "a", {"signoff/signoff.json": BODY, "x.signoff.json": BODY, "views/PROVENANCE.json": BODY})
    b = tree(tmp_path / "b", {"signoff/signoff.json": BODY, "x.signoff.json": BODY, "views/PROVENANCE.json": BODY})
    lst = tmp_path / "t"
    lst.write_text(f"{a}\n{b}\n")
    assert run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1")["rows"] == 0


def test_only_tree_limits_links(tmp_path, capsys):
    a, b, lst = setup(tmp_path)
    assert run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1", "--only-tree", str(a))["rows"] == 0  # a holds the kept files
    m = tmp_path / "m2"
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1", "--only-tree", str(b), "--manifest", str(m))
    rows = [l.split("\t") for l in m.read_text().splitlines()[1:]]
    assert r["rows"] == 2 and all(x[4].startswith(str(b)) for x in rows)


def test_kept_file_with_wrong_sha_not_linked(tmp_path, capsys):
    # both copies carry the same wrong bytes with the index stat restored: cmp passes, only the blob sha catches it
    a, b, lst = setup(tmp_path)
    for t in (a, b):
        f = t / "big/f.bin"
        st = os.stat(f)
        f.write_bytes(b"q" * len(BODY))
        os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
    r = run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1", "--apply", "--manifest", str(tmp_path / "m"))
    assert r["skipped"].get("kept-sha-mismatch") == 1
    assert ino(a / "big/f.bin") != ino(b / "big/f.bin")


def test_verify_detects_a_write_through_a_link(tmp_path, capsys):
    a, b, lst = setup(tmp_path)
    m, alert = tmp_path / "m", tmp_path / "ALERT"
    run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1", "--apply", "--manifest", str(m))
    assert D.main(["--verify", str(m), "--alert-file", str(alert)]) == 0
    assert not alert.exists()
    f = a / "big/f.bin"
    os.chmod(f, 0o644)                           # what root in a container effectively does
    f.write_bytes(b"w" * len(BODY))
    assert D.main(["--verify", str(m), "--alert-file", str(alert)]) == 3
    txt = alert.read_text()
    assert "ALERT" in txt and "f.bin" in txt
    assert (b / "big/f.bin").read_bytes() == b"w" * len(BODY)     # the write did reach the other tree: why detection exists


def test_verify_ignores_a_legally_deleted_tree(tmp_path, capsys):
    import shutil
    a, b, lst = setup(tmp_path)
    m = tmp_path / "m"
    run(capsys, "--trees", str(lst), "--min-idle-h", "0", "--min-size", "1", "--apply", "--manifest", str(m))
    shutil.rmtree(a, ignore_errors=True)
    shutil.rmtree(b, ignore_errors=True)
    assert D.main(["--verify", str(m)]) == 0
