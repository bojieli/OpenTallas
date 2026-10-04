#!/usr/bin/env python3
"""GPU-backed exact ISA golden for a Qwen3-8B ROM TP4 DSpark speculative step at a nonzero position.

Default-off, new file: the pinned oracles (tools/qwen_rom_position_oracle_w12.py,
tools/qwen_o4_layer0_oracle_w12.py, tools/qwen_o4_token_oracle_w12.py, tools/hdc_golden.py)
are imported, never edited.  Only the DENSE matvec moves to the GPU:

  gpu_matvec(wT, x, split)  ==  hdc_golden.matvec(w, x, split)  (bit for bit)
      x rounded to BF16 (G.to_bf16, on the host), chunk c = columns [c*kc, (c+1)*kc),
      each chunk summed sequentially from +0 as acc = z(acc + z(w*x)) (one CUDA
      elementwise kernel per IEEE operation: no FMA contraction, no flush-to-zero;
      z canonicalises a zero result to +0 as G.add / G.mul do), then the chunk sums
      added by the pairwise tree ((c0+c1)+(c2+c3)) -- exactly matvec_chunked.

Everything else (stream-unit ops, attention over the KV window, all-reduce fold, head
argmax) is the pinned NumPy golden.  --selftest checks the kernel against G.matvec on
random and denormal operands before any run.

Phases (one process, state kept in RAM; positions in LAYER-MAJOR order, which is exact:
layer n at position p reads only layer n's KV of positions < p and position p's VM after
layer n-1, and the full per-position VM is carried, as the position oracle carries it):

  prefill   positions 0 .. P-1 of the prompt (sequential-decode golden prefill), per layer
            and die the KV window before P  -> kv_P<P>/L<n>_die<d>.bin (u32, the runtime's
            --kv-dir format); the target features (X after layers 1, 9, 17, 25, 33) of every
            committed position for the drafter.
  block     the AR golden of the verify block [t_P, d1, d2, d3] at positions P .. P+3: per
            layer, die and position the input and output X (hex), the K/V the position writes;
            the AR head (lm_head image + final norm, tools/qwen_o4_token_oracle_w12.py
            HeadMachine) per position: argmax token and logit bits.

Drafts come from tools/qwen_rom_dspark_drafter_golden.py golden_step (W8 contract, KV fp8,
single-core order) fed with THIS golden's target features; see --drafter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault('QWEN_O4_GROUPS', '6144')
os.environ.setdefault('QWEN_O4_TP', '4')
os.environ.setdefault('HDC_SU_WIDTH', '1024')
os.environ.setdefault('HDC_KV_FMT', 'fp8')
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import torch  # noqa: E402

import hdc_golden as G  # noqa: E402
import hdc_isa as I  # noqa: E402
import hdc_program as P  # noqa: E402
import hdc_qwen_fullshape_program_w12 as FP  # noqa: E402
import qwen_o4_layer0_oracle_w12 as L0  # noqa: E402
import qwen_o4_token_oracle_w12 as TO  # noqa: E402
import qwen_rom_position_oracle_w12 as PO  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEV = torch.device('cuda')
if not torch.cuda.is_available():   # this host's CUDA init fails intermittently: the caller retries (exit 75)
    print('CUDA unavailable at init', flush=True)
    sys.exit(75)
TP, W = PO.TP, PO.W
X_BASE = PO.X_BASE
FEATURE_LAYERS = (1, 9, 17, 25, 33)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---- the exact GPU matvec ---------------------------------------------------------------------
def _z(t):
    return torch.where(t == 0, torch.zeros((), dtype=t.dtype, device=t.device), t)


def gpu_wT(codes, split):
    """codes [n, k] (int8 or float) -> GPU float32 [kc, split, n] with wT[k, c, n] = w[n, c*kc + k]."""
    n, k = codes.shape
    kc = k // split
    assert kc * split == k
    t = torch.as_tensor(np.ascontiguousarray(codes), device=DEV).to(torch.float32)
    return t.reshape(n, split, kc).permute(2, 1, 0).contiguous()


@torch.no_grad()
def gpu_matvec(wT, x, split):
    """hdc_golden.matvec(w, x, split), bit-exact (see the module docstring)."""
    kc = wT.shape[0]
    xb = G.to_bf16(np.asarray(x, dtype=np.float32))
    xr = torch.as_tensor(xb.reshape(split, kc), device=DEV)
    acc = torch.zeros(wT.shape[1:], dtype=torch.float32, device=DEV)
    for k in range(kc):
        prod = _z(torch.mul(wT[k], xr[:, k:k + 1]))
        acc = _z(torch.add(acc, prod))
    while acc.shape[0] > 1:
        acc = _z(torch.add(acc[0::2], acc[1::2]))
    return acc[0].cpu().numpy()


def selftest(seed=1):
    rng = np.random.default_rng(seed)
    torch.backends.cuda.matmul.allow_tf32 = False
    cases = 0
    for n, k, split in ((300, 512, 8), (64, 4096, 16), (37, 96, 1), (128, 1024, 64)):
        w = rng.integers(-128, 128, size=(n, k)).astype(np.float32)
        for kind in ('normal', 'denormal', 'cancel'):
            if kind == 'normal':
                x = rng.standard_normal(k).astype(np.float32)
            elif kind == 'denormal':
                x = (rng.standard_normal(k) * 1e-39).astype(np.float32)   # BF16-representable subnormals
                x[::7] = -x[::7]
            else:
                x = rng.standard_normal(k).astype(np.float32)
                w[:, 1::2] = -w[:, 0::2]
                x[1::2] = x[0::2]                                         # exact cancellations -> zero sums
            ref = G.matvec(w, x, split)
            got = gpu_matvec(gpu_wT(w, split), x, split)
            if not np.array_equal(G.bits(ref), G.bits(got)):
                raise SystemExit(f'GPU matvec differs from G.matvec: n={n} k={k} split={split} {kind}: '
                                 f'{int(np.sum(G.bits(ref) != G.bits(got)))} rows')
            cases += 1
    return cases


# ---- die machines with the GPU matvec ------------------------------------------------------------
class GpuDieMachine(PO.FastDieMachine):
    _gw = {}

    def me(self, f, dyn):
        if f['me_wsrc']:
            return P.Machine.me(self, f, dyn)
        meta = self.image.layout[f['me_wbase']]
        n = f['me_nout'] + dyn[f['me_d_nout']]
        split = 1 << f['me_split']
        if n != meta['rows'] or split != meta['split']:
            raise ValueError(f'ISA/matrix geometry mismatch: {meta["name"]}')
        key = (id(self.image), meta['base'])
        if key not in self._gw:
            codes, scales = self.image.matrix(meta)
            self._gw[key] = (gpu_wT(codes, split), scales)
        wT, scales = self._gw[key]
        xbase = f['me_xbase'] + dyn[f['me_d_xbase']]
        x = self.vm[xbase:xbase + meta['columns']]
        raw = gpu_matvec(wT, x, split)
        out = raw if meta['name'] in ('o', 'down') else G.mul(raw, scales)
        if not f['me_oen']:
            raise ValueError('layer oracle expects each matrix to write VM')
        self.vm[f['me_obase'] * W:f['me_obase'] * W + n] = out

    @classmethod
    def drop(cls):
        cls._gw.clear()
        torch.cuda.empty_cache()


class GpuHeadMachine(TO.HeadMachine):
    _gw = {}

    def me(self, f, dyn):
        if f['me_wsrc']:
            raise ValueError('head has no KV-sourced op')
        n = f['me_nout'] + dyn[f['me_d_nout']]
        row0 = f.get('me_row0', 0)
        split = 1 << f['me_split']
        geo = self.image.manifest['geometry']
        if split != geo['split'] or not f['me_round'] or not f['me_amax']:
            raise ValueError('head chunk geometry changed')
        per_round, kc = PO.GROUPS // split, geo['k_per_split']
        if f['me_wbase'] != row0 // (per_round * W * PO.I.INTERLEAVE) * kc * PO.I.INTERLEAVE or f['me_wcs'] != row0 // W:
            raise ValueError('head chunk code/scale base does not match its first row')
        key = id(self.image)
        if key not in self._gw:
            self._gw[key] = gpu_wT(self.image.codes, split)
        wT = self._gw[key]
        xbase = f['me_xbase'] + dyn[f['me_d_xbase']]
        x = self.vm[xbase:xbase + 4096]
        raw = gpu_matvec(wT[:, :, row0:row0 + n], x, split)
        out = G.mul(raw, self.image.scales[row0:row0 + n])
        if f['me_oen']:
            raise ValueError('head chunk writes VM')
        self.logits = np.concatenate([self.logits, out]) if f['me_amc'] else out
        self.argmax = int(np.argmax(self.logits))


# ---- runner --------------------------------------------------------------------------------------
class Golden:
    def __init__(self, layer_dirs, head_dirs, binding, layers, out):
        self.layer_dirs, self.head_dirs, self.binding = layer_dirs, head_dirs, binding
        self.layers = layers
        self.out = Path(out)
        self.kv = {}          # (layer, die) -> current KV window (np.float32), carried across positions
        self.image_sha = {}

    def images(self, n):
        ims = [PO.StageImage(self.layer_dirs.format(layer=n, die=d), n) for d in range(TP)]
        if any(im.descriptors != ims[0].descriptors for im in ims):
            raise ValueError('TP descriptor mismatch')
        self.image_sha[f'L{n}'] = [im.image_sha for im in ims]
        return ims

    def run_positions(self, tokens, positions, vms_in, hook=None):
        """Layer-major AR over (token, position) pairs; vms_in: per position, per die full VM.
        hook(n, j, die_vms_before, die_vms_after, machines) records."""
        vms = [list(v) for v in vms_in]
        for n in range(self.layers):
            t0 = time.time()
            ims = self.images(n)
            ms = [GpuDieMachine(im) for im in ims]
            for d, m in enumerate(ms):
                if (n, d) in self.kv:
                    m.kv = self.kv[(n, d)]
            for j, (tok, pos) in enumerate(zip(tokens, positions)):
                before = [v.copy() for v in vms[j]] if hook else None
                vms[j] = PO.run_layer(ims, ms, vms[j], tok, pos)
                if hook:
                    hook(n, j, before, vms[j], ms)
            for d, m in enumerate(ms):
                self.kv[(n, d)] = m.kv
            GpuDieMachine.drop()
            PO.FastDieMachine._wt.clear()
            print(f'  layer {n}: {len(tokens)} positions {time.time() - t0:.0f} s', flush=True)
        return vms

    def head(self, x):
        """AR head of one position's X (tools/qwen_rom_verify_head_oracle_w12.py semantics)."""
        layout0 = json.loads((Path(self.layer_dirs.format(layer=0, die=0)) / 'layer0_rom.json').read_text())['matrix_layout']
        logits_all, per_die = [], []
        with FP.program_geometry(PO.VM):
            for d in range(TP):
                im = self._head_image(d)
                vm = np.zeros(L0.VM_ELEMS, dtype=np.float32)
                vm[PO.VM['X']:PO.VM['X'] + 4096] = x
                m = GpuHeadMachine(im, d, vm, layout0)
                dyn = P.dyn_values(m.lay, token=0, pos=0)
                for f in im.program:
                    if f['unit'] == I.UNIT_ME:
                        m.me(f, dyn)
                    elif f['unit'] == I.UNIT_SU:
                        m.su(f, dyn)
                logits_all.append(np.asarray(m.logits, dtype=np.float32))
                per_die.append({'argmax_local': m.argmax,
                                'logit_bits': f'{int(G.bits(np.float32(m.logits[m.argmax]))):08x}'})
        logits = np.concatenate(logits_all)
        tok = int(np.argmax(logits))
        top2 = np.sort(logits)[-2:]
        return {'argmax_token': tok, 'logit_bits': f'{int(G.bits(np.float32(logits[tok]))):08x}',
                'top2_margin': float(top2[1] - top2[0]), 'per_die': per_die}, logits

    _heads = {}

    def _head_image(self, d):
        if d not in self._heads:
            self._heads[d] = TO.HeadImage(self.head_dirs.format(die=d), self.binding, d)
        return self._heads[d]


