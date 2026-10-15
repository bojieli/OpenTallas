#!/usr/bin/env python3
"""Same-scale SVG floorplan of a links.json candidate (GLOBAL-FP-S).  Colours come from CSS variables so the
comparison page themes them; every figure uses the full 33 x 26 mm die at one scale."""
import json, math, sys

KIND_VAR = {'hub': '--k-hub', 'res': '--k-res', 'phy': '--k-io', 'ctrl': '--k-io', 'svc': '--k-io', 'link': '--k-io',
            'band_blk': '--k-io', 'svcj': '--k-io', 'frame': '--k-frame'}
CLASS_VAR = {'field': '--c-field', 'su': '--c-su', 'coll': '--c-coll', 'coll+hop': '--c-coll', 'hbm': '--c-hbm',
             'select': '--c-hbm', 'engram': '--c-engram'}
LABEL = {'sp_su_s': 'SU', 'sp_vm': 'VM', 'sp_capture': 'cap', 'sp_gather': 'gather', 'sp_pq': 'PQ', 'sp_wfc': 'wfc',
         'sp_collective': 'COLL', 'sp_hc_s': 'HC_s', 'sp_hc_t': 'HC_t', 'mix4': 'MIX4', 'phy_SW': 'HBM PHY',
         'svc_SW': 'svc', 'sp_host': 'host', 'bk_selector': 'selector', 'bk_collector': 'collector'}


def svg(lj, width_px=520):
    W, H = lj['die']['w_um'], lj['die']['h_um']
    s = width_px / W
    hp = H * s
    Y = lambda y: hp - y * s
    out = ['<svg viewBox="0 0 %.1f %.1f" width="100%%" role="img" aria-label="%s floorplan" xmlns="http://www.w3.org/2000/svg">'
           % (width_px, hp, lj['candidate'])]
    out.append('<rect x="0" y="0" width="%.1f" height="%.1f" fill="var(--die)" stroke="var(--rule)"/>' % (width_px, hp))
    nodes = {n['id']: n for n in lj['nodes']}
    m = lj['metrics']
    if m.get('corridor'):
        x, y, w, h = m['corridor']
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="var(--corr)" />' % (x * s, Y(y + h), w * s, h * s))
    for n in lj['nodes']:
        k = 'frame' if n['id'].startswith('F') else n['group']
        var = KIND_VAR.get(k, '--k-io')
        if n['id'] in ('sp_vm', 'mix4'):
            var = '--k-vm'
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="var(%s)" stroke="var(--rule)" stroke-width="0.4"><title>%s %.0fx%.0f um</title></rect>'
                   % (n['x_um'] * s, Y(n['y_um'] + n['h_um']), n['w_um'] * s, n['h_um'] * s, var, n['id'], n['w_um'], n['h_um']))
    # links: trees thin, p2p width ~ sqrt(bits)
    for l in lj['links']:
        col = CLASS_VAR.get(l['class'], '--c-hbm')
        a = (l['src']['x_um'] * s, Y(l['src']['y_um']))
        if len(l['dst']) > 1:
            for d in l['dst']:
                out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(%s)" stroke-opacity="0.18" stroke-width="0.6"/>'
                           % (a[0], a[1], d['x_um'] * s, Y(d['y_um']), col))
        else:
            d = l['dst'][0]
            sw = max(0.6, math.sqrt(l['bits']) / 22)
            out.append('<path d="M%.1f %.1f L%.1f %.1f L%.1f %.1f" fill="none" stroke="var(%s)" stroke-opacity="0.85" stroke-width="%.2f"><title>%s %s-%s %d b %.0f um</title></path>'
                       % (a[0], a[1], d['x_um'] * s, a[1], d['x_um'] * s, Y(d['y_um']), col, sw, l['id'], l['src']['node'], d['node'], l['bits'], l['length_um']))
    for nid, lab in LABEL.items():
        n = nodes.get(nid)
        if not n:
            continue
        out.append('<text x="%.1f" y="%.1f" font-size="9" text-anchor="middle" fill="var(--ink)" font-family="var(--mono)">%s</text>'
                   % ((n['x_um'] + n['w_um'] / 2) * s, Y(n['y_um'] + n['h_um'] / 2) + 3, lab))
    out.append('</svg>')
    return '\n'.join(out)


if __name__ == '__main__':
    print(svg(json.load(open(sys.argv[1]))))
