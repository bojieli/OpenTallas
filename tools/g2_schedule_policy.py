"""Conservative configuration-time G2 residency policy; not runtime adaptation.

Choose the widest supported whole-K pass that can replay in the existing banks.
This is a capacity heuristic, not a latency/energy optimizer: activation traffic,
recurrence spacing and external service rates can change the best schedule.
"""


def choose_schedule(rows: int, columns: int, depth: int) -> dict:
    if rows < 1 or columns < 1 or depth < 1:
        raise ValueError('rows, columns and depth must be positive')
    lanes = 8
    capacity = 1024
    local_columns = (columns + lanes - 1) // lanes
    row_words = local_columns * depth
    width = min(3, local_columns, capacity // depth)
    if rows == 1:
        reason = 'single row has no cross-row reuse'
    elif row_words <= capacity:
        reason = 'complete weight row fits resident banks'
    elif width == 0:
        reason = 'one whole-K column exceeds residency capacity; stream row-first'
    else:
        return {'pass_first': True, 'pass_columns': width,
                'reason': 'widest supported whole-K pass that fits resident banks',
                'packed_row_words': row_words, 'packed_pass_words': width * depth,
                'capacity_words': capacity}
    return {'pass_first': False, 'pass_columns': 3, 'reason': reason,
            'packed_row_words': row_words, 'packed_pass_words': None,
            'capacity_words': capacity}
