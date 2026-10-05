#!/usr/bin/env python3
"""Layer-streamed teacher-forced MAIN PASS of DeepSeek-V4.1-Flash on one small GPU slice.

Runs the vendor's own inference/model.py (checkpoint snapshot dba1be0a40aa45a94ad051997016db3960a90277)
unchanged -- Block, Attention, Compressor, Indexer, Engram, MoE, Gate, hyper-connections -- one
decoder layer resident at a time. Weights are preadv'd from the safetensors shards into two pinned
host buffers (double-buffered: layer i+1 is read while layer i computes), copied to the GPU, used,
and freed. Only the hashed engram rows (~90k per engram layer) are read from the 98 GB tables.

The six tilelang kernels of inference/kernel.py are replaced by torch equivalents written from the
kernel sources (a stub `kernel` module is registered before model.py is imported, so tilelang is
not needed). Reason: on an RTX PRO 6000 (sm_120) the vendor fp8_gemm returns NaN for most M and
sparse_attn needs 141,312 B shared memory (limit 101,376 B). Quantizers are bit-exact to the
kernels (checked against the launchable ones); GEMMs dequantize both operands exactly to bf16 and
accumulate in fp32, so only the summation order differs.

Each sequence runs attention at bsz=1 with prefill (start_pos=0); the vendor's cross-layer
shared_attn state is saved/restored per sequence, and the token-wise MoE of a layer runs once over
all sequences' tokens. Residual streams live on the host between layers, so GPU memory is ~one
layer of weights (~7.4 GB) plus one sequence's activations.

INPUT   --traces traces.json : list of {"ids": [token ids], ...} (other fields ignored)
OUTPUT  --out main_pass.pt   : torch.save dict with, per sequence j (lists, CPU tensors):
          argmax[j]     [T] long   greedy next-token id at every position (fp32 head, as vendor)
          top2gap[j]    [T] float  logit gap top1-top2
          logp_next[j]  [T] float  log p(trace token t+1 | prefix) (nan at the last position)
          main_hidden[j][T, 15360] bf16  DSpark input: attention input (mean over hc copies) of
                                         layers 37,38,39 concatenated (vendor Transformer.forward)
          timing, bytes_read, engram_rows
Command: python3 v41_stream.py --traces traces.json --out main_pass.pt [--gpu-cap-gb 11.5]
Measured (RTX PRO 6000 shared with other jobs): 8 sequences / 8,798 tokens -> 615 s, 9.07 GB peak,
298.7 GB streamed per pass.
"""
import argparse, json, os, queue, struct, sys, threading, time, types
from pathlib import Path

import numpy as np
import torch

SNAP = Path(os.environ.get("V41_SNAPSHOT", "/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--"
                           "DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277"))
DEV = "cuda"
GPU_CAP_GB = 11.5

# ================================================================================================
# torch replacements for inference/kernel.py
# ================================================================================================
import torch

torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction = False
torch.backends.cuda.matmul.allow_tf32 = False

FP4_TABLE = torch.tensor([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 0.0, -0.5, -1.0, -1.5, -2.0, -3.0, -4.0, -6.0],
                         dtype=torch.float32, device="cpu")
_tables = {}


def _fp4_table(dev):
    t = _tables.get(dev)
    if t is None:
        t = _tables[dev] = FP4_TABLE.to(dev)
    return t


def _pow2_ceil_log2(t):
    """fast_round_scale: 2 ** (exponent(t) - 127 + (mantissa != 0)), t fp32 > 0."""
    bits = t.contiguous().view(torch.int32)
    e = ((bits >> 23) & 0xFF) - 127 + ((bits & 0x7FFFFF) != 0).int()
    return torch.ldexp(torch.ones_like(t), e)


