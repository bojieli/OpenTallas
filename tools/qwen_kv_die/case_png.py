#!/usr/bin/env python3
"""KVPLAN 1815: floorplan picture of a prepared KV/system die CASE (no die job needed): every placed instance of
case_kv/{place.tcl, elements.lef, die.v} as its outline, coloured by family; relay standards / reset stations drawn
as dots (red = qkd_rlys_1 reset stations of kv_rst_regional, orange = data relay replicas).
    case_png.py CASE --out PNG [--window x0,y0,x1,y1] [--title T]
"""
import argparse
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

FAM = [(r'^(qkd_hbm3e_phy_pc|ot_qfd_serdes|ot_qkvd_ucie)', '#555555', 'PHY'),
       (r'^ot_qwen_tp8_pv', '#8e44ad', 'PV pair'),
       (r'^(ot_qkh_|qkh_|qkd_hgs|qkd_hss)', '#2e86c1', 'head leaves'),
       (r'^qkd_ectl', '#17a589', 'engine control'),
       (r'^qkd_ctrl', '#d4ac0d', 'HBM controller strip'),
       (r'^(qkd_land|qkd_astk|qkd_pv16_vport)', '#ca6f1e', 'landing / ASTK / vport'),
       (r'^(qkd_cdc|qkd_kvwq)', '#a04000', 'CDC / write queue'),
       (r'^(qkd_hslice|qkd_host)', '#7d3c98', 'HOST'),
       (r'.', '#95a5a6', 'other')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('case')
    ap.add_argument('--out', required=True)
    ap.add_argument('--window')
    ap.add_argument('--title', default='')
    a = ap.parse_args()
    size, cur = {}, None
    for ln in open(a.case + '/elements.lef'):
        s = ln.strip()
        if s.startswith('MACRO '):
            cur = s.split()[1]
        elif s.startswith('SIZE') and cur and cur not in size:
            t = s.split()
            size[cur] = (float(t[1]), float(t[3]))
    mst = {}
    for m in re.finditer(r'^\s+(\w+) (\S+) \(', open(a.case + '/die.v').read(), re.M):
        mst[m.group(2)] = m.group(1)
    pos = []
    for ln in open(a.case + '/place.tcl'):
        m = re.search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)', ln)
        if m and m.group(1) in mst and mst[m.group(1)] in size:
            pos.append((m.group(1), mst[m.group(1)], float(m.group(2)), float(m.group(3))))
    W = max(x + size[mm][0] for _, mm, x, _ in pos)
    H = max(y + size[mm][1] for _, mm, _, y in pos)
    win = [float(v) for v in a.window.split(',')] if a.window else [0, 0, W, H]
    ww, wh = win[2] - win[0], win[3] - win[1]
    fig, ax = plt.subplots(figsize=(8 * ww / max(ww, wh) + 3, 8 * wh / max(ww, wh) + 1), dpi=180)
    used = set()
    rx, ry, ox, oy = [], [], [], []
    for nm, mm, x, y in pos:
        w, h = size[mm]
        if x > win[2] or x + w < win[0] or y > win[3] or y + h < win[1]:
            continue
        if mm.startswith(('qkd_rlys_', 'qkd_rly_', 'qkd_rst_region')):
            (rx if (mm == 'qkd_rlys_1' and nm.startswith('rrs_')) else ox).append(x + w / 2)
            (ry if (mm == 'qkd_rlys_1' and nm.startswith('rrs_')) else oy).append(y + h / 2)
            continue
        for pat, col, lab in FAM:
            if re.match(pat, mm):
                break
        used.add((lab, col))
        ax.add_patch(Rectangle((x, y), w, h, facecolor=col, edgecolor='black', linewidth=0.1, alpha=0.75))
    ms = 0.3 if not a.window else 2
    ax.plot(ox, oy, '.', color='orange', ms=ms, label=f'data relay replicas ({len(ox)})')
    ax.plot(rx, ry, '.', color='red', ms=ms, label=f'reset stations ({len(rx)})')
    for lab, col in sorted(used):
        ax.add_patch(Rectangle((0, 0), 0, 0, facecolor=col, label=lab))
    ax.set_xlim(win[0], win[2])
    ax.set_ylim(win[1], win[3])
    ax.set_aspect('equal')
    ax.set_title(a.title or a.case, fontsize=8)
    ax.legend(fontsize=5, loc='upper left', bbox_to_anchor=(1.01, 1))
    ax.tick_params(labelsize=5)
    fig.savefig(a.out, bbox_inches='tight')
    print(a.out, len(pos), 'instances', len(rx), 'reset stations')


if __name__ == '__main__':
    main()
