#!/usr/bin/env python3
"""External HBM images of IDX index keys for the service key-staging bench (H-NETLIST idxcoll 2026-10-15).

The die binds hb_idx.key_lines[j*8792 + p*1099 +: 1099] to svg_<Q[j]><p>.sm_packet (tools/hbm_die_v15/v16_specs/
idxcoll.json): key pair (stack s, beat b, port p) = keys 16b+2p, 16b+2p+1 of the stack's owned keys (key_format_v1:
16 keys per stack beat, 8 ports, 136-B pair) is ONE packed136 record at row b of SM p's own key region (its four PCs).
This tool writes, for the eight SMs of a stack, ROWS such records (beats B0..B0+ROWS-1) and installs them with the
production installer (tools/hbm_svc_packed136_image.install: XOR PC mapping, packed136 compaction, sector30 addresses)
on each SM's book reservation, exactly as tools/hbm_die_v15/svc_capacity_images_1705.py does for weights.  Record
byte order = the installer's (record integer little-endian: HBM byte 0 = bits 7:0), so key 16b+2p is bits 0..543 and
key 16b+2p+1 bits 544..1087 of the record, = key_lines[p*1099+11 +: 1088] (ot_hbm_idx_score_static lane 2p / 2p+1).
Key CONTENT is deterministic external test data (sha256 stream of stack/key, 68 B per key): off-chip DRAM data.

    idx_key_images_2210.py --stack S --rows 64 [--beat0 0] --out DIR   -> DIR/smNN/{records,backing,sectors}.hex, keys.json
"""
import argparse, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from hbm_svc_packed136_image import install, digest  # noqa: E402

BOOK = ROOT / 'results/arch/hbm_die_v15/checkpoint_allocation/book.json'
TEMPLATE = ROOT / 'results/arch/hbm_die_v15/checkpoint_allocation/sm09.json'


def key(stack, k):
    """one 68-B (544-b) packed index key: deterministic external test data"""
    h = b''.join(hashlib.sha256(f'idxcoll2210/stack{stack}/key{k}/{i}'.encode()).digest() for i in range(3))[:68]
    return int.from_bytes(h, 'little')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--stack', type=int, required=True)
    ap.add_argument('--rows', type=int, default=64)
    ap.add_argument('--beat0', type=int, default=0)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    assert 1 <= a.rows <= 64 and 0 <= a.beat0 and a.beat0 + a.rows <= 171
    book = json.loads(BOOK.read_text()); tmpl = json.loads(TEMPLATE.read_text())
    res = {r['sm']: r for r in book['new_reservations']}
    a.out.mkdir(parents=True, exist_ok=True)
    rep = []
    for p in range(8):
        sm = 8 * a.stack + p; r = res[sm]
        assert r['stack'] == a.stack and r['pcs'] == [4 * p + k for k in range(4)], (sm, r['stack'], r['pcs'])
        d = a.out / f'sm{sm:02d}'; d.mkdir(exist_ok=False)
        alloc = dict(tmpl, allocation_id=f'idxcoll2210-keys-sm{sm}', sm=sm, stack=r['stack'], pcs=r['pcs'],
                     row_base=r['rows'][0], row_count=r['rows'][1] - r['rows'][0],
                     provenance=dict(tmpl['provenance'], book=str(BOOK.relative_to(ROOT)),
                                     note='book new_reservations entry; IDX key region (external test data)'))
        (d / 'allocation.json').write_text(json.dumps(alloc, indent=1) + '\n')
        lines = []
        for row in range(a.rows):
            b = a.beat0 + row
            pair = key(a.stack, 16 * b + 2 * p) | (key(a.stack, 16 * b + 2 * p + 1) << 544)
            lines.append(f'{pair:0272x}')
        (d / 'records.hex').write_text('\n'.join(lines) + '\n')
        img = d / 'img'
        rec = install(d / 'records.hex', digest(d / 'records.hex'), a.rows, d / 'allocation.json', img)
        phys = (img / 'physical.hex').read_text().splitlines()
        back, sect, seen = [], [], set()
        for k in range(rec['sectors']):
            addr = int(phys[2 * k][1:], 16)
            assert addr % 65536 not in seen; seen.add(addr % 65536)
            back.append(f'@{addr % 65536:08x}\n{phys[2 * k + 1]}\n'); sect.append(phys[2 * k + 1] + '\n')
        (d / 'backing.hex').write_text(''.join(back)); (d / 'sectors.hex').write_text(''.join(sect))
        cfg = dict(sm=sm, stack=r['stack'], port=p, pcs=r['pcs'], row_base=r['rows'][0], rows=a.rows, beat0=a.beat0,
                   sectors=rec['sectors'], records_sha256=digest(d / 'records.hex'),
                   backing_sha256=digest(d / 'backing.hex'), external_test_data=True)
        (d / 'config.json').write_text(json.dumps(cfg, indent=1) + '\n')
        rep.append(cfg)
    print(json.dumps(dict(stack=a.stack, rows=a.rows, beat0=a.beat0, sms=[c['sm'] for c in rep], sectors=rep[0]['sectors'])))


if __name__ == '__main__':
    main()
