#!/usr/bin/env python3
"""HBMb/SMH7-VMG 2026-10-21: g8r clock-region map of a VM hub-glue tile from a placed seam census (vms_glue_seam_census.tcl).
Each register GROUP the g8r RTL can clock separately (tile chain stage per bank, ring-stop lane band / pair / half, hub bank
request stage / face-group copy, reset leaf) gets the band (0 s / 1 core / 2 n) that holds the majority of its flops in the
measured g7s placement.  Seams are lane-aligned (3 lanes | 2 lanes + header | 3 lanes): SEAMS = (580.1, 976.0) um.
    vms_glue_region_map.py <seam.txt> <out.json> --source <odb path text>
"""
import collections, json, re, sys
SEAMS = (580.1, 976.0)
W = {'xq': 276, 'xq2': 276, 'eg': 276, 'pq': 285, 'pr': 266, 'status': 18, 'xq_done': 1, 'xq2_done': 1, 'flt': 1}


def key(n):
    n = re.sub(r'\$.*', '', n.replace('\\', ''))
    m = re.match(r'^bk_(\w+?)_s(\d+)\[(\d+)\]$', n)
    if m and m.group(1) in W:
        return f"T:{m.group(1)}_s{m.group(2)}:b{int(m.group(3)) // W[m.group(1)]}"
    m = re.match(r'^bk_(\w+?)_s(\d+)$', n)
    if m and m.group(1) in W:
        return f"T:{m.group(1)}_s{m.group(2)}:b0"
    m = re.match(r'^bank_status_s(\d+)\[(\d+)\]$', n)
    if m:
        return f"T:status_s{m.group(1)}:b{int(m.group(2)) // 18}"
    m = re.match(r'^b(\d)_(\w+?)(\[\d+\])?$', n)
    if m:
        return f"T:{m.group(2)}_pin:b{m.group(1)}"
    m = re.match(r'^(\w+)_g_s(\d+)', n)
    if m:
        return f"T:{m.group(1)}_g_s{m.group(2)}"
    if not n.startswith('u_core.'):
        return 'T:' + re.sub(r'\[\d+\]', '', n)
    n = n[7:]
    m = re.match(r'^u_(c?cw)\.(.*)$', n)
    if m:
        r = m.group(2)
        for pat, fmt in ((r'a_l\[(\d+)\]', None), (r'a_eg\[(\d+)\]', 'S:a_eg:b{}'), (r'band\[(\d)\]', 'S:band:l{}'),
                         (r'half\[(\d)\]\.pi_m', 'S:pim{}'), (r'half\[(\d)\]\.g_b0\.ri_m', 'S:rim'),
                         (r'(?:pl|pv)\[(\d)\]', 'S:pair{}'), (r'(?:hl|hb)\[(\d)\]', 'S:hl{}')):
            mm = re.match(pat, r)
            if mm:
                if fmt is None:
                    b = int(mm.group(1)) // 276
                    return f"S:a_l:l{b if b < 8 else 'h'}"
                return fmt.format(*mm.groups())
        return 'S:hdr'
    m = re.match(r'^u_hub\.req_grp\[(\d)\]\.bank\[(\d)\]', n)
    if m:
        return f"H:bank{m.group(2)}"
    m = re.match(r'^u_hub\.req_grp\[(\d)\]', n)
    if m:
        return f"H:qrg{m.group(1)}"
    m = re.match(r'^u_hub\.rsp_grp\[(\d)\]', n)
    if m:
        return f"H:rsp{m.group(1)}"
    if n.startswith('u_hub.'):
        return 'H:core'
    m = re.match(r'^u_rst\.grp\[(\d+)\]\.lf\[(\d+)\]', n)
    if m:
        return f"R:lf{m.group(2)}"
    if n.startswith('u_rst.'):
        return 'R:sync'
    m = re.match(r'^(\w+_r)(\[|$)', n)
    return 'C:' + (m.group(1) if m else n.split('.')[0])


def main():
    src, out = sys.argv[1], sys.argv[2]
    origin = sys.argv[sys.argv.index('--source') + 1] if '--source' in sys.argv else src
    band = lambda y: 0 if y < SEAMS[0] else (1 if y < SEAMS[1] else 2)
    g = collections.defaultdict(lambda: [0, 0, 0])
    for ln in open(src):
        p = ln.split()
        g[key(p[0])][band(float(p[1]))] += 1
    reg = {k: max(range(3), key=lambda i: v[i]) for k, v in g.items()}
    tot = [0, 0, 0]
    for k, v in g.items():
        tot[reg[k]] += sum(v)
    rec = dict(schema='opentallas.vms_glue.g8r_region_map.v1', seams_um=list(SEAMS), regions=['s', 'core', 'n'],
               source=origin, flops_per_region=tot,
               groups={k: dict(region=reg[k], counts=g[k], majority=round(max(g[k]) / sum(g[k]), 3)) for k in sorted(g)})
    open(out, 'w').write(json.dumps(rec, indent=0) + '\n')
    print('REGION_MAP', out, 'flops per region', tot, 'groups', len(g))


if __name__ == '__main__':
    main()
