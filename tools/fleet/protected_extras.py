#!/usr/bin/env python3
"""Reconcile manual protection extras with explicit owner retirement receipts.

Only the manual extra cache is filtered. Automatic SIGNED/NEAR-COUNT rows and
missing-path checks remain untouched. A retirement matches one exact host/path;
missing directories alone never retire a protection. No files/directories/jobs
named by a protection are modified.
"""
import argparse
import fcntl
from pathlib import Path
import os
import shlex
import tempfile


def key(line):
    if not line.strip() or line.lstrip().startswith('#'):
        return None
    cols = line.rstrip('\n').split('\t')
    if len(cols) < 2 or not cols[1].startswith('/'):
        raise ValueError('invalid protection row: expected host<TAB>absolute path')
    return cols[0], cols[1].rstrip('/')


def retired_keys(receipts):
    out = set()
    for line in Path(receipts).read_text().splitlines():
        k = key(line)
        if k is None:
            continue
        cols = line.split('\t')
        if len(cols) < 4 or not cols[2] or not cols[3]:
            raise ValueError('retirement requires owner commit and reason')
        out.add(k)
    return out


def reconcile(extras, receipts, additions=None, write=False):
    """Locked read/merge/filter of the manual cache; retain all other rows verbatim."""
    extras = Path(extras)
    with Path(str(extras) + '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        retired = retired_keys(receipts)  # absent/bad receipts fail before writing
        rows = extras.read_text().splitlines(keepends=True)
        if additions is not None:
            seen = {x.rstrip('\n') for x in rows}
            for line in Path(additions).read_text().splitlines():
                if line and line not in seen:
                    rows.append(line + '\n')
                    seen.add(line)
        active = ''.join(line for line in rows if key(line) not in retired)
        if write:
            mode = extras.stat().st_mode & 0o777
            fd, tmp = tempfile.mkstemp(prefix=extras.name + '.', dir=extras.parent)
            try:
                with os.fdopen(fd, 'w') as stream:
                    stream.write(active)
                os.chmod(tmp, mode)
                os.replace(tmp, extras)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        return active


def hooks(source_dir, out_dir, receipts):
    """Generate OWN compatible cycle/regen copies; never edit paused lane code.

    The counted-record generator, scan guards and audit remain byte-identical.
    Only manual cache merge/render sites are replaced by the explicit filter.
    """
    source_dir, out_dir = Path(source_dir).resolve(), Path(out_dir).resolve()
    if source_dir == out_dir:
        raise ValueError('hooks require a distinct owned output directory')
    helper = Path(__file__).resolve()
    extra = source_dir / 'extra_protect.tsv'
    shared = f'python3 {shlex.quote(str(helper))} --extras {shlex.quote(str(extra))} --retired {shlex.quote(str(Path(receipts).resolve()))}'
    cycle = (source_dir / 'cycle.sh').read_text()
    regen = (source_dir / 'regen_protect.sh').read_text()
    merge = 'cat newlane$N.tsv >> extra_protect.tsv'
    render = 'cat extra_protect.tsv;'
    run = 'bash regen_protect.sh'
    if cycle.count(merge) != 1 or cycle.count(run) != 1 or regen.count(render) != 1:
        raise ValueError('protection generator anchors changed; originals untouched')
    out_dir.mkdir(parents=True, exist_ok=True)
    if (out_dir / 'cycle.sh').exists() or (out_dir / 'regen_protect.sh').exists():
        raise ValueError('owned hook output already exists; preserve it')
    cycle = cycle.replace(merge, shared + ' --add "newlane$N.tsv" --write >/dev/null')
    cycle = cycle.replace(run, 'bash ' + shlex.quote(str(out_dir / 'regen_protect.sh')))
    regen = regen.replace(render, shared + ';')
    (out_dir / 'cycle.sh').write_text(cycle)
    (out_dir / 'regen_protect.sh').write_text(regen)
    return out_dir / 'cycle.sh'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--extras')
    p.add_argument('--retired', required=True)
    p.add_argument('--add')
    p.add_argument('--write', action='store_true')
    p.add_argument('--hook-source')
    p.add_argument('--hook-out')
    a = p.parse_args()
    if a.hook_source:
        if not a.hook_out:
            p.error('--hook-source requires --hook-out')
        print(hooks(a.hook_source, a.hook_out, a.retired))
    elif a.extras:
        print(reconcile(a.extras, a.retired, a.add, a.write), end='')
    else:
        p.error('pass --extras or --hook-source/--hook-out')


if __name__ == '__main__':
    main()
