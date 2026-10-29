#!/usr/bin/env python3
"""Opt-in physical-only preservation for emitted SAMECLK host CDC face RTL.

Usage: cdc_control_preserve.py INPUT.v OUTPUT.v RECEIPT.json [u_done,u_ing]
The optional member list also supports CDC_PC u_rx,u_tx. No default flow changes."""
import hashlib
import json
import re
import sys
from pathlib import Path

def no_attrs(s):
    return re.sub(r'\(\*.*?\*\)\s*', '', s, flags=re.S)

def patch(s, members=('u_done', 'u_ing')):
    old = s
    changed = []
    for member in members:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', member):
            raise ValueError('invalid member name')
        swv = '\\' + member + '.g_sf.u_sf.swv'
        pat = r'(?m)^(  reg ' + re.escape(swv) + r' ;)$'
        s, n = re.subn(pat, r'  (* keep = 1 *)\n\1', s)
        if n != 1:
            raise ValueError(f'expected one internal swv flop: {swv}, found {n}')
        changed.append('keep internal duplicate ' + swv)
        alias = '\\' + member + '.g_ops2.ovp'
        pat = r'(?m)^  \(\* keep = [^\n]* \*\)\n(  wire ' + re.escape(alias) + r' ;)$'
        s, n = re.subn(pat, r'\1', s)
        if n != 1:
            raise ValueError(f'expected one kept output-only alias: {alias}, found {n}')
        changed.append('drop dead alias keep ' + alias)
    if no_attrs(s) != no_attrs(old):
        raise ValueError('physical preservation unexpectedly changed RTL logic')
    return s, changed

if __name__ == '__main__':
    src, out, report = map(Path, sys.argv[1:4])
    members = tuple(sys.argv[4].split(',')) if len(sys.argv)>4 else ('u_done', 'u_ing')
    old = src.read_text()
    new, changed = patch(old, members)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(new)
    report.write_text(json.dumps(dict(source=str(src), source_sha256=hashlib.sha256(old.encode()).hexdigest(),
        output_sha256=hashlib.sha256(new.encode()).hexdigest(), changes=changed,
        attribute_stripped_byte_identity=True, cycles_added=0), indent=1) + '\n')
