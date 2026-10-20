"""Checkpoint handoff must survive protected hardlinks and refuse missing inputs."""
from pathlib import Path
import subprocess

SCRIPT = Path(__file__).parent / "chain/die_chain.sh"


def place_function():
    source = SCRIPT.read_text()
    return source[source.index("place() {"):source.index("\ncase $DIE", source.index("place() {"))]


def test_checkpoint_copy_fallback(tmp_path):
    source = tmp_path / "root owned.odb"
    target = tmp_path / "checkpoint.odb"
    source.write_bytes(b"current checkpoint")
    target.write_bytes(b"stale checkpoint")
    result = subprocess.run(["bash", "-c", place_function() +
                             '\nln() { return 1; }; place "$1" "$2"', "place", str(source), str(target)])
    assert result.returncode == 0
    assert target.read_bytes() == source.read_bytes()
    assert source.exists()


def test_missing_checkpoint_refuses(tmp_path):
    result = subprocess.run(["bash", "-c", place_function() +
                             '\nplace "$1" "$2"', "place", str(tmp_path / "absent.odb"), str(tmp_path / "dest.odb")])
    assert result.returncode != 0


def test_multi_output_copy_fallback(tmp_path):
    sources = [tmp_path / name for name in ("route.guide", "die_grt.spef", "ckpt_grt.odb")]
    for number, path in enumerate(sources):
        path.write_text(str(number))
    target = tmp_path / "sta"
    target.mkdir()
    result = subprocess.run(["bash", "-c", place_function() +
                             '\nln() { return 1; }; place "$@"', "place", *map(str, sources), str(target)])
    assert result.returncode == 0
    assert all((target / source.name).read_bytes() == source.read_bytes() for source in sources)
