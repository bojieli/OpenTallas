#!/usr/bin/env python3
"""Build ABI 3.0 RTL correlation vectors from the deployments this program ships.

``tools/build_abi3_rtl_vectors.py`` builds 65 vectors that are *real* ABI 3.0
programs but are written for the campaign: each one is constructed to reach a
particular corner of the sequencer.  None of them is a program this project
claims to run.  This generator closes that gap by taking the four shipped
deployments themselves --

    Qwen3-8B ROM single chip        92535108...  75 instructions, 239 descriptors
    Qwen3-8B HBM single chip        8e1185ea...  75 instructions, 218 descriptors
    DeepSeek-V4-Flash ROM wafer     fa907792...  1171 instructions, 3403 descriptors
    DeepSeek-V4-Flash HBM cluster   2943197b...  1146 instructions, 2953 descriptors

-- and emitting, for each of them, the same four memory images the RTL
verification top already reads (the 256-byte program header, the 32-byte
instruction records, the descriptor records and the request-bound runtime
symbols) together with the golden control-plane observation
``runtime.sim.device.Device`` produces for the same request.

Nothing is transcribed.  The deployment is read from its build directory with
``runtime.abi3.deployment.Deployment.read``; its digest is checked against the
digest this repository ships, so a rebuilt or edited deployment is refused
rather than silently correlated; the runtime symbols a request does not carry
come from ``runtime.driver.GenerationDriver``, which is the code the service
uses; and every expected number comes from executing the program.

Depth.  Each deployment is run to its own COMPLETE, not to a chosen prefix
length: at a sixteen-token prompt the whole transaction fits in the declared
``max_retired_work`` on both entrypoints, so the bounded prefix is the whole
program.  ``--max-retired-work`` is available to bound a request that does not
fit -- it lowers the work bound on *both* sides, the RTL's ``cfg`` input and the
golden device's header field, so both trap at the same retirement -- and the
vector set records, per case, whether it was used.  It was not needed for any
case here and the artifact says so per case rather than in prose.

Engine datapaths stay out of scope, exactly as in the microsequencer vector
set: every dispatchable engine operation is bound to a recording no-op, so what
is correlated is the instruction stream, the issue order, the descriptor IDs
and the resolved operand views -- the control plane -- and not the arithmetic.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.constants import (  # noqa: E402
    Control,
    Major,
    NO_ID,
    SUBOPCODES,
)
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import (  # noqa: E402
    ExtendedDescriptorType,
    Phase,
    Symbol,
)
from runtime.abi3.records import decode_body, split_program  # noqa: E402
from runtime.abi3.verifier import (  # noqa: E402
    _FAMILY_DESCRIPTOR as FAMILY_DESCRIPTOR,
    verify_deployment,
)
from runtime.driver import GenerationDriver  # noqa: E402
from runtime.sim import engine as engine_module  # noqa: E402
from runtime.sim.device import Device  # noqa: E402

OUTPUT_DIR = ROOT / "testdata/compiler/abi3_deployment"

# The RTL verification top this campaign drives is the shared
# rtl/test/a3_microsequencer_top.sv module.  The deployment campaign overrides
# only its memory geometry so all four shipped images fit; the module's defaults
# and the production RTL geometry remain unchanged.  Every image below is
# padded to these deployment-only bounds so the DUT reads fully initialised
# memory.  A deployment that does not fit is refused rather than quietly
# truncated.
PROGRAM_WORDS = 4096      # 256-bit instruction records
HEADER_WORDS = 8192       # 32-bit words, 64 per deployment
DESC_WORDS = 8192         # 1536-bit descriptor prefixes
SYMBOL_WORDS = 2048       # 32-bit words, 16 per case
DESCRIPTOR_PREFIX_BYTES = 192

CASE_STRIDE = 38
# Checker-side array sizes, transcribed in rtl/test/tb_a3_deployment.sv and
# rtl/test/a3_deployment_harness.cpp.
CASE_MEM_WORDS = 512
ISSUE_MEM_WORDS = 131072
VIEW_MEM_WORDS = 1048576
SYMBOL_STRIDE = 16
HEADER_STRIDE = 64
ISSUE_STRIDE = 3          # opcode, descriptor ID, instruction index
VIEW_STRIDE = 7
META_WORDS = 8

# OPERATOR operand slots in the order the golden model and the RTL both walk
# them (runtime/abi3/descriptors.OPERATOR_PAYLOAD).
OPERAND_FIELDS = (
    "input_view_0",
    "input_view_1",
    "input_view_2",
    "input_view_3",
    "output_view_0",
    "output_view_1",
)


# ---------------------------------------------------------------------------
# The deployments, and the digests that say which ones they are
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Target:
    key: str
    title: str
    deployment: str
    capability: str
    checkpoint: str
    digest: str
    reproduce: str


TARGETS = (
    Target(
        key="qwen3-8b-rom-single-chip",
        title="Qwen3-8B ROM single chip",
        deployment="build/abi3/qwen3-8b-rom",
        capability="configs/hardware/abi3_capability/rom_qwen3.json",
        checkpoint=(
            "~/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
            "b968826d9c46dd6066d109eabc6255188de91218"
        ),
        digest="925351080448450ee4b14a0e3260001dbac9aeafc582fd3202d53a0a379b9c91",
        reproduce="make abi3-rom-qwen-build",
    ),
    Target(
        key="qwen3-8b-hbm-single-chip",
        title="Qwen3-8B HBM single chip",
        deployment="build/abi3/qwen3-8b-hbm-tokens",
        capability="configs/hardware/abi3_capability/hbm_sram_single_chip.json",
        checkpoint=(
            "~/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
            "b968826d9c46dd6066d109eabc6255188de91218"
        ),
        digest="8e1185ea1aef360efcdb101379fc40e22658bfd81edd970dc8cfdd29c6c8ff0c",
        reproduce=(
            "python3 tools/build_hbm_sram_deployment.py --ir "
            "build/ir-v3/qwen3-8b/kernel_ir.v3.json --profile single-chip "
            "--out build/abi3/qwen3-8b-hbm-tokens"
        ),
    ),
    Target(
        key="deepseek-v4-flash-rom-wafer",
        title="DeepSeek-V4-Flash ROM wafer",
        deployment="build/abi3/deepseek-v4-flash-rom",
        capability="configs/hardware/abi3_capability/rom_deepseek_v4.json",
        checkpoint=(
            "~/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Flash-0731/"
            "snapshots/7872f01b1d1fe23eabc4c98b48bffcef5a386062"
        ),
        digest="fa907792d8eb73ec1237525468581e47945a9077e5a247f4f88c43fbb5042394",
        reproduce="make abi3-rom-deepseek-build",
    ),
    Target(
        key="deepseek-v4-flash-hbm-cluster",
        title="DeepSeek-V4-Flash HBM 32-node cluster",
        deployment="build/abi3/deepseek-v4-flash-hbm-tokens",
        capability="configs/hardware/abi3_capability/hbm_sram_cluster_32.json",
        checkpoint=(
            "~/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Flash-0731/"
            "snapshots/7872f01b1d1fe23eabc4c98b48bffcef5a386062"
        ),
        digest="2943197b3055d6198899d402efd927810cd307c09287f9d250b1b1afb2695275",
        reproduce=(
            "python3 tools/build_hbm_sram_deployment.py --ir "
            "build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json "
            "--profile cluster-32 --out "
            "build/abi3/deepseek-v4-flash-hbm-tokens"
        ),
    ),
)


RTL_PACKAGE = ROOT / "rtl/abi3/ot_a3_pkg.sv"

# The implementation bounds the RTL package declares, and what in a deployment
# each one bounds.  These are read out of the RTL source rather than restated
# here, because a bound restated in two places is a bound that will disagree
# with itself.
BOUND_PARAMETERS = (
    "A3_LOOP_DEPTH",
    "A3_STATE_SLOTS",
    "A3_EVENT_COUNT",
    "A3_WAIT_PRODUCERS",
)

# What in a capability or in the frozen ABI expresses each bound.  A bound with
# no capability field cannot be refused at admission, which is why a program
# that exceeds it reaches the RTL and traps there; amendments A22 and A23
# closed the two that had none, so every entry below now names something a
# deployment is admitted against.
BOUND_CAPABILITY_FIELD = {
    "A3_LOOP_DEPTH": (
        "limits.max_loop_depth -- expressible, and runtime.abi3.verifier "
        "checks it"
    ),
    "A3_STATE_SLOTS": (
        "limits.max_state_resources (amendment A22) -- runtime.abi3.verifier "
        "check state_resource_bound and tools/check_abi3_deployment.py refuse "
        "a deployment declaring more STATE descriptors than the capability "
        "holds slots for. Before A22 no capability field named a state-slot "
        "count at all, so no deployment could be refused for exceeding it and "
        "the overrun was discovered here as trap class 4"
    ),
    "A3_EVENT_COUNT": (
        "limits.max_event_id + 1 (amendment A23) -- runtime.abi3.verifier "
        "check event_id_bound and tools/check_abi3_deployment.py refuse a "
        "program naming an event ID above the capability's space. Before A23 "
        "this parameter was labelled limits.max_events, which bounds the "
        "*number of distinct event IDs* a program signals; a scoreboard "
        "indexed by event ID is bounded by the largest ID plus one, and the "
        "two coincide only when IDs are dense from zero. The four shipped "
        "capabilities now agree with this parameter and with each other, "
        "because it is storage in the shared microsequencer"
    ),
    "A3_WAIT_PRODUCERS": (
        "runtime.abi3.descriptors.MAX_WAIT_PRODUCERS, a frozen ABI constant "
        "the wait-set payload is sized by; the two agree at 12"
    ),
}
BOUND_RE = re.compile(
    r"localparam\s+integer\s+(A3_[A-Z_]+)\s*=\s*(\d+)\s*;"
)


def rtl_bounds() -> dict[str, int]:
    """The sequencer's own implementation bounds, read from its package.

    ``rtl/abi3/ot_a3_pkg.sv`` calls these "implementation bounds (capability
    fields, not ABI)".  That is exactly right, and it is the point: a capability
    field is checked by ``runtime.abi3.verifier`` at admission, so a program
    that exceeds it is *refused*.  These four are not in any capability this
    repository ships, so nothing refuses a program that exceeds them and the
    RTL discovers it at run time instead.  Reading them here makes the overrun
    a computed fact in the vector set rather than something only a long
    simulation reveals.
    """
    text = RTL_PACKAGE.read_text(encoding="utf-8")
    found = {name: int(value) for name, value in BOUND_RE.findall(text)}
    missing = [name for name in BOUND_PARAMETERS if name not in found]
    if missing:
        raise SystemExit(
            f"{RTL_PACKAGE} no longer declares {missing}; this campaign reads "
            "the RTL's bounds from the RTL rather than restating them"
        )
    return {name: found[name] for name in BOUND_PARAMETERS}


def deployment_demands(deployment: Deployment) -> dict[str, int]:
    """What this deployment asks of each bound the RTL package declares."""
    header, body = split_program(deployment.program)
    instructions = decode_body(body)
    events = {
        int(i.signal_event_id)
        for i in instructions
        if int(i.signal_event_id) != NO_ID
    }
    for wait_id in {
        int(i.wait_set_id) for i in instructions if int(i.wait_set_id) != NO_ID
    }:
        payload = deployment.table.get(
            wait_id, ExtendedDescriptorType.EVENT_WAIT_SET
        ).payload
        for slot in range(int(payload["producer_count"])):
            events.add(int(payload[f"producer_{slot}"]))
    producers = [0]
    for wait_id in deployment.table.ids_of_type(
        ExtendedDescriptorType.EVENT_WAIT_SET
    ):
        payload = deployment.table.get(
            wait_id, ExtendedDescriptorType.EVENT_WAIT_SET
        ).payload
        producers.append(int(payload["producer_count"]))
    depth = 0
    deepest = 0
    for instruction in instructions:
        if int(instruction.major) != int(Major.CONTROL):
            continue
        if int(instruction.sub) == int(Control.LOOP_SETUP):
            depth += 1
            deepest = max(deepest, depth)
        elif int(instruction.sub) == int(Control.LOOP_NEXT):
            depth = max(0, depth - 1)
    return {
        "A3_LOOP_DEPTH": deepest,
        "A3_STATE_SLOTS": len(
            deployment.table.ids_of_type(ExtendedDescriptorType.STATE)
        ),
        # A scoreboard indexed by event ID needs one bit per *ID*, so the bound
        # is the largest ID plus one, not the number of distinct events.
        "A3_EVENT_COUNT": (max(events) + 1) if events else 0,
        "A3_WAIT_PRODUCERS": max(producers),
    }


def bound_overruns(
    bounds: dict[str, int], demands: dict[str, int]
) -> list[dict[str, Any]]:
    """Every RTL bound this deployment exceeds, with both numbers."""
    return [
        {
            "parameter": name,
            "rtl_bound": bounds[name],
            "deployment_requires": demands[name],
            "declared_in": "rtl/abi3/ot_a3_pkg.sv",
            "expressed_by": BOUND_CAPABILITY_FIELD[name],
        }
        for name in BOUND_PARAMETERS
        if demands[name] > bounds[name]
    ]


def checkpoint_root(target: "Target", override: Path | None) -> Path:
    """Where the deployment's object segments are read from.

    Engine datapaths are no-ops, but activation still authenticates every
    declared mapped range before an instruction can observe it.  The files a
    MEMORY_OBJECT names therefore have to exist, be large enough, and contain
    the bytes whose SHA-256 the deployment binds.  Refusing a missing root here,
    with the path in the message, is better than a MemoryError four frames deep.
    """
    if override is not None:
        return override
    pattern = str(Path(target.checkpoint).expanduser())
    matches = sorted(glob.glob(pattern))
    if not matches:
        raise SystemExit(
            f"{target.key}: no checkpoint at {pattern}; the deployment's "
            "memory objects are file-backed and activation must authenticate "
            "their declared ranges"
        )
    return Path(matches[0])


# ---------------------------------------------------------------------------
# Recording engine stubs -- identical policy to the microsequencer vector set
# ---------------------------------------------------------------------------
def install_engine_stubs() -> None:
    """Force every dispatchable engine operation to a recording no-op.

    This is the same policy, and for the same reason, as
    ``tools/build_abi3_rtl_vectors.py``: RTL 3.0 implements the control plane,
    so a golden model that *did* compute would trap on data the RTL never sees
    and the comparison would not be well posed.  Binding every dispatchable
    ``(family, subopcode)`` to a no-op makes the two sides differ in nothing but
    the datapath neither is exercising.  No checkpoint byte reaches an engine;
    Device activation still reads every mapped range once to authenticate its
    declared digest.

    ``runtime.sim.engine.register`` refuses to replace an existing
    implementation, so the binding is written directly; the result does not
    depend on whether the engine package was imported first, which is the
    property that keeps the vector set reproducible.
    """

    def _noop(ctx, sub, descriptor):  # noqa: ANN001 - engine handler signature
        return None

    dispatchable = (
        Major.DMA,
        Major.TENSOR,
        Major.VECTOR,
        Major.ATTENTION,
        Major.ROUTE,
        Major.REDUCTION,
        Major.SELECTION,
        Major.LINK,
    )
    for family in dispatchable:
        for member in SUBOPCODES[family]:
            engine_module._REGISTRY[(int(family), int(member))] = _noop  # noqa: SLF001


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Request:
    """One transaction: an entrypoint and the request-bound symbols."""

    name: str
    entrypoint_id: int
    phase: Phase
    prompt_tokens: int
    position: int

    def symbols(self) -> dict[int, int]:
        """The request half of the symbol table.

        These are the same bindings ``runtime.driver.GenerationDriver`` writes
        for a prefill and for a decode step; the deployment half comes from the
        driver itself so that nothing here decides what a program's
        ``LAYER_COUNT`` or ``ACTIVE_EXPERT_COUNT`` is.
        """
        if self.phase is Phase.PREFILL:
            span = self.prompt_tokens
            return {
                int(Symbol.SPAN_TOKENS): span,
                int(Symbol.POSITION_START): 0,
                int(Symbol.POSITION_END): span,
                int(Symbol.CONTEXT_LENGTH): span,
                int(Symbol.PHASE): int(Phase.PREFILL),
                int(Symbol.MAX_NEW_TOKENS): 1,
                int(Symbol.BATCH): 1,
                int(Symbol.GENERATION_INDEX): 0,
                int(Symbol.SPAN_LAST_INDEX): span - 1,
            }
        return {
            int(Symbol.SPAN_TOKENS): 1,
            int(Symbol.POSITION_START): self.position,
            int(Symbol.POSITION_END): self.position + 1,
            int(Symbol.CONTEXT_LENGTH): self.position + 1,
            int(Symbol.PHASE): int(Phase.DECODE),
            int(Symbol.MAX_NEW_TOKENS): 1,
            int(Symbol.BATCH): 1,
            int(Symbol.GENERATION_INDEX): 0,
            int(Symbol.SPAN_LAST_INDEX): 0,
        }


def requests(prompt_tokens: int) -> tuple[Request, ...]:
    return (
        Request("prefill", 0, Phase.PREFILL, prompt_tokens, 0),
        Request("decode", 1, Phase.DECODE, prompt_tokens, prompt_tokens),
    )


# ---------------------------------------------------------------------------
# Golden execution
# ---------------------------------------------------------------------------
def resolved_views(
    device: Device, entry: dict[str, Any], symbols: dict[int, int]
) -> list[dict[str, Any]]:
    """Every operand view of one issued instruction, resolved by the simulator.

    The extents and offsets come from ``runtime.sim.memory.ViewResolver.resolve``
    -- the device's own resolver -- evaluated against the loop bindings the
    device recorded in its trace at exactly this instruction.  Nothing here
    recomputes them; a hand-computed extent would prove only that this file and
    the RTL agree with each other.
    """
    instruction = device.instructions[entry["pc"]]
    if FAMILY_DESCRIPTOR.get(instruction.major) != ExtendedDescriptorType.OPERATOR:
        return []
    operator = device.deployment.table.get(
        instruction.descriptor_id, ExtendedDescriptorType.OPERATOR
    )
    views: list[dict[str, Any]] = []
    for slot, field in enumerate(OPERAND_FIELDS):
        view_id = int(operator.payload[field])
        if view_id == NO_ID:
            continue
        resolved = device.views.resolve(view_id, entry["loops"], symbols)
        views.append({
            "index": int(entry["pc"]),
            "slot": slot,
            "descriptor_id": view_id,
            "extent_axis": int(resolved.extent_axis),
            "extent": int(resolved.dims[int(resolved.extent_axis)]),
            "element_offset": int(resolved.element_offset),
            "rank": len(resolved.dims),
        })
    return views


def effective_symbols(
    driver: GenerationDriver, device: Device, request: Request
) -> dict[int, int]:
    """The symbol bindings the golden device actually sees.

    ``Device.run_transaction`` supplies four of them itself -- the phase and
    generation-index defaults, and the node dimension -- so the image the RTL
    reads has to be the union, not just what the caller passed.
    """
    symbols = {**driver.deployment_symbols, **request.symbols()}
    symbols.setdefault(int(Symbol.PHASE), int(request.phase))
    symbols.setdefault(int(Symbol.GENERATION_INDEX), 0)
    symbols[int(Symbol.NODE_COUNT)] = int(device.node_count)
    symbols[int(Symbol.NODE_ID)] = 0
    return symbols


def run_golden(
    device: Device, driver: GenerationDriver, request: Request
) -> dict[str, Any]:
    """Execute one request on the golden device and return the observation."""
    session = device.create_session()
    mark = len(device.trace)
    symbols = effective_symbols(driver, device, request)
    result = device.run_transaction(
        session,
        entrypoint_id=request.entrypoint_id,
        symbols={**driver.deployment_symbols, **request.symbols()},
    )
    trace = device.trace[mark:]
    counters = result.counters
    cluster_state_rows = int(counters.get("state.rows_committed", 0))
    if cluster_state_rows % max(int(device.node_count), 1):
        raise SystemExit(
            f"state.rows_committed={cluster_state_rows} is not symmetric over "
            f"the deployment's {device.node_count} nodes"
        )
    issues: list[dict[str, Any]] = []
    views: list[dict[str, Any]] = []
    for entry in trace:
        instruction = device.instructions[entry["pc"]]
        issues.append({
            "index": int(entry["pc"]),
            "family": int(instruction.major),
            "sub": int(instruction.sub),
            "descriptor_id": int(instruction.descriptor_id),
        })
        views.extend(resolved_views(device, entry, symbols))
    success = result.status == 0
    return {
        "status": int(result.status),
        "trap_class": int(result.trap_class),
        "first_fault": int(result.first_fault_instruction),
        "complete": bool(success),
        "fetched": int(result.fetched),
        "retired": int(result.retired),
        "predicated_off": int(result.predicated_off),
        "issued": int(counters.get("instructions.issued", 0)),
        "loop_iterations": int(counters.get("control.loop_iterations", 0)),
        "branches": int(counters.get("control.branches_taken", 0)),
        "wait_events": int(counters.get("queue.wait_events", 0)),
        "state_prepares": int(counters.get("state.prepares", 0)),
        "state_commits": int(counters.get("state.commits", 0)),
        "state_discards": int(counters.get("state.discards", 0)),
        "state_reads": int(counters.get("state.reads", 0)),
        "state_generation_advances": int(
            counters.get("state.generation_advances", 0)
        ),
        "state_commits_applied": (
            int(counters.get("state.commits", 0)) if success else 0
        ),
        # One verification top is one sequencer/node instance.  Device reports
        # state bytes/rows as cluster totals because a commit copies the same
        # run into every node-local state image.  Compare RTL with the exact
        # per-node run; retain the cluster total beside it so the scope cannot
        # be mistaken or silently divided by a later consumer.
        "state_rows_committed": cluster_state_rows // max(device.node_count, 1),
        "state_rows_committed_cluster_total": cluster_state_rows,
        "state_row_scope": "per_node_symmetric_commit_run",
        "node_count": int(device.node_count),
        "message": result.message,
        "symbols": symbols,
        "issues": issues,
        "views": views,
        "counters": {k: int(v) for k, v in sorted(counters.items())},
    }


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------
def le_words(blob: bytes) -> list[int]:
    return [int.from_bytes(blob[i : i + 4], "little") for i in range(0, len(blob), 4)]


def hex_lines(values: list[int], width_bits: int, total: int | None = None) -> str:
    """Render one memory image.

    ``total`` pads the image to the size of the RTL memory it initialises, so
    the DUT never reads an uninitialised word.  The checker-side images (cases,
    issues, views, meta) are never read by the DUT and are emitted at their
    exact length; padding them would add megabytes of zeros to the repository
    for nothing.
    """
    if total is not None and len(values) > total:
        raise SystemExit(
            f"image overflow: {len(values)} words exceed the RTL memory's {total}"
        )
    digits = width_bits // 4
    padded = values if total is None else values + [0] * (total - len(values))
    return "".join(f"{value:0{digits}x}\n" for value in padded)


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--prompt-tokens",
        type=int,
        default=16,
        help=(
            "prompt length of the correlated request; 16 is what the ROM "
            "read-service vector set uses, so the two campaigns describe the "
            "same request"
        ),
    )
    parser.add_argument(
        "--max-retired-work",
        type=int,
        default=0,
        help=(
            "bound the co-simulated prefix at this many retired instructions "
            "on both sides; 0 means the deployment's own declared bound, which "
            "is what every case here runs under"
        ),
    )
    parser.add_argument(
        "--checkpoint-root",
        type=Path,
        default=None,
        help=(
            "override where every deployment's object segments are mapped "
            "from; the default is the authenticated checkpoint each "
            "deployment was built against"
        ),
    )
    parser.add_argument(
        "--allow-digest-drift",
        action="store_true",
        help=(
            "emit vectors for a deployment whose digest is not the one this "
            "repository ships (for bisecting a rebuild; never for evidence)"
        ),
    )
    args = parser.parse_args(argv)
    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    install_engine_stubs()
    bounds = rtl_bounds()
    overrun_summary: list[dict[str, Any]] = []

    program_words: list[int] = []
    header_words: list[int] = []
    desc_words: list[int] = []
    symbol_words: list[int] = []
    case_words: list[int] = []
    issue_words: list[int] = []
    view_words: list[int] = []
    records: list[dict[str, Any]] = []
    deployments: list[dict[str, Any]] = []

    for target_index, target in enumerate(TARGETS):
        directory = ROOT / target.deployment
        if not directory.exists():
            raise SystemExit(
                f"{target.key}: deployment is missing at {target.deployment}; "
                f"build it with:\n    {target.reproduce}"
            )
        deployment = Deployment.read(directory)
        actual = deployment.deployment_digest.hex()
        if actual != target.digest and not args.allow_digest_drift:
            raise SystemExit(
                f"{target.key}: deployment digest is {actual}, this campaign "
                f"correlates {target.digest}. The vector set names the program "
                "it ran; re-record rather than accepting a different one."
            )
        capability = Capability.from_dict(
            json.loads((ROOT / target.capability).read_text(encoding="utf-8"))
        )
        report = verify_deployment(deployment, capability)
        if not report.admitted:
            raise SystemExit(
                f"{target.key}: the ABI verifier refuses this deployment: "
                f"{report.errors}"
            )

        image = deployment.program
        header_blob = image[:256]
        body = image[256:]
        instruction_count = int.from_bytes(header_blob[16:20], "little")
        entrypoint_count = int.from_bytes(header_blob[20:24], "little")
        declared_work = int.from_bytes(header_blob[184:192], "little")

        program_base = len(program_words)
        for offset in range(0, len(body), 32):
            program_words.append(int.from_bytes(body[offset : offset + 32], "little"))
        header_base = len(header_words)
        header_words.extend(le_words(header_blob))

        desc_base = len(desc_words)
        table = deployment.table
        for index in range(len(table)):
            record = table._records[index]  # noqa: SLF001
            prefix = record[:DESCRIPTOR_PREFIX_BYTES]
            prefix = prefix + bytes(DESCRIPTOR_PREFIX_BYTES - len(prefix))
            desc_words.append(int.from_bytes(prefix, "little"))
        state_count = len(table.ids_of_type(ExtendedDescriptorType.STATE))

        demands = deployment_demands(deployment)
        overruns = bound_overruns(bounds, demands)
        for overrun in overruns:
            overrun_summary.append({"deployment": target.key, **overrun})

        deployments.append({
            "key": target.key,
            "title": target.title,
            "deployment_dir": target.deployment,
            "deployment_sha256": actual,
            "descriptor_table_sha256": hashlib.sha256(table.encode()).hexdigest(),
            "program_sha256": hashlib.sha256(image).hexdigest(),
            "target_id": deployment.target_id,
            "model_id": deployment.model_id,
            "instruction_count": instruction_count,
            "descriptor_count": len(table),
            "state_descriptor_count": state_count,
            "entrypoint_count": entrypoint_count,
            "declared_max_retired_work": declared_work,
            "capability": target.capability,
            "capability_digest": capability.digest,
            "admitted": report.admitted,
            "verifier_errors": list(report.errors),
            "rtl_bound_demands": demands,
            "rtl_bound_overruns": overruns,
            "co_simulable_within_rtl_bounds": not overruns,
            "reproduce": target.reproduce,
        })

        root = checkpoint_root(target, args.checkpoint_root)

        for request in requests(args.prompt_tokens):
            device = Device(
                deployment, capability, verify=False, trace=True, root=root
            )
            bounded = bool(args.max_retired_work) and args.max_retired_work < (
                device.header.max_retired_work
            )
            if bounded:
                # Lower the bound on *both* sides by the same number: the RTL
                # takes it as cfg_max_retired_work below, the golden device
                # reads it out of this header field.  Neither program image is
                # touched, so the deployment digest is still the shipped one.
                device.header = replace(
                    device.header, max_retired_work=args.max_retired_work
                )
            work_bound = int(device.header.max_retired_work)
            driver = GenerationDriver(device)
            golden = run_golden(device, driver, request)

            symbols = golden["symbols"]
            symbol_base = len(symbol_words)
            mask = 0
            for index in range(SYMBOL_STRIDE):
                value = symbols.get(index)
                symbol_words.append(0 if value is None else int(value) & 0xFFFFFFFF)
                if value is not None:
                    mask |= 1 << index

            opcodes: dict[tuple[int, int], int] = {}
            for issue in golden["issues"]:
                key = (int(issue["family"]), int(issue["sub"]))
                opcodes[key] = opcodes.get(key, 0) + 1

            issue_base = len(issue_words) // ISSUE_STRIDE
            for issue in golden["issues"]:
                issue_words.append((issue["family"] << 8) | issue["sub"])
                issue_words.append(issue["descriptor_id"] & 0xFFFFFFFF)
                issue_words.append(issue["index"] & 0xFFFFFFFF)

            view_base = len(view_words) // VIEW_STRIDE
            for view in golden["views"]:
                view_words.append(view["descriptor_id"] & 0xFFFFFFFF)
                view_words.append(view["slot"])
                view_words.append(view["extent"] & 0xFFFFFFFF)
                view_words.append(view["element_offset"] & 0xFFFFFFFF)
                view_words.append((view["element_offset"] >> 32) & 0xFFFFFFFF)
                view_words.append(view["rank"])
                view_words.append(view["extent_axis"])

            entry = next(
                e for e in deployment.entrypoints
                if e["entrypoint_id"] == request.entrypoint_id
            )
            flags = 1 | 2 | (4 if golden["complete"] else 0)
            words = [
                program_base,
                instruction_count,
                desc_base,
                len(table),
                symbol_base,
                mask,
                header_base,
                int(entry["first_instruction"]),
                work_bound & 0xFFFFFFFF,
                (work_bound >> 32) & 0xFFFFFFFF,
                flags,
                0,                       # expected header trap class: admitted
                instruction_count,
                entrypoint_count,
                int(golden["trap_class"]),
                int(golden["first_fault"]) & 0xFFFFFFFF,
                int(golden["fetched"]),
                int(golden["retired"]),
                int(golden["predicated_off"]),
                int(golden["issued"]),
                int(golden["loop_iterations"]),
                int(golden["branches"]),
                int(golden["wait_events"]),
                int(golden["state_prepares"]),
                int(golden["state_commits"]),
                int(golden["state_discards"]),
                int(golden["state_reads"]),
                int(golden["state_generation_advances"]),
                int(golden["state_commits_applied"]),
                int(golden["state_rows_committed"]),
                issue_base,
                len(golden["issues"]),
                view_base,
                len(golden["views"]),
                state_count,
                (target_index << 8) | int(request.phase),
                # The bound the *header* declares, which the header-admission
                # check compares against.  It is the same number as words 8/9
                # unless --max-retired-work lowered the co-simulation bound, and
                # keeping them apart is what lets a bounded prefix still check
                # that the RTL reads the real header correctly.
                declared_work & 0xFFFFFFFF,
                (declared_work >> 32) & 0xFFFFFFFF,
            ]
            if len(words) != CASE_STRIDE:
                raise SystemExit(
                    f"case record is {len(words)} words, expected {CASE_STRIDE}"
                )
            case_words.extend(words)

            issue_blob = b"".join(
                int(word).to_bytes(4, "little")
                for word in issue_words[issue_base * ISSUE_STRIDE :]
            )
            view_blob = b"".join(
                int(word).to_bytes(4, "little")
                for word in view_words[view_base * VIEW_STRIDE :]
            )
            records.append({
                "name": f"{target.key}/{request.name}",
                "deployment": target.key,
                "deployment_sha256": actual,
                "request": request.name,
                "entrypoint_id": request.entrypoint_id,
                "phase": int(request.phase),
                "prompt_tokens": args.prompt_tokens,
                "symbols": {str(k): int(v) for k, v in sorted(symbols.items())},
                "work_bound": work_bound,
                "declared_max_retired_work": declared_work,
                "work_bound_lowered_for_cosimulation": bounded,
                "ran_to_completion": bool(golden["complete"]),
                "depth": {
                    "static_instructions_in_program": instruction_count,
                    "distinct_static_instructions_reached": len(
                        {int(i["index"]) for i in golden["issues"]}
                    ),
                    "instructions_fetched": int(golden["fetched"]),
                    "instructions_retired": int(golden["retired"]),
                    "engine_issues": len(golden["issues"]),
                    "resolved_operand_views": len(golden["views"]),
                },
                "golden": {
                    key: value for key, value in sorted(golden.items())
                    if key not in {"issues", "views", "counters", "symbols"}
                },
                "golden_counters": golden["counters"],
                "issued_opcodes": [
                    {"family": family, "sub": sub, "issues": count}
                    for (family, sub), count in sorted(opcodes.items())
                ],
                "issue_base": issue_base,
                "issue_count": len(golden["issues"]),
                "issue_stream_sha256": hashlib.sha256(issue_blob).hexdigest(),
                "view_base": view_base,
                "view_count": len(golden["views"]),
                "view_stream_sha256": hashlib.sha256(view_blob).hexdigest(),
            })

    opcode_union: dict[tuple[int, int], int] = {}
    for record in records:
        for entry in record["issued_opcodes"]:
            key = (entry["family"], entry["sub"])
            opcode_union[key] = opcode_union.get(key, 0) + entry["issues"]

    total_issues = sum(r["issue_count"] for r in records)
    total_views = sum(r["view_count"] for r in records)
    completions = sum(1 for r in records if r["ran_to_completion"])
    if total_views == 0:
        raise SystemExit(
            "no operand view was resolved: the view comparison would pass "
            "without comparing anything"
        )
    if completions != len(records):
        # Not fatal -- a bounded prefix is a legitimate vector -- but it must
        # not pass unnoticed, because it changes what the marker means.
        print(
            f"note: {len(records) - completions} of {len(records)} cases stop "
            "at a bound rather than at COMPLETE",
            file=sys.stderr,
        )

    meta = [
        len(records), total_issues, total_views, completions, len(TARGETS),
        0, 0, 0,
    ]

    # The two checkers hold these images in fixed-size arrays; a vector set that
    # outgrew them would be read back truncated and still "pass".
    for name, used, limit in (
        ("case", len(case_words), CASE_MEM_WORDS),
        ("issue", len(issue_words), ISSUE_MEM_WORDS),
        ("view", len(view_words), VIEW_MEM_WORDS),
    ):
        if used > limit:
            raise SystemExit(
                f"the {name} image is {used} words and the checkers in "
                f"rtl/test/tb_a3_deployment.sv and "
                f"rtl/test/a3_deployment_harness.cpp hold {limit}; raise both "
                "before regenerating"
            )

    files = {
        # Read by the DUT: padded to the RTL memory size.
        "a3_program.hex": hex_lines(program_words, 256, PROGRAM_WORDS),
        "a3_header.hex": hex_lines(header_words, 32, HEADER_WORDS),
        "a3_descriptor.hex": hex_lines(
            desc_words, DESCRIPTOR_PREFIX_BYTES * 8, DESC_WORDS
        ),
        "a3_symbol.hex": hex_lines(symbol_words, 32, SYMBOL_WORDS),
        # Read by the two checkers only: exact length.
        "a3_deployment_case.hex": hex_lines(case_words, 32),
        "a3_deployment_issue.hex": hex_lines(issue_words, 32),
        "a3_deployment_view.hex": hex_lines(view_words, 32),
        "a3_deployment_meta.hex": hex_lines(meta, 32),
    }
    for name, payload in files.items():
        (out / name).write_text(payload, encoding="ascii")

    marker = (
        f"PASS: ABI3 RTL deployment co-simulation deployments={len(TARGETS)} "
        f"cases={len(records)} completions={completions} "
        f"issues={total_issues} views={total_views}"
    )
    summary = {
        "schema": "opentallas.rtl.abi3_deployment_vectors.v1",
        "rtl_implementation_bounds": {
            "source": "rtl/abi3/ot_a3_pkg.sv",
            "values": bounds,
            "expressed_by": BOUND_CAPABILITY_FIELD,
            "note": (
                "these four are the sequencer's own bounds. The RTL package "
                "calls them capability fields; expressed_by says, per bound, "
                "what in a capability or in the frozen ABI actually expresses "
                "it. A bound nothing expresses cannot be refused at admission, "
                "so a program that exceeds it is admitted and traps in the RTL "
                "instead"
            ),
            "overruns": overrun_summary,
        },
        "abi": {"major": 3, "minor": 0},
        "what_is_correlated": (
            "the four deployments this program ships, executed on the RTL "
            "control plane and on runtime.sim.device.Device from the same "
            "program image, the same descriptor table and the same runtime "
            "symbols; one verification top is compared with node zero's "
            "resolved views and the exact per-node state commit run, while "
            "the vector record separately retains the cluster node count and "
            "cluster-total committed rows"
        ),
        "engine_stub_policy": (
            "every dispatchable engine operation is a recording no-op: RTL 3.0 "
            "implements the control plane, so the comparison is the control "
            "plane and no checkpoint byte reaches an engine on either side; "
            "the golden Device still authenticates all mapped source ranges "
            "before execution"
        ),
        "prompt_tokens": args.prompt_tokens,
        "requested_max_retired_work": args.max_retired_work,
        "case_count": len(records),
        "deployment_count": len(TARGETS),
        "completion_count": completions,
        "issue_event_count": total_issues,
        "view_resolution_count": total_views,
        "issued_opcodes": [
            {"family": family, "sub": sub, "issues": count}
            for (family, sub), count in sorted(opcode_union.items())
        ],
        "issue_reference": (
            "runtime.sim.device.Device's own trace: for every engine issue the "
            "family, subopcode, descriptor ID and the instruction index that "
            "issued it, in program order"
        ),
        "view_reference": (
            "runtime.sim.memory.ViewResolver.resolve, evaluated against the "
            "loop bindings runtime.sim.device.Device recorded at each issue; "
            "amendments A4 (dynamic index terms), A13 (partial final iteration "
            "of a block loop) and A18 (the axis that iteration is partial in)"
        ),
        "required_marker": marker,
        "geometry": {
            "program_words": PROGRAM_WORDS,
            "header_words": HEADER_WORDS,
            "descriptor_words": DESC_WORDS,
            "symbol_words": SYMBOL_WORDS,
            "case_stride": CASE_STRIDE,
            "issue_stride": ISSUE_STRIDE,
            "view_stride": VIEW_STRIDE,
            "descriptor_prefix_bytes": DESCRIPTOR_PREFIX_BYTES,
            "program_words_used": len(program_words),
            "header_words_used": len(header_words),
            "descriptor_words_used": len(desc_words),
            "symbol_words_used": len(symbol_words),
        },
        "image_sha256": {
            name: hashlib.sha256(payload.encode("ascii")).hexdigest()
            for name, payload in sorted(files.items())
        },
        "deployments": deployments,
        "cases": records,
    }
    (out / "abi3_deployment_rtl_vectors.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for overrun in overrun_summary:
        print(
            f"OVERRUN {overrun['deployment']}: {overrun['parameter']} is "
            f"{overrun['rtl_bound']} in {overrun['declared_in']} and this "
            f"deployment needs {overrun['deployment_requires']}",
            file=sys.stderr,
        )
    print(
        f"abi3 deployment rtl vectors: deployments={len(TARGETS)} "
        f"cases={len(records)} completions={completions} "
        f"issues={total_issues} views={total_views}"
    )
    for record in records:
        depth = record["depth"]
        print(
            f"  {record['name']}: retired={depth['instructions_retired']} "
            f"of a {depth['static_instructions_in_program']}-instruction "
            f"program, issues={depth['engine_issues']}, "
            f"views={depth['resolved_operand_views']}, "
            f"complete={record['ran_to_completion']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