def fresh_vm(x):
    vm = np.zeros(L0.VM_ELEMS, dtype=np.float32)
    vm[X_BASE:X_BASE + 4096] = x
    return vm


def write_hex(path, v):
    with open(path, 'w') as s:
        for b in G.bits(np.asarray(v, dtype=np.float32)):
            s.write(f'{int(b):08x}\n')


def kv_bin(path, kv):
    G.bits(kv).astype('<u4').tofile(path)


class Emb:
    """FP32 X rows of tokens: the realmem npz (prompt rows) or the pinned snapshot (any token)."""

    def __init__(self, npz, snapshot):
        self.rows, self.src = {}, {}
        if npz:
            z = np.load(npz)
            for t, sc, cd in zip(z['tokens'], z['scales'], z['codes']):
                x = (cd.view(np.int8).astype(np.float32) * np.float32(G.from_bits(np.uint32(sc) << np.uint32(16)))).astype(np.float32)
                self.rows[int(t)] = x
                self.src[int(t)] = 'npz'
        self.snapshot = snapshot

    def __call__(self, t):
        if t not in self.rows:
            r = PO.embedding_x(self.snapshot, [t])[t]
            self.rows[t] = r[0]
            self.src[t] = 'snapshot'
        return self.rows[t]


# ---- the DSpark drafter (tools/qwen_rom_dspark_drafter_golden.py golden_step, GPU dense matvec) -------
class Drafter:
    """golden_step of the pinned drafter golden (W8 contract, single-core order), its dense matvecs on the
    GPU (gpu_matvec == G.matvec), fed with THIS golden's target features (X after layers 1, 9, 17, 25, 33)."""

    def __init__(self, draft_dir, kv='fp8'):
        import qwen_rom_dspark_drafter_golden as DG
        from safetensors import safe_open
        self.DG, self.kv = DG, kv
        self.cfg = json.loads((Path(draft_dir) / 'config.json').read_text())
        self.mask_id = int(self.cfg['mask_token_id'])
        assert tuple(self.cfg['target_layer_ids']) == FEATURE_LAYERS

        def call(w8, x):
            if not hasattr(w8, 'gw'):
                w8.gw = gpu_wT(w8.codes, w8.split)
            return G.mul(gpu_matvec(w8.gw, x, w8.split), w8.scale)
        DG.W8.__call__ = call
        t0 = time.time()
        with safe_open(str(Path(draft_dir) / 'model.safetensors'), framework='pt', device='cpu') as sf:
            g = lambda k: sf.get_tensor(k)  # noqa: E731
            vec = lambda k: g(k).float().numpy().astype(np.float32)  # noqa: E731
            W8 = DG.W8
            Wt = {'fc': W8(g('fc.weight')), 'hidden_norm': vec('hidden_norm.weight'), 'norm': vec('norm.weight'),
                  'lm_head': W8(g('lm_head.weight')), 'w2': W8(g('markov_head.markov_w2.weight')), 'layers': []}
            Wt['w1'] = W8(g('markov_head.markov_w1.weight')).deq()
            Wt['embed'] = W8(g('embed_tokens.weight')).deq()
            for L in range(5):
                p = f'layers.{L}.'
                Wt['layers'].append({'in': vec(p + 'input_layernorm.weight'), 'post': vec(p + 'post_attention_layernorm.weight'),
                                     'qn': vec(p + 'self_attn.q_norm.weight'), 'kn': vec(p + 'self_attn.k_norm.weight'),
                                     **{n: W8(g(p + f'self_attn.{n}_proj.weight')) for n in 'qkvo'},
                                     **{n: W8(g(p + f'mlp.{n}_proj.weight')) for n in ('gate', 'up', 'down')}})
        self.Wt = Wt
        self.load_seconds = round(time.time() - t0, 1)

    def draft(self, feats, anchor, start, S=3):
        t0 = time.time()
        toks, logits = self.DG.golden_step(self.Wt, np.asarray(feats[:start], dtype=np.float32), anchor, start, S,
                                           self.mask_id, self.kv)
        return {'start': start, 'anchor': anchor, 'S': S, 'kv': self.kv, 'draft_tokens': toks,
                'logit_bits': [f'{int(G.bits(np.float32(logits[j][toks[j]]))):08x}' for j in range(S)],
                'seconds': round(time.time() - t0, 1)}


