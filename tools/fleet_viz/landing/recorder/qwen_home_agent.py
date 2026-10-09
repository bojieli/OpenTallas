"""Qwen3-8B (BF16, local) as a home-hub agent over the mock home tool server. Records every turn."""
import json, re, subprocess, sys, time, torch
sys.path.insert(0, '/home/ubuntu/landing-scratch/tools')
from home_tools import TOOLS, SYSTEM, run_calls
from transformers import AutoTokenizer, AutoModelForCausalLM
out_path, port, request = sys.argv[1], int(sys.argv[2]), sys.argv[3]
torch.set_num_threads(int(sys.argv[4]) if len(sys.argv) > 4 else 10); torch.manual_seed(0)
srv = subprocess.Popen([sys.executable, '/home/ubuntu/landing-scratch/tools/home_server.py', str(port)]); time.sleep(1)
P = '/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218'
tok = AutoTokenizer.from_pretrained(P); m = AutoModelForCausalLM.from_pretrained(P, dtype=torch.bfloat16).eval()
initial = json.loads(__import__('urllib.request').request.urlopen(f'http://127.0.0.1:{port}/').read())
msgs = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': request}]
turns = []; prev_prompt = 0
for step in range(8):
    ids = tok.apply_chat_template(msgs, tools=[t['function'] for t in TOOLS], add_generation_prompt=True, enable_thinking=True, return_tensors='pt')
    t0 = time.time()
    with torch.no_grad():
        o = m.generate(ids, attention_mask=torch.ones_like(ids), max_new_tokens=1024, do_sample=True, temperature=0.6, top_p=0.95, top_k=20)
    gen = o[0, ids.shape[1]:].tolist(); gen_s = time.time() - t0
    raw = tok.decode(gen, skip_special_tokens=False).replace('<|im_end|>', '').replace('<|endoftext|>', '')
    think = ''; body = raw
    mt = re.search(r'<think>(.*?)</think>', raw, re.S)
    if mt: think = mt.group(1).strip(); body = raw[mt.end():]
    think_tokens = len(tok(mt.group(0), add_special_tokens=False).input_ids) if mt else 0
    calls = [json.loads(x) for x in re.findall(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', body, re.S)]
    content = re.sub(r'<tool_call>.*?</tool_call>', '', body, flags=re.S).strip()
    turn = dict(step=step + 1, prompt_tokens=int(ids.shape[1]), new_prompt_tokens=int(ids.shape[1]) - prev_prompt,
                output_tokens=len(gen), reasoning_tokens=think_tokens, content_tokens=len(gen) - think_tokens,
                thinking=think, content=content, tool_calls=calls, local_gen_s=round(gen_s, 2))
    msgs.append({'role': 'assistant', 'content': content, 'tool_calls': [{'type': 'function', 'function': c} for c in calls]} if calls else {'role': 'assistant', 'content': content})
    prev_prompt = int(ids.shape[1]) + len(gen)
    if calls:
        res, wall = run_calls(port, calls); turn['tool_results'] = res; turn['tool_wall_ms'] = wall
        for r in res: msgs.append({'role': 'tool', 'content': json.dumps(r['result'])})
    turns.append(turn); print('step', step + 1, 'out', len(gen), 'calls', [c['name'] for c in calls], flush=True)
    if not calls: break
final = json.loads(__import__('urllib.request').request.urlopen(f'http://127.0.0.1:{port}/').read())
srv.terminate()
json.dump(dict(model='Qwen/Qwen3-8B', revision='b968826d9c46dd6066d109eabc6255188de91218', dtype='bfloat16',
               device='cpu (local RTX PRO 6000 in GPU-requires-reset state)', sampling=dict(temperature=0.6, top_p=0.95, top_k=20, seed=0, enable_thinking=True),
               system=SYSTEM, request=request, tools=[t['function']['name'] for t in TOOLS], initial_state=initial, final_state=final, turns=turns,
               recorded=time.strftime('%Y-%m-%d %H:%M %Z')), open(out_path, 'w'), indent=1)
