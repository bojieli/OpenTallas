#!/usr/bin/env python3
"""GLOBAL-FP-H comparison page: same-scale floorplans + one-objective table for every scored candidate.

  python3 tools/hbm_globalfp_page.py --graph graph.json --ref ref.json --sel sel.json --out index.html
sel.json: [{"tag":..., "dir":..., "label":..., "family":..., "note":...}, ...] (first = current)
"""
import argparse, html, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hbm_globalfp as F
import hbm_globalfp_run as R

KC = {'SM': 'sm', 'PHY': 'phy', 'PC': 'pc', 'VM_bank': 'vm', 'VM_hub': 'vm2', 'SU': 'eng', 'SFU': 'eng', 'HC': 'eng', 'HC_ENGINE': 'eng2',
      'QUANT': 'eng', 'COLL': 'coll', 'SERDES': 'io', 'ENDPOINT': 'io', 'ATT_tile': 'att', 'ATT_gather': 'att2', 'ATT_QP': 'att2',
      'ATT_reduce': 'att2', 'ATT_ctl': 'att2', 'IDX': 'idx'}
LC = {'SM_HBM': 'lh', 'HBM_K': 'lh', 'KV': 'lh', 'SM_X': 'lx', 'ATT_Q': 'la', 'ATT_O': 'la', 'ATT_QP': 'la', 'ATT_KVX': 'la', 'ATT_SC': 'la', 'ATT_PV': 'la', 'ATT_P': 'la',
      'COLL_RING': 'lc', 'VM_RING': 'lc', 'COLL_EP': 'lc', 'COLL_VM': 'lc', 'EP_SERDES': 'lc', 'KV_DESC': 'la', 'SM_OUT': 'lx', 'LG_SU': 'lx'}


def svg(G, P, m, scale=0.0118, top=160):
    W, H = F.W_DIE * scale, F.H_DIE * scale
    Y = lambda y: H - y * scale
    o = [f'<svg viewBox="0 0 {W:.1f} {H:.1f}" role="img" class="fp"><rect class="die" x="0" y="0" width="{W:.1f}" height="{H:.1f}"/>']
    for i, r in sorted(P.items(), key=lambda kv: -kv[1]['w'] * kv[1]['h']):
        k = G['nodes'][i]['kind']
        o.append(f'<rect class="b {KC.get(k, "o")}" x="{r["x"]*scale:.1f}" y="{Y(r["y"]+r["h"]):.1f}" width="{max(.6, r["w"]*scale):.1f}" height="{max(.6, r["h"]*scale):.1f}"><title>{html.escape(i)} ({k})</title></rect>')
    per = sorted([p for p in m['_per'] if p[1] > F.REACH], key=lambda p: -p[0]['bits'] * p[1])[:top]
    for l, d, ps, pt in per:
        sw = max(0.35, min(2.2, l['bits'] / 900))
        o.append(f'<path class="l {LC.get(l["cls"], "lo")}" stroke-width="{sw:.2f}" d="M{ps[0]*scale:.1f},{Y(ps[1]):.1f}L{pt[0]*scale:.1f},{Y(ps[1]):.1f}L{pt[0]*scale:.1f},{Y(pt[1]):.1f}"><title>{html.escape(l["id"])} {l["bits"]} b, {d:.0f} um</title></path>')
    o.append('</svg>')
    return ''.join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--graph', required=True); ap.add_argument('--ref', required=True); ap.add_argument('--sel', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--intro', default=''); ap.add_argument('--extra', default='')
    a = ap.parse_args()
    G0 = json.load(open(a.graph)); ref = json.load(open(a.ref)); sel = json.load(open(a.sel))
    graphs = {a.graph: G0}
    rows, cards = [], []
    base = None
    for s in sel:
        mm = json.load(open(os.path.join(s['dir'], s['tag'] + '.metrics.json')))
        F.set_die(mm.get('die_h') or F.H_DIE_V15)
        gp = s.get('graph', a.graph)
        if gp not in graphs:
            graphs[gp] = json.load(open(gp))
        G = graphs[gp]
        for t in mm.get('transforms', []):
            G = {'quad_drain': R.t_quad_drain, 'hc_quad': R.t_hc_per_quadrant, 'noatt': R.t_noatt, 'npg4': R.t_npg4}[t](G)
        P = json.load(open(os.path.join(s['dir'], s['tag'] + '.P.json')))
        m = F.score(G, P, ref)
        if base is None:
            base = m
        area = sum(n['area_mm2'] for n in G['nodes'].values())
        d = lambda k: (m[k] / base[k] - 1) * 100
        rows.append(f'<tr class="{"cur" if s is sel[0] else ""}"><th scope="row">{html.escape(s["label"])}<span class="fam">{html.escape(s["family"])}</span></th>'
                    f'<td>{m["J"]:.2f}</td><td>{m["fixed_return_violations"]}/{m["worst_cut"]["segments_over_060"]}</td><td>{m["sum_bits_mm"]/1e6:.3f}<i>{d("sum_bits_mm"):+.0f}%</i></td>'
                    f'<td>{m["traffic_mm_qwen"]/1e9:.2f}<i>{d("traffic_mm_qwen"):+.0f}%</i></td><td>{m["traffic_mm_ds"]/1e9:.2f}<i>{d("traffic_mm_ds"):+.0f}%</i></td>'
                    f'<td>{m["bits_over_500"]/1e3:.0f}k</td><td>{m["relay_flops"]/1e6:.2f}M</td><td class="{"bad" if m["fixed_return_violations"] else ""}">{m["fixed_return_violations"]}</td>'
                    f'<td class="{"bad" if m["worst_cut"]["ratio"] > .6 else "ok"}">{m["worst_cut"]["ratio"]:.2f}</td><td>{m["n_long_returns"]}</td><td>{area:.1f}</td><td>{F.W_DIE*F.H_DIE/1e6:.0f}</td></tr>')
        lr = ''.join(f'<li><code>{html.escape(r["link"])}</code> {r["bits"]} b, {r["length_um"]/1000:.1f} mm. {html.escape(r["reason"])}</li>' for r in m['long_returns'][:5])
        cards.append(f'<figure class="card" id="{html.escape(s["tag"])}"><figcaption><b>{html.escape(s["label"])}</b><span class="fam">{html.escape(s["family"])}</span>'
                     f'<span class="j">J {m["J"]:.2f}</span></figcaption>{svg(G, P, m)}<p class="note">{html.escape(s.get("note", ""))}</p>'
                     f'<details><summary>Longest wide returns</summary><ul class="lr">{lr}</ul></details></figure>')
    page = TEMPLATE.replace('%INTRO%', a.intro).replace('%ROWS%', '\n'.join(rows)).replace('%CARDS%', '\n'.join(cards)).replace('%EXTRA%', a.extra)
    open(a.out, 'w').write(page)


