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
