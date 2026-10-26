#!/usr/bin/env python3
"""PATH-S81/F2 10-25: hard-child parameter overrides stripped from a frame kit are RECORDED, never dropped.

A hard view (LEF + liberty) has no parameters, so the physical kit instantiates every hard child without #() (ORFS
read_verilog rejects overrides on a liberty black box).  The view was hardened with those overrides (the q element view
ot_v41_rom_elem_q_qxpq_w10 is NB=2: pval 64 / prow 32 / pv 2 bits), but any tool that reads the kit RTL against the RTL
of the hard master (the die as-built bind: tools/die_plan/bind_elab.py lib stubs) used to see the RTL defaults (NB=1) and
tied lane 1 of every qbank (F2 class, 54,432 bits die-wide).

strip_hard() removes the overrides AND returns the hardened parameter set per master; it fails closed when one master is
instantiated with two different override sets (one hard view cannot be both) or with an override whose value is not a
constant (it cannot be baked).  write_sidecar() stores the set beside the kit as <kit>.hard_params.json; the bind manifest
key "hard_params" lists the sidecars and bind_elab.lib_stubs() bakes the values into the hard master's interface stub
(fail closed there too: unknown master / undeclared parameter / conflicting sidecars).

  hard_params.py SRC.sv --hard M1,M2,... --out KIT.hard_params.json [--check-kit KIT.sv]
      record the hardened set of an existing kit without rebuilding it (--check-kit: the kit must hold the same number of
      hard sites and no hard-master #() left)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = 'opentallas.frame_kit.hard_params.v1'
# simulation labels only (no hardware effect, no port width): never baked.  INSTANCE names the ROM image / print label;
# dsfd_bf_col MB names the column ROM image (ot_v41_bf_col header: "which column (simulation ROM image name only)")
LABELS = frozenset({'INSTANCE', 'MB'})
HARD_STRIP = re.compile(r"^(\s*)([a-zA-Z]\w*)\s*#\(((?:[^()]|\([^()]*\))*)\)\s*(u_\w+)\s*\(", re.M)
CONST = re.compile(r"""\s*(?:-?\d+|\d*'[sS]?[bBoOdDhH][0-9a-fA-FxXzZ_?]+|-?\d+\.\d+|"[^"]*")\s*""")


def _split_top(s):
    """split a named-override list at its top-level commas"""
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch in '({[':
            depth += 1
        elif ch in ')}]':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def parse_overrides(body, where=''):
    """'.NB(2), .MTP(1), ...' -> {'NB': '2', ...}; positional overrides cannot be recorded -> fail"""
    ov = {}
    for item in _split_top(body):
        m = re.fullmatch(r"\s*\.(\w+)\s*\((.*)\)\s*", item, re.S)
        if not m:
            raise SystemExit(f'hard_params: {where}: positional / unparsed parameter override {item.strip()!r}')
        ov[m.group(1)] = m.group(2).strip()
    return ov


def strip_hard(text, hard, where=''):
    """-> (text without #() on hard children, #() sites seen (hard + soft: the kit header count), {master: {param: value}} hardened set).  Fail closed on
    an unbakeable (non-constant) value or two different override sets on one master."""
    sets, sites = {}, {}

    def rep(m):
        master, inst = m.group(2), m.group(4)
        if master not in hard:
            return m.group(0)
        ov = {k: v for k, v in parse_overrides(m.group(3), f'{where} {inst}').items() if k not in LABELS}
        bad = {k: v for k, v in ov.items() if not CONST.fullmatch(v)}
        if bad:
            raise SystemExit(f'hard_params: {where} {master} {inst}: override(s) not a constant, cannot be baked: {bad}')
        prev = sets.setdefault(master, ov)
        if prev != ov:
            diff = {k: (prev.get(k), ov.get(k)) for k in sorted(set(prev) | set(ov)) if prev.get(k) != ov.get(k)}
            raise SystemExit(f'hard_params: {where} {master}: {inst} overrides differ from {sites[master][0]} {diff} -- '
                             'one hard view cannot hold two configurations (uniquify the view first)')
        sites.setdefault(master, []).append(inst)
        return f'{m.group(1)}{master} {inst} ('

    t2, n = HARD_STRIP.subn(rep, text)
    for master in sorted(hard):
        if re.search(rf"^\s*{re.escape(master)}\s*#\(", t2, re.M):
            raise SystemExit(f'hard_params: {where} {master}: an override survived the strip (unrecognised form)')
    return t2, n, {m: dict(sorted(sets[m].items())) for m in sorted(sets)}, {m: len(v) for m, v in sorted(sites.items())}


def write_sidecar(path, params, sites, src, src_text):
    rec = dict(schema=SCHEMA, source=str(src), source_sha256=hashlib.sha256(src_text.encode()).hexdigest(),
               note='hardened parameter set of each hard child whose #() the kit stripped (labels '
                    + ', '.join(sorted(LABELS)) + ' excluded); bind_elab bakes these into the hard master stubs',
               sites=sites, masters=params)
    Path(path).write_text(json.dumps(rec, indent=1) + '\n')
    return rec


def sidecar_path(kit):
    kit = str(kit)
    return (kit[:-3] if kit.endswith('.sv') else kit) + '.hard_params.json'


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('src')
    ap.add_argument('--hard', required=True, help='comma-separated hard master names')
    ap.add_argument('--out', required=True)
    ap.add_argument('--check-kit')
    ap.add_argument('--root', default='.', help='paths in the record are relative to this')
    a = ap.parse_args()
    hard = set(a.hard.split(','))
    t = Path(a.src).read_text()
    t2, n, params, sites = strip_hard(t, hard, a.src)
    if a.check_kit:
        k = Path(a.check_kit).read_text()
        left = [m for m in hard if re.search(rf"^\s*{re.escape(m)}\s*#\(", k, re.M)]
        if left:
            raise SystemExit(f'hard_params: {a.check_kit} still carries #() on hard masters {left}')
        hdr = re.search(r'hard-child #\(\) overrides removed \((\d+) sites\)', k)
        if hdr and int(hdr.group(1)) != n:
            raise SystemExit(f'hard_params: {a.check_kit} records {hdr.group(1)} stripped sites, {a.src} has {n}')
    try:
        src = Path(a.src).resolve().relative_to(Path(a.root).resolve())
    except ValueError:
        src = Path(a.src)
    write_sidecar(a.out, params, sites, src, t)
    print(json.dumps(dict(out=a.out, sites=n, masters={m: len(p) for m, p in params.items()})))


if __name__ == '__main__':
    sys.exit(main())
