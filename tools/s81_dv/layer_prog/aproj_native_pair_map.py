#!/usr/bin/env python3
"""Actual-inventory DENSE2 capture ownership and fixture-scoreboard map.

This emits no synthetic producer and no calendar admission. GO/FIN/CAP issue
and transport must still be exercised in the actual RTL source vehicle.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import struct
from types import SimpleNamespace

import lower_xs as X


class Inventory:
    def __init__(self, tree):
        base = Path(tree) / 'results/arch/s81_dv_1016'
        self.plan = json.loads((base / 'p4l/plan.json').read_text())
        self.blocks = {b['name']: b for b in self.plan['blocks']}
        raw = gzip.decompress((base / 'bind9/die.v.gz').read_bytes())
        self.die_sha = hashlib.sha256(raw).hexdigest()
        self.inst = {}
        for line in raw.decode().splitlines():
            m = re.match(r'\s*(\w+)\s+(?:#\(.*?\)\s+)?(u_[A-Za-z0-9_]+)\s*\((.*)\);', line)
            if m:
                master, name, ports = m.groups()
                self.inst[name] = dict(master=master, ports=ports)

    def strap(self, name, port):
        m = re.search(r'\.' + port + r"\((\d+)'([dh])([0-9a-fA-F]+)\)", self.inst[name]['ports'])
        if not m:
            raise ValueError(f'Missing actual {port} strap on {name}')
        return int(m[3], 16 if m[2] == 'h' else 10)

    def slices(self):
        return {name: dict(sid=self.strap(name, 'sid')) for name, row in self.inst.items()
                if row['master'].startswith('ot_s81sl_slice')}

    def frames_of(self, name):
        group = self.blocks[name[2:]]['group']
        return sorted('u_' + b['name'] for b in self.plan['blocks']
                      if b.get('kind') == 'frame' and b['group'] == group and 'u_' + b['name'] in self.inst)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tree', required=True)
    p.add_argument('--fixtures', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    fixture = Path(a.fixtures)
    meta = json.loads((fixture / 'meta.json').read_text())
    manifest = json.loads((fixture / 'ops.json').read_text())['attn.a_proj']
    raw = (fixture / 'ops/attn.a_proj.bin').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest['sha256']
    bits = struct.unpack('<' + 'I' * (len(raw) // 4), raw)
    rank = meta['rank']
    nq = meta['tp_split']['a_proj.wq_a_rows'][rank]
    nk = meta['tp_split']['a_proj.wkv_rows'][rank]
    # Shapes come from the pinned real fixture metadata; no generated values.
    fx = dict(meta=meta, w={k: [SimpleNamespace(shape=(rows[1] - rows[0], 5120))]
                            for k, rows in [('wq_a', nq), ('wkv', nk)]})
    die = Inventory(a.tree)
    out = dict(schema='opentallas.s81.aproj_native_pair_map.v1', die_sha256=die.die_sha,
               compiler_sha256=hashlib.sha256(Path(X.__file__).read_bytes()).hexdigest(),
               fixture_a_proj_sha256=manifest['sha256'], rank=rank, halves={})
    os.environ.update(OT_XS_APROJ_TOPO='1', OT_XS_APROJ_RANK_TAGS='1', OT_XS_APROJ_ALIGN4='1')
    for half in ('A', 'B'):
        os.environ['OT_XS_DENSE_SPLIT2'] = half
        captures, frames = [], []
        for name in sorted(die.slices(), key=lambda n: die.strap(n, 'sid')):
            _, owned = X.placement(die, name, fx)
            frames.extend(owned)
            if not any(f['rows'] for f in owned):
                continue
            capture = X.aproj_capture_contract(die, name, fx, flags=1)
            assert capture['cfg']['rcnt'] % 8 == 0 and capture['rows'][0]['rank_row'] % 8 == 0
            for i, row in enumerate(capture['rows']):
                assert bits[row['golden_output_index']] & 65535 == 0, 'fixture a_proj value is not BF16-expanded'
                row.update(native_leaf=0, native_row=i // 4, word=i % 4,
                           expected32_scoreboard_only=f"{bits[row['golden_output_index']]:08x}")
            captures.append(capture)
        rows = [r['rank_row'] for c in captures for r in c['rows']]
        wanted = range(0, 224) if half == 'A' else range(224, 448)
        assert rows == list(wanted)
        assert sum(bool(f['rows']) for f in frames) == 56 and len(frames) == 72
        out['halves'][half] = dict(captures=captures, active_frames=56, idle_frames=16,
            checks=dict(no_missing_rows=True, no_duplicate_rows=True, actual_frames_only=True,
                        native_256bit_pairs_aligned=True, fixture_golden_indices_bound=True),
            added_phases=0, added_arithmetic=0)
    out['qualification'] = 'OWNERSHIP/GOLDEN MAP MODEL ONLY; actual GO/FIN/CAP issue and transport remain unqualified'
    Path(a.out).write_text(json.dumps(out, indent=2) + '\n')
    print('APROJ_NATIVE_PAIR_MAP A224 B224 actual72 active56 idle16 golden-bound; source RTL issuance still required')


if __name__ == '__main__':
    main()
