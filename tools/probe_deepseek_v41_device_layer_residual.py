"""Every layer's residual, as the DEVICE sees it, with no heuristic matching.

results/abi3/deepseek_v41_device_oracle_engram_depth.json has two unambiguous
taps -- the engram layers, 1 and 14 -- and says what it cannot settle: WHICH layer
between 2 and 13 introduces the difference, because "narrowing further needs a
shape-aware per-operator comparison rather than the best-cosine matching the
earlier bisection used".

This is that comparison's device half, and it needs no matching at all. The IR
names a kernel ``main.layerNN.attention.norm`` per layer whose single value input
is ``main.layerNN.hyper_connection.attention.collapsed`` -- the residual stream
entering the block, after the hyper-connection collapse. Every one of them is an
RMS_NORM over the model width, so recording each RMS_NORM's input row in issue
order, deduplicated by operator descriptor, gives one tap per layer in order. The
vendor's own RMSNorm sees the same tensor, so the pairing is by construction.

Writes ROWS, not summaries: the vendor's Block does ``x = self.hc_pre(x, pre_mix)``
then ``x = self.attn_norm(x)``, so the tensor its RMSNorm sees IS this one, and
tools/compare_deepseek_v41_layer_residual.py does the comparison against a
forward pre-hook on each ``layers[n].attn_norm`` and ``layers[n].ffn_norm``. Tap
2k is layer k's attention norm input and tap 2k+1 its FFN norm input.

Usage: probe_deepseek_v41_device_layer_residual.py DEPLOYMENT CAPABILITY WORKLOAD
CHECKPOINT OUTPUT [WIDTH] [STOP_AFTER]
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
from runtime.abi3.constants import Major, Vector
from runtime.sim.engine import _REGISTRY as registry
from runtime.sim.formats import widen
from runtime.abi3.constants import DType

deployment_root, capability_path, workload_path, checkpoint, output = (
    Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]),
    Path(sys.argv[4]), Path(sys.argv[5]))
WIDTH = int(sys.argv[6]) if len(sys.argv) > 6 else 5120
STOP_AFTER = int(sys.argv[7]) if len(sys.argv) > 7 else 32

deployment = Deployment.read(deployment_root)
capability = Capability.from_dict(json.loads(capability_path.read_text()))
workload = json.loads(workload_path.read_text())
prompt = [int(t) for t in workload['token_ids']]
device = Device(deployment, capability, root=checkpoint, verify=False)

taps: list[dict] = []
seen: set[int] = set()

class _Stop(Exception):
    pass

key = (int(Major.VECTOR), int(Vector.RMS_NORM))
original = registry[key]

def wrapper(ctx, sub, operator):
    descriptor_id = int(operator.descriptor_id)
    if descriptor_id not in seen:
        try:
            view = ctx.input_view(operator, 0)
        except Exception:
            view = None
        if view is not None and view.dims and int(view.dims[-1]) == WIDTH:
            #: ``ctx.read`` hands back CODES, not values: a BF16 view read as
            #: float gives 14018.0 for 0x36C2. The shipped V4.1 frame carries the
            #: residual stream in BF16, so it has to be widened -- which is exact
            #: for BF16, FP16 and FP32 alike and introduces no rounding here.
            codes = np.asarray(ctx.read(view))
            if DType(view.dtype) == DType.FP32:
                rows = np.asarray(codes, dtype=np.float64)
            else:
                rows = np.asarray(widen(view.dtype, codes), dtype=np.float64)
            rows = rows.reshape(-1, rows.shape[-1])
            taps.append({
                'order': len(taps),
                'operator': descriptor_id,
                'view': int(view.descriptor_id),
                'dims': [int(x) for x in view.dims],
                'dtype': str(view.dtype),
                'rows': rows.tolist(),
            })
            seen.add(descriptor_id)
            print(f"tap {len(taps)-1}: operator {descriptor_id} view "
                  f"{view.descriptor_id} dims {tuple(view.dims)} "
                  f"[{rows.min():.6f}, {rows.max():.6f}]", flush=True)
            if len(taps) >= STOP_AFTER:
                original(ctx, sub, operator)
                raise _Stop
    return original(ctx, sub, operator)

registry[key] = wrapper
driver = GenerationDriver(device)
try:
    driver.generate(prompt, max_new_tokens=1)
except _Stop:
    print("stopped after the requested number of taps", flush=True)
finally:
    registry[key] = original

output.write_text(json.dumps({
    'schema': 'opentallas.probe.v41_device_layer_residual.v1',
    'width': WIDTH,
    'prompt_token_count': len(prompt),
    'deployment': str(deployment_root),
    'tap_count': len(taps),
    'taps': taps,
}) + "\n")
print(f"-> {output}", flush=True)
