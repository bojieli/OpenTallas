#!/usr/bin/env python3
"""Source-model only: registered quad-local D storage, preserving 2048 SRAMs.

This is a successor comparison, not a physical or RTL qualification. The
arithmetic tile outputs remain head-major, with the literal HG1 quad order.
"""
import argparse
import json
from pathlib import Path


def physical_head(cohort, lane):
    return ((cohort >> 1) << 3) | ((lane >> 1) << 2) | ((cohort & 1) << 1) | (lane & 1)


def location(head):
    return ((head >> 3) * 2 + ((head >> 1) & 1), ((head >> 2) & 1) * 2 + (head & 1))


def payload(record, head, dim):
    return ((record + 1) << 24) ^ (head << 16) ^ (dim * 131 + 17)


def flag(record, head, dim):
    return ((record * 3 + head * 5 + dim) % 19) == 0


def prove(mutant=None):
    # One word per real 32x128 SRAM address. Only two of 32 rows are allocated,
    # exactly as the current D serializer. No memory exists for a missing bank.
    mem = {}
    checks = 0
    mapping = [physical_head(a, l) for a in range(4) for l in range(4)]
    assert sorted(mapping) == list(range(16))
    for h in range(16):
        assert physical_head(*location(h)) == h

    # Records 0 and 1 coexist; record 2 reuses epoch 0 only after its drain.
    # H1 uses the same complete capture image, but only head 0 is observable.
    for active_heads in (16, 1):
        mem.clear()
        for record in range(3):
            epoch = record & 1
            for c in range(16):
                for tile in range(32):
                    dim = tile * 16 + c
                    for cohort in range(4):
                        words, flags = [], []
                        for lane in range(4):
                            h = physical_head(cohort, lane)
                            words.append(payload(record, h, dim) if h < active_heads else 0)
                            # Deliberately poison inactive flags: only real output
                            # selection/masking may suppress them, never preload.
                            flags.append(flag(record, h, dim) if h < active_heads else True)
                        addr_epoch = 0 if mutant == "epoch_alias" else epoch
                        mem[tile, cohort, c, addr_epoch] = (words, flags)
            # Retained epoch 0 must survive the complete epoch 1 capture.
            for observed_record in ([0, 1] if record == 1 else [record]):
                e = observed_record & 1
                for h in range(active_heads):
                    a, lane = location(h)
                    if mutant == "contiguous_quad":
                        a, lane = h // 4, h % 4
                    for block in range(8):
                        # Each canonical commit carries 8 VM banks x8 FP32
                        # words, selecting four consecutive feature tiles.
                        for group in range(4):
                            tile = 4 * block + group
                            for c in range(16):
                                dim = tile * 16 + c
                                word, flags = mem[tile, a, c, e]
                                assert word[lane] == payload(observed_record, h, dim)
                                assert flags[lane] == flag(observed_record, h, dim)
                                checks += 2
    return checks


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    checks = prove()
    rejected = []
    for mutant in ("contiguous_quad", "epoch_alias"):
        try:
            prove(mutant)
        except (AssertionError, KeyError):
            rejected.append(mutant)
        else:
            raise AssertionError(f"mutant escaped: {mutant}")
    # Explicit source register accounting; physical pin-register cloning,
    # clock buffers, local decode and mapped fanout repair remain unmeasured.
    ff = dict(write_face=138, stored_flags=128, read_flags=64,
              read_lane_select=2, read_response_valid=1, output_face=529)
    result = dict(
        status="MODEL_PASS_RTL_AND_PHYSICAL_UNQUALIFIED",
        checks=checks, rejected_mutants=rejected,
        head_order=[[physical_head(a, l) for l in range(4)] for a in range(4)],
        stores=128, macros_per_store=16, total_macros=2048,
        macro_shape="32x128 actual source macro; two allocated epoch addresses",
        source_ff_per_store=ff, source_ff_total_per_store=sum(ff.values()),
        source_clock_endpoints_per_store=sum(ff.values()) + 16,
        source_census_is_not_mapped=True,
        registered_tile_selector=dict(leaves=32, inputs=4 * 528,
                                      outputs=528, source_ff_per_leaf=2646),
        calendar=dict(write_availability_extra_edges=1,
                      read_extra_edges_vs_current_registered_D=3,
                      registered_cohort_selector_edges=2,
                      h16_commits=128, h1_commits=8,
                      capture_edges=16,
                      h1_min_record_interval_edges=16),
        open=["Actual RTL and SRAM port proof", "Native current-bank producer join",
              "Registered face control/clock equality proof", "Mapped cell/clock census",
              "Actual pin budgets/access/cuts", "Whole forward placement",
              "Immutable whole-operation throughput price"],
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"PASS quad-local PV model checks={checks}, mutants={rejected}")


if __name__ == "__main__":
    main()
