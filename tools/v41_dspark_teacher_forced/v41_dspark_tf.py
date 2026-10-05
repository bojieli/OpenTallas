#!/usr/bin/env python3
"""Teacher-forced DSpark (the mtp.0/1/2 drafter) of DeepSeek-V4.1-Flash at every position of a trace.

What DSpark is (vendor inference/model.py, DSparkBlock / Transformer.forward_spec): the three mtp
stages run IN SERIES as one 3-layer block drafter over a block of 5 positions [verified token,
noise token 128799 x 4]. Its input is main_hidden = concat of the attention input (mean over the
4 hyper-connection copies) of layers 37, 38, 39, projected by mtp.0.main_proj + main_norm to
main_x. Each stage's DSparkAttention attends a 128-slot sliding window of main_kv (its own wkv of
main_x, rope'd at the main positions, fp8 act-quantized) plus the 5 block tokens. mtp.2's
forward_head applies the shared head plus a Markov-head logit bias along the greedy-chained
drafts. One call drafts 5 tokens.

Teacher forcing: for every (sequence j, position p >= 1), the block's first token is g_p = the main
model's greedy token at p (the token a greedy speculative decoder would just have verified), and
the window holds main_kv of positions max(0, p-127)..p -- exactly what the vendor decode step
forward_spec(g_p, main_hidden[p], start_pos=p) sees after a prefill. Block positions get rope at
p+1..p+5. Rows are batched with an explicit per-row window instead of the ring cache. Validated
against the vendor decode path (ring cache, start_pos=p) on real mtp.0/mtp.1 weights: cos
0.988-0.9996 (rounding amplified through two MoE stages on random inputs).

Needs v41_stream.py (same directory) for the kernels, checkpoint streaming and vendor plumbing.

INPUT   --traces traces.json  (list of {"ids": [...]}); --main main_pass.pt (from v41_stream.py)
OUTPUT  --out drafts.pt : torch.save dict {rows [R,2] long (j,p), drafts [R,5] long (greedy drafts
        for tokens p+2..p+6), confidence [R,5] float (vendor confidence head), seconds}
Command: python3 v41_dspark_tf.py --traces traces.json --main main_pass.pt --out drafts.pt
Measured: 8,782 rows in 84 s, one 2.6 GB stage resident at a time, GPU peak < 9.1 GB.
"""
import argparse, json, sys, time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v41_stream as S  # noqa: E402
V, DEV = S.V, S.DEV


def _window_ctx(main_kv, rb, rp, win):
    offs = torch.arange(-win + 1, 1, device="cpu")
    pos = rp.view(-1, 1) + offs.view(1, -1)
    valid = pos >= 0
    kvw = main_kv[rb.view(-1, 1), pos.clamp_min(0)]
    return {"kv": kvw.to(DEV), "valid": valid.to(DEV), "pos": rp.to(DEV)}


def _rope_rows(x, freqs, inverse=False):
    """vendor apply_rotary_emb with a per-row position table."""
    xc = torch.view_as_complex(x.float().unflatten(-1, (-1, 2)))
    if inverse:
        freqs = freqs.conj()
    if xc.ndim == 4:
        freqs = freqs.unsqueeze(2)
    x.copy_(torch.view_as_real(xc * freqs).flatten(-2))
    return x


def _dspark_attn_rows(self, x, start_pos, main_x):
    """DSparkAttention.forward's decode branch (start_pos > 0) with one row per (sequence, p)."""
    ctx = self._rows_ctx
    r, nb, _ = x.size()
    rd, win = self.rope_head_dim, self.window_size
    posb = ctx["pos"].view(-1, 1) + 1 + torch.arange(nb, device=x.device).view(1, -1)
    fr = self.freqs_cis[posb]
    qr = self.q_norm(self.wq_a(x))
    q = self.wq_b(qr).unflatten(-1, (self.n_local_heads, self.head_dim))
    _rope_rows(q[..., -rd:], fr)
    kv = self.kv_norm(self.wkv(x))
    _rope_rows(kv[..., -rd:], fr)
    V.act_quant(kv, V.fp8_block_size, V.scale_fmt, V.scale_dtype, True)
    kvcat = torch.cat([ctx["kv"], kv], dim=1)
    widx = torch.where(ctx["valid"], torch.arange(win, device=x.device).view(1, -1), -1)
    bidx = (win + torch.arange(nb, device=x.device)).view(1, -1).expand(r, -1)
    idx = torch.cat([widx, bidx], dim=1).int().unsqueeze(1).expand(r, nb, -1).contiguous()
    o = V.sparse_attn(q, kvcat, self.attn_sink, idx, self.softmax_scale)
    _rope_rows(o[..., -rd:], fr, inverse=True)
    o = o.view(r, nb, self.n_local_groups, -1)
    wo_a = self.wo_a.weight.view(self.n_local_groups, self.o_lora_rank, -1)
    o = torch.einsum("bsgd,grd->bsgr", o, wo_a)
    return self.wo_b(o.flatten(2))


_vendor_forward = V.DSparkAttention.forward


def _dispatch(self, x, start_pos, main_x):
    if getattr(self, "_rows_ctx", None) is not None:
        return _dspark_attn_rows(self, x, start_pos, main_x)
    return _vendor_forward(self, x, start_pos, main_x)


