#!/usr/bin/env python3
"""Header-only profiles of candidate LLMs for the ROM-vs-HBM model sweep (2026-10-03).

Reads each checkpoint's config.json, its safetensors index and every shard's
JSON header through the repository's own range-read profiler
(``opentallas.profiling._cached_json`` / ``_shard_header``: two HTTP range
reads per shard, no tensor payload is ever fetched, no model is ever run).
Parameter counts come from header shapes; MXFP4 ``*_blocks`` U8 tensors count
two values per byte and block-scale tensors count none.

Output: one JSON per model under configs/models/candidates/rom_sweep/.  These
are a separate, simpler schema than the ModelProfile files one directory up
(nothing globs this directory), so no existing artifact is touched.

Usage:
  PYTHONPATH=src python3 tools/rom_model_sweep_profile.py --cache-dir <scratch> [--only slug ...]
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from opentallas.profiling import HF_BASE, _cached_json, _shard_header  # noqa: E402

OUT = ROOT / "configs/models/candidates/rom_sweep"

# slug, profiled repo, pinned revision, original repo (license holder), license, family note,
# drafters published on HF (searched 2026-10-03 through the HF model API; none was downloaded or run)
MODELS: list[dict[str, Any]] = [
    dict(slug="qwen3-8b", repo="Qwen/Qwen3-8B", rev="b968826d9c46dd6066d109eabc6255188de91218",
         license="apache-2.0", drafters=dict(dflash="z-lab/Qwen3-8B-DFlash-b16", eagle3="RedHatAI/Qwen3-8B-speculator.eagle3"),
         anchor=True),
    dict(slug="qwen3-14b", repo="Qwen/Qwen3-14B", rev="40c069824f4251a91eefaf281ebe4c544efd3e18", license="apache-2.0",
         drafters=dict(eagle3="RedHatAI/Qwen3-14B-speculator.eagle3")),
    dict(slug="phi-4", repo="microsoft/phi-4", rev="2db69c1c3e91a05d2c64a3185acfbaf36f744e25", license="mit",
         drafters={}),
    dict(slug="mistral-small-3.2-24b", repo="mistralai/Mistral-Small-3.2-24B-Instruct-2506",
         rev="95a6d26c4bfb886c58daf9d3f7332c857cb27b43", license="apache-2.0", drafters={}),
    dict(slug="gemma-3-27b", repo="unsloth/gemma-3-27b-it", rev="7a5a3053dbd5d1d58e48159e87b9df2fc545a49a",
         original="google/gemma-3-27b-it", license="gemma", drafters={},
         mirror_note="google/gemma-3-27b-it is gated; profiled from the ungated byte-identical-shape unsloth mirror"),
    dict(slug="qwen3.8-27b", repo="Qwen/Qwen3.8-27B", rev="1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0", license="apache-2.0",
         drafters=dict(dflash="z-lab/Qwen3.8-27B-DFlash2")),
    dict(slug="gemma-4-31b", repo="google/gemma-4-31B-it", rev="842da3794eaa0b77d5f08bae87a17459d91ff475",
         license="apache-2.0",
         drafters=dict(dflash="z-lab/gemma-4-31B-it-DFlash", eagle3="RedHatAI/gemma-4-31B-it-speculator.eagle3")),
    dict(slug="qwen3-32b", repo="Qwen/Qwen3-32B", rev="9216db5781bf21249d130ec9da846c4624c16137", license="apache-2.0",
         drafters=dict(eagle3="RedHatAI/Qwen3-32B-speculator.eagle3")),
    dict(slug="llama-3.3-70b", repo="unsloth/Llama-3.3-70B-Instruct", rev="99cd0d2c829e92a67c844f9144c2509632e5c87f",
         original="meta-llama/Llama-3.3-70B-Instruct", license="llama3.3",
         drafters=dict(eagle3="nvidia/Llama-3.3-70B-Instruct-Eagle3"),
         mirror_note="meta-llama repo is gated; profiled from the ungated unsloth mirror"),
    dict(slug="qwen3-30b-a3b", repo="Qwen/Qwen3-30B-A3B-Instruct-2507", rev="0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe",
         license="apache-2.0", drafters=dict(eagle3="RedHatAI/Qwen3-30B-A3B-Instruct-2507-speculator.eagle3")),
    dict(slug="qwen3.6-35b-a3b", repo="Qwen/Qwen3.6-35B-A3B", rev="995ad96eacd98c81ed38be0c5b274b04031597b0", license="apache-2.0",
         drafters=dict(dflash="z-lab/Qwen3.6-35B-A3B-DFlash")),
    dict(slug="gemma-4-26b-a4b", repo="google/gemma-4-26B-A4B-it", rev="4d7ae4984b7db7de8f8457170b3f1a419ee76d52",
         license="apache-2.0", drafters=dict(dflash="z-lab/gemma-4-26B-A4B-it-DFlash",
                                             eagle3="RedHatAI/gemma-4-26B-A4B-it-speculator.eagle3")),
    dict(slug="gpt-oss-20b", repo="openai/gpt-oss-20b", rev="6cee5e81ee83917806bbde320786a8fb61efebee",
         license="apache-2.0", drafters=dict(eagle3="RedHatAI/gpt-oss-20b-speculator.eagle3")),
    dict(slug="gpt-oss-120b", repo="openai/gpt-oss-120b", rev="b5c939de8f754692c1647ca79fbf85e8c1e70f8a",
         license="apache-2.0", drafters=dict(eagle3="nvidia/gpt-oss-120b-Eagle3-v3", dflash="z-lab/gpt-oss-120b-DFlash")),
    dict(slug="llama-4-scout", repo="unsloth/Llama-4-Scout-17B-16E-Instruct", rev="afd8e498c87bda51c7ea8ec68ea2f7c066e6340b",
         original="meta-llama/Llama-4-Scout-17B-16E-Instruct", license="llama4",
         drafters=dict(eagle1="morgendave/EAGLE-Llama-4-Scout-17B-16E-Instruct"),
         mirror_note="meta-llama repo is gated; profiled from the ungated unsloth mirror"),
    dict(slug="glm-4.5-air", repo="zai-org/GLM-4.5-Air", rev="a24ceef6ce4f3536971efe9b778bdaa1bab18daa", license="mit",
         drafters={}),
    dict(slug="mistral-small-4-119b", repo="mistralai/Mistral-Small-4-119B-2603", rev="a11f36bebf709121056b1dbcc943d1c6afbe494d", license="apache-2.0",
         drafters=dict(eagle="mistralai/Mistral-Small-4-119B-2603-eagle")),
    dict(slug="qwen3-235b-a22b", repo="Qwen/Qwen3-235B-A22B-Instruct-2507", rev="ac9c66cc9b46af7306746a9250f23d47083d689e",
         license="apache-2.0", drafters=dict(eagle3="nvidia/Qwen3-235B-A22B-Eagle3")),
    dict(slug="minimax-m2.7", repo="MiniMaxAI/MiniMax-M2.7", rev="d494266a4affc0d2995ba1fa35c8481cbd84294b", license="other (MiniMax model license)",
         drafters=dict(eagle3="asherszhang/MiniMax-M2.7-EAGLE3-draft-vocab200k")),
    dict(slug="kimi-k2-0905", repo="moonshotai/Kimi-K2-Instruct-0905", rev="ac6c49f04883bd0a0598b790693a72061c676629",
         license="other (modified MIT)", drafters={}),
]

SCALE_RE = re.compile(r"(_scales?|\.weight_scale(_inv)?|\.scale|input_scale|_scale_inv)$")
VISION_RE = re.compile(r"(vision|visual|audio|multi_modal_projector|mm_projector|embed_vision|embed_audio|image_newline|"
                       r"patch_embed|siglip|\bmm\.)", re.I)
EMBED_RE = re.compile(r"(embed_tokens|\.wte\.|tok_embeddings|word_embeddings)")
HEAD_RE = re.compile(r"(^|\.)lm_head\.")
ROUTED_RE = re.compile(r"(?:^|\.)experts\.(?:\d+\.|gate_up_proj|down_proj|gate_proj|up_proj|w1|w2|w3)")
MTP_RE = re.compile(r"(^|\.)(mtp|nextn)[._]|(^|\.)mtp\.", re.I)
LAYER_RE = re.compile(r"(?:^|\.)layers\.(\d+)\.")


def text_cfg(cfg: dict) -> dict:
    t = cfg.get("text_config") or cfg.get("llm_config") or cfg
    return dict(cfg, **t) if t is not cfg else cfg


def resolve_rev(repo: str) -> str:
    import os
    from urllib.request import Request, urlopen
    req = Request(f"{HF_BASE}/api/models/{repo}", headers={"User-Agent": "OpenTallas/0.1 checkpoint-metadata-profiler",
                                                          **({"Authorization": f"Bearer {os.environ['HF_TOKEN']}"}
                                                             if os.environ.get("HF_TOKEN") else {})})
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read())["sha"]


def params_of(name: str, dtype: str, shape: list[int]) -> int:
    if SCALE_RE.search(name) or name.endswith(("_bias_scales",)):
        return 0
    n = 1
    for s in shape:
        n *= int(s)
    if dtype in ("U8", "I8") and (name.endswith("_blocks") or ROUTED_RE.search(name)):
        return 2 * n                       # MXFP4: two E2M1 values a byte
    return n


def role_of(name: str, n_layers: int) -> str:
    if VISION_RE.search(name):
        return "vision"
    m = LAYER_RE.search(name)
    if MTP_RE.search(name) or (m and int(m.group(1)) >= n_layers):
        return "mtp"
    if HEAD_RE.search(name):
        return "head"
    if EMBED_RE.search(name):
        return "embed"
    if ROUTED_RE.search(name) and "shared_expert" not in name:
        return "routed"
    return "dense"


def kv_layers(c: dict) -> list[dict]:
    """Per-layer KV/state descriptors from the config.  Bytes are at the FP8 (1 B) KV format the Qwen ROM adopted
    (results/uarch/qwen_rom_calibrated_calendar_20261003: fp8_e4m3); recurrent states stay FP32 as released."""
    L = c["num_hidden_layers"]
    mt = c.get("model_type", "")
    hd = c.get("head_dim") or c["hidden_size"] // c["num_attention_heads"]
    nkv = c.get("num_key_value_heads", c["num_attention_heads"])
    full = dict(kind="full", bytes_per_pos=2 * nkv * hd, window=0)
    out = []
    if "kv_lora_rank" in c and c.get("kv_lora_rank"):                       # MLA (Kimi-K2, Mistral-Small-4)
        b = c["kv_lora_rank"] + c.get("qk_rope_head_dim", 64)
        return [dict(kind="mla", bytes_per_pos=b, window=0)] * L
    lt = c.get("layer_types")
    if mt.startswith("gemma4"):
        gk = c.get("num_global_key_value_heads", nkv)
        gh = c.get("global_head_dim", hd)
        kv_mult = 1 if c.get("attention_k_eq_v") else 2
        for t in lt:
            out.append(dict(kind="window", bytes_per_pos=2 * nkv * hd, window=c["sliding_window"]) if t == "sliding_attention"
                       else dict(kind="full", bytes_per_pos=kv_mult * gk * gh, window=0))
        return out
    if mt.startswith(("qwen3_5", "qwen3_next")):
        state = c["linear_num_value_heads"] * c["linear_key_head_dim"] * c["linear_value_head_dim"] * 4
        conv = (2 * c["linear_num_key_heads"] * c["linear_key_head_dim"] + c["linear_num_value_heads"]
                * c["linear_value_head_dim"]) * (c.get("linear_conv_kernel_dim", 4) - 1) * 2
        for t in lt:
            out.append(dict(kind="linear", bytes_per_pos=0, window=0, state_bytes=state + conv) if t == "linear_attention"
                       else full)
        return out
    if lt:                                                                    # gpt-oss, gemma3 (newer configs)
        for t in lt:
            out.append(dict(kind="window", bytes_per_pos=2 * nkv * hd, window=c["sliding_window"])
                       if t == "sliding_attention" else full)
        return out
    if mt.startswith("gemma3"):
        pat = c.get("sliding_window_pattern", 6)
        return [full if (i + 1) % pat == 0 else dict(kind="window", bytes_per_pos=2 * nkv * hd, window=c["sliding_window"])
                for i in range(L)]
    if mt.startswith("llama4"):
        nrl = c.get("no_rope_layers")
        chunk = c.get("attention_chunk_size", 8192)
        return [dict(kind="chunk", bytes_per_pos=2 * nkv * hd, window=chunk) if (nrl and nrl[i]) else full
                for i in range(L)]
    sw = c.get("sliding_window")
    if sw and c.get("use_sliding_window", False):
        return [dict(kind="window", bytes_per_pos=2 * nkv * hd, window=sw)] * L
    return [full] * L


def moe_of(c: dict) -> dict:
    E = c.get("num_experts") or c.get("n_routed_experts") or c.get("num_local_experts") or 0
    k = c.get("num_experts_per_tok") or c.get("experts_per_token") or c.get("top_k_experts") or c.get("moe_topk") or 0
    return dict(experts=E or 0, top_k=k or 0, shared=c.get("n_shared_experts") or (1 if c.get("shared_expert_intermediate_size") else 0))


def mtp_of(c: dict, mtp_params: int) -> dict:
    n = (c.get("num_nextn_predict_layers") or c.get("mtp_num_hidden_layers") or
         (c.get("num_mtp_modules") if c.get("use_mtp") else 0) or 0)
    return dict(native_modules=int(n), weights_present=mtp_params > 0, params=mtp_params)


def profile(m: dict, cache: Path) -> dict:
    rev = m["rev"] or resolve_rev(m["repo"])
    root = cache / "metadata" / m["slug"] / rev
    cfg, cfg_raw = _cached_json(f"{HF_BASE}/{m['repo']}/resolve/{rev}/config.json", root / "config.json")
    idx, idx_raw = _cached_json(f"{HF_BASE}/{m['repo']}/resolve/{rev}/model.safetensors.index.json",
                                root / "model.safetensors.index.json")
    shards = sorted(set(idx["weight_map"].values()))
    with ThreadPoolExecutor(max_workers=16) as pool:
        heads = dict(zip(shards, pool.map(lambda s: _shard_header(m["repo"], rev, s, cache), shards)))
    c = text_cfg(cfg)
    L = c["num_hidden_layers"]
    p = defaultdict(int)
    b = defaultdict(int)
    dt = defaultdict(int)
    layer_params = defaultdict(lambda: defaultdict(int))
    n_t = 0
    for s in shards:
        for name, t in heads[s].items():
            if name == "__metadata__":
                continue
            n_t += 1
            st = int(t["data_offsets"][1]) - int(t["data_offsets"][0])
            r = role_of(name, L)
            n = params_of(name, t["dtype"], t["shape"])
            p[r] += n
            b[r] += st
            dt[t["dtype"]] += st
            lm = LAYER_RE.search(name)
            if lm and r in ("dense", "routed"):
                layer_params[int(lm.group(1))][r] += n
    tied = bool(c.get("tie_word_embeddings")) and p["head"] == 0
    moe = moe_of(c)
    head_p = p["embed"] if tied else p["head"]
    routed_active = p["routed"] * (moe["top_k"] / moe["experts"]) if moe["experts"] else 0
    active = p["dense"] + routed_active + head_p
    stored_text = p["dense"] + p["routed"] + p["embed"] + p["head"]
    kv = kv_layers(c)
    nl = len(layer_params)
    rec = dict(
        schema="rom_model_sweep.profile.v1", slug=m["slug"], repo=m["repo"], revision=rev,
        original_repo=m.get("original", m["repo"]), license=m["license"], mirror_note=m.get("mirror_note"),
        config_sha256=hashlib.sha256(cfg_raw).hexdigest(), index_sha256=hashlib.sha256(idx_raw).hexdigest(),
        shards=len(shards), tensors=n_t, header_storage_bytes_by_dtype=dict(dt),
        method="config.json + safetensors JSON headers via opentallas.profiling range reads; no tensor payload "
               "fetched, no inference run",
        model_type=c.get("model_type"), architectures=cfg.get("architectures"),
        layers=L, hidden=c["hidden_size"], heads=c["num_attention_heads"],
        kv_heads=c.get("num_key_value_heads"), head_dim=c.get("head_dim") or c["hidden_size"] // c["num_attention_heads"],
        vocab=c.get("vocab_size"), tied_embeddings=tied, max_context=c.get("max_position_embeddings"),
        intermediate=c.get("intermediate_size"), moe_intermediate=c.get("moe_intermediate_size"),
        moe=moe,
        params=dict(dense_layers=p["dense"], routed=p["routed"], embed=p["embed"], head=p["head"],
                    mtp=p["mtp"], vision=p["vision"], total_text=stored_text,
                    total_all=sum(p.values()), active_per_token=round(active),
                    active_routed=round(routed_active), head_streamed=head_p),
        header_bytes=dict(b),
        layer_count_in_headers=nl,
        kv_layers=kv,
        mtp=mtp_of(c, p["mtp"]),
        drafters_published=m.get("drafters", {}),
        quantization=(cfg.get("quantization_config") or c.get("quantization_config") or {}).get("quant_method"),
    )
    return rec


def deepseek_v41_from_repo() -> dict:
    """The DeepSeek-V4.1-Flash anchor, built offline from the repository's own pinned header profile
    (configs/models/candidates/deepseek-v4.1-flash.json + data/inventory/deepseek-v4.1-flash.json)."""
    prof_p = ROOT / "configs/models/candidates/deepseek-v4.1-flash.json"
    inv_p = ROOT / "data/inventory/deepseek-v4.1-flash.json"
    prof = json.loads(prof_p.read_text())
    inv = json.loads(inv_p.read_text())
    oc = prof["metadata"]["operator_config"]
    pc = inv["parameter_counts"]
    head = oc["vocab_size"] * oc["hidden_size"]
    kv = []
    for g in prof["attention_groups"]:
        for _ in range(g["count"]):
            if g["kind"] == "window":
                kv.append(dict(kind="window", bytes_per_pos=g["entry_bytes"], window=g["window_tokens"]))
            else:
                kv.append(dict(kind="csa", bytes_per_pos=g["entry_bytes"], window=g["window_tokens"],
                               window_entry=g.get("window_entry_bytes", 0.0), ratio=g["compression_ratio"],
                               top_k=g["top_k"], index_entry=g["index_entry_bytes"],
                               owner=g.get("kv_owner", True), scans=g.get("scans_index", True),
                               scan_cap=g.get("index_scan_entries_cap"), label=g["label"]))
    E, k = oc["num_routed_experts"], oc["experts_per_token"]
    routed = pc["decode_routed"]
    dense = pc["decode_dense"] - head
    return dict(
        schema="rom_model_sweep.profile.v1", slug="deepseek-v4.1-flash", repo=prof["source_repo"],
        revision=prof["source_revision"], original_repo=prof["source_repo"], license="deepseek (see repo)",
        mirror_note="anchor built offline from the repository's pinned header profile; no network read",
        config_sha256=None, index_sha256=inv.get("index_sha256"),
        sources={str(prof_p.relative_to(ROOT)): hashlib.sha256(prof_p.read_bytes()).hexdigest(),
                 str(inv_p.relative_to(ROOT)): hashlib.sha256(inv_p.read_bytes()).hexdigest()},
        method="derived from the committed header profile (itself config + safetensors headers)",
        model_type="deepseek_v41", layers=prof["num_layers"], hidden=oc["hidden_size"], heads=oc["num_attention_heads"],
        kv_heads=1, head_dim=oc["head_dim"], vocab=oc["vocab_size"], tied_embeddings=False,
        max_context=prof["max_context_tokens"], moe_intermediate=oc["moe_intermediate_size"],
        moe=dict(experts=E, top_k=k, shared=oc["num_shared_experts"]),
        params=dict(dense_layers=dense, routed=routed, embed=head, head=head, mtp=pc["draft_dense"] + pc["draft_routed"],
                    engram_tables=pc["engram_table"], vision=0,
                    total_text=dense + routed + 2 * head + pc["engram_table"],
                    total_all=dense + routed + 2 * head + pc["engram_table"] + pc["draft_dense"] + pc["draft_routed"],
                    active_per_token=round(dense + routed * k / E + head), active_routed=round(routed * k / E),
                    head_streamed=head),
        kv_layers=kv, mtp=dict(native_modules=3, weights_present=True, params=pc["draft_dense"] + pc["draft_routed"]),
        drafters_published=dict(dspark="deepseek-ai/DeepSeek-V4-Flash-DSpark (DSpark; repo tau 3.649 at 6 positions)"),
        quantization="fp8 dense / mxfp4 routed (released); ROM here at 8-bit like every other row",
        anchor_rates=dict(rom_ar=2786.8, rom_mtp=4588.9, hbm_ar_w19=2261.7, hbm_mtp_w19=4765.4,
                          src="results/uarch/consolidation.json headline_table.v41[0..1]"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", required=True, type=Path)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--v41-anchor", action="store_true", help="also write the DeepSeek-V4.1 anchor (offline)")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.v41_anchor:
        (OUT / "deepseek-v4.1-flash.json").write_text(json.dumps(deepseek_v41_from_repo(), indent=1) + "\n")
    for m in MODELS:
        if a.only and m["slug"] not in a.only:
            continue
        r = profile(m, a.cache_dir)
        (OUT / f"{m['slug']}.json").write_text(json.dumps(r, indent=1) + "\n")
        pp = r["params"]
        print(f"{m['slug']:24s} total_text {pp['total_text']/1e9:8.2f}B active {pp['active_per_token']/1e9:7.2f}B "
              f"mtp {pp['mtp']/1e9:5.2f}B vision {pp['vision']/1e9:5.2f}B L {r['layers']} kvL {len(r['kv_layers'])}")


if __name__ == "__main__":
    main()
