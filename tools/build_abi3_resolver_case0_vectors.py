#!/usr/bin/env python3
"""Extract the shipped case-0 view-resolution stimulus for a targeted bench.

``tools/rtl_abi3_deployment_campaign.py`` measures the whole control plane on
the four shipped deployments.  Its case 0 is Qwen3-8B on ROM, prefill, sixteen
prompt tokens.  This tool replays exactly that case on the golden device
(``runtime.sim.device.Device``, the normative reference) and writes out, per
issued OPERATOR instruction, everything ``ot_a3_resolver_bank`` needs and
nothing else:

  * the OPERATOR payload's six operand view IDs, in slot order, NO_ID included;
  * the TENSOR_VIEW descriptor records those IDs name, verbatim -- the first
    192 bytes of the record, which is the 1,536-bit prefix the RTL descriptor
    store presents;
  * the loop stack as the sequencer's ``ot_a3_loop_stack`` would be holding it
    at that instruction: for each open loop, its LOOP_CONTROL descriptor ID,
    its induction value, and the three amendment-A13 fields the stack caches
    at LOOP_SETUP (bound kind is RUNTIME_SYMBOL *and* this request bound that
    symbol; max(bound_divisor, 1); the bound symbol's value);
  * the request's symbol file: sixteen 64-bit values and a bound mask.

The loop bindings are the device's own, taken from its trace at that
instruction (``entry["loops"]``), not recomputed here.  The A13 fields are read
off the LOOP_CONTROL descriptor with the same three rules
``ot_a3_loop_stack`` applies, and that transcription is the one thing in this
file that could be wrong; ``rtl/test/tb_a3_resolver_case0.sv`` therefore also
checks the resolved extents, axes, offsets and ranks against the golden
resolver's own answers, which are carried in this vector set for that purpose.
A stimulus that produced different views from the golden model would fail
there rather than quietly mis-measure.

The output is stimulus only.  It is written outside the repository by default
because it is large and derived; pass ``--out-dir``.

  python3 tools/build_abi3_resolver_case0_vectors.py --out-dir DIR
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.build_abi3_deployment_rtl_vectors as base  # noqa: E402

from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.constants import NO_ID  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import (  # noqa: E402
    ExtendedDescriptorType,
    SelectorKind,
)
from runtime.driver import GenerationDriver  # noqa: E402
from runtime.sim.device import Device  # noqa: E402

DESCRIPTOR_PREFIX_BYTES = 192
LOOP_DEPTH = 4          # ot_a3_pkg::A3_LOOP_DEPTH
SYMBOL_COUNT = 16       # ot_a3_pkg::A3_SYMBOL_COUNT
LOOP_WORDS = 5          # id, value, symbolic, divisor, bound value
VIEW_STRIDE = 5         # slot answer: extent, axis, rank, offset lo, offset hi
TXN_WORDS = 6 + LOOP_DEPTH * LOOP_WORDS + 6 * VIEW_STRIDE

VECTORS_JSON = ROOT / "testdata/compiler/abi3_deployment/abi3_deployment_rtl_vectors.json"


def loop_state(
    device: Device, loops: dict[int, int], symbols: dict[int, int]
) -> list[tuple[int, int, int, int, int]]:
    """The open loops as ot_a3_loop_stack caches them at LOOP_SETUP.

    Three rules, transcribed from rtl/abi3/ot_a3_loop_stack.sv:
      symbolic = (bound_selector_kind == RUNTIME_SYMBOL) && symbol is bound
      divisor  = bound_divisor == 0 ? 1 : bound_divisor
      bound    = the bound symbol's value, low 32 bits
    """
    rows: list[tuple[int, int, int, int, int]] = []
    for loop_id, value in loops.items():
        control = device.deployment.table.get(
            loop_id, ExtendedDescriptorType.LOOP_CONTROL
        )
        payload = control.payload
        symbol_id = int(payload["bound_symbol_id"])
        bound_value = symbols.get(symbol_id)
        symbolic = (
            int(payload["bound_selector_kind"]) == int(SelectorKind.RUNTIME_SYMBOL)
            and bound_value is not None
        )
        divisor = int(payload["bound_divisor"]) or 1
        rows.append(
            (
                int(loop_id) & 0xFFFFFFFF,
                int(value) & 0xFFFFFFFF,
                1 if symbolic else 0,
                divisor & 0xFFFFFFFF,
                int(bound_value or 0) & 0xFFFFFFFF,
            )
        )
    if len(rows) > LOOP_DEPTH:
        raise SystemExit(
            f"{len(rows)} loops are open at one instruction; the stack is "
            f"{LOOP_DEPTH} deep"
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument(
        "--deployment",
        type=Path,
        default=None,
        help="deployment bundle directory (default: the case-0 target's)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="root the deployment's object segments resolve against",
    )
    args = parser.parse_args()

    target = base.TARGETS[0]
    assert target.key == "qwen3-8b-rom-single-chip", target.key
    directory = args.deployment or (ROOT / target.deployment)

    recorded = json.loads(VECTORS_JSON.read_text(encoding="utf-8"))
    case0 = recorded["cases"][0]
    if case0["name"] != "qwen3-8b-rom-single-chip/prefill":
        raise SystemExit(f"case 0 is {case0['name']!r}, not the ROM prefill case")

    base.install_engine_stubs()
    deployment = Deployment.read(directory)
    digest = deployment.deployment_digest.hex()
    if digest != case0["deployment_sha256"]:
        raise SystemExit(
            f"deployment digest {digest} is not case 0's "
            f"{case0['deployment_sha256']}"
        )
    capability = Capability.from_dict(
        json.loads((ROOT / target.capability).read_text(encoding="utf-8"))
    )

    prompt_tokens = int(recorded["prompt_tokens"])
    request = base.requests(prompt_tokens)[0]
    if request.entrypoint_id != case0["entrypoint_id"]:
        raise SystemExit("case 0 is not entrypoint 0")

    device = Device(
        deployment, capability, verify=False, trace=True,
        root=args.root or ROOT,
    )
    driver = GenerationDriver(device)
    symbols = base.effective_symbols(driver, device, request)
    golden = base.run_golden(device, driver, request)
    if not golden["complete"]:
        raise SystemExit("case 0 did not run to completion on the golden device")

    # The golden per-view answers, in the order the golden model produced them:
    # trace order, and within one instruction, slot order.  A program index is
    # NOT a key -- case 0 issues 74 instructions 691 times -- so this is walked
    # as a queue beside the same trace, and the walk is checked to consume it
    # exactly.
    answers = list(golden["views"])
    answer_cursor = 0

    # -- descriptor store: only the views case 0 names, densely re-indexed ---
    table = deployment.table
    dense: dict[int, int] = {}
    records: list[bytes] = []

    def intern(view_id: int) -> int:
        if view_id not in dense:
            record = table._records[view_id]  # noqa: SLF001
            prefix = record[:DESCRIPTOR_PREFIX_BYTES]
            prefix = prefix + bytes(DESCRIPTOR_PREFIX_BYTES - len(prefix))
            dense[view_id] = len(records)
            records.append(prefix)
        return dense[view_id]

    txns: list[list[int]] = []
    operand_fields = base.OPERAND_FIELDS
    for entry in device.trace:
        instruction = device.instructions[entry["pc"]]
        if (
            base.FAMILY_DESCRIPTOR.get(instruction.major)
            is not ExtendedDescriptorType.OPERATOR
        ):
            continue
        operator = table.get(
            instruction.descriptor_id, ExtendedDescriptorType.OPERATOR
        )
        words: list[int] = []
        slots: list[int] = []
        for field in operand_fields:
            view_id = int(operator.payload[field])
            slots.append(view_id)
            words.append(
                0xFFFFFFFF if view_id == NO_ID else intern(view_id)
            )
        rows = loop_state(device, entry["loops"], symbols)
        for index in range(LOOP_DEPTH):
            if index < len(rows):
                words.extend(rows[index])
            else:
                # An unused slot must never match a query: NO_ID is not a
                # LOOP_CONTROL descriptor ID, so it cannot collide.
                words.extend([0xFFFFFFFF, 0, 0, 1, 0])
        for slot, view_id in enumerate(slots):
            if view_id == NO_ID:
                words.extend([0, 0, 0, 0, 0])
                continue
            answer = answers[answer_cursor]
            answer_cursor += 1
            if (
                int(answer["index"]) != int(entry["pc"])
                or int(answer["slot"]) != slot
                or int(answer["descriptor_id"]) != view_id
            ):
                raise SystemExit(
                    f"golden view {answer_cursor - 1} is "
                    f"(pc {answer['index']}, slot {answer['slot']}, view "
                    f"{answer['descriptor_id']}), this walk is at "
                    f"(pc {entry['pc']}, slot {slot}, view {view_id})"
                )
            offset = int(answer["element_offset"])
            words.extend(
                [
                    int(answer["extent"]) & 0xFFFFFFFF,
                    int(answer["extent_axis"]) & 0xFF,
                    int(answer["rank"]) & 0xFF,
                    offset & 0xFFFFFFFF,
                    (offset >> 32) & 0xFFFFFFFF,
                ]
            )
        assert len(words) == TXN_WORDS, (len(words), TXN_WORDS)
        txns.append(words)

    if len(txns) != case0["issue_count"]:
        # Not every issue is an OPERATOR in general; case 0 happens to be all
        # OPERATOR, and the header note in ot_a3_resolver_bank.sv says 691.
        print(
            f"note: {len(txns)} OPERATOR issues of {case0['issue_count']} issues"
        )
    if answer_cursor != len(answers):
        raise SystemExit(
            f"{answer_cursor} of {len(answers)} golden views were consumed"
        )
    view_total = sum(
        1 for words in txns for word in words[:6] if word != 0xFFFFFFFF
    )
    if view_total != case0["view_count"]:
        raise SystemExit(
            f"{view_total} operand views, case 0 recorded {case0['view_count']}"
        )

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "resolver_case0_desc.hex").write_text(
        "".join(
            f"{int.from_bytes(record, 'little'):0{DESCRIPTOR_PREFIX_BYTES * 2}x}\n"
            for record in records
        ),
        encoding="utf-8",
    )
    (out / "resolver_case0_txn.hex").write_text(
        "".join(f"{word:08x}\n" for words in txns for word in words),
        encoding="utf-8",
    )
    symbol_words: list[int] = []
    mask = 0
    for index in range(SYMBOL_COUNT):
        value = symbols.get(index)
        if value is None:
            symbol_words.extend([0, 0])
            continue
        mask |= 1 << index
        symbol_words.append(int(value) & 0xFFFFFFFF)
        symbol_words.append((int(value) >> 32) & 0xFFFFFFFF)
    symbol_words.append(mask)
    (out / "resolver_case0_sym.hex").write_text(
        "".join(f"{word:08x}\n" for word in symbol_words), encoding="utf-8"
    )
    manifest: dict[str, Any] = {
        "case": case0["name"],
        "deployment_sha256": digest,
        "prompt_tokens": prompt_tokens,
        "transactions": len(txns),
        "operand_views": view_total,
        "descriptors": len(records),
        "txn_words": TXN_WORDS,
        "loop_depth": LOOP_DEPTH,
        "symbol_count": SYMBOL_COUNT,
    }
    (out / "resolver_case0_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
