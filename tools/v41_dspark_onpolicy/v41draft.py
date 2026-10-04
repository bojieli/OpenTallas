"""Phase B: DSpark drafts along the main model's own greedy continuation (vendor forward_spec decode path)."""
import sys, json, time, types, argparse
import torch
import torch.nn as nn
import torch.nn.functional as F
import v41gen as G
from v41gen import M, CK


class Embed(nn.Module):
    def __init__(self, w):
        super().__init__(); self.w = w
    def forward(self, ids):
        return F.embedding(ids, self.w)


class Head(nn.Module):
    """ParallelHead with the bf16 checkpoint weight upcast per chunk (the vendor keeps it fp32: same values)."""
    def __init__(self, w):
        super().__init__(); self.w = w
    def forward(self, x, full_logits=False):
        if not full_logits:
            x = x[:, -1]
        xf = x.float()
        return torch.cat([F.linear(xf, self.w[v:v + 16384].float()) for v in range(0, self.w.size(0), 16384)], -1)


def moe_forward(self, x, image_mask=None):
    """vendor MoE.forward with one host sync (bincount) instead of one torch.where per expert; same arithmetic."""
    shape = x.size()
    x = x.view(-1, self.dim)
    weights, indices = self.gate(x, None)
    y = torch.zeros_like(x, dtype=torch.float32)
    k = indices.size(1)
    flat = indices.flatten()
    order = torch.argsort(flat, stable=True)
    tok, w = order // k, weights.flatten()[order]
    counts = torch.bincount(flat, minlength=self.n_routed_experts).tolist()
    o = 0
    for i, c in enumerate(counts):
        if c:
            rows = tok[o:o + c]
            y.index_add_(0, rows, self.experts[i](x[rows], w[o:o + c, None]).float())
        o += c
    y += self.shared_experts(x)
    return y.type_as(x).view(shape)


M.MoE.forward = moe_forward


def build(args):
    blocks = []
    for s in range(args.n_mtp_layers):
        with torch.device('meta'):
            blk = M.DSparkBlock(args.n_layers + s, args)
        G.fix_freqs(blk, args)
        hp = G.host_params(f'mtp.{s}.', blk)
        G.to_gpu(blk, hp)
        blocks.append(blk)
    embed = Embed(CK.read('embed.weight').cuda())
    head = Head(CK.read('head.weight').cuda())
    for blk in blocks:
        blk.embed = embed
        blk.head = head
    return blocks


def reset(blocks):
    for blk in blocks:
        for n, b in list(blk.named_buffers()):
            if n.endswith('freqs_cis'):
                continue
            parts = n.split('.'); m = blk
            for p in parts[:-1]:
                m = getattr(m, p)
            m._buffers[parts[-1]] = torch.zeros(b.shape, dtype=b.dtype, device='cuda')