def act_quant(x, block_size=128, scale_fmt=None, scale_dtype=torch.float32, inplace=False):
    N = x.size(-1)
    assert N % block_size == 0
    xf = x.float().unflatten(-1, (N // block_size, block_size))
    amax = xf.abs().amax(-1).clamp_min(1e-4)
    if scale_fmt is not None:
        s = _pow2_ceil_log2(amax * torch.tensor(1 / 448.0, dtype=torch.float32, device=x.device))
    else:
        s = amax * torch.tensor(1 / 448.0, dtype=torch.float32, device=x.device)
    q = (xf / s.unsqueeze(-1)).clamp(-448.0, 448.0).to(torch.float8_e4m3fn)
    if inplace:
        y = (q.float() * s.unsqueeze(-1)).to(x.dtype).flatten(-2)
        x.copy_(y)
        return x
    return q.flatten(-2).contiguous(), s.to(scale_dtype)


def _round_e2m1(v):
    """RNE onto the e2m1 grid {0, .5, 1, 1.5, 2, 3, 4, 6} with saturation at 6, sign kept."""
    a = v.abs().clamp(max=6.0)
    q = torch.where(a < 2.0, 0.5, torch.where(a < 4.0, 1.0, 2.0))
    r = torch.round(a / q) * q  # torch.round is half-to-even == mantissa-even here
    return torch.copysign(r, v)


def fp4_act_quant(x, block_size=32, inplace=False, scale_dtype=torch.float8_e8m0fnu):
    assert scale_dtype in (torch.float8_e8m0fnu, torch.float8_e4m3fn)
    N = x.size(-1)
    xf = x.float().unflatten(-1, (N // block_size, block_size))
    amax = xf.abs().amax(-1)
    if scale_dtype == torch.float8_e4m3fn:
        amax = amax.clamp_min(6 * 2 ** -9)
        s = (amax / 6.0).to(torch.float8_e4m3fn).float()
    else:
        amax = amax.clamp_min(6 * 2 ** -126)
        s = _pow2_ceil_log2(amax * torch.tensor(1 / 6.0, dtype=torch.float32, device=x.device))
    q = _round_e2m1((xf / s.unsqueeze(-1)).clamp(-6.0, 6.0))
    if inplace:
        x.copy_((q * s.unsqueeze(-1)).to(x.dtype).flatten(-2))
        return x
    raise NotImplementedError("packed fp4 output is not used by model.py")


def _deq_rows(a, a_s, block):
    """[..., K] fp8 with [..., K/block] scales -> bf16 (exact)."""
    K = a.size(-1)
    return (a.float().unflatten(-1, (K // block, block)) * a_s.float().unsqueeze(-1)).flatten(-2).to(torch.bfloat16)


def fp8_gemm(a, a_s, b, b_s, scale_dtype=torch.float32, block_size=128):
    N, K = b.shape
    ad = _deq_rows(a, a_s, block_size)
    nb, kb = b_s.shape
    if N % block_size == 0:
        # e4m3 and a power-of-two e8m0 scale are both exact in bf16, so dequantize in bf16
        bd = (b.view(nb, block_size, kb, block_size).to(torch.bfloat16)
              * b_s.to(torch.bfloat16)[:, None, :, None]).view(N, K)
    else:
        bs = b_s.float().repeat_interleave(block_size, 0)[:N].repeat_interleave(block_size, 1)[:, :K]
        bd = (b.float() * bs).to(torch.bfloat16)
    return torch.matmul(ad, bd.t()).to(torch.get_default_dtype())


_pair_tables = {}


def _fp4_pairs(dev):
    """byte -> (low nibble value, high nibble value) in bf16, as convert.py unpacks e2m1 pairs."""
    t = _pair_tables.get(dev)
    if t is None:
        u = torch.arange(256, device="cpu")
        t = torch.stack([FP4_TABLE[u & 0x0F], FP4_TABLE[(u >> 4) & 0x0F]], -1).to(torch.bfloat16).to(dev)
        _pair_tables[dev] = t
    return t


def fp4_gemm(a, a_s, b, b_s, scale_dtype=torch.float32, act_block_size=128):
    N = b.size(0)
    u = b.view(torch.uint8)
    w = torch.nn.functional.embedding(u.int(), _fp4_pairs(u.device)).view(N, -1)  # [N, K] bf16, exact
    K = w.size(1)
    bd = (w.view(N, K // 32, 32) * b_s.to(torch.bfloat16).unsqueeze(-1)).view(N, K)
    ad = _deq_rows(a, a_s, act_block_size)
    return torch.matmul(ad, bd.t()).to(torch.get_default_dtype())


def hc_split_sinkhorn(mixes, hc_scale, hc_base, hc_mult=4, sinkhorn_iters=20, eps=1e-6):
    hc = hc_mult
    m = mixes.float()
    pre = torch.sigmoid(m[..., :hc] * hc_scale[0] + hc_base[:hc]) + eps
    post = 2 * torch.sigmoid(m[..., hc:2 * hc] * hc_scale[1] + hc_base[hc:2 * hc])
    comb = (m[..., 2 * hc:] * hc_scale[2] + hc_base[2 * hc:]).unflatten(-1, (hc, hc))
    comb = torch.softmax(comb, -1) + eps
    comb = comb / (comb.sum(-2, keepdim=True) + eps)
    for _ in range(sinkhorn_iters - 1):
        comb = comb / (comb.sum(-1, keepdim=True) + eps)
        comb = comb / (comb.sum(-2, keepdim=True) + eps)
    return pre, post, comb


def sparse_attn(q, kv, attn_sink, topk_idxs, softmax_scale, chunk_elems=48 * 1024 * 1024):
    b, m, h, d = q.shape
    k = topk_idxs.size(-1)
    out = torch.empty_like(q)
    if k == 0:
        return out.zero_()
    mc = max(1, min(m, chunk_elems // max(1, b * k * d)))
    bidx = torch.arange(b, device=q.device).view(b, 1, 1)
    sink = attn_sink.float().view(1, 1, h)
    for s in range(0, m, mc):
        e = min(m, s + mc)
        ii = topk_idxs[:, s:e].long()
        valid = ii >= 0
        g = kv[bidx, ii.clamp_min(0)].float()  # [b, mc, k, d]
        g = g * valid.unsqueeze(-1)
        qs = q[:, s:e].float()  # [b, mc, h, d]
        sc = torch.matmul(qs, g.transpose(-1, -2)) * softmax_scale  # [b, mc, h, k]
        sc.masked_fill_(~valid.unsqueeze(2), float("-inf"))
        mx = sc.amax(-1).clamp_min(-1e30)
        p = torch.exp(sc - mx.unsqueeze(-1))
        ssum = p.sum(-1) + torch.exp(sink - mx)
        o = torch.matmul(p.to(torch.bfloat16).float(), g) / ssum.unsqueeze(-1)
        out[:, s:e] = o.to(q.dtype)
        del g, sc, p, o
    return out


sparse_attn_torch = sparse_attn


def _install_vendor():
    """Register the torch kernels as module `kernel`, then import the vendor model.py."""
    km = types.ModuleType("kernel")
    for n in ("act_quant", "fp4_act_quant", "fp4_gemm", "fp8_gemm", "hc_split_sinkhorn", "sparse_attn"):
        setattr(km, n, globals()[n])
    sys.modules["kernel"] = km
    sys.path.insert(0, str(SNAP / "inference"))
    import model as vendor  # noqa: E402
    assert vendor.sparse_attn is sparse_attn and vendor.fp8_gemm is fp8_gemm
    return vendor


V = _install_vendor()


# ================================================================================================
# checkpoint streaming
# ================================================================================================
class Ckpt:
    def __init__(self, snap=SNAP):
        from safetensors import safe_open
        self.snap = snap
        self.meta = {}  # name -> (file, dtype, shape, abs_offset, nbytes)
        self.handles = {}
        for f in sorted(snap.glob("model-*.safetensors")):
            with open(f, "rb") as fh:
                n = struct.unpack("<Q", fh.read(8))[0]
                hdr = json.loads(fh.read(n))
            for k, v in hdr.items():
                if k == "__metadata__":
                    continue
                a, b = v["data_offsets"]
                self.meta[k] = (str(f), v["dtype"], v["shape"], 8 + n + a, b - a)
        self._safe_open = safe_open
        self.bytes_read = 0
        self.read_seconds = 0.0

    def handle(self, f):
        h = self.handles.get(f)
        if h is None:
            h = self.handles[f] = self._safe_open(f, framework="pt", device="cpu")
        return h

    def get(self, name):
        f = self.meta[name][0]
        t = self.handle(f).get_tensor(name)
        self.bytes_read += self.meta[name][4]
        return t

    def names(self, prefix):
        return [k for k in self.meta if k.startswith(prefix)]

    def drop_cache(self, names):
        """posix_fadvise(DONTNEED) the byte ranges we just streamed, so a 300 GB pass does not
        evict the page cache of other users on this shared machine."""
        byfile = {}
        for k in names:
            f, _, _, off, nb = self.meta[k]
            byfile.setdefault(f, []).append((off, nb))
        for f, rngs in byfile.items():
            lo = min(o for o, _ in rngs); hi = max(o + n for o, n in rngs)
            fd = os.open(f, os.O_RDONLY)
            try:
                os.posix_fadvise(fd, lo, hi - lo, os.POSIX_FADV_DONTNEED)
            finally:
                os.close(fd)

    def rows(self, name, idx_sorted_unique):
        """Read selected rows of a 2-D tensor straight from the file (engram tables)."""
        f, dt, shape, off, nb = self.meta[name]
        width = shape[1]  # 1-byte dtypes only (F8_E4M3 / F8_E8M0)
        idx = np.asarray(idx_sorted_unique, dtype=np.int64)
        out = np.empty((idx.size, width), dtype=np.uint8)
        fd = os.open(f, os.O_RDONLY)
        try:
            from concurrent.futures import ThreadPoolExecutor

            def rd(chunk):
                for k in chunk:
                    out[k] = np.frombuffer(os.pread(fd, width, off + int(idx[k]) * width), dtype=np.uint8)
            chunks = np.array_split(np.arange(idx.size), 256)
            with ThreadPoolExecutor(64) as ex:
                list(ex.map(rd, chunks))
        finally:
            os.close(fd)
        self.bytes_read += out.nbytes
        return out


_ST_DT = {"F8_E4M3": torch.float8_e4m3fn, "F8_E8M0": torch.float8_e8m0fnu, "I8": torch.int8,
          "BF16": torch.bfloat16, "F32": torch.float32, "F16": torch.float16}


class PinnedReader:
    """Reads a module's tensors straight from the shards into one of two pinned host buffers
    (big parallel preads, no mmap page-fault path), returning tensor views into that buffer.
    Pageable H2D measured ~1 GB/s under this machine's load; pinned ~12 GB/s."""

    def __init__(self, ck, cap_bytes, nbuf=2, threads=8, piece=64 << 20):
        self.ck = ck
        self.bufs = [torch.empty(cap_bytes, dtype=torch.uint8, device="cpu", pin_memory=True) for _ in range(nbuf)]
        self.np = [b.numpy() for b in self.bufs]
        self.free = queue.Queue()
        for i in range(nbuf):
            self.free.put(i)
        self.threads, self.piece = threads, piece

    def read(self, prefix, skip=()):
        from concurrent.futures import ThreadPoolExecutor
        ck = self.ck
        names = [n for n in ck.names(prefix) if not any(s in n for s in skip)]
        byfile = {}
        for n in names:
            f, dt, shape, off, nb = ck.meta[n]
            byfile.setdefault(f, []).append((off, nb, n))
        bi = self.free.get()  # blocks until the consumer released a buffer
        buf, arr = self.bufs[bi], self.np[bi]
        pos = 0
        jobs = []  # (fd_path, file_off, buf_off, n)
        where = {}
        for f, items in byfile.items():
            items.sort()
            runs, cur = [], None
            for off, nb, n in items:
                if cur and off - (cur[0] + cur[1]) <= (1 << 20):
                    cur[1] = off + nb - cur[0]; cur[2].append((off, nb, n))
                else:
                    cur = [off, nb, [(off, nb, n)]]; runs.append(cur)
            for start, length, members in runs:
                pos = (pos + 4095) // 4096 * 4096
                assert pos + length <= arr.size, "pinned buffer too small"
                for o in range(0, length, self.piece):
                    jobs.append((f, start + o, pos + o, min(self.piece, length - o)))
                for off, nb, n in members:
                    where[n] = pos + (off - start)
                pos += length
        t0 = time.time()
        fds = {f: os.open(f, os.O_RDONLY) for f in byfile}
        try:
            def rd(j):
                f, fo, bo, n = j
                mv = memoryview(arr[bo:bo + n])
                got = 0
                while got < n:
                    k = os.preadv(fds[f], [mv[got:]], fo + got)
                    assert k > 0
                    got += k
            with ThreadPoolExecutor(self.threads) as ex:
                list(ex.map(rd, jobs))
        finally:
            for fd in fds.values():
                os.close(fd)
        ck.read_seconds += time.time() - t0
        ck.bytes_read += sum(j[3] for j in jobs)
        out = {}
        for n in names:
            f, dt, shape, off, nb = ck.meta[n]
            b = where[n]
            tdt = _ST_DT[dt]
            v = buf[b:b + nb]
            if b % tdt.itemsize == 0 if hasattr(tdt, "itemsize") else True:
                t = v.view(tdt).view(shape)
            else:
                t = v.clone().view(tdt).view(shape)
            out[n[len(prefix):]] = t
        return out, names, bi

    def release(self, bi):
        torch.cuda.synchronize()  # copies out of the buffer must have landed
        self.free.put(bi)




# ================================================================================================
# vendor model plumbing
# ================================================================================================
def make_args(max_seq):
    cfg = json.load(open(SNAP / "inference" / "config.json"))
    cfg.update(max_batch_size=1, max_seq_len=max_seq, temperature=0.0, vision_n_layers=0)
    args = V.ModelArgs(**{k: v for k, v in cfg.items() if k in V.ModelArgs.__dataclass_fields__})
    V.world_size, V.rank = 1, 0
    V.default_dtype = torch.float8_e4m3fn
    return args


class _TinyEngramEmbedding(V.ParallelEngramEmbedding):
    """Vendor ParallelEngramEmbedding without the 98 GB table; the gathered rows are attached per
    pass and the hash ids remapped into them. forward() is the vendor's, unchanged."""

    def __init__(self, num_embeddings, dim):
        torch.nn.Module.__init__(self)
        self.num_embeddings = num_embeddings
        self.dim = dim
        self.part_num_embeddings = num_embeddings
        self.vocab_start_idx = 0
        self.vocab_end_idx = num_embeddings
        self.block_size = V.fp8_block_size
        self.weight = torch.nn.Parameter(torch.empty(1, dim, dtype=torch.float8_e4m3fn), requires_grad=False)
        self.scale = torch.nn.Parameter(torch.empty(1, dim // self.block_size, dtype=V.scale_dtype), requires_grad=False)


V.ParallelEngramEmbedding = _TinyEngramEmbedding


def load_into(module, sd, prefix):
    """Copy checkpoint tensors into a freshly built vendor module, applying convert.py's MP=1
    transforms: wo_a dequantized to bf16, int8 experts viewed as float4_e2m1fn_x2."""
    params = dict(module.named_parameters())
    used = set()
    for name, p in params.items():
        if ".engram.embed." in "." + name or name.endswith("wo_a.scale"):
            continue
        if name.endswith("wo_a.weight"):
            w = sd[name].to(DEV); s = sd[name.replace("weight", "scale")].to(DEV)
            ob, ib = w.size(0) // s.size(0), w.size(1) // s.size(1)
            w = (w.unflatten(0, (-1, ob)).unflatten(-1, (-1, ib)).float() * s[:, None, :, None].float())
            p.data.copy_(w.flatten(2, 3).flatten(0, 1).bfloat16())
            used.update([name, name.replace("weight", "scale")])
            continue
        if name not in sd:
            raise KeyError(f"{prefix}{name} missing from checkpoint")
        t = sd[name]
        used.add(name)
        if p.dtype == torch.float4_e2m1fn_x2:
            assert t.dtype == torch.int8 and tuple(t.shape) == tuple(p.shape), (name, t.dtype, t.shape, p.shape)
            p.data.view(torch.int8).copy_(t, non_blocking=True)
        else:
            assert tuple(t.shape) == tuple(p.shape), (name, t.shape, p.shape)
            p.data.copy_(t, non_blocking=True)
    extra = set(sd) - used - {k for k in sd if ".engram.embed." in "." + k or k.endswith("bias_vl")}
    if extra:
        raise KeyError(f"unconsumed checkpoint keys under {prefix}: {sorted(extra)[:5]}")


def build_on_gpu(ctor):
    prev = torch.get_default_dtype()
    torch.set_default_dtype(torch.bfloat16)
    try:
        with torch.device(DEV):
            return ctor()
    finally:
        torch.set_default_dtype(prev)


class Engine:
    def __init__(self, max_seq, gpu_cap_gb=GPU_CAP_GB, log=print):
        torch.set_default_dtype(torch.bfloat16)  # as the vendor generate.py does
        torch.set_default_device(DEV)
        torch.cuda.set_per_process_memory_fraction(gpu_cap_gb * 1e9 / torch.cuda.get_device_properties(0).total_memory)
        self.args = make_args(max_seq)
        self.ck = Ckpt()
        self.log = log
        self.layout = V.EngramLayout.from_args(self.args)
        from transformers import AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(str(SNAP))
        with torch.device(DEV):
            self.hasher = V.NgramHashState(self.args, self.layout, self.tok)
        self.timing = {}
        self.reader = None

    def _t(self, k, dt):
        self.timing[k] = self.timing.get(k, 0.0) + dt

    def prefetch(self, jobs):
        """Background reader into two pinned buffers: yields (tag, state_dict, names) in order,
        one job ahead; a buffer is recycled when the consumer asks for the next item."""
        if self.reader is None:
            cap = 0
            for pre in [f"layers.{i}." for i in range(self.args.n_layers)] + ["mtp.0.", "mtp.1.", "mtp.2.", "embed.", "head."]:
                cap = max(cap, sum(self.ck.meta[n][4] for n in self.ck.names(pre) if ".engram.embed." not in n))
            t = time.time()
            self.reader = PinnedReader(self.ck, int(cap * 1.01) + (64 << 20))
            self.log(f"pinned buffers 2 x {cap/1e9:.2f} GB allocated in {time.time()-t:.1f}s")
        q = queue.Queue(maxsize=1)

        def worker():
            for tag, prefix, skip in jobs:
                sd, names, bi = self.reader.read(prefix, skip)
                q.put((tag, sd, names, bi))
            q.put(None)
        threading.Thread(target=worker, daemon=True).start()
        while True:
            item = q.get()
            if item is None:
                break
            tag, sd, names, bi = item
            yield tag, sd, names
            del sd
            self.reader.release(bi)

    def gather_engram(self, blk, hash_ids):
        uniq, inv = torch.unique(hash_ids.flatten(), return_inverse=True)
        u = uniq.cpu().numpy()
        t = time.time()
        w = self.ck.rows(f"layers.{blk.layer_id}.engram.embed.weight", u)
        s = self.ck.rows(f"layers.{blk.layer_id}.engram.embed.scale", u)
        self._t("engram_row_read_s", time.time() - t)
        e = blk.engram.embed
        e.weight = torch.nn.Parameter(torch.from_numpy(w).to(DEV).view(torch.float8_e4m3fn), requires_grad=False)
        e.scale = torch.nn.Parameter(torch.from_numpy(s).to(DEV).view(V.scale_dtype), requires_grad=False)
        return inv.view(hash_ids.shape), int(u.size)

    @torch.inference_mode()
    def main_pass(self, seqs):
        """seqs: list of 1-D CPU LongTensors. See module docstring for the returned fields."""
        args = self.args
        t_pass = time.time()
        N = len(seqs)
        ids = [s.to(DEV).view(1, -1) for s in seqs]
        hashes = [self.hasher(x, 0, None).cpu() for x in ids]  # [1,T,n_engram_layers,C]
        jobs = [("embed", "embed.", ())] + [(i, f"layers.{i}.", (".engram.embed.",)) for i in range(args.n_layers)]
        jobs += [("head", "head.", ()), ("norm", "norm.", ())]
        H = [None] * N; PM = [None] * N  # residual streams kept on the host between layers
        SA = [dict(compress_kv=None, index_k=None, topk_idxs=None, candidates=None) for _ in range(N)]
        MH = [[] for _ in range(N)]
        stash = [None] * N
        engram_rows = {}
        head_w = norm_w = None
        for tag, sd, names in self.prefetch(jobs):
            t0 = time.time()
            if tag == "embed":
                emb = sd["weight"].to(DEV)
                for j in range(N):
                    h = torch.nn.functional.embedding(ids[j], emb).unsqueeze(2).repeat(1, 1, args.hc_mult, 1)
                    PM[j] = V.make_identity_pre_mix(h, args.hc_mult).cpu()
                    H[j] = h.cpu()
                del emb
            elif tag == "head":
                head_w = sd["weight"].to(DEV)
            elif tag == "norm":
                norm_w = sd["weight"].to(DEV)
            else:
                i = tag
                blk = build_on_gpu(lambda: V.Block(i, args, self.layout))
                load_into(blk, sd, f"layers.{i}.")
                del sd
                torch.cuda.synchronize()
                self._t("h2d_build_s", time.time() - t0)
                t1 = time.time()
                if blk.engram is not None:
                    allh = torch.cat([hh[0, :, blk.engram.layer_hash_index, :] for hh in hashes], 0).to(DEV)
                    hid, engram_rows[i] = self.gather_engram(blk, allh)
                    off = 0
                for j in range(N):
                    for k, v in SA[j].items():
                        setattr(V.shared_attn, k, None if v is None else v.to(DEV))
                    h, pm = H[j].to(DEV), PM[j].to(DEV)
                    if blk.engram is not None:
                        T = h.size(1)
                        h = blk.engram(h, hid[off:off + T].unsqueeze(0), None)
                        off += T
                    if i in args.dspark_target_layer_ids:
                        MH[j].append(h.mean(dim=2)[0].cpu())
                    # vendor Block.forward, split at the FFN so the token-wise MoE runs once over
                    # all sequences: identical operations, one expert sweep per layer
                    residual = h
                    attn_pre, attn_post, attn_comb = blk.hc_mixes(h, blk.hc_attn_fn, blk.hc_attn_scale, blk.hc_attn_base)
                    x = blk.hc_pre(h, pm)
                    x = blk.attn_norm(x)
                    x = blk.attn(x, 0)
                    x = blk.hc_post(x, residual, attn_post, attn_comb)
                    residual = x
                    ffn_pre, ffn_post, ffn_comb = blk.hc_mixes(x, blk.hc_ffn_fn, blk.hc_ffn_scale, blk.hc_ffn_base)
                    x = blk.hc_pre(x, attn_pre)
                    x = blk.ffn_norm(x)
                    stash[j] = (x, residual.cpu(), ffn_post, ffn_comb, ffn_pre)
                    H[j] = None
                    SA[j] = {k: (None if getattr(V.shared_attn, k) is None else getattr(V.shared_attn, k).cpu())
                             for k in SA[j]}
                    del h, pm, residual
                lens = [stash[j][0].size(1) for j in range(N)]
                y = blk.ffn(torch.cat([stash[j][0] for j in range(N)], dim=1), None)
                ys = torch.split(y, lens, dim=1)
                for j in range(N):
                    _, residual, ffn_post, ffn_comb, ffn_pre = stash[j]
                    h = blk.hc_post(ys[j], residual.to(DEV), ffn_post, ffn_comb)
                    if i == args.n_layers - 1:
                        h = blk.hc_pre(h, ffn_pre)  # vendor: h = layer.hc_pre(h, pre_mix) after the loop
                    H[j], PM[j] = h.cpu(), ffn_pre.cpu()
                    stash[j] = None
                del y, ys
                torch.cuda.synchronize()
                self._t("compute_s", time.time() - t1)
                del blk
            self.ck.drop_cache(names)
            self.log(f"  [{tag}] {time.time()-t0:5.2f}s peak={torch.cuda.max_memory_allocated()/1e9:.2f}GB "
                     f"read={self.ck.bytes_read/1e9:.1f}GB")
        t1 = time.time()
        rms = V.RMSNorm(args.dim, args.norm_eps).to(DEV)
        rms.weight.data.copy_(norm_w)
        head_w = head_w.float()  # vendor ParallelHead keeps the head in fp32
        out = {"argmax": [], "top2gap": [], "logp_next": [], "main_hidden": [torch.cat(m, -1) for m in MH]}
        for j in range(N):
            x = rms(H[j].to(DEV))[0]
            T = x.size(0)
            am = torch.empty(T, dtype=torch.long, device="cpu")
            gap = torch.empty(T, dtype=torch.float32, device="cpu")
            lpn = torch.full((T,), float("nan"), dtype=torch.float32, device="cpu")
            for s in range(0, T, 256):
                lg = torch.nn.functional.linear(x[s:s + 256].float(), head_w)
                am[s:s + 256] = lg.argmax(-1).cpu()
                tv = lg.topk(2, -1).values
                gap[s:s + 256] = (tv[:, 0] - tv[:, 1]).cpu()
                nxt = ids[j][0, s + 1:s + 257]
                k = nxt.numel()
                if k:
                    lpn[s:s + k] = lg[:k].log_softmax(-1)[torch.arange(k, device=DEV), nxt].cpu()
            out["argmax"].append(am); out["top2gap"].append(gap); out["logp_next"].append(lpn)
        del head_w
        self._t("head_s", time.time() - t1)
        self._t("pass_s", time.time() - t_pass)
        out.update(timing=dict(self.timing), bytes_read=self.ck.bytes_read, read_seconds=self.ck.read_seconds,
                   engram_rows=engram_rows)
        return out


def _log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--traces", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gpu-cap-gb", type=float, default=GPU_CAP_GB)
    a = ap.parse_args()
    tr = json.load(open(a.traces))
    seqs = [torch.tensor(t["ids"], dtype=torch.long, device="cpu") for t in tr]
    eng = Engine(max(len(s) for s in seqs) + 16, a.gpu_cap_gb, _log)
    out = eng.main_pass(seqs)
    torch.save(out, a.out)
    _log(f"main pass {out['timing']['pass_s']:.1f}s tokens={sum(len(s) for s in seqs)} "
         f"timing={out['timing']} -> {a.out}")


if __name__ == "__main__":
    main()
