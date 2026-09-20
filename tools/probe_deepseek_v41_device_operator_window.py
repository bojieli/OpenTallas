#!/usr/bin/env python3
"""Every device engine output inside ONE operator window, for a shape-aware bisection.

results/abi3/deepseek_v41_divergence_enters_layer2_attention.json brackets the V4.1
divergence between two taps that need no matching -- layer 2's attention-norm input
agrees to a few BF16 ulps and its FFN-norm input does not -- and says what it cannot
settle: which operator inside that sublayer. The bracket is a pair of DESCRIPTOR
IDS, so this records every engine output the device produces between them.

WHY A WINDOW RATHER THAN THE WHOLE PROGRAM. The earlier bisection recorded every
engine call in the program and matched each oracle checkpoint to the most nearly
proportional device record of the same element count; with thousands of candidates
that matching is unreliable, and its own record says so. Inside one sublayer there
are a few hundred, and of those only a handful share any given element count, so the
match is nearly forced.

Usage: probe_deepseek_v41_device_operator_window.py DEPLOYMENT CAPABILITY WORKLOAD
CHECKPOINT OUTPUT FIRST LAST [MAX_ELEMENTS]

FIRST and LAST are descriptor ids; the window is open at both ends, so the two
bracketing operators are not themselves recorded. Each record carries the output
view's dims and one row at the last prompt position, which is where the comparison
reads.
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
from runtime.sim.engine import _REGISTRY as registry
from runtime.sim.formats import widen
from runtime.abi3.constants import DType

deployment_root, capability_path, workload_path, checkpoint, output = (
    Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]),
    Path(sys.argv[4]), Path(sys.argv[5]))
FIRST, LAST = int(sys.argv[6]), int(sys.argv[7])
MAX_ELEMENTS = int(sys.argv[8]) if len(sys.argv) > 8 else 200_000

deployment = Deployment.read(deployment_root)
capability = Capability.from_dict(json.loads(capability_path.read_text()))
workload = json.loads(workload_path.read_text())
prompt = [int(t) for t in workload["token_ids"]]
device = Device(deployment, capability, root=checkpoint, verify=False)

records: list[dict] = []
seen: set[int] = set()

class _Stop(Exception):
    pass

def _rows(ctx, view):
    """The view as float64 rows, widening codes when the view is not FP32."""
    codes = np.asarray(ctx.read(view))
    if DType(view.dtype) == DType.FP32:
        values = np.asarray(codes, dtype=np.float64)
    else:
        try:
            values = np.asarray(widen(view.dtype, codes), dtype=np.float64)
        except Exception:
            values = np.asarray(codes, dtype=np.float64)
    return values.reshape(-1, values.shape[-1]) if values.ndim else values.reshape(1, -1)

def wrap(key, original):
    def wrapper(ctx, sub, operator):
        result = original(ctx, sub, operator)
        descriptor_id = int(operator.descriptor_id)
        if FIRST < descriptor_id < LAST and descriptor_id not in seen:
            seen.add(descriptor_id)
            try:
                view = ctx.output_view(operator, 0)
            except Exception:
                view = None
            if view is not None:
                size = int(np.prod(view.dims)) if view.dims else 0
                entry = {
                    "operator": descriptor_id,
                    "major": int(key[0]), "sub": int(key[1]),
                    "view": int(view.descriptor_id),
                    "dims": [int(x) for x in view.dims],
                    "elements": size,
                    "dtype": str(view.dtype),
                }
                if 0 < size <= MAX_ELEMENTS:
                    rows = _rows(ctx, view)
                    entry["rows"] = rows.tolist()
                records.append(entry)
        elif descriptor_id >= LAST:
            raise _Stop
        return result
    return wrapper

for key, original in list(registry.items()):
    registry[key] = wrap(key, original)

driver = GenerationDriver(device)
try:
    driver.generate(prompt, max_new_tokens=1)
except _Stop:
    print("stopped at the window's closing descriptor", flush=True)

output.write_text(json.dumps({
    "schema": "opentallas.probe.v41_device_operator_window.v1",
    "window": {"after_descriptor": FIRST, "before_descriptor": LAST},
    "prompt_token_count": len(prompt),
    "deployment": str(deployment_root),
    "record_count": len(records),
    "records": records,
}) + "\n")
print(f"{len(records)} engine outputs in the window -> {output}", flush=True)
