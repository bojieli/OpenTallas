#!/usr/bin/env python3
"""Comparison page for the GLOBAL-FP-S candidates (one HTML file, inline same-scale SVGs)."""
import argparse, html, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import draw

CSS = """
:root{
 /* layout: one reading column; a two-up figure grid at the same die scale; dense metric table */
 --bg:#f4f5f2;--panel:#ffffff;--ink:#1d2321;--muted:#5d6763;--rule:#c9cfcb;--accent:#1f6f5c;--warn:#a2461f;
 --die:#fbfbf9;--corr:#f3df9a;--k-hub:#86a9c9;--k-res:#cdbbe6;--k-io:#b9bfbc;--k-frame:#e9ece4;--k-vm:#e3a061;
 --c-field:#1f8a6a;--c-su:#c2412f;--c-coll:#2f5fb8;--c-hbm:#6d7672;--c-engram:#9a3a9a;
 --sans:"IBM Plex Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace;--disp:"IBM Plex Sans Condensed","IBM Plex Sans",sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --bg:#151917;--panel:#1d2220;--ink:#e3e8e5;--muted:#9aa6a0;--rule:#3a423e;--accent:#5fc3a5;--warn:#f0905e;
 --die:#202624;--corr:#5c5230;--k-hub:#3f6487;--k-res:#5a4a78;--k-io:#4b524f;--k-frame:#2a302d;--k-vm:#a8672c;
 --c-field:#4fd0a5;--c-su:#ff7a66;--c-coll:#7aa2ff;--c-hbm:#a3aca8;--c-engram:#d58ad5;color-scheme:dark}}
:root[data-theme="dark"]{
 --bg:#151917;--panel:#1d2220;--ink:#e3e8e5;--muted:#9aa6a0;--rule:#3a423e;--accent:#5fc3a5;--warn:#f0905e;
 --die:#202624;--corr:#5c5230;--k-hub:#3f6487;--k-res:#5a4a78;--k-io:#4b524f;--k-frame:#2a302d;--k-vm:#a8672c;
 --c-field:#4fd0a5;--c-su:#ff7a66;--c-coll:#7aa2ff;--c-hbm:#a3aca8;--c-engram:#d58ad5;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5}
.wrap{max-width:1180px;margin:0 auto;padding-block:28px 60px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
h1{font-family:var(--disp);font-weight:600;font-size:30px;margin:0 0 4px;text-wrap:balance}
h2{font-family:var(--disp);font-weight:600;font-size:21px;margin:34px 0 10px;text-wrap:balance}
.sub{color:var(--muted);font-size:13px;font-family:var(--mono)}
p,li{max-width:76ch}
.rec{background:var(--panel);border:1px solid var(--rule);border-left:4px solid var(--accent);padding:14px 18px;margin-top:18px}
.rec b{color:var(--accent)}
.scope{color:var(--warn);font-family:var(--mono);font-size:12px;letter-spacing:.04em;text-transform:uppercase}
.tbl{overflow-x:auto;background:var(--panel);border:1px solid var(--rule)}
table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
th,td{padding:6px 9px;border-bottom:1px solid var(--rule);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{font-family:var(--mono);font-weight:500;font-size:11px;letter-spacing:.04em;color:var(--muted);text-transform:uppercase}
tr.best td{background:color-mix(in srgb,var(--accent) 12%,transparent)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px}
figure{margin:0;background:var(--panel);border:1px solid var(--rule);padding:10px;min-width:0}
figcaption{font-size:12.5px;color:var(--muted);margin-top:6px}
figcaption b{color:var(--ink);font-family:var(--mono)}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--muted);margin:8px 0}
.sw{display:inline-block;width:12px;height:12px;vertical-align:-2px;margin-right:5px;border:1px solid var(--rule)}
code{font-family:var(--mono);font-size:12.5px}
.bar{height:10px;display:inline-block;vertical-align:middle}
"""


