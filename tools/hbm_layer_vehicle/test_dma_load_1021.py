#!/usr/bin/env python3
"""LOAD source-address and split-packet contract checks against actual RTL ABI."""
import random
from dma_load_1021 import lower_load, source_location, load_word, vmfc_load_word, vmfc_release_word


def test_inverse():
    rng = random.Random(1021)
    addresses = [0, 31, 32, (1 << 35) - 1, 1 << 35, (1 << 36) - 1]
    addresses += [rng.randrange(1 << 36) for _ in range(4096)]
    for address in addresses:
        x = source_location(address)
        j, beat = x['slot'] >> 2, x['slot'] & 3
        bhi, col = j & 7, (x['col'] << 1) | (j >> 3)
        # Actual vmks source address: {row,bhi,col,P^col^{row[1:0],bhi},2'b00}.
        hashed = x['pc'] ^ col ^ (((x['row'] & 3) << 3) | bhi)
        sector = (x['row'] << 15) | (bhi << 12) | (col << 7) | (hashed << 2) | beat
        assert ((x['quarter'] // 2) << 35) | (sector << 5) | x['byte'] == address
        assert x['lane'] in range(8) and x['group'] in range(2)
    print('ADDRESS_INVERSE_PASS', len(addresses))


def test_packet_split():
    for fmt, size in [('FP32', 4), ('BF16', 2), ('FP8E4M3', 1), ('UE8M0', 1), ('INT8', 1), ('U32', 4)]:
        o_fmt = 'U32' if fmt == 'U32' else 'FP32'
        a = [17179889664, 19, 3, 96, 1, 'HBM', fmt]
        o = [88966, 19, 3, 31, 1, 'VM', o_fmt]
        def place(word):
            return (2, (word // 8) & 8191, word & 7)
        plan = lower_load(a, o, place)
        reconstructed = []
        for op in plan['operations']:
            f = op['fields']
            assert op['payload'] >> 97 == op['command']
            assert (op['payload'] >> 89) & 255 == 1 << op['source']['lane']
            assert f['word'] + f['count'] <= 8 and f['byte'] + size * f['count'] <= 32
            for j in range(f['count']):
                reconstructed.append((op['logical_word'] + j, f['sector'], f['word'] + j))
        expected = [(o[0] + r * o[3] + j, *place(o[0] + r * o[3] + j)[1:]) for r in range(3) for j in range(19)]
        assert reconstructed == expected
        assert not plan['execution_qualified']
    print('PACKET_SPLIT_PASS formats6 rows3 unalignedtail19')


def test_rejections():
    f = dict(bank=0, epoch=1, group=0, slot=0, byte=0, fmt=0, sector=0, word=0, count=8, release=0, destbank=0, destq=0)
    for change in [dict(fmt=3), dict(count=0), dict(count=9), dict(byte=31), dict(word=1), dict(destbank=1), dict(epoch=65536)]:
        try:
            load_word(**dict(f, **change))
        except ValueError:
            pass
        else:
            raise AssertionError(change)
    assert vmfc_load_word(2, load_word(**f), (1 << 88) | 17) & ((1 << 89) - 1) == (1 << 88) | 17
    release = vmfc_release_word(0xfe, bank=1, epoch=37)
    assert (release >> 89) & 255 == 0xfe
    command = release >> 97
    assert command & 1 == 1 and (command >> 1) & 65535 == 37
    assert (command >> 52) & 15 == 0 and (command >> 56) & 1 == 1
    print('REJECTIONS_PASS malformed7 old89preserved')


if __name__ == '__main__':
    test_inverse()
    test_packet_split()
    test_rejections()
