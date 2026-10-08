"""Read-only evidence probe for completed routes with broken post-route helpers."""
import glob
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys

HELPER_ERROR = re.compile(r"(?:NameError|ImportError|ModuleNotFoundError):|(?:error: )?unrecognized arguments:|unexpected keyword argument")


def probe(config):
    root = Path(config['route_root'])
    markers = {}
    for name in ('status', 'exit'):
        p = root / name
        if p.is_file():
            text = p.read_text()
            values = dict(re.findall(r'^(flow_rc|rc)=(-?\d+)\s*$', text, re.M))
            if values:
                markers[str(p)] = dict(values=values, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    # A stale checkpoint next to a failed physical attempt is not completion.
    if not markers or any(int(v) != 0 for m in markers.values() for v in m['values'].values()):
        return None
    artifacts = []
    for pattern in config['odb_patterns']:
        for name in glob.glob(pattern):
            p = Path(name)
            if p.is_file() and p.stat().st_size:
                st = p.stat()
                artifacts.append(dict(path=str(p), bytes=st.st_size, mtime_ns=st.st_mtime_ns))
    if not artifacts:
        return None
    errors = []
    for name in ('corner.log', 'abstract.log', 'abstract_ss.log', 'abstract_ff.log'):
        p = root / name
        if not p.is_file():
            continue
        with p.open('rb') as f:
            f.seek(max(0, p.stat().st_size - 65536))
            tail = f.read()
        text = tail.decode(errors='replace')
        if HELPER_ERROR.search(text):
            errors.append(dict(path=str(p), tail=text, tail_sha256=hashlib.sha256(tail).hexdigest()))
    if not errors:
        return None
    return dict(route_root=str(root), completion_markers=markers, artifacts=artifacts, helper_errors=errors)


def remote_command(config):
    # Ship only this stdlib probe; never rewrite the job's pinned source/helpers.
    return 'python3 - ' + shlex.quote(json.dumps(config)) + " <<'POSTROUTE_PROBE'\n" + Path(__file__).read_text() + '\nPOSTROUTE_PROBE\n'


if __name__ == '__main__':
    print(json.dumps(probe(json.loads(sys.argv[1]))))
