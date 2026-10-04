"""Qualified-run selection (pre-registered 2026-10-03): EVERY agentic prompt of results/speculative/raw/prompts.jsonl.gz
(24 per workload x 5 workloads), no length cap (the longest is the context the prompt provides), file order.
Usage: python3 select_qualified.py OUT.json [N_PER_WORKLOAD]"""
import sys, json, gzip, copy, hashlib
import prompts as P
from encoding import encode_messages
from transformers import AutoTokenizer
out_path = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 10 ** 9
tok = AutoTokenizer.from_pretrained(P.SNAP)
rows = [json.loads(l) for l in gzip.open(P.REPO + '/results/speculative/raw/prompts.jsonl.gz')]
out, skipped = [], []
for w in [x for x in P.WL if x.startswith('agentic_')]:
    k = 0
    for r in rows:
        if r['workload'] != w or k >= N: continue
        msgs = copy.deepcopy(r['messages'])
        if r.get('tools'):
            if msgs[0]['role'] != 'system': msgs = [{'role': 'system', 'content': ''}] + msgs
            msgs[0]['tools'] = r['tools']
        mode = 'thinking' if r['enable_thinking'] else 'chat'
        try: text = encode_messages(msgs, thinking_mode=mode)
        except Exception as e: skipped.append((r['prompt_id'], 'encode_error:' + repr(e)[:80])); continue
        ids = tok.encode(text, add_special_tokens=False)
        out.append(dict(workload=w, prompt_id=r['prompt_id'], prompt_sha256=r['prompt_sha256'], thinking_mode=mode,
                        n_prompt=len(ids), n_messages=len(r['messages']), ids=ids, text_sha256=hashlib.sha256(text.encode()).hexdigest()))
        k += 1
s = json.dumps(dict(items=out, skipped=skipped), sort_keys=True)
open(out_path, 'w').write(s)
print('n', len(out), 'skipped', skipped, 'prompt tokens', sum(o['n_prompt'] for o in out), 'max', max(o['n_prompt'] for o in out),
      'sha256', hashlib.sha256(s.encode()).hexdigest())
