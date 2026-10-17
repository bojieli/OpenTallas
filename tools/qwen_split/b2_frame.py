#!/usr/bin/env python3
"""TP8 b2 physical result frame; position changes only, arithmetic group stays fixed."""
GROUPS = 3072
POSITIONS = 24

def group_at(split, position, bandf=2):
    if bandf not in (1, 2) or not 0 <= split <= 12 or not 0 <= position < POSITIONS:
        raise ValueError((split, position, bandf))
    bits = 2 if bandf == 2 else 3
    band, slot = divmod(position, 1 << bits)
    top = 7 + bits
    if split <= top:
        count = 1 << (top - split)
        return band * count + slot if slot < count else None
    return slot if band == 0 and slot < GROUPS >> split else None

def position_of(split, group, bandf=2):
    if not 7 <= split <= 11 or not 0 <= group < GROUPS >> split:
        raise ValueError(f'empty/unsupported TP8 output group: split={split}, group={group}')
    bits = 2 if bandf == 2 else 3
    top = 7 + bits
    return (group // (1 << (top-split))) * (1 << bits) + group % (1 << (top-split)) if split <= top else group

if __name__ == '__main__':
    checks = 0
    for split in range(7, 13):
        for bandf in (1, 2):
            got = [group_at(split, p, bandf) for p in range(POSITIONS)]
            active = [g for g in got if g is not None]
            assert sorted(active) == list(range(GROUPS >> split))
            for group in active:
                assert group_at(split, position_of(split, group, bandf), bandf) == group
                checks += 1
    print(f'PASS b2_frame bijection {checks} groups; split12 empty and position_of rejected')
