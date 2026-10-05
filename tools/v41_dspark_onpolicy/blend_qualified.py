"""Per-class DSpark tau (gamma 1..5, greedy and T=1), the pre-registered blend and envelope, and DS ROM / DS HBM rates.
Protocol: results/speculative/v41_mtp_acceptance_qualified_20261003/PROTOCOL.md + PROTOCOL_ADDENDUM.md.
Usage: python3 blend_qualified.py OUT.json DRAFTS.json [DRAFTS.json ...]"""
import sys, os, json, random, statistics, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acc_qualified as Q

G = 5
OURS = {
    'c_coding': ('coding_humaneval',),
    'd_longdoc': ('longdoc',),
    'e_multilingual': ('multilingual_aya',),
    'f_agentic': ('agentic_swe_agent', 'agentic_tau_bench', 'agentic_mind2web'),
    'g_assistant_fc': ('agentic_bfcl', 'agentic_json_mode', 'assistant_smarthome'),
}
SUPPLEMENTARY = {'coding_think_supp': ('coding_humaneval_think',), 'reasoning_math500_think_supp': ('reasoning_math500_think',),
                 'g_bfcl_jsonmode_only': ('agentic_bfcl', 'agentic_json_mode'), 'g_smarthome_only': ('assistant_smarthome',)}
LMSYS_LABEL = 'LMSYS published, V4-Flash (not V4.1), verify window (upper bound on accepted length), block 6'
LMSYS_SRC = 'https://www.lmsys.org/blog/2026-07-06-dspark-sglang/ Figure 4 (mixed traffic)'
PUBLISHED = {'a_chat': ('Arena-Hard', 3.78), 'b_reasoning': ('GSM8K', 5.24), 'h_creative': ('Poetry', 2.91)}
CLASSES = ['a_chat', 'b_reasoning', 'c_coding', 'd_longdoc', 'e_multilingual', 'f_agentic', 'g_assistant_fc', 'h_creative']
o14, o12 = 1 / 14, 1 / 12
WEIGHTS = {
    'equal (default)': {c: 1 / 8 for c in CLASSES},
    'chat-heavy': dict({c: o14 for c in CLASSES}, a_chat=0.5),
    'assistant-heavy': dict({c: o14 for c in CLASSES}, g_assistant_fc=0.5),
    'agent-heavy': dict({c: o14 for c in CLASSES}, f_agentic=0.5),
    'reasoning/coding-heavy': dict({c: o12 for c in CLASSES}, b_reasoning=0.25, c_coding=0.25),
    '3-class equal': dict(a_chat=1 / 3, f_agentic=1 / 3, g_assistant_fc=1 / 3),
    '3-class chat-heavy': dict(a_chat=0.5, f_agentic=0.25, g_assistant_fc=0.25),
    '3-class agent-heavy': dict(a_chat=0.25, f_agentic=0.5, g_assistant_fc=0.25),
    '3-class assistant-heavy': dict(a_chat=0.25, f_agentic=0.25, g_assistant_fc=0.5),
    'measured-only equal (c-g)': {c: 1 / 5 for c in OURS},
    # Owner decision 2026-10-03: long-document and multilingual classes retired as dated workloads.
    'owner 6-class equal': {c: 1 / 6 for c in CLASSES if c not in ('d_longdoc', 'e_multilingual')},
    'owner 6-class chat-heavy': dict({c: 0.1 for c in CLASSES if c not in ('d_longdoc', 'e_multilingual')}, a_chat=0.5),
    'owner 6-class agent-heavy': dict({c: 0.1 for c in CLASSES if c not in ('d_longdoc', 'e_multilingual')}, f_agentic=0.5),
    'owner 6-class assistant-heavy': dict({c: 0.1 for c in CLASSES if c not in ('d_longdoc', 'e_multilingual')}, g_assistant_fc=0.5),
    'owner measured-only equal (c,f,g)': dict(c_coding=1 / 3, f_agentic=1 / 3, g_assistant_fc=1 / 3),
}
# step times (us).  HBM: d2aff19ef v41_hbm_speculation_methods.json contexts.1048576 (measured union + composed draft 51.88).
HBM_STEP = {1: 550.21, 2: 604.59, 3: 653.77, 4: 705.48, 5: 752.73}
HBM_AR_US = 442.14
# ROM: pilot sensitivity (verify shape of uarch_model v41_verify_T, gamma<5 derived) + ASSUMED 3/40 draft 26.9 us;
# proxy: draft replaced by d2aff19ef's HBM-composition ratio (42.1 us).  Both UNVALIDATED.
ROM_STEP_ASSUMED = {1: 447.3, 2: 533.7, 3: 620.3, 4: 706.7, 5: 795.2}
ROM_STEP_PROXY = {g: s - 26.9 + 42.1 for g, s in ROM_STEP_ASSUMED.items()}
ROM_AR_US = 358.8


