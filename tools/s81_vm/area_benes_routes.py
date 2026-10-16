#!/usr/bin/env python3
"""Isolated static 128-wire Beneš route compiler and exact switch witness.

Permutation convention: permutation[source] = destination. Physical wires do
not shuffle between stages. A switch bit 0 passes its pair straight; 1 swaps.
This generates candidate evidence, not a production compiler/RTL change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

N = 128
NSRC = 53
NDEST = 96  # destination = 3 * bank + lane; bank 0..31, lane 0..2
DISTANCES = [1, 2, 4, 8, 16, 32, 64, 32, 16, 8, 4, 2, 1]


def switch_pair(stage: int, switch: int) -> tuple[int, int]:
    distance = DISTANCES[stage]
    a = (switch // distance) * 2 * distance + switch % distance
    return a, a + distance


def complete_assignment(destinations: list[int]) -> list[int]:
    """Complete 53 live injective assignments with 75 pad source edges.

    Unused physical destinations comprise 43 unused bank/lane seats plus 32
    pad destinations. Pad sources are deliberately invalid, even when routed
    to unused bank/lane seats. Runtime seat conflicts need upstream rejection.
    """
    if len(destinations) != NSRC:
        raise ValueError("exactly 53 live source destinations required")
    if any(type(d) is not int or not 0 <= d < NDEST for d in destinations):
        raise ValueError("live destinations must be integers in 0..95")
    if len(set(destinations)) != NSRC:
        raise ValueError("duplicate bank/lane destination")
    used = set(destinations)
    return list(destinations) + [d for d in range(N) if d not in used]


def compile_route(permutation: list[int]) -> list[list[int]]:
    """Route by deterministic alternating coloring, O(N log N).

    Edges are input sources. Each source conflicts with its input pair and
    the source feeding its paired output. Their union is disjoint even cycles
    (parallel edges allowed). Color chooses the upper/lower recursive subnet.
    """
    if len(permutation) != N or sorted(permutation) != list(range(N)):
        raise ValueError("expected a permutation of 0..127")
    bits = [[0] * (N // 2) for _ in DISTANCES]

    def route(p: list[int], depth: int, prefix: int, first: int, last: int):
        n = len(p)
        # Local even wire i expands to global wire (i << depth) | prefix.
        def index(i: int) -> int:
            a = (i << depth) | prefix
            return (a >> (depth + 1)) * (1 << depth) + (a % (1 << depth))

        if n == 2:
            bits[first][index(0)] = p[0]
            return
        inverse = [0] * n
        for source, dest in enumerate(p):
            inverse[dest] = source
        color = [-1] * n
        for seed in range(n):
            if color[seed] != -1:
                continue
            color[seed] = 0
            stack = [seed]
            while stack:
                source = stack.pop()
                for neighbor in (source ^ 1, inverse[p[source] ^ 1]):
                    if color[neighbor] == -1:
                        color[neighbor] = color[source] ^ 1
                        stack.append(neighbor)
                    elif color[neighbor] == color[source]:
                        raise AssertionError("non-bipartite routing graph")
        children = [[-1] * (n // 2) for _ in range(2)]
        for source, dest in enumerate(p):
            c = color[source]
            bits[first][index(source & ~1)] = c ^ (source & 1)
            bits[last][index(dest & ~1)] = c ^ (dest & 1)
            children[c][source // 2] = dest // 2
        for c in (0, 1):
            route(children[c], depth + 1, prefix | (c << depth), first + 1, last - 1)

    route(permutation, 0, 0, 0, len(DISTANCES) - 1)
    return bits


def simulate(bits: list[list[int]], inputs: list) -> list:
    """Independent physical switch simulation, including arbitrary payloads."""
    if len(inputs) != N or len(bits) != len(DISTANCES):
        raise ValueError("expected 128 inputs and 13 stages")
    wires = list(inputs)
    for stage, setting in enumerate(bits):
        if len(setting) != 64 or any(type(b) is not int or b not in (0, 1) for b in setting):
            raise ValueError("expected 64 binary switch settings per stage")
        out = list(wires)
        for switch, crossed in enumerate(setting):
            a, b = switch_pair(stage, switch)
            out[a], out[b] = (wires[b], wires[a]) if crossed else (wires[a], wires[b])
        wires = out
    return wires


def expected_output(permutation: list[int], inputs: list) -> list:
    out = [None] * N
    for source, dest in enumerate(permutation):
        out[dest] = inputs[source]
    return out


def witness(name: str, permutation: list[int], rng: random.Random, live=False) -> dict:
    bits = compile_route(permutation)
    # Exact record: valid, source identity, 128 data bits, row14, mask4, tag8.
    # Pad records retain unique identities to expose errors invisible on zeros.
    payloads = [(int(s < NSRC) if live else 1, s, rng.getrandbits(128),
                 rng.getrandbits(14), rng.getrandbits(4), rng.getrandbits(8))
                for s in range(N)]
    actual = simulate(bits, payloads)
    expected = expected_output(permutation, payloads)
    if actual != expected:
        raise AssertionError(f"route mismatch: {name}")
    mutant = [row.copy() for row in bits]
    mutant[6][31] ^= 1
    mutant_out = simulate(mutant, payloads)
    mismatches = [i for i in range(N) if mutant_out[i] != expected[i]]
    if not mismatches:
        raise AssertionError(f"switch mutant survived: {name}")
    return dict(name=name, permutation_source_to_destination=permutation,
                live_bank_lane_assignment=([{'source': s, 'bank': permutation[s] // 3,
                                             'lane': permutation[s] % 3} for s in range(NSRC)]
                                           if live else None),
                stage_bits=bits, stage_bits_hex_lsb_switch0=[f'{sum(b << j for j, b in enumerate(row)):016x}' for row in bits],
                exact_records_compared=N, exact_pass=True,
                exact_payload_sha256=hashlib.sha256(json.dumps(actual).encode()).hexdigest(),
                mutant=dict(stage=6, switch=31, rejected=True, mismatch_destinations=mismatches))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('results/arch/s81_vm_area_1417/benes_routes.json'))
    parser.add_argument('--assignment', type=Path, help='JSON list of 53 distinct bank*3+lane destinations')
    args = parser.parse_args()
    rng = random.Random(1417)
    cases = []
    assignments = {
        'full53_low_seats': list(range(NSRC)),
        'full53_high_reverse': list(range(95, 95 - NSRC, -1)),
        'full53_bank_lane_stride': [(s * 37 + 17) % NDEST for s in range(NSRC)],
        'full53_random_seats': rng.sample(range(NDEST), NSRC),
    }
    if args.assignment:
        assignments['user_assignment'] = json.loads(args.assignment.read_text())
    for name, assignment in assignments.items():
        cases.append(witness(name, complete_assignment(assignment), rng, live=True))
    for name, permutation in [('identity', list(range(N))), ('reverse', list(reversed(range(N)))),
                              ('rotate1', [(s + 1) % N for s in range(N)]),
                              ('bit_reverse', [int(f'{s:07b}'[::-1], 2) for s in range(N)])]:
        cases.append(witness(name, permutation, rng))
    for i in range(100):
        permutation = list(range(N))
        rng.shuffle(permutation)
        cases.append(witness(f'random_full128_{i:03d}', permutation, rng))
    invalid_rejected = []
    for name, assignment in [('duplicate', [0] * NSRC), ('out_of_range', list(range(52)) + [96]),
                              ('wrong_count', list(range(52))), ('invalid_type', list(range(52)) + [True])]:
        try:
            complete_assignment(assignment)
        except ValueError:
            invalid_rejected.append(name)
        else:
            raise AssertionError(f'invalid assignment accepted: {name}')
    result = dict(status='PASS_ISOLATED_PYTHON_ROUTING_ONLY_NOT_PRODUCTION_OR_PHYSICALLY_QUALIFIED',
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  topology=dict(wires=N, live_sources=NSRC, pad_sources=N-NSRC,
                                bank_lane_destinations=NDEST, pad_destinations=N-NDEST,
                                stages=13, switches_per_stage=64, total_switches=832,
                                pair_xor_distances=DISTANCES,
                                pair_formula='a=(j//distance)*2*distance+j%distance; b=a+distance',
                                bit_semantics='0 straight; 1 cross; no interstage wire shuffle',
                                logical_switch_steps=13, registered_candidate_latency_cycles=26,
                                registers_per_switch_stage=2, initiation_interval_cycles=1,
                                latency_scope='parent candidate has input pin register plus switch output register per stage; ingress/egress/credit costs additional'),
                  compiler_scope='candidate static permutation routes; no production compiler or RTL edits',
                  random_seed=1417, random_full_permutations=100, cases_passed=len(cases),
                  exact_records_compared=N * len(cases), mutants_rejected=len(cases),
                  invalid_assignments_rejected=invalid_rejected, cases=cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'cases_passed', 'exact_records_compared', 'mutants_rejected')}))


if __name__ == '__main__':
    main()
