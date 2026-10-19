#!/usr/bin/env python3
"""KVJ-A3 (10-17, coordinator decision 0dd): partition plan of the Qwen KV-die HOST root qkd_host_root_admission into a
cluster of clock-family children (core / host / ingest / phy) + CDC leaves at the family seams.

Inputs: the census roll-up (hier_rollup.py: per-instance std cells / area / flops / macros / clocks, from the
hierarchical mapped synth RVT TT and the proc elaboration).  Output: partition_plan.json (children, member instances,
sizes, outline estimates, CDC ownership).  Sizes are HIERARCHICAL synth (no cross-child optimisation; the flat synth of
the same root is 0.75x area / 0.74x flops) -> outlines are conservative.

usage: partition_plan.py census_rollup.json out.json
"""
import json
import math
import sys
from pathlib import Path

LAT = 43.2           # hard-child origin lattice (ref_tile CHILD_LATTICE_UM)
UTIL = 0.55          # std-cell util target (parent-first 50-60 %)
HALO = 5.4           # recipe >= 2 macro halo
FLAT = 0.75          # flat / hierarchical area ratio measured on this root (76,530 / 102,134 um2)
MACRO = {'ot_sram_1r1w_512x128_m4_r2c2': (174.096, 29.700), 'ot_sram_1r1w_1024x256_m2_r2c2': (174.744, 70.470),
         'ot_sram_1rw_256x64_m4_r2c2': (66.312, 17.820), 'ot_sram_1r1w_32x128_m1': (51.408, 20.790)}
FRAME = (777.6, 518.4)
R = 'top/u_rank/'
# child -> (family, member instance paths, note).  'glue:' members are RTL re-cut items (no instance yet).
CHILDREN = {
    'qkd_hr_phy_adp': ('phy', [R + 'u_adapter/g_slice[0].u_slice'], 'qfd_link_adp128 hardened ONCE, stepped x8 (one per ck_phy[i] lane); 1 SRAM each'),
    'qkd_hr_phy_pad': ('phy', [R + 'u_phy/u_pad'], 'qkd_host_rx_pad5 (ck_pad); FDI 1024-b data in -> 546-b W546 word out'),
    'qkd_hr_core_prompt': ('core', [R + 'u_control/u_control', R + 'u_program', R + 'u_program_rx', 'top/u_records'],
                           'prompt/CSR/ctl/rst services (1 SRAM 1024x256) + program loader (4 SRAM 256x64) + program rx + record port'),
    'qkd_hr_core_rx': ('core', [R + 'u_control/u_packet/u_rx'], 'qkd_host_rx_class_admission (rx packet class)'),
    'qkd_hr_core_tx': ('core', [R + 'u_control/u_packet/u_tx', R + 'u_control/u_packet/u_axi', R + 'u_control/u_packet/u_ctrl'],
                       'tx class + AXI packet + ctrl/token service packet'),
    'qkd_hr_core_guard': ('core', [R + 'u_guard', R + 'u_native'], 'service guard (markers FIFO) + native token endpoint'),
    'qkd_hr_core_queue': ('core', [R + 'u_bridge/u_queue', R + 'u_marker_consumer', R + 'u_bootbarrier', 'glue:qm_core', 'glue:fence_core'],
                          'qm ingress16 service + boot barrier/marker + core side of native_qm and visibility_fence'),
    'qkd_hr_core_order': ('core', [R + 'u_chain', R + 'u_dispatch'], 'ingest chain (map/sum/order) + boot dispatch/retire order'),
    'qkd_hr_core_peer': ('core', [R + 'u_peer', 'top/u_peer_codec', 'top/u_root_mux', 'top/u_coordinator'],
                         'board peer link + rank codec + root mux + TP8 coordinator: ONE clock group (direct valid/ready '
                         'interfaces, no synchroniser: root_mux<->coordinator 2x8x512 b, peer_link->program_rx, '
                         'coordinator<->rank token request/grant) -> ck_peer/ck_root_mux/ck_coordinator_* = core (HOST_CLK_INFERRED '
                         'says host for ck_peer/ck_root_mux: inconsistent, owner to confirm)'),
    'qkd_hr_host_qm': ('host', [R + 'u_bridge/u_pacer', 'glue:qm_host', 'glue:fence_host'],
                       'the whole host family: native_qm host face (between the bridge CDC and the hx/cx CDC) + credit pacer + fence host side'),
    'qkd_hr_ingest_eng': ('ingest', [R + 'u_qm/u_eng', 'glue:qm_ingest'], 'native ingest engine (32 SRAM 32x128) + ingest side of native_qm'),
    'qkd_hr_cdc_pc': ('cdc:phy|core', [R + 'u_phy/u_rx', R + 'u_phy/u_tx'], 'two W546 PIPE2 die CDC channels: PHY rx (phy->core), tx (core->phy)'),
    'qkd_hr_cdc_ch': ('cdc:core|host', [R + 'u_bridge/u_ing', R + 'u_bridge/u_done', 'glue:fence_sync'],
                      'qm ingress (core->host) + done (host->core) W546 CDC channels + visibility-fence synchronisers'),
    'qkd_hr_cdc_hi': ('cdc:host|ingest', [R + 'u_qm/u_hx', R + 'u_qm/u_cx'], 'native_qm host stream (host->ingest, W514) + completion (ingest->host, W64)'),
    'qkd_hr_cdc_ci': ('cdc:core|ingest', [R + 'u_qm/u_ox', R + 'u_qm/u_rx'], 'native_qm HBM write face out (ingest->core) + read return (core->ingest)'),
}
GLUE = {  # estimated std cells / flops of the re-cut glue (own logic of the mixed parents, split by its flop domains)
    'glue:qm_core': (1700, 590), 'glue:qm_host': (1750, 600), 'glue:qm_ingest': (1050, 350),
    'glue:fence_core': (300, 80), 'glue:fence_host': (2400, 700), 'glue:fence_sync': (150, 0)}
