"""Qualified run, batch 2 (added 2026-10-03 on the user's broadened class definition; see the record's PROTOCOL.md
addendum).  Classes with no published DSpark value, 24 prompts each, chat (non-thinking) mode unless stated:
  coding_humaneval        committed HumanEval prompts, thinking OFF (xcheck_humaneval_nothink rows)   [class value]
  coding_humaneval_think  committed HumanEval prompts, thinking ON (reasoning_humaneval rows)          [supplementary]
  reasoning_math500_think committed MATH-500 prompts, thinking ON (reasoning_math500 rows)             [supplementary]
  longdoc                 LongBench-E (zai-org/LongBench @5e628be4): gov_report_e, qmsum, multifieldqa_en_e, hotpotqa_e,
                          6 each, LongBench's own prompt templates, longest contexts <= MAXLEN tokens
  multilingual_aya        CohereLabs/aya_dataset @f9ea0458 test split: 4 each of the 6 non-English languages
  assistant_smarthome     acon96/Home-Assistant-Requests-V2 @29ac1a80 home_assistant_test_english.jsonl (MIT; synthetic
                          home-llm requests): system device state + user request + the HA tool schema
Usage: python3 select_batch2.py DATASET_DIR OUT.json [MAXLEN]"""
import sys, json, gzip, copy, hashlib, random, zipfile
import prompts as P
from encoding import encode_messages
from transformers import AutoTokenizer
DD, out_path = sys.argv[1], sys.argv[2]
MAXLEN = int(sys.argv[3]) if len(sys.argv) > 3 else 12000
N = 24
SEED = 20261003
tok = AutoTokenizer.from_pretrained(P.SNAP)
out, skipped = [], []


def add(workload, pid, msgs, tools, think, source):
    msgs = copy.deepcopy(msgs)
    if tools:
        if msgs[0]['role'] != 'system':
            msgs = [{'role': 'system', 'content': ''}] + msgs
        msgs[0]['tools'] = tools
    text = encode_messages(msgs, thinking_mode='thinking' if think else 'chat')
    ids = tok.encode(text, add_special_tokens=False)
    if len(ids) > MAXLEN:
        skipped.append((pid, len(ids))); return False
    out.append(dict(workload=workload, prompt_id=pid, source=source, thinking_mode='thinking' if think else 'chat',
                    n_prompt=len(ids), ids=ids, text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                    prompt_sha256=hashlib.sha256(json.dumps([msgs, tools, think], sort_keys=True, default=str).encode()).hexdigest()))
    return True


rows = [json.loads(l) for l in gzip.open(P.REPO + '/results/speculative/raw/prompts.jsonl.gz')]
for src_wl, wl, think in (('xcheck_humaneval_nothink', 'coding_humaneval', False),
                          ('reasoning_humaneval', 'coding_humaneval_think', True),
                          ('reasoning_math500', 'reasoning_math500_think', True)):
    for r in [x for x in rows if x['workload'] == src_wl][:N]:
        add(wl, r['prompt_id'], r['messages'], r.get('tools'), think, 'committed:' + src_wl)

# LongBench templates (THUDM/LongBench config/dataset2prompt.json)
LB = {
    'gov_report_e': "You are given a report by a government agency. Write a one-page summary of the report.\n\nReport:\n{context}\n\nNow, write a one-page summary of the report.\n\nSummary:",
    'qmsum': "You are given a meeting transcript and a query containing a question or instruction. Answer the query in one or more sentences.\n\nTranscript:\n{context}\n\nNow, answer the query based on the above meeting transcript in one or more sentences.\n\nQuery: {input}\nAnswer:",
    'multifieldqa_en_e': "Read the following text and answer briefly.\n\n{context}\n\nNow, answer the following question based on the above text, only give me the answer and do not output any other words.\n\nQuestion: {input}\nAnswer:",
    'hotpotqa_e': "Answer the question based on the given passages. Only give me the answer and do not output any other words.\n\nThe following are given passages.\n{context}\n\nAnswer the question based on the given passages. Only give me the answer and do not output any other words.\n\nQuestion: {input}\nAnswer:",
}
z = zipfile.ZipFile(DD + '/longbench_data.zip')
for sub, tmpl in LB.items():
    items = [json.loads(l) for l in z.open(f'data/{sub}.jsonl')]
    cand = []
    for r in items:
        msgs = [{'role': 'user', 'content': tmpl.format(context=r['context'], input=r.get('input', ''))}]
        n = len(tok.encode(encode_messages(msgs, thinking_mode='chat'), add_special_tokens=False))
        if n <= MAXLEN:
            cand.append((n, r['_id'], msgs))
    cand.sort(key=lambda c: -c[0])                       # longest feasible contexts first
    for n, pid, msgs in cand[:N // 4]:
        add('longdoc', f'{sub}:{pid}', msgs, None, False, 'zai-org/LongBench@5e628be450b7e67fb7ae6e201bd6d8f7056f7672:' + sub)

import pandas as pd
aya = pd.read_parquet(DD + '/aya_test.parquet')
for lang in sorted(set(aya.language) - {'English'}):
    sub = aya[aya.language == lang].reset_index()
    order = list(range(len(sub))); random.Random(f'{SEED}:{lang}').shuffle(order)
    for i in order[:N // 6]:
        r = sub.iloc[i]
        add('multilingual_aya', f"aya-{r['language_code']}-{int(r['index'])}", [{'role': 'user', 'content': r['inputs']}], None, False,
            'CohereLabs/aya_dataset@f9ea04583f02a8f86404ff6c58bf75fe637df8a2:test')

ha = [json.loads(l) for l in open(DD + '/ha_test_english.jsonl')]
order = list(range(len(ha))); random.Random(f'{SEED}:ha').shuffle(order)
k = 0
txt = lambda c: c if isinstance(c, str) else ''.join(x.get('text', '') for x in c)
for i in order:
    r = ha[i]
    m = r['messages']
    if len(m) < 2 or m[0]['role'] != 'system' or m[1]['role'] != 'user':
        continue
    msgs = [{'role': 'system', 'content': txt(m[0]['content'])}, {'role': 'user', 'content': txt(m[1]['content'])}]
    tools = [{'type': 'function', 'function': t['function']} for t in (r.get('tools') or [])]
    if add('assistant_smarthome', f'ha-test-en-{i}', msgs, tools or None, False,
           'acon96/Home-Assistant-Requests-V2@29ac1a80b7185e7b4c2c9e43b7e4fe71531ec434:home_assistant_test_english.jsonl'):
        k += 1
    if k == N:
        break

s = json.dumps(dict(items=out, skipped=skipped), sort_keys=True)
open(out_path, 'w').write(s)
import collections
c = collections.defaultdict(list)
for o in out: c[o['workload']].append(o['n_prompt'])
for w, v in c.items(): print(w, len(v), 'min', min(v), 'max', max(v), 'sum', sum(v))
print('n', len(out), 'skipped', len(skipped), 'prompt tokens', sum(o['n_prompt'] for o in out), 'sha256', hashlib.sha256(s.encode()).hexdigest())
