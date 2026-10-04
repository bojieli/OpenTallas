"""On-policy greedy DSpark acceptance for DeepSeek-V4.1-Flash on one shared GPU.

Phase A: greedy decode of the MAIN model (vendor inference/model.py modules, layer-streamed:
non-expert weights resident in host RAM, routed experts pread from the safetensors shards per
layer per step, only the experts the batch routes to).  Stores every position's DSpark input
(attention input of layers 37,38,39, mean over hc copies) and the greedy tokens.
Phase B: DSpark drafts at every generated position via the vendor forward_spec decode path
(DSparkBlock ring cache), compared against the model's own greedy continuation.
"""
import sys, os, json, struct, time, math, types, argparse, threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

SNAP = '/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277'
torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False
torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction = False

# ---------------------------------------------------------------- torch replacements of kernel.py
def _pow2_ceil(v):
    b = v.contiguous().view(torch.int32)
    e = ((b >> 23) & 0xFF) - 127 + ((b & 0x7FFFFF) != 0).int()
    return torch.ldexp(torch.ones_like(v), e)

def _fp4_round(y):
    a = y.abs()
    q = torch.full_like(a, 6.0)
    q = torch.where(a <= 5.0, 4.0, q)
    q = torch.where(a < 3.5, 3.0, q)
    q = torch.where(a <= 2.5, 2.0, q)
    q = torch.where(a < 1.75, 1.5, q)
    q = torch.where(a <= 1.25, 1.0, q)
    q = torch.where(a < 0.75, 0.5, q)
    q = torch.where(a <= 0.25, 0.0, q)
    return torch.copysign(q, y)