# outlines set by the macro lattice (20-um macro channels, 43.2 lattice), not by std area:
#  adp: the 174.1-um SRAM sets the width (216 = 5 x 43.2); 64.8 tall = macro + std band + pin margin (3.3:1, forced)
#  ingest: 32 x 51.4x20.8 SRAMs, 4 columns x 8 rows at 86.4 x 43.2 pitch = 345.6 x 345.6 + a 43.2-um std band
OVERRIDE = {'qkd_hr_phy_adp': (216.0, 64.8), 'qkd_hr_ingest_eng': (388.8, 345.6),
            # pin-limited (upper-bound pin bits / full perimeter <= ~6-7 /um)
            'qkd_hr_core_peer': (216.0, 172.8), 'qkd_hr_core_tx': (172.8, 129.6), 'qkd_hr_phy_pad': (86.4, 86.4)}
AREA_PER_CELL = 102134.0 / 784320   # um2 per std cell, this root, hierarchical


def outline(std_um2, macros):
    mac = sum(n * (MACRO[v][0] + 2 * HALO) * (MACRO[v][1] + 2 * HALO) for v, n in macros.items())
    core = std_um2 / UTIL + mac
    wmin = max([MACRO[v][0] + 2 * 20 for v in macros] or [0])
    side = max(math.sqrt(core), wmin)
    w = math.ceil(side / LAT) * LAT
    h = max(LAT, math.ceil(core / w / LAT) * LAT)
    return round(w, 1), round(h, 1), round(core)


