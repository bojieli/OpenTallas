"""Fixed packed136 service bounds, derived from the existing stream-clock RTL.

Not an HBM fetch bound or a production calendar compiler. This gives the minimum
copy/cache time AFTER actual issuer start_v. All sector delivery is assumed to
meet the mandatory existing 4,4,4,4,1 stream pattern without a stall.
"""
import json
from pathlib import Path


def contract(rows):
    assert 1 <= rows <= 64
    sectors = ((rows * 136 + 127) // 128) * 4
    # On cache OPEN, elapsed=slot_phase=record_phase=0. First row is
    # eligible at OPEN+3; slot_phase1 is skipped every five edges.
    last_row_write = 3 + ((rows - 1) // 4) * 5 + (rows - 1) % 4
    remaining, sector_edges = sectors, 0
    while remaining:
        remaining -= min(remaining, 1 if sector_edges % 5 == 4 else 4)
        sector_edges += 1
    busy_clear_nba = max(last_row_write, sector_edges) + 1
    return dict(rows=rows, sectors=sectors, sector_edges=sector_edges,
                last_row_write_after_cache_open=last_row_write,
                busy_clear_nba_after_cache_open=busy_clear_nba,
                # Minimum cache bench can assert OPEN after observing the
                # clear NBA, so the next OPEN is accepted one edge later.
                next_direct_cache_open=busy_clear_nba + 1,
                # Feed open_q delays issuer start by one stream edge.
                issuer_start_to_ready=last_row_write + 2,
                # Issuer sees busy clear on a subsequent edge, then feed
                # open_q adds one more edge before the next cache OPEN.
                issuer_start_separation=busy_clear_nba + 2)


def verify_sector_prefixes(rows):
    """Prove gather availability and circular buffer capacity for the schedule.

    This checks integer producer/consumer prefix inequalities independently of
    RTL payload values, using the fixed slot positions declared above.
    """
    timing = contract(rows)
    received = consumed = 0
    writes = {3 + (r // 4) * 5 + r % 4: r for r in range(rows)}
    max_occupancy = 0
    for edge in range(1, max(timing['sector_edges'], max(writes)) + 1):
        incoming = min(timing['sectors'] - received, 1 if (edge - 1) % 5 == 4 else 4)
        # The RTL reads present[] before this edge's sector NBA updates.
        if edge in writes:
            assert received - consumed >= 5, (rows, edge, received, consumed)
        assert received - consumed + incoming <= 16, (rows, edge)
        max_occupancy = max(max_occupancy, received - consumed + incoming)
        received += incoming
        if edge in writes:
            consumed += 5 if writes[edge] % 4 == 3 else 4
    assert received == timing['sectors']
    assert consumed == (rows * 17) // 4
    return max_occupancy


def verify_recorded_witnesses(root):
    import re
    log = (root / 'results/rtl/hbm_smxl_cache_1020/minimum/m0.log').read_text()
    for rows in [64, 60, 16, 1]:
        opens = [int(m.group(1)) for m in re.finditer(
            rf'OPEN c=(\d+) bank=[01] epoch=\d+ count={rows} ok=1', log)]
        assert len(opens) == 2, (rows, opens)
        observed = opens[1] - opens[0]
        assert observed == contract(rows)['next_direct_cache_open'], (rows, observed, contract(rows))
    # Two independently observed actual production readiness transitions.
    for rows, issuer_start, ready_edge in [(64, 4486, 4569), (8, 4570, 4583)]:
        assert issuer_start + contract(rows)['issuer_start_to_ready'] == ready_edge
    # This is a lower bound at the observed start, not a new valid calendar.
    needed = 4773 + contract(64)['issuer_start_to_ready']
    assert needed == 4856 and needed - 4851 == 5
    return dict(minimum_witness_rows=[64, 60, 16, 1], production_ready_witness_rows=[64, 8],
                failing_observed_start=4773, unchanged_go=4851,
                earliest_ready_at_observed_start=needed, shortage_edges=5,
                calendar_qualified=False, hbm_fetch_qualified=False, price_qualified=False)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(dict(scope=__doc__, rows=[dict(contract(n), max_sector_occupancy=verify_sector_prefixes(n)) for n in range(1, 65)],
                          evidence=verify_recorded_witnesses(root)), indent=2))
