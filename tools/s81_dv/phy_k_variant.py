#!/usr/bin/env python3
"""BIND/mu4 (10-19): derive the S81 K-only HBM macro abstract ot_hbm3e_phy_v41x_aw30_e8p5_k from the generic
ot_hbm3e_phy_v41x_aw30_e8p5 views (physical/asap7_memory_macros_v2/<macro>/: _bb.v, .lef, _{tt,ff,ss}.lib, .json).

The S81 die never uses the W port (the QE weight region: weights are in the ROM field) and nothing on the die reads the
model counters refreshes / w_reads, so the strict die bind saw OUTPUT_OPEN on w_rdy / w_room / wr_* / w_oor / refreshes /
w_reads and pads on w_v / w_addr / w_len / w_tag / wr_rdy.  The K-only macro has none of these pins (removed at the
source, not tied); k_oor stays and is wired to a die status pin by the binder.  Same outline, same K / kr / clk / rst_n
pin shapes, timing arcs and PDN: the variant is the generic abstract with the W / counter PIN, bus and type groups
deleted and the cell renamed.  Functional model: rtl/dsrom_sys/s81_link/ot_hbm3e_phy_v41x_aw30_e8p5_k.sv.

  phy_k_variant.py [--root physical/asap7_memory_macros_v2]      (writes <root>/ot_hbm3e_phy_v41x_aw30_e8p5_k/)
"""
import argparse, hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = 'ot_hbm3e_phy_v41x_aw30_e8p5'
DST = SRC + '_k'
DROP = ('w_v', 'w_rdy', 'w_addr', 'w_len', 'w_tag', 'w_room', 'wr_v', 'wr_rdy', 'wr_tag', 'wr_beat', 'wr_data',
        'w_oor', 'refreshes', 'w_reads')


def rename(t):
    return re.sub(r'\b' + SRC + r'(?=\b|_)', DST, t)


def lef(t):
    out, skip, n = [], None, 0
    for ln in t.split('\n'):
        m = re.match(r'  PIN (\w+)(\[\d+\])?$', ln)
        if m and m.group(1) in DROP:
            skip = f'  END {m.group(1)}{m.group(2) or ""}'; n += 1; continue
        if skip:
            if ln == skip:
                skip = None
            continue
        out.append(ln)
    assert skip is None and n > 0
    t = '\n'.join(out)
    for d in DROP:
        assert not re.search(r'\bPIN ' + d + r'\b', t), d
    return rename(t), n


def _drop_block(t, hdr_re):
    """remove every brace block whose header matches hdr_re (a line '<indent>hdr {' through its matching '}')."""
    n = 0
    while True:
        m = re.search(hdr_re, t, re.M)
        if not m:
            return t, n
        i = m.start(); j = t.index('{', m.start()); depth = 0
        for k in range(j, len(t)):
            if t[k] == '{':
                depth += 1
            elif t[k] == '}':
                depth -= 1
                if depth == 0:
                    break
        e = t.index('\n', k) + 1
        t = t[:i] + t[e:]; n += 1


def lib(t):
    names = '|'.join(DROP)
    t, nb = _drop_block(t, r'^    (?:bus|pin) \((?:' + names + r')\) \{')
    t, nt = _drop_block(t, r'^  type \(' + SRC + r'_(?:' + names + r')_t\) \{')
    assert nb == len(DROP), nb
    for d in DROP:
        assert not re.search(r'\((?:' + d + r')\)', t), d
    return rename(t), nb, nt


def bb(t):
    lines = [ln for ln in t.split('\n') if not re.match(r'\s+(?:input|output) wire (?:\[\d+:0\] )?(?:' + '|'.join(DROP) + r'),?$', ln)]
    t = '\n'.join(lines)
    t = re.sub(r',(\s*\n\);)', r'\1', t)           # last port loses its comma
    t = t.replace('// Blackbox view', '// S81 K-only variant (tools/s81_dv/phy_k_variant.py: no W port, no model counters).\n// Blackbox view', 1)
    return rename(t)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', type=Path, default=ROOT / 'physical/asap7_memory_macros_v2')
    a = ap.parse_args()
    s, d = a.root / SRC, a.root / DST
    d.mkdir(exist_ok=True)
    rec = dict(schema='opentallas.s81.phy_k_variant.v1', source=SRC, name=DST, dropped_ports=list(DROP), sources={}, emitted={})
    for f in sorted(s.iterdir()):
        rec['sources'][f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
    t = (s / f'{SRC}.lef').read_text(); o, n = lef(t); (d / f'{DST}.lef').write_text(o); rec['lef_pins_dropped'] = n
    for c in ('tt', 'ff', 'ss'):
        o, nb, nt = lib((s / f'{SRC}_{c}.lib').read_text()); (d / f'{DST}_{c}.lib').write_text(o)
        rec[f'lib_{c}_groups_dropped'] = [nb, nt]
    (d / f'{DST}_bb.v').write_text(bb((s / f'{SRC}_bb.v').read_text()))
    j = json.loads((s / f'{SRC}.json').read_text())
    j['name'] = DST
    j['variant'] = dict(of=SRC, tool='tools/s81_dv/phy_k_variant.py', dropped_ports=list(DROP),
                        note='S81 K-only: W port and model counters removed; outline / K pins / PDN unchanged')
    (d / f'{DST}.json').write_text(json.dumps(j, indent=2) + '\n')
    for f in sorted(d.iterdir()):
        if f.name != 'variant.json':
            rec['emitted'][f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
    (d / 'variant.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: v for k, v in rec.items() if k not in ('sources', 'emitted')}))


if __name__ == '__main__':
    main()
