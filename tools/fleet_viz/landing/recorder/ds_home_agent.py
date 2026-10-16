"""DeepSeek API (OpenAI-compatible chat/completions) as a home agent over the mock home server. The key is read from env, never written."""
import json, os, subprocess, sys, time, urllib.request
sys.path.insert(0, '/home/ubuntu/landing-scratch/tools')
from home_tools import TOOLS, SYSTEM, run_calls
out_path, port, request = sys.argv[1], int(sys.argv[2]), sys.argv[3]
srv = subprocess.Popen([sys.executable, '/home/ubuntu/landing-scratch/tools/home_server.py', str(port)]); time.sleep(1)
initial = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/').read())
msgs = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': request}]; turns = []
for step in range(10):
    body = json.dumps(dict(model='deepseek-flash', messages=msgs, tools=TOOLS, stream=False)).encode()
    req = urllib.request.Request('https://api.deepseek.com/chat/completions', data=body,
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + os.environ['DEEPSEEK_API_KEY']})
    t0 = time.time(); r = json.loads(urllib.request.urlopen(req, timeout=300).read()); api_s = time.time() - t0
    ch = r['choices'][0]['message']; u = r.get('usage', {})
    calls = [dict(name=c['function']['name'], arguments=json.loads(c['function']['arguments'] or '{}'), id=c['id']) for c in (ch.get('tool_calls') or [])]
    rt = (u.get('completion_tokens_details') or {}).get('reasoning_tokens', 0)
    turn = dict(step=step + 1, served_model=r.get('model'), prompt_tokens=u.get('prompt_tokens'), cached_prompt_tokens=u.get('prompt_cache_hit_tokens', 0),
                new_prompt_tokens=u.get('prompt_cache_miss_tokens', u.get('prompt_tokens')), output_tokens=u.get('completion_tokens'),
                reasoning_tokens=rt, content_tokens=(u.get('completion_tokens') or 0) - rt, thinking=ch.get('reasoning_content') or '',
                content=ch.get('content') or '', tool_calls=[dict(name=c['name'], arguments=c['arguments']) for c in calls], api_s=round(api_s, 2))
    m = {'role': 'assistant', 'content': ch.get('content') or ''}
    if ch.get('reasoning_content'): m['reasoning_content'] = ch['reasoning_content']
    if ch.get('tool_calls'): m['tool_calls'] = ch['tool_calls']
    msgs.append(m)
    if calls:
        res, wall = run_calls(port, calls); turn['tool_results'] = [dict(x, arguments=x['arguments']) for x in res]; turn['tool_wall_ms'] = wall
        for c, x in zip(calls, res): msgs.append({'role': 'tool', 'tool_call_id': c['id'], 'content': json.dumps(x['result'])})
    turns.append(turn); print('step', step + 1, r.get('model'), u.get('prompt_tokens'), u.get('completion_tokens'), [c['name'] for c in calls], flush=True)
    if not calls: break
final = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/').read()); srv.terminate()
json.dump(dict(model='deepseek-flash (DeepSeek API)', system=SYSTEM, request=request, tools=[t['function']['name'] for t in TOOLS],
               initial_state=initial, final_state=final, turns=turns, recorded=time.strftime('%Y-%m-%d %H:%M %Z')), open(out_path, 'w'), indent=1)
