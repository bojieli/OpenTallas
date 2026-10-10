#!/usr/bin/env python3
"""Independent list reconstruction for compact inverse-map sizing (not RTL)."""
import json
import random
from pathlib import Path
from uarch_model_hgi_row_gather import inverse_selected_model


def check(owners, group):
    count = [owners.count(r) for r in range(group)]
    base = [sum(count[:r]) for r in range(group)]
    inv = [-1] * len(owners)
    j = [0] * group
    for i, r in enumerate(owners):
        inv[base[r] + j[r]] = i
        j[r] += 1
    # Golden uses each selection's original list index, not the prefix map.
    owned = [[i for i, owner in enumerate(owners) if owner == r]
             for r in range(group)]
    restored = [None] * len(owners)
    empty = 0
    for slot in range(max(count)):
        for r in range(group):
            if slot >= count[r]:
                empty += 1
                continue
            i = inv[base[r] + slot]
            assert i == owned[r][slot]
            assert restored[i] is None
            restored[i] = (r, slot)
    golden = [(r, owners[:i].count(r)) for i, r in enumerate(owners)]
    assert restored == golden
    assert sum(count) == len(owners)
    return dict(group=group, k=len(owners), m=max(count), empty_slots=empty,
                inverse_records=len(inv), verdict='PASS')


def main():
    rng = random.Random(20261010)
    cases = [check([77]*2048,96), check([0]*512,96),
             check([r for r in range(96) for _ in range(5)] + [0]*32,96),
             check([rng.randrange(96) for _ in range(512)],96)]
    for g in (1,2,4,8):
        cases.append(check([rng.randrange(g) for _ in range(2048)],g))
    out = Path('results/uarch/hgi_inverse_selected_20261010')
    out.mkdir(parents=True, exist_ok=True)
    (out/'sizing.json').write_text(json.dumps(dict(
        typical=inverse_selected_model(), worst=inverse_selected_model(k=2048)),indent=2)+'\n')
    (out/'mapping.json').write_text(json.dumps(dict(
        qualification='Algorithm only, not RTL exactness or rate evidence',
        cases=cases, verdict='PASS'),indent=2)+'\n')
    print(f'PASS compact inverse mapping {len(cases)} cases; RTL pending')


if __name__ == '__main__':
    main()
