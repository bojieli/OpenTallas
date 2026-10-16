"""Pass-through recording proxy for the DeepSeek Anthropic-compatible endpoint.
Records request bodies and SSE events with timestamps. NEVER records headers (the API key lives there)."""
import http.client, json, sys, time, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
UP = 'api.deepseek.com'; OUT = sys.argv[2]; PORT = int(sys.argv[1]); lock = threading.Lock(); seq = [0]
def rec(o):
    with lock:
        with open(OUT, 'a') as f: f.write(json.dumps(o) + '\n')
class P(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *a): pass
    def _go(self):
        with lock: seq[0] += 1; n = seq[0]
        ln = int(self.headers.get('Content-Length') or 0); body = self.rfile.read(ln) if ln else b''
        t0 = time.time()
        hdr = {k: v for k, v in self.headers.items() if k.lower() not in ('host', 'content-length', 'accept-encoding', 'connection')}
        hdr['Accept-Encoding'] = 'identity'
        try: req = json.loads(body) if body else None
        except Exception: req = None
        rec(dict(kind='req', n=n, t=t0, method=self.command, path=self.path, body=req))
        c = http.client.HTTPSConnection(UP, timeout=600); c.request(self.command, self.path, body=body, headers=hdr); r = c.getresponse()
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in ('transfer-encoding', 'content-length', 'connection', 'content-encoding'): self.send_header(k, v)
        self.send_header('Transfer-Encoding', 'chunked'); self.end_headers()
        buf = b''; events = []; tfirst = None; raw = b''
        while True:
            ch = r.read1(65536) if hasattr(r, 'read1') else r.read(65536)
            if not ch: break
            now = time.time(); tfirst = tfirst or now
            self.wfile.write(b'%x\r\n' % len(ch) + ch + b'\r\n'); self.wfile.flush()
            buf += ch
            if len(raw) < 4_000_000: raw += ch
            while b'\n\n' in buf:
                ev, buf = buf.split(b'\n\n', 1)
                for line in ev.split(b'\n'):
                    if line.startswith(b'data:'):
                        try: events.append([round(now - t0, 4), json.loads(line[5:].strip())])
                        except Exception: pass
        self.wfile.write(b'0\r\n\r\n'); self.wfile.flush()
        t1 = time.time()
        o = dict(kind='resp', n=n, t0=t0, tfirst=tfirst, t1=t1, status=r.status, events=events)
        if not events:
            try: o['json'] = json.loads(raw)
            except Exception: o['text'] = raw[:2000].decode('utf-8', 'replace')
        rec(o)
    do_POST = do_GET = do_DELETE = _go
ThreadingHTTPServer(('127.0.0.1', PORT), P).serve_forever()
