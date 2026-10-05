"""Compare the two stores at the ONE tap whose shape both lanes agree on."""
import hashlib, json, sys
import numpy as np
from pathlib import Path
sys.path.insert(0, ".")
from runtime.abi3.capability import Capability
from runtime.abi3.constants import Major, Selection
from runtime.abi3.deployment import Deployment
from runtime.driver import GenerationDriver
from runtime.sim.device import Device
from runtime.sim.engine import _REGISTRY
from runtime.sim.engines import load_engines
import runtime.sim.engines.selection as SEL
load_engines()
STORES = {
    "rom": ("build/abi3/deepseek-v41-reduced-rom",
            "configs/hardware/abi3_capability/rom_deepseek_v41_wafer.json"),
    "hbm": ("build/abi3/deepseek-v41-reduced-hbm",
            "results/abi3/deepseek_v41_hbm_comparator_capability.json"),
}
def run(store):
    dep_dir, cap_path = STORES[store]
    body = json.loads(Path(cap_path).read_text())
    cap = Capability.from_dict(body.get("capability", body))
    dev = Device(Deployment.read(Path(dep_dir)), cap, verify=False, trace=False,
                 root=Path("build/models/deepseek-v4.1-flash-reduced-v1"))
    grab = {}
    key = (int(Major.SELECTION), int(Selection.ARGMAX))
    original = _REGISTRY[key]
    def spy(ctx, sub, descriptor):
        view = ctx.input_view(descriptor, 0)
        vals = np.asarray(SEL._widen(ctx, view), dtype=np.float64).reshape(-1)
        grab["logits"] = vals.copy()
        return original(ctx, sub, descriptor)
    _REGISTRY[key] = spy
    try:
        drv = GenerationDriver(dev)
        oracle = json.loads(Path("results/abi3/deepseek_v41_reduced_reference_oracle.json").read_text())
        prompt = list(oracle["results"]["TA-DS41-REDUCED-EOS-1"]["prompt_token_ids"])
        res = drv.generate(prompt, max_new_tokens=1).to_dict()
    finally:
        _REGISTRY[key] = original
    return grab.get("logits"), res.get("generated_token_ids")
out = {}
for s in ("rom", "hbm"):
    lg, tok = run(s)
    out[s] = (lg, tok)
    print(f"{s}: token {tok} logits n={0 if lg is None else lg.size}", flush=True)
a, b = out["rom"][0], out["hbm"][0]
if a is None or b is None:
    print("one store produced no logits"); raise SystemExit(0)
print(f"identical: {np.array_equal(a, b)}")
d = np.abs(a - b)
print(f"max abs diff {d.max():.6e}  mean {d.mean():.6e}  differing elements {(d>0).sum()} of {d.size}")
print(f"rom argmax {int(np.argmax(a))} ({a.max():+.6f})   hbm argmax {int(np.argmax(b))} ({b.max():+.6f})")
print(f"rom logit at hbm's pick {a[int(np.argmax(b))]:+.6f}   hbm logit at rom's pick {b[int(np.argmax(a))]:+.6f}")
print(f"oracle token 1638: rom {a[1638]:+.6f}  hbm {b[1638]:+.6f}")
