#!/usr/bin/env python3
"""KV-P8-HUB 10-23: hub_Wi host root = ONE hard core qkd_host_rt_obsx (clears hub_Wi G0C, 22 'no pins').

KV owner decision (KV-P7 21:43): the 22 planned MU-0 qkd_hr_* host-cluster cores (post_v37c HOST_CORES) are DROPPED: the
bound MU=1 die (kv41 kv3_hub_Wi_part: u_host = qkd_host_root_admission_obsx #(ENABLE_NATIVE/SERVICE/TOKEN 1, NL 2))
has no netlist for them.  The bound obsx root is sized by ORFS synth (cores/hostrt_synth_v38w.json: SYNTH_HIERARCHICAL,
main RTL at/after 6c696c13a, SRAM macros as port-only black boxes, macros counted per instance) and, being <= ~380k
cells, becomes ONE planned hard core:

    host = qkd_host_rt_obsx (content leaf 'host', module qkd_host_rt)

Outline = std area / FILL (0.55, the astk cores' rule) + the SRAM macro footprints (MACRO_HALO each side), square-ish on
the 8.64-um lattice.  Site: the lattice position (>= BAND = 25.92 um from every type face: face-register band >= 22 um)
that minimises the bit-weighted Manhattan distance from the core box to the face windows of the buses the core talks to
(core_conns from the bound netlist); pins are then assigned top-down (core_pins_v37p machinery, bound hub_Wi netlist:
boundary bits of u_host, face = best facing to its partners, even spread on the plan tracks) for that site, and the
site is re-optimised once with the real pin groups.  Outline, buses, ft_slots, lanes and ports are untouched; only
partition_types.kv3_hub_Wi.hard_cores (+ cores/qkd_host_rt_obsx_pins.json, core_conns.json[kv3_hub_Wi]) are written.
usage: post_v38w.py die_plan.json PLAN_DIR [--gen RTL_DIR] > die_plan.json"""
import json
import math
import re
import sys
from pathlib import Path

G = 8.64
FILL = 0.55
BAND = 3 * G           # 25.92 um >= 22 um face band on every side
MACRO_HALO = 2.16      # per side around each SRAM macro (channel)
TN = 'kv3_hub_Wi'
INST, MOD = 'host', 'qkd_host_rt_obsx'


def lat(v):
    return round(math.ceil(v / G - 1e-9) * G, 6)


def outline(syn):
    area = syn['std_area_um2'] / FILL
    for m in syn.get('macros', {}).values():
        w, h = m['size_um']
        area += m['count'] * (w + 2 * MACRO_HALO) * (h + 2 * MACRO_HALO)
    cw = lat(math.sqrt(area))
    return cw, lat(area / cw)


def tools(pdir):
    sys.path.insert(0, str(Path(pdir).resolve().parents[2] / 'tools/die_plan'))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import check as C
    import schema as S
    return C, S


def box_dist(p, b):
    x0, y0, x1, y1 = b
    return max(x0 - p[0], 0, p[0] - x1) + max(y0 - p[1], 0, p[1] - y1)


def best_site(plan, pdir, cw, ch, conns, widths):
    """lattice origin minimising sum(bits x Manhattan(window, core box)) over the core's bus partners."""
    C, S = tools(pdir)
    P = S.Plan(plan)
    bt = C._bus_targets(P, TN)
    W, H = plan['partition_types'][TN]['outline_um']
    tg = {}
    for port, vs in conns.items():
        for v in vs:
            if v.startswith('bus:') and v[4:] in bt:
                tg[v[4:]] = bt[v[4:]][1]
    best = None
    nx = int((W - 2 * BAND - cw) / G + 1e-9)
    ny = int((H - 2 * BAND - ch) / G + 1e-9)
    for i in range(nx + 1):
        for j in range(ny + 1):
            x, y = round(BAND + i * G, 6), round(BAND + j * G, 6)
            b = (x, y, x + cw, y + ch)
            c = sum(widths.get(n, 1) * box_dist(p, b) for n, p in tg.items())
            if best is None or c < best[0] - 1e-6:
                best = (c, x, y)
    return best, len(tg)


