"""Derived ECO capsules carry seed inputs, never transport locality markers."""
import os
from pathlib import Path
import subprocess


def test_actual_prd_seed_copy_excludes_transport_markers(tmp_path):
    script = Path(__file__).with_name('post_route_drv') / 'prd_mk.sh'
    text = script.read_text()
    copy = text[text.index('OUT_EXCLUDE=()'):text.index('\nB=$OUT/run/results')]
    source, out = tmp_path / 'source', tmp_path / 'result'
    (source / 'macros').mkdir(parents=True)
    out.mkdir()
    for p in (source / '.ot-run-spill-copy', source / 'macros/.ot-run-spill-copy'):
        p.write_text('old transport owner')
    (source / 'freeze.json').write_text('{"clock":"captured"}')
    (source / '.keep').write_text('')
    os.utime(source / 'freeze.json', (100,100))
    subprocess.run(['bash','-c',copy],env=dict(os.environ,KIT=str(source),OUT=str(out)),check=True)
    assert not list(out.rglob('.ot-run-spill-copy'))
    assert (out / 'freeze.json').read_text() == '{"clock":"captured"}'
    assert (out / 'freeze.json').stat().st_mtime_ns == (source / 'freeze.json').stat().st_mtime_ns
    assert (out / '.keep').is_file()
