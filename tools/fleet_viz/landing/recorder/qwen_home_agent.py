"""Qwen3-8B as a smart-home hub agent over the mock home tool server, thinking mode on, with a capped thinking budget.

    python3 qwen_home_agent.py OUT.json PORT "REQUEST" --backend openrouter|local [--think-budget 768] [--answer-max 400] [--threads 16]

What changed from the first harness (whose thinking runs never called a tool and whose non-thinking run set 22:41):
  * tools go through the native tool-calling path: the OpenAI tools schema on OpenRouter; locally, the released Qwen3
    chat template's own tools= rendering and <tool_call> parsing (exactly what the template defines);
  * the thinking budget is capped per turn: locally, generation stops at </think> or at --think-budget tokens, and on the
    budget a nudge closes the thought ("...give the answer based on the thinking directly now.</think>") before the answer
    is generated (Qwen's published budget-forcing recipe); on OpenRouter, reasoning.max_tokens + max_tokens;
  * the system prompt states the tool contract (dates, 24-hour times, read before acting, when to stop);
  * every tool call's arguments are validated against the schema (required keys, types, enums, HH:MM, YYYY-MM-DD,
    ranges) before it reaches the home; an invalid call is not executed and the model gets the validation error back.
The OpenRouter key is read from the env only (OPENROUTER_API_KEY) and never written; no request headers are recorded."""
import argparse, json, os, re, subprocess, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from home_tools import run_calls

DOORS = ['front_door', 'back_door', 'garage_entry']
ROOMS = ['kitchen', 'living_room', 'hallway', 'bedroom', 'office', 'porch', 'all']
APPLIANCES = ['oven', 'tv', 'dishwasher']
def fn(name, desc, props=None, req=()):
    return {'type': 'function', 'function': {'name': name, 'description': desc,
            'parameters': {'type': 'object', 'properties': props or {}, 'required': list(req)}}}
TOOLS = [
 fn('get_home_state', 'Read every sensor: door locks, door and window contacts, lights, thermostat, appliances, alarms. No arguments.'),
 fn('set_lights', 'Turn the lights in one room (or "all") on or off.',
    {'room': {'type': 'string', 'enum': ROOMS}, 'on': {'type': 'boolean'}}, ('room', 'on')),
 fn('lock_door', 'Lock one smart lock.', {'door': {'type': 'string', 'enum': DOORS}}, ('door',)),
 fn('set_thermostat', 'Set the thermostat target temperature in degrees Celsius (5-30) and optionally the mode.',
    {'target_c': {'type': 'number', 'minimum': 5, 'maximum': 30}, 'mode': {'type': 'string', 'enum': ['heat', 'cool', 'off']}}, ('target_c',)),
 fn('get_calendar', "List the user's calendar events for one date. Events are not sorted.",
    {'date': {'type': 'string', 'description': 'YYYY-MM-DD'}}, ('date',)),
 fn('set_alarm', 'Set a wake-up alarm at the next occurrence of a 24-hour local time.',
    {'time': {'type': 'string', 'description': 'HH:MM, 24-hour'}, 'label': {'type': 'string'}}, ('time',)),
 fn('turn_off_appliance', 'Turn off one appliance.', {'appliance': {'type': 'string', 'enum': APPLIANCES}}, ('appliance',)),
]
SPEC = {t['function']['name']: t['function']['parameters'] for t in TOOLS}
SYSTEM = (
 "You are the on-device assistant of a smart-home hub. Current local time: Friday 2026-10-09 22:41. Tomorrow is Saturday 2026-10-10.\n"
 "Tool contract:\n"
 "- You act only through the provided tools. Each call is executed on the real devices and its JSON result comes back to you.\n"
 "- Never assume a device state or a calendar entry: read it with get_home_state or get_calendar first.\n"
 "- Dates are YYYY-MM-DD. Times are 24-hour HH:MM local time. set_alarm rings at the next occurrence of the time you give, "
 "so work out the exact time yourself from what the tools return.\n"
 "- Put independent calls in the same turn. A call that depends on another call's result goes in a later turn.\n"
 "- If a call returns an error, do not retry it blindly; tell the user.\n"
 "- Think briefly. When everything asked has been done, stop calling tools and reply in two or three short spoken sentences, "
 "including anything that is still open or could not be done.")

HHMM = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$'); DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
def validate(name, args):
    """return None if the call is valid, else a message for the model"""
    if name not in SPEC: return f'unknown tool {name!r}'
    if not isinstance(args, dict): return 'arguments must be a JSON object'
    p = SPEC[name]; props = p['properties']
    for k in p['required']:
        if k not in args: return f'missing required argument {k!r}'
    for k, v in args.items():
        if k not in props: return f'unexpected argument {k!r}'
        s = props[k]; ty = s['type']
        if ty == 'string' and not isinstance(v, str): return f'{k} must be a string'
        if ty == 'boolean' and not isinstance(v, bool): return f'{k} must be true or false'
        if ty == 'number' and (isinstance(v, bool) or not isinstance(v, (int, float))): return f'{k} must be a number'
        if 'enum' in s and v not in s['enum']: return f'{k} must be one of {s["enum"]}'
        if 'minimum' in s and not (s['minimum'] <= v <= s['maximum']): return f'{k} must be within {s["minimum"]}..{s["maximum"]}'
    if name == 'set_alarm' and not HHMM.match(args['time']): return 'time must be HH:MM, 24-hour (e.g. 07:05)'
    if name == 'get_calendar' and not DATE.match(args['date']): return 'date must be YYYY-MM-DD'
    return None

