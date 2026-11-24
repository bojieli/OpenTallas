#!/usr/bin/env python3
"""BIST CRC-32 signatures of a QC rank's programmed ROMs, read from the via maps themselves.

The ROM BIST reads every stored word (266 bits, including the 10 dead
bitlines) of a 4096x266 macro and folds it into the macro compiler's CRC
(tools/mem_compiler/ecc.signature).  This tool decodes each via map through
the physical bitline order (bitline = 8 * bit + word % 8) -- i.e. it signs
what is actually programmed, not an expected image -- for:
  * the 7,680 code ROMs of a rank (code mask manifest), and
  * the 48 table ROMs of a rank (table receipt), when given.
With --reference (an earlier signature receipt) every shared instance must
carry the same CRC.  The fast packed CRC is self-tested against the bitwise
hardware reference before use.

  bist_signatures.py --rank N --code-manifest <masks_rN>/rankN/manifest.json \
      [--tables <tables>/rankN] [--reference old_rankN.json] --out sig.json
"""
from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from mem_compiler.ecc import signature  # noqa: E402

WORDS, STORED_BITS, ROW_BYTES = 4096, 266, 266


def stored_words(path: Path) -> np.ndarray:
    """(4096, 266) stored bits of one via map; mask row r, bitline 8*b+s holds bit b of word 8*r+s."""
    rows = [bytes.fromhex(line.strip().decode())[::-1] for line in path.open('rb') if line.strip()]
    if len(rows) != 512 or any(len(r) != ROW_BYTES for r in rows):
        raise ValueError(f'wrong via map shape: {path}')
    bits = np.unpackbits(np.frombuffer(b''.join(rows), dtype=np.uint8).reshape(512, ROW_BYTES),
                         axis=1, bitorder='little').reshape(512, STORED_BITS, 8)
    return bits.transpose(0, 2, 1).reshape(WORDS, STORED_BITS)


def crc(bits: np.ndarray) -> str:
    if bits.shape != (WORDS, STORED_BITS):
        raise ValueError('incorrect ROM word geometry')
    reflected = binascii.crc32(np.packbits(bits, bitorder='little')) ^ 0xFFFFFFFF
    return f"{int(f'{reflected:032b}'[::-1], 2):08x}"


def self_test() -> None:
    rng = np.random.default_rng(1)
    bits = (rng.random((WORDS, STORED_BITS)) < 0.01).astype(np.uint8)
    words = [int(''.join(map(str, row[::-1])), 2) for row in bits]
    if int(crc(bits), 16) != signature(words, STORED_BITS):
        raise ValueError('packed CRC does not match the bitwise hardware reference')


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rank', type=int, required=True)
    ap.add_argument('--code-manifest', type=Path, required=True)
    ap.add_argument('--tables', type=Path)
    ap.add_argument('--reference', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    self_test()
    rec = json.loads(a.code_manifest.read_text())
    if rec['rank'] != a.rank or rec['macros'] != 7680:
        raise ValueError('code manifest identity')
    mdir = a.code_manifest.parent / 'masks'
    code = {}
    for p in rec['pairs']:
        for c in p['columns']:
            f = mdir / c['file']
            if sha(f) != c['sha256']:
                raise ValueError(f'mask pin mismatch: {f}')
            code[c['instance']] = dict(crc32=crc(stored_words(f)), viamap_sha256=c['sha256'])
    tables = {}
    if a.tables:
        receipt = json.loads((a.tables / 'receipt.json').read_text())
        if receipt['rank'] != a.rank or len(receipt['images']) != 48:
            raise ValueError('table receipt identity')
        for name, digest in sorted(receipt['images'].items()):
            f = a.tables / 'masks' / name
            if sha(f) != digest:
                raise ValueError(f'table mask pin mismatch: {f}')
            tables[name.removesuffix('.viamap.hex')] = dict(crc32=crc(stored_words(f)), viamap_sha256=digest)
    res = dict(schema='opentallas.qwen-rom-bist-signatures.v2', rank=a.rank, macro='ot_rom_4096x266_m8',
               words=WORDS, stored_bits=STORED_BITS, read_from='decoded via maps',
               convention='CRC-32 04c11db7, ffffffff init, all stored bits LSB-first per word, no xorout',
               code_manifest_sha256=sha(a.code_manifest), code=code, tables=tables)
    if a.reference:
        ref = json.loads(a.reference.read_text())
        diff = [k for k, v in ref.get('code', {}).items() if code.get(k, {}).get('crc32') != v['crc32']]
        res['reference'] = dict(path=str(a.reference), compared=len(ref.get('code', {})), differing=len(diff),
                                first=diff[:5])
    ok = len(code) == 7680 and (not a.tables or len(tables) == 48) and not res.get('reference', {}).get('differing')
    res['verdict'] = 'PASS' if ok else 'FAIL'
    a.out.write_text(json.dumps(res, separators=(',', ':')) + '\n')
    print(json.dumps(dict(rank=a.rank, verdict=res['verdict'], code=len(code), tables=len(tables),
                          reference=res.get('reference'))))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
