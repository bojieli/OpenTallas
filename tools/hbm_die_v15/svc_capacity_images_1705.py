#!/usr/bin/env python3
"""External DRAM images for the SM-specific four-PC service engine capacity / all-SM mapping replay (H-DIE 2026-10-15).

Codex DECISION 14:40 asks for the 13-SRAM/SM service engine's capacity and all-SM mapping to be proved.  The archived
checkpoint (results/arch/hbm_die_v15/mapped4_checkpoint) has 13 active SMs at 40 records.  This tool writes, for EVERY
SM of the requested stack (8 per stack, 32 per die), ROWS logical 136-byte records (default 64 = the feed's 6-bit row
index maximum) and installs them with the production installer (tools/hbm_svc_packed136_image.install: XOR PC mapping,
packed136 compaction, actual sector30 addresses) on each SM's book reservation (checkpoint_allocation/book.json
new_reservations: stack, four PCs, row base).  Record CONTENT is deterministic external test data (sha256 stream of
sm/row): it is off-chip DRAM data, the one boundary the owner rule lets a bench model; every on-chip operation in the
replay is the actual RTL.  Not a checkpoint/numerical claim.

    svc_capacity_images_1705.py --stack S --rows 64 --out DIR      -> DIR/smNN/{records,backing,sectors}.hex, config.json
"""
import argparse, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from hbm_svc_packed136_image import install, digest  # noqa: E402

BOOK = ROOT / 'results/arch/hbm_die_v15/checkpoint_allocation/book.json'
TEMPLATE = ROOT / 'results/arch/hbm_die_v15/checkpoint_allocation/sm09.json'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--stack', type=int, required=True)
    ap.add_argument('--rows', type=int, default=64)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    book = json.loads(BOOK.read_text()); tmpl = json.loads(TEMPLATE.read_text())
    res = {r['sm']: r for r in book['new_reservations']}
    a.out.mkdir(parents=True, exist_ok=True)
    rep = []
    for i in range(8):
        sm = 8 * a.stack + i; r = res[sm]
        assert r['stack'] == a.stack and r['pcs'] == [4 * i + k for k in range(4)], (sm, r['stack'], r['pcs'])
        d = a.out / f'sm{sm:02d}'; d.mkdir(exist_ok=False)
        alloc = dict(tmpl, allocation_id=f'hdie1705-capacity-sm{sm}', sm=sm, stack=r['stack'], pcs=r['pcs'],
                     row_base=r['rows'][0], row_count=r['rows'][1] - r['rows'][0],
                     provenance=dict(tmpl['provenance'], book=str(BOOK.relative_to(ROOT)),
                                     note='book new_reservations entry; capacity replay (external test data)'))
        (d / 'allocation.json').write_text(json.dumps(alloc, indent=1) + '\n')
        lines = []
        for row in range(a.rows):
            h = b''.join(hashlib.sha256(f'hdie1705/sm{sm}/row{row}/{k}'.encode()).digest() for k in range(5))[:136]
            lines.append(h.hex())
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
        cfg = dict(sm=sm, stack=r['stack'], pcs=r['pcs'], row_base=r['rows'][0], rows=a.rows, sectors=rec['sectors'],
                   records_sha256=digest(d / 'records.hex'), backing_sha256=digest(d / 'backing.hex'),
                   external_test_data=True)
        (d / 'config.json').write_text(json.dumps(cfg, indent=1) + '\n')
        rep.append(cfg)
    print(json.dumps(dict(stack=a.stack, rows=a.rows, sms=[c['sm'] for c in rep], sectors=rep[0]['sectors'])))


if __name__ == '__main__':
    main()
