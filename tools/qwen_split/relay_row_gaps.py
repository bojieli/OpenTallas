"""Actual vacant row intervals used by the Qwen relay site allocator.

This only permits searching a row channel. The allocator's full occupancy and
pin-to-pin reach checks remain mandatory for every placed frame.
"""

def row_gaps(intervals):
    merged = []
    for lo, hi in sorted(set(intervals)):
        if hi <= lo:
            raise ValueError('nonpositive tile height')
        if merged and lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(hi, merged[-1][1]))
        else:
            merged.append((lo, hi))
    return [(a[1], b[0]) for a, b in zip(merged, merged[1:]) if b[0] > a[1]]


def contains_frame(gaps, y, height):
    return height > 0 and any(lo <= y and y + height <= hi for lo, hi in gaps)
