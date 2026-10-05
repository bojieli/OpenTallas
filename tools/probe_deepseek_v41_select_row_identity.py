#!/usr/bin/env python3
"""Where the streamed select's QUERY ROW is, if it is anywhere.

``ROUTE.INDEX_TOPK``'s causal horizon is a function of the query's absolute
position.  In the shipped V4.1 HBM cell the score plane is streamed one query at
a time -- amendment A18 encodes one request-dependent extent per view and that
plane has two dynamic axes -- so the operator is issued once per row and
``query_position`` resolves to ``POSITION_START + row`` with ``row`` always 0 and
``POSITION_START`` zero throughout prefill.  Every issue at layers 2 and 8 then
sees a horizon of zero and selects nothing.

results/abi3/deepseek_v41_select_row_is_not_in_its_operands.json records two
derivations from the SCORE view that were built, measured and refuted: its
resolved layout carries no dynamic term at all, so nothing in it distinguishes
one launch from the next.  This probe looks at the three places that record did
NOT examine:

* the OUTPUT view -- the select writes one row per launch into an index array,
  so unlike the score plane the destination cannot be the same row every time;
* ``EngineContext.loops``, the induction value of every enclosing loop, which
  the runtime already carries at dispatch and which no engine reads; and
* the output view's ``element_offset``, which is where a resolved row-walking
  term ends up after resolution even when the term list is consumed.

It asserts nothing.  It prints what is there so a derivation is chosen against a
measurement rather than against an expectation, which is how the two refuted
ones were built.

Usage: probe_deepseek_v41_select_row_identity.py DEPLOYMENT CAPABILITY WORKLOAD
CHECKPOINT OUTPUT [MAX_ISSUES]
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.capability import Capability
from runtime.abi3.deployment import Deployment
from runtime.sim.engines import load_engines
load_engines()
from runtime.sim.device import Device
from runtime.driver import GenerationDriver
from runtime.abi3.constants import Major, Route
from runtime.sim.engine import _REGISTRY as registry

deployment_root, capability_path, workload_path, checkpoint, output = (
    Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]),
    Path(sys.argv[4]), Path(sys.argv[5]))
MAX_ISSUES = int(sys.argv[6]) if len(sys.argv) > 6 else 400

deployment = Deployment.read(deployment_root)
capability = Capability.from_dict(json.loads(capability_path.read_text()))
workload = json.loads(workload_path.read_text())
prompt = [int(t) for t in workload["token_ids"]]
device = Device(deployment, capability, root=checkpoint, verify=False)

records: list[dict] = []
issues: dict[int, int] = {}
key = (int(Major.ROUTE), int(Route.INDEX_TOPK))
original = registry[key]


def _layout(view) -> dict:
    return {
        "view": int(view.descriptor_id),
        "dims": [int(x) for x in view.dims],
        "strides": [int(x) for x in view.strides],
        "element_offset": int(view.element_offset),
        "loop_terms": [[int(s), int(i)] for s, i in getattr(view, "loop_terms", ())],
    }


def wrapper(ctx, sub, operator):
    result = original(ctx, sub, operator)
    descriptor_id = int(operator.descriptor_id)
    issues[descriptor_id] = issues.get(descriptor_id, 0) + 1
    if len(records) < MAX_ISSUES:
        row: dict = {
            "issue": issues[descriptor_id],
            "operator": descriptor_id,
            #: the induction value of every enclosing loop, keyed by loop id
            "loops": {str(k): int(v) for k, v in dict(ctx.loops).items()},
            "output": _layout(ctx.output_view(operator, 0)),
        }
        for slot, name in ((0, "score"), (1, "window"), (2, "ratio"), (3, "mask")):
            view = ctx.optional_input(operator, slot)
            row[name] = None if view is None else _layout(view)
        #: THE COMPRESSION RATIO AS DATA, and the aux slots.  The horizon is
        #: ``(position + 1) // ratio`` and the ratio is read from a memory object,
        #: not from a symbol, so nothing in the view layouts above says what it is.
        #: At layer 14 the device selects 0,0,0,0,0,0,0,1,1,1 where the vendor
        #: selects 0,1,1,2,2,3,3,4,4,5, and the first is what a ratio of EIGHT
        #: produces against the second's TWO -- which this records rather than
        #: infers.
        ratio_view = ctx.optional_input(operator, 2)
        row["ratio"] = None
        if ratio_view is not None:
            try:
                row["ratio"] = int(
                    np.asarray(ctx.read(ratio_view), dtype=np.uint64).reshape(-1)[0]
                )
            except Exception as error:
                row["ratio"] = f"unreadable: {error}"
        row["aux"] = []
        for slot in range(4):
            try:
                row["aux"].append(int(operator.payload[f"aux_id_{slot}"]))
            except Exception:
                row["aux"].append(None)
        try:
            row["symbols"] = {str(k): int(v) for k, v in dict(ctx.symbols).items()}
        except Exception:
            row["symbols"] = {}
        records.append(row)
    return result


registry[key] = wrapper
driver = GenerationDriver(device)
try:
    driver.generate(prompt, max_new_tokens=1)
except Exception as error:  # a refusal downstream is not this probe's business
    print(f"generation stopped: {type(error).__name__}: {error}", flush=True)
finally:
    registry[key] = original

#: Which of the three candidate carriers actually MOVES between issues of one
#: operator.  A carrier that is constant across issues cannot be the row.
moving: dict[str, dict[str, bool]] = {}
for descriptor_id in sorted(issues):
    mine = [r for r in records if r["operator"] == descriptor_id]
    if len(mine) < 2:
        continue
    def varies(get) -> bool:
        seen = {json.dumps(get(r), sort_keys=True) for r in mine}
        return len(seen) > 1
    moving[str(descriptor_id)] = {
        "issues_recorded": len(mine),
        "loops_vary": varies(lambda r: r["loops"]),
        "output_offset_varies": varies(lambda r: r["output"]["element_offset"]),
        "output_loop_terms_vary": varies(lambda r: r["output"]["loop_terms"]),
        "score_offset_varies": varies(
            lambda r: (r["score"] or {}).get("element_offset")),
        "symbols_vary": varies(lambda r: r["symbols"]),
    }

report = {
    "schema": "opentallas.derived.deepseek_v41_select_row_identity.v1",
    "producer": {"tool": "tools/probe_deepseek_v41_select_row_identity.py"},
    "issue_counts": {str(k): int(v) for k, v in sorted(issues.items())},
    "what_moves_between_issues": moving,
    "records": records,
    "not_a_claim": [
        "this records layouts and loop induction values; it does not decide "
        "which of them the ABI should say carries the row",
    ],
}
Path(output).parent.mkdir(parents=True, exist_ok=True)
Path(output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(f"{len(records)} issues recorded over {len(issues)} operators -> {output}")
for descriptor_id, flags in moving.items():
    print(f"  operator {descriptor_id}: {flags}")
