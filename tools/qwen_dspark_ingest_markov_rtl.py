#!/usr/bin/env python3
"""Qwen3-8B ROM DSpark drafter: context ingest + Markov epilogue as RTL stages at P ~8,191 (default-off helper).

The drafter step's two terms that were priced only (results/rtl/qwen_dspark_system_20261004/ctx8k:
ingest 3,024 + Markov 4,851 = 7,875 cycles, tools/qwen_rom_dspark_drafter_rom.py) are run here as the minimum
components on the VPRM REAL_MEM die (tools/qwen_rom_rt_vprm_w12.py, the same build as the ctx8k components),
each exact against the ISA golden of the same program (GPU matvec, tools/qwen_rom_position_oracle_w12.run_layer):

  ING   (layer -1)  3 newly committed context tokens: FC 20,480 -> 4,096 (rows split by die; existing W12 row
                    projection, tools/qwen_rom_dspark_images.projection_program) x 3, the all-gather of the
                    1,024-row slices as ONE one-stream all-reduce of zero-padded vectors (3 x 4,096 words), then
                    hidden_norm (RMSNorm, the target's SU sequence) x 3 -> ctx_j
  CTXj  (layer 0, P = 8185+j, np 1)  the drafter layer-0 context K/V ingest of ctx_j
                    (tools/qwen_rom_dspark_images.context_kv_program: QKV .. K/V rows written to HBM); the 5 drafter
                    layers have the same shape, so a layer's term is measured once and composed x 5
  MKV   (layer -1)  one Markov slot: w2 (37,984 x 256 a die) . w1[prev] (the W8 w1 row, dequantised) and the add
                    of the base logits, in vector memory (sequential over the S = 3 slots)

Not in RTL (recorded as such): the w1 row lookup (an IO-edge ROM, host-preloaded here) and the biased argmax over
the 37,984 logits + the cross-die argmax gather (the stream unit has SUM/MAX reducers but no argmax; the ME argmax
cannot see the added bias).  Inputs are real operands: FC features are the target's hidden states after layers
1, 9, 17, 25, 33 at P 8185..8187 of the 8,192-token prompt, the base logits are the target's logits at P 8191 and
prev is the prompt token at 8191 (local GPU, HF transformers; operands only, never a reference for exactness).

  prep    (local GPU)  --snapshot-target --tokens --out           -> operands.npz
  build   (local)      --images <dspark images> --operands --out  -> stage dirs + manifests
  golden  (local GPU)  --stages --operands --out --remote-root    -> per job: x_preload, plan, expect, kv
  collect              --res <dir of k_*.json> --out              -> record
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

TP, H, NCTX, FEAT = 4, 4096, 3, 20480
CTX_POS0 = 8185                  # the three committed rows the step at P8191 ingests (8185..8187), start 8188
MKV_POS = 8191
TARGET_LAYERS = (1, 9, 17, 25, 33)
# vector-memory map of the ING / MKV stages (elements; VM 1,048,576)
F_BASE, O_BASE, HN_BASE = 65536, 0, 147456   # O: the all-reduce region (descriptor vm_word < 256)
SSX_BASE, RX_BASE = 160000, 160016
W1_BASE, W2_OUT, LB_BASE, MK_OUT = 0, 32768, 393216, 327680   # LB: all 151,936 base logits, die d reads its slice
NMK = 37984
FILES = ('program.hex', 'segments.hex', 'crom.hex', 'matrix_int8.hex', 'matrix_scale_bf16.hex')


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------------------------------------------- prep
def prep(a):
    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM
    toks = [int(t) for t in Path(a.tokens).read_text().split()]
    if len(toks) < MKV_POS + 1:
        raise SystemExit('prompt shorter than 8,192 tokens')
    model = AutoModelForCausalLM.from_pretrained(str(a.snapshot_target), torch_dtype=torch.bfloat16, device_map='cuda')
    model.eval()
    with torch.no_grad():
        out = model(torch.tensor([toks[:MKV_POS + 1]], device='cuda'), output_hidden_states=True)
    hs = out.hidden_states                     # [0] embeddings, [i + 1] after layer i
    feats = np.stack([np.concatenate([hs[L + 1][0, p].float().cpu().numpy() for L in TARGET_LAYERS])
                      for p in range(CTX_POS0, CTX_POS0 + NCTX)]).astype(np.float32)
    logits = out.logits[0, MKV_POS].float().cpu().numpy().astype(np.float32)
    np.savez(a.out, feats=feats, logits=logits, prev=np.int64(toks[MKV_POS]),
             ctx_positions=np.arange(CTX_POS0, CTX_POS0 + NCTX), target_layers=np.array(TARGET_LAYERS))
    print(json.dumps({'feats': list(feats.shape), 'logits': list(logits.shape), 'prev': toks[MKV_POS],
                      'feat_absmax': float(np.abs(feats).max()), 'logit_absmax': float(np.abs(logits).max())}))


# ---------------------------------------------------------------------------------------------------- programs
def ing_program(rank, fc_row, lay, eps):
    """FC x 3 (die slice rows into zero-padded O_j) | one all-reduce of the 3 x 4,096 words | hidden_norm x 3."""
    import hdc_isa as I
    import hdc_program as P
    import qwen_rom_dspark_images as DI
    prog = []
    for j in range(NCTX):
        body = DI.projection_program(lay, fc_row, F_BASE + j * FEAT, O_BASE + j * H + rank * 1024, enabled=True)
        prog.extend(f for f in body if f['unit'] == I.UNIT_ME)
    prog.append(dict(unit=I.UNIT_END, barrier=1, _coll=(P.COLL_ALLREDUCE, O_BASE // I.W_LANES, NCTX * H // I.W_LANES, 0)))
    f32 = P.f32
    for j in range(NCTX):
        prog.append(dict(unit=I.UNIT_SU, barrier=1, su_nout=1, su_nin=H, a_base=O_BASE + j * H, a_si=1,
                         red=I.RED_SUM, red_sq=1, r_base=SSX_BASE + j))
        prog.append(dict(unit=I.UNIT_SU, barrier=1, su_nout=1, su_nin=1, a_base=SSX_BASE + j, ma=I.MA_AIMM,
                         imm1=f32(1.0 / H), ad=I.AD_IMM, imm2=f32(eps), sfu=I.SFU_RSQRT, dst=I.DST_VM,
                         d_base=RX_BASE + j))
        prog.append(dict(unit=I.UNIT_SU, barrier=1, su_nout=1, su_nin=H, a_base=O_BASE + j * H, a_si=1, ma=I.MA_AB,
                         b_base=RX_BASE + j, c_src=I.SRC_ALT, c_base=0, c_si=1, mc=I.MC_C, dst=I.DST_VM,
                         d_base=HN_BASE + j * H, d_si=1))
    prog.append(dict(unit=I.UNIT_END, barrier=1, _coll=(P.COLL_END, 0, 0, 0)))
    return prog


def mkv_program(rank, w2_row, lay):
    """w2 . w1[prev] into VM, then logits = base + bias (one stream pass) -- one Markov slot."""
    import hdc_isa as I
    import hdc_program as P
    import qwen_rom_dspark_images as DI
    prog = [f for f in DI.projection_program(lay, w2_row, W1_BASE, W2_OUT, enabled=True) if f['unit'] == I.UNIT_ME]
    prog.append(dict(unit=I.UNIT_SU, barrier=1, su_nout=1, su_nin=NMK, a_base=LB_BASE + rank * NMK, a_si=1,
                     c_base=W2_OUT, c_si=1, ad=I.AD_C, dst=I.DST_VM, d_base=MK_OUT, d_si=1))
    prog.append(dict(unit=I.UNIT_END, barrier=1, _coll=(P.COLL_END, 0, 0, 0)))
    return prog


def write_stage(d, prog, crom_lo, layout, die, copy_from=None, link=()):
    import hdc_golden as G
    import hdc_program as P
    import qwen_rom_dspark_images as DI
    d.mkdir(parents=True, exist_ok=True)
    DI.write_program(d, '', DI.encode_program(prog))
    if crom_lo is not None:
        import numpy as np
        lo = np.asarray(crom_lo, dtype=np.float32)
        (d / 'crom.hex').write_text(P.hexwords((int(G.bits(v)) for v in lo), 64))
    for name in link:
        dst = d / name
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        shutil.copyfile(Path(copy_from) / name, dst)
    man = {'die': die, 'tp': TP, 'norm_fold': False, 'matrix_layout': layout, 'post_tp_scale_bases': [0, 0],
           'program_words': len((d / 'program.hex').read_text().split()),
           'image_sha256': {f: sha(d / f) for f in FILES}}
    (d / 'stage.json').write_text(json.dumps(man, indent=1) + '\n')
    return man


def build(a):
    import numpy as np
    os.environ.setdefault('QWEN_O4_TP', '4')
    import hdc_qwen_fullshape_program_w12 as FP
    import qwen_rom_dspark_images as DI
    src = Path(a.images)
    meta = json.loads((src / 'drafter_images.json').read_text())
    piece = {(p['name'], p['rank']): p['matrix'] for p in meta['pieces']}
    hn = np.load(src / 'hidden_norm.npy').astype(np.float32)
    out = Path(a.out)
    rec = {'schema': 'opentallas.qwen-dspark-ingest-markov-stages.v1', 'images': str(src),
           'images_manifest_sha256': sha(src / 'drafter_images.json'), 'stages': {}}
    eps = 1e-6
    for r in range(TP):
        row = piece[('fc', r)]
        lay = FP.LayerZero(None, r, [row] * 4)
        rec['stages'][f'ING-d{r}'] = write_stage(out / f'ING-d{r}', ing_program(r, row, lay, eps), hn, [row] * 4, r,
                                                  src / f'fc-d{r}', ('matrix_int8.hex', 'matrix_scale_bf16.hex'))
        row = piece[('markov_w2', r)]
        lay = FP.LayerZero(None, r, [row] * 4)
        rec['stages'][f'MKV-d{r}'] = write_stage(out / f'MKV-d{r}', mkv_program(r, row, lay), np.zeros(1, np.float32),
                                                  [row] * 4, r, src / f'markov_w2-d{r}',
                                                  ('matrix_int8.hex', 'matrix_scale_bf16.hex'))
        dm = json.loads((src / f'D0-d{r}' / 'drafter_layer.json').read_text())
        lay = FP.LayerZero(None, r, dm['matrix_layout'])
        lay.norm_fold = False
        for j in range(NCTX):
            d = out / f'CTX{j}-d{r}'
            prog = DI.context_kv_program(lay, CTX_POS0 + j, enabled=True)
            m = write_stage(d, prog, None, dm['matrix_layout'], r, src / f'D0-d{r}',
                            ('crom.hex', 'matrix_int8.hex', 'matrix_scale_bf16.hex'))
            m.update(post_tp_scale_bases=dm['post_tp_scale_bases'], context_position=CTX_POS0 + j,
                     context_input_vm_base=FP.vm_map()[0]['H'])
            (d / 'stage.json').write_text(json.dumps(m, indent=1) + '\n')
            rec['stages'][f'CTX{j}-d{r}'] = m
    (out / 'stages.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: v['program_words'] for k, v in rec['stages'].items() if k.endswith('d0')}))


# ---------------------------------------------------------------------------------------------------- golden
def golden(a):
    import numpy as np
    import hdc_golden as G
    import hdc_qwen_fullshape_isa_w12 as QI
    import hdc_qwen_fullshape_program_w12 as FP
    import qwen_rom_position_oracle_w12 as PO
    import qwen_rom_verify_program_w12 as V
    import qwen_rom_dspark_oracle_gpu_w12 as GO
    if not (G.SU_WIDTH == 1024 and G.KV_FMT == 'fp8'):
        raise SystemExit('run in the oracle arithmetic environment (HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8)')

    class Img(PO.StageImage):
        def __init__(self, d):   # noqa: D401 -- stage.json manifest
            self.dir = Path(d)
            m = json.loads((self.dir / 'stage.json').read_text())
            self.manifest = {'die': m['die'], 'layer': 0, 'tp': TP, 'matrix_layout': m['matrix_layout'],
                             'post_tp_scale_bases': m['post_tp_scale_bases']}
            self.meta = m
            self.image_sha = {f: sha(self.dir / f) for f in FILES}
            if self.image_sha != m['image_sha256']:
                raise SystemExit(f'stage image digest changed: {d}')
            self.layout = {row['base']: row for row in m['matrix_layout']}
            self.program = [QI.decode_instruction(int(x, 16)) for x in (self.dir / 'program.hex').read_text().split()]
            self.descriptors = [V.decode_descriptor(int(x, 16)) for x in (self.dir / 'segments.hex').read_text().split()]
            lo, hi = [], []
            for line in (self.dir / 'crom.hex').read_text().split():
                if line.startswith('@'):
                    continue
                line = line.rjust(16, '0')
                hi.append(int(line[:8], 16)); lo.append(int(line[8:16], 16))
            self.crom = np.stack((G.from_bits(np.array(lo, dtype=np.uint32)), G.from_bits(np.array(hi, dtype=np.uint32))), axis=1)
            self._mat = {}

    ops = np.load(a.operands)
    st, out, R = Path(a.stages), Path(a.out), Path(a.remote_root)
    out.mkdir(parents=True, exist_ok=True)
    rec = {'schema': 'opentallas.qwen-dspark-ingest-markov-golden.v1', 'operands_sha256': sha(a.operands),
           'stages_sha256': sha(st / 'stages.json'), 'jobs': {}}

    def machines(names):
        ims = [Img(st / f'{names}-d{d}') for d in range(TP)]
        if any(im.descriptors != ims[0].descriptors for im in ims):
            raise SystemExit('TP descriptor mismatch')
        ms = [GO.GpuDieMachine(im) for im in ims]
        for m in ms:
            m.vm = np.zeros(1 << 20, dtype=np.float32)
        return ims, ms

    def hexv(v):
        return ''.join(f'{int(w):08x}\n' for w in G.bits(np.asarray(v, dtype=np.float32)))

    def job(name, stage, layer, pos, xbases, pre, vms_out, ims, kv=None):
        jd = out / name
        jd.mkdir(exist_ok=True)
        (jd / 'x_preload.hex').write_text(pre)
        exp = {'x': {}, 'kv': {}}
        for d, vm in enumerate(vms_out):
            for j, b in enumerate(xbases):
                p = jd / f'{stage}_p{j}_die{d}_x.hex'
                p.write_text(hexv(vm[b:b + H]))
                exp['x'][f'p{j}_die{d}'] = str(R / name / p.name)
        if kv is not None:
            for d, lines in enumerate(kv):
                p = jd / f'{stage}_die{d}_kvblk.hex'
                p.write_text('\n'.join(lines) + '\n')
                exp['kv'][f'die{d}'] = str(R / name / p.name)
        dirs = ' '.join(str(R / 'stages' / f'{stage}-d{d}') for d in range(TP))
        (jd / 'plan').write_text(f'XBASES {",".join(str(b) for b in xbases)}\n'
                                 f'STAGE {stage} {layer} 0 {pos} 1 0 0 {R / name / "x_preload.hex"} {dirs}\n')
        (jd / 'expect.json').write_text(json.dumps({'stages': {stage: exp}}, indent=1) + '\n')
        rec['jobs'][name] = {'stage': stage, 'layer': layer, 'pos': pos, 'xbases': xbases,
                             'images': {f'die{d}': im.image_sha for d, im in enumerate(ims)}}

    # ING: features at F_j; outputs ctx_j at HN_j (every die holds the full vector after the all-gather)
    feats = ops['feats'].astype(np.float32)
    ims, ms = machines('ING')
    vms = []
    pre = ''
    for j in range(NCTX):
        pre += f'@{F_BASE + j * FEAT:x}\n' + hexv(feats[j])
    for m in ms:
        vm = m.vm.copy()
        for j in range(NCTX):
            vm[F_BASE + j * FEAT:F_BASE + (j + 1) * FEAT] = feats[j]
        vms.append(vm)
    res = PO.run_layer(ims, ms, vms, 0, MKV_POS)
    ctx = [res[0][HN_BASE + j * H:HN_BASE + (j + 1) * H].copy() for j in range(NCTX)]
    if any(not np.array_equal(G.bits(r[HN_BASE:HN_BASE + NCTX * H]), G.bits(res[0][HN_BASE:HN_BASE + NCTX * H])) for r in res):
        raise SystemExit('ING: dies disagree after the all-gather')
    # cross-check against the plain-numpy semantics: rows of die r = W8 FC slice, hidden_norm = G.rmsnorm
    hn = ims[0].crom[:H, 0]
    sem_ok = True
    for j in range(NCTX):
        rows = []
        for d in range(TP):
            codes, scales = ims[d].matrix(ims[d].meta['matrix_layout'][0])
            rows.append(G.mul(PO.matvec_chunked(np.ascontiguousarray(codes.astype(np.float32).reshape(1024, 2048, 10)
                                                                      .transpose(2, 1, 0)), feats[j], 2048), scales))
        ref = G.rmsnorm(np.concatenate(rows), hn, np.float32(1e-6))
        sem_ok &= bool(np.array_equal(G.bits(ref), G.bits(ctx[j])))
    rec['ing_isa_equals_semantics'] = sem_ok
    job('k_ING', 'ING', -1, MKV_POS, [HN_BASE + j * H for j in range(NCTX)], pre, res, ims)
    GO.GpuDieMachine.drop()

    # CTXj: drafter layer 0 context K/V of ctx_j at P 8185 + j (zero KV window: the program reads none)
    for j in range(NCTX):
        ims, ms = machines(f'CTX{j}')
        hb = ims[0].meta['context_input_vm_base']
        pos = CTX_POS0 + j
        vms = []
        for m in ms:
            m.kv = np.zeros(2 * m.lay.kv_v0, dtype=np.float32)
            vm = m.vm.copy()
            vm[hb:hb + H] = ctx[j]
            vms.append(vm)
        res = PO.run_layer(ims, ms, vms, 0, pos)
        kv = []
        for m in ms:
            lines = []
            for h in range(2):
                for dd in range(128):
                    lines.append(f'K 0 {h} {dd} {E4(m.kv[((h * 512 + pos // 16) * 128 + dd) * 16 + pos % 16], G):02x}')
            for h in range(2):
                for dd in range(128):
                    lines.append(f'V 0 {h} {dd} {E4(m.kv[m.lay.kv_v0 + (h * 8192 + pos) * 128 + dd], G):02x}')
            kv.append(lines)
        job(f'k_CTX{j}', f'CTX{j}', 0, pos, [hb], f'@{hb:x}\n' + hexv(ctx[j]), res, ims, kv)
        GO.GpuDieMachine.drop()
    kvdir = out / 'kv0'
    kvdir.mkdir(exist_ok=True)
    rec['kv_window'] = 'zero (written on the RTL host: L0_die<d>.bin, 2 x kv_v0 u32 zeros)'

    # MKV: w1[prev] (dequantised W8 row) at W1_BASE, die d's base-logit slice at LB_BASE
    src = Path(json.loads((st / 'stages.json').read_text())['images'])
    w1c = np.load(src / 'markov_w1_codes.npy', mmap_mode='r')
    w1s = np.load(src / 'markov_w1_scales_bf16.npy', mmap_mode='r')
    prev = int(ops['prev'])
    w1row = G.mul(np.asarray(w1c[prev], dtype=np.float32),
                  G.from_bits(np.uint32(int(w1s.reshape(-1)[prev])) << np.uint32(16)))
    logits = ops['logits'].astype(np.float32)
    ims, ms = machines('MKV')
    vms = []
    for d, m in enumerate(ms):
        vm = m.vm.copy()
        vm[W1_BASE:W1_BASE + 256] = w1row
        vm[LB_BASE:LB_BASE + TP * NMK] = logits
        vms.append(vm)
    res = PO.run_layer(ims, ms, vms, 0, MKV_POS)
    for d in range(TP):    # bias add semantics: G.add(base, w2 . w1)
        bias = res[d][W2_OUT:W2_OUT + NMK]
        if not np.array_equal(G.bits(G.add(logits[d * NMK:(d + 1) * NMK], bias)), G.bits(res[d][MK_OUT:MK_OUT + NMK])):
            raise SystemExit('MKV: add mismatch')
    nb = -(-NMK // H)
    pre = f'@{W1_BASE:x}\n' + hexv(w1row) + f'@{LB_BASE:x}\n' + hexv(logits)
    job('k_MKV', 'MKV', -1, MKV_POS, [MK_OUT + i * H for i in range(nb)] + [W2_OUT + i * H for i in range(nb)],
        pre, res, ims)
    rec['mkv'] = {'prev': prev, 'argmax_per_die_isa': [int(np.argmax(r[MK_OUT:MK_OUT + NMK])) for r in res]}
    (out / 'golden.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ('ing_isa_equals_semantics', 'mkv')}))


# ---------------------------------------------------------------------------------------------------- collect
PRICED = {'ingest': 3024, 'markov': 4851, 'markov_per_slot': 1617, 'source': 'tools/qwen_rom_dspark_drafter_rom.py '
          'draft_step_cycles.existing_rtl S=3 n_ctx=3 (results/rtl/qwen_rom_dspark_20261003/drafter/drafter_rom_schedule.json)'}
LINK_LAT, SU_WIDTH, S_SLOTS, N_LAYERS = 339, 64, 3, 5


def collect(a):
    res = Path(a.res)
    jobs = {}
    for name in ('k_ING', 'k_CTX0', 'k_CTX1', 'k_CTX2', 'k_MKV'):
        r = json.loads((res / f'{name}.json').read_text())
        st = next(iter(r['stages'].values()))
        bad = {k: v['mismatches'] for k, v in r['checks'].items() if v['mismatches']}
        exact = r['status'] == 'pass' and not bad and r['returncode'] == 0
        jobs[name] = {'cycles': st['cycles'], 'exact': exact, 'checks': len(r['checks']), 'mismatching_checks': bad,
                      'status': r['status'], 'faults': {k: st.get(k) for k in ('seq_fault', 'core_fault', 'coll_fault') if k in st},
                      'binary_sha256': r['binary_sha256'], 'result_sha256': sha(res / f'{name}.json'),
                      'simulate_wall_seconds': r.get('simulate_wall_seconds')}
    ing = jobs['k_ING']['cycles']
    ctx_layer = sum(jobs[f'k_CTX{j}']['cycles'] for j in range(NCTX))
    ingest = ing + N_LAYERS * ctx_layer
    mkv = jobs['k_MKV']['cycles']
    # the per-slot remainder that has no RTL: biased argmax over the die's 37,984 logits + cross-die argmax gather;
    # priced as the model prices it (tree 50 + 2 link latencies + 8), the stream pass itself is in the measured MKV
    argmax_gather = 50 + 2 * LINK_LAT + 8
    markov_measured = S_SLOTS * mkv
    markov = markov_measured + S_SLOTS * argmax_gather
    rec = {'schema': 'opentallas.qwen-dspark-ingest-markov-rtl.v1', 'position': 'P8191 step (context rows 8185..8187, '
           'Markov operands at 8191)', 'vehicle': 'VPRM REAL_MEM die (tools/qwen_rom_rt_vprm_w12.py, bld_dbg build of '
           'the ctx8k components), TP4 G6144 SW64, 1.2 GHz cycles', 'jobs': jobs,
           'all_exact': all(j['exact'] for j in jobs.values()),
           'composition': {
               'ingest': {'ING (FC x3 + all-gather + hidden_norm x3)': ing,
                          'context K/V one drafter layer, 3 rows (CTX0+CTX1+CTX2)': ctx_layer,
                          'layers': N_LAYERS, 'total_measured': ingest, 'priced': PRICED['ingest'],
                          'delta_vs_priced': ingest - PRICED['ingest']},
               'markov': {'MKV one slot (w2 . w1 + bias add, measured)': mkv, 'slots': S_SLOTS,
                          'measured_part': markov_measured,
                          'unvalidated_per_slot_argmax_and_gather (priced, no RTL)': argmax_gather,
                          'w1_row_lookup': 'host-preloaded (IO-edge ROM not in RTL; not priced by the model either)',
                          'total_with_priced_remainder': markov, 'priced': PRICED['markov'],
                          'delta_vs_priced': markov - PRICED['markov']},
               'ingest_plus_markov': ingest + markov, 'priced_total': PRICED['ingest'] + PRICED['markov'],
               'measured_share': (ingest + markov_measured) / (ingest + markov)},
           'priced_source': PRICED['source'],
           'notes': ['context K/V ingest reuses the drafter layer QKV-through-K/V instructions (Q retained, '
                     'tools/qwen_rom_dspark_images.context_kv_program); the pricing counted only the K/V rows',
                     'the 5 drafter layers share one shape; layer 0 is measured and composed x5 (owner: one layer per type)',
                     'exactness = RTL bit-exact vs the ISA golden of the same program (GPU matvec); the ING ISA output '
                     'also equals the plain W8 FC + G.rmsnorm semantics (golden.json ing_isa_equals_semantics)'],
           }
    Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec['composition'], indent=1), rec['all_exact'])


def E4(v, G):
    import numpy as np
    b = int(G.bits(np.float32(v)))
    s, e, m = b >> 31, (b >> 23) & 255, b & 0x7fffff
    if e == 0 and m == 0:
        return s << 7
    if 121 <= e <= 135 and m & 0xfffff == 0:
        return (s << 7) | ((e - 120) << 3) | (m >> 20)
    if e == 120 and m & 0x1fffff == 0:
        return (s << 7) | 4 | (m >> 21)
    if e == 119 and m & 0x3fffff == 0:
        return (s << 7) | 2 | (m >> 22)
    if e == 118 and m == 0:
        return (s << 7) | 1
    raise ValueError(f'not E4M3: {b:08x}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('prep'); p.add_argument('--snapshot-target', required=True); p.add_argument('--tokens', required=True)
    p.add_argument('--out', required=True)
    p = sp.add_parser('build'); p.add_argument('--images', required=True); p.add_argument('--out', required=True)
    p = sp.add_parser('golden'); p.add_argument('--stages', required=True); p.add_argument('--operands', required=True)
    p.add_argument('--out', required=True); p.add_argument('--remote-root', required=True)
    p = sp.add_parser('collect'); p.add_argument('--res', required=True); p.add_argument('--out', required=True)
    a = ap.parse_args()
    {'prep': prep, 'build': build, 'golden': golden, 'collect': collect}[a.cmd](a)


if __name__ == '__main__':
    main()
