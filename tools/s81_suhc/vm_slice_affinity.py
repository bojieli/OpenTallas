#!/usr/bin/env python3
"""Client-affine S81 VM banking: exact logical-row -> (slice, physical row, bank) map (S-FUNC 2026-10-16).

The S81 VM (dsfd_vm_static512_suhc) is four 128-bit slices x 32 banks x 512 entries (16,384 physical rows per
slice).  Today every 512-bit logical row is STRIPED: chunk j (bits 128j..128j+127) lives in slice j at physical row
= logical row, so every port word touches all four slices and every VM port must reach the whole VM (S-VM hub
screen: wider is worse, 28 relay edges at R 900 um).

Client-affine banking places a tensor's rows only in a SLICE SET S beside its consumer's face (k = |S| in {1, 2, 4}).
Region layout (static, compiler-assigned, never a runtime choice):
    logical row r in region R (first logical row B, k = |S|, per-slice physical base P[s]):
      i = r - B;  chunk j (0..3) -> slice S[j % k], physical row P[S[j % k]] + i * (4 / k) + j // k
A logical-row access is therefore four 128-bit bank operations on the same edge: one per slice when k = 4 (the
striped layout is the region {S = [0,1,2,3], P[s] = B}), two in each of two slices when k = 2, four in one slice when
k = 1.  The chunks of one row are bank-distinct by construction: within one slice they are consecutive physical rows
whose bits [1:0] differ, and the XOR bank map (row & 31) ^ (((row >> 5) & 7) << 2) never alters bits [1:0].  Bases
must be aligned to 4 / k physical rows so a row's chunks never straddle that alignment.

Bandwidth consequence (exact, no averaging): a client whose port moves n logical rows per edge on a k-slice set
needs n * 4 / k bank operations per slice per edge out of 32; the static checker counts them per (slice, bank, edge).
Wiring consequence: a client port that touches a region must be wired to every slice of that region.  The contract
names each client's wired slices for reads and writes; an access outside them is a compile error, not a slow path.

This module is pure layout/validation; static_vm_reservations.check() consumes it when a contract names
"slice_affinity" (absent = the historical striped behaviour, unchanged).
"""
from __future__ import annotations

SLICES = 4
SLICE_ROWS = 16384          # physical 128-bit rows per slice (32 banks x 512 entries)
CHUNKS = 4                  # 128-bit chunks per 512-bit logical row
LOGICAL_ROWS = 16384


def xor_bank(phys_row: int) -> int:
    return (phys_row & 31) ^ (((phys_row >> 5) & 7) << 2)


def validate(aff: dict) -> tuple[list, list]:
    """-> (normalised regions, [invalid reasons]).  Regions: {name, first_row, rows, slices, phys_base{slice: row}}."""
    bad, regs = [], []
    if not isinstance(aff, dict) or aff.get('slices', SLICES) != SLICES:
        return [], ['slice_affinity_requires_four_slices']
    for idx, r in enumerate(aff.get('regions') or []):
        try:
            name = str(r.get('name', idx))
            first, rows = r['first_row'], r['rows']
            sl = list(r['slices'])
            base = {int(k): v for k, v in r['phys_base'].items()}
        except (KeyError, TypeError, AttributeError, ValueError):
            bad.append(f'slice_affinity_region_malformed:{idx}'); continue
        if type(first) is not int or type(rows) is not int or first < 0 or rows <= 0 or first + rows > LOGICAL_ROWS:
            bad.append(f'slice_affinity_region_range:{name}'); continue
        if (len(sl) not in (1, 2, 4) or len(set(sl)) != len(sl) or any(type(s) is not int or not 0 <= s < SLICES for s in sl)):
            bad.append(f'slice_affinity_region_slice_set:{name}'); continue
        if sorted(base) != sorted(sl) or any(type(v) is not int for v in base.values()):
            bad.append(f'slice_affinity_region_bases:{name}'); continue
        per = CHUNKS // len(sl)
        if any(v < 0 or v % per or v + rows * per > SLICE_ROWS for v in base.values()):
            bad.append(f'slice_affinity_region_physical_range:{name}'); continue
        regs.append(dict(name=name, first_row=first, rows=rows, slices=sl, phys_base=base, per=per))
    if not regs:
        bad.append('slice_affinity_no_regions')
    # logical ranges disjoint; physical occupancy disjoint per slice
    order = sorted(regs, key=lambda x: x['first_row'])
    for a, b in zip(order, order[1:]):
        if b['first_row'] < a['first_row'] + a['rows']:
            bad.append(f"slice_affinity_logical_overlap:{a['name']}/{b['name']}")
    for s in range(SLICES):
        spans = sorted((x['phys_base'][s], x['phys_base'][s] + x['rows'] * x['per'], x['name']) for x in regs if s in x['slices'])
        for a, b in zip(spans, spans[1:]):
            if b[0] < a[1]:
                bad.append(f'slice_affinity_physical_overlap:slice{s}:{a[2]}/{b[2]}')
    reach = aff.get('client_reach')
    if not isinstance(reach, dict) or any(not isinstance(v, dict) or any(k not in ('read', 'write') for k in v) for v in reach.values()):
        bad.append('slice_affinity_client_reach_missing')
    return regs, bad


def region_of(row: int, regs: list):
    for r in regs:
        if r['first_row'] <= row < r['first_row'] + r['rows']:
            return r
    return None


def chunks(row: int, reg: dict) -> list:
    """the four (slice, physical row, bank) bank operations of one logical-row access."""
    i, k = row - reg['first_row'], len(reg['slices'])
    out = []
    for j in range(CHUNKS):
        s = reg['slices'][j % k]
        p = reg['phys_base'][s] + i * reg['per'] + j // k
        out.append((s, p, xor_bank(p)))
    return out


def striped(first_row: int = 0, rows: int = LOGICAL_ROWS, name: str = 'striped') -> dict:
    """the historical layout as a region (all four slices, physical row = logical row)."""
    return dict(name=name, first_row=first_row, rows=rows, slices=[0, 1, 2, 3], phys_base={s: first_row for s in range(SLICES)})


def allocate(tensors: list, first_row: int = 0) -> dict:
    """Pack tensors into affine regions: logical rows consecutive (in the given order), physical rows first-fit per
    slice.  tensors: [{name, rows, slices}].  -> {regions, slice_rows_used, overflow[]}.  No silent shrink."""
    nxt = {s: 0 for s in range(SLICES)}
    regs, overflow, cur = [], [], first_row
    for t in tensors:
        sl, per = list(t['slices']), CHUNKS // len(t['slices'])
        base = {}
        for s in sl:
            b = -(-nxt[s] // per) * per
            base[s] = b
        end = {s: base[s] + t['rows'] * per for s in sl}
        if any(v > SLICE_ROWS for v in end.values()):
            overflow.append(dict(tensor=t['name'], slices=sl, need=t['rows'] * per,
                                 free={s: SLICE_ROWS - base[s] for s in sl}))
        for s in sl:
            nxt[s] = end[s]
        regs.append(dict(name=t['name'], first_row=cur, rows=t['rows'], slices=sl, phys_base=base))
        cur += t['rows']
    return dict(regions=regs, slice_rows_used=dict(nxt), slice_rows=SLICE_ROWS, overflow=overflow,
                logical_rows_used=cur - first_row)