def fmt(v, d=1):
    return ('{:,.%df}' % d).format(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cands', required=True)
    ap.add_argument('--links-dir', required=True)
    ap.add_argument('--graph', required=True)
    ap.add_argument('--rec', required=True)
    ap.add_argument('--text', required=True, help='json with recommendation/findings/method text blocks')
    ap.add_argument('--out', required=True)
    ap.add_argument('--explorer-metrics', default=None, help='explorer_metrics.json from register.py')
    a = ap.parse_args()
    C = json.loads(Path(a.cands).read_text())['candidates']
    G = json.loads(Path(a.graph).read_text())
    T = json.loads(Path(a.text).read_text())
    base = next(c['metrics'] for c in C if c['metrics']['candidate'].startswith('C0'))
    rows = []
    for c in C:
        m = c['metrics']
        cls = ' class="best"' if m['candidate'] == a.rec else ''
        d = (m['sum_traffic_bit_um_M'] / base['sum_traffic_bit_um_M'] - 1) * 100
        rows.append('<tr%s><td>%s</td><td>%s</td><td>%s</td><td>%+.1f%%</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%d</td></tr>' % (
            cls, html.escape(m['candidate']), m['vm_shape'], fmt(m['sum_bit_um_M']), d, fmt(m['sum_traffic_bit_um_M'], 1),
            fmt(m['relay_flops'] / 1e3, 0), fmt(m['bits_over_500'] / 1e3, 1), fmt(m['field_worst_path_um'] / 1e3, 1),
            m['field_worst_cycles'], '%.2f / %d' % (m['cut']['p99_share'], m['cut']['gcell_edges_over_060']), m['legality']['overlaps']))
    xrows = ''
    if a.explorer_metrics:
        XM = json.loads(Path(a.explorer_metrics).read_text())
        order = ['_canonical_s81_gen18c'] + [c['metrics']['candidate'] for c in C if c['metrics']['candidate'] in XM]
        for k in order:
            v = XM[k]['metrics']
            cls = ' class="best"' if k == a.rec else ''
            nm = 'GEN18c canonical (exact plan + LEF pins)' if k.startswith('_') else k
            xrows += '<tr%s><td>%s</td><td><code>%s</code></td><td>%s</td><td>%s</td><td>%.2f</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                cls, html.escape(nm), XM[k]['id'], fmt(v['sum_bit_um_hops'] / 1e9, 3), fmt(v['over_reach_bits'], 0), v['worst_cut'],
                v['cut_windows_over_limit'], fmt((v['relay_bit_stages'] or 0) / 1e6, 2),
                fmt(v['needed_relay_bit_stages_lower_bound'] / 1e6, 2),
                '&ndash;' if v['sum_traffic_length'] is None else fmt(v['sum_traffic_length'] / 1e12, 1))
    figs = []
    for c in C:
        m = c['metrics']
        lj = json.loads((Path(a.links_dir) / (m['candidate'] + '.links.json')).read_text())
        figs.append('<figure>%s<figcaption><b>%s</b> &middot; traffic&times;length %s M bit&middot;um/cycle &middot; worst field round trip %s mm<br>%s</figcaption></figure>' % (
            draw.svg(lj, 520), html.escape(m['candidate']), fmt(m['sum_traffic_bit_um_M']), fmt(m['field_worst_path_um'] / 1e3),
            html.escape(' | '.join(n for n in m['notes'] if not n.startswith('columns'))[:420])))
    cls_names = ['field', 'su', 'coll+hop', 'coll', 'engram', 'hbm', 'select']
    crow = ['<tr><td>%s</td>%s</tr>' % (html.escape(c['metrics']['candidate']), ''.join(
        '<td>%s</td>' % fmt(c['metrics']['by_class_traffic_bit_um_M'].get(k, 0), 1) for k in cls_names)) for c in C]
    rec = next(c['metrics'] for c in C if c['metrics']['candidate'] == a.rec)
    longl = ''.join('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
        l['id'], html.escape(' - '.join(l['ends'])), fmt(l['bits'], 0), fmt(l['length_um'], 0), html.escape(T['reasons'].get(l['cls'], T['reasons'].get('default'))))
        for l in rec['long_links'])
    ed = sorted(G['edges'], key=lambda e: -e['traffic'])
    erow = ''.join('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%.3f</td><td>%s</td></tr>' % (
        e['id'], e['kind'] + (' / ' + e['tree_mode'] if e.get('tree_mode') else ''), html.escape(e['ends'][0] + (' &rarr; %d frames' % (len(e['ends']) - 1) if e['kind'] == 'tree' else ' - ' + e['ends'][1])),
        fmt(e['width'], 0), e['cls'], e['duty'], fmt(e['traffic'], 0)) for e in ed[:30])
    page = ['<title>S81 Global Floorplan Study</title>',
            '<meta name="claude:viewport-fit-sides" content="cover">',
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@600&family=IBM+Plex+Sans:wght@400;600&display=swap">',
            '<style>%s</style><div class="wrap">' % CSS,
            '<div class="scope">Screen only &middot; block-level estimator &middot; nothing adopted without the coordinator &middot; not native</div>',
            '<h1>S81 die: global floorplan candidates</h1>',
            '<div class="sub">%s</div>' % html.escape(T['source']),
            '<div class="rec">%s</div>' % T['recommendation'],
            '<h2>One objective, every candidate</h2>',
            '<p>%s</p>' % T['objective'],
            '<div class="tbl"><table><thead><tr><th>Candidate</th><th>VM</th><th>&Sigma; width&times;len<br>M bit&middot;um</th><th>vs C0<br>traffic</th><th>&Sigma; traffic&times;len<br>M bit&middot;um/cyc</th><th>relay flops<br>k</th><th>bits &gt;500 um<br>k</th><th>worst field<br>round trip mm</th><th>cycles</th><th>cut p99 / gcell&gt;0.60</th><th>overlaps</th></tr></thead><tbody>%s</tbody></table></div>' % ''.join(rows),
            ('<h2>Explorer measurement (same code as the canonical record)</h2><p>%s</p>' % T.get('explorer', '') +
             '<div class="tbl"><table><thead><tr><th>Record</th><th>explorer id</th><th>hop bit&middot;um<br>G</th><th>over-reach bits<br>(&gt;500 um)</th><th>worst cut</th><th>windows<br>&gt;0.60</th><th>relay bit&middot;stages<br>M</th><th>needed relay<br>bit&middot;stages M</th><th>&Sigma; t&times;L<br>T bit&middot;um/token</th></tr></thead><tbody>%s</tbody></table></div>' % xrows) if xrows else '',
            '<h2>Same-scale floorplans</h2>',
            '<div class="legend"><span><i class="sw" style="background:var(--k-frame)"></i>field frame (fixed)</span><span><i class="sw" style="background:var(--k-hub)"></i>hub parent</span><span><i class="sw" style="background:var(--k-vm)"></i>VM / MIX4</span><span><i class="sw" style="background:var(--k-res)"></i>unbound reservation</span><span><i class="sw" style="background:var(--corr)"></i>spine crossing corridor</span><span><i class="sw" style="background:var(--c-field)"></i>field</span><span><i class="sw" style="background:var(--c-su)"></i>SU/HC</span><span><i class="sw" style="background:var(--c-coll)"></i>collective/links</span><span><i class="sw" style="background:var(--c-engram)"></i>Engram</span></div>',
            '<p class="sub">Full 33.0 x 26.0 mm die in every panel, one scale. Line width ~ sqrt(bits) for block links; trees drawn root-to-frame at low opacity.</p>',
            '<div class="grid">%s</div>' % ''.join(figs),
            '<h2>Traffic&times;length by class (M bit&middot;um per cycle)</h2>',
            '<div class="tbl"><table><thead><tr><th>Candidate</th>%s</tr></thead><tbody>%s</tbody></table></div>' % (''.join('<th>%s</th>' % k for k in cls_names), ''.join(crow)),
            '<h2>Findings</h2><ul>%s</ul>' % ''.join('<li>%s</li>' % f for f in T['findings']),
            '<h2>Long links in the recommended candidate, with reasons</h2>',
            '<div class="tbl"><table><thead><tr><th>link</th><th>ends</th><th>bits</th><th>length um</th><th>reason</th></tr></thead><tbody>%s</tbody></table></div>' % longl,
            '<h2>Data-flow graph: heaviest 30 links</h2>',
            '<p>%s</p>' % T['graph'],
            '<div class="tbl"><table><thead><tr><th>id</th><th>kind</th><th>ends</th><th>bits</th><th>class</th><th>duty</th><th>bits/cycle</th></tr></thead><tbody>%s</tbody></table></div>' % erow,
            '<h2>Method, assumptions, unknowns</h2><ul>%s</ul>' % ''.join('<li>%s</li>' % f for f in T['method']),
            '</div>']
    Path(a.out).write_text('\n'.join(page))


if __name__ == '__main__':
    main()
