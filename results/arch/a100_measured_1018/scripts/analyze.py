#!/usr/bin/env python3
"""A100-BENCH2 10-19: measured Qwen3-8B decode on 1x A100 SXM4 80GB (vLLM 0.31.0) vs the modelled roofline
(claude/s81-balance-1018 results/arch/s81_balance_1018/compute.py, a100_qwen).
usage: analyze.py <raw_dir> <out_json>
Pure decode (dec*): num_prompts = concurrency C, all requests start together. Token k of request i is emitted at
start_i + ttft_i + sum(itls_i[:k]). The decode window runs from the LAST first token to the FIRST request end; in it
every request is decoding and no prefill runs, so tokens/window = decode-only aggregate at batch C."""
import glob, json, os, re, sys

RAW, OUTF = sys.argv[1], sys.argv[2]

# ---- Qwen3-8B shapes (config.json): 36 layers, hidden 4096, FFN 12288, 32 q heads, 8 kv heads, head 128, vocab 151936
L, H, F, NQ, NKV, HD, V = 36, 4096, 12288, 32, 8, 128, 151936
LIN = L * (2 * H * H + 2 * H * NKV * HD + 3 * H * F)        # 6.945e9 linear params in the layers
LMH = V * H                                                 # 0.622e9 lm_head (untied, kept BF16 in the W8A8 ckpt)
WBYTES = dict(w8a8=LIN * 1 + LMH * 2, bf16=(LIN + LMH) * 2)  # bytes read a decode step (embedding is a gather)
KV_ELEM = L * NKV * HD * 2                                  # 73,728 K+V elements a token of context
KVB = dict(kvfp8=1, kvauto=2)
FLOP = lambda ctx: 2 * (LIN + LMH) + 4 * L * NQ * HD * ctx   # a token

# ---- the modelled roofline, copied from compute.py a100_qwen (INT8 weights, FP8 KV)
A = dict(bw=2.039e12, cap=80e9, bf16=312e12, int8=624e12, eff=dict(weight=0.75, kv=0.70, compute=0.45, capacity=0.90))
QW, DFLASH_W = 8.19e9, 1.05e9
def model(B, ctx=8192):
    e = A["eff"]; qkv = L * NKV * HD * 2 * ctx
    qops = 15.14e9 + 2 * 2 * L * NQ * HD * ctx
    t = max(QW / (A["bw"] * e["weight"]) + B * qkv / (A["bw"] * e["kv"]), B * qops / (A["int8"] * e["compute"]))
    return dict(B=B, per_user=1 / t, agg=B / t)
