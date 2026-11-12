#!/usr/bin/env python3
"""Light standalone server for the design explorer (EXPLORER-2): the design pages + API (design_service.py), the static
layout store and on-store search (layout_service.py), the layout viewer assets (explorer/element/*.js, vendor/deck.gl),
and the dataflow / token / coverage page assets.  No fleet pollers, no ssh: it only reads files.

    LV_STORE=<store> DESIGN_INDEX=<design_index.json> python3 -I design_dev_server.py [--port 8766] [--bind 127.0.0.1]

fleet-viz's server.py mounts the same two services, so this is for pilots, screenshots and a light read-only host.
"""
import argparse, os, pathlib, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import design_service, layout_service

DS = design_service.Service()
LS = layout_service.Service(log=lambda *a: None)
STATIC_DIRS = {'/explorer/element/': HERE / 'explorer' / 'element', '/explorer/dataflow/': HERE / 'explorer' / 'dataflow',
               '/explorer/token/': HERE / 'explorer' / 'token', '/explorer/coverage/': HERE / 'explorer' / 'coverage'}
if os.environ.get('DATAFLOW_DATA'):   # generated plan_<die> link records (plan_dataflow.py output dir of a deployed fleet-viz)
    STATIC_DIRS = {'/explorer/dataflow/data/': pathlib.Path(os.environ['DATAFLOW_DATA']), **STATIC_DIRS}
TYPES = dict(design_service.TYPES, **{'.gz': 'application/gzip', '.bin': 'application/octet-stream', '.webp': 'image/webp'})


class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a): pass

    def send(self, code, body, ctype, extra=()):
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body)))
        for k, v in extra: self.send_header(k, v)
        self.send_header('X-Content-Type-Options', 'nosniff'); self.end_headers()
        if self.command != 'HEAD': self.wfile.write(body)

    def do_HEAD(self): self.do_GET()

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path in ('/', '/explorer', '/explorer/', '/explorer/design'):
            self.send_response(302); self.send_header('Location', '/explorer/design/'); self.send_header('Content-Length', '0'); self.end_headers(); return
        if u.path.startswith('/explorer/design/'): return DS.page(self, u.path[len('/explorer/design/'):])
        if u.path == '/api/plan_now':   # same contract as server.py: plan_now.json, or a JSON 404 when none is recorded
            import json
            f = pathlib.Path(os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz'))) / 'plan_now.json'
            try: return self.send(200, f.read_bytes(), 'application/json')
            except OSError: return self.send(404, json.dumps(dict(error='no plan_now.json (no token-pass state recorded)')).encode(), 'application/json')
        if u.path.startswith('/api/design/'): return DS.handle(self, u.path[len('/api/design/'):], q)
        if u.path.startswith('/layout_store/'): return LS.static(self, u.path[len('/layout_store/'):], False)
        if u.path.startswith('/api/layout/'): return LS.handle(self, u.path[len('/api/layout/'):], q, False)
        for pre, base in STATIC_DIRS.items():
            if u.path.startswith(pre):
                rel = u.path[len(pre):] or 'index.html'
                try:
                    p = (base / rel).resolve(); ok = p.is_relative_to(base.resolve()) and p.is_file()
                except (OSError, ValueError):
                    ok = False
                if not ok: return self.send(404, b'not found', 'text/plain')
                if p.name.endswith('.json.gz'):
                    return self.send(200, p.read_bytes(), 'application/json', (('Content-Encoding', 'gzip'),))
                return self.send(200, p.read_bytes(), TYPES.get(p.suffix, 'application/octet-stream'))
        self.send(404, b'not found', 'text/plain')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--port', type=int, default=8766); ap.add_argument('--bind', default='127.0.0.1')
    a = ap.parse_args()
    s = ThreadingHTTPServer((a.bind, a.port), H)
    print('design explorer on http://%s:%d/explorer/design/ (store %s, index %s)' % (a.bind, a.port, layout_service.LS.STORE, design_service.INDEX), flush=True)
    s.serve_forever()


if __name__ == '__main__':
    main()