def act_quant(x, block_size=128, scale_fmt=None, scale_dtype=torch.float32, inplace=False):
    shp = x.shape; N = shp[-1]
    xf = x.float().reshape(-1, N // block_size, block_size)
    amax = xf.abs().amax(-1).clamp_min(1e-4)
    s = _pow2_ceil(amax * (1 / 448.0)) if scale_fmt is not None else amax * (1 / 448.0)
    y = (xf / s.unsqueeze(-1)).clamp(-448.0, 448.0).to(torch.float8_e4m3fn)
    if inplace:
        x.copy_((y.float() * s.unsqueeze(-1)).reshape(shp).to(x.dtype))
        return x
    return y.reshape(shp), s.to(scale_dtype).reshape(*shp[:-1], N // block_size)

def act_roundtrip(x):
    """fp8 e4m3 per-32 ue8m0 quant + exact dequant (what fp8_gemm/fp4_gemm consume)."""
    shp = x.shape; N = shp[-1]
    xf = x.float().reshape(-1, N // 32, 32)
    amax = xf.abs().amax(-1).clamp_min(1e-4)
    s = _pow2_ceil(amax * (1 / 448.0)).unsqueeze(-1)
    y = (xf / s).clamp(-448.0, 448.0).to(torch.float8_e4m3fn).float() * s
    return y.reshape(shp).to(torch.bfloat16)

def fp4_act_quant(x, block_size=32, inplace=False, scale_dtype=torch.float8_e8m0fnu):
    assert inplace
    shp = x.shape; N = shp[-1]
    xf = x.float().reshape(-1, N // block_size, block_size)
    amax = xf.abs().amax(-1)
    if scale_dtype == torch.float8_e4m3fn:
        amax = amax.clamp_min(6 * 2 ** -9)
        s = (amax / 6.0).to(torch.float8_e4m3fn).float()
    else:
        amax = amax.clamp_min(6 * 2 ** -126)
        s = _pow2_ceil(amax * (1 / 6.0))
    y = _fp4_round((xf / s.unsqueeze(-1)).clamp(-6.0, 6.0)) * s.unsqueeze(-1)
    x.copy_(y.reshape(shp).to(x.dtype))
    return x

def hc_split_sinkhorn(mixes, hc_scale, hc_base, hc_mult=4, sinkhorn_iters=20, eps=1e-6):
    hc = hc_mult
    pre = torch.sigmoid(mixes[..., :hc] * hc_scale[0] + hc_base[:hc]) + eps
    post = 2 * torch.sigmoid(mixes[..., hc:2 * hc] * hc_scale[1] + hc_base[hc:2 * hc])
    comb = (mixes[..., 2 * hc:] * hc_scale[2] + hc_base[2 * hc:]).unflatten(-1, (hc, hc))
    comb = comb.softmax(-1) + eps
    comb = comb / (comb.sum(-2, keepdim=True) + eps)
    for _ in range(sinkhorn_iters - 1):
        comb = comb / (comb.sum(-1, keepdim=True) + eps)
        comb = comb / (comb.sum(-2, keepdim=True) + eps)
    return pre, post, comb

def sparse_attn(q, kv, attn_sink, topk_idxs, softmax_scale, chunk=128):
    b, m, h, d = q.shape
    out = torch.empty_like(q)
    for bi in range(b):
        for m0 in range(0, m, chunk):
            idx = topk_idxs[bi, m0:m0 + chunk].long()          # [c,t]
            valid = idx >= 0
            g = kv[bi][idx.clamp_min(0)].float() * valid.unsqueeze(-1)   # [c,t,d]
            qq = q[bi, m0:m0 + chunk].float()                # [c,h,d]
            s = torch.matmul(qq, g.transpose(1, 2)) * softmax_scale   # [c,h,t]
            s = s.masked_fill(~valid.unsqueeze(1), float('-inf'))
            mx = s.amax(-1, keepdim=True).clamp_min(-1e30)
            p = torch.exp(s - mx)
            den = p.sum(-1) + torch.exp(attn_sink.float().view(1, h) - mx.squeeze(-1))
            o = torch.matmul(p.to(torch.bfloat16).float(), g) / den.unsqueeze(-1)
            out[bi, m0:m0 + chunk] = o.to(q.dtype)
    return out

def _unsupported(*a, **k):
    raise RuntimeError('replaced by linear()')

kern = types.ModuleType('kernel')
kern.act_quant = act_quant; kern.fp4_act_quant = fp4_act_quant; kern.hc_split_sinkhorn = hc_split_sinkhorn
kern.sparse_attn = sparse_attn; kern.fp8_gemm = _unsupported; kern.fp4_gemm = _unsupported
sys.modules['kernel'] = kern
for stub in ('vision', 'image_processor'):
    mod = types.ModuleType(stub)
    if stub == 'vision':
        mod.Aligner = mod.ViT = None
    else:
        mod.IMAGE, mod.IMAGE_END, mod.IMAGE_NEW_LINE, mod.IMAGE_START = 0, 1, 2, 3
    sys.modules[stub] = mod
sys.path.insert(0, SNAP + '/inference')
import model as M  # noqa: E402
import queue
PINQ = queue.Queue()
def init_pinned(n, size=19 * 2**20):
    for _ in range(n):
        PINQ.put(torch.empty(size, dtype=torch.uint8, device='cpu', pin_memory=True))

FP4_TABLE = torch.tensor([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 0.0, -0.5, -1.0, -1.5, -2.0, -3.0, -4.0, -6.0])

def deq_fp8_weight(w, s):
    N, K = w.shape
    bn, bk = s.shape
    assert N % 32 == 0 and K % 32 == 0 and bn == N // 32 and bk == K // 32, (w.shape, s.shape)
    return (w.float().view(bn, 32, bk, 32) * s.float()[:, None, :, None]).view(N, K).to(torch.bfloat16)

_LUT = {}
def deq_fp4_weight(w, s):
    """w: packed [N, K/2] (int8 / uint8 / fp4x2 view), low nibble = even element."""
    u = w.view(torch.uint8)
    N, K2 = u.shape
    lut = _LUT.get(u.device)
    if lut is None:
        tab = FP4_TABLE.to(u.device); ar = torch.arange(256, device=u.device)
        lut = _LUT[u.device] = torch.stack([tab[ar & 15], tab[ar >> 4]], -1)
    vals = lut[u.int()].view(N, -1, 32)
    return (vals * s.float().view(N, -1, 1)).view(N, K2 * 2).to(torch.bfloat16)

def my_linear(x, weight, bias=None):
    assert bias is None
    deq = getattr(weight, '_deq', None)
    if deq is None and weight.dtype == torch.float8_e4m3fn:
        deq = deq_fp8_weight(weight, weight.scale)
    elif deq is None and weight.dtype == torch.float4_e2m1fn_x2:
        deq = deq_fp4_weight(weight, weight.scale)
    if deq is not None:
        return F.linear(act_roundtrip(x), deq).to(torch.get_default_dtype())
    return F.linear(x, weight)

M.linear = my_linear
VERBOSE = os.environ.get('V41_VERBOSE') == '1'
MH_TAIL = 0
BATCHED_DECODE = False
FIT_CACHES = 0   # opt-in: args.max_seq_len when per-trace caches are sized to need

# ---------------------------------------------------------------- checkpoint access
LOCK = threading.Lock()
class Ckpt:
    def __init__(self):
        self.wm = json.load(open(SNAP + '/model.safetensors.index.json'))['weight_map']
        self.hdr = {}
        self.fds = {}
    def meta(self, name):
        f = self.wm[name]
        with LOCK:
          if f not in self.hdr:
            p = os.path.realpath(SNAP + '/' + f)
            with open(p, 'rb') as fh:
                n = struct.unpack('<Q', fh.read(8))[0]
                hd = (json.loads(fh.read(n)), 8 + n)
            self.fds[f] = os.open(p, os.O_RDONLY)
            self.hdr[f] = hd
        h, base = self.hdr[f]
        e = h[name]
        return self.fds[f], base + e['data_offsets'][0], e['data_offsets'][1] - e['data_offsets'][0], e['dtype'], e['shape']
    DT = {'BF16': torch.bfloat16, 'F32': torch.float32, 'F8_E4M3': torch.float8_e4m3fn, 'F8_E8M0': torch.float8_e8m0fnu,
          'I8': torch.int8}
    def read(self, name, pin=False):
        fd, off, n, dt, shape = self.meta(name)
        buf = torch.empty(n, dtype=torch.uint8, device='cpu', pin_memory=pin)
        mv = memoryview(buf.numpy())
        got = 0
        while got < n:
            got += os.preadv(fd, [mv[got:]], off + got)
        return buf.view(self.DT[dt]).view(*shape)

CK = Ckpt()
POOL = ThreadPoolExecutor(24)

# ---------------------------------------------------------------- module construction
def load_args(max_seq_len):
    cfg = json.load(open(SNAP + '/inference/config.json'))
    cfg['vision_n_layers'] = 0
    args = M.ModelArgs(**cfg)
    args.max_batch_size = 1
    args.max_seq_len = max_seq_len
    args.temperature = 0
    return args

def set_param(mod, name, t):
    parts = name.split('.')
    for p in parts[:-1]:
        mod = getattr(mod, p) if not p.isdigit() else mod[int(p)]
    mod._parameters[parts[-1]] = nn.Parameter(t, requires_grad=False)

def fix_scales(mod):
    for m in mod.modules():
        if isinstance(m, M.Linear) and m.scale is not None:
            m.weight.scale = m.scale

def fix_freqs(mod, args):
    for m in mod.modules():
        if isinstance(m, M.Attention):
            if m.compress_ratio:
                osl, theta = args.original_seq_len, args.compress_rope_theta
            else:
                osl, theta = 0, args.rope_theta
            m._buffers['freqs_cis'] = M.precompute_freqs_cis.__wrapped__(
                m.rope_head_dim, args.max_seq_len, osl, theta, args.rope_factor, args.beta_fast, args.beta_slow).cuda()
            if m.indexer is not None:
                m.indexer.freqs_cis = None

def host_params(prefix, mod, skip=()):
    """Read every parameter of mod (skipping names containing any of skip) into host RAM."""
    out = {}
    names = [n for n, _ in mod.named_parameters() if not any(s in n for s in skip)]
    def rd(n):
        return n, CK.read(prefix + n)
    for n, t in POOL.map(rd, names):
        out[n] = t
    # wo_a: convert.py dequantizes it to bf16 (the module declares bf16 and has no scale)
    for n in list(out):
        if n.endswith('attn.wo_a.weight'):
            s = CK.read(prefix + n.replace('weight', 'scale'))
            out[n] = deq_fp8_weight(out[n], s)
    for n, t in list(out.items()):
        p = dict(mod.named_parameters())[n]
        if p.dtype != t.dtype:
            if t.dtype == torch.int8:
                t = t.view(torch.float4_e2m1fn_x2)
            else:
                t = t.to(p.dtype)
        assert tuple(p.shape) == tuple(t.shape), (n, p.shape, t.shape)
        out[n] = t.pin_memory() if not t.is_pinned() else t
    return out

def to_gpu(mod, hp):
    for n, t in hp.items():
        set_param(mod, n, t.cuda(non_blocking=True))
    fix_scales(mod)
    for m in mod.modules():
        if isinstance(m, M.Linear) and m.weight.dtype == torch.float8_e4m3fn:
            m.weight._deq = deq_fp8_weight(m.weight, m.scale)

def to_meta(mod, hp):
    for n in hp:
        set_param(mod, n, torch.empty(0, device='meta'))

# ---------------------------------------------------------------- engram rows from disk
class EngramRows(nn.Module):
    def __init__(self, layer_id):
        super().__init__()
        self.w = CK.meta(f'layers.{layer_id}.engram.embed.weight')
        self.s = CK.meta(f'layers.{layer_id}.engram.embed.scale')
    def forward(self, ids):
        shp = ids.shape
        flat = ids.reshape(-1).cpu().numpy()
        uniq, inv = np.unique(flat, return_inverse=True)
        W = np.empty((len(uniq), 256), np.uint8); S = np.empty((len(uniq), 8), np.uint8)
        fdw, offw = self.w[0], self.w[1]; fds, offs = self.s[0], self.s[1]
        def rd(rng):
            for j in range(*rng):
                r = int(uniq[j])
                W[j] = np.frombuffer(os.pread(fdw, 256, offw + r * 256), np.uint8)
                S[j] = np.frombuffer(os.pread(fds, 8, offs + r * 8), np.uint8)
        n = len(uniq); step = max(1, n // 96 + 1)
        list(POOL.map(rd, [(a, min(n, a + step)) for a in range(0, n, step)]))
        w = torch.from_numpy(W).cuda().view(torch.float8_e4m3fn).float().view(-1, 8, 32)
        s = torch.from_numpy(S).cuda().view(torch.float8_e8m0fnu).float().view(-1, 8, 1)
        vals = (w * s).view(-1, 256).to(torch.bfloat16)
        return vals[torch.from_numpy(inv).cuda()].view(*shp, 256)

# ---------------------------------------------------------------- routed experts from disk
EXP_NAMES = ('w1', 'w2', 'w3')
class ExpertStore:
    def __init__(self, prefix, n_exp):
        self.prefix = prefix
        m = {}
        for e in range(n_exp):
            ent = []
            for w in EXP_NAMES:
                for k in ('weight', 'scale'):
                    ent.append(CK.meta(f'{prefix}.{e}.{w}.{k}'))
            m[e] = ent
        self.m = m
        self.n = n_exp
    def read(self, e):
        ent = self.m[e]
        tot = sum(x[2] for x in ent)
        buf = PINQ.get()
        assert buf.numel() >= tot
        mv = memoryview(buf.numpy())
        o = 0; parts = []
        for fd, off, n, dt, shape in ent:
            got = 0
            while got < n:
                got += os.preadv(fd, [mv[o + got:o + n]], off + got)
            parts.append((o, n, dt, shape)); o += n
        return buf, parts

def gpu_expert(buf, parts):
    g = buf.cuda(non_blocking=True)
    ts = [g[o:o + n].view(Ckpt.DT[dt]).view(*shape) for o, n, dt, shape in parts]
    W1 = deq_fp4_weight(ts[0], ts[1]); W2 = deq_fp4_weight(ts[2], ts[3]); W3 = deq_fp4_weight(ts[4], ts[5])
    return W1, W2, W3

def expert_fwd(x, w, W1, W2, W3, lim):
    xq = act_roundtrip(x)
    gate = F.linear(xq, W1).float()
    up = F.linear(xq, W3).float()
    if lim > 0:
        up = up.clamp(-lim, lim); gate = gate.clamp(max=lim)
    h = F.silu(gate) * up * w
    return F.linear(act_roundtrip(h.to(torch.bfloat16)), W2)

def moe_stream(ffn, store, x, lim, stats):
    weights, indices = ffn.gate(x)
    y = torch.zeros_like(x, dtype=torch.float32)
    k_act = indices.size(1)
    flat = indices.flatten()
    order = torch.argsort(flat, stable=True)
    tok_sorted = order // k_act
    w_sorted = weights.flatten()[order]
    counts = torch.bincount(flat, minlength=store.n).tolist()      # the one sync
    offs = [0]
    for c in counts:
        offs.append(offs[-1] + c)
    uniq = [e for e in range(store.n) if counts[e]]
    stats['experts'] += len(uniq)
    t0 = time.time()
    CH = 48
    futs = {}
    def submit(k):
        for e in uniq[k:k + CH]:
            futs[e] = POOL.submit(store.read, e)
    submit(0)
    for k in range(0, len(uniq), CH):
        if k + CH < len(uniq):
            submit(k + CH)
        used = []
        for e in uniq[k:k + CH]:
            tw = time.time()
            buf, parts = futs.pop(e).result()
            stats['io_s'] = stats.get('io_s', 0) + time.time() - tw
            W1, W2, W3 = gpu_expert(buf, parts)
            used.append(buf)
            rows = tok_sorted[offs[e]:offs[e + 1]]
            out = expert_fwd(x[rows], w_sorted[offs[e]:offs[e + 1], None], W1, W2, W3, lim)
            y.index_add_(0, rows, out.float())
            del W1, W2, W3
        torch.cuda.synchronize()
        for buf in used:
            PINQ.put(buf)
    stats['moe_s'] += time.time() - t0
    y += ffn.shared_experts(x)
    return y.type_as(x)

# ---------------------------------------------------------------- per-trace state
class Trace:
    def __init__(self, item, blocks, max_new):
        self.item = item
        self.tokens = list(item['ids'])
        self.L = len(self.tokens)
        self.max_new = max_new
        self.done = False
        self.shared = M.SharedAttentionRuntime()
        self.caches = {}
        for i, blk in enumerate(blocks):
            d = {}
            for n, b in blk.named_buffers():
                if n.endswith('freqs_cis'):
                    continue
                shape = list(b.shape)
                if FIT_CACHES and len(shape) == 3 and shape[1] > 128:
                    # opt-in: size the seq axis of compressed / indexer caches to this trace's need (the vendor
                    # code only slices them up to end_pos // ratio); the 128-row window rings are untouched
                    need = self.L + max_new + 16
                    shape[1] = min(shape[1], -(-shape[1] * need // FIT_CACHES))
                t = torch.zeros(shape, dtype=b.dtype, device='cuda')
                if n.endswith('score_state'):
                    t.fill_(-float('inf'))
                d[n] = t
            self.caches[i] = d
        self.main_hidden = []   # cpu bf16 chunks [s, 3*dim]
        self.pos = 0            # tokens processed so far

def swap_caches(blk, d):
    for n, t in d.items():
        parts = n.split('.')
        m = blk
        for p in parts[:-1]:
            m = getattr(m, p)
        m._buffers[parts[-1]] = t

# ---------------------------------------------------------------- one forward over a group of traces
def forward_group(traces, chunks, blocks, hps, stores, embed_w, head_w, norm_w, engram_hash, args, stats, want_logits=False):
    """chunks[b] = list of token ids to process for trace b at its current pos. Returns next greedy token per trace."""
    if BATCHED_DECODE and all(len(c) == 1 for c in chunks):
        return forward_decode_batched(traces, chunks, blocks, hps, stores, embed_w, head_w, norm_w, engram_hash, args, stats,
                                      want_logits)
    H, premix, start = [], [], []
    for tr, ch in zip(traces, chunks):
        ids = torch.tensor(ch, device='cuda').view(1, -1)
        h = F.embedding(ids, embed_w).unsqueeze(2).repeat(1, 1, args.hc_mult, 1)
        H.append(h); premix.append(M.make_identity_pre_mix(h, args.hc_mult)); start.append(tr.pos)
    mh = [[] for _ in traces]
    for i, blk in enumerate(blocks):
        t0 = time.time()
        to_gpu(blk, hps[i])
        t1 = time.time()
        if blk.engram is not None:
            for b, tr in enumerate(traces):
                full = torch.tensor(tr.tokens[:start[b] + len(chunks[b])], device='cuda').view(1, -1)
                hashes = engram_hash(full, 0)[:, start[b]:]
                H[b] = blk.engram(H[b], hashes[:, :, blk.engram.layer_hash_index, :], None)
        if i in args.dspark_target_layer_ids:
            for b in range(len(traces)):
                mh[b].append(H[b].mean(dim=2))
        ys, keep = [], []
        for b, tr in enumerate(traces):
            swap_caches(blk, tr.caches[i]); M.shared_attn = tr.shared
            x = H[b]; residual = x
            attn_pre, attn_post, attn_comb = blk.hc_mixes(x, blk.hc_attn_fn, blk.hc_attn_scale, blk.hc_attn_base)
            x = blk.hc_pre(x, premix[b]); x = blk.attn_norm(x); x = blk.attn(x, start[b])
            x = blk.hc_post(x, residual, attn_post, attn_comb)
            residual = x
            ffn_pre, ffn_post, ffn_comb = blk.hc_mixes(x, blk.hc_ffn_fn, blk.hc_ffn_scale, blk.hc_ffn_base)
            y = blk.ffn_norm(blk.hc_pre(x, attn_pre))
            ys.append(y.view(-1, args.dim)); keep.append((residual, ffn_post, ffn_comb, ffn_pre))
        stats['attn_s'] += time.time() - t1
        Y = moe_stream(blk.ffn, stores[i], torch.cat(ys), args.swiglu_limit, stats)
        o = 0
        for b in range(len(traces)):
            n = ys[b].size(0)
            residual, ffn_post, ffn_comb, ffn_pre = keep[b]
            H[b] = blk.hc_post(Y[o:o + n].view(1, n, args.dim), residual, ffn_post, ffn_comb)
            premix[b] = ffn_pre; o += n
        del ys, keep, Y
        to_meta(blk, hps[i])
        if VERBOSE:
            torch.cuda.synchronize()
            print(f'  layer {i} {time.time()-t0:.2f}s attn {stats["attn_s"]:.1f} moe {stats["moe_s"]:.1f} io {stats.get("io_s",0):.1f} deq {stats.get("deq_s",0):.1f} exps {stats["experts"]}', flush=True)
    nxt = []
    for b, tr in enumerate(traces):
        h = blocks[-1].hc_pre(H[b][:, -1:], premix[b][:, -1:])
        hf = h.float(); h = (norm_w * (hf * torch.rsqrt(hf.square().mean(-1, keepdim=True) + args.norm_eps))).to(h.dtype)
        logits = torch.cat([F.linear(h.float().view(1, -1), head_w[v:v + 32768].float()) for v in range(0, head_w.size(0), 32768)], -1)
        nxt.append(logits if want_logits else logits.argmax(-1))
        tr.pos = start[b] + len(chunks[b])
    mhs = torch.cat([torch.cat(m, dim=-1)[0] for m in mh]).cpu()
    o = 0
    for b, tr in enumerate(traces):
        n = len(chunks[b]); tr.main_hidden.append(mhs[o:o + n]); o += n
    if want_logits:
        return nxt
    return torch.cat(nxt).tolist()


def forward_decode_batched(traces, chunks, blocks, hps, stores, embed_w, head_w, norm_w, engram_hash, args, stats, want_logits):
    """opt-in (--batched-decode): one decode token per trace, the traces stacked on the sequence axis for every
    per-token operation (embedding, Engram, hc mixes / Sinkhorn, hc pre/post, norms, MoE, head).  Only the vendor
    attention, which owns the per-trace caches and positions, runs per trace.  Same modules and arithmetic per row;
    GEMMs see M = N rows instead of 1, so rounding can differ from the per-trace path (as it already does with batch
    composition).  Engram hashes use each trace's last max_ngram_size tokens (identical to hashing the full history)."""
    N = len(traces)
    start = [tr.pos for tr in traces]
    ids = torch.tensor([c[0] for c in chunks], device='cuda').view(1, N)
    H = F.embedding(ids, embed_w).unsqueeze(2).repeat(1, 1, args.hc_mult, 1)          # [1, N, hc, d]
    premix = M.make_identity_pre_mix(H, args.hc_mult)
    K = engram_hash.layout.max_ngram_size
    hl = []
    for tr, c in zip(traces, chunks):
        full = tr.tokens[:tr.pos + 1]
        tail = torch.tensor(full[-K:], device='cuda').view(1, -1)
        hl.append(engram_hash(tail, 0)[:, -1:])
    hashes = torch.cat(hl, 1)                                                          # [1, N, layers, cols]
    mh = []
    for i, blk in enumerate(blocks):
        t0 = time.time()
        to_gpu(blk, hps[i])
        t1 = time.time()
        if blk.engram is not None:
            H = blk.engram(H, hashes[:, :, blk.engram.layer_hash_index, :], None)
        if i in args.dspark_target_layer_ids:
            mh.append(H.mean(dim=2))
        residual = H
        attn_pre, attn_post, attn_comb = blk.hc_mixes(H, blk.hc_attn_fn, blk.hc_attn_scale, blk.hc_attn_base)
        x = blk.attn_norm(blk.hc_pre(H, premix))                                       # [1, N, d]
        outs = []
        for b, tr in enumerate(traces):
            swap_caches(blk, tr.caches[i]); M.shared_attn = tr.shared
            outs.append(blk.attn(x[:, b:b + 1], start[b]))
        x = torch.cat(outs, 1)
        H = blk.hc_post(x, residual, attn_post, attn_comb)
        residual = H
        ffn_pre, ffn_post, ffn_comb = blk.hc_mixes(H, blk.hc_ffn_fn, blk.hc_ffn_scale, blk.hc_ffn_base)
        y = blk.ffn_norm(blk.hc_pre(H, attn_pre))
        stats['attn_s'] += time.time() - t1
        Y = moe_stream(blk.ffn, stores[i], y.view(-1, args.dim), args.swiglu_limit, stats)
        H = blk.hc_post(Y.view(1, N, args.dim), residual, ffn_post, ffn_comb)
        premix = ffn_pre
        del Y, y, x, outs
        to_meta(blk, hps[i])
    h = blocks[-1].hc_pre(H, premix)
    hf = h.float(); h = (norm_w * (hf * torch.rsqrt(hf.square().mean(-1, keepdim=True) + args.norm_eps))).to(h.dtype)
    logits = torch.cat([F.linear(h.float().view(N, -1), head_w[v:v + 32768].float()) for v in range(0, head_w.size(0), 32768)], -1)
    mhs = torch.cat(mh, dim=-1)[0].cpu()                                               # [N, 3*d]
    for b, tr in enumerate(traces):
        tr.pos = start[b] + 1
        tr.main_hidden.append(mhs[b:b + 1])
    if want_logits:
        return [logits[b:b + 1] for b in range(N)]
    return logits.argmax(-1).tolist()


# ---------------------------------------------------------------- opt-in: T=1 twin traces (qualified run, 2026-10-03)
def pick(tr, logits):
    """greedy (mode 'greedy') or vendor sample() at T=1, top_p 1 (mode 't1') with a per-trace seeded generator;
    t1 records the target probability of the sampled token (the speculative-sampling replay needs p(x))."""
    if tr.mode == 'greedy':
        return int(logits.argmax(-1))
    probs = torch.softmax(logits.float().view(-1), -1, dtype=torch.float32)
    e = torch.empty_like(probs).exponential_(1, generator=tr.gen)
    t = int((probs / e).argmax())
    tr.p_tok.append(float(probs[t]))
    return t


def twin(tr, blocks, seed):
    """a T=1 copy of a prefilled greedy trace: same prompt, caches cloned (prefill is shared)."""
    import copy as _c
    t = Trace.__new__(Trace)
    t.item, t.L, t.max_new, t.done, t.pos = tr.item, tr.L, tr.max_new, False, tr.pos
    t.tokens = list(tr.tokens)
    t.caches = {i: {n: x.clone() for n, x in d.items()} for i, d in tr.caches.items()}
    # the runtime keeps references to the owning layer's cache tensors across forwards (index_k is only
    # re-published when a compressor group completes): re-point them at the twin's clones
    t.shared = M.SharedAttentionRuntime()
    ident = {id(x): (i, n) for i, d in tr.caches.items() for n, x in d.items()}
    for f in ('compress_kv', 'index_k', 'topk_idxs', 'candidates'):
        v = getattr(tr.shared, f)
        if v is None:
            continue
        if id(v) in ident:
            i, n = ident[id(v)]
            setattr(t.shared, f, t.caches[i][n])
        else:
            setattr(t.shared, f, v.clone())
    t.main_hidden = list(tr.main_hidden)
    t.mode = 't1'; t.p_tok = []
    t.gen = torch.Generator(device='cuda'); t.gen.manual_seed(seed)
    return t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prompts', default='prompts_sel.json')
    ap.add_argument('--max-new', type=int, default=160)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--prefill-group-tokens', type=int, default=12000)
    ap.add_argument('--out', default='gen_out.pt')
    ap.add_argument('--max-seq-len', type=int, default=6144)
    ap.add_argument('--gpu-frac', type=float, default=0.15)
    ap.add_argument('--t1-twins', action='store_true', help='opt-in: add a T=1 sampled twin per prompt (shared prefill)')
    ap.add_argument('--seed', type=int, default=20261003)
    ap.add_argument('--mh-prompt-tail', type=int, default=0, help='opt-in: keep only the last N prompt rows of main_hidden '
                    '(DSpark prefill only seeds its window_size=128 ring)')
    ap.add_argument('--save-every', type=int, default=10)
    ap.add_argument('--batched-decode', action='store_true', help='opt-in: stack the traces for every per-token op in decode')
    ap.add_argument('--stop-after-steps', type=int, default=0, help='opt-in: save and stop after this many decode steps')
    ap.add_argument('--fit-caches', action='store_true', help='opt-in: size each trace\'s compressed/indexer caches to L+max_new')
    a = ap.parse_args()
    torch.cuda.set_per_process_memory_fraction(a.gpu_frac)
    torch.set_default_dtype(torch.bfloat16)
    torch.set_grad_enabled(False)
    args = load_args(a.max_seq_len)
    global MH_TAIL, FIT_CACHES, BATCHED_DECODE
    BATCHED_DECODE = a.batched_decode
    MH_TAIL = a.mh_prompt_tail
    FIT_CACHES = a.max_seq_len if a.fit_caches else 0
    init_pinned(3 * 48 + 8)
    torch.set_default_device('cuda')
    M.world_size, M.rank, M.default_dtype = 1, 0, torch.float8_e4m3fn
    items = json.load(open(a.prompts))['items']
    if a.limit:
        items = items[:a.limit]
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(SNAP)
    t0 = time.time()
    layout = M.EngramLayout.from_args(args)
    with torch.device('cuda'):
        engram_hash = M.NgramHashState(args, layout, tok)
    print('engram hash state', time.time() - t0, flush=True)
    blocks, hps, stores = [], [], []
    for i in range(args.n_layers):
        with torch.device('meta'):
            blk = M.Block(i, args, layout)
        blk.ffn.experts = None
        if blk.engram is not None:
            blk.engram.embed = EngramRows(i)
        fix_freqs(blk, args)
        hps.append(host_params(f'layers.{i}.', blk, skip=('ffn.experts.', 'engram.embed.')))
        to_meta(blk, hps[-1])
        stores.append(ExpertStore(f'layers.{i}.ffn.experts', args.n_routed_experts))
        blocks.append(blk)
        print('layer', i, 'host params', sum(t.numel() * t.element_size() for t in hps[-1].values()) / 1e9, 'GB', round(time.time() - t0, 1), flush=True)
    embed_w = CK.read('embed.weight').cuda()
    head_w = CK.read('head.weight').cuda()
    norm_w = CK.read('norm.weight').cuda()
    print('resident loaded', time.time() - t0, 'GPU GB', torch.cuda.memory_allocated() / 1e9, flush=True)
    traces = [Trace(it, blocks, a.max_new) for it in items]
    stats = dict(experts=0, moe_s=0.0, attn_s=0.0, h2d_s=0.0)
    # prefill in groups
    groups, cur, ctok = [], [], 0
    for tr in traces:
        if cur and ctok + tr.L > a.prefill_group_tokens:
            groups.append(cur); cur, ctok = [], 0
        cur.append(tr); ctok += tr.L
    groups.append(cur)
    for tr in traces:
        tr.mode = 'greedy'
    twins = []
    for g in groups:
        ts = time.time()
        if not a.t1_twins:
            nxt = forward_group(g, [tr.tokens for tr in g], blocks, hps, stores, embed_w, head_w, norm_w, engram_hash, args, stats)
            for tr, n in zip(g, nxt):
                tr.tokens.append(n)
        else:
            lg = forward_group(g, [tr.tokens for tr in g], blocks, hps, stores, embed_w, head_w, norm_w, engram_hash, args, stats,
                               want_logits=True)
            for tr, l in zip(g, lg):
                if MH_TAIL:
                    tr.main_hidden = [torch.cat(tr.main_hidden)[-MH_TAIL:].clone()]
                import zlib
                tw = twin(tr, blocks, a.seed ^ zlib.crc32(tr.item['prompt_id'].encode()))
                tr.tokens.append(pick(tr, l)); tw.tokens.append(pick(tw, l))
                twins.append(tw)
        print(f'prefill group {len(g)} traces {sum(tr.L for tr in g)} tok {time.time()-ts:.1f}s stats {stats}', flush=True)
    traces = traces + twins
    eos = tok.eos_token_id
    step = 0
    while True:
        act = [tr for tr in traces if not tr.done]
        if not act:
            break
        ts = time.time()
        nxt = forward_group(act, [[tr.tokens[-1]] for tr in act], blocks, hps, stores, embed_w, head_w, norm_w, engram_hash, args, stats,
                            want_logits=a.t1_twins)
        if a.t1_twins:
            nxt = [pick(tr, l) for tr, l in zip(act, nxt)]
        for tr, n in zip(act, nxt):
            tr.tokens.append(n)
            if n == eos or len(tr.tokens) - tr.L >= tr.max_new:
                tr.done = True
        step += 1
        print(f'step {step} active {len(act)} {time.time()-ts:.1f}s experts {stats["experts"]} moe {stats["moe_s"]:.0f} attn {stats["attn_s"]:.0f} h2d {stats["h2d_s"]:.0f} gpu_peak {torch.cuda.max_memory_allocated()/1e9:.2f}', flush=True)
        if a.stop_after_steps and step >= a.stop_after_steps:
            break
        if step % a.save_every == 0 or not [tr for tr in traces if not tr.done]:
            save(traces, a.out, tok)
    save(traces, a.out, tok)
    print('done', time.time() - t0, flush=True)

def save(traces, path, tok):
    out = []
    for tr in traces:
        mh = torch.cat(tr.main_hidden) if tr.main_hidden else None
        d = dict(item={k: v for k, v in tr.item.items() if k != 'ids'}, prompt_ids=tr.item['ids'], tokens=tr.tokens,
                 L=tr.L, main_hidden=mh, text=tok.decode(tr.tokens[tr.L:]))
        if hasattr(tr, 'mode'):    # opt-in qualified fields
            d.update(mode=tr.mode, p_tok=getattr(tr, 'p_tok', None),
                     mh_offset=(len(tr.tokens) - 1 - mh.size(0)) if mh is not None else None)
        out.append(d)
    torch.save(out, path + '.tmp')
    os.replace(path + '.tmp', path)

if __name__ == '__main__':
    main()
