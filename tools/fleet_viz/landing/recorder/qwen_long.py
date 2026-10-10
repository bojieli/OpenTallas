"""Generate one long Qwen3-8B answer (BF16, CPU fallback: local GPU needs a reset) and record per-token pieces."""
import json, time, torch, sys
from transformers import AutoTokenizer, AutoModelForCausalLM
torch.set_num_threads(12); torch.manual_seed(0)
P = '/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218'
tok = AutoTokenizer.from_pretrained(P); m = AutoModelForCausalLM.from_pretrained(P, torch_dtype=torch.bfloat16); m.eval()
q = ("Write a thorough, well-structured guide (about 1,500 words) titled 'How a cup of espresso gets made, from farm to cup'. "
     "Cover growing and harvesting, processing, roasting chemistry, grinding, and the physics of extraction at 9 bar. "
     "Use markdown headings and a few bullet lists.")
msgs = [{'role': 'user', 'content': q}]
ids = tok.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False, return_tensors='pt')
t0 = time.time()
with torch.no_grad():
    out = m.generate(ids, max_new_tokens=2150, do_sample=True, temperature=0.7, top_p=0.8, top_k=20)
gen = out[0, ids.shape[1]:].tolist()
if gen and gen[-1] in (tok.eos_token_id, tok.convert_tokens_to_ids('<|im_end|>')): gen = gen[:-1]
pieces = []; prev = ''
for i in range(len(gen)):
    s = tok.decode(gen[:i + 1], skip_special_tokens=True); pieces.append(s[len(prev):]); prev = s
json.dump(dict(model='Qwen/Qwen3-8B', revision='b968826d9c46dd6066d109eabc6255188de91218', dtype='bfloat16', device='cpu (12 threads; local RTX PRO 6000 in GPU-requires-reset state)',
               sampling=dict(temperature=0.7, top_p=0.8, top_k=20, seed=0, enable_thinking=False), prompt=q, prompt_tokens=int(ids.shape[1]),
               output_tokens=len(gen), pieces=pieces, text=prev, wall_s=round(time.time() - t0, 1), recorded=time.strftime('%Y-%m-%d %H:%M %Z')),
          open(sys.argv[1], 'w'), ensure_ascii=False)
print('tokens', len(gen), 'wall', time.time() - t0)