def accept(drafts, ys):
    a = 0
    while a < len(drafts) and drafts[a] == ys[a]:
        a += 1
    return a


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--mode', choices=('selftest', 'qualify0', 'run'), required=True)
    ap.add_argument('--layer-dirs', default='/home/ubuntu/qwen-dspark-oracle-run/img_tp4/L{layer}-d{die}')
    ap.add_argument('--head-dirs', default='/home/ubuntu/qwen-dspark-oracle-run/img_tp4/head-d{die}')
    ap.add_argument('--binding', type=Path, default=Path('/home/ubuntu/qwen-dspark-oracle-run/img_tp4/binding'))
    ap.add_argument('--layers', type=int, default=36)
    ap.add_argument('--tokens', type=Path, help='prompt token ids')
    ap.add_argument('--embedding-npz', type=Path)
    ap.add_argument('--snapshot', type=Path)
    ap.add_argument('--draft-dir', type=Path)
    ap.add_argument('--P', type=int, default=255)
    ap.add_argument('--S', type=int, default=3)
    ap.add_argument('--ref', type=Path, help='qualify0: retained token oracle dir; run: CPU position-oracle P dir (kv_pre/, L<nn>_die<d>_x.hex)')
    ap.add_argument('--preload', type=Path, help='qualify0: token-0 X preload (@1000)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if I.SU_WIDTH != 1024 or G.SU_WIDTH != 1024 or G.KV_FMT != 'fp8' or PO.GROUPS != 6144 or TP != 4:
        raise SystemExit('requires QWEN_O4_GROUPS=6144 QWEN_O4_TP=4 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8')
    t_all = time.time()
    a.out.mkdir(parents=True, exist_ok=True)
    rec = {'schema': 'opentallas.qwen-dspark-oracle-gpu.v1', 'mode': a.mode, 'torch': torch.__version__,
           'gpu': torch.cuda.get_device_name(0), 'selftest_cases': selftest(),
           'source_sha256': {q: sha(ROOT / q) for q in (
               'tools/qwen_rom_dspark_oracle_gpu_w12.py', 'tools/qwen_rom_position_oracle_w12.py',
               'tools/qwen_o4_layer0_oracle_w12.py', 'tools/qwen_o4_token_oracle_w12.py', 'tools/hdc_golden.py',
               'tools/hdc_program.py', 'tools/hdc_isa.py', 'tools/hdc_qwen_fullshape_program_w12.py',
               'tools/hdc_qwen_fullshape_isa_w12.py', 'tools/qwen_rom_dspark_drafter_golden.py')}}
    print(f'selftest: {rec["selftest_cases"]} GPU matvec cases bit-equal to hdc_golden.matvec', flush=True)
    if a.mode == 'selftest':
        return
    rec_path = a.out / 'oracle.json'
    save = lambda: rec_path.write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')  # noqa: E731
    gold = Golden(a.layer_dirs, a.head_dirs, a.binding, a.layers, a.out)

    if a.mode == 'qualify0':
        # retained TP4 token oracle (position 0, token 0): every layer's X on every die, and the head
        x0 = L0._preload_x(a.preload)
        bad = {}

        def hook(n, j, before, after, ms):
            for d in range(TP):
                exp = np.array([int(s, 16) for s in (a.ref / f'L{n:02d}_die{d}_x.hex').read_text().split()], dtype=np.uint32)
                got = G.bits(after[d][X_BASE:X_BASE + 4096])
                bad[f'L{n}_die{d}'] = int(np.sum(exp != got))
        vms = gold.run_positions([0], [0], [[fresh_vm(x0) for _ in range(TP)]], hook)
        rec['layer_x_mismatches_total'] = sum(bad.values())
        rec['layer_x_checks'] = len(bad)
        if a.layers == 36:
            h, _ = gold.head(vms[0][0][X_BASE:X_BASE + 4096])
            ref = json.loads((a.ref / 'oracle.json').read_text())
            rec['head'] = h
            rec['head_equal'] = (h['argmax_token'] == ref['next_token'] and h['logit_bits'] == ref['next_logit_bits'])
        rec['wall_seconds'] = round(time.time() - t_all, 1)
        save()
        print(json.dumps({k: rec[k] for k in ('layer_x_mismatches_total', 'layer_x_checks', 'head_equal', 'wall_seconds') if k in rec}))
        return

    # ---- run: prefill, drafts, block AR, accept, step 2 ------------------------------------------
    prompt = [int(t) for t in a.tokens.read_text().split()]
    Pp, S = a.P, a.S
    emb = Emb(a.embedding_npz, a.snapshot)
    rec.update({'P': Pp, 'S': S, 'prompt_tokens_sha256': sha(a.tokens), 'prompt_head': prompt[:Pp + 1],
                'claim_boundary': 'ISA golden (hdc_golden arithmetic, pinned TP4 images and programs; dense matvec on the '
                                  'GPU, bit-equal to G.matvec). Not an RTL verdict.'})
    feats = {}                           # position -> [5, 4096] target features (X after layers 1, 9, 17, 25, 33)
    kv_snap = {}                         # tag -> {(n, d): kv copy}
    qual = {'checks': 0, 'mismatches': 0}

    def x_of(v):
        return v[X_BASE:X_BASE + 4096]

    def make_hook(positions, record_dir, snap_at):
        """record X in/out and K/V written per block position; snapshot KV windows: snap_at = {position: tag}
        taken BEFORE that position runs (the window of the committed positions < it)."""
        def hook(n, j, before, after, ms):
            pos = positions[j]
            for d in range(TP):
                if not np.array_equal(G.bits(x_of(after[0])), G.bits(x_of(after[d]))):
                    raise SystemExit(f'dies disagree at layer {n} position {pos}')
            if n in FEATURE_LAYERS:
                feats.setdefault(pos, np.zeros((5, 4096), dtype=np.float32))[FEATURE_LAYERS.index(n)] = x_of(after[0])
            if record_dir is not None and pos in record_dir:
                pdir = record_dir[pos]
                for d in range(TP):
                    write_hex(pdir / f'L{n:02d}_die{d}_xin.hex', x_of(before[d]))
                    write_hex(pdir / f'L{n:02d}_die{d}_x.hex', x_of(after[d]))
                    lay, kv = ms[d].lay, ms[d].kv
                    kel = [lay.k_elem(0, h, pos, dim) for h in range(lay.KV) for dim in range(lay.HD)]
                    vel = [lay.v_elem(0, h, pos, dim) for h in range(lay.KV) for dim in range(lay.HD)]
                    (pdir / 'kv_at_P').mkdir(exist_ok=True)
                    (pdir / 'kv_at_P' / f'L{n}_die{d}.json').write_text(json.dumps(
                        {'k_elem': kel, 'k_bits': [f'{int(b):08x}' for b in G.bits(kv[kel])],
                         'v_elem': vel, 'v_bits': [f'{int(b):08x}' for b in G.bits(kv[vel])]}) + '\n')
                # qualification against the CPU position oracle at the same position (layers it has)
                if a.ref is not None and pos == Pp and (a.ref / f'L{n:02d}_die0_x.hex').exists():
                    for d in range(TP):
                        exp = np.array([int(s, 16) for s in (a.ref / f'L{n:02d}_die{d}_x.hex').read_text().split()], dtype=np.uint32)
                        qual['checks'] += 1
                        qual['mismatches'] += int(np.sum(exp != G.bits(x_of(after[d]))))
                    if qual['mismatches']:
                        rec['qualification_cpu_P'] = qual
                        save()
                        raise SystemExit(f'GPU golden differs from the CPU position oracle at layer {n}: {qual}')
        return hook

    def run_block(tokens, positions, vms, record_dir, snap_before):
        # layer-major with per-position KV snapshots (taken inside run_layer order)
        out_vms = [list(v) for v in vms]
        for n in range(gold.layers):
            t0 = time.time()
            ims = gold.images(n)
            ms = [GpuDieMachine(im) for im in ims]
            for d, m in enumerate(ms):
                if (n, d) in gold.kv:
                    m.kv = gold.kv[(n, d)]
            hook = make_hook(positions, record_dir, snap_before)
            for j, (tok, pos) in enumerate(zip(tokens, positions)):
                if pos in snap_before:
                    for d in range(TP):
                        kv_snap.setdefault(snap_before[pos], {})[(n, d)] = ms[d].kv.copy()
                before = [v.copy() for v in out_vms[j]] if (record_dir and pos in record_dir) else [None] * TP
                if before[0] is None:
                    before = out_vms[j]
                out_vms[j] = PO.run_layer(ims, ms, out_vms[j], tok, pos)
                hook(n, j, before, out_vms[j], ms)
            for d, m in enumerate(ms):
                gold.kv[(n, d)] = m.kv
            GpuDieMachine.drop()
            print(f'  layer {n}: {len(tokens)} positions {time.time() - t0:.0f} s', flush=True)
            if a.ref is not None and n < 3 and (a.ref / 'kv_pre').exists() and Pp in snap_before and snap_before[Pp] == 'P':
                for d in range(TP):
                    exp = np.load(a.ref / 'kv_pre' / f'L{n}_die{d}.npy')
                    qual['checks'] += 1
                    qual['mismatches'] += int(np.sum(exp != G.bits(kv_snap['P'][(n, d)])))
                rec['qualification_cpu_P'] = qual
                save()
                if qual['mismatches']:
                    raise SystemExit(f'KV window differs from the CPU position oracle at layer {n}: {qual}')
        return out_vms

    def heads(vms, positions, tokens, tag):
        hs = []
        for j, pos in enumerate(positions):
            h, _ = gold.head(x_of(vms[j][0]))
            h.update(position=pos, input_token=tokens[j])
            hs.append(h)
            print(f'  head {tag} position {pos}: token {h["argmax_token"]} ({h["logit_bits"]})', flush=True)
        return hs

    def dump_kv(tag, P_):
        d_ = a.out / f'kv_P{P_}'
        d_.mkdir(exist_ok=True)
        dig = {}
        for (n, d), kv in sorted(kv_snap[tag].items()):
            path = d_ / f'L{n}_die{d}.bin'
            kv_bin(path, kv)
            dig[f'L{n}_die{d}'] = sha(path)
        return str(d_), dig

    # prefill 0 .. P-1 and the pending token at P (independent of the drafts), layer-major
    t0 = time.time()
    toks0 = prompt[:Pp + 1]
    pos0 = list(range(Pp + 1))
    vms0 = [[fresh_vm(emb(t)) for _ in range(TP)] for t in toks0]
    rec['embedding_source'] = {str(t): emb.src[t] for t in sorted(set(toks0))}
    s1 = a.out / f'step1_P{Pp}'
    pdirs = {}
    for j in range(S + 1):
        pdirs[Pp + j] = s1 / f'pos{Pp + j}'
        pdirs[Pp + j].mkdir(parents=True, exist_ok=True)
    for j, t in enumerate(toks0):
        if Pp in pdirs and j == Pp:
            write_hex(pdirs[Pp] / 'x_embed.hex', emb(t))
    vms0 = run_block(toks0, pos0, vms0, {Pp: pdirs[Pp]}, {Pp: 'P'})
    rec['prefill_seconds'] = round(time.time() - t0, 1)
    rec['kv_dir_P'], rec['kv_P_sha256'] = dump_kv('P', Pp)
    save()
    # drafts at P: anchor = prompt[P], context = features of positions 0 .. P-1
    dr = Drafter(a.draft_dir)
    rec['drafter'] = {'golden': 'tools/qwen_rom_dspark_drafter_golden.py golden_step (W8 contract, single-core order)',
                      'kv': 'fp8', 'checkpoint': str(a.draft_dir), 'features': 'this golden: X after layers 1, 9, 17, 25, 33',
                      'load_seconds': dr.load_seconds}
    F1 = np.stack([feats[p] for p in range(Pp)]).reshape(Pp, -1)
    d1 = dr.draft(F1, prompt[Pp], Pp, S)
    rec['step1_draft'] = d1
    save()
    print('step1 drafts', d1, flush=True)
    btoks = [prompt[Pp]] + d1['draft_tokens']
    bpos = list(range(Pp, Pp + S + 1))
    for j in range(1, S + 1):
        write_hex(pdirs[Pp + j] / 'x_embed.hex', emb(btoks[j]))
    # positions P+1 .. P+S continue from the KV windows after P (vms of P carried for its head)
    t0 = time.time()
    rest = run_block(btoks[1:], bpos[1:], [[fresh_vm(emb(t)) for _ in range(TP)] for t in btoks[1:]],
                     {p: pdirs[p] for p in bpos[1:]}, {p: f'commit{p}' for p in bpos[1:]})
    bvms = [vms0[Pp]] + rest
    hs1 = heads(bvms, bpos, btoks, 'step1')
    ys = [h['argmax_token'] for h in hs1]
    acc = accept(d1['draft_tokens'], ys)
    rec['step1'] = {'P': Pp, 'block_tokens': btoks, 'positions': bpos, 'argmax': ys, 'heads': hs1, 'accepted': acc,
                    'emitted': ys[:acc + 1], 'block_seconds': round(time.time() - t0, 1)}
    save()
    print(f'step1 block {btoks} argmax {ys} accepted {acc}', flush=True)
    if acc == S:
        rec['note'] = 'all drafts accepted at P: no rejection; choose another P'
        save()
        raise SystemExit('a == S: no rejected draft at this P')
    # step 2: P' = P + a + 1, KV windows = committed positions < P' only (snapshot before P')
    P2 = Pp + acc + 1
    kv_tag = f'commit{P2}'
    gold.kv = {k: v.copy() for k, v in kv_snap[kv_tag].items()}
    rec['kv_dir_P2'], rec['kv_P2_sha256'] = dump_kv(kv_tag, P2)
    for j in range(acc + 1):                 # committed block positions' features (X of the AR golden)
        assert Pp + j in feats
    F2 = np.stack([feats[p] for p in range(P2)]).reshape(P2, -1)
    d2 = dr.draft(F2, ys[acc], P2, S)
    rec['step2_draft'] = d2
    save()
    print('step2 drafts', d2, flush=True)
    btoks2 = [ys[acc]] + d2['draft_tokens']
    bpos2 = list(range(P2, P2 + S + 1))
    s2 = a.out / f'step2_P{P2}'
    pdirs2 = {}
    for j, p in enumerate(bpos2):
        pdirs2[p] = s2 / f'pos{p}'
        pdirs2[p].mkdir(parents=True, exist_ok=True)
        write_hex(pdirs2[p] / 'x_embed.hex', emb(btoks2[j]))
    t0 = time.time()
    bvms2 = run_block(btoks2, bpos2, [[fresh_vm(emb(t)) for _ in range(TP)] for t in btoks2], pdirs2, {})
    hs2 = heads(bvms2, bpos2, btoks2, 'step2')
    ys2 = [h['argmax_token'] for h in hs2]
    acc2 = accept(d2['draft_tokens'], ys2)
    rec['step2'] = {'P': P2, 'block_tokens': btoks2, 'positions': bpos2, 'argmax': ys2, 'heads': hs2, 'accepted': acc2,
                    'emitted': ys2[:acc2 + 1], 'block_seconds': round(time.time() - t0, 1)}
    rec['embedding_source'] = {str(t): emb.src[t] for t in sorted(emb.src)}
    rec['layer_image_sha256'] = gold.image_sha
    # digests of every recorded file
    dig = {}
    for root in (s1, s2):
        for f in sorted(root.rglob('*')):
            if f.is_file():
                dig[str(f.relative_to(a.out))] = sha(f)
    rec['file_sha256'] = dig
    rec['wall_seconds'] = round(time.time() - t_all, 1)
    save()
    print(json.dumps({'P': Pp, 'block': btoks, 'argmax': ys, 'a': acc, 'P2': P2, 'block2': btoks2, 'argmax2': ys2,
                      'a2': acc2, 'wall_seconds': rec['wall_seconds']}))


if __name__ == '__main__':
    main()
