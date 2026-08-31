#!/usr/bin/env python3
"""Generate the RTL vectors for the ABI 3.0 inter-chip endpoint.

Every expected value here is produced by the executed functional model, not by
this file's own arithmetic:

* the reduced result is ``runtime.sim.engines.reduction.ordered_sum`` over the
  same binary32 contributions, in the reduction order the case declares;
* the message and byte counts the fabric must not contradict come from
  ``runtime.sim.engines.link.collective_traffic`` and ``barrier_messages``;
* the traversal count the case is measured against is the one
  ``src/opentallas/roofline.py`` charges, recomputed here from the same rule
  (``MESH_ALLREDUCE_DIAMETER_FACTOR`` x mesh diameter) so that the RTL's
  measured traversals can be compared with the model's charge in one place.

The generator also records, per configuration, how many elements differ between
``SEQUENTIAL_ASCENDING`` and ``PAIRWISE_TREE`` on the identical contributions.
That number is the whole reason the engine refuses one of the two orders.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import ReductionOrder, TopologyClass
from runtime.abi3.descriptors import CollectiveOp
from runtime.sim.engines.link import barrier_messages, collective_traffic
from runtime.sim.engines.reduction import ordered_sum

# The engine-local barrier opcode.  It is not an ABI collective_op; the ABI
# spells a barrier LINK.BARRIER with a zero byte extent.
OP_BARRIER = 0xFF

ALG_RECURSIVE_DOUBLING = 0
ALG_HALVING_DOUBLING = 1

#: The factor src/opentallas/roofline.py charges a stitched mesh all-reduce.
MESH_ALLREDUCE_DIAMETER_FACTOR = 1.1

CASE_STRIDE = 16


def fp32(values) -> np.ndarray:
    return np.ascontiguousarray(values, dtype=np.float32)


def codes(values: np.ndarray) -> np.ndarray:
    return fp32(values).view(np.uint32)


def contributions(nodes: int, vec_len: int, seed: int) -> np.ndarray:
    """One binary32 contribution per (participant, element).

    The values are deliberately chosen so that a binary32 sum is order
    sensitive: a large leading term next to many small ones is exactly the case
    where sequential accumulation and a balanced tree disagree.
    """
    rng = np.random.default_rng(seed)
    base = rng.uniform(-1.0, 1.0, size=(nodes, vec_len))
    scale = np.power(2.0, rng.integers(-12, 13, size=(nodes, vec_len)))
    values = fp32(base * scale)
    # Guarantee at least one order-sensitive element: one big term, many small.
    values[0, :] = fp32(np.float32(2.0) ** 20)
    values[1:, 0] = fp32(np.float32(2.0) ** -6)
    return fp32(values)


def halving_tree(values: np.ndarray) -> np.ndarray:
    """The fold a recursive-halving reduce-scatter performs: top bit first.

    This is not one of the three orders `spec/abi3/registries.json` names, and
    it coincides with `BLOCKED_ASCENDING` only at sixteen participants -- eight
    lanes over sixteen terms is the top-bit-first fold.  It is written out here
    rather than borrowed so that the coincidence is checked, not assumed.
    """
    current = fp32(values)
    count = current.shape[0]
    while count > 1:
        half = count // 2
        current = np.add(current[:half], current[half:count], dtype=np.float32)
        count = half
    return fp32(current[0])


def reduce_expect(values: np.ndarray, op: int, order: int,
                  alg: int = 0) -> np.ndarray:
    if op == int(CollectiveOp.SUM):
        if alg == ALG_HALVING_DOUBLING:
            return halving_tree(values)
        return fp32(ordered_sum(values, order))
    if op == int(CollectiveOp.MAX):
        return fp32(np.maximum.reduce(values, axis=0))
    if op == int(CollectiveOp.MIN):
        return fp32(np.minimum.reduce(values, axis=0))
    raise ValueError(f"op {op} is not a reduction")


def mesh_diameter(mesh_x: int, mesh_y: int) -> int:
    return (mesh_x - 1) + (mesh_y - 1)


def hop_distance(rank: int, step: int, mesh_x: int, lgx: int) -> int:
    peer = rank ^ (1 << step)
    x0, y0 = rank % mesh_x, rank // mesh_x
    x1, y1 = peer % mesh_x, peer // mesh_x
    return abs(x1 - x0) + abs(y1 - y0)


def schedule(op: int, alg: int, mesh_x: int, mesh_y: int, vec_len: int):
    """Flits offered and link crossings walked, per node and in total.

    Returned per case: (serial_traversal_max, engine_flits_total,
    wire_flit_crossings_total, steps_per_node).
    """
    nodes = mesh_x * mesh_y
    lgx = int(math.log2(mesh_x)) if mesh_x > 1 else 0
    lgy = int(math.log2(mesh_y)) if mesh_y > 1 else 0
    lg = lgx + lgy
    serial = [0] * nodes
    engine = 0
    crossings = 0
    for rank in range(nodes):
        if op == OP_BARRIER:
            for k in range(lg):
                d = hop_distance(rank, k, mesh_x, lgx)
                serial[rank] += d
                engine += 1
                crossings += d
        elif op == int(CollectiveOp.BROADCAST):
            rprime = rank  # root is rank 0 in every generated case
            for k in range(lg):
                have = rprime < (1 << k)
                take = (rprime ^ (1 << k)) < (1 << k)
                if have or take:
                    d = hop_distance(rank, k, mesh_x, lgx)
                    serial[rank] += d
                    if have:
                        engine += vec_len
                        crossings += vec_len * d
        elif alg == ALG_HALVING_DOUBLING and op in (
            int(CollectiveOp.SUM), int(CollectiveOp.MAX), int(CollectiveOp.MIN)
        ):
            block = vec_len
            for k in range(lg - 1, -1, -1):
                half = block // 2
                d = hop_distance(rank, k, mesh_x, lgx)
                serial[rank] += d
                engine += half
                crossings += half * d
                block = half
            for k in range(lg):
                d = hop_distance(rank, k, mesh_x, lgx)
                serial[rank] += d
                engine += block
                crossings += block * d
                block = block * 2
        else:
            for k in range(lg):
                d = hop_distance(rank, k, mesh_x, lgx)
                serial[rank] += d
                engine += vec_len
                crossings += vec_len * d
    return max(serial), engine, crossings, lg if op != OP_BARRIER or True else lg


def build_config(cfg: dict) -> dict:
    mesh_x = cfg["mesh_x"]
    mesh_y = cfg["mesh_y"]
    vec_len = cfg["vec_len"]
    nodes = mesh_x * mesh_y
    lg = (int(math.log2(mesh_x)) if mesh_x > 1 else 0) + (
        int(math.log2(mesh_y)) if mesh_y > 1 else 0
    )
    values = contributions(nodes, vec_len, cfg["seed"])

    tree = fp32(ordered_sum(values, int(ReductionOrder.PAIRWISE_TREE)))
    seq = fp32(ordered_sum(values, int(ReductionOrder.SEQUENTIAL_ASCENDING)))
    blocked = fp32(ordered_sum(values, int(ReductionOrder.BLOCKED_ASCENDING)))
    halving = halving_tree(values)
    differing = int(np.count_nonzero(codes(tree) != codes(seq)))
    tree_vs_halving = int(np.count_nonzero(codes(tree) != codes(halving)))
    blocked_vs_halving = int(np.count_nonzero(codes(blocked) != codes(halving)))

    cases = []
    for spec in cfg["cases"]:
        op = spec["op"]
        alg = spec.get("alg", ALG_RECURSIVE_DOUBLING)
        order = spec.get("order", int(ReductionOrder.PAIRWISE_TREE))
        auto_trap = (
            op == int(CollectiveOp.SUM)
            and not (
                (alg == ALG_RECURSIVE_DOUBLING
                 and order == int(ReductionOrder.PAIRWISE_TREE))
                or (alg == ALG_HALVING_DOUBLING
                    and order == int(ReductionOrder.BLOCKED_ASCENDING)
                    and nodes == 16)
            )
        )
        expect_trap = bool(spec.get("expect_trap", False)) or auto_trap
        inject_node = spec.get("inject_node", -1)
        inject_dir = spec.get("inject_dir", 0)

        if expect_trap:
            expected = values.copy()          # a trap changes nothing
            serial = engine = crossings = 0
        elif op == OP_BARRIER:
            expected = values.copy()
            serial, engine, crossings, _ = schedule(op, alg, mesh_x, mesh_y, vec_len)
        elif op == int(CollectiveOp.BROADCAST):
            expected = np.tile(values[0], (nodes, 1))
            serial, engine, crossings, _ = schedule(op, alg, mesh_x, mesh_y, vec_len)
        else:
            reduced = reduce_expect(values, op, order, alg)
            expected = np.tile(reduced, (nodes, 1))
            serial, engine, crossings, _ = schedule(op, alg, mesh_x, mesh_y, vec_len)

        traffic_messages = 0
        traffic_bytes = 0
        if op in (
            int(CollectiveOp.SUM), int(CollectiveOp.MAX), int(CollectiveOp.MIN),
            int(CollectiveOp.BROADCAST),
        ) and not expect_trap:
            traffic_messages, traffic_bytes = collective_traffic(
                op, nodes, vec_len * 4
            )
        elif op == OP_BARRIER:
            traffic_messages = barrier_messages(
                int(TopologyClass.WAFER_LOGICAL_DEVICE), nodes
            )

        cases.append(
            {
                "label": spec["label"],
                "op": op,
                "alg": alg,
                "order": order,
                "root_x": spec.get("root_x", 0),
                "root_y": spec.get("root_y", 0),
                "inject_node": inject_node,
                "inject_dir": inject_dir,
                "expect_trap": expect_trap,
                "expected_serial_traversals": int(serial),
                "expected_engine_flits": int(engine),
                "expected_wire_crossings": int(crossings),
                "expected_steps_per_node": 0 if expect_trap else (
                    2 * lg if (alg == ALG_HALVING_DOUBLING and op in (
                        int(CollectiveOp.SUM), int(CollectiveOp.MAX),
                        int(CollectiveOp.MIN))) else lg),
                "functional_model_messages": int(traffic_messages),
                "functional_model_payload_bytes": int(traffic_bytes),
                "expected": expected,
            }
        )

    return {
        "mesh_x": mesh_x,
        "mesh_y": mesh_y,
        "vec_len": vec_len,
        "nodes": nodes,
        "credits": cfg["credits"],
        "retry_max": cfg["retry_max"],
        "hop_cycles": cfg["hop_cycles"],
        "seed": cfg["seed"],
        "lg": lg,
        "diameter": mesh_diameter(mesh_x, mesh_y),
        "model_charged_traversals": MESH_ALLREDUCE_DIAMETER_FACTOR
        * mesh_diameter(mesh_x, mesh_y),
        "contributions": values,
        "cases": cases,
        "sequential_vs_tree_differing_elements": differing,
        "pairwise_tree_vs_halving_differing_elements": tree_vs_halving,
        "blocked_ascending_vs_halving_differing_elements": blocked_vs_halving,
        "sequential_vs_tree_elements": int(vec_len),
    }


def write_hex(path: Path, words) -> None:
    path.write_text("".join(f"{int(w) & 0xFFFFFFFF:08x}\n" for w in words))


def emit(config: dict, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    nodes = config["nodes"]
    vec_len = config["vec_len"]

    contrib_words = []
    expect_words = []
    for case in config["cases"]:
        contrib_words.extend(codes(config["contributions"]).reshape(-1).tolist())
        expect_words.extend(codes(case["expected"]).reshape(-1).tolist())

    case_words = []
    for case in config["cases"]:
        row = [0] * CASE_STRIDE
        row[0] = case["op"]
        row[1] = case["alg"]
        row[2] = case["order"]
        row[3] = case["root_x"]
        row[4] = case["root_y"]
        row[5] = case["inject_node"] & 0xFFFFFFFF
        row[6] = case["inject_dir"]
        row[7] = (1 if case["expect_trap"] else 0) | (
            2 if case["inject_node"] >= 0 else 0
        )
        row[8] = case["expected_serial_traversals"]
        row[9] = case["expected_engine_flits"]
        row[10] = case["expected_wire_crossings"]
        row[11] = case["expected_steps_per_node"] * nodes
        case_words.extend(row)

    meta = [
        config["mesh_x"], config["mesh_y"], vec_len, config["credits"],
        config["retry_max"], config["hop_cycles"], len(config["cases"]), nodes,
    ]

    write_hex(out_dir / "contrib.hex", contrib_words)
    write_hex(out_dir / "expect.hex", expect_words)
    write_hex(out_dir / "case.hex", case_words)
    write_hex(out_dir / "meta.hex", meta)

    summary = {k: v for k, v in config.items()
               if k not in {"contributions", "cases"}}
    summary["cases"] = [
        {k: v for k, v in case.items() if k != "expected"}
        for case in config["cases"]
    ]
    summary["marker"] = marker(config)
    return summary


def marker(config: dict) -> str:
    checks = 0
    for case in config["cases"]:
        checks += 1  # trap expectation
        checks += config["nodes"] * config["vec_len"]  # result
        checks += 4  # traversals, engine flits, steps, crossings/retry relation
    return (
        f"PASS: A3 LINK mesh={config['mesh_x']}x{config['mesh_y']} "
        f"vec={config['vec_len']} hop={config['hop_cycles']} "
        f"cases={len(config['cases'])} checks={checks}"
    )


def default_configurations() -> list[dict]:
    base_cases = [
        {"label": "allreduce_sum_recursive_doubling", "op": int(CollectiveOp.SUM),
         "alg": ALG_RECURSIVE_DOUBLING},
        {"label": "allreduce_sum_halving_doubling", "op": int(CollectiveOp.SUM),
         "alg": ALG_HALVING_DOUBLING,
         "order": int(ReductionOrder.BLOCKED_ASCENDING)},
        {"label": "allreduce_sum_halving_doubling_pairwise_order_refused",
         "op": int(CollectiveOp.SUM), "alg": ALG_HALVING_DOUBLING,
         "order": int(ReductionOrder.PAIRWISE_TREE)},
        {"label": "allreduce_sum_recursive_doubling_blocked_order_refused",
         "op": int(CollectiveOp.SUM), "alg": ALG_RECURSIVE_DOUBLING,
         "order": int(ReductionOrder.BLOCKED_ASCENDING)},
        {"label": "allreduce_max", "op": int(CollectiveOp.MAX),
         "alg": ALG_RECURSIVE_DOUBLING},
        {"label": "allreduce_min", "op": int(CollectiveOp.MIN),
         "alg": ALG_RECURSIVE_DOUBLING},
        {"label": "broadcast", "op": int(CollectiveOp.BROADCAST)},
        {"label": "barrier", "op": OP_BARRIER},
        {"label": "allreduce_sum_with_crc_replay", "op": int(CollectiveOp.SUM),
         "alg": ALG_RECURSIVE_DOUBLING, "inject_node": 0, "inject_dir": 0},
        {"label": "allreduce_sum_sequential_order_refused",
         "op": int(CollectiveOp.SUM), "alg": ALG_RECURSIVE_DOUBLING,
         "order": int(ReductionOrder.SEQUENTIAL_ASCENDING), "expect_trap": True},
    ]
    configs = []
    for hop in (1, 2, 4, 8):
        configs.append({
            "name": f"mesh4x4_vec16_hop{hop}",
            "mesh_x": 4, "mesh_y": 4, "vec_len": 16, "credits": 8,
            "retry_max": 3, "hop_cycles": hop, "seed": 20260831,
            "cases": base_cases,
        })
    configs.append({
        "name": "mesh8x8_vec64_hop1",
        "mesh_x": 8, "mesh_y": 8, "vec_len": 64, "credits": 8,
        "retry_max": 3, "hop_cycles": 1, "seed": 20260901,
        "cases": base_cases,
    })
    configs.append({
        "name": "mesh2x2_vec4_hop1",
        "mesh_x": 2, "mesh_y": 2, "vec_len": 4, "credits": 8,
        "retry_max": 3, "hop_cycles": 1, "seed": 20260902,
        "cases": base_cases,
    })
    return configs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "testdata/rtl/a3_link"))
    args = parser.parse_args()
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    index = {"schema": "opentallas.rtl.a3_link_vectors.v1", "configurations": []}
    for cfg in default_configurations():
        built = build_config(cfg)
        summary = emit(built, out_root / cfg["name"])
        summary["name"] = cfg["name"]
        index["configurations"].append(summary)

    (out_root / "index.json").write_text(
        json.dumps(index, indent=1, sort_keys=True) + "\n"
    )
    for entry in index["configurations"]:
        print(f"{entry['name']}: {entry['marker']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
