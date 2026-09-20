#!/usr/bin/env python3
"""The DEVICE's selected compressed positions, per ROUTE.INDEX_TOPK operator.

results/abi3/deepseek_v41_divergence_enters_layer2_attention.json brackets the V4.1
divergence inside layer 2's attention and shows it absent at prompt position 0. Two
facts about layer 2 explain why that shape points at a SELECTION rather than at an
arithmetic difference: it is the first layer with a nonzero compress_ratio, and it is
the first kv_source_layer, so its Indexer owns its keys and picks the index_topk best
compressed positions per query.

A top-k is DISCRETE. A one-ulp difference in two nearly equal scores does not perturb
the output by an ulp, it swaps which position is attended to, and the attention output
then differs by far more than the scores did. That is the only mechanism in the block
that turns the few-BF16-ulp drift measured through layers 0 and 1 into the 44.8x step
measured across layer 2's attention, and at position 0 there is nothing to select.

So this records what the device selected, and
tools/compare_deepseek_v41_index_selection.py compares it against the vendor's own
Indexer return -- which is exactly this quantity: ``index_score.topk(...).indices``
sorted, with out-of-range entries set to -1.

Usage: probe_deepseek_v41_device_index_selection.py DEPLOYMENT CAPABILITY WORKLOAD
CHECKPOINT OUTPUT [MAX_OPERATORS]
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
MAX_OPERATORS = int(sys.argv[6]) if len(sys.argv) > 6 else 4

deployment = Deployment.read(deployment_root)
capability = Capability.from_dict(json.loads(capability_path.read_text()))
workload = json.loads(workload_path.read_text())
prompt = [int(t) for t in workload["token_ids"]]
device = Device(deployment, capability, root=checkpoint, verify=False)

selections: list[dict] = []
seen: set[int] = set()
#: HOW MANY TIMES each operator is ISSUED, which a probe that dedupes by descriptor
#: cannot see and must not omit: a view of one query row issued ten times computes
#: the same ten rows a view of ten rows computes once, and reading the first
#: occurrence alone cannot tell those apart.
issues: dict[int, int] = {}
rows_by_issue: dict[int, list] = {}

class _Stop(Exception):
    pass

key = (int(Major.ROUTE), int(Route.INDEX_TOPK))
original = registry[key]

def wrapper(ctx, sub, operator):
    result = original(ctx, sub, operator)
    descriptor_id = int(operator.descriptor_id)
    issues[descriptor_id] = issues.get(descriptor_id, 0) + 1
    #: EVERY issue, not the first sixteen. The causal mask leaves nothing to select
    #: for the earliest query rows -- a compressed group has to have COMPLETED before
    #: a position for that position to attend to it -- so a sample of the first
    #: issues is biased towards empty selections and says nothing about the rest.
    if issues[descriptor_id] <= 512:
        #: The SCORE view's own layout, because the streamed query row is derived
        #: from it: which loop term walks its rows is a function of its strides,
        #: and a derivation that matches no term silently selects nothing.
        try:
            score = ctx.input_view(operator, 0)
            print(f"  score view {score.descriptor_id} dims {tuple(score.dims)} "
                  f"strides {tuple(score.strides)} loop_terms {score.loop_terms} "
                  f"offset {score.element_offset}", flush=True)
        except Exception as error:
            print(f"  score view unavailable: {error}", flush=True)
        view = ctx.output_view(operator, 0)
        raw = np.asarray(ctx.read(view)).astype(np.int64)
        raw = np.where(raw >= (1 << 31), raw - (1 << 32), raw)
        rows_by_issue.setdefault(descriptor_id, []).append(
            {"issue": issues[descriptor_id],
             "dims": [int(x) for x in view.dims],
             "rows": raw.reshape(-1, raw.shape[-1]).tolist()
             if raw.ndim > 1 else raw.reshape(1, -1).tolist()}
        )
    if descriptor_id not in seen:
        seen.add(descriptor_id)
        #: The SCORE view's own layout, because the streamed query row is derived
        #: from it: which loop term walks its rows is a function of its strides,
        #: and a derivation that matches no term silently selects nothing.
        try:
            score = ctx.input_view(operator, 0)
            print(f"  score view {score.descriptor_id} dims {tuple(score.dims)} "
                  f"strides {tuple(score.strides)} loop_terms {score.loop_terms} "
                  f"offset {score.element_offset}", flush=True)
        except Exception as error:
            print(f"  score view unavailable: {error}", flush=True)
        view = ctx.output_view(operator, 0)
        rows = np.asarray(ctx.read(view))
        rows = rows.reshape(-1, rows.shape[-1]) if rows.ndim > 1 else rows.reshape(1, -1)
        #: The selected indices are an integer view; read them as signed, because
        #: the vendor marks an out-of-range entry with -1 and so does this operator.
        signed = rows.astype(np.int64)
        signed = np.where(signed >= (1 << 31), signed - (1 << 32), signed)
        #: The runtime symbol table AT THE SELECTION, because the row extent and
        #: the operand-present predicate are both functions of it: layer 2's
        #: select declares [span_tokens, 512] and is predicated on
        #: ``context_groups_ratio2 > 0``, so a one-row all-padding output is
        #: either a wrong span or a false predicate and only these values say
        #: which.
        try:
            symbols = {str(k): int(v) for k, v in dict(ctx.symbols).items()}
        except Exception:
            symbols = {}
        selections.append({
            "order": len(selections),
            "operator": descriptor_id,
            "symbols": symbols,
            "view": int(view.descriptor_id),
            "dims": [int(x) for x in view.dims],
            "dtype": str(view.dtype),
            "rows": signed.tolist(),
        })
        print(f"selection {len(selections)-1}: operator {descriptor_id} "
              f"dims {tuple(view.dims)} "
              f"range [{signed.min()}, {signed.max()}] symbols {symbols}", flush=True)
        if len(selections) >= MAX_OPERATORS:
            raise _Stop
    return result

registry[key] = wrapper
driver = GenerationDriver(device)
try:
    driver.generate(prompt, max_new_tokens=1)
except _Stop:
    print("stopped after the requested number of selections", flush=True)
finally:
    registry[key] = original

output.write_text(json.dumps({
    "schema": "opentallas.probe.v41_device_index_selection.v1",
    "prompt_token_count": len(prompt),
    "deployment": str(deployment_root),
    "selection_count": len(selections),
    "issues_per_operator": issues,
    "per_issue_rows": rows_by_issue,
    "selections": selections,
}) + "\n")
for descriptor_id, count in sorted(issues.items()):
    print(f"operator {descriptor_id}: issued {count} time(s)", flush=True)
print(f"-> {output}", flush=True)
