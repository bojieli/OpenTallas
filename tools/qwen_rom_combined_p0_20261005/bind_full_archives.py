#!/usr/bin/env python3
"""Bind the generated 5.050 top to genuine retained protectlib archives.

Repairs the missing hierarchical make include without any frontend or child
build. Validate literal DPI signatures and archive symbols before writing it.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def declarations(path):
    return set(' '.join(x.split()) for x in
               re.findall(r'^\s*extern\s+[^\n]+;', path.read_text(), re.M))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--authority', type=Path, required=True)
    a = p.parse_args()
    record = json.loads((a.output/'prepared.json').read_text())
    generated = a.output/'die'
    mk = (generated/'Vdie.mk').read_text()
    if 'VERILATOR_ROOT = '+record['canonical_runtime'] not in mk or '5.050' not in record['version']:
        raise RuntimeError('actual generated 5.050 runtime differs from retained engines')
    required = declarations(generated/'Vdie__Dpi.h')
    retained = declarations(a.authority/'die/Vdie__Dpi.h')
    if not required or not required <= retained:
        raise RuntimeError('current DPI module/header ABI differs from retained top')
    libraries = [Path(p) for p in record['reused_archives'] if Path(p).name.startswith('libot_')]
    symbols = set()
    pins = {}
    for library in libraries:
        nm = subprocess.check_output(['nm', '-g', '--defined-only', str(library)], text=True)
        symbols.update(line.split()[-1] for line in nm.splitlines() if len(line.split()) >= 3)
        pins[str(library)] = hashlib.sha256(library.read_bytes()).hexdigest()
    imports = {re.search(r'(\w+)\s*\(', prototype)[1] for prototype in required}
    if not imports <= symbols:
        raise RuntimeError('actual retained protectlibs do not define '+str(sorted(imports-symbols)))
    fragment = '# Genuine retained 5.050 protectlibs; top-only build, no child targets.\n'
    fragment += 'VM_HIER_LIBS := '+' '.join(map(str, libraries))+'\n'
    with (generated/'Vdie_hier.mk').open('x') as f:
        f.write(fragment)
    result = dict(status='PASS_ACTUAL_HEADER_ARCHIVE_BINDING_ONLY',
                  required_DPI_prototypes=sorted(required), actual_import_symbols=sorted(imports),
                  readonly_archive_sha256=pins, canonical_runtime=record['canonical_runtime'],
                  make_fragment=fragment, frontend_rerun=False, engine_rebuild=False,
                  full_token_pass=False, physical_qualified=False)
    (a.output/'archive_binding.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(status=result['status'], matched_imports=len(imports), retained_archives=len(libraries))))


if __name__ == '__main__':
    main()
