"""Router capture on the main model's own greedy continuations (teacher-forced) plus the DSpark drafter's routing.

Phase R1: one teacher-forced pass (start_pos 0, one chunk per trace) of the MAIN model over each trace's prompt +
greedy continuation, with v41gen's layer-streamed modules unchanged; every MoE gate's top-6 indices are recorded per
position and layer.  The routing at a decode position is therefore the routing the verify pass sees for that input
token (up to the torch-kernel summation order; the decode path is not re-run).
Phase R2: the DSpark drafter (vendor forward_spec decode path, as v41draft.py) at every generated position, with its
three stages' top-3-of-128 gate indices recorded over the 5 block slots, and the drafts compared with the input
drafts.json (a cross-check that teacher-forced main_hidden reproduces the pilot's decode-path drafts).

    python3 v41router.py --traces drafts.json --out router.pt [--gpu-frac 0.3]
"""
import sys, json, time, types, argparse
import torch
import v41gen as G
from v41gen import M, CK

REC = {}          # layer -> list of [n, k] int16 index tensors, in call order


def _wrap(orig):
    def moe_stream(ffn, store, x, lim, stats):
        _, idx = ffn.gate(x)
        REC.setdefault(store.layer, []).append(idx.to(torch.int16).cpu())
        return orig(ffn, store, x, lim, stats)
    return moe_stream


def phase_r1(traces_in, a):
    args = G.load_args(a.max_seq_len)
    G.init_pinned(3 * 48 + 8)
    torch.set_default_device('cuda')
    M.world_size, M.rank, M.default_dtype = 1, 0, torch.float8_e4m3fn
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(G.SNAP)
    layout = M.EngramLayout.from_args(args)
    with torch.device('cuda'):
        engram_hash = M.NgramHashState(args, layout, tok)
    blocks, hps, stores = [], [], []
    for i in range(args.n_layers):
        with torch.device('meta'):
            blk = M.Block(i, args, layout)
        blk.ffn.experts = None
        if blk.engram is not None:
            blk.engram.embed = G.EngramRows(i)
        G.fix_freqs(blk, args)
        hps.append(G.host_params(f'layers.{i}.', blk, skip=('ffn.experts.', 'engram.embed.')))
        G.to_meta(blk, hps[-1])
        st = G.ExpertStore(f'layers.{i}.ffn.experts', args.n_routed_experts)
        st.layer = i
        stores.append(st)
        blocks.append(blk)
    embed_w = CK.read('embed.weight').cuda()
    head_w = CK.read('head.weight').cuda()
    norm_w = CK.read('norm.weight').cuda()
    G.moe_stream = _wrap(G.moe_stream)
    traces = []
    for t in traces_in:
        it = dict(t['item'], ids=list(t['tokens']))
        tr = G.Trace(it, blocks, 0)
        tr.L_prompt = t['L']
        traces.append(tr)
    stats = dict(experts=0, moe_s=0.0, attn_s=0.0, h2d_s=0.0)
    groups, cur, ctok = [], [], 0
    for tr in traces:
        if cur and ctok + tr.L > a.prefill_group_tokens:
            groups.append(cur); cur, ctok = [], 0
        cur.append(tr); ctok += tr.L
    groups.append(cur)
    out = []
    t0 = time.time()
    for g in groups:
        ts = time.time()
        REC.clear()
        nxt = G.forward_group(g, [tr.tokens for tr in g], blocks, hps, stores, embed_w, head_w, norm_w,
                              engram_hash, args, stats)
        lens = [tr.L for tr in g]
        per = [torch.cat(REC[i]).split(lens) for i in range(args.n_layers)]
        for b, tr in enumerate(g):
            idx = torch.stack([per[i][b] for i in range(args.n_layers)])        # [layers, n, 6]
            out.append(dict(item={k: v for k, v in tr.item.items() if k != 'ids'}, L=tr.L_prompt, tokens=tr.tokens,
                            router_idx=idx, main_hidden=torch.cat(tr.main_hidden)[:-1],
                            next_token_after_trace=nxt[b]))
        print(f'R1 group {len(g)} traces {sum(lens)} tok {time.time()-ts:.1f}s total {time.time()-t0:.0f}s '
              f'gpu_peak {torch.cuda.max_memory_allocated()/1e9:.2f}', flush=True)
    # free the main model before the drafter
    del blocks, hps, stores, embed_w, head_w, norm_w, engram_hash
    torch.cuda.empty_cache()
    return out


DREC = []


def phase_r2(gen, traces_in, a):
    import v41draft as D
    args = G.load_args(8192)
    blocks = D.build(args)
    for s, blk in enumerate(blocks):
        def hook(mod, inp, outp, s=s):
            DREC.append((s, outp[1].to(torch.int16).cpu()))
        blk.ffn.gate.register_forward_hook(hook)
    model = types.SimpleNamespace(mtp=blocks, hc_mult=args.hc_mult)
    ref = {t['item']['prompt_id']: t for t in traces_in}
    for tr in gen:
        ts = time.time()
        D.reset(blocks)
        toks, L, mh = tr['tokens'], tr['L'], tr['main_hidden'].cuda()
        ids = torch.tensor(toks, device='cuda')
        M.Transformer.forward_spec(model, ids[L:L + 1], mh[:L].unsqueeze(0), 0)
        DREC.clear()
        drafts, didx = {}, {}
        for p in range(L, mh.size(0)):
            n0 = len(DREC)
            res = M.Transformer.forward_spec(model, ids[p + 1:p + 2], mh[p:p + 1].unsqueeze(0), p)
            drafts[p] = res[0][0, 1:].tolist()
            didx[p] = torch.stack([x[1].view(-1, x[1].size(-1)) for x in DREC[n0:]])   # [3 stages, 5 slots, 3]
        r = ref[tr['item']['prompt_id']]['drafts']
        agree = sum(drafts[p] == r[str(p)] for p in drafts if str(p) in r)
        tr['drafter_idx'] = {p: v for p, v in didx.items()}
        tr['drafts_tf'] = drafts
        tr['drafts_agree_with_pilot'] = [agree, len(drafts)]
        print('R2', tr['item']['prompt_id'], 'rows', len(drafts), 'agree', agree, f'{time.time()-ts:.1f}s', flush=True)
        tr['main_hidden'] = None
    return gen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--traces', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--gpu-frac', type=float, default=0.3)
    ap.add_argument('--max-seq-len', type=int, default=8192)
    ap.add_argument('--prefill-group-tokens', type=int, default=12000)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    torch.cuda.set_per_process_memory_fraction(a.gpu_frac)
    torch.set_default_dtype(torch.bfloat16)
    torch.set_grad_enabled(False)
    traces_in = json.load(open(a.traces))
    if a.limit:
        traces_in = traces_in[:a.limit]
    gen = phase_r1(traces_in, a)
    torch.save([{k: v for k, v in g.items() if k != 'main_hidden'} for g in gen], a.out + '.r1')
    gen = phase_r2(gen, traces_in, a)
    torch.save(gen, a.out)
    print('done', flush=True)


if __name__ == '__main__':
    main()
