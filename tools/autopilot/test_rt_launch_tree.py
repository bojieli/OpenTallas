import hashlib
import json
from pathlib import Path
import subprocess


def launch(source, runtime, target, *pins):
    script = Path(__file__).with_name("rt_launch_tree.sh")
    return subprocess.run(
        ["bash", str(script), str(source), str(runtime), str(target), *map(str, pins)],
        capture_output=True,
        text=True,
    )


def test_sealed_source_launch_metadata_is_not_inherited(tmp_path):
    source = tmp_path / "source"
    runtime = tmp_path / "runtime"
    target = tmp_path / "launch"
    (source / "tools").mkdir(parents=True)
    (runtime / "tools").mkdir(parents=True)
    (source / "tools/source-only.py").write_text("# retained source tool\n")
    (runtime / "tools/clock.py").write_text("# current runtime tool\n")
    source_stamp = source / ".rt_launch_ok"
    source_stamp.write_text('{"rt":"old runtime","src":"old source"}\n')
    (source / ".rt_launch_filled").write_text("stale source fill\n")
    for marker in (source_stamp, source / ".rt_launch_filled"):
        marker.chmod(0o444)
    source.chmod(0o555)

    result = launch(source, runtime, target)
    assert result.returncode == 0, result.stderr
    target_stamp = target / ".rt_launch_ok"
    assert not target_stamp.is_symlink()
    stamp = json.loads(target_stamp.read_text())
    assert stamp["src"] == str(source)
    assert stamp["rt"] == str(runtime)
    assert stamp["pins"] == {}
    assert (target / ".rt_launch_filled").read_text() == "tools/source-only.py\n"
    assert (target / "tools/clock.py").samefile(runtime / "tools/clock.py")
    assert source_stamp.read_text() == '{"rt":"old runtime","src":"old source"}\n'
    assert (source / ".rt_launch_filled").read_text() == "stale source fill\n"

    before = target_stamp.stat().st_mtime_ns
    assert launch(source, runtime, target).returncode == 0
    assert target_stamp.stat().st_mtime_ns == before
    result = launch(source, source, target)
    assert result.returncode == 97
    assert "incompatible launch stamp" in result.stderr
    assert target_stamp.stat().st_mtime_ns == before


def test_launch_stamp_must_be_local_and_match_pinned_tools(tmp_path):
    source = tmp_path / "source"
    runtime = tmp_path / "runtime"
    pin_runtime = tmp_path / "pin_runtime"
    target = tmp_path / "launch"
    source.mkdir()
    (runtime / "tools").mkdir(parents=True)
    (pin_runtime / "tools/die_plan").mkdir(parents=True)
    pinned = pin_runtime / "tools/die_plan/relay.py"
    pinned.write_text("# pinned relay tool\n")
    (runtime / "tools/die_plan").mkdir()
    digest = hashlib.sha256(pinned.read_bytes()).hexdigest()
    args = (pin_runtime, f"relay.py={digest}")

    result = launch(source, runtime, target, *args)
    assert result.returncode == 0, result.stderr
    assert launch(source, runtime, target, *args).returncode == 0
    assert launch(source, runtime, target).returncode == 97

    marker = target / ".rt_launch_ok"
    inherited = source / ".rt_launch_ok"
    marker.rename(inherited)
    marker.symlink_to(inherited)
    result = launch(source, runtime, target, *args)
    assert result.returncode == 97
    assert marker.is_symlink()


def test_cleanup_of_an_incomplete_launch_tree_never_changes_rt_inode_modes(tmp_path):
    """SEALED-INODE-SHARED (COORD 11-26): a stale L made of cp -al hard links of rt files is removed without chmod on the files: the rt inode modes stay a-w"""
    import os
    import stat
    source = tmp_path / "source"
    runtime = tmp_path / "runtime"
    target = tmp_path / "launch"
    (source / "tools").mkdir(parents=True)
    (runtime / "tools/sub").mkdir(parents=True)
    f1, f2 = runtime / "tools/clock.py", runtime / "tools/sub/deep.py"
    f1.write_text("# rt tool\n")
    f2.write_text("# rt deep tool\n")
    for f in (f1, f2):
        f.chmod(0o444)
    for d in (runtime / "tools/sub", runtime / "tools", runtime):
        d.chmod(0o555)
    # an incomplete launch tree: hard links of rt files, dirs read-only, no .rt_launch_ok
    subprocess.run(["cp", "-al", str(runtime / "tools"), str(target)], check=True)       # target/ = links of rt/tools, no stamp
    os.chmod(target / "sub", 0o555)
    os.chmod(target, 0o555)
    assert (target / "clock.py").samefile(f1) and f1.stat().st_nlink == 2
    try:
        result = launch(source, runtime, target)
        assert result.returncode == 0, result.stderr
        for f in (f1, f2):
            assert stat.S_IMODE(f.stat().st_mode) == 0o444, f           # the rt inodes are still a-w
        assert f1.read_text() == "# rt tool\n" and f2.read_text() == "# rt deep tool\n"
        assert (target / ".rt_launch_ok").is_file() and (target / "tools/clock.py").samefile(f1)
    finally:
        for d in (runtime, runtime / "tools", runtime / "tools/sub"):
            d.chmod(0o755)


def test_script_has_no_recursive_file_chmod():
    """no chmod -R u+w anywhere in the launch script: that is the corruption path into sealed rt"""
    text = Path(__file__).with_name("rt_launch_tree.sh").read_text()
    code = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    assert not any("chmod -R" in ln.split("#")[0] for ln in code)
