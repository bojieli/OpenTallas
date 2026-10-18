#!/usr/bin/env python3
"""KVJ-A3 r2: ref_tile specs for the single-family HOST-cluster children (core family, one ck_core entry).

Tops are the generated wrappers in rtl/qwen_sys/host_cluster_20261017/qkd_hr_cluster.v (or the member itself for a
direct child).  Pin faces follow the r2 floorplan intent (CENTROIDS: each port goes on the face toward the centroid of
the children it talks to; a die port toward the nearest cluster edge); buses cover the whole face (pin_ranges +
pin_balance).  Outline: max(std area / UTIL, the perimeter that keeps <= PIN_PER_UM pins/um, the macros), on the
21.6-um grid, aspect <= 1.6.  The die tools re-pin top-down at the parent (owner rule 10-13); these faces are the
pre-route proposal.  Benches: the cluster composition gate (bench/cluster_gate.py) exact + this child's reset mutant.

usage: child_specs.py OUTDIR [child ...]
"""
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RES = ROOT / 'results/arch/qwen_split_1014/host_root_cluster'
CLUSTER_DIR = 'rtl/qwen_sys/host_cluster_20261017'
W, H = 950.4, 648.0
# r2 floorplan intent (um, cluster origin SW): adp x8 = S band 0..172.8; the rest per data flow
CENTROIDS = dict(qkd_hr_phy_adp=(475, 86), qkd_hr_phy_pad=(300, 230), qkd_hr_cdc_pc=(520, 250),
                 qkd_hr_core_tx=(790, 250), qkd_hr_core_rx=(140, 280), qkd_hr_core_peer=(480, 410),
                 qkd_hr_core_prompt=(170, 450), qkd_hr_core_guard=(800, 400), qkd_hr_core_queue=(330, 590),
                 qkd_hr_core_order=(110, 600), qkd_hr_cdc_host=(560, 590), qkd_hr_ingest_qm=(800, 560))
UTIL, PIN_PER_UM = 0.5, 6.0
MACROS = {'ot_sram_1r1w_1024x256_m2_r2c2': (174.744, 70.470), 'ot_sram_1rw_256x64_m4_r2c2': (66.312, 17.820)}
FLAT = 1.0                                               # hier census area ~ the route synthesis (queue gate: 7,286 vs 5,415 hier)
PINFLOP_UM2 = 0.45                                       # one pin register + its anchoring per pin bit
DIRECT_TOP = {}


def inst_of(direct, child):
    return dict(qkd_hr_core_tx='u_rank__u_control__u_packet__u_tx').get(child) if direct else None