def gen_pins(plan, rtl, pdir):
    """top-down pins for the host core only (core_pins_v37p machinery restricted to kv3_hub_Wi)."""
    C, S = tools(pdir)
    import core_pins_v37p as CP
    sub = json.loads(json.dumps(plan))
    for tn, t in sub['partition_types'].items():
        if tn != TN:
            t.pop('hard_cores', None)
        for hc in t.get('hard_cores', []):
            hc.pop('pins_file', None)
    og = CP.Net.graph

    def graph(self):
        g = og(self)
        return {k: v for k, v in g.items() if not any(CP.CLKRST.match(e[1]) for e in v)}
    CP.Net.graph = graph
    CP.SWAP = {}
    CP.apply_layout = lambda types: {}
    CP.C, CP.S, CP.SP = C, S, S.Plan(sub)
    tmp = Path(pdir) / '_v38w_tmp'
    tmp.mkdir(parents=True, exist_ok=True)
    pj = tmp / 'plan.json'
    pj.write_text(json.dumps(sub))
    argv = sys.argv
    sys.argv = ['core_pins_v37p.py', str(pj), rtl, str(tmp)]
    try:
        CP.main()
    finally:
        sys.argv = argv
        CP.Net.graph = og
    pins = json.loads((tmp / 'cores' / f'{MOD}_pins.json').read_text())
    cc = json.loads((tmp / 'core_conns.json').read_text()).get(TN, {}).get(INST, {})
    patch = json.loads((tmp / 'cores' / 'core_patch_v37p.json').read_text()).get(TN, {}).get(INST, {})
    for f in sorted(tmp.rglob('*'), reverse=True):
        f.unlink() if f.is_file() else f.rmdir()
    tmp.rmdir()
    return pins, cc, patch


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    rtl = sys.argv[sys.argv.index('--gen') + 1] if '--gen' in sys.argv else None
    if rtl:
        a.remove(rtl)
    plan, pdir = json.load(open(a[0])), Path(a[1])
    syn = json.loads((pdir / 'cores' / 'hostrt_synth_v38w.json').read_text())
    t = plan['partition_types'][TN]
    old = [h['inst'] for h in t.get('hard_cores', [])]
    assert all(i.startswith('host__qkd_hr_') for i in old), old
    cw, ch = outline(syn)
    widths = {b['name']: b['width'] for b in t['buses']}
    W, H = t['outline_um']
    hc = dict(inst=INST, module=MOD, origin_um=[round(lat((W - cw) / 2), 6), round(lat((H - ch) / 2), 6)],
              outline_um=[cw, ch], orient='R0', track_offset_um=[0.0, 0.0], pins_file=f'cores/{MOD}_pins.json')
    t['hard_cores'] = [hc]
    site_f = pdir / 'cores' / 'hostrt_site_v38w.json'
    if rtl:
        _, cc, _ = gen_pins(plan, rtl, pdir)             # pass 1: partners of the core's boundary bits
        (c1, x, y), n = best_site(plan, pdir, cw, ch, cc, widths)
        hc['origin_um'] = [x, y]
        pins, cc, patch = gen_pins(plan, rtl, pdir)      # pass 2: pins for the chosen site
        (c2, x2, y2), _ = best_site(plan, pdir, cw, ch, cc, widths)
        if (x2, y2) != (x, y):
            hc['origin_um'] = [x2, y2]
            pins, cc, patch = gen_pins(plan, rtl, pdir)
        (pdir / 'cores' / f'{MOD}_pins.json').write_text(json.dumps(pins, indent=0))
        ccall = json.loads((pdir / 'core_conns.json').read_text())
        ccall[TN] = {INST: cc}
        (pdir / 'core_conns.json').write_text(json.dumps(ccall, separators=(',', ':'), sort_keys=True))
        site_f.write_text(json.dumps(dict(origin_um=hc['origin_um'], orient=patch.get('orient', 'R0'), cost_bit_um=c2,
                                          partner_buses=n), indent=1))
    site = json.loads(site_f.read_text())
    hc['origin_um'], hc['orient'] = site['origin_um'], site.get('orient', 'R0')
    hc['note'] = (f"host_core: u_host = qkd_host_root_admission_obsx #(ENABLE_NATIVE/SERVICE/TOKEN 1, NL 2) (bound MU=1 "
                  f"hub_Wi); PLANNED core (KV-P8-HUB v3.8w): {syn['cells']} cells / {syn['std_area_um2']:.0f} um2 std "
                  f"(cores/hostrt_synth_v38w.json) at fill {FILL} + {sum(m['count'] for m in syn.get('macros', {}).values())}"
                  f" SRAM macros; face band {BAND:.2f}; site = min bit-weighted distance to its {site['partner_buses']} "
                  f"partner windows; lef/lib pending (CORE-KS harden)")
    plan['note'] = plan.get('note', '') + (' | v3.8w (KV-P8-HUB 10-23): hub_Wi 22 MU-0 qkd_hr_* cores dropped (KV owner '
                                           '21:43) -> ONE hard core qkd_host_rt_obsx (post_v38w.py)')
    sys.stderr.write(f'post_v38w: host core {cw} x {ch} at {hc["origin_um"]} ({len(old)} planned cores removed)\n')
    json.dump(plan, sys.stdout, indent=1)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
