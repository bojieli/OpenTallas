#!/usr/bin/env python3
"""ROM-WEIGHTS-1119 (11-24): WEIGHTS-ONLY S81 stage fixtures -- the real checkpoint content of one TP4 rank die of
one stage of the S81 release stage map, with no w17 golden shard.

The stage map of record is the one the S81 die plan binds (physical/die_plan/s81/inputs/plan.json facts.stage_map):
results/arch/s81_map72_1021/r2_241/stage_map_f72r224gpq_241.json -- 241 TP4 stages on the 72-frame die, DENSE2 split
(a dense layer's a_proj rows [0,R) on the upstream "A" stage, the rest of the layer on "B"; "X" = experts only), every
stage with an exact xs_capacity PASS.  A stage = (optional) dense part of `dense_layer` + ONE contiguous expert range
[L, a, b] (L may differ from dense_layer: an A stage holds layer L+1's a_proj rows and the tail experts of layer L).

dv_layer_fixtures.py builds a golden-checked fixture of one layer at one token (its six routed experts, golden
activations).  This tool writes the fixture of a STAGE die in the same layout xs_place.py reads:

  weights/<k>.bin   the rank's raw checkpoint slices (rtl_v41_fullshape_layer_campaign.die_slices: the split and the
                    bytes dv_layer_fixtures.weights() writes); dense slices of dense_layer only as the DENSE2 half
                    needs them (A: wq_a + wkv, the a_proj tensors; B / unsplit: every dense slice; X: none), routed
                    experts = the stage's range (on its own layer)
  ops/<op>.bin      the x vectors the return planner reads: SYNTHETIC, declared in meta.x_policy (seeded N(0, 0.25)
                    FP32 at the released shape).  ROM weight CONTENT does not depend on them (the image writer copies
                    checkpoint bytes); the planner's merge scoring does, so the placement is "legalised under x_policy"
  meta.json         stage, spec (xs_capacity spec_ops / spec_env inputs), experts, layers, x_policy, tp_split, pins
  files.json, ops.json, manifest.sha256

    OT_V41_FLASH_SNAPSHOT=<ckpt> python3 -I tools/s81_dv/layer_prog/stage_fixtures.py --stage R000 --rank 0 --out DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import zlib
from collections import OrderedDict
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
for p in ("tools", "tools/s81_dv", "tools/s81_dv/layer_prog"):
    sys.path.insert(0, str(ROOT / p))

SCHEMA = "opentallas.s81_dv.stage_fixture.v1"
MAP_DEFAULT = ROOT / "results/arch/s81_map72_1021/r2_241/stage_map_f72r224gpq_241.json"
X_SEED = 20261124
X_POLICY = f"synthetic N(0,0.25) fp32 per op, numpy default_rng({X_SEED} + crc32(op)); weights-only image mode"
TP = 4
APROJ = ("wq_a", "wq_a.scale", "wkv", "wkv.scale")


def map_path(p=None):
    return Path(p or os.environ.get("OT_XS_STAGE_MAP") or MAP_DEFAULT)


def stage_record(stage, path=None):
    d = json.loads(map_path(path).read_text())
    for s in d["stages"]:
        if s["stage"] == stage:
            return s, d
    raise KeyError(stage)


def stage_spec(s):
    """the xs_capacity spec of a stage record (spec_ops / spec_env / FixN inputs, as the capacity verdict ran it)"""
    cap = s.get("capacity", {})
    spec = dict(id=s.get("spec"), dense_layer=s.get("dense_layer"), experts=int(s.get("n_experts", 0)))
    if s.get("dense_split2") is not None:
        spec["dense_split2"] = s["dense_split2"]
        spec["dense_split2_rows"] = cap.get("dense_split2_rows")
    return spec


def stage_experts(s):
    out = []
    for L, a, b in s["experts"]:
        out += [(L, e) for e in range(a, b + 1)]
    assert len({L for L, _ in out}) <= 1, ("one expert layer a stage", s["stage"])
    return out


def dense_keep(spec, name):
    """which non-expert die_slices entries the stage die holds"""
    if spec.get("dense_layer") is None:
        return False
    if spec.get("dense_split2") == "A":
        return name in APROJ
    return True


def x_shapes(m, experts, spec):
    """released shape of every x vector op_groups / lower_xs / xs_bf read (FP32)"""
    sh = {"ffn.norm.scale": (m.dim,)}
    for e in experts:
        sh[f"ffn.experts.{e}.route_w"] = (2304,)
    if spec.get("dense_layer") is not None:
        sh.update({"attn.norm.scale": (m.dim,), "attn.a_proj": (1280 + m.hd,)})
        if spec.get("dense_split2") != "A":
            sh.update({"attn.q_norm.scale": (1280,), "attn.wo_a": (m.groups * m.o_rank,),
                       "ffn.shared.swiglu": (2304,), "attn.normalize.unrope": (m.heads * m.hd,)})
    return sh


def synth_x(op, shape):
    rng = np.random.default_rng(X_SEED + zlib.crc32(op.encode()))
    return (rng.standard_normal(shape) * 0.25).astype(np.float32)


def sha_b(b):
    return hashlib.sha256(b).hexdigest()


def gen(stage, rank, out, path=None, ck=None):
    import dv_layer_fixtures as DF
    import rtl_v41_fullshape_layer_campaign as LC
    import xs_capacity as XC
    s, doc = stage_record(stage, path)
    spec = stage_spec(s)
    xs, bf, _ = XC.spec_ops(spec)
    lx = stage_experts(s)
    experts = [e for _, e in lx]
    ck = ck or LC.Checkpoint(LC.HF)
    m, init_sha = LC.build_model(ck, engram=False)
    o = DF.Out(Path(out))
    sl = dict(tp=TP, dim=m.dim, hd=m.hd, heads=m.heads, q_rank=1280, o_groups=m.groups, o_rank=m.o_rank,
              n_exp=m.n_exp, moe_ff=2304, hc=m.hc, ratio=m.ratio)
    LC.R_KV_SRC, LC.R_IDX_SRC = (lambda: m.kv_src), (lambda: m.idx_src)
    D = spec.get("dense_layer")
    if D is not None:
        if D in (1, 14) and spec.get("dense_split2") != "A":
            raise SystemExit(f"{stage}: Engram dense layer {D} (eng.wkv x) is not in the weights-only mode yet")
        for name, tensor, rows, cols in LC.die_slices(D, rank, sl, [], False):
            if dense_keep(spec, name):
                a, dt = LC._raw(ck, tensor, rows, cols)
                o.put(f"weights/{name}.bin", a, tensor=tensor, rows=rows, cols=cols, format=dt)
    if lx:
        EL = lx[0][0]
        for name, tensor, rows, cols in LC.die_slices(EL, rank, sl, experts, False):
            if name.startswith("exp"):
                a, dt = LC._raw(ck, tensor, rows, cols)
                o.put(f"weights/{name}.bin", a, tensor=tensor, rows=rows, cols=cols, format=dt)
    ops = OrderedDict()
    for op, shp in x_shapes(m, experts, spec).items():
        ops[op] = o.put(f"ops/{op}.bin", synth_x(op, shp), note="synthetic x (meta.x_policy)")
    shared = D is not None and spec.get("dense_split2") != "A"
    meta = OrderedDict(schema=SCHEMA, stage=stage, spec=spec, layer=f"L{D if D is not None else lx[0][0]}",
                       layer_index=D, expert_layer=lx[0][0] if lx else None, layers=s["layers"], rank=rank, tp=TP,
                       experts=experts, shared=shared, xs_ops=xs, bf_ops=bf, x_policy=X_POLICY, weights_only=True,
                       checkpoint=str(LC.HF), golden_init_sha256=init_sha,
                       stage_map=dict(path=str(map_path(path).resolve().relative_to(ROOT)) if str(map_path(path).resolve()).startswith(str(ROOT)) else str(map_path(path)),
                                      sha256=sha_b(map_path(path).read_bytes())),
                       tp_split=DF.tp_split(m), sources=DF.src_pins(),
                       command=f"python3 -I tools/s81_dv/layer_prog/stage_fixtures.py --stage {stage} --rank {rank} --out DIR")
    o.text("ops.json", json.dumps(ops, indent=1) + "\n")
    o.text("files.json", json.dumps(o.files, indent=1) + "\n")
    o.text("meta.json", json.dumps(meta, indent=1, default=str) + "\n")
    o.manifest()
    return dict(dir=str(out), stage=stage, rank=rank, spec=spec, experts=len(experts), files=len(o.files))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--rank", type=int, choices=range(TP), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--stage-map", type=Path, default=None)
    a = ap.parse_args(argv)
    print(json.dumps(gen(a.stage, a.rank, a.out, a.stage_map)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
