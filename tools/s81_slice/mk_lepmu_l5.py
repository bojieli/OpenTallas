#!/usr/bin/env python3
"""S81-LINK5 (10-21) L5B-LEPMU: copy-A/B MU endpoint ot_s81sl_lep_mu_ab (default params = the u_lep instance of
ot_s81sl_slice_lepw_mab_mu_72 @e93685328: SRAM 1, RX_SRAM 0, NB 80) re-floorplanned to 475.2 x 1900.8 for the
561.6 x 1987.2 slot at R0 (820.8, 1728) of lepw_mab_mu: lane pairs A (lo0/lo1, li0/li1) and B (lo2/lo3, li2/li3) on the
W face, each lane's pins in the band facing its u_ln tile (parent lanes at y 1490.4 / 2116.8 / 2743.2 / 3369.6, 583.2
tall -> tile-local overlaps [0,345.6] [388.8,972] [1015.2,1598.4] [1641.6,1900.8]); slice-side ro / ri + mu_c / mu_rt /
sl_f on the E face (slice ri_w / ro_w across the 172.8 corridor); landing ml_* on the N face (dsdv_mu_land at y 3888).
  t5a (MAIN)     : TX SRAM column per lane inside that lane's band (x 129.6, 86.4 pitch) -> lane-local TX / RX logic.
  t5b (FALLBACK) : all 20 TX SRAMs in one central 2x10 block (x 43.2 / 259.2, y 561.6.., 86.4 pitch); ro / ri centred.
Both: full core rows (no regions), one TritonCTS tree with the LEPNH r5b / lepmuh_r6g recipe (24 sinks / 30 um,
15-um buffers, -balance_levels: r6g gate spread TT 61.5 / FF 55.0), io_hold_margin 0.03."""
import json, shutil, subprocess, sys
from pathlib import Path
WT = Path(sys.argv[1]); RT = WT / 'physical/ref_tile'
BASE = json.loads((RT / 's81sl_lepmu/spec.json').read_text())
SRAM = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2'
W, H = 475.2, 1900.8
BANDS = [(20.0, 340.0), (640.0, 960.0), (1020.0, 1340.0), (1650.0, 1880.0)]   # W-face lane bands (tile-local um)


def lane_ranges(k, a, b):
    m = round((a + b) / 2, 1)
    r = {f'lo{k}_d': [a, m - 9], f'lo{k}_v': [m - 9, m - 6], f'lo{k}_r': [m - 6, m - 3], f'l{k}_f': [m - 3, m + 3],
         f'li{k}_v': [m + 3, m + 6], f'li{k}_r': [m + 6, m + 9], f'li{k}_d': [m + 9, b]}
    return {p: [round(x, 1) for x in v] for p, v in r.items()}


def macro(t, k, x, y):
    return {'view': SRAM, 'inst': f'*g_tx?{t}?.g_legacy_write.u_m.g_sram.g_t?{k}?.u_m', 'at': [x, y], 'orient': 'R0'}


