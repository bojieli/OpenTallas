#!/usr/bin/env python3
"""Integer die placement of the DeepSeek-V4.1-Flash ROM array: all 188 dies, each with its role, stage, tensor
group, the weight bytes it holds and its HBM stacks (user decision 2026-09-27: integerise the placement --
112 layer dies = 28 stages x 4, 76 non-layer dies incl. 4 head dies -- and state every non-layer die's role).

    python3 tools/v41_die_placement.py [--out results/arch/v41_die_placement.json]

Bytes come from the RELEASED checkpoint's safetensors headers (tools/audit_v41_weight_precision.py's snapshot,
official precision).  ROM per die = the array's per-die capacity (checkpoint bytes / 188, the report's
packaging option (b)).

Placement rules:
* LAYER DIES (stages 0..27, tensor group g = stage, dies 4g..4g+3): the 40 layers' bytes (attention, shared and
  routed experts, norms, HC, and the two Engram layers' projections) are laid out contiguously in layer order,
  cut into 28 equal-byte stages; a stage boundary may fall inside a layer (the report DAG's 27 in-layer
  boundaries).  Within a stage the 4 dies stripe every matrix (tensor parallel 4).  4 HBM3E stacks each (user
  decision 2026-09-27) hold KV and index keys.
* HEAD GROUP (4 dies, stage 28): lm_head and token embedding (BF16, vocabulary-split 4 ways), and the DSpark
  MTP drafter (3 blocks, 128-expert MoE, main_proj, Markov/confidence heads), whose draft chain starts at the
  lm_head output; these dies keep the layer engines (the draft runs a sliding-window layer span) and 4 HBM3E
  stacks each like the layer dies (spec owner, rack conflict C10): the drafter's per-user window KV (3 blocks x 128
  rows x 528 B) is 1.4 MB per die at the 28-user fill -- SRAM -- but 52 MB per die at the spec's 1,024-user
  saturation point, and one package type keeps the 29 stage modules identical.  Aligned with the codex rack
  (b667bf38) in every other respect: embedding on the head dies, 72 table dies off the ring.
* ENGRAM DIES (72): the two Engram tables (FP8 + 8 UE8M0 per row); gather slices and the assembler only
  (R-U1), no HBM, no layer engines.  The embedding quarters sit beside the head's vocabulary quarters so
  the next-token row returns directly over the ring.  Engram bytes that do not fit on the table dies fill
  spare ROM on the head and layer dies (prefetched within the >= 3.57 us slack).
"""
import argparse
import collections
import json
import math
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = Path("/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/"
            "dba1be0a40aa45a94ad051997016db3960a90277")
CFG = ROOT / "configs/models/candidates/deepseek-v4.1-flash.json"
BUDGET = ROOT / "results/arch/arch_budget_v41.json"
OUT = ROOT / "results/arch/v41_die_placement.json"
SIZE = {"BF16": 2, "F16": 2, "F32": 4, "F8_E4M3": 1, "F8_E8M0": 1, "I8": 1}
DIES, STAGES, GROUP, HEAD_DIES = 188, 28, 4, 4
STACKS_LAYER_DIE = 4


