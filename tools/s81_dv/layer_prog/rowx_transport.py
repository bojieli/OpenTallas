#!/usr/bin/env python3
"""Compile ROWX2 rank slots into the existing per-half ROWS PK2 q frame.

Source ABI: dsdv_svc_att.sv + tb_dsdv_svc_rowx.sv at feaec58ef0.
Inputs are actual 513-bit per-tile export words, in pass/word order. No row
payload is invented: valid 256-bit halves are copied unchanged. Owner numbers
are die + 4*stack. This is a transport transform, not a die link scheduler.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

MASK256 = (1 << 256) - 1
# xhalf = {88'b0, data[127:89],9'b0,data[88:0],scale[15:0],rank[9:0],tile[3:0],v}
RESERVED = ((1 << 88) - 1) << 168 | ((1 << 9) - 1) << 120


def owner_of(gid: int) -> int:
    if not 0 <= gid < 1 << 32:
        raise ValueError('selected gid must fit the SEL_IDS 32-bit field')
    return ((gid >> 4) & 3) | (((gid >> 6) & 3) << 2)


@dataclass(frozen=True)
class ExportSpec:
    nxw: int = 40
    passes: int = 7
    period: int = 320

    def check(self, nsel: int) -> None:
        if not 0 < nsel <= 512:
            raise ValueError('ROWX selection must contain 1..512 ranks')
        if self.nxw not in range(5, 41, 5) or not 1 <= self.passes <= 16:
            raise ValueError('ROWX NXW/NP does not fit the RTL legal fields')
        if not 8 * self.nxw <= self.period < 4096:
            raise ValueError('XP must cover all eight tile windows and fit 12 bits')
        if 2 * self.nxw * self.passes < nsel:
            raise ValueError('ROWX passes do not cover nsel (RTL fault 26)')
        if 8 * self.nxw % 160:
            raise ValueError('each half/pass must respect the pvrd nw=160 strap')

    def entry_cycle(self, tile: int, word: int) -> int:
        """Offset from first tile's first entry word, after each source is aligned."""
        p, i = divmod(word, self.nxw)
        return p * self.period + (tile % 8) * self.nxw + i

    def header_spec(self, xo: int = 8) -> int:
        if not 0 <= xo < 65536:
            raise ValueError('XO must fit 16 bits')
        return xo | self.nxw << 16 | 1 << 30 | (self.passes - 1) << 31 | self.period << 35


def _valid_half(h: int, tile: int, rank: int, nsel: int) -> bool:
    if not h & 1:
        if h:
            raise ValueError(f'nonzero invalid half at tile {tile} rank {rank}')
        return False
    if rank >= nsel or (h >> 5) & 1023 != rank or (h >> 1) & 15 != tile or h & RESERVED:
        raise ValueError(f'bad ROWX half identity/reserved fields at tile {tile} rank {rank}')
    return True


def merge_repair(exports: Mapping[int, Mapping[int, Sequence[int]]], gids: Sequence[int],
                 receiver: int, half: int, spec: ExportSpec = ExportSpec()) -> list[int]:
    """Strict slot OR-merge, excluding receiver, then adjacent-tile PK2 pairing.

    Require every owner and eight tiles, including zero slots. Missing traffic,
    duplicate holders, rank swaps, and accidentally merging self traffic fail.
    Return nsel*4 payload words; zero words retain their fixed booked q slots.
    """
    spec.check(len(gids))
    if receiver not in range(16) or half not in (0, 1):
        raise ValueError('receiver must be die+4*stack in 0..15; half must be 0 or 1')
    if set(exports) != set(range(16)):
        raise ValueError('exactly sixteen owner export streams are required')
    tiles = range(8 * half, 8 * half + 8)
    merged = {t: [0] * len(gids) for t in tiles}
    owners = [owner_of(int(g)) for g in gids]
    nwords = spec.passes * spec.nxw
    for t in tiles:
        seen = [None] * len(gids)
        for o in range(16):
            if set(exports[o]) != set(tiles) or len(exports[o][t]) != nwords:
                raise ValueError(f'incomplete fixed export slots for owner {o}, tile {t}')
            for w, word in enumerate(exports[o][t]):
                if not 0 <= word < 1 << 513 or word >> 512 != int(w % spec.nxw % 5 == 0):
                    raise ValueError(f'bad P.V head/width owner {o}, tile {t}, word {w}')
                for j in range(2):
                    rank = 2 * w + j
                    h = word >> (256 * j) & MASK256
                    if not _valid_half(h, t, rank, len(gids)):
                        continue
                    if owners[rank] != o or seen[rank] is not None:
                        raise ValueError(f'non-disjoint/wrong holder tile {t}, rank {rank}, owner {o}')
                    seen[rank] = o
                    if o != receiver:
                        merged[t][rank] |= h
        if seen != owners:
            raise ValueError(f'missing held rank on tile {t}')
    return [merged[t][r] | merged[t + 1][r] << 256
            for r in range(len(gids)) for t in range(8 * half, 8 * half + 8, 2)]


