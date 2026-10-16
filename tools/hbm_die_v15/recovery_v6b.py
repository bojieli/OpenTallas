#!/usr/bin/env python3
"""Audit the interrupted v6b adoption without modifying the active v15 contract.

The 770.4 mm2 study and the later 780 mm2 draft are different candidates.
New reserves below are preliminary windows, never inherited physical views.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_globalfp as F
import hbm_die_views as V


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--netlist-ref', default='af261fbcb')
    ap.add_argument('--suport-tree', default='/home/ubuntu/wt/hnl-suport-0030')
    a = ap.parse_args()
    d = ROOT / a.plan
    p = json.loads((d / 'compact.P.json').read_text())
    met = json.loads((d / 'compact.metrics.json').read_text())
    width, height = met['die_um']
    net = json.loads(subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                             f'{a.netlist_ref}:results/arch/hbm_die_v16/contract.json']))
    graph = json.loads((d / 'compact.graph.json').read_text())
    homes = {}
    for q in ('SW', 'SE', 'NW', 'NE'):
        # Empty region above the bank-pair's HC/SFU: 1,020 x 1,300 um.
        # Each calendar gets 0.60 mm2, versus the recorded ~0.52 SRAM lower bound.
        for g in range(4):
            hc, sfu = p[f'hc_{q}{g}'], p[f'sfu_{q}{g}']
            for k in range(2):
                x = hc['x'] if q.endswith('W') else hc['x'] + hc['w'] - 500
                x += (520 if q.endswith('W') else -520) * k
                y = max(hc['y'] + hc['h'], sfu['y'] + sfu['h']) + 20 if q.startswith('S') else min(hc['y'], sfu['y']) - 1220
                homes[f'xc_{q}{2*g+k}'] = dict(x=round(x, 3), y=round(y, 3), w=500, h=1200, orient='R0')
        # Reserve above the DMA/operand stack, with no change to its footprints.
        coll = p[f'coll_{q}']
        y = coll['y'] + coll['h'] + 742 if q.startswith('S') else coll['y'] - 1842
        x = coll['x'] + 620 if q.endswith('W') else coll['x'] + coll['w'] - 836
        homes[f'smw_{q}'] = dict(x=round(x, 3), y=round(y, 3), w=216, h=1100, orient='R0')
        # Correct the impossible monolithic draft window, without claiming a
        # legal incident-face assignment or replacing the production structure.
        x = coll['x'] if q.endswith('W') else coll['x'] + coll['w'] - 600
        cy = y if q.startswith('S') else y + 500
        homes[f'sucx_{q}'] = dict(x=round(x, 3), y=round(cy, 3), w=600, h=600, orient='R0')
        if q == 'SW':
            homes['cij_SW'] = dict(x=coll['x'], y=round(coll['y'] + coll['h'] + 21.6, 3), w=200, h=200, orient='R0')
    source = {}
    for n, b in homes.items():
        if n not in net['instances']:
            continue
        i = net['instances'][n]
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', f"{a.netlist_ref}:{i['source']}"])
        source[n] = dict(master=i['master'], params=i['params'], source=i['source'],
                         source_ref=a.netlist_ref, source_sha256=hashlib.sha256(raw).hexdigest(),
                         ports=i['ports'], pin_status='WINDOW_UNQUALIFIED', physical_view=None)
    for q in ('SW', 'SE', 'NW', 'NE'):
        for pre, mod in [('sucx', 'cxport'), ('sfus', 'sfustore')]:
            n = f'{pre}_{q}'
            path = f'rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_{mod}.sv'
            f = Path(a.suport_tree) / path
            source[n] = dict(master=f'ot_hbm_su_static_{mod}', source=path,
                             source_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),
                             source_ref=None, source_state='UNCOMMITTED_PENDING_NATIVE_PROOF',
                             pin_status='WINDOW_UNQUALIFIED', physical_view=None)
            ports = V.L.parse_module(str(f), source[n]['master'], {})['ports']
            source[n]['ports'] = {k: dict(direction=direction, bits=bits) for k, (direction, bits) in ports.items()}
    i = net['instances']['cij_SW']
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', f"{a.netlist_ref}:{i['source']}"])
    source['cij_SW'] = dict(master=i['master'], params=i['params'], source=i['source'],
                            source_ref=a.netlist_ref, source_sha256=hashlib.sha256(raw).hexdigest(),
                            ports=i['ports'], pin_status='WINDOW_UNQUALIFIED', physical_view=None)
    for n, s in source.items():
        b = homes.get(n, p.get(n))
        s['port_bits'] = sum(v['bits'] for v in s['ports'].values())
        s['perimeter_capacity_bits'] = int(2 * (b['w'] + b['h']) * 0.60 / 0.096)
        s['perimeter_capacity_pass'] = s['port_bits'] <= s['perimeter_capacity_bits']
        if n in p and n in homes:
            s['inherited_perimeter_capacity_bits'] = int(2 * (p[n]['w'] + p[n]['h']) * 0.60 / 0.096)
    allp = dict(p, **homes)
    (d / 'corrected.P.json').write_text(json.dumps(allp, indent=1) + '\n')
    F.W_DIE, F.H_DIE = width, height
    distances = {}
    for q in ('SW', 'SE', 'NW', 'NE'):
        distances[q] = dict(cx_coll_gap_um=F.gap(p[f'sucx_{q}'], p[f'coll_{q}'])[0],
                            cx_slice_gap_um=[F.gap(p[f'sucx_{q}'], p[f'su_{q}{g}'])[0] for g in range(4)],
                            sfustore_core_gap_um=F.gap(p[f'sfus_{q}'], p[f'sfucore_{q}'])[0])
    missing_edges = [n for n in source if not any(l['src'] == n or l['dst'] == n for l in graph['links'])]
    rep = dict(schema='opentallas.hbm.v6b.recovery.v1', qualification='FAIL_CLOSED_NOT_ADOPTED',
               historical_study_mm2=770.4, candidate_mm2=met['die_mm2'], die_um=met['die_um'],
               new_window_area_mm2=sum(b['w'] * b['h'] for b in homes.values()) / 1e6,
               homes=homes, source_pins=source, overlaps=F.overlaps(allp), outside=F.outside(allp),
               inherited_boundary_gap_lower_bounds=distances, graph_missing_incident_edges=missing_edges,
               impossible_pin_windows=[n for n, s in source.items() if not s['perimeter_capacity_pass']],
               warnings=['Outlines for xc/smw/sucx/sfus/cij are preliminary window grants, not measured mapped fit.',
                         'Existing pin cuts and relay costs exclude new connections listed in graph_missing_incident_edges.',
                         'Gap lower bounds are not source-bound pin routes or qualified relay placement.',
                         'No inherited physical views apply to new or resized masters.'])
    (d / 'recovery.json').write_text(json.dumps(rep, indent=1) + '\n')
    # Source-native to-scale figure of the corrected windows, not route proof.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(16, 12))
    for n, b in allp.items():
        new = n in homes
        color = '#f6b26b' if new else '#d9e6ef'
        ax.add_patch(Rectangle((b['x'], b['y']), b['w'], b['h'], facecolor=color,
                               edgecolor='#a40000' if new else '#445566', linewidth=0.5))
        if new or n.startswith(('coll_', 'sucore_', 'sfucore_', 'vmh_', 'sm_')):
            ax.text(b['x'] + b['w']/2, b['y'] + b['h']/2, n, fontsize=4, ha='center', va='center')
    ax.set(xlim=(0, width), ylim=(0, height), aspect='equal', xlabel='um', ylabel='um',
           title='HBM 780 mm2 join-window correction: orange reserves; source-pin faces and graph OPEN')
    fig.tight_layout()
    fig.savefig(d / 'corrected_windows.png', dpi=160)
    plt.close(fig)
    print(json.dumps({k: rep[k] for k in ('qualification', 'candidate_mm2', 'new_window_area_mm2', 'overlaps', 'outside', 'graph_missing_incident_edges')}))


if __name__ == '__main__':
    main()
