# Pilot selection: agentic prompts of results/speculative/raw/prompts.jsonl.gz NOT used by the committed
# v41_flash_dspark_onpolicy_greedy.json run (its selection = prompts.py build(4, 4500)); next N per agentic workload
# in file order, length cap raised to MAXLEN so long tau-bench/SWE contexts are no longer filtered out.
import sys, json, gzip, copy, hashlib
sys.path.insert(0, '/tmp/claude-mtp-wt/tools/v41_dspark_onpolicy')
import prompts as P
from encoding import encode_messages
N = int(sys.argv[1]); MAXLEN = int(sys.argv[2])
base, _, tok = P.build(4, 4500)
used = {o['prompt_id'] for o in base}
rows = [json.loads(l) for l in gzip.open('/tmp/claude-mtp-wt/results/speculative/raw/prompts.jsonl.gz')]
out, skipped = [], []
for w in [x for x in P.WL if x.startswith('agentic_')]:
    k = 0
    for r in rows:
        if r['workload'] != w or r['prompt_id'] in used: continue
        msgs = copy.deepcopy(r['messages'])
        if r.get('tools'):
            if msgs[0]['role'] != 'system': msgs = [{'role': 'system', 'content': ''}] + msgs
            msgs[0]['tools'] = r['tools']
        mode = 'thinking' if r['enable_thinking'] else 'chat'
        try: text = encode_messages(msgs, thinking_mode=mode)
        except Exception as e: skipped.append((r['prompt_id'], 'encode_error:' + repr(e)[:80])); continue
        ids = tok.encode(text, add_special_tokens=False)
        if len(ids) > MAXLEN: skipped.append((r['prompt_id'], f'len {len(ids)}')); continue
        out.append(dict(workload=w, prompt_id=r['prompt_id'], prompt_sha256=r['prompt_sha256'], thinking_mode=mode,
                        n_prompt=len(ids), ids=ids, text_sha256=hashlib.sha256(text.encode()).hexdigest()))
        k += 1
        if k == N: break
for o in out: print(o['workload'], o['prompt_id'], o['thinking_mode'], o['n_prompt'])
print('skipped', skipped); print('n', len(out), 'prompt tokens', sum(o['n_prompt'] for o in out), 'max', max(o['n_prompt'] for o in out))
s = json.dumps(dict(items=out, skipped=skipped), sort_keys=True)
open('prompts_sel.json', 'w').write(s); print('sha256', hashlib.sha256(s.encode()).hexdigest())
