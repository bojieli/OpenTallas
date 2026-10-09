"""Per case x {full, patch}: median / p90 of the recorded quantities and the wall time per lane (same model as the page)."""
import json, sys, statistics
D = sys.argv[1]; R = dict(ds_rom=4351.6, hbm=3700.3, gpu=873.63, openrouter=88.5); KV = ('ds_rom', 'hbm')
def q(a, p):
    s = sorted(a); k = (len(s) - 1) * p; lo = int(k); hi = min(lo + 1, len(s) - 1); return s[lo] + (s[hi] - s[lo]) * (k - lo)
def lane(it, r, kv): return sum(c['prefill_s'] + (c['kv_s'] if kv else 0) + c['output_tokens'] / r + c['tool_s'] for c in it['calls'])
for cid in ('bi', 'desk', 'edit'):
    d = json.load(open(f'{D}/genui_{cid}.json'))
    none = [it['i'] for it in d['interactions'] if it['kind'] == 'none']
    for k in ('full', 'patch'):
        L = [it for it in d['interactions'] if it['kind'] == k]
        if not L: continue
        S = lambda f: [f(it) for it in L]; sm = lambda key: (lambda it: sum(c[key] for c in it['calls']))
        cols = dict(turns=S(lambda it: len(it['calls'])), tool_calls=S(lambda it: sum(len(c['tool_calls']) for c in it['calls'])),
                    reasoning=S(sm('reasoning_tokens')), output=S(sm('output_tokens')), html=S(sm('html_tokens')), patch=S(sm('patch_tokens')), tool_args=S(sm('tool_tokens')),
                    tool_result=S(sm('tool_result_tokens')), new_prefill=S(sm('new_tokens')), tool_s=S(sm('tool_s')), prefill_kv_ms=S(lambda it: 1000 * sum(c['prefill_s'] + c['kv_s'] for c in it['calls'])),
                    **{f'wall_{n}': S(lambda it, r=r, n=n: lane(it, r, n in KV)) for n, r in R.items()}, **{f'decode_{n}': S(lambda it, r=r: sum(c['output_tokens'] for c in it['calls']) / r) for n, r in R.items()},
                    api_recorded=S(sm('api_s')))
        print(f'{cid} {k} n={len(L)} (interactions {[it["i"] for it in L]}){"  no-change: " + str(none) if none and k == "full" else ""}')
        for n, a in cols.items(): print(f'   {n:18s} median {q(a, .5):10.1f}   p90 {q(a, .9):10.1f}')
