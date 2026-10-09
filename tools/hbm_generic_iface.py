#!/usr/bin/env python3
"""HGI-1: the generic HBM-die interface (docs/HBM_GENERIC_INTERFACE.md), reference encoder and validator.

One table, three uses:
  * SPEC: every field of the model descriptor (MD), the program record header (UOP), the memory descriptor
    (MDESC) and the SU template (SUT), with bit positions, legal values and the consuming block;
  * encode(): the 64-word MD for a model, from its HF config.json plus the deployment (TP size, head shard);
    section C (the only words hardware reads) is DERIVED here, never by hardware;
  * validate(): the checks the command processor does at CFG_COMMIT (magic, version, CRC, reserved bits, legal
    mode values) plus the software-only check that section C equals derive(sections A/B).

    python3 tools/hbm_generic_iface.py --out results/arch/hbm_generic_iface_20261009
    python3 tools/hbm_generic_iface.py --check results/arch/hbm_generic_iface_20261009

The DS descriptor's section C must equal the reset values (DS behaviour): loading it is a no-op for every block.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (0, 9)
MAGIC = 0x31494748                     # "HGI1" little-endian
NWORDS = 64
CRC_WORD = 63

MODELS = {
    "ds_v41_flash": dict(cfg="compiler/models/deepseek-v4.1-flash/config.json", model_class=1, tp=96, head_rows=0),
    "qwen3_8b": dict(cfg="compiler/models/qwen3-8b/config.json", model_class=2, tp=4, head_rows=37984),
}

# enum encodings ----------------------------------------------------------------------------------------------
FMT = {"FP32": 0, "BF16": 1, "FP8E4M3": 2, "FP4E2M1": 3, "INT8": 4, "U32": 5, "UE8M0": 6}
SCALE = {"NONE": 0, "ROW_BF16": 1, "BLOCK_UE8M0": 2}
ROPE_PAIR = {"ADJACENT": 0, "HALF": 1}
ROPE_SCALING = {"NONE": 0, "YARN": 1}
FEATURES = ["MOE", "INDEXER", "HC", "ENGRAM", "MTP", "QK_NORM", "ATTN_SINK", "KV_COMPRESS", "SHARED_LATENT_KV",
            "Q_LORA", "O_GROUPS", "SWIGLU_CLAMP"]

# MD fields: (name, word, lsb, width, kind, consumer, why).  kind: u (unsigned), f32 (IEEE bits), enum, flags.
# Section A/B (words 0-39) are read by software (compiler, golden, simulator, validator); hardware reads only the
# header (0-1), section C (40-55), section D (56-62) and the CRC (63).
MD_FIELDS = [
    # section A: header
    ("magic", 0, 0, 32, "u", "cp", "reject a non-HGI image"),
    ("ver_minor", 1, 0, 8, "u", "cp", "reject an incompatible layout"),
    ("ver_major", 1, 8, 8, "u", "cp", "reject an incompatible layout"),
    ("n_words", 1, 16, 8, "u", "cp", "fixed 64; guards a truncated load"),
    ("model_class", 2, 0, 8, "u", "sw", "1 DeepSeek-V4.1-Flash, 2 Qwen3 dense; names the golden"),
    ("features", 3, 0, 12, "flags", "sw", "which operator families the program contains (bit order FEATURES)"),
    # section B: model geometry (software only)
    ("hidden", 4, 0, 16, "u", "sw", "residual width"),
    ("layers", 4, 16, 8, "u", "sw", "backbone layers"),
    ("mtp_layers", 4, 24, 4, "u", "sw", "built-in draft layers (DSpark 3)"),
    ("q_heads", 5, 0, 8, "u", "sw", "attention heads"),
    ("kv_heads", 5, 8, 8, "u", "sw", "KV heads (1 = shared latent / MQA)"),
    ("head_dim", 5, 16, 12, "u", "sw", "per-head width"),
    ("vocab", 6, 0, 18, "u", "sw", "vocabulary (151,936 needs 18 bits)"),
    ("ffn_inter", 7, 0, 16, "u", "sw", "dense FFN width (0 = none)"),
    ("moe_inter", 7, 16, 16, "u", "sw", "expert FFN width (0 = none)"),
    ("norm_type", 8, 0, 2, "u", "sw", "0 RMSNorm"),
    ("act", 8, 2, 2, "u", "sw", "0 SiLU-gated (SwiGLU)"),
    ("norm_eps", 9, 0, 32, "f32", "sw", "RMSNorm eps (DS 1e-20, Qwen 1e-6), an SU template immediate"),
    ("rope_pair", 10, 0, 2, "enum", "sw", "0 adjacent (2i, 2i+1), 1 half (i, i + dims/2)"),
    ("rope_dims", 10, 2, 10, "u", "sw", "rotated dims per head (DS 64, Qwen 128)"),
    ("rope_offset", 10, 12, 10, "u", "sw", "first rotated dim (DS head_dim - 64, Qwen 0)"),
    ("rope_scaling", 10, 22, 2, "enum", "sw", "0 none, 1 YaRN; only the host's table generator reads it"),
    ("rope_theta", 11, 0, 32, "f32", "sw", "table generator only"),
    ("rope_factor", 12, 0, 32, "f32", "sw", "YaRN factor (0 = none); table generator only"),
    ("yarn_beta_fast", 13, 0, 8, "u", "sw", "table generator only"),
    ("yarn_beta_slow", 13, 8, 8, "u", "sw", "table generator only"),
    ("yarn_orig_log2", 13, 16, 6, "u", "sw", "log2 original max positions; table generator only"),
    ("compress_rope_theta", 14, 0, 32, "f32", "sw", "DS compressed-KV RoPE tables; table generator only"),
    ("window", 15, 0, 17, "u", "sw", "sliding window rows (0 = dense)"),
    ("ctx_max", 16, 0, 21, "u", "sw", "deployed context (positions)"),
    ("attn_scale", 17, 0, 32, "f32", "sw", "softmax scale literal of the golden (an SU immediate, never folded)"),
    ("swiglu_limit", 18, 0, 32, "f32", "sw", "SwiGLU clamp (0 = none)"),
    ("weight_fmt", 19, 0, 3, "enum", "sw", "dense weight format"),
    ("kv_fmt", 19, 3, 3, "enum", "sw", "KV cache format"),
    ("act_quant", 19, 6, 3, "enum", "sw", "matvec activation format (FP8 block for DS, BF16 for Qwen)"),
    ("scale_kind", 19, 9, 3, "enum", "sw", "weight scale: none / per-row BF16 / UE8M0 block"),
    ("wblock", 19, 12, 6, "u", "sw", "weight block size (DS 32)"),
    ("expert_fmt", 19, 18, 3, "enum", "sw", "expert weight format (DS FP4)"),
    ("n_routed", 20, 0, 10, "u", "sw", "MoE routed experts"),
    ("n_shared", 20, 10, 3, "u", "sw", "MoE shared experts"),
    ("moe_topk", 20, 13, 4, "u", "sw", "experts per token"),
    ("moe_scoring", 20, 17, 2, "u", "sw", "0 softmax, 1 sqrt(softplus)"),
    ("moe_norm_topk", 20, 19, 1, "u", "sw", "normalise top-k weights"),
    ("routed_scaling", 21, 0, 32, "f32", "sw", "routed scaling factor"),
    ("idx_heads", 22, 0, 8, "u", "sw", "indexer heads"),
    ("idx_head_dim", 22, 8, 10, "u", "sw", "indexer head dim"),
    ("idx_topk", 22, 18, 12, "u", "sw", "indexer top-k"),
    ("cand_topk_blocks", 23, 0, 12, "u", "sw", "candidate blocks"),
    ("cand_block", 23, 12, 6, "u", "sw", "candidate block size"),
    ("cand_src_layer", 23, 18, 8, "u", "sw", "candidate source layer"),
    ("hc_mult", 24, 0, 4, "u", "sw", "hyper-connection copies"),
    ("hc_sinkhorn_iters", 24, 4, 6, "u", "sw", "Sinkhorn iterations"),
    ("hc_eps", 25, 0, 32, "f32", "sw", "Sinkhorn eps"),
    ("engram_heads", 26, 0, 4, "u", "sw", "Engram heads"),
    ("engram_head_dim", 26, 4, 10, "u", "sw", "Engram head dim"),
    ("engram_max_ngram", 26, 14, 3, "u", "sw", "Engram n-gram order"),
    ("engram_layers", 26, 17, 3, "u", "sw", "Engram layer count (ids in the config)"),
    ("mtp_kind", 27, 0, 2, "u", "sw", "0 none, 1 DSpark"),
    ("mtp_block", 27, 2, 4, "u", "sw", "draft block"),
    ("mtp_markov_rank", 27, 6, 10, "u", "sw", "DSpark Markov rank"),
    ("mtp_experts", 27, 16, 9, "u", "sw", "draft routed experts"),
    ("mtp_topk", 27, 25, 4, "u", "sw", "draft experts per token"),
    ("mtp_noise_token", 28, 0, 18, "u", "sw", "DSpark noise token"),
    ("q_lora", 29, 0, 12, "u", "sw", "q LoRA rank"),
    ("o_lora", 29, 12, 12, "u", "sw", "o LoRA rank"),
    ("o_groups", 29, 24, 4, "u", "sw", "o groups"),
    ("tp_size", 30, 0, 8, "u", "sw", "dies in the tensor-parallel group"),
    ("cfg_sha256", 32, 0, 256, "u", "sw", "sha256 of the model config.json (words 32-39): binds MD to one model"),
    # section C: BLOCK MODE WORDS (hardware).  Reset value = DS behaviour.  Exactly the approved parameter list
    # (hbm-generic PLAN.md + REVIEW_20261009 addendum); token width 18, SM fmt3 and per-PC KV striping need no field.
    ("cp_vocab", 40, 0, 18, "u", "hfd_cmdproc", "doorbell / completion token range check (width is 18 everywhere)"),
    ("cp_ctx_max", 41, 0, 21, "u", "hfd_cmdproc", "doorbell position range check"),
    ("rope_half", 42, 0, 1, "u", "RoPE chains (hfd_su q/kv)", "0 adjacent pairs (2i, 2i+1); 1 split-half (i, i + dims/2)"),
    ("rope_rot_log2", 42, 1, 3, "u", "RoPE chains (hfd_su q/kv)", "rotated dims: 6 = 64-dim tail (DS), 7 = 128 (Qwen)"),
    ("norm_d_units", 43, 0, 6, "u", "norm engine", "vector width / 128: 40 (D5120, DS) or 32 (D4096); zero-padded tree is exact"),
    ("norm_hc_off", 43, 6, 1, "u", "norm engine", "1 skips the hc_pre mix"),
    ("norm_out_bf16", 43, 7, 1, "u", "norm engine", "0 FP8 publish (DS), 1 BF16"),
    ("sfx_sink_off", 44, 0, 1, "u", "ot_dsrom_su_softmax", "1 drops the sink term from max and denominator"),
    ("sfx_multipass", 44, 1, 1, "u", "ot_dsrom_su_softmax", "1 rows > NVMAX*LPH: global max, fixed 640-row chunks exp+sum carried in, then scale"),
    ("glu_out_bf16", 45, 0, 1, "u", "SwiGLU fused chain", "0 FP8 publish quant (DS), 1 BF16"),
    ("glu_clamp_off", 45, 1, 1, "u", "SwiGLU fused chain", "1 skips the swiglu_limit clamp"),
    ("glu_routew_off", 45, 2, 1, "u", "SwiGLU fused chain", "1 skips the route-weight multiply (= x 1.0, exact)"),
    ("coll_group_size", 46, 0, 8, "u", "hfd_coll", "4, 8 or 96 dies; groups aligned: rank = die_id mod size, owner order = rank order"),
    ("coll_head_rows", 46, 8, 18, "u", "hfd_coll", "argmax select: global id = rank * rows + local id (0: ids already global, DS)"),
    ("kv_dense", 47, 0, 1, "u", "hfd_kvwb_native, hfd_host_ingest, causal mask", "0 DS (window ring / selected rows / ROWS+IKEY ingest); 1 dense per-head linear [l][kvh][K|V][pos][hd] FP8, cache-length mask, QKV NHD ingest"),
    ("emb_int8", 48, 0, 1, "u", "embedding fetch (svc row + SU)", "0 BF16 rows (DS); 1 INT8 rows + BF16 row scale"),
    ("emb_row_bytes", 48, 1, 16, "u", "embedding fetch (svc row + SU)", "embedding row stride, 32 B aligned (DS 10,240 BF16; Qwen 4,128 = 4,096 codes + BF16 scale + pad)"),
    # section D: program entry points and image placement (hardware: the CP fetch)
    ("entry_ar", 56, 0, 32, "u", "hfd_cmdproc", "AR decode step: record offset in the image (16 B units)"),
    ("entry_verify", 57, 0, 32, "u", "hfd_cmdproc", "MTP verify pass (0 = absent)"),
    ("entry_draft", 58, 0, 32, "u", "hfd_cmdproc", "MTP draft pass (0 = absent)"),
    ("image_base", 60, 0, 28, "u", "hfd_cmdproc", "program image in HBM, 4 KiB pages"),
    ("image_pages", 61, 0, 28, "u", "hfd_cmdproc", "program image size, 4 KiB pages"),
    ("crc32", 63, 0, 32, "u", "hfd_cmdproc", "IEEE CRC-32 of words 0..62"),
]
FIELD = {f[0]: f for f in MD_FIELDS}
RESET = dict(cp_vocab=129280, cp_ctx_max=1 << 20, rope_half=0, rope_rot_log2=6, norm_d_units=40, norm_hc_off=0,
             norm_out_bf16=0, sfx_sink_off=0, sfx_multipass=0, glu_out_bf16=0, glu_clamp_off=0, glu_routew_off=0,
             coll_group_size=96, coll_head_rows=0, kv_dense=0, emb_int8=0, emb_row_bytes=10240)
LEGAL = dict(cp_vocab=(1, 1 << 18), cp_ctx_max=(1, 1 << 20), rope_half=(0, 1), rope_rot_log2={6, 7},
             norm_d_units={32, 40}, norm_hc_off=(0, 1), norm_out_bf16=(0, 1), sfx_sink_off=(0, 1), sfx_multipass=(0, 1),
             glu_out_bf16=(0, 1), glu_clamp_off=(0, 1), glu_routew_off=(0, 1), coll_group_size={4, 8, 96},
             coll_head_rows=(0, (1 << 18) - 1), kv_dense=(0, 1), emb_int8=(0, 1), emb_row_bytes=(1, 65535))
HW_WORDS = sorted({f[1] for f in MD_FIELDS if f[5] != "sw"})
ERR = {0: "OK", 1: "E_MAGIC", 2: "E_VERSION", 3: "E_CRC", 4: "E_BUSY", 5: "E_RANGE", 6: "E_RESERVED"}

# program record header (UOP, 128 bits) -----------------------------------------------------------------------
UNITS = ["CTL", "SM", "SU", "SFU", "FUSED", "ATT", "COLL", "ARGMAX", "DMA", "IDX", "HC", "SIMT"]
UOP_FIELDS = [  # (name, lsb, width)
    ("imm_b", 0, 32), ("imm_a", 32, 32), ("param", 64, 32), ("slot", 96, 3), ("tmpl", 99, 1),
    ("opnd", 100, 4), ("pred", 104, 2), ("wait", 106, 12), ("op", 118, 6), ("unit", 124, 4),
]
OPS = {
    "CTL": ["NOP", "LOOP", "ENDLOOP", "END", "FENCE", "TOKX", "AMAX", "ACCEPT"],
    "SM": ["MATVEC"],
    "SU": ["VOP"],
    "SFU": ["GLU"],
    "FUSED": ["HC_PRE_NORM", "ROW_NORM", "HC_POST"],
    "ATT": ["QK", "PV"],
    "COLL": ["ALL_REDUCE_SUM", "ALL_GATHER", "TOPK_MERGE", "ARGMAX_MERGE"],
    "ARGMAX": ["LOCAL"],
    "DMA": ["LOAD", "STORE", "FENCE"],
    "IDX": ["INDEX_Q", "INDEX_SCORES", "TOPK_LOCAL", "SELECT"],
    "HC": ["HC_MIX"],
    "SIMT": ["RUN"],
}
PRED = ["ALWAYS", "POS0", "NOT_POS0", "LAST_ITER"]
# memory descriptor (MDESC, 256 bits)
MDESC_FIELDS = [
    ("space", 0, 2), ("fmt", 2, 3), ("base", 8, 40), ("n", 48, 20), ("m", 68, 20), ("stride", 88, 32),
    ("istride", 120, 16), ("lstride", 136, 32), ("dyn_sel", 168, 5), ("dyn_mul", 173, 27), ("n_sel", 200, 5),
]
SPACE = ["HBM", "VM", "STREAM", "NONE"]
DYN = ["ZERO", "POS", "POS1", "TOKEN", "L", "RANK", "SLOT", "POS_SLOT"]
# SU template (SUT, 256 bits): the pipeline fields of tools/hdc_isa_v41.py (semantics: hdc_program_v41.Machine.su1)
SUT_FIELDS = [
    ("a_src", 2), ("a_ind", 2), ("b_src", 2), ("b_half", 1), ("c_src", 2), ("c_pair", 1), ("d_src", 2),
    ("a_rnd", 1), ("a_relu", 1), ("a_min", 1), ("c_clip", 1), ("m1", 3), ("m2", 2), ("qm", 3), ("ad", 3),
    ("sfu", 3), ("e1", 3), ("e2", 2), ("rnd", 1), ("dst", 2), ("red", 2), ("red_sq", 1), ("red_whole", 1),
    ("red_rnd", 1), ("su_vec", 2), ("red_tree", 1), ("imm1", 32), ("imm2", 32), ("imm3", 32),
]


def f32bits(x):
    return struct.unpack("<I", struct.pack("<f", float(x)))[0]


def derive(md):
    """Section C from sections A/B plus the deployment: the ONLY place block modes are computed."""
    dense = md["kv_heads"] > 1                       # per-head KV (GQA) rather than one shared latent
    int8 = md["weight_fmt"] == FMT["INT8"]
    return dict(
        cp_vocab=md["vocab"], cp_ctx_max=md["ctx_max"],
        rope_half=int(md["rope_pair"] == ROPE_PAIR["HALF"]), rope_rot_log2=md["rope_dims"].bit_length() - 1,
        norm_d_units=md["hidden"] // 128, norm_hc_off=int(md["hc_mult"] == 0), norm_out_bf16=int(md["act_quant"] == FMT["BF16"]),
        sfx_sink_off=int(not md["features"] >> FEATURES.index("ATTN_SINK") & 1), sfx_multipass=int(md["window"] == 0),
        glu_out_bf16=int(md["act_quant"] == FMT["BF16"]), glu_clamp_off=int(md["swiglu_limit"] == 0),
        glu_routew_off=int(md["n_routed"] == 0),
        coll_group_size=md["tp_size"], coll_head_rows=md["_head_rows"],
        kv_dense=int(dense), emb_int8=int(int8), emb_row_bytes=-(-(md["hidden"] * (1 if int8 else 2) + (2 if int8 else 0)) // 32) * 32)


def from_config(name):
    spec = MODELS[name]
    raw = (ROOT / spec["cfg"]).read_bytes()
    c = json.loads(raw)
    t = c.get("text_config", c)
    ds = spec["model_class"] == 1
    feats = set()
    if ds:
        feats |= {"MOE", "INDEXER", "HC", "ENGRAM", "MTP", "ATTN_SINK", "KV_COMPRESS", "SHARED_LATENT_KV", "Q_LORA",
                  "O_GROUPS", "SWIGLU_CLAMP"}
    else:
        feats |= {"QK_NORM"}
    rs = t.get("rope_scaling") or {}
    hd = t["head_dim"]
    rope_dims = t.get("qk_rope_head_dim", hd)
    md = dict(
        magic=MAGIC, ver_minor=VERSION[1], ver_major=VERSION[0], n_words=NWORDS, model_class=spec["model_class"],
        features=sum(1 << FEATURES.index(f) for f in feats),
        hidden=t["hidden_size"], layers=t["num_hidden_layers"], mtp_layers=t.get("num_nextn_predict_layers", 0),
        q_heads=t["num_attention_heads"], kv_heads=t["num_key_value_heads"], head_dim=hd, vocab=t["vocab_size"],
        ffn_inter=0 if ds else t["intermediate_size"], moe_inter=t.get("moe_intermediate_size", 0),
        norm_type=0, act=0, norm_eps=f32bits(t["rms_norm_eps"]),
        rope_pair=ROPE_PAIR["ADJACENT" if ds else "HALF"], rope_dims=rope_dims, rope_offset=hd - rope_dims,
        rope_scaling=ROPE_SCALING["YARN" if rs.get("rope_type") == "yarn" else "NONE"],
        rope_theta=f32bits(t["rope_theta"]), rope_factor=f32bits(rs.get("factor", 0.0)),
        yarn_beta_fast=rs.get("beta_fast", 0), yarn_beta_slow=rs.get("beta_slow", 0),
        yarn_orig_log2=(rs.get("original_max_position_embeddings", 1)).bit_length() - 1 if rs else 0,
        compress_rope_theta=f32bits(t.get("compress_rope_theta", 0.0)),
        window=t.get("sliding_window") or 0,
        ctx_max=1 << 20 if ds else 40960,
        attn_scale=f32bits(1.0 / float(hd) ** 0.5),
        swiglu_limit=f32bits(t.get("swiglu_limit", 0.0) or 0.0),
        weight_fmt=FMT["FP8E4M3" if ds else "INT8"], kv_fmt=FMT["FP8E4M3"],
        act_quant=FMT["FP8E4M3" if ds else "BF16"], scale_kind=SCALE["BLOCK_UE8M0" if ds else "ROW_BF16"],
        wblock=32 if ds else 0, expert_fmt=FMT["FP4E2M1" if ds else "FP32"],
        n_routed=t.get("n_routed_experts", 0), n_shared=t.get("n_shared_experts", 0),
        moe_topk=t.get("num_experts_per_tok", 0), moe_scoring=1 if t.get("scoring_func") == "sqrtsoftplus" else 0,
        moe_norm_topk=int(bool(t.get("norm_topk_prob", False))),
        routed_scaling=f32bits(t.get("routed_scaling_factor", 0.0)),
        idx_heads=t.get("index_n_heads", 0), idx_head_dim=t.get("index_head_dim", 0), idx_topk=t.get("index_topk", 0),
        cand_topk_blocks=t.get("candidate_topk_blocks", 0), cand_block=t.get("candidate_block_size", 0),
        cand_src_layer=t.get("candidate_source_layer_id", 0),
        hc_mult=t.get("hc_mult", 0), hc_sinkhorn_iters=t.get("hc_sinkhorn_iters", 0), hc_eps=f32bits(t.get("hc_eps", 0.0)),
        engram_heads=t.get("engram_n_heads", 0), engram_head_dim=t.get("engram_head_dim", 0),
        engram_max_ngram=t.get("engram_max_ngram_size", 0), engram_layers=len(t.get("engram_layer_ids", [])),
        mtp_kind=1 if ds else 0, mtp_block=t.get("dspark_block_size", 0), mtp_markov_rank=t.get("dspark_markov_rank", 0),
        mtp_experts=t.get("dspark_n_routed_experts", 0), mtp_topk=t.get("dspark_num_experts_per_tok", 0),
        mtp_noise_token=t.get("dspark_noise_token_id", 0),
        q_lora=t.get("q_lora_rank", 0), o_lora=t.get("o_lora_rank", 0), o_groups=t.get("o_groups", 0),
        tp_size=spec["tp"], cfg_sha256=int.from_bytes(hashlib.sha256(raw).digest(), "little"),
        entry_ar=1, entry_verify=0, entry_draft=0, image_base=0, image_pages=0, _head_rows=spec["head_rows"],
    )
    md.update(derive(md))
    return md, hashlib.sha256(raw).hexdigest()


def pack(md):
    words = [0] * NWORDS
    for name, w, lsb, width, kind, _, _ in MD_FIELDS:
        if name == "crc32":
            continue
        v = int(md.get(name, 0))
        assert 0 <= v < (1 << width), (name, v)
        if width > 32:
            for k in range(width // 32):
                words[w + k] = (v >> (32 * k)) & 0xFFFFFFFF
        else:
            words[w] |= v << lsb
    words[CRC_WORD] = zlib.crc32(struct.pack("<63I", *words[:63])) & 0xFFFFFFFF
    return words


def unpack(words):
    md = {}
    for name, w, lsb, width, *_ in MD_FIELDS:
        if width > 32:
            md[name] = sum(words[w + k] << (32 * k) for k in range(width // 32))
        else:
            md[name] = (words[w] >> lsb) & ((1 << width) - 1)
    return md


def reserved_mask():
    used = [0] * NWORDS
    for name, w, lsb, width, *_ in MD_FIELDS:
        if width > 32:
            for k in range(width // 32):
                used[w + k] = 0xFFFFFFFF
        else:
            used[w] |= ((1 << width) - 1) << lsb
    return used


def hw_check(words, busy=False):
    """What hfd_cmdproc does at CFG_COMMIT.  Returns an ERR code; on any error the active registers keep their
    previous values (the reset values = DS if never loaded)."""
    if busy:
        return 4
    if words[0] != MAGIC:
        return 1
    if ((words[1] >> 8) & 0xFF, words[1] & 0xFF) != VERSION or ((words[1] >> 16) & 0xFF) != NWORDS:
        return 2
    if zlib.crc32(struct.pack("<63I", *words[:63])) & 0xFFFFFFFF != words[CRC_WORD]:
        return 3
    used = reserved_mask()
    if any(words[w] & ~used[w] & 0xFFFFFFFF for w in HW_WORDS):
        return 6
    md = unpack(words)
    for k, lim in LEGAL.items():
        v = md[k]
        if (v not in lim) if isinstance(lim, set) else not (lim[0] <= v <= lim[1]):
            return 5
    return 0


def sw_check(words):
    md = unpack(words)
    md["_head_rows"] = md["coll_head_rows"]
    want = derive(md)
    bad = {k: (md[k], v) for k, v in want.items() if md[k] != v}
    return bad


def self_test(words):
    """Negative cases for the hardware check (conformance CF-0)."""
    out = {}
    w = list(words); w[0] ^= 1; out["bad_magic"] = hw_check(w)
    w = list(words); w[1] ^= 1; out["bad_version"] = hw_check(w)
    w = list(words); w[9] ^= 1; out["bad_crc"] = hw_check(w)
    out["busy"] = hw_check(words, busy=True)
    w = list(words); w[42] = (w[42] & ~0xE) | (5 << 1); w[63] = zlib.crc32(struct.pack("<63I", *w[:63])); out["rope_rot_5"] = hw_check(w)
    w = list(words); w[42] |= 1 << 31; w[63] = zlib.crc32(struct.pack("<63I", *w[:63])); out["reserved_bit"] = hw_check(w)
    return out


def spec_json():
    return dict(
        schema="opentallas.hbm_generic_iface.v0.9", version=f"{VERSION[0]}.{VERSION[1]}",
        doc="docs/HBM_GENERIC_INTERFACE.md", magic=hex(MAGIC), md_words=NWORDS,
        md_fields=[dict(name=n, word=w, lsb=l, width=wd, kind=k, consumer=c, why=y,
                        reset=RESET.get(n), legal=(sorted(LEGAL[n]) if isinstance(LEGAL.get(n), set) else LEGAL.get(n)))
                   for n, w, l, wd, k, c, y in MD_FIELDS],
        hw_words=HW_WORDS, errors=ERR, features=FEATURES, fmt=FMT, scale_kind=SCALE, rope_pair=ROPE_PAIR,
        uop=dict(bits=128, fields=[dict(name=n, lsb=l, width=w) for n, l, w in UOP_FIELDS], units=UNITS, ops=OPS,
                 pred=PRED, opnd_order=["A", "B", "C", "O"],
                 record="header(16 B) + [SUT 32 B if tmpl] + one MDESC (32 B) per set opnd bit, in A,B,C,O order"),
        mdesc=dict(bits=256, fields=[dict(name=n, lsb=l, width=w) for n, l, w in MDESC_FIELDS], space=SPACE, dyn=DYN,
                   address="base + L*lstride + DYN[dyn_sel]*dyn_mul; HBM bytes (32 B aligned), VM FP32 words"),
        sut=dict(bits=256, fields=[dict(name=n, width=w) for n, w in SUT_FIELDS],
                 semantics="tools/hdc_program_v41.py Machine.su1 (R-ARITH chunk8); c_pair partner i XOR 1 (DS) or i XOR dims/2 (rope_half)"),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--check")
    a = ap.parse_args()
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "spec.json").write_text(json.dumps(spec_json(), indent=1) + "\n")
        summary = {}
        for name in MODELS:
            md, cfg_sha = from_config(name)
            words = pack(md)
            hw, sw = hw_check(words), sw_check(words)
            assert hw == 0 and not sw, (name, hw, sw)
            modes = {k: md[k] for k in RESET}
            ds_noop = all(modes[k] == RESET[k] for k in RESET)
            neg = self_test(words)
            assert neg == dict(bad_magic=1, bad_version=2, bad_crc=3, busy=4, rope_rot_5=5, reserved_bit=6), neg
            (out / f"md_{name}.hex").write_text("".join(f"{x:08x}\n" for x in words))
            (out / f"md_{name}.json").write_text(json.dumps(dict(
                model=name, config=MODELS[name]["cfg"], config_sha256=cfg_sha,
                fields={k: v for k, v in md.items() if not k.startswith("_") and k != "cfg_sha256"},
                block_modes=modes, equals_reset_ds=ds_noop, crc32=hex(words[CRC_WORD]),
                hw_check=ERR[hw], negative_cases={k: ERR[v] for k, v in neg.items()}), indent=1) + "\n")
            summary[name] = dict(block_modes=modes, equals_reset_ds=ds_noop, crc32=hex(words[CRC_WORD]))
        assert summary["ds_v41_flash"]["equals_reset_ds"] and not summary["qwen3_8b"]["equals_reset_ds"]
        print(json.dumps(summary, indent=1))
    if a.check:
        d = Path(a.check)
        assert json.loads((d / "spec.json").read_text()) == json.loads(json.dumps(spec_json())), "spec drift"
        for name in MODELS:
            words = [int(x, 16) for x in (d / f"md_{name}.hex").read_text().split()]
            md, _ = from_config(name)
            assert words == pack(md), f"{name}: descriptor drift"
            assert hw_check(words) == 0 and not sw_check(words), name
        print("hbm_generic_iface: spec and descriptors current")


if __name__ == "__main__":
    sys.exit(main())
