#!/usr/bin/env python3
"""Static LOAD lowering for the proposed vmfc W159 / vmdel load62 ABI.

This module emits command payloads, not an executable replay or qualification.
The caller supplies the consumer's actual logical-word -> (quarter, sector,
word) placement and source bank/epoch ownership. Window completion and fixed
routing ages must be measured and scheduled before these commands may run.
"""
from __future__ import annotations

FMT = {'FP32': 0, 'BF16': 1, 'FP8E4M3': 2, 'INT8': 4, 'U32': 5, 'UE8M0': 6}
SIZE = {'FP32': 4, 'BF16': 2, 'FP8E4M3': 1, 'INT8': 1, 'U32': 4, 'UE8M0': 1}
QUARTERS = ('SW', 'SE', 'NW', 'NE')
LOAD_FIELDS = {'bank': (0, 1), 'epoch': (1, 16), 'group': (17, 2),
               'slot': (19, 6), 'byte': (25, 5), 'fmt': (30, 3),
               'sector': (33, 16), 'word': (49, 3), 'count': (52, 4),
               'release': (56, 1), 'destbank': (57, 3), 'destq': (60, 2)}


def load_word(**fields):
    """Encode the real proposed source consumer ABI; reject truncation."""
    if set(fields) != set(LOAD_FIELDS):
        raise ValueError('load command needs exactly ' + ','.join(LOAD_FIELDS))
    value = 0
    for name, (lo, width) in LOAD_FIELDS.items():
        x = int(fields[name])
        if not 0 <= x < 1 << width:
            raise ValueError(f'{name}={x} does not fit {width} bits')
        value |= x << lo
    if fields['fmt'] not in SIZE_BY_FMT or not 1 <= fields['count'] <= 8:
        raise ValueError('unsupported format or count (FP4 code3 is not UE8M0)')
    if fields['byte'] + fields['count'] * SIZE_BY_FMT[fields['fmt']] > 32:
        raise ValueError('load crosses a source sector')
    if fields['word'] + fields['count'] > 8:
        raise ValueError('load crosses a destination sector')
    if (fields['sector'] & 7) != fields['destbank']:
        raise ValueError('destination bank differs from sector bank')
    return value


SIZE_BY_FMT = {FMT[name]: size for name, size in SIZE.items()}


def vmfc_load_word(lane, command, legacy_payload=0):
    """Preserve old W89 fields; append one lane-valid and one shared load62."""
    if not 0 <= lane < 8 or not 0 <= command < 1 << 62 or not 0 <= legacy_payload < 1 << 89:
        raise ValueError('vmfc payload out of range')
    return legacy_payload | (1 << (89 + lane)) | (command << 97)


def source_location(address):
    """Invert vmks' actual PC hash and fixed 16x4 burst window address.

    d4g has two stacks, each split across two 16-PC quadrants. Source address
    selects a byte in a sector; a window holds every slot of all its PCs.
    """
    if not 0 <= address < 1 << 36:
        raise ValueError('source outside current two-stack d4g address range')
    stack, local = address >> 35, address & ((1 << 35) - 1)
    sector = local >> 5
    pc = ((sector >> 2) ^ (sector >> 7) ^ (sector >> 12)) & 31
    return dict(quarter=2 * stack + pc // 16,
                lane=(pc & 3) + 4 * ((pc >> 2) & 1), group=(pc >> 3) & 1,
                slot=(((sector >> 7) & 1) << 5) | (((sector >> 12) & 7) << 2) | (sector & 3),
                row=sector >> 15, col=(sector >> 8) & 15,
                byte=local & 31, pc=pc)


def lower_load(a, o, destination, *, bank=0, epoch=1):
    """Lower effective fixture descriptors [base,n,m,stride,istride,space,fmt].

    destination(logical_word) returns the actual physical (q, sector, word).
    No destination placement, fixture value, ready edge, or routing age is
    invented here. Every emitted operation stays within one source and one
    destination sector. Source windows are explicit to price full64-PC reads.
    """
    if a[5] != 'HBM' or o[5] != 'VM' or a[6] not in FMT or o[6] not in ('FP32', 'U32'):
        raise ValueError('unsupported DMA.LOAD descriptors')
    if (a[6] == 'U32') != (o[6] == 'U32') or a[1:3] != o[1:3]:
        raise ValueError('LOAD shape or U32 identity mismatch')
    if a[1] <= 0 or a[2] <= 0 or a[4] != 1 or o[4] != 1:
        raise ValueError('LOAD needs nonempty contiguous inner rows')
    operations, windows = [], {}
    size = SIZE[a[6]]
    for row in range(a[2]):
        index = 0
        while index < a[1]:
            address = a[0] + row * a[3] + index * size
            loc = source_location(address)
            q, sector, word = destination(o[0] + row * o[3] + index)
            if not (0 <= q < 4 and 0 <= sector < 1 << 16 and 0 <= word < 8):
                raise ValueError('destination outside hardware aperture')
            count = min(a[1] - index, (32 - loc['byte']) // size, 8 - word)
            # A supplied placement can change at any word. Never assume its
            # remaining words are contiguous just because logical words are.
            for j in range(1, count):
                if destination(o[0] + row * o[3] + index + j) != (q, sector, word + j):
                    count = j
                    break
            if count < 1:
                raise ValueError('source element straddles sector')
            key = (loc['quarter'], loc['row'], loc['col'])
            if key not in windows:
                windows[key] = dict(quarter=loc['quarter'], row=loc['row'], col=loc['col'], bank=bank, epoch=epoch)
            fields = dict(bank=bank, epoch=epoch, group=loc['group'], slot=loc['slot'], byte=loc['byte'],
                          fmt=FMT[a[6]], sector=sector, word=word, count=count, release=0,
                          destbank=sector & 7, destq=q)
            command = load_word(**fields)
            operations.append(dict(source=loc, window=list(key), logical_word=o[0] + row * o[3] + index,
                                   fields=fields, command=command,
                                   calendar_target=56 + loc['quarter'], payload=vmfc_load_word(loc['lane'], command)))
            index += count
    return dict(schema='opentallas.static_dma_load_plan.v1', execution_qualified=False,
                windows=list(windows.values()), operations=operations,
                output_words=a[1] * a[2],
                open_obligations=['source begin/window ready ages', 'bank release after final scheduled read',
                                  'static source-to-destination route ages and contention', 'VM writer calendar slots'])
