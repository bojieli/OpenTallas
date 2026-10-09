#!/usr/bin/env python3
"""Turn hbm-sim CF-TOPK conformance vectors into ot_hgi_idx_unit bench inputs (hgi-takeover 2026-10-09).

Per vector: the first record (IDX.TOPK) as the die record bus {n_R, n_O, n_B, n_A, R, O, B, A, header, valid} (1,237 b),
the VM input words and the expected VM output words.  Static descriptors are the effective ones (no DYN / indexed).
  hgi_idx_unit_vectors.py OUTDIR [--mutant NAME]  -> OUTDIR/vec_<i>.{rec,vmin,vmout}.mem, OUTDIR/list.txt"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CONF = ROOT / 'results/arch/hgi_sim_20261009/conformance'
OPND = 'ABCDORI'

def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    idx = json.loads((CONF / 'index.json').read_text())
    vecs = [v for v in (idx['vectors'] if isinstance(idx, dict) else idx) if v['row'] == 'CF-TOPK']
    lines = []
    for i, v in enumerate(vecs):
        j = json.loads((CONF / v['file']).read_text())
        rb = bytes.fromhex(j['record_hex'][0])
        hdr = int.from_bytes(rb[:16], 'little')
        opnd = (hdr >> 93) & 0x7F
        off = 16 + (32 if (hdr >> 92) & 1 else 0)
        d = {}
        for b, name in enumerate(OPND):
            if opnd >> b & 1:
                d[name] = int.from_bytes(rb[off:off + 32], 'little'); off += 32
        n = {k: (x >> 48) & 0xFFFFF for k, x in d.items()}
        bus = 1 | hdr << 1
        pos = 129
        for name in 'ABOR':
            bus |= d.get(name, 0) << pos; pos += 256
        for name in 'ABOR':
            bus |= n.get(name, 0) << pos; pos += 21
        (out / f'vec_{i}.rec.mem').write_text(f'{bus:0310x}\n')
        vmin = [(a + w, int.from_bytes(bytes.fromhex(h)[w*4:w*4+4], 'little'))
                for a, h in j['dies'][0]['vm_in'] for w in range(len(h) // 8)]
        (out / f'vec_{i}.vmin.mem').write_text(''.join(f'{a:05x}{x:08x}\n' for a, x in vmin) + 'fffffffffffff\n')
        ed = j['expect'].get('dies') or [{}]
        exp = ed[0].get('vm_out', [])
        vmout = [(a + w, int.from_bytes(bytes.fromhex(h)[w*4:w*4+4], 'little')) for a, h in exp for w in range(len(h) // 8)]
        (out / f'vec_{i}.vmout.mem').write_text(''.join(f'{a:05x}{x:08x}\n' for a, x in vmout) + 'fffffffffffff\n')
        lines.append(f"{i} {j['expect']['status']} {v['id']}")
    (out / 'list.txt').write_text(f'{len(vecs)}\n' + '\n'.join(lines) + '\n')
    print(len(vecs), 'vectors')

if __name__ == '__main__':
    main()
