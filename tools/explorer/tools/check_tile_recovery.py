#!/usr/bin/env python3
"""Outage check (not part of the pytest suite: it restarts the service once): open a design at exact-geometry zoom,
restart the explorer service while tiles are loading, and require that every tile is drawn afterwards with no failure left.

    python3 -I check_tile_recovery.py [node id] [unit]      # needs Playwright (see tests/README.md)
"""
import json, subprocess, sys, time
from playwright.sync_api import sync_playwright
node = sys.argv[1] if len(sys.argv) > 1 else 's81.t.slice_station__t12'
unit = sys.argv[2] if len(sys.argv) > 2 else 'explorer-fable.service'
ST = "(() => { const e = window.otx.eng; let f = 0, ok = 0; for (const t of e.tiles.values()) { if (t.failed) f++; else if (t.n) ok++; } return {mode: e.mode, pending: e.pending.size, ok, failed: f, hud: document.querySelector('[data-testid=layout-info]').textContent, log: e.failLog.length, why: e.failLog.slice(-1).map((x) => x.why)[0] || null}; })()"
with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1500, 'height': 950})
    pg.goto('http://127.0.0.1:8770/#/element/%s?cam=700.000,600.000,2.6' % node, wait_until='load')
    pg.wait_for_function("window.otx && window.otx.eng && window.otx.eng.mode === 'geometry' && window.otx.eng.pending.size === 0", timeout=120000)
    before = pg.evaluate(ST)
    pg.evaluate("(() => { const e = window.otx.eng; e.setCam(300, 300, 2.6); })()")       # a place whose tiles are not loaded yet
    subprocess.run(['systemctl', '--user', 'restart', unit], check=True)                    # the outage, while the tiles are being fetched
    seen = 0; t0 = time.time(); s = None
    while time.time() - t0 < 90:
        time.sleep(0.5); s = pg.evaluate(ST); seen = max(seen, s['failed'])
        if s['pending'] == 0 and s['failed'] == 0 and s['ok'] > 0 and time.time() - t0 > 6: break
    print(json.dumps(dict(node=node, before=before, after=s, failed_seen_during_outage=seen, recovered_s=round(time.time() - t0, 1))))
    b.close()
    sys.exit(0 if s and s['failed'] == 0 and s['ok'] > 0 else 1)
