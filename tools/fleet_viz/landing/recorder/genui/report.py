"""Per case x {full, patch}: median / p90 of the recorded quantities and decode / prefill+KV / tools / total per lane.
usage: report.py RECORDINGS_DIR [ds_rom hbm gpu openrouter rates]"""
import json, sys
D = sys.argv[1]; r = [float(x) for x in sys.argv[2:6]] if len(sys.argv) > 5 else [4351.6, 3700.3, 873.63, 88.5]
R = dict(zip(('DS ROM', 'HBM', 'GPU', 'OpenRouter'), r)); KV = ('DS ROM', 'HBM')
def q(a, p):
    s = sorted(a); k = (len(s) - 1) * p; lo = int(k); hi = min(lo + 1, len(s) - 1); return s[lo] + (s[hi] - s[lo]) * (k - lo)
mp = lambda a, f='{:.1f}': f'{f.format(q(a, .5))}/{f.format(q(a, .9))}'
for cid in ('bi', 'desk', 'edit'):
    d = json.load(open(f'{D}/genui_{cid}.json')); none = [it['i'] for it in d['interactions'] if it['kind'] == 'none']
    for k in ('full', 'patch'):
        L = [it for it in d['interactions'] if it['kind'] == k]
        if not L: continue
        S = lambda f: [f(it) for it in L]; sm = lambda key: (lambda it: sum(c[key] for c in it['calls']))
        print(f'{cid}.{k} n={len(L)} {[it["i"] for it in L]}' + (f' no-change {none}' if none and k == 'full' else ''))
        print('   turns', mp(S(lambda it: len(it['calls'])), '{:.0f}'), '| tools', mp(S(lambda it: sum(len(c['tool_calls']) for c in it['calls'])), '{:.0f}'),
              '| reasoning', mp(S(sm('reasoning_tokens')), '{:.0f}'), '| html', mp(S(sm('html_tokens')), '{:.0f}'), '| patch', mp(S(sm('patch_tokens')), '{:.0f}'),
              '| tool-args', mp(S(sm('tool_tokens')), '{:.0f}'), '| tool-results', mp(S(sm('tool_result_tokens')), '{:.0f}'), '| out', mp(S(sm('output_tokens')), '{:.0f}'))
        print('   prefill+KV ms', mp(S(lambda it: 1000 * sum(c['prefill_s'] + c['kv_s'] for c in it['calls'])), '{:.0f}'), '| tools s', mp(S(sm('tool_s'))),
              '| per-tool-call ms', mp([1000 * c['tool_s'] / len(c['tool_calls']) for it in L for c in it['calls'] if c['tool_calls']], '{:.0f}'), '| API recorded s', mp(S(sm('api_s'))))
        for n, rt in R.items():
            dec = S(lambda it: sum(c['output_tokens'] for c in it['calls']) / rt)
            tot = S(lambda it: sum(c['prefill_s'] + (c['kv_s'] if n in KV else 0) + c['output_tokens'] / rt + c['tool_s'] for c in it['calls']))
            print(f'   {n:10s} decode {mp(dec)}  total {mp(tot)}')