NUDGE = "\n\nConsidering the limited time, I have to give the answer based on the thinking directly now.\n</think>\n\n"

class Local:
    """released Qwen3-8B weights, BF16, transformers; Qwen3 chat template with tools=; budget-forced thinking"""
    def __init__(self, a):
        import glob, torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        torch.set_num_threads(a.threads); torch.manual_seed(a.seed); self.torch = torch
        P = glob.glob(os.path.expanduser('~/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/*'))[0]
        self.rev = os.path.basename(P); self.tok = AutoTokenizer.from_pretrained(P)
        self.m = AutoModelForCausalLM.from_pretrained(P, dtype=torch.bfloat16).eval(); self.a = a
        self.END = [self.tok.convert_tokens_to_ids(x) for x in ('<|im_end|>', '<|endoftext|>')]; self.CLOSE = self.tok.convert_tokens_to_ids('</think>')
        self.prev_prompt = 0
    def gen(self, ids, n, stop):
        with self.torch.no_grad():
            o = self.m.generate(ids, attention_mask=self.torch.ones_like(ids), max_new_tokens=n, do_sample=True, temperature=0.6, top_p=0.95, top_k=20,
                                eos_token_id=stop, pad_token_id=self.END[0])
        return o[0, ids.shape[1]:].tolist()
    def turn(self, msgs):
        t0 = time.time(); tok = self.tok
        ids = tok.apply_chat_template(msgs, tools=TOOLS, add_generation_prompt=True, enable_thinking=True, return_tensors='pt')
        g1 = self.gen(ids, self.a.think_budget, [self.CLOSE] + self.END)        # thinking, up to the budget
        nudged = bool(g1) and g1[-1] != self.CLOSE and g1[-1] not in self.END
        if g1 and g1[-1] in self.END:                                          # finished without closing the thought (should not happen)
            g2, inj = [], []
        else:
            inj = tok(NUDGE, add_special_tokens=False).input_ids if nudged else tok('\n\n', add_special_tokens=False).input_ids
            ids2 = self.torch.cat([ids, self.torch.tensor([g1 + inj])], 1)
            g2 = self.gen(ids2, self.a.answer_max, self.END)
        think_text = tok.decode(g1, skip_special_tokens=False).replace('<think>', '').replace('</think>', '').strip()
        body = tok.decode(g2, skip_special_tokens=False).replace('<|im_end|>', '').replace('<|endoftext|>', '')
        calls, bad = [], []
        for x in re.findall(r'<tool_call>\s*(.*?)\s*</tool_call>', body, re.S):
            try: c = json.loads(x); calls.append(dict(name=c.get('name'), arguments=c.get('arguments', {})))
            except Exception as e: bad.append(f'unparseable tool call: {e}')
        content = re.sub(r'<tool_call>.*?</tool_call>', '', body, flags=re.S).strip()
        pt = int(ids.shape[1]); r = dict(prompt_tokens=pt, new_prompt_tokens=pt - self.prev_prompt, output_tokens=len(g1) + len(g2),
                                         reasoning_tokens=len(g1), thinking=think_text, content=content, calls=calls, parse_errors=bad,
                                         think_capped=nudged, nudge_tokens=len(inj) if nudged else 0, local_gen_s=round(time.time() - t0, 2))
        self.prev_prompt = pt + len(g1) + len(inj) + len(g2)
        return r
    def assistant_msg(self, r, calls):
        m = {'role': 'assistant', 'content': r['content']}
        if calls: m['tool_calls'] = [{'type': 'function', 'function': {'name': c['name'], 'arguments': c['arguments']}} for c in calls]
        return m
    def tool_msg(self, c, result): return {'role': 'tool', 'content': json.dumps(result)}
    def meta(self): return dict(backend='local', model='Qwen/Qwen3-8B', revision=self.rev, dtype='bfloat16',
                                device=f'cpu ({self.a.threads} threads; local RTX PRO 6000 in GPU-requires-reset state)',
                                sampling=dict(temperature=0.6, top_p=0.95, top_k=20, seed=self.a.seed, enable_thinking=True))