def t1_rows(model, blocks, tr, ids, mh, L, n_rows):
    """T=1 (opt-in, qualified run): for every row p, the DSpark draft distribution q_k at depth k = 1..5 evaluated at the
    trajectory token x_k = tok[p+1+k], with the Markov head teacher-forced on tok[p+k] (the vendor forward_head feeds
    its own previous sample; under the maximal coupling below depth k only matters when d_{k-1} == x_{k-1}).
    Same vendor modules as forward_spec; only forward_head's sampling loop is replaced by a teacher-forced read."""
    M.Transformer.forward_spec(model, ids[L:L + 1], mh[:L].unsqueeze(0), 0)
    last = len(tr['tokens']) - 1
    q_tok, d_greedy = {}, {}
    m0, mL = blocks[0], blocks[-1]
    for p in range(L, n_rows):
        inp = ids[p + 1:p + 2]
        h, main_x = m0.forward_embed(mh[p:p + 1].unsqueeze(0), inp)
        pre_mix = M.make_identity_pre_mix(h, model.hc_mult)
        for layer in blocks:
            h, pre_mix = layer(h, p, pre_mix, main_x)
        x = mL.hc_pre(h, pre_mix)
        logits = mL.head(mL.norm(x), full_logits=True)          # [1, 5, V] fp32
        K = min(mL.block_size, last - (p + 1))
        if K <= 0:
            continue
        prev = ids[p + 1:p + 1 + K]                               # Markov inputs tok[p+1 .. p+K]
        tgt = ids[p + 2:p + 2 + K]                                # trajectory tokens tok[p+2 .. p+1+K]
        bias, _ = mL.markov_head(prev)                            # [K, V]
        lg = logits[0, :K].float() + bias.float()
        q = torch.softmax(lg, -1, dtype=torch.float32)
        q_tok[p] = q.gather(1, tgt.view(-1, 1)).view(-1)
        d_greedy[p] = lg.argmax(-1)
    ps = list(q_tok)
    qt = {p: v for p, v in zip(ps, [x.tolist() for x in q_tok.values()])}
    dg = {p: v for p, v in zip(ps, [x.tolist() for x in d_greedy.values()])}
    return dict(item=tr['item'], L=L, tokens=tr['tokens'], mode='t1', p_tok=tr['p_tok'], q_tok=qt, draft_argmax_tf=dg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gen', default='gen_out.pt')
    ap.add_argument('--out', default='drafts.json')
    ap.add_argument('--gpu-frac', type=float, default=0.15)
    ap.add_argument('--max-seq-len', type=int, default=8192)
    a = ap.parse_args()
    torch.cuda.set_per_process_memory_fraction(a.gpu_frac)
    torch.set_default_dtype(torch.bfloat16)
    torch.set_grad_enabled(False)
    args = G.load_args(a.max_seq_len)
    torch.set_default_device('cuda')
    M.world_size, M.rank, M.default_dtype = 1, 0, torch.float8_e4m3fn
    t0 = time.time()
    blocks = build(args)
    print('dspark loaded', time.time() - t0, 'GPU GB', torch.cuda.memory_allocated() / 1e9, flush=True)
    model = types.SimpleNamespace(mtp=blocks, hc_mult=args.hc_mult)
    gen = torch.load(a.gen)
    out = []
    for tr in gen:
        ts = time.time()
        reset(blocks)
        toks, L, mh = tr['tokens'], tr['L'], tr['main_hidden'].cuda()
        off = tr.get('mh_offset') or 0
        if off:                        # opt-in tail-trimmed prompt rows: rows before L-128 never reach the window ring
            assert L - off >= args.window_size, (L, off)
            mh = torch.cat([torch.zeros(off, mh.size(1), dtype=mh.dtype, device='cuda'), mh])
        n_rows = mh.size(0)            # positions 0 .. L+G-2
        assert n_rows == len(toks) - 1, (n_rows, len(toks))
        ids = torch.tensor(toks, device='cuda')
        if tr.get('mode') == 't1':
            out.append(t1_rows(model, blocks, tr, ids, mh, L, n_rows))
            print(tr['item']['workload'], tr['item']['prompt_id'], 't1 rows', len(out[-1]['q_tok']), f'{time.time()-ts:.1f}s', flush=True)
            continue
        M.Transformer.forward_spec(model, ids[L:L + 1], mh[:L].unsqueeze(0), 0)
        drafts, conf = {}, {}
        for p in range(L, n_rows):
            res = M.Transformer.forward_spec(model, ids[p + 1:p + 2], mh[p:p + 1].unsqueeze(0), p)
            output_ids, logits, confidence = res
            drafts[p] = output_ids[0, 1:]
            conf[p] = torch.sigmoid(confidence[0].float())
        if drafts:
            ps = list(drafts)
            dl = torch.stack([drafts[p] for p in ps]).tolist(); cl = torch.stack([conf[p] for p in ps]).tolist()
            drafts = dict(zip(ps, dl)); conf = dict(zip(ps, cl))
        out.append(dict(item=tr['item'], L=L, tokens=toks, drafts=drafts, confidence_sigmoid=conf, mode=tr.get('mode', 'greedy')))
        print(tr['item']['workload'], tr['item']['prompt_id'], 'rows', len(drafts), f'{time.time()-ts:.1f}s', flush=True)
    json.dump(out, open(a.out, 'w'))


if __name__ == '__main__':
    main()