def main():
    roll = {n['path']: n for n in json.loads(Path(sys.argv[1]).read_text())['nodes']}
    out, tot = {}, dict(cells=0, area=0, ff=0)
    for name, (fam, members, note) in CHILDREN.items():
        c = a = f = 0
        mac, clocks = {}, {}
        for m in members:
            if m.startswith('glue:'):
                gc, gf = GLUE[m]
                c += gc
                a += gc * AREA_PER_CELL
                f += gf
                continue
            n = roll[m]
            c += n['std_cells']
            a += n['std_area_um2']
            f += n['ff_mapped']
            for k, v in (n['macros'] or {}).items():
                mac[k] = mac.get(k, 0) + v
            for k, v in n['clocks'].items():
                clocks[k] = clocks.get(k, 0) + v
        reps = 8 if name == 'qkd_hr_phy_adp' else 1
        w, h, core = outline(a, mac)
        if name in OVERRIDE:
            w, h = OVERRIDE[name]
        out[name] = dict(family=fam, members=members, note=note, instances=reps, std_cells_hier=c,
                         std_cells_flat_est=round(c * FLAT), std_area_um2_hier=round(a), flops_hier=f,
                         flops_flat_est=round(f * 0.74), macros=mac, elab_clock_ports=clocks,
                         clock_roots=(2 if fam.startswith('cdc') else 1), outline_est=dict(w=w, h=h),
                         core_need_um2=core, aspect=round(max(w, h) / min(w, h), 2))
        tot['cells'] += reps * c
        tot['area'] += reps * w * h
        tot['ff'] += reps * f
    plan = dict(schema='opentallas.qwen-host-root-cluster-plan.v1', root='qkd_host_root_admission',
                frame_um=FRAME, frame_area_um2=round(FRAME[0] * FRAME[1]), util=UTIL, lattice_um=LAT,
                children=out, totals=dict(std_cells_hier=tot['cells'], flops_hier=tot['ff'],
                                          child_outline_area_um2=round(tot['area']),
                                          child_area_over_frame=round(tot['area'] / (FRAME[0] * FRAME[1]), 3)))
    Path(sys.argv[2]).write_text(json.dumps(plan, indent=1) + '\n')
    for k, v in out.items():
        print(f"{k:20s} {v['family']:16s} x{v['instances']} cells {v['std_cells_hier']:7d} (flat~{v['std_cells_flat_est']:6d}) "
              f"ff {v['flops_hier']:6d} mac {sum(v['macros'].values()):2d} outline {v['outline_est']['w']}x{v['outline_est']['h']} ar {v['aspect']}")
    print(plan['totals'])


if __name__ == '__main__':
    main()


def pin_counts(elab, plan_path):
    """Upper-bound pin bits per child from the proc elaboration: every port bit of a member instance whose parent net
    also reaches something outside the child's members (glue cells count as outside).  Clock ports listed apart."""
    mods = json.loads(Path(elab).read_text())['modules']
    plan = json.loads(Path(plan_path).read_text())
    top = plan['root']
    types = {'top': top}

    def cell_of(path):
        par, _, inst = path.rpartition('/')
        if par not in types:
            cell_of(par)
        c = mods[types[par]]['cells'][inst]
        types[path] = c['type']
        return par, c

    for name, ch in plan['children'].items():
        members = [m for m in ch['members'] if not m.startswith('glue:')]
        inside = set(members)
        bits_in = bits_out = 0
        clocks = set()
        for m in members:
            par, c = cell_of(m)
            pm = mods[types[par]]
            users = {}
            for cn, cc in pm['cells'].items():
                for pn, bb in cc['connections'].items():
                    for b in bb:
                        users.setdefault(b, set()).add(f'{par}/{cn}')
            ports = set(b for p in pm['ports'].values() for b in p['bits'])
            cm = mods[c['type']]['ports']
            for pn, bb in c['connections'].items():
                d = cm[pn]['direction']
                if pn.startswith(('ck', 'clk')) or pn in ('wclk', 'rclk', 'cq', 'qw', 'qr', 'qp', 'ccw', 'ccr'):
                    clocks.add(pn)
                    continue
                for b in bb:
                    if isinstance(b, str):
                        continue
                    ext = (b in ports) or any(u not in inside for u in users.get(b, ()) if u != m)
                    if ext:
                        if d == 'input':
                            bits_in += 1
                        else:
                            bits_out += 1
        ch['pin_bits_upper'] = dict(data_in=bits_in, data_out=bits_out, clock_ports_elab=sorted(clocks))
        per = 2 * (ch['outline_est']['w'] + ch['outline_est']['h'])
        ch['pin_bits_upper']['per_um_full_perimeter'] = round((bits_in + bits_out) * ch['instances'] / ch['instances'] / per, 2)
    Path(plan_path).write_text(json.dumps(plan, indent=1) + '\n')
    for k, v in plan['children'].items():
        print(k, v['pin_bits_upper'])


if __name__ == '__main__' and len(sys.argv) > 3 and sys.argv[3] == '--pins':
    pass