COL0 = [43.2, 604.8, 1036.8, 1468.8]   # t5a: lane column bottoms (5 rows x 86.4 -> 375.3 tall each, inside the lane band)
VARIANTS = {
    't5a': dict(
        macros=[macro(t, k, 129.6, round(COL0[t] + 86.4 * k, 1)) for t in range(4) for k in range(5)],
        e={'sl_f': [500.0, 506.0], 'ro': [520.0, 940.0], 'clk': [943.0, 947.0], 'rst_n': [949.0, 953.0],
           'ri': [960.0, 1380.0], 'mu_c': [1385.0, 1405.0], 'mu_rt': [1410.0, 1430.0]},
        why='MAIN: lane-local floorplan -- lane t\'s 5 TX SRAMs (lane bank column x 129.6, 86.4 pitch, 35-um channels '
            'between halos) sit inside lane t\'s W pin band (bottoms y 43.2 / 604.8 / 1036.8 / 1468.8), so TX read -> lo '
            'and li -> RX FIFO stay lane-local; ro [520,940] / ri [960,1380] centred on the E face between the pair-A and '
            'pair-B lanes (hf0 feeds lanes 0+2, hf1 lanes 1+3; ri merges both pairs + ml_rd).'),
    't5b': dict(
        macros=[macro(t, k, 43.2 if t % 2 == 0 else 259.2, round(561.6 + 86.4 * (5 * (t // 2) + k), 1))
                for t in range(4) for k in range(5)],
        e={'sl_f': [580.0, 586.0], 'ro': [600.0, 940.0], 'clk': [943.0, 947.0], 'rst_n': [949.0, 953.0],
           'ri': [960.0, 1300.0], 'mu_c': [1305.0, 1325.0], 'mu_rt': [1330.0, 1350.0]},
        why='FALLBACK: central core -- all 20 TX SRAMs in one 2 x 10 block (cols x 43.2 / 259.2 = lanes 0,2 | 1,3 by '
            'half-word hf0 / hf1; rows y 561.6.. at 86.4 pitch, lanes 0/1 lower, 2/3 upper), ro [600,940] / ri '
            '[960,1300] centred on E: every lane-face hop is a pin-flop -> core register wire, logic stays in one block.'),
}
RXV = 'physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1'


def nmacro(t, k, x, y):
    return {'view': SRAM, 'inst': f'*g_tx?{t}?.g_safe_write.u_m.g_bank?{k}?.u_m', 'at': [x, y], 'orient': 'R0'}


def rmacro(t, k, x, y):
    return {'view': RXV, 'inst': f'*g_rx?{t}?.g_sa.g_true_sram.u_rx_mem.g_bank?{k}?.u_m', 'at': [x, y], 'orient': 'R0'}


NATIVE = {'RX_SRAM': 1, 'IN_PIPE': 1, 'NATIVE32': 1}
KEEP = ['ot_sram_showahead_hit5', 'ot_s81sl_lep_rx_control', 'ot_s81sl_lep_host_event', 'ot_s81sl_lep_tx_push',
        'ot_s81sl_lep_stamp', 'ot_s81sl_lep_vcopy', 'ot_s81sl_lep_pair_ready', 'ot_s81sl_lep_return8',
        'ot_sram_showahead_readptr']
NWHY = (' REGATE after t5a/t5b native census FAIL (default params: max 1,559 loads, 694 drivers > 32; floorplan refused): '
        'kit params RX_SRAM 1 / IN_PIPE 1 / NATIVE32 1 = the Codex-qualified native32 structure of lep_mu_a/_h (6cb5f3eff, '
        'now plumbed through ot_s81sl_lep_mu_ab, defaults 0 unchanged); RX = 5 x 32x128 SRAM per lane. IN_PIPE adds +1 edge '
        'on ro / mu_c: die u_lep params + calendar are a LEAD call before bind.')
VARIANTS['t5c'] = dict(params=NATIVE, keep=KEEP, e=VARIANTS['t5a']['e'],
    macros=[nmacro(t, k, 129.6, round(COL0[t] + 86.4 * k, 1)) for t in range(4) for k in range(5)] +
           [rmacro(t, k, 388.8, round(COL0[t] + 43.2 * k, 1)) for t in range(4) for k in range(5)],
    why='MAIN-native: t5a lane-local TX columns (x 129.6) + per-lane RX SRAM column (x 388.8, 43.2 pitch, toward the E '
        'ri face) in the same lane band.' + NWHY)
VARIANTS['t5d'] = dict(params=NATIVE, keep=KEEP, e=VARIANTS['t5b']['e'],
    macros=[nmacro(t, k, 43.2 if t % 2 == 0 else 259.2, round(345.6 + 86.4 * (5 * (t // 2) + k), 1))
            for t in range(4) for k in range(5)] +
           [rmacro(t, k, round(43.2 + 86.4 * k, 1), round(1209.6 + 43.2 * t, 1)) for t in range(4) for k in range(5)],
    why='FALLBACK-native: central core -- TX 2 x 10 block (x 43.2 / 259.2, y 345.6.., 86.4 pitch) with the RX SRAMs '
        'as 4 lane rows of 5 directly above it (y 1209.6.. 43.2 pitch), ri [960,1300] beside the RX rows.' + NWHY)
ONLY = sys.argv[2:] or list(VARIANTS)
for v, cfg in VARIANTS.items():
    if v not in ONLY: continue
    name = f's81sl_lepmu_{v}'; dst = RT / name
    if dst.exists(): shutil.rmtree(dst)
    dst.mkdir()
    s = json.loads(json.dumps(BASE))
    s['name'] = name
    s['sources'] = ['rtl/lib/ot_rst_relay_tree3.sv', 'rtl/lib/ot_sram_oldread_wreg.sv', 'rtl/lib/ot_sram_showahead_1r1w.sv',
                    'rtl/lib/ot_rst_relay.sv', 'rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv',
                    'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv']
    s['params'] = cfg.get('params', {})
    s['outline'] = {'w': W, 'h': H}
    s['macros'] = cfg['macros']
    wp = []
    for k in range(4):
        wp += [f'lo{k}_v', f'lo{k}_r', f'lo{k}_d', f'li{k}_v', f'li{k}_r', f'li{k}_d', f'l{k}_f']
    s['pins'] = {'W': wp + ['rxv', 'rxvb'], 'S': ['fault'], 'N': ['ml_wv', 'ml_wd', 'ml_rv', 'ml_rd', 'ml_f'],
                 'E': ['ro', 'ri', 'mu_c', 'mu_rt', 'sl_f', 'clk', 'rst_n']}
    rng = {}
    for k, (a, b) in enumerate(BANDS):
        rng.update(lane_ranges(k, a, b))
    rng['rxv'] = [345.0, 351.0]; rng['rxvb'] = [1345.0, 1351.0]
    rng.update(cfg['e'])
    rng['fault'] = [228.0, 234.0]
    s['pin_ranges'] = rng
    s['route'] = dict(BASE['route'])
    s['route'].update(hold_margin_ns=0.045, io_hold_margin_ns=0.03,
                      cts_sink={'size': 24, 'diameter_um': 30, 'extra': '-distance_between_buffers 15 -balance_levels'})
    s['route'].pop('synth_keep_modules', None)
    if cfg.get('keep'): s['route']['synth_keep_modules'] = cfg['keep']
    s['pre_cts_extra'] = []; s['orfs_vars'] = {}
    s['io_flop_at_pins'] = {'cols': 4, 'allow_none': True}
    s['job'] = dict(BASE['job'])
    s['job'].update(owner='Claude:S81-LINK5-L5B-LEPMU', branch='claude/s81-link5-lepmu-1021', tag=name,
                    views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}',
                    purpose='S81-LINK5: copy-A/B MU end-slice link endpoint (u_lep of ot_s81sl_slice_lepw_mab_mu_72, s_0N '
                            '5th lane pair; HOST_EN 0, MU_EN 1, AB_EN 1, NB 80) to closure (TT setup / FF hold / DRC 0).')
    if cfg.get('params'): s['job']['extra_paths'] = s['job']['extra_paths'] + [RXV]
    if cfg.get('params'):   # L5B-LEPBENCH 10-21: kit benches drive lep_mu_ab with the kit params (bench arg n32)
        WD = 'results/rtl/s81_link5_lepmu_1021'
        s['job']['extra_paths'] = s['job']['extra_paths'] + [WD]
        bl = []
        for b in json.loads(json.dumps(BASE['job']['benches'])):
            b['cmd'] += ' n32'
            if 'fail_witness' in b: b['fail_witness'] = WD + '/n32_' + b['fail_witness'].rsplit('/', 1)[1]
            bl.append(b)
        s['job']['benches'] = bl
    s['fill_reason'] = {'pin_bound': (
        'Slot-bound: 475.2 x 1900.8 is the lepw_mab_mu u_lep slot (561.6 x 1987.2 at R0 (820.8,1728)) and its W face must '
        'face four 583.2-tall lane tiles on a 626.4 pitch (pair A + pair B, 4,456 lane pins), N face the landing (2,211 '
        'pins), E face the slice ring (2,277 pins). 20 TX SRAM (103.6k um2); fill is the price of the lane pitch, not a '
        'squeezed util target. RULE FREEZE 10-20: tile fill is guidance, die GRT/STA decide.')}
    s['structural_change'] = (
        'S81-LINK5 L5B-LEPMU 10-21: s81sl_lepmu (475.2x691.2, lanes B on S, never closed) re-floorplanned to the '
        'lepw_mab_mu slot: 475.2 x 1900.8, pairs A+B on W in four lane bands [20,340] [640,960] [1020,1340] [1650,1880] '
        '(each inside its u_ln tile overlap), ro/ri/mu/clk on E, ml on N, fault S. ' + cfg['why'] +
        ' Clock: one TritonCTS tree, r6g recipe (no km16: r5e km16 lep twin 91.9/89.6). Same RTL as the die instance '
        '(e93685328) except the params listed, same ports and SDC.')
    (dst / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
    (dst / 'README.md').write_text(
        f'# {name} (S81-LINK5 L5B-LEPMU 10-21)\n\n{s["structural_change"]}\n\n'
        'SAFE checklist:\n'
        '1 pins: source-registered (ro / li / ml_rd / mu_c land in pin flops; ri / lo / ml_wd / mu_rt / fault leave flops), '
        'reset_landing 2 stages: PASS.\n'
        '2 reach: RISK, measured by the gate -- the slot geometry spreads the 4 lanes over 1,860 um of W face; '
        'cross-lane one-cycle hops (roq -> TX write reg of lanes 0+2 / 1+3, RX head -> ri merge, ml_rd -> ri) are up to '
        '~700-950 um. No relay without an RTL change (+cycles, lead/calendar call); t5b concentrates logic so the long '
        'hops are pure flop->flop wires.\n'
        '3 fanout: native census measured by the gate (default params = die instance; NATIVE32 replicas not exposed by '
        'ot_s81sl_lep_mu_ab).\n'
        '4 depth: unchanged RTL (MU-S81-2/RX rebuild: show-ahead heads, AO222 rid, 0 added cycles).\n'
        '5 storage: TX 20 SRAM macros; RX 8-deep x 553 flop FIFOs per lane (DR 8 = lane credit depth, RX_SRAM 0 is the '
        'die instance param): waived, die binding exactness.\n'
        '6 floorplan: macros on the 43.2 lattice, 86.4 pitch (35-um channels), full core rows, faces <= 4.7/um; aspect '
        '4:1 waived (slot set by the lane pitch).\n'
        '7 clock: one tree, r6g recipe, spread <= 80 TT+FF measured by the gate; io_hold_margin 0.03.\n'
        '8 schedule: 0 added cycles.\n')
    r = subprocess.run(['python3', 'tools/ref_tile/ref_tile.py', 'gen', str(dst / 'spec.json')], cwd=WT,
                       capture_output=True, text=True)
    print(name, r.returncode, r.stdout[-400:], r.stderr[-800:])
