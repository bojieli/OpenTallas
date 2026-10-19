#!/usr/bin/env python3
"""Give die masters private transitive RTL namespaces, without modifying pinned sources.

The manifest lists the intended source files from each master's immutable synthesis inventory.  All module
identifiers in a family receive the same suffix; primitive SRAM names remain external.  The transform must invert
byte-for-byte for every input, and records both hashes.  This is source disambiguation, not a timing qualification:
the renamed masters require fresh source-bound synthesis before their timing can be used.
"""
import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def scope_family(root, family, config):
    suffix = '__d4g_' + family
    files = config['sources']
    blobs = {f: (root / f).read_text() for f in files}
    names = set()
    for f, text in blobs.items():
        clean = re.sub(r'/\*.*?\*/|//[^\n]*', ' ', text, flags=re.S)
        if re.search(r'^\s*`include\b', clean, re.M):
            raise ValueError(f'{f}: include must be explicitly resolved before scoping')
        names.update(re.findall(r'^\s*(?:\(\*.*?\*\)\s*)*module\s+(?:automatic\s+)?(\w+)', clean, re.M))
    if config['master'] not in names:
        raise ValueError(f'{family}: top absent from source inventory')
    if any(n.endswith(suffix) for n in names):
        raise ValueError(f'{family}: namespace is already present')
    # Retain the die-visible master/pin identity. Only private child module names change; the contract's explicit
    # source selects this top, so floorplan grants and latency-class dispatch keep their existing identity.
    mapping = {n: n + suffix for n in names if n != config['master']}
    inverse = {v: k for k, v in mapping.items()}
    transform = lambda text, m: re.sub(r'\b[A-Za-z_]\w*\b', lambda x: m.get(x[0], x[0]), text)
    out = Path('rtl/hbm_accel/die_glue/scoped_d4g') / (family + '.sv')
    parts, records = [], []
    for f, text in blobs.items():
        renamed = transform(text, mapping)
        if transform(renamed, inverse) != text:
            raise ValueError(f'{f}: inverse transform differs')
        records.append(dict(path=f, sha256=digest(text.encode()), scoped_sha256=digest(renamed.encode())))
        parts.append('// Scoped source: ' + f + '\n' + renamed + '\n')
    target = root / out
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(''.join(parts))
    return dict(master=config['master'], source=str(out), sources=records,
                names=mapping, sha256=digest(target.read_bytes()), inverse_byte_exact=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('contract')
    ap.add_argument('out')
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--report', required=True)
    ap.add_argument('--root', default='.')
    a = ap.parse_args()
    root = Path(a.root)
    with gzip.open(a.contract, 'rt') if a.contract.endswith('.gz') else open(a.contract) as f:
        contract = json.load(f)
    manifest = json.loads(Path(a.manifest).read_text())
    families = {n: scope_family(root, n, c) for n, c in manifest.items()}
    old = {c['master']: families[n] for n, c in manifest.items()}
    count = 0
    for inst in contract['instances'].values():
        if inst['master'] in old:
            row = old[inst['master']]
            inst.update(master=row['master'], source=row['source'], rtl_deps=[])
            count += 1
    # Contract straps carry a master identity too, even for masters whose port names are unchanged.
    for strap in contract.get('straps', []):
        if strap.get('master') in old:
            strap['master'] = old[strap['master']]['master']
    Path(a.out).write_text(json.dumps(contract, separators=(',', ':')) + '\n')
    Path(a.report).write_text(json.dumps(dict(instances=count, families=families), indent=1) + '\n')
    print(f'L14_SCOPED instances={count} families={len(families)} inverse_byte_exact=PASS')


if __name__ == '__main__':
    main()