def rates(t, g=G):
    return dict(hbm_w19_dspark=round(t * 1e6 / HBM_STEP[g], 1), rom_draft_assumed=round(t * 1e6 / ROM_STEP_ASSUMED[g], 1),
                rom_draft_proxy=round(t * 1e6 / ROM_STEP_PROXY[g], 1))


def boot(pp, B, seed=7):
    by = collections.defaultdict(list)
    for x in pp:
        by[x['workload']].append(x)
    rng = random.Random(seed); bm, bp = [], []
    for _ in range(B):
        s = []
        for v in by.values():
            s += [rng.choice(v) for _ in v]
        bm.append(statistics.median(x['committed'] / x['cycles'] for x in s))
        bp.append(sum(x['committed'] for x in s) / sum(x['cycles'] for x in s))
    bm.sort(); bp.sort()
    q = lambda v: [round(v[int(0.025 * B)], 3), round(v[int(0.975 * B) - 1], 3)]
    return q(bm), q(bp)


def class_stats(pp, B):
    pp = [x for x in pp if x['cycles'] > 0]
    if not pp:
        return None
    med = statistics.median(x['committed'] / x['cycles'] for x in pp)
    pooled = sum(x['committed'] for x in pp) / sum(x['cycles'] for x in pp)
    cm, cp = boot(pp, B)
    return dict(prompts=len(pp), generated_tokens=sum(x['n_generated'] for x in pp), cycles=round(sum(x['cycles'] for x in pp), 1),
                tau_median_of_prompts=round(med, 3), tau_median_ci95=cm, tau_pooled=round(pooled, 3), tau_pooled_ci95=cp,
                prompt_tokens_range=[min(x['n_prompt'] for x in pp), max(x['n_prompt'] for x in pp)],
                prompt_tokens_median=statistics.median(x['n_prompt'] for x in pp),
                per_workload={w: dict(prompts=sum(1 for x in pp if x['workload'] == w),
                                      tau_median=round(statistics.median(x['committed'] / x['cycles'] for x in pp if x['workload'] == w), 3))
                              for w in sorted({x['workload'] for x in pp})})


