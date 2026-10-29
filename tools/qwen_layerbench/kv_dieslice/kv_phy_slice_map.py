#!/usr/bin/env python3
"""TOK-KV-2 10-28: GENERATE the HBM PHY slice -> bound partition map that kv_preload.py needs, from the bind itself
(never the hand-kept bind/asbuilt_map.json of an older bind).

Sources (all outputs of the bind of record):
  BIND/bind_names.json      '<partition>.u_core' -> as-built leaf 'phy_<S>[.u_sub].u_s<k>'
  TOP (bound top .sv)       every mapped partition is instantiated there, and its partition type holds
                            'qkd_hbm3e_phy_pc4 u_core' (the 4-PC slice the bench model replaces)
  SLICES (kv_phy_slices.sv) the binder's slice view: as-built u_s<k> owns PCs 4k..4k+3 (pi0 of u_s<k> = pi<4k>)
Fails closed unless all 4 stacks x 8 slices map one-to-one.
    kv_phy_slice_map.py BIND_NAMES TOP SLICES > phy_slice_map.json
Output: {"parts": {"phy_<S>.u_s<k>": "phy_<S>_<j>"}, "asbuilt": {...: as-built name}, "sources": {file: sha256}}
"""
import hashlib
import json
import re
import sys
from pathlib import Path

STACKS = ('EN', 'ES', 'WN', 'WS')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def slice_pcs(text):
    """kv_phy_slices.sv qkd_hbm3e_phy_pc_s8: u_s<k> -> PC of its pi0..pi3 ports."""
    m = re.search(r'module\s+qkd_hbm3e_phy_pc_s8\b(.*?)endmodule', text, re.S)
    if not m:
        raise SystemExit('kv_phy_slice_map: no qkd_hbm3e_phy_pc_s8 in SLICES')
    out = {}
    for k, body in re.findall(r'qkd_hbm3e_phy_pc4\s+u_s(\d+)\s*\((.*?)\);', m.group(1), re.S):
        out[int(k)] = [int(re.search(r'\.pi%d\(pi(\d+)\)' % i, body).group(1)) for i in range(4)]
    return out


def build(names, top_text, rtl_dir, slices_text):
    errs = []
    pcs = slice_pcs(slices_text)
    for k in range(8):
        if pcs.get(k) != [4 * k + i for i in range(4)]:
            errs.append(f'slice u_s{k} PCs {pcs.get(k)} != 4k..4k+3')
    parts, asb = {}, {}
    for key, leaf in names.items():
        m = re.fullmatch(r'phy_([A-Z]{2})(?:\.u_sub)?\.u_s(\d+)', leaf)
        if not m:
            continue
        part, _, inst = key.partition('.')
        if inst != 'u_core':
            errs.append(f'{key}: slice leaf is not the partition u_core')
        slot = f'phy_{m.group(1)}.u_s{m.group(2)}'
        if slot in parts:
            errs.append(f'{slot} bound twice ({parts[slot]}, {part})')
        parts[slot] = part
        asb[slot] = leaf
        t = re.search(r'^\s*(\w+)\s+(?:#\(.*?\)\s*)?%s\s*\(' % re.escape(part), top_text, re.M)
        if not t:
            errs.append(f'{part}: not instantiated in the bound top')
            continue
        tf = Path(rtl_dir) / f'{t.group(1)}.sv'
        if not tf.exists() or not re.search(r'qkd_hbm3e_phy_pc4\s+u_core\b', tf.read_text()):
            errs.append(f'{part}: type {t.group(1)} has no qkd_hbm3e_phy_pc4 u_core')
    want = {f'phy_{s}.u_s{k}' for s in STACKS for k in range(8)}
    if set(parts) != want:
        errs.append(f'slots missing {sorted(want - set(parts))} extra {sorted(set(parts) - want)}')
    if len(set(parts.values())) != len(parts):
        errs.append('partition holds more than one slice')
    return dict(sorted(parts.items())), dict(sorted(asb.items())), errs


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    bn, top, sl = sys.argv[1:]
    parts, asb, errs = build(json.loads(Path(bn).read_text()), Path(top).read_text(), Path(top).parent,
                             Path(sl).read_text())
    if errs:
        for e in errs:
            print('kv_phy_slice_map: FAIL', e, file=sys.stderr)
        raise SystemExit(2)
    moved = sum(1 for s, p in parts.items() if p != s.replace('.u_s', '_'))
    json.dump(dict(schema='opentallas.kv.phy_slice_map.v1', parts=parts, asbuilt=asb,
                   sources={bn: sha(bn), top: sha(top), sl: sha(sl)}), sys.stdout, indent=1)
    print()
    print(f'kv_phy_slice_map: PASS {len(parts)} slices, {moved} not at phy_<S>_<k>', file=sys.stderr)


if __name__ == '__main__':
    main()
