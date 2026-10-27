#!/usr/bin/env python3
"""Resident HC fn via masks for ALL 24 projection rows (4 TP4 ranks x 6 leaves), all 40 main + 3 MTP sets.

Leaf l of rank r computes mix row 6*r + l (gatherpack word order); its 64 ot_rom_4096x266_m8 macros are named
hcx_r{r}_p{l}_b{bank}_l{m}_p{page} (dsfd_sp_hcx_projection IMAGE convention). The mapping is exactly
hcx_resident_image.py (codex/s81-hc-home-1014) generalised from one row to 24 and vectorised: payload of
(row, bank, run, m) = the 256-bit HBM-window sector bs+4+(8*row+bank)*320+run*4+m; address 80*(2*set+block)+run;
via column bit*8+addr%8 of mask row (addr&4095)//8 of page addr>>12. No coefficient is altered or compressed.
--check-row0 DIR compares row 0 against an existing single-row image (hcx_r0_b*_l*_p*.viamap.hex).
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np


def load(src):
    rom = {}
    for s in (src / 'hu_hbm.mem').read_text().split():
        rom[int(s[:10], 16)] = int(s[10:], 16)
    cases = (src / 'hu_case.mem').read_text().split()
    assert len(cases) == 2, src
    return rom, cases


def sets(root):
    for layer in range(43):
        yield layer, root / ('vec' if layer < 40 else 'vecm') / (f'L{layer:02d}' if layer < 40 else f'M{layer-40}R0')


def build(root, out, rows):
    # masks[row][bank][m][page] : bool [512, 2128]
    masks = {(r, b, m, p): np.zeros((512, 2128), np.uint8) for r in rows for b in range(8) for m in range(4) for p in range(2)}
    src_rec = []
    for layer, src in sets(root):
        rom, cases = load(src)
        src_rec.append(dict(layer=layer, path=str(src), hbm_sha256=hashlib.sha256((src / 'hu_hbm.mem').read_bytes()).hexdigest()))
        for block, line in enumerate(cases):
            d = int(line[56:], 16); b_ = (d >> 384) & ((1 << 256) - 1); bs = ((b_ >> 8) & ((1 << 40) - 1)) >> 5
            addr = 80 * (2 * layer + block) + np.arange(80)
            pg, low = addr >> 12, addr & 4095
            for r in rows:
                for bank in range(8):
                    for m in range(4):
                        pay = [rom[bs + 4 + (8 * r + bank) * 320 + run * 4 + m] for run in range(80)]
                        by = np.frombuffer(b''.join(p.to_bytes(32, 'little') for p in pay), np.uint8).reshape(80, 32)
                        bits = np.unpackbits(by, axis=1, bitorder='little')          # [80, 256]
                        for run in range(80):
                            nz = np.nonzero(bits[run])[0]
                            if nz.size:
                                masks[(r, bank, m, int(pg[run]))][low[run] // 8, nz * 8 + low[run] % 8] = 1
        print(f'HCX_RANK_IMAGES set {layer} {src.name} done', flush=True)
    out.mkdir(parents=True, exist_ok=True)
    digests = {}
    for (r, bank, m, p), arr in masks.items():
        name = f'hcx_r{r // 6}_p{r % 6}_b{bank}_l{m}_p{p}.viamap.hex'
        packed = np.packbits(arr, axis=1, bitorder='little')                       # [512, 266] bytes
        text = ''.join(f'{int.from_bytes(row.tobytes(), "little"):0532x}\n' for row in packed)
        (out / name).write_text(text)
        digests[name] = hashlib.sha256(text.encode()).hexdigest()
    (out / 'rank_image_manifest.json').write_text(json.dumps(dict(
        rows=list(rows), row_of_leaf='6*rank+leaf', sets=43, macro='ot_rom_4096x266_m8', macros=64 * len(rows),
        native_addresses=[0, 80 * 86 - 1], sources=src_rec, sha256=digests), indent=2) + '\n')
    return digests


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--vectors', type=Path, required=True, help='root holding vec/Lnn and vecm/MkR0 (hcx_real.py output)')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--rows', default='0-23')
    ap.add_argument('--check-row0', type=Path)
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.rows.split('-')) if '-' in a.rows else (int(a.rows), int(a.rows))
    rows = list(range(lo, hi + 1))
    build(a.vectors, a.out, rows)
    if a.check_row0:
        assert 0 in rows
        bad = [f for b in range(8) for m in range(4) for p in range(2)
               if (a.out / f'hcx_r0_p0_b{b}_l{m}_p{p}.viamap.hex').read_bytes() != (a.check_row0 / f'hcx_r0_b{b}_l{m}_p{p}.viamap.hex').read_bytes()
               for f in [f'b{b}_l{m}_p{p}']]
        print('HCX_RANK_IMAGES row0 vs reference:', 'IDENTICAL 64/64' if not bad else f'DIFFER {bad[:8]}')
        raise SystemExit(1 if bad else 0)