class OpenRouter:
    """OpenRouter chat/completions, native tools; provider and reported quantisation recorded"""
    MODEL = 'qwen/qwen3-8b'
    def __init__(self, a):
        from or_client import chat, endpoints
        self.chat = chat; self.a = a; self.ep = [dict(provider=e['provider_name'], quantization=e.get('quantization'), name=e.get('name')) for e in endpoints(self.MODEL)]
        self.prov = set(); self.served = set(); self.ids = 0
    def turn(self, msgs):
        body = dict(model=self.MODEL, messages=msgs, tools=TOOLS, tool_choice='auto', temperature=0.6, top_p=0.95, top_k=20, seed=self.a.seed,
                    max_tokens=self.a.think_budget + self.a.answer_max, reasoning={'max_tokens': self.a.think_budget}, usage={'include': True})
        r, s = self.chat(body); ch = r['choices'][0]['message']; u = r.get('usage') or {}
        self.prov.add(r.get('provider')); self.served.add(r.get('model'))
        rt = (u.get('completion_tokens_details') or {}).get('reasoning_tokens') or 0
        calls, bad = [], []
        for c in ch.get('tool_calls') or []:
            try: calls.append(dict(name=c['function']['name'], arguments=json.loads(c['function']['arguments'] or '{}'), id=c['id']))
            except Exception as e: bad.append(f'unparseable tool call: {e}')
        cached = (u.get('prompt_tokens_details') or {}).get('cached_tokens') or 0
        return dict(prompt_tokens=u.get('prompt_tokens'), new_prompt_tokens=(u.get('prompt_tokens') or 0) - cached, output_tokens=u.get('completion_tokens'),
                    reasoning_tokens=rt, thinking=ch.get('reasoning') or '', content=ch.get('content') or '', calls=calls, parse_errors=bad,
                    finish_reason=r['choices'][0].get('finish_reason'), provider=r.get('provider'), served_model=r.get('model'), api_s=round(s, 2), _raw_calls=ch.get('tool_calls'))
    def assistant_msg(self, r, calls):
        m = {'role': 'assistant', 'content': r['content']}
        if r.get('_raw_calls'): m['tool_calls'] = r['_raw_calls']
        return m
    def tool_msg(self, c, result): return {'role': 'tool', 'tool_call_id': c['id'], 'content': json.dumps(result)}
    def meta(self): return dict(backend='openrouter', model='Qwen/Qwen3-8B', openrouter_model=self.MODEL, provider=sorted(p for p in self.prov if p),
                                served_model=sorted(s for s in self.served if s), endpoints_listed=self.ep,
                                quantization=[e['quantization'] for e in self.ep if e['provider'] in self.prov] or None,
                                sampling=dict(temperature=0.6, top_p=0.95, top_k=20, seed=self.a.seed, enable_thinking=True))

ap = argparse.ArgumentParser()
ap.add_argument('out'); ap.add_argument('port', type=int); ap.add_argument('request')
ap.add_argument('--backend', choices=['local', 'openrouter'], required=True)
ap.add_argument('--think-budget', type=int, default=768); ap.add_argument('--answer-max', type=int, default=400)
ap.add_argument('--threads', type=int, default=16); ap.add_argument('--seed', type=int, default=0); ap.add_argument('--max-turns', type=int, default=8)
a = ap.parse_args()
srv = subprocess.Popen([sys.executable, os.path.join(HERE, 'home_server.py'), str(a.port)]); time.sleep(1)
try:
    B = Local(a) if a.backend == 'local' else OpenRouter(a)
    initial = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{a.port}/').read())
    msgs = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': a.request}]; turns = []
    for step in range(a.max_turns):
        r = B.turn(msgs); calls = r.pop('calls'); r.pop('_raw_calls', None)
        good = [c for c in calls if validate(c['name'], c['arguments']) is None]
        rejected = [dict(name=c['name'], arguments=c['arguments'], error=validate(c['name'], c['arguments'])) for c in calls if c not in good]
        r.update(step=step + 1, tool_calls=[dict(name=c['name'], arguments=c['arguments']) for c in calls], rejected_calls=rejected)
        msgs.append(B.assistant_msg(r, calls))
        if good:
            res, wall = run_calls(a.port, [dict(name=c['name'], arguments=c['arguments']) for c in good]); r['tool_results'] = res; r['tool_wall_ms'] = wall
        resmap = {id(c): x['result'] for c, x in zip(good, r.get('tool_results', []))}
        for c in calls:                                                           # one tool message per call, in call order
            msgs.append(B.tool_msg(c, resmap[id(c)] if id(c) in resmap else {'error': 'invalid arguments: ' + validate(c['name'], c['arguments'])}))
        if r['parse_errors'] and not calls:
            msgs.append({'role': 'user', 'content': 'Your tool call could not be parsed: ' + '; '.join(r['parse_errors'])})
        turns.append(r)
        print('step', step + 1, 'out', r['output_tokens'], 'think', r['reasoning_tokens'], 'capped', r.get('think_capped'), 'calls',
              [(c['name'], c['arguments']) for c in calls], 'rejected', len(rejected), flush=True)
        if not calls and not r['parse_errors']: break
    final = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{a.port}/').read())
finally:
    srv.terminate()
json.dump(dict(B.meta(), system=SYSTEM, request=a.request, tools=[t['function']['name'] for t in TOOLS], think_budget=a.think_budget, answer_max=a.answer_max,
               initial_state=initial, final_state=final, turns=turns, recorded=time.strftime('%Y-%m-%d %H:%M %Z')), open(a.out, 'w'), indent=1)