def main(out, paths):
    per = collections.defaultdict(list)          # (mode, gamma) -> per-prompt rows
    for path in paths:
        trs = json.load(open(path))
        for i, tr in enumerate(trs):
            mode = tr.get('mode', 'greedy')
            for g in range(1, G + 1):
                st = Q.greedy_prompt(tr, g) if mode == 'greedy' else Q.t1_prompt(tr, 1000 + i, g)
                per[(mode, g)].append(dict(workload=tr['item']['workload'], prompt_id=tr['item']['prompt_id'], n_prompt=tr['L'],
                                           n_generated=len(tr['tokens']) - tr['L'], cycles=st['cycles'], committed=st['committed']))
    res = dict(protocol=['results/speculative/v41_mtp_acceptance_qualified_20261003/PROTOCOL.md',
                         'results/speculative/v41_mtp_acceptance_qualified_20261003/PROTOCOL_ADDENDUM.md'],
               inputs=[os.path.basename(p) for p in paths],
               published=dict(label=LMSYS_LABEL, source=LMSYS_SRC, values={c: dict(set=s, tau_verify_window=v) for c, (s, v) in PUBLISHED.items()}),
               rate_basis=dict(hbm_step_us=HBM_STEP, hbm_ar_us=HBM_AR_US, rom_step_us_draft_assumed=ROM_STEP_ASSUMED,
                               rom_step_us_draft_proxy={g: round(s, 1) for g, s in ROM_STEP_PROXY.items()}, rom_ar_us=ROM_AR_US,
                               note='HBM: d2aff19ef measured union + composed DSpark draft 51.88 us (1M).  ROM: verify shape from the pilot '
                                    'sensitivity (gamma<5 derived) + draft ASSUMED 3/40 (26.9 us) or HBM-ratio proxy (42.1 us); the ROM draft '
                                    'is UNVALIDATED either way.'),
               classes={}, supplementary={}, blends={}, envelope={})
    for mode in ('greedy', 't1'):
        for g in range(1, G + 1):
            rows = per.get((mode, g), [])
            B = 20000 if g == G else 4000
            for name, wls in OURS.items():
                s = class_stats([x for x in rows if x['workload'] in wls], B)
                if s:
                    s['rates_at_median'] = rates(s['tau_median_of_prompts'], g)
                res['classes'].setdefault(name, {}).setdefault(mode, {})[g] = s
            for name, wls in SUPPLEMENTARY.items():
                s = class_stats([x for x in rows if x['workload'] in wls], B)
                res['supplementary'].setdefault(name, {}).setdefault(mode, {})[g] = s
    for mode in ('greedy', 't1'):
        tau = {}
        src = {}
        for c in CLASSES:
            if c in PUBLISHED:
                tau[c] = PUBLISHED[c][1]; src[c] = 'LMSYS published (upper bound)'
            else:
                s = res['classes'][c][mode].get(G)
                if s:
                    tau[c] = s['tau_median_of_prompts']; src[c] = 'ours (median of per-prompt tau)'
        res['envelope'][mode] = dict(min=min(((v, c) for c, v in tau.items())), max=max(((v, c) for c, v in tau.items())),
                                     class_tau_gamma5=tau, class_source=src,
                                     rates_min=rates(min(tau.values())), rates_max=rates(max(tau.values())),
                                     measured_only_min=min(((v, c) for c, v in tau.items() if c not in PUBLISHED), default=None),
                                     measured_only_max=max(((v, c) for c, v in tau.items() if c not in PUBLISHED), default=None))
        for wn, w in WEIGHTS.items():
            if not all(c in tau for c in w):
                res['blends'].setdefault(wn, {})[mode] = dict(missing=[c for c in w if c not in tau]); continue
            h = 1 / sum(x / tau[c] for c, x in w.items())
            a = sum(x * tau[c] for c, x in w.items())
            pub_share = sum(x for c, x in w.items() if c in PUBLISHED)
            d = dict(tau_blend_harmonic=round(h, 3), tau_blend_arithmetic_ref=round(a, 3), published_weight_share=round(pub_share, 3),
                     rates_gamma5=rates(h))
            if pub_share == 0:     # measured-only: every gamma
                d['by_gamma'] = {}
                for g in range(1, G + 1):
                    tg = {c: res['classes'][c][mode][g]['tau_median_of_prompts'] for c in w}
                    hg = 1 / sum(x / tg[c] for c, x in w.items())
                    d['by_gamma'][g] = dict(tau=round(hg, 3), rates=rates(hg, g))
            res['blends'].setdefault(wn, {})[mode] = d
    res['weights'] = WEIGHTS
    json.dump(res, open(out, 'w'), indent=1, default=str)
    for c in CLASSES:
        if c in PUBLISHED:
            print(c, 'LMSYS', PUBLISHED[c]); continue
        for mode in ('greedy', 't1'):
            s = res['classes'][c][mode][G]
            if s:
                print(c, mode, 'n', s['prompts'], 'median', s['tau_median_of_prompts'], s['tau_median_ci95'], 'pooled', s['tau_pooled'],
                      'by gamma', [res['classes'][c][mode][g]['tau_median_of_prompts'] for g in range(1, G + 1)])
    for wn, v in res['blends'].items():
        print(wn, {m: (x.get('tau_blend_harmonic'), x.get('rates_gamma5')) for m, x in v.items()})
    print('envelope', {m: (v['min'], v['max']) for m, v in res['envelope'].items()})


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
