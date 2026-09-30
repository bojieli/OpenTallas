#!/usr/bin/env python3
"""Checked contract: DeepSeek-V4.1 selected compressed-KV row id -> owner die / stack / local row / HBM sectors.

A compressed row's GLOBAL id g is its position in the source layer's compressed cache (the golden's
state["ckv"][src][g]; the indexer's top-k returns these positions, sorted ascending).  Rows are placed in 16-row
groups striped over the tensor group's 4 dies, then over each die's 4 HBM stacks:

    group = g // 16
    die   = group % 4            = g[5:4]
    stack = (group // 4) % 4     = g[7:6]
    local = (g // 256) * 16 + g % 16      (row index inside that die/stack's region)
    sector(k) = region_base_sector[stack] + 9 * local + k,  k = 0..8   (288-B row: 256 B of E2M1 nibbles, 32 E4M3 scales)

Implemented by rtl/chip/ot_chip_v41x_ckv_selected_dma.sv (source_die/source_stack/source_local),
rtl/chip/ot_chip_v41x_ckv_sel_ids.sv (rd_die/rd_stack/rd_local, owned lists by g[5:4]),
rtl/chip/ot_chip_v41x_ckv_sel_fetch.sv and rtl/chip/ot_chip_v41x_ckv_pc_fetch.sv (port = stack * P + local % P).
tests/test_v41_selection_global_ids.py simulates the RTL against this module.

Each die fetches only the rows it owns and all-gathers them: every die of the tensor group stages all n_sel rows.
"""
from __future__ import annotations

GROUP = 16
DIES = 4
STACKS = 4
SECTORS_PER_ROW = 9


def owner(g: int) -> tuple[int, int, int]:
    """(die, stack, local row) of global compressed-row id g."""
    if g < 0:
        raise ValueError(g)
    group = g // GROUP
    return group % DIES, (group // DIES) % STACKS, (g // (GROUP * DIES * STACKS)) * GROUP + g % GROUP


def sectors(g: int, region_base_sector) -> list[int]:
    """The nine HBM sector addresses of row g on its owner stack."""
    _, stack, local = owner(g)
    return [region_base_sector[stack] + SECTORS_PER_ROW * local + k for k in range(SECTORS_PER_ROW)]


def port(g: int, ports_per_stack: int) -> int:
    """Request port of row g in the wide fetch (ot_chip_v41x_ckv_pc_fetch, P = ports_per_stack)."""
    _, stack, local = owner(g)
    return stack * ports_per_stack + local % ports_per_stack


def bits_form(g: int) -> tuple[int, int, int]:
    """The RTL's bit-slice form of owner(); equal to owner() for every g >= 0."""
    return (g >> 4) & 3, (g >> 6) & 3, ((g >> 8) << 4) | (g & 15)


def region_rows(n_rows: int, stack: int, die: int) -> int:
    """Number of local rows die/stack holds when the source has n_rows compressed rows."""
    return sum(1 for g in range(n_rows) if owner(g)[:2] == (die, stack))


if __name__ == "__main__":
    import random
    rnd = random.Random(1)
    for g in list(range(4096)) + [rnd.randrange(1 << 20) for _ in range(100000)]:
        assert owner(g) == bits_form(g), g
    print("owner() == RTL bit form for 104,096 ids")