def header_bytes(snap):
    per = collections.Counter()
    for f in sorted(snap.glob("*.safetensors")):
        with open(f, "rb") as fh:
            n = struct.unpack("<Q", fh.read(8))[0]
            h = json.loads(fh.read(n))
        for k, v in h.items():
            if k == "__metadata__":
                continue
            b = math.prod(v["shape"]) * SIZE.get(v["dtype"], 1)
            m = re.match(r"layers\.(\d+)\.(.*)", k)
            if m:
                key = f"engram_table_L{m.group(1)}" if m.group(2).startswith("engram.embed") else f"layer_{int(m.group(1))}"
            elif k.startswith("mtp."):
                key = "mtp"
            elif k.startswith("embed."):
                key = "embed"
            elif k.startswith("head."):
                key = "head"
            elif k.startswith(("vision.", "aligner.", "image_")):
                key = "vision_unused"
            else:
                key = "other"
            per[key] += b
    return per


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot", type=Path, default=SNAP)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    cfg = json.loads(CFG.read_text())
    cap = cfg["checkpoint_bytes"] / DIES                     # per-die ROM, the report's placement
    per = header_bytes(a.snapshot)
    L = cfg.get("num_layers", 40)
    layer_b = [per[f"layer_{i}"] for i in range(L)]
    other_small = per["other"]                               # final norm etc.: on the last stage
    layer_total = sum(layer_b) + other_small
    stage_b = layer_total / STAGES
    # --- layer dies: contiguous cut into 28 equal-byte stages ------------------------------------------------------
    stages = []
    cum = 0.0
    bounds = [0.0]
    for b in layer_b:
        cum += b
        bounds.append(cum)
    for s in range(STAGES):
        lo, hi = s * stage_b, min((s + 1) * stage_b, sum(layer_b))
        frags = []
        for i in range(L):
            a0, a1 = bounds[i], bounds[i + 1]
            ov = min(a1, hi) - max(a0, lo)
            if ov > 1:
                frags.append(dict(layer=i, fraction=ov / layer_b[i], bytes=ov))
        stages.append(dict(stage=s, layers=frags, bytes=hi - lo + (other_small if s == STAGES - 1 else 0.0)))
    layer_die_spare = [cap - st["bytes"] / GROUP for st in stages]
    # --- head group: lm_head + DSpark -------------------------------------------------------------------------------
    head_bytes = per["head"] + per["mtp"] + per["embed"]
    head_die_spare = cap - head_bytes / HEAD_DIES
    # --- Engram dies --------------------------------------------------------------------------------------------------
    n_eg = DIES - STAGES * GROUP - HEAD_DIES
    tables = sorted(k for k in per if k.startswith("engram_table_"))
    engram_total = sum(per[t] for t in tables)
    eg_capacity = n_eg * cap
    spill = max(0.0, engram_total - eg_capacity)
    spill_head = min(spill, max(0.0, head_die_spare) * HEAD_DIES)
    spill_layer = spill - spill_head
    layer_spare_total = sum(max(0.0, x) for x in layer_die_spare) * GROUP
    dies = []
    for st in stages:
        for j in range(GROUP):
            d = 4 * st["stage"] + j
            dies.append(dict(die=d, role="layer", stage=st["stage"], tensor_group=st["stage"], rank=j,
                             package=d // 2, layers=[dict(layer=f["layer"], fraction=round(f["fraction"], 4))
                                                     for f in st["layers"]],
                             weight_bytes=st["bytes"] / GROUP,
                             engram_spill_bytes=spill_layer / (STAGES * GROUP),
                             hbm_stacks=STACKS_LAYER_DIE,
                             engines="block-dot pool + BF16 pool + vector unit + HC + select + one-shot (R-U2)"))
    base = STAGES * GROUP
    for j in range(HEAD_DIES):
        dies.append(dict(die=base + j, role="head+dspark", stage=STAGES, tensor_group=STAGES, rank=j,
                         package=(base + j) // 2, weight_bytes=head_bytes / HEAD_DIES,
                         holds=f"lm_head and embedding vocabulary quarter {j} (BF16, rows "
                               f"{j * 129280 // 4}..{(j + 1) * 129280 // 4 - 1}); DSpark drafter weights striped 4 ways",
                         embedding_bytes=per["embed"] / HEAD_DIES,
                         engram_spill_bytes=spill_head / HEAD_DIES, hbm_stacks=STACKS_LAYER_DIE,
                         engines="R-L1 4x BF16 engine + block-dot pool (draft MoE) + vector unit + one-shot"))
    base += HEAD_DIES
    # Engram: table rows striped over the dedicated dies in table order (each die a contiguous row range)
    t_bytes = [per[t] for t in tables]
    cum_t = [0.0]
    for b in t_bytes:
        cum_t.append(cum_t[-1] + b)
    on_eg = engram_total - spill                             # the dedicated dies are filled first, in table order
    for j in range(n_eg):
        lo = j * cap
        hi = min(on_eg, lo + cap)
        parts = []
        for ti, t in enumerate(tables):
            ov = min(hi, cum_t[ti + 1]) - max(lo, cum_t[ti])
            if ov > 1:
                parts.append(dict(table=t.replace("engram_table_", "Engram layer "), bytes=ov,
                                  row_fraction=[round((max(lo, cum_t[ti]) - cum_t[ti]) / t_bytes[ti], 5),
                                                round((min(hi, cum_t[ti + 1]) - cum_t[ti]) / t_bytes[ti], 5)]))
        dies.append(dict(die=base + j, role="engram", stage=None,
                         tensor_group=None, package=(base + j) // 2,
                         weight_bytes=sum(p["bytes"] for p in parts),
                         engram=parts, hbm_stacks=0,
                         engines="Engram per-bank gather slices + assembler (R-U1)"))
    rec = dict(schema="opentallas.v41-die-placement.v1", tool="tools/v41_die_placement.py", snapshot=str(a.snapshot),
               dies=DIES, packages=DIES // 2, n_stages=STAGES, group=GROUP, rom_bytes_per_die=cap,
               bytes=dict({k: v for k, v in per.items() if not k.startswith("layer_")}, layers_total=sum(layer_b)),
               counts=dict(layer=STAGES * GROUP, head=HEAD_DIES, engram=n_eg),
               hbm_stacks=dict(per_layer_die=STACKS_LAYER_DIE, per_head_die=STACKS_LAYER_DIE,
                               total=(STAGES * GROUP + HEAD_DIES) * STACKS_LAYER_DIE,
                               per_two_die_package_layer=2 * STACKS_LAYER_DIE),
               engram_spill=dict(total=spill, onto_head_dies=spill_head, onto_layer_dies=spill_layer,
                                 layer_die_spare_total=layer_spare_total, fits=spill_layer <= layer_spare_total + 1),
               min_layer_die_spare_bytes=min(layer_die_spare), head_die_spare_bytes=head_die_spare,
               stages=[dict(stage=s["stage"], layers=[dict(layer=f["layer"], fraction=round(f["fraction"], 4)) for f in s["layers"]],
                            bytes=s["bytes"]) for s in stages],
               die_table=dies,
               notes=["a stage boundary inside a layer splits that layer's routed experts between two groups "
                      "(the report DAG's in-layer boundaries); the attention and dense parts sit with the stage "
                      "that holds the layer's start",
                      "vision/aligner weights (%.2f GB) are not stored: text decode only" % (per["vision_unused"] / 1e9)])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print("per-die ROM %.3f GB; stage %.3f GB (%.3f per die); head die %.3f GB; Engram spill %.2f GB (head %.2f, layer %.2f of %.2f spare)"
          % (cap / 1e9, stage_b / 1e9, stage_b / 4e9, head_bytes / 4e9, spill / 1e9, spill_head / 1e9, spill_layer / 1e9,
             layer_spare_total / 1e9))
    for s in stages:
        print(s["stage"], [(f["layer"], round(f["fraction"], 2)) for f in s["layers"]])


if __name__ == "__main__":
    main()
