"""The long Qwen3-8B answer via OpenRouter (local GPU needs a reset). Same prompt and sampling as the CPU run (qwen_long.py).
    orkey.sh python3 qwen_long_or.py OUT.json
Pieces are the streamed text re-tokenised with the released Qwen3-8B tokenizer (the replay paces per token)."""
import json, sys, time, glob, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from or_client import chat, endpoints
from transformers import AutoTokenizer
MODEL = 'qwen/qwen3-8b'
P = glob.glob(os.path.expanduser('~/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/*'))[0]
tok = AutoTokenizer.from_pretrained(P)
q = ("Write a thorough, well-structured guide (about 1,500 words) titled 'How a cup of espresso gets made, from farm to cup'. "
     "Cover growing and harvesting, processing, roasting chemistry, grinding, and the physics of extraction at 9 bar. "
     "Use markdown headings and a few bullet lists.")
ep = [dict(provider=e['provider_name'], tag=e.get('tag'), quantization=e.get('quantization'), name=e.get('name')) for e in endpoints(MODEL)]
body = dict(model=MODEL, messages=[{'role': 'user', 'content': q}], max_tokens=2150, temperature=0.7, top_p=0.8, top_k=20, seed=0,
            reasoning={'enabled': False}, usage={'include': True})
chunks, t0 = chat(body, stream=True)
text = ''.join((c['choices'][0]['delta'].get('content') or '') for _, c in chunks if c.get('choices'))
reasoning = ''.join((c['choices'][0]['delta'].get('reasoning') or '') for _, c in chunks if c.get('choices'))
usage = [c['usage'] for _, c in chunks if c.get('usage')]; usage = usage[-1] if usage else {}
prov = sorted({c.get('provider') for _, c in chunks if c.get('provider')}); served = sorted({c.get('model') for _, c in chunks if c.get('model')})
first = next((t for t, c in chunks if c.get('choices') and c['choices'][0]['delta'].get('content')), None)
ids = tok(text, add_special_tokens=False).input_ids
pieces = []; prev = ''
for i in range(len(ids)):
    s = tok.decode(ids[:i + 1]); pieces.append(s[len(prev):]); prev = s
assert prev == text, 'retokenisation does not round-trip'
fin = [c['choices'][0].get('finish_reason') for _, c in chunks if c.get('choices') and c['choices'][0].get('finish_reason')]
json.dump(dict(model='Qwen/Qwen3-8B', source='openrouter', openrouter_model=MODEL, served_model=served, provider=prov,
               endpoints_listed=ep, quantization=[e['quantization'] for e in ep if e['provider'] in prov] or None,
               sampling=dict(temperature=0.7, top_p=0.8, top_k=20, seed=0, enable_thinking=False),
               prompt=q, prompt_tokens=usage.get('prompt_tokens'), output_tokens=len(ids), api_completion_tokens=usage.get('completion_tokens'),
               api_reasoning_tokens=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens'), reasoning_chars=len(reasoning),
               finish_reason=fin[-1] if fin else None, pieces=pieces, text=text,
               api_wall_s=round(chunks[-1][0] - t0, 2), api_ttft_s=round(first - t0, 2) if first else None,
               recorded=time.strftime('%Y-%m-%d %H:%M %Z')), open(sys.argv[1], 'w'), ensure_ascii=False)
print('provider', prov, 'served', served, 'tokens', len(ids), 'api', usage.get('completion_tokens'), 'finish', fin[-1:] , 'reasoning chars', len(reasoning))
