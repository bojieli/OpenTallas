#!/usr/bin/env python3
"""Declared ROM-mask test stimulus, never an internal output provider.
Matches the checked-in physical macro's 8-way bitline mux exactly.
"""
import argparse
from pathlib import Path


def value(kind, row, lane):
    if kind == 'n':
        return 0x40000000 ^ (row << 8) ^ lane
    return ((0x3f000000 ^ (row << 8) ^ lane) << 32) | (0xbf000000 ^ (row << 8) ^ lane)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    narrow = {layer * 138 + off for layer in range(36) for off in (0, 9, 10, 73, 74, 137)} | {4968, 5031}
    for kind, columns, lanes, width, rows in [('n', 8, 8, 32, narrow), ('w', 16, 4, 64, {0, 4095, 4096, 8191})]:
        for column in range(columns):
            for depth in range(2):
                physical = [0] * 512
                for row in rows:
                    if row // 4096 != depth:
                        continue
                    local = row % 4096
                    word = sum(value(kind, row, column * lanes + k) << (width * k) for k in range(lanes))
                    for bit in range(266):
                        if (word >> bit) & 1:
                            physical[local // 8] |= 1 << (bit * 8 + local % 8)
                path = args.out / f'crom_{kind}_c{column}_d{depth}.viamap.hex'
                path.write_text(''.join(f'{word:0532x}\n' for word in physical))


if __name__ == '__main__':
    main()