def model_cap(ctx=8192):
    return int((A["cap"] * A["eff"]["capacity"] - QW - DFLASH_W) // (L * NKV * HD * 2 * ctx))
def model_best(ctx):
    cap = model_cap(ctx)
    pts = [model(B, ctx) for B in sorted(set([1, 2, 4, 8, 16, 32, 48, 64, 96, 128, cap])) if B <= cap]
    return max(pts, key=lambda p: p["agg"])

def decode_window(d):
    st, tt, it, lat = d["start_times"], d["ttfts"], d["itls"], d["latencies"]
    t_first = [s + f for s, f in zip(st, tt)]
    t_end = [s + l for s, l in zip(st, lat)]
    w0, w1 = max(t_first), min(t_end)
    n = 0
    for s, f, its in zip(st, tt, it):
        t = s + f
        for x in its:
            t += x
            if w0 < t <= w1:
                n += 1
    if w1 <= w0 or n == 0:
        return None
    C = len(st)
    return dict(window_s=w1 - w0, tokens=n, agg=n / (w1 - w0), per_user=n / (w1 - w0) / C, step_ms=1e3 * (w1 - w0) * C / n)

rows = []
for f in sorted(glob.glob(os.path.join(RAW, "*", "*_c*.json"))):
    cfg = os.path.basename(os.path.dirname(f)); m = re.match(r"(\w+?)_c(\d+)\.json", os.path.basename(f))
    sweep, C = m.group(1), int(m.group(2))
    d = json.load(open(f))
    inl, outl = d["input_lens"][0] if "input_lens" in d else None, d["output_lens"][0] if "output_lens" in d else None
    r = dict(config=cfg, sweep=sweep, C=C, completed=d["completed"], input_len=inl, output_len=outl,
             output_tput=d["output_throughput"], median_tpot_ms=d["median_tpot_ms"], median_itl_ms=d["median_itl_ms"],
             p99_itl_ms=d["p99_itl_ms"], median_ttft_ms=d["median_ttft_ms"], duration_s=d["duration"])
    if sweep.startswith("dec") and "start_times" in d:
        w = decode_window(d)
        if w:
            r.update({"dec_" + k: v for k, v in w.items()})
            r["mean_ctx"] = inl + outl / 2
    rows.append(r)

def get(cfg, sweep, C):
    for r in rows:
        if r["config"] == cfg and r["sweep"] == sweep and r["C"] == C:
            return r

# ---- derived efficiencies (W8A8 + FP8 KV, the configuration the model prices)
eff = {}
cfg = "w8a8_kvfp8"
s1, l1 = get(cfg, "decshort", 1), get(cfg, "declong", 1)
if s1 and l1 and "dec_step_ms" in s1 and "dec_step_ms" in l1:
    ts, tl = s1["dec_step_ms"] / 1e3, l1["dec_step_ms"] / 1e3
    ks, kl = KV_ELEM * s1["mean_ctx"], KV_ELEM * l1["mean_ctx"]       # FP8: 1 byte an element
    # t = W/(bw e_w) + KV/(bw e_kv): two batch-1 points, two unknowns
    b = (tl - ts) / (kl - ks); a = (ts - b * ks) / WBYTES["w8a8"]
    eff["weight_b1"] = 1 / (a * A["bw"]); eff["kv_b1"] = 1 / (b * A["bw"])
    eff["effective_bw_b1_short_TBps"] = (WBYTES["w8a8"] + ks) / ts / 1e12
    eff["effective_bw_b1_long_TBps"] = (WBYTES["w8a8"] + kl) / tl / 1e12
    # batched long context: per-user step slope from the largest batch vs batch 1 (KV read + attention + overheads)
    big = max([r for r in rows if r["config"] == cfg and r["sweep"] == "declong" and "dec_step_ms" in r], key=lambda r: r["C"])
    slope = (big["dec_step_ms"] - l1["dec_step_ms"]) / 1e3 / (big["C"] - 1)
    eff["kv_batched"] = KV_ELEM * big["mean_ctx"] / slope / A["bw"]
    eff["kv_batched_at_C"] = big["C"]
    eff["bw_total_at_maxC_TBps"] = (WBYTES["w8a8"] + big["C"] * KV_ELEM * big["mean_ctx"]) / (big["dec_step_ms"] / 1e3) / 1e12
    # compute: short context, largest batch: FLOPs a step / (INT8 peak x step); a lower bound (step also streams weights)
    bs = max([r for r in rows if r["config"] == cfg and r["sweep"] == "decshort" and "dec_step_ms" in r], key=lambda r: r["C"])
    eff["compute_at_short_maxC"] = bs["C"] * FLOP(bs["mean_ctx"]) / (bs["dec_step_ms"] / 1e3) / A["int8"]
    eff["compute_at_short_maxC_C"] = bs["C"]
    eff["achieved_TOPS_short_maxC"] = bs["C"] * FLOP(bs["mean_ctx"]) / (bs["dec_step_ms"] / 1e3) / 1e12

# ---- measured vs modelled summary per config and context
summary = {}
for cfg in sorted({r["config"] for r in rows}):
    for sweep, ctx in (("declong", 8192), ("decshort", 512)):
        pts = [r for r in rows if r["config"] == cfg and r["sweep"] == sweep and "dec_agg" in r]
        if not pts:
            continue
        b1 = next((r for r in pts if r["C"] == 1), None)
        best = max(pts, key=lambda r: r["dec_agg"])
        summary[f"{cfg}/{sweep}"] = dict(
            ctx_model=ctx, b1_tok_s=b1["dec_per_user"] if b1 else None,
            best_agg_tok_s=best["dec_agg"], best_C=best["C"], per_user_at_best=best["dec_per_user"],
            model_b1=model(1, ctx)["per_user"], model_best_agg=model_best(ctx)["agg"], model_best_B=model_best(ctx)["B"],
            model_per_user_at_best=model_best(ctx)["per_user"], model_at_measured_bestC=model(min(best["C"], model_cap(ctx)), ctx)["agg"])
    for sweep in ("long", "short"):   # mixed prefill+decode serving sweeps (vllm bench serve output throughput)
        pts = [r for r in rows if r["config"] == cfg and r["sweep"] == sweep]
        if pts:
            best = max(pts, key=lambda r: r["output_tput"])
            summary[f"{cfg}/{sweep}_serving"] = dict(best_output_tput=best["output_tput"], best_C=best["C"],
                                                     b1_output_tput=next((r["output_tput"] for r in pts if r["C"] == 1), None))

kv = {}
for p in glob.glob(os.path.join(RAW, "*", "kv.txt")):
    kv[os.path.basename(os.path.dirname(p))] = dict(re.findall(r"(\w+)=(\d+)", open(p).read()))
json.dump(dict(shapes=dict(linear_params=LIN, lm_head_params=LMH, weight_bytes=WBYTES, kv_elems_per_token=KV_ELEM),
               model=dict(A=A, b1_8k=model(1)["per_user"], best_8k=model_best(8192), cap_8k=model_cap(8192)),
               efficiencies_w8a8_kvfp8=eff, kv_capacity=kv, summary=summary, rows=rows),
          open(OUTF, "w"), indent=1)
print(json.dumps(dict(eff=eff, summary=summary), indent=1))
