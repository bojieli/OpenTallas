#!/usr/bin/env python3
"""Exhaustively check the native XOR-map per-PC Engram address bound."""
import json

def check():
    maximum_sectors = maximum_rows = crossings = 0
    for first in range(1 << 17):
        rows, counts = {}, {}
        for address in range(first, first + 9):
            pc = ((address >> 2) ^ (address >> 7) ^ (address >> 12)) & 31
            rows.setdefault(pc, set()).add(address >> 15)
            counts[pc] = counts.get(pc, 0) + 1
        maximum_sectors = max(maximum_sectors, max(counts.values()))
        maximum_rows = max(maximum_rows, max(map(len, rows.values())))
        crossings += int((first >> 15) != ((first + 8) >> 15))
    assert (maximum_sectors, maximum_rows) == (8, 1)
    witness = [a for a in range(2043, 2052)
               if ((a >> 2) ^ (a >> 7) ^ (a >> 12)) & 31 == 16]
    assert witness == list(range(2044, 2052))
    return {"checked_sector_start_residues": 1 << 17,
            "crossing_start_residues": crossings,
            "max_sectors_per_PC_per_logical_row": maximum_sectors,
            "max_distinct_physical_rows_per_PC_per_logical_row": maximum_rows,
            "four_rows_requests_per_PC_max": 4 * maximum_sectors,
            "four_rows_physical_row_visits_per_PC_max": 4 * maximum_rows,
            "universal_timing_bound_certified": False}

if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
