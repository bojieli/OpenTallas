#!/usr/bin/env python3
"""LH-UNREAD F-P 10-19: opt in the IDX256R collar (packed 769-bit operand face, 8-bit programme address).

Reserved operand bits (767) are neither stored nor exported by ot_hbm_static_cfg_collar_idx256r and a nonzero write
into one faults; pw_addr[11:8] (constant 0 on every successful IDX256 write) is not exported. Every consumer edge of
col_idx.prm / col_idx.pw_addr is remapped to the packed position; any consumed bit outside the retained map fails closed.
No view is admitted here (SOURCE_ONLY: synth/native/physical re-grant required)."""
import argparse, copy, gzip, hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OLD = 'ot_hbm_static_cfg_collar_idx256'
NEW = 'ot_hbm_static_cfg_collar_idx256r'
SRC = 'rtl/hbm_accel/host_static_20261015/' + NEW + '.sv'
PRV = 'rtl/hbm_accel/host_static_20261015/' + OLD + '.sv'
# retained operand segments [lo, hi) in operand-bit order -> packed prm positions (must equal the RTL header)
SEGS = [(0, 44), (51, 424), (766, 1108), (1450, 1460)]
PMAP = {}
for lo, hi in SEGS:
    for b in range(lo, hi):
        PMAP[b] = len(PMAP)
assert len(PMAP) == 769


def remap(lo, hi, m, port):
    bits = [m.get(b) for b in range(lo, hi)]
    if None in bits:
        raise ValueError('consumed %s bit outside the retained map: [%d,%d)' % (port, lo, hi))
    if bits != list(range(bits[0], bits[0] + len(bits))):
        raise ValueError('consumed %s range not contiguous after packing: [%d,%d)' % (port, lo, hi))
    return bits[0], bits[0] + len(bits)


def apply(original):
    c = copy.deepcopy(original); v = c['instances']['col_idx']
    if v['master'] not in (OLD, NEW): raise ValueError('l20p requires the l19 IDX256 collar on col_idx')
    if v['params'].get('NPR') != 6: raise ValueError('packed face is NPR6 only')
    changed = v['master'] != NEW
    edges = [e for e in c['edges'] if e['source'][0] == 'col_idx' and e['source'][1] in ('prm', 'pw_addr')]
    if changed:
        if v['ports']['prm']['bits'] != 1536 or v['ports']['pw_addr']['bits'] != 12: raise ValueError('unexpected idx256 face')
        consumed = set()
        for e in edges:
            port, lo, hi = e['source'][1:4]
            m = PMAP if port == 'prm' else {b: b for b in range(8)}
            nlo, nhi = remap(lo, hi, m, port)
            if port == 'prm': consumed |= set(range(lo, hi))
            e['source'] = ['col_idx', port, nlo, nhi]
        if consumed != set(PMAP): raise ValueError('retained map has unconsumed bits: %d' % len(set(PMAP) - consumed))
        v['ports']['prm']['bits'] = 769; v['ports']['pw_addr']['bits'] = 8
        v['note'] += (' | l20p: IDX256R packed operand face prm769 (reserved operand fields not stored/exported, nonzero'
                      ' reserved write = sticky fault), pw_addr8 (row>=256 already faults); 0 added edges')
    v.update(master=NEW, source=SRC, rtl_deps=[])
    for s in c['straps']:
        if s.get('inst') == 'col_idx': s['master'] = NEW
    r = dict(layer='l20p_idx_collar_prm', changed=changed, instance='col_idx', master=NEW, source=SRC,
             retained_operand_segments=SEGS, packed_prm_bits=769, removed_prm_bits=767, removed_pw_addr_bits=4,
             remapped_edges=len(edges), successful_data_added_edges=0, state_bits_removed=767,
             predecessor_sha256=hashlib.sha256((ROOT / PRV).read_bytes()).hexdigest(),
             successor_sha256=hashlib.sha256((ROOT / SRC).read_bytes()).hexdigest(),
             qualification='SOURCE_ONLY_NEEDS_SYNTH_NATIVE_TTFF_PHYSICAL_REGRANT', no_hard_view_admitted=True)
    return c, r


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('inp'); p.add_argument('out'); p.add_argument('--report', required=True); a = p.parse_args()
    with gzip.open(a.inp, 'rt') if a.inp.endswith('.gz') else open(a.inp) as f: c = json.load(f)
    c, r = apply(c); Path(a.out).write_text(json.dumps(c, separators=(',', ':')) + '\n'); Path(a.report).write_text(json.dumps(r, indent=1) + '\n')
    print('L20P_IDX256R prm1536->769 pw_addr12->8 remapped_edges=%d removed_bits=771 0 added edges' % r['remapped_edges'])


if __name__ == '__main__':
    main()
