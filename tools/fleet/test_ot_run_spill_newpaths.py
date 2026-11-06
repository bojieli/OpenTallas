"""Spill result copy-back retains newly seeded old-mtime inputs."""
import os
import shlex
import subprocess
from pathlib import Path
from test_ot_run_scratch_disk import m


def test_written_union_preserves_new_old_mtime_and_required_metadata(tmp_path):
    kit = tmp_path / 'kit'
    kit.mkdir()
    old = 1_000_000_000
    for name in ('bulk.odb', 'changed.v', 'freeze.json'):
        (kit / name).write_text('seed')
        os.utime(kit / name, (old, old))
    stamp = tmp_path / 'stamp'
    stamp.write_text('')
    (tmp_path / 'stamp.inputs').write_bytes(b''.join(os.fsencode(str(p).lstrip('/')) + b'\0' for p in kit.iterdir()))
    # cp -a creates a fresh directory/path with the seed's unchanged old timestamp.
    new = kit / 'i1'
    new.mkdir()
    (new / 'freeze.json').write_text('new frozen clock contract')
    os.utime(new / 'freeze.json', (old, old))
    (kit / 'changed.v').write_text('ordinary changed output')
    os.utime(kit / 'changed.v', ns=(stamp.stat().st_mtime_ns + 1000000,) * 2)
    command = m.spill_written_listing([str(kit)], str(stamp))
    result = subprocess.run(['bash', '-c', 'cd / && ' + command], capture_output=True, check=True)
    selected = {Path(os.fsdecode(p)).name if p else '' for p in result.stdout.split(b'\0')} - {''}
    assert selected == {'freeze.json', 'changed.v'}
    assert os.fsencode(str(new / 'freeze.json').lstrip('/')) in result.stdout.split(b'\0')
    assert os.fsencode(str(kit / 'bulk.odb').lstrip('/')) not in result.stdout.split(b'\0')


def test_forward_captures_baseline_and_late_proof_remains_exact(tmp_path):
    cmd = m.spill_fwd_cmd('src', 'dst', ['/srv/opentallas-scratch2/claude/a'], '/tmp/s')
    assert '/tmp/s.inputs' in cmd and '-print0' in cmd
    cmd = m.spill_back_cmd('src', 'dst', ['/srv/opentallas-scratch2/claude/a'], '/tmp/s', only=['/srv/opentallas-scratch2/claude/a/lec'])
    assert 'freeze.json' not in cmd and '.inputs' not in cmd