def landing_reads(nsel: int, half: int, *, rb: int = 0,
                  spec: ExportSpec = ExportSpec()) -> list[dict[str, int]]:
    """Source leaf reads for PK2 order, with the pvrd nw=160 overwrite edge.

    Offsets use the first half-entry export word as zero, before transport ages.
    Every half is one 256-bit row pair at row base + 2*j. A consumer must have
    read it strictly before overwrite_cycle. This publishes constraints; it does
    not assume that the current XR programme can meet them.
    """
    spec.check(nsel)
    if half not in (0, 1) or not 0 <= rb <= 897:
        raise ValueError('bad half or rb+126 exceeds the 10-bit leaf row field')
    out = []
    for rank in range(nsel):
        word, j = divmod(rank, 2)
        p, i = divmod(word, spec.nxw)
        for tile in range(8 * half, 8 * half + 8):
            ordinal = p * 8 * spec.nxw + (tile % 8) * spec.nxw + i
            slot = ordinal % 160
            later = ordinal + 160
            lp, within = divmod(later, 8 * spec.nxw)
            overwrite = lp * spec.period + within
            out.append(dict(rank=rank, tile=tile, leaf=slot % 5,
                            row=rb + 4 * (slot // 5) + 2 * j,
                            available_cycle=spec.entry_cycle(tile, word),
                            overwrite_cycle=overwrite))
    return out


def rows_frame(payload: Sequence[int], tag: int, *, pos: int, user: int,
               mask: int = 1, end: bool = False) -> list[int]:
    """The actual SVC header layout; PK2 spec bit 0 is set, payload is verbatim."""
    if not (0 < len(payload) <= 4095 and tag in range(256) and pos in range(1 << 21)
            and user in range(1024) and mask in range(1, 16)):
        raise ValueError('ROWS header field does not fit the SVC ABI')
    if any(not 0 <= w < 1 << 512 for w in payload):
        raise ValueError('PK2 payload word exceeds 512 bits')
    h = 6 << 508 | int(end) << 507 | mask << 503 | tag << 495 | len(payload) << 480
    return [h | pos << 459 | user << 449 | 1, *payload]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path, help='JSON gids, receiver, half, tag, pos, user, exports[owner][tile]=hex words')
    p.add_argument('output', type=Path)
    p.add_argument('--read-plan', type=Path, help='write source leaf read/overwrite constraints as JSON')
    a = p.parse_args()
    d = json.loads(a.input.read_text())
    spec = ExportSpec(**d.get('spec', {}))
    exports = {int(o): {int(t): [int(w, 16) for w in words] for t, words in tiles.items()}
               for o, tiles in d['exports'].items()}
    payload = merge_repair(exports, d['gids'], d['receiver'], d['half'], spec)
    frame = rows_frame(payload, d['tag'], pos=d['pos'], user=d['user'], mask=d.get('mask', 1))
    a.output.write_text(''.join(f'{w:0128x}\n' for w in frame))
    if a.read_plan:
        a.read_plan.write_text(json.dumps(landing_reads(len(d['gids']), d['half'],
                              rb=d.get('rb', 0), spec=spec), indent=1) + '\n')
    print(json.dumps({'q_cycles': len(frame), 'payload_words': len(payload),
                      'export_entry_slots': spec.passes * spec.period,
                      'die_link_schedule': 'NOT_COMPILED', 'pvrd_reuse_words': 160,
                      'source_abi': 'feaec58ef0'}))


if __name__ == '__main__':
    main()
