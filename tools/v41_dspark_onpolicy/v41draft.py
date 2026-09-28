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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gen', default='gen_out.pt')
    ap.add_argument('--out', default='drafts.json')
    ap.add_argument('--gpu-frac', type=float, default=0.15)
    a = ap.parse_args()
    torch.cuda.set_per_process_memory_fraction(a.gpu_frac)
    torch.set_default_dtype(torch.bfloat16)
    torch.set_grad_enabled(False)
    args = G.load_args(8192)
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
        n_rows = mh.size(0)            # positions 0 .. L+G-2
        assert n_rows == len(toks) - 1, (n_rows, len(toks))
        ids = torch.tensor(toks, device='cuda')
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
        out.append(dict(item=tr['item'], L=L, tokens=toks, drafts=drafts, confidence_sigmoid=conf))
        print(tr['item']['workload'], tr['item']['prompt_id'], 'rows', len(drafts), f'{time.time()-ts:.1f}s', flush=True)
    json.dump(out, open(a.out, 'w'))


if __name__ == '__main__':
    main()
