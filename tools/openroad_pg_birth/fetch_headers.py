#!/usr/bin/env python3
"""Fetch exact official public headers used by the pinned native extension."""
import argparse, hashlib, json, urllib.request
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('directory', type=Path)
a = p.parse_args()
m = json.loads(Path(__file__).with_name('headers.json').read_text())
for r in m['headers']:
    f = a.directory / r['path']
    data = f.read_bytes() if f.exists() else urllib.request.urlopen(
        f"https://raw.githubusercontent.com/{m['repo']}/{m['revision']}/{r['source']}", timeout=30).read()
    if hashlib.sha256(data).hexdigest() != r['sha256']:
        raise ValueError('header identity differs: ' + r['path'])
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open('xb') as out:
            out.write(data)
print('PINNED_OPENDB_HEADERS_PASS', len(m['headers']))
