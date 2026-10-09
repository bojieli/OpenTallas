#!/usr/bin/env python3
"""Fast self-test of hgi_sim on a tiny synthetic Qwen3 (random BF16 weights, TP4 shapes scaled down): records
round-trip, CFG commit, every Qwen family's result buffer equal to the qwen_r25 golden, mutants failing.

    python3 -m hgi_sim.test_tiny          (from tools/; seconds, no checkpoint)
"""
from __future__ import annotations

import json
import struct
import sys
import tempfile
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

CFG = dict(architectures=["Qwen3ForCausalLM"], num_hidden_layers=2, hidden_size=256, num_attention_heads=8,
           num_key_value_heads=4, head_dim=128, intermediate_size=512, vocab_size=1024, rms_norm_eps=1e-6,
           rope_theta=1000000.0, tie_word_embeddings=False, max_position_embeddings=40960)


def write_snapshot(d: Path, seed=0):
    rng = np.random.default_rng(seed)
    c = CFG
    H, NH, KV, HD, FF, V = (c[k] for k in ("hidden_size", "num_attention_heads", "num_key_value_heads", "head_dim",
                                           "intermediate_size", "vocab_size"))
    t = {"model.embed_tokens.weight": (V, H), "lm_head.weight": (V, H), "model.norm.weight": (H,)}
    for i in range(c["num_hidden_layers"]):
        p = f"model.layers.{i}."
        t.update({p + "input_layernorm.weight": (H,), p + "post_attention_layernorm.weight": (H,),
                  p + "self_attn.q_proj.weight": (NH * HD, H), p + "self_attn.k_proj.weight": (KV * HD, H),
                  p + "self_attn.v_proj.weight": (KV * HD, H), p + "self_attn.o_proj.weight": (H, NH * HD),
                  p + "self_attn.q_norm.weight": (HD,), p + "self_attn.k_norm.weight": (HD,),
                  p + "mlp.gate_proj.weight": (FF, H), p + "mlp.up_proj.weight": (FF, H),
                  p + "mlp.down_proj.weight": (H, FF)})
    hdr, blobs, off = {}, [], 0
    for name, shape in t.items():
        if len(shape) == 1:
            a = rng.uniform(0.5, 1.5, shape).astype(np.float32)
        else:
            a = (rng.standard_normal(shape) * (0.5 if "embed" in name else 0.05)).astype(np.float32)
        b = (a.view(np.uint32) >> 16).astype(np.uint16).tobytes()
        hdr[name] = dict(dtype="BF16", shape=list(shape), data_offsets=[off, off + len(b)])
        blobs.append(b)
        off += len(b)
    h = json.dumps(hdr).encode()
    h += b" " * (-len(h) % 8)
    (d / "model.safetensors").write_bytes(struct.pack("<Q", len(h)) + h + b"".join(blobs))
    (d / "model.safetensors.index.json").write_text(json.dumps(dict(weight_map={k: "model.safetensors" for k in t})))
    (d / "config.json").write_text(json.dumps(c))


def main():
    import qwen_r25_golden as R
    from hgi_sim import qwen_proof as QP
    tmp = Path(tempfile.mkdtemp(prefix="hgi_tiny_"))
    write_snapshot(tmp)
    model = R.QwenR25(tmp, tmp / "img")
    ok = True
    for stage, layer, pos in (("layer", 0, 63), ("layer", 1, 40), ("head", 0, 0)):
        r = QP.run_stage(model, model.ck.cfg, stage, layer, pos)
        print(stage, layer, pos, "PASS" if r["pass_"] else f"FAIL {r.get('fault')} {r.get('failures')}",
              r.get("families"))
        ok &= r["pass_"]
    for mu in ("rope_adjacent", "kv_swap", "qknorm_bf16"):
        r = QP.run_stage(model, model.ck.cfg, "layer", 0, 63, mutant=mu)
        print("mutant", mu, "fails as required" if not r["pass_"] else "NOT DETECTED",
              sorted({f["family"] for f in r.get("failures", [])})[:4])
        ok &= not r["pass_"]
    print("ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
