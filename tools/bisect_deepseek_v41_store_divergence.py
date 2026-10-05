"""Find where the two DeepSeek V4.1 stores stop agreeing, without an oracle.

WHY THIS EXISTS
---------------
The ROM wafer emits token 2750 and the HBM single chip 459 from the same graph
over the same weights, and the reference oracle says 1638.  Three numbers, and the
pair is the useful one: TWO LANES LOWERING ONE GRAPH MUST PRODUCE THE SAME BYTES,
so they are each other's reference and no PyTorch run is needed to compare them.

WHAT IT MEASURES
----------------
Every engine dispatch is wrapped, and for each one the digest of every bound
output view is recorded against the descriptor's ``source_kernel_id`` -- the graph
kernel both lanes were lowered from.  The traces are then compared per kernel.

WHAT IT ESTABLISHES, AND WHAT IT DOES NOT
-----------------------------------------
It establishes agreement: through graph kernel 201, every kernel that BOTH lanes
emit as a single comparable output produces byte-identical results -- 198 of them.

It does NOT establish where values first diverge, and the reason is worth writing
down because it defeated three successively finer comparisons:

  1. Comparing dispatch SEQUENCES reports kernel 0, where both lanes produced the
     identical digest and the ROM wafer simply ran it twice -- it is a two-node
     device.  9,211 engine outputs against 4,112 is mostly that.
  2. Comparing (family, sub, digest) SETS reports kernel 60, where the ROM lane
     spends a DMA.COPY on a movement the HBM lane expresses as a view alias.  Both
     hold the same bytes afterwards.
  3. Comparing digests alone reports kernel 74, where the ROM lane emits the
     eight-group output projection as eight operators and the HBM lane as one.
  4. Restricting to kernels where both emit exactly ONE digest reports kernel 202,
     ROUTE.INDEX_TOPK -- and its views are [128, 64] -> [128, 16] on ROM against
     [1, 64] -> [1, 16] on HBM.  The HBM lane launches that operator once per
     query row where the ROM lane launches it once per span, so the two digests
     are of differently shaped buffers and cannot disagree meaningfully.

The lanes tile differently, legitimately, so a per-launch digest is the wrong
instrument.  What is needed is the digest of each kernel's whole declared OUTPUT
TENSOR once its last launch has retired, which this tool does not yet take.
Reported this way so the next attempt starts from the instrument rather than from
kernel 202.
"""

import hashlib, json, sys
import numpy as np
from pathlib import Path
sys.path.insert(0, ".")
from runtime.abi3.capability import Capability
from runtime.abi3.deployment import Deployment
from runtime.driver import GenerationDriver
from runtime.sim.device import Device
from runtime.sim.engine import _REGISTRY
from runtime.sim.engines import load_engines
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
    deployment = Deployment.read(Path(dep_dir))
    dev = Device(deployment, cap, verify=False, trace=False,
                 root=Path("build/models/deepseek-v4.1-flash-reduced-v1"))
    trace = []
    originals = dict(_REGISTRY)
    def wrap(key, fn):
        def spy(ctx, sub, descriptor):
            fn(ctx, sub, descriptor)
            kid = int(descriptor.payload.get("source_kernel_id", -1))
            digests = []
            for slot in (0, 1):
                vid = descriptor.payload.get(f"output_view_{slot}")
                if vid is None or int(vid) == 0xFFFFFFFF:
                    continue
                try:
                    view = ctx.output_view(descriptor, slot)
                    arr = np.ascontiguousarray(ctx.read(view))
                    digests.append(hashlib.sha256(arr.tobytes()).hexdigest()[:16])
                except Exception as exc:
                    digests.append(f"unread:{type(exc).__name__}")
            trace.append((kid, key[0], key[1], tuple(digests)))
        return spy
    for key, fn in list(_REGISTRY.items()):
        _REGISTRY[key] = wrap(key, fn)
    try:
        drv = GenerationDriver(dev)
        oracle = json.loads(Path("results/abi3/deepseek_v41_reduced_reference_oracle.json").read_text())
        prompt = list(oracle["results"]["TA-DS41-REDUCED-EOS-1"]["prompt_token_ids"])
        res = drv.generate(prompt, max_new_tokens=1).to_dict()
    finally:
        _REGISTRY.clear(); _REGISTRY.update(originals)
    return trace, res.get("generated_token_ids")

import os
DUMP = Path(os.environ.get("OT_TRACE_DUMP", "/tmp/store_traces.json"))
traces = {}
tokens = {}
for store in ("rom", "hbm"):
    t, tok = run(store)
    traces[store] = t
    tokens[store] = tok
    print(f"{store}: {len(t)} engine outputs recorded, token {tok}", flush=True)
DUMP.write_text(json.dumps({"tokens": tokens,
                            "traces": {k: [list(e[:3]) + [list(e[3])] for e in v]
                                       for k, v in traces.items()}}))
print("dumped", DUMP, flush=True)

rom, hbm = traces["rom"], traces["hbm"]
by_rom, by_hbm = {}, {}
for kid, fam, sub, dig in rom: by_rom.setdefault(kid, []).append((fam, sub, dig))
for kid, fam, sub, dig in hbm: by_hbm.setdefault(kid, []).append((fam, sub, dig))
shared = sorted(set(by_rom) & set(by_hbm))
print(f"kernels executed in both: {len(shared)}  (rom-only {len(set(by_rom)-set(by_hbm))}, hbm-only {len(set(by_hbm)-set(by_rom))})")
#: DEDUPLICATED, because a replication difference is not a value difference.
#: The ROM wafer is a two-node device and runs some kernels once per node, so it
#: records 9,211 engine outputs where the single-chip HBM records 4,112 -- and
#: comparing sequences reports kernel 0 as "divergent" when both stores produced
#: the identical digest, ROM twice.  What matters is the SET of digests a kernel
#: produced: if the two stores computed the same bytes, the sets are equal
#: however many times each lane ran it.
def norm(entries):
    #: DIGESTS ONLY, not (family, sub, digest).  A lane may express one graph
    #: kernel as a different NUMBER of operators -- the ROM wafer adds a DMA.COPY
    #: where the HBM lane aliases a view, and both then hold the same bytes -- so
    #: including the opcode reports a structural difference as a value one.  What
    #: the graph fixes is the bytes each kernel produces; how many operators a
    #: backend spends producing them is its own business.
    out = set()
    for _fam, _sub, digs in entries:
        out.update(digs)
    return sorted(out)
first = None
for kid in shared:
    if norm(by_rom[kid]) != norm(by_hbm[kid]):
        first = kid
        break
if first is None:
    print("NO DIVERGENCE among shared kernels")
else:
    print(f"\nFIRST VALUE-DIVERGENT KERNEL: source_kernel_id {first}")
    print("  rom:", norm(by_rom[first]))
    print("  hbm:", norm(by_hbm[first]))
    agree = [k for k in shared if norm(by_rom[k]) == norm(by_hbm[k])]
    print(f"  kernels agreeing: {len(agree)} of {len(shared)}")
    idx = shared.index(first)
    for kid in shared[max(0, idx-3):idx]:
        print(f"  agreed before: kid {kid} {by_rom[kid][0][:2]}")
