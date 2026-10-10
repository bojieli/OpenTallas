"""Minimal OpenRouter chat/completions client. The key comes from the env (OPENROUTER_API_KEY) and is never written:
nothing here logs request headers, and callers record only bodies and usage."""
import json, os, time, urllib.request
URL = 'https://openrouter.ai/api/v1/chat/completions'
def endpoints(model):
    r = urllib.request.Request(f'https://openrouter.ai/api/v1/models/{model}/endpoints', headers={'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY']})
    return json.loads(urllib.request.urlopen(r, timeout=60).read())['data']['endpoints']
def chat(body, stream=False):
    """non-streaming: (response json, wall s). streaming: (list of (t, chunk json), t0)"""
    req = urllib.request.Request(URL, data=json.dumps(dict(body, stream=stream)).encode(),
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY'],
                                          'HTTP-Referer': 'https://github.com/OpenTallas', 'X-Title': 'OpenTallas landing recorder'})
    t0 = time.time(); resp = urllib.request.urlopen(req, timeout=600)
    if not stream:
        return json.loads(resp.read()), time.time() - t0
    out = []
    for line in resp:
        line = line.decode().strip()
        if not line.startswith('data:'): continue
        d = line[5:].strip()
        if d == '[DONE]': break
        out.append((time.time(), json.loads(d)))
    return out, t0