def face_of(child, peers):
    cx, cy = CENTROIDS[child]
    vx = vy = 0.0
    for p in peers:
        if p.startswith('DIE:'):
            d = dict(W=cx, E=W - cx, S=cy, N=H - cy)
            f = min(d, key=d.get)
            vx += {'W': -1, 'E': 1}.get(f, 0)
            vy += {'S': -1, 'N': 1}.get(f, 0)
            continue
        t = 'qkd_hr_' + p[2:] if p.startswith('u_') and ('qkd_hr_' + p[2:]) in CENTROIDS else None
        if t is None:
            t = 'qkd_hr_phy_adp' if 'adapter' in p else ('qkd_hr_core_rx' if '__u_rx' in p else
                                                         ('qkd_hr_core_tx' if '__u_tx' in p else 'qkd_hr_phy_pad'))
        px, py = CENTROIDS[t]
        n = math.hypot(px - cx, py - cy) or 1
        vx += (px - cx) / n
        vy += (py - cy) / n
    score = dict(E=vx, W=-vx, N=vy, S=-vy)
    return sorted(score, key=lambda f: -score[f])


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    ports = json.load(open(RES / 'r2_ports.json'))
    census = {x['path']: x for x in json.load(open(RES / 'census/census_rollup.json'))['nodes']}
    part = json.load(open(RES / 'partition_r2.json'))['children']
    srcs = [l.strip() for l in (ROOT / 'tools/qwen_kv_die/host_cluster/bench/sources.txt').read_text().splitlines()
            if l.strip() and not l.startswith('physical/')]
    want = sys.argv[2:] or ['qkd_hr_core_prompt', 'qkd_hr_core_peer', 'qkd_hr_core_guard', 'qkd_hr_core_queue',
                            'qkd_hr_core_order', 'qkd_hr_core_tx']
    for child in want:
        direct = child in DIRECT_TOP
        mem = part[child]['members']
        area = sum(census[m]['std_area_um2'] for m in mem) * FLAT
        macros = {}
        for m in mem:
            for k, v in (census[m]['macros'] or {}).items():
                macros[k] = macros.get(k, 0) + v
        if direct:
            top, params, src = DIRECT_TOP[child]
            text = (ROOT / src[0]).read_text()
            mod = re.search(r'module\s+' + top + r'\b.*?\);', text, re.S).group(0)
            plist = [(m.group(2), m.group(1)) for m in re.finditer(r'\b(input|output)\b[^;,)]*?(\w+)\s*(?=[,)])', mod)]
            prow = {p['port']: p for p in ports.get(child, {}).get('ports', [])}
            rows = []
            for name, d in plist:
                rows.append(dict(port=name, dir=d, width=1, peers=['u_core_peer']))
        else:
            top, params, src = child, {}, [f'{CLUSTER_DIR}/{child}.v'] + srcs
            rows = ports[child]['ports']
        bits = sum(r['width'] for r in rows)
        clk = [r['port'] for r in rows if re.match(r'^(ck|clk)', r['port'])]
        rst = [r['port'] for r in rows if r['dir'] == 'input' and re.search(r'(rst_n|^por_n$|^rst$)', r['port'])]
        mac_area = sum(MACROS[k][0] * MACROS[k][1] * n for k, n in macros.items())
        need_area = (area + bits * PINFLOP_UM2) / UTIL + mac_area * 1.3
        # square-ish outline whose perimeter carries every pin at PIN_PER_UM (15 % slack), macros permitting
        side = max(math.sqrt(need_area), bits * 1.15 / PIN_PER_UM / 4, 64.8)
        w = max(side, max([MACROS[k][0] + 30 for k in macros] + [0]))
        h = max(side, need_area / w)
        g = 21.6
        w, h = math.ceil(w / g) * g, math.ceil(h / g) * g
        cap = dict(N=w * PIN_PER_UM, S=w * PIN_PER_UM, E=h * PIN_PER_UM, W=h * PIN_PER_UM)
        pins = {f: [] for f in 'NSEW'}
        load = {f: 0 for f in 'NSEW'}
        for r in sorted((r for r in rows if r['port'] not in clk), key=lambda r: -r['width']):
            order = face_of(child, r['peers'] or ['u_core_peer'])
            f = next((f for f in order if load[f] + r['width'] <= cap[f]), min(load, key=lambda f: load[f] / cap[f]))
            pins[f].append(r['port'])
            load[f] += r['width']
        # the clock sits on the face with the most data pins (register mass behind the busiest face)
        cf = max(load, key=load.get)
        pins[cf].insert(len(pins[cf]) // 2, clk[0] if clk else 'ck')
        for c in clk[1:]:
            pins[cf].append(c)
        spec = dict(name=child, top=top, sources=src + [f'physical/asap7_memory_macros/{k}/{k}_bb.v' for k in macros],
                    params=params, clock_port=clk[0] if clk else 'ck', reset_ports=rst, outline=dict(w=round(w, 2), h=round(h, 2)),
                    macros=[dict(view=f'physical/asap7_memory_macros/{k}', count=n) for k, n in macros.items()],
                    pins=pins,
                    structural_change=(f'KVJ-A3 r2 HOST cluster child {child} (core family, one ck_core entry): members '
                                       + ', '.join(m.split('/')[-1] for m in mem) + ('' if direct else
                                       ' + their glue, generated wrapper (tools/qwen_kv_die/host_cluster/gen_cluster.py)')
                                       + '. Partition results/arch/qwen_split_1014/host_root_cluster/partition_r2.json'),
                    kind='tile', recipe=4, hold_budget='die', inhold=False, outhold=False, layer_cap='M5',
                    route=dict(pd=0.5, threads=8, peak_ram_gb=24, pin_h='M4', pin_v='M5', hold_margin_ns=0.03,
                               macro_halo_um=5.4, pin_balance=dict(group_max=1, h='M4', v='M5')),
                    pin_regs=dict(enable=True, reset='^(' + '|'.join(rst) + ')$',
                                  reason='literal async reset roles only (data levels such as native_link_reset_seen are registered)'))
        cg = 'python3 tools/qwen_kv_die/host_cluster/bench/cluster_gate.py'
        mut = f'--inst {inst_of(direct, child)}' if direct else f'--child {child[len("qkd_hr_"):]}'
        spec['job'] = dict(owner='Claude:KV-HOSTCL', branch='claude/kvj-a3-1017', tag='r2',
                           purpose=f'HOST root cluster r2 child {child} (pre-route gate + route; parent qkd_host_root is CRITICAL)',
                           benches=[dict(name='cluster_lockstep', expect='pass', threads=16, peak_ram_gb=24, needs=['verilator'],
                                         cmd=f'{cg} exact --out {{RUN}}/bench/cg_exact',
                                         pass_regex=r'CLUSTER_GATE PASS exact runs_pass=6/6',
                                         min_count_regex=r'CLUSTER_GATE PASS exact runs_pass=6/6 core_cycles=(\d+)'),
                                    dict(name='cluster_child_mutant', expect='fail', threads=16, peak_ram_gb=24, needs=['verilator'],
                                         cmd=f'{cg} mutant --out {{RUN}}/bench/cg_mut {mut}',
                                         fail_regex=r'CLUSTER_GATE FAIL mutant',
                                         fail_witness=f'results/arch/qwen_split_1014/host_root_cluster/benches/cg_mutant_{child}.log')])
        (out / f'{child}.json').write_text(json.dumps(spec, indent=1) + '\n')
        print(child, top, f'{w:.1f}x{h:.1f}', 'bits', bits, 'faces', load, 'macros', macros, 'area~', round(area))


if __name__ == '__main__':
    main()
