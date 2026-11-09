import importlib.util
import json
import os
import subprocess
from pathlib import Path

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
    import pytest
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