V.DSparkAttention.forward = _dispatch


@torch.inference_mode()
def dspark_drafts(eng, main_hidden, g, rows, row_chunk=1024, head_chunk=128):
    """main_hidden: list of [T_j, 3*dim] bf16; g: list of [T_j] long; rows [R,2] (j, p>=1)."""
    args = eng.args
    bs = args.dspark_block_size
    R = rows.size(0)
    rb, rp = rows[:, 0], rows[:, 1]
    B = len(main_hidden)
    T = max(m.size(0) for m in main_hidden)
    draft_ids = torch.full((R, bs), args.dspark_noise_token_id, dtype=torch.long, device="cpu")
    draft_ids[:, 0] = torch.stack([g[j][p] for j, p in rows.tolist()])
    jobs = [("embed", "embed.", ())] + [(s, f"mtp.{s}.", ()) for s in range(args.n_mtp_layers)] + [("head", "head.", ())]
    H = torch.empty(R, bs, args.hc_mult, args.dim, dtype=torch.bfloat16, device="cpu")
    P = torch.empty(R, bs, args.hc_mult, dtype=torch.float32, device="cpu")
    main_x = torch.zeros(B, T, args.dim, dtype=torch.bfloat16, device="cpu")
    last = None
    t_all = time.time()
    for tag, sd, names in eng.prefetch(jobs):
        t0 = time.time()
        if tag == "embed":
            emb = sd["weight"].to(DEV)
        elif tag == "head":
            head = S.build_on_gpu(lambda: V.ParallelHead(args.vocab_size, args.dim, args.norm_eps, args.hc_eps))
            head.weight.data.copy_(sd["weight"])
            last.head = head
            drafts = torch.empty(R, bs, dtype=torch.long, device="cpu")
            conf = torch.empty(R, bs, dtype=torch.float32, device="cpu")
            for c in range(0, R, head_chunk):
                sl = slice(c, min(R, c + head_chunk))
                out_ids, logits, confidence = last.forward_head(H[sl].to(DEV), P[sl].to(DEV), draft_ids[sl, 0].to(DEV))
                drafts[sl] = out_ids[:, 1:].cpu()
                conf[sl] = confidence.float().cpu()
                del logits
            del head
        else:
            s = tag
            blk = S.build_on_gpu(lambda: V.DSparkBlock(args.n_layers + s, args))
            S.load_into(blk, sd, f"mtp.{s}.")
            del sd
            blk.embed = None
            blk.temperature = 0.0
            attn = blk.attn
            if s == 0:
                for b in range(B):
                    n = main_hidden[b].size(0)
                    main_x[b, :n] = blk.main_norm(blk.main_proj(main_hidden[b].unsqueeze(0).to(DEV)))[0].cpu()
            main_kv = torch.zeros(B, T, args.head_dim, dtype=torch.bfloat16, device="cpu")
            for b in range(B):
                kv = attn.kv_norm(attn.wkv(main_x[b:b + 1].to(DEV)))
                V.apply_rotary_emb(kv[..., -attn.rope_head_dim:], attn.freqs_cis[:T])
                V.act_quant(kv, V.fp8_block_size, V.scale_fmt, V.scale_dtype, True)
                main_kv[b] = kv[0].cpu()
            for c in range(0, R, row_chunk):
                sl = slice(c, min(R, c + row_chunk))
                if s == 0:
                    x = torch.nn.functional.embedding(draft_ids[sl].to(DEV), emb).unsqueeze(2).repeat(1, 1, args.hc_mult, 1)
                    pm = V.make_identity_pre_mix(x, args.hc_mult)
                else:
                    x, pm = H[sl].to(DEV), P[sl].to(DEV)
                attn._rows_ctx = _window_ctx(main_kv, rb[sl], rp[sl], attn.window_size)
                x, pm = V.Block.forward(blk, x, 1, pm, None, None)
                H[sl] = x.cpu(); P[sl] = pm.cpu()  # in place: chunk sl was read above
            attn._rows_ctx = None
            if s == args.n_mtp_layers - 1:
                last = blk
            else:
                del blk
            if s == 0:
                del emb
        eng.ck.drop_cache(names)
        eng.log(f"  [mtp {tag}] {time.time()-t0:5.2f}s peak={torch.cuda.max_memory_allocated()/1e9:.2f}GB")
    return drafts, conf, time.time() - t_all


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--traces", required=True)
    ap.add_argument("--main", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gpu-cap-gb", type=float, default=S.GPU_CAP_GB)
    a = ap.parse_args()
    tr = json.load(open(a.traces))
    mp = torch.load(a.main)
    lens = [len(t["ids"]) for t in tr]
    eng = S.Engine(max(lens) + 16, a.gpu_cap_gb, S._log)
    rows = torch.tensor([[j, p] for j in range(len(tr)) for p in range(1, lens[j] - 1)], dtype=torch.long, device="cpu")
    drafts, conf, secs = dspark_drafts(eng, mp["main_hidden"], mp["argmax"], rows)
    torch.save({"rows": rows, "drafts": drafts, "confidence": conf, "seconds": secs}, a.out)
    S._log(f"dspark {secs:.1f}s rows={rows.size(0)} -> {a.out}")


if __name__ == "__main__":
    main()
