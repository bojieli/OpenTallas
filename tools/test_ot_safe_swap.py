"""Regression tests for tools/ot_safe_swap.sh (guard v2). Run: python3 -m pytest tools/test_ot_safe_swap.py"""
import os, shutil, subprocess, pathlib, pytest
SH = pathlib.Path(__file__).with_name("ot_safe_swap.sh")

def run(tmp, *args, env=None):
    e = dict(os.environ, OT_SWAP_ALLOW_SAME_FS="1", HOME=str(tmp / "home"))
    e.update(env or {})
    return subprocess.run(["bash", str(SH), *args], capture_output=True, text=True, env=e)

@pytest.fixture
def lay(tmp_path):
    (tmp_path / "home").mkdir()
    src, dst = tmp_path / "a" / "t", tmp_path / "b" / "t"
    for d in (src, dst):
        (d / "x").mkdir(parents=True); (d / "x" / "f").write_text("1")
    ref = tmp_path / "protected.tsv"; ref.write_text("/some/other/path\n")
    return tmp_path, src, dst, ref

def test_ok_and_swap_removes_trash(lay):
    tmp, src, dst, ref = lay
    r = run(tmp, "--apply", "--refuse-file", str(ref), str(src), str(dst))
    assert r.returncode == 0 and "swapped" in r.stdout, r.stdout + r.stderr
    assert src.is_symlink() and not pathlib.Path(str(src) + ".swap-trash").exists()

def test_non_writable_dir_refused_tree_intact(lay):          # root-owned file / non-deletable tree
    tmp, src, dst, ref = lay
    os.chmod(src / "x", 0o555)
    try:
        r = run(tmp, "--apply", "--refuse-file", str(ref), str(src), str(dst))
        assert r.returncode == 3 and "not fully deletable" in r.stdout
        assert (src / "x" / "f").exists() and not src.is_symlink()
    finally:
        os.chmod(src / "x", 0o755)

def test_other_owner_file_refused(lay):
    tmp, src, dst, ref = lay
    if os.geteuid() == 0 or subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode != 0:
        pytest.skip("needs sudo -n to create a root-owned file")
    subprocess.run(["sudo", "-n", "chown", "root", str(src / "x" / "f")], check=True)
    try:
        r = run(tmp, "--apply", "--refuse-file", str(ref), str(src), str(dst))
        assert r.returncode == 3 and "not fully deletable" in r.stdout and (src / "x" / "f").exists()
    finally:
        subprocess.run(["sudo", "-n", "chown", os.environ.get("USER", "ubuntu"), str(src / "x" / "f")])

def test_protected_path_refused(lay):
    tmp, src, dst, ref = lay
    ref.write_text(f"{src}\n")
    r = run(tmp, "--apply", "--refuse-file", str(ref), str(src), str(dst))
    assert r.returncode == 3 and "named in" in r.stdout and not src.is_symlink()

def test_protected_parent_and_child_refused(lay):
    tmp, src, dst, ref = lay
    ref.write_text(f'{{"p": "{src.parent}"}}\n')
    assert run(tmp, "--refuse-file", str(ref), str(src), str(dst)).returncode == 3
    ref.write_text(f"{src}/x/f\n")
    assert run(tmp, "--refuse-file", str(ref), str(src), str(dst)).returncode == 3

def test_no_refusal_file_fails_closed(lay):
    tmp, src, dst, ref = lay
    r = run(tmp, str(src), str(dst))
    assert r.returncode == 3 and "fail closed" in r.stdout

def test_live_ref_refused(lay):
    tmp, src, dst, ref = lay
    if subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode != 0:
        pytest.skip("live-ref scan needs sudo -n")
    p = subprocess.Popen(["sleep", "30"], cwd=src)
    try:
        r = run(tmp, "--refuse-file", str(ref), str(src), str(dst))
        assert r.returncode == 3 and "LIVE" in r.stdout
    finally:
        p.kill()

def test_parent_symlink_loop_refused(lay):                   # the epyc4 kw45 case
    tmp, src, dst, ref = lay
    link = tmp / "c"; link.symlink_to(src.parent)
    r = run(tmp, "--refuse-file", str(ref), str(src), str(link / "t"))
    assert r.returncode == 3 and not src.is_symlink()
