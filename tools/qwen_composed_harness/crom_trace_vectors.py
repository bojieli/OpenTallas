#!/usr/bin/env python3
"""Replay vectors for tb_crom_trace_replay.sv from an OT_CROM_TRACE file (rom_vm_adapter.hpp observation).

Each 'R edge mask a..' line is one constant read the actual core issued; 'B edge image' names the stage image
(.../layer<L>/die<r> or the head image -> stage 36). Expected words come from that same stage image (comparison
only). The vectors keep the recorded edge spacing so the native path is driven at the core's own request timing.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

END = 541313


def read_image(path):
    words, addr = [0] * END, 0
    with open(path) as f:
        for line in f:
            for tok in line.split('//')[0].split():
                if tok[0] == '@':
                    addr = int(tok[1:], 16)
                    continue
                words[addr] = int(tok, 16)
                addr += 1
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('trace', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    reads, images, stage, words, rank = [], {}, None, None, None
    for line in a.trace.read_text().splitlines():
        f = line.split()
        if f[0] == 'B':
            img = f[2]
            m = re.search(r'layer(\d+)/die(\d+)$', img)
            if m:
                stage, r = int(m.group(1)), int(m.group(2))
            else:
                m = re.search(r'die(\d+)$', img)
                if not m:
                    raise SystemExit(f'FAIL unknown image {img}')
                stage, r = 36, int(m.group(1))
            if rank is not None and r != rank:
                raise SystemExit('FAIL rank changes inside one adapter trace')
            rank = r
            path = Path(img) / 'crom.hex'
            words = read_image(path)
            images[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
            continue
        if f[0] != 'R':
            raise SystemExit(f'FAIL bad trace line {line[:80]}')
        edge, mask = int(f[1]), int(f[2], 16)
        lanes = [l for l in range(64) if mask >> l & 1]
        addrs = [int(x, 16) for x in f[3:]]
        if len(addrs) != len(lanes):
            raise SystemExit('FAIL lane count')
        full = [0] * 64
        for l, x in zip(lanes, addrs):
            full[l] = x
        reads.append((edge, stage, mask, full, [words[x] if mask >> l & 1 else 0 for l, x in enumerate(full)]))
    if not reads:
        raise SystemExit('FAIL empty trace')
    with open(a.out / 'rd_hdr.hex', 'w') as h, open(a.out / 'rd_mask.hex', 'w') as mk, \
            open(a.out / 'rd_addr.hex', 'w') as ad, open(a.out / 'rd_exp.hex', 'w') as ex:
        for edge, st, mask, full, exp in reads:
            h.write(f'{(edge << 8) | st:016x}\n')
            mk.write(f'{mask:016x}\n')
            ad.write(''.join(f'{x:06x}\n' for x in full))
            ex.write(''.join(f'{x:016x}\n' for x in exp))
    stages = sorted({r[1] for r in reads})
    gaps = [b[0] - a_[0] for a_, b in zip(reads, reads[1:])]
    man = {'trace': str(a.trace), 'trace_sha256': hashlib.sha256(a.trace.read_bytes()).hexdigest(), 'rank': rank,
           'reads': len(reads), 'stages': stages, 'first_edge': reads[0][0], 'last_edge': reads[-1][0],
           'min_gap': min(gaps) if gaps else None, 'active_lane_reads': sum(bin(r[2]).count('1') for r in reads),
           'stage_images_sha256': images}
    (a.out / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    print(f"VECTORS reads {len(reads)} rank {rank} stages {stages} first_edge {reads[0][0]} min_gap {man['min_gap']}")


if __name__ == '__main__':
    main()