TEMPLATE = r'''<title>HBM Die Global Floorplan</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@400;600&family=IBM+Plex+Mono:wght@400;500&family=Literata:opsz,wght@7..72,500&display=swap">
<style>
/* Layout: report column; one-objective table, then a same-scale grid of die plans (1 mm = 11.8 px) */
:root{--bg:#f6f7f5;--fg:#1d2321;--mute:#5c6863;--line:#cdd5d1;--panel:#ffffff;--accent:#0f6b5c;--bad:#b3261e;--ok:#2e7d32;
--sm:#e9c99d;--phy:#7d8784;--pc:#bfae78;--vm:#2b68a8;--vm2:#79a6d6;--eng:#3f9a52;--eng2:#1d5e2c;--coll:#7d4aa0;--io:#4b2a73;--att:#d86b35;--att2:#b8432c;--idx:#178f9c;
--lh:#a4760a;--lx:#2b68a8;--la:#c0392b;--lc:#7d4aa0;--lo:#55605c;
--f-display:"Literata",Georgia,serif;--f-body:"IBM Plex Sans Condensed","Arial Narrow",system-ui,sans-serif;--f-mono:"IBM Plex Mono",ui-monospace,monospace;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111614;--fg:#e3e9e6;--mute:#9aa7a1;--line:#2c3532;--panel:#18201d;--accent:#5cc2ad;--bad:#ff8a80;--ok:#81c784;
--sm:#5e4a2e;--phy:#59625f;--pc:#7c7046;--vm:#5d97d6;--vm2:#3b5d84;--eng:#5fbf72;--eng2:#2f8a46;--coll:#a77cc8;--io:#8c6bbd;--att:#e58a57;--att2:#e06650;--idx:#3fc0cc;--lh:#e0b040;--lx:#7fb3ea;--la:#ff7b6b;--lc:#c9a0e8;--lo:#a5b1ac;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#111614;--fg:#e3e9e6;--mute:#9aa7a1;--line:#2c3532;--panel:#18201d;--accent:#5cc2ad;--bad:#ff8a80;--ok:#81c784;
--sm:#5e4a2e;--phy:#59625f;--pc:#7c7046;--vm:#5d97d6;--vm2:#3b5d84;--eng:#5fbf72;--eng2:#2f8a46;--coll:#a77cc8;--io:#8c6bbd;--att:#e58a57;--att2:#e06650;--idx:#3fc0cc;--lh:#e0b040;--lx:#7fb3ea;--la:#ff7b6b;--lc:#c9a0e8;--lo:#a5b1ac;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font-family:var(--f-body);font-size:15px;line-height:1.5}
main{max-width:1240px;margin:0 auto;padding-block:28px 60px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:26px}
h1{font-family:var(--f-display);font-weight:500;font-size:2rem;margin:0;text-wrap:balance}
h2{font-family:var(--f-display);font-weight:500;font-size:1.3rem;margin:0 0 8px;text-wrap:balance}
p,li{max-width:70ch}
.eyebrow{font-family:var(--f-mono);font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.lede{color:var(--mute);margin:6px 0 0}
section{display:grid;gap:10px;min-width:0}
.tw{overflow-x:auto;border:1px solid var(--line);background:var(--panel)}
table{border-collapse:collapse;font-variant-numeric:tabular-nums;width:100%;font-size:.88rem}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
thead th{font-family:var(--f-mono);font-size:.72rem;font-weight:500;color:var(--mute);text-align:right;vertical-align:bottom;white-space:normal}
tbody th{text-align:left;font-weight:600}
td i{font-style:normal;color:var(--mute);font-size:.78rem;margin-left:5px}
tr.cur th,tr.cur td{background:color-mix(in srgb,var(--accent) 8%,transparent)}
.fam{display:block;font-family:var(--f-mono);font-size:.7rem;font-weight:400;color:var(--mute)}
td.bad{color:var(--bad);font-weight:600} td.ok{color:var(--ok)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:18px}
.card{margin:0;background:var(--panel);border:1px solid var(--line);padding:12px;display:grid;gap:8px;min-width:0}
.card figcaption{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline}
.card .fam{display:inline}
.card .j{margin-left:auto;font-family:var(--f-mono);font-size:.85rem;color:var(--accent)}
svg.fp{width:100%;height:auto;display:block}
.die{fill:var(--bg);stroke:var(--mute);stroke-width:.8}
.b{stroke:var(--fg);stroke-opacity:.35;stroke-width:.25}
.sm{fill:var(--sm)}.phy{fill:var(--phy)}.pc{fill:var(--pc)}.vm{fill:var(--vm)}.vm2{fill:var(--vm2)}.eng{fill:var(--eng)}.eng2{fill:var(--eng2)}.coll{fill:var(--coll)}.io{fill:var(--io)}.att{fill:var(--att)}.att2{fill:var(--att2)}.idx{fill:var(--idx)}.o{fill:var(--mute)}
.l{fill:none;stroke-opacity:.55}.lh{stroke:var(--lh)}.lx{stroke:var(--lx)}.la{stroke:var(--la)}.lc{stroke:var(--lc)}.lo{stroke:var(--lo)}
.note{font-size:.85rem;color:var(--mute);margin:0}
.lr{font-size:.8rem;margin:6px 0 0;padding-left:18px} code{font-family:var(--f-mono);font-size:.78rem}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.8rem;color:var(--mute)}
.legend span::before{content:"";display:inline-block;width:11px;height:11px;margin-right:5px;vertical-align:-1px;background:var(--c)}
.rec{border-left:3px solid var(--accent);padding:4px 0 4px 14px;background:transparent}
dl.k{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;margin:0;font-size:.88rem}
dl.k dt{font-family:var(--f-mono);font-size:.78rem;color:var(--mute)} dl.k dd{margin:0;min-width:0}
details summary{cursor:pointer;font-size:.82rem;color:var(--accent)}
details summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
</style>
<main>
<header><div class="eyebrow">GLOBAL-FP-H &middot; HBM accelerator die &middot; 32.98 &times; 25.98 mm</div>
<h1>HBM Die Global Floorplan</h1>%INTRO%</header>
<section><h2>One objective, every candidate</h2>
<div class="tw"><table><thead><tr><th scope="col" style="text-align:left">Candidate</th><th scope="col">J (baseline raw = ref)</th><th scope="col">LG fixed-return violations / cut segments &gt;0.60</th><th scope="col">&Sigma; bits&middot;mm (M)</th><th scope="col">Qwen traffic&middot;length (GB&middot;mm/token)</th><th scope="col">DS traffic&middot;length (GB&middot;mm/token)</th><th scope="col">bits over 500 &micro;m</th><th scope="col">relay flops (needed)</th><th scope="col">fixed-return LG links &gt;500 &micro;m</th><th scope="col">worst cut (&le;0.60)</th><th scope="col">returns &gt;2 mm</th><th scope="col">block area mm&sup2;</th><th scope="col">die mm&sup2;</th></tr></thead>
<tbody>%ROWS%</tbody></table></div>
<p class="note">Percentages are against the first row. Lengths are closest-outline Manhattan gaps (pins unassigned), the same optimistic rule for every candidate. Cut: 1&nbsp;mm segments of every 100&nbsp;&micro;m line, 14.06 usable tracks/&micro;m, routes split HV/VH avoiding PHYs.</p>
</section>
%EXTRA%
<section><h2>Same-scale plans</h2>
<div class="legend"><span style="--c:var(--sm)">SM frame</span><span style="--c:var(--pc)">PC controllers</span><span style="--c:var(--vm)">VM bank + LG chain</span><span style="--c:var(--eng)">SU/SFU/HC/QUANT port groups</span><span style="--c:var(--coll)">COLL</span><span style="--c:var(--io)">SerDes/endpoint</span><span style="--c:var(--idx)">IDX</span><span style="--c:var(--lh)">HBM/KV link</span><span style="--c:var(--lx)">x-load link</span><span style="--c:var(--la)">KV descriptor link</span><span style="--c:var(--lc)">ring/collective link</span></div>
<p class="note">Lines: the 160 widest-times-longest links over 500 &micro;m, stroke width by bits.</p>
<div class="grid">%CARDS%</div></section>
</main>
'''

if __name__ == '__main__':
    main()
