#!/usr/bin/env python3
"""hbmdie-1011: top-down hierarchy contract for the HBM accelerator R25GQ die (variant r25gqn).

Builds the die model with tools/hbm_accel_die_fp.py and writes results/arch/hier_contract_1011/r25gq.json: per slot
(every die master that is not a relay / clock / reset waypoint) outline, instances (position / orient), pins grouped per
port (face, layer, centre along the face, bits), clock entry, PG / layer contract, I/O budget, hierarchy decision
(hardened cluster replicated >= 4x vs two-level tiles + hub placed by the die) and the element handoff (tiles, hub,
seams).  Also: die-level relay status (segments over the 504 um reach with no PHYSICAL relay), the seam-check
definition and pass criteria, and the per-region die-top implementation plan.
Provisional schema 'hier-contract/0'; migrate to tools/hier_contract/ when it lands.

  python3 tools/hbm_accel_die_hier_contract.py [--out results/arch/hier_contract_1011/r25gq.json] [--version N --note ...]
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
PERIOD_PS = 833.333
WAYPOINT = re.compile(r'^hfd_(stn|ckb|rrl|meso|att_su_relay|rly)')
PINNED = ROOT / 'physical/hbm_accel_die_views/ports_r25gqn'

LAYER_CONTRACT = dict(
    rule='M8 / M9 belong to the die top only.  A hard child carries full-length VDD/VSS stripes on its TOP layer as PG '
         'pins; its parent straps exactly one layer above; a child never routes signals on its parent\'s strap layer.',
    die_blocks_and_clusters='signals M1-M7 around own M7 VDD/VSS stripes (PG pins M7); die straps M8 (die grid M8/M9)',
    cluster_tiles='tiles inside a hardened cluster: signals <= M6 around own M6 PG stripes; cluster straps M7 = cluster PG pins',
    two_level_tiles='tiles the die places directly: EITHER PG M7 stripes (signals <= M7, die straps M8) OR PG M6 stripes '
                    '(signals <= M6, die straps M7 locally over that tile region, die M8/M9 above); recorded per slot',
    abstracts='exact-shape LEF (never -bloat_occupied_layers) + TT/FF/SS libs from the shared exporter; '
              'tools/hier_contract/child_lint.py PASS before any parent / die region using it is submitted',
)
IO_DEFAULT = dict(input_delay_T=0.2, output_delay_T=0.2, period_ps=PERIOD_PS,
                  boundary='registered: pin flop on every input, flop on every output (no logic before / after)')

# Per-slot hierarchy decision (owner TWO-LEVEL rule 21:00 + AMENDMENT 21:30: clusters instantiated >= 4x keep ONE
# hardened level, harden once / replicate; unique parents are two-level, tiles + hub placed by the die).
HIER = {
    'hfd_hc': dict(decision='two_level_die_region_array', count_rule='4 quarters (R0/MY/MX/R180), 4 identical die regions',
                   owner='conservative-1011/B (tile) / hbmdie-1011 (region)',
                   tiles='88 x hfd_hc_tile_xl (135.648 x 156.33, CLOSED TT +10.37 / FF +4.70 / DRC 0, 5c35b1a6e) per quarter '
                         'in the 8 x 11 serpentine grid (pitch 179.136 x 187.38, physical/hbm_accel_die_views/hcp/rtl_qt/'
                         'macro_place.tcl @87e02e7ad re-fit to the slot); GLUE RULE: no hfd_hc_hub -- chain-head glue '
                         '(band capture, 3 head relays each way, XOR fold slice, rst sync) into head tiles / die-region relays',
                   slot_change='v6: region 2,263.68 x 1,499.04 = the CLOSED tiled quarter (r25gqw ports; the die adapts '
                               'to the closed element): SU-facing edge fixed, grows away from the spine into the HC | '
                               'attention channel (345.6 -> 114.96 um); supersedes the v1 2,032.944 x 1,684.8 taller slot',
                   layers='v1.1: tiles placed by the die (closed tile as-is: PG M7 stripes, signals <= M7), die region straps '
                          'M8 (die-only layer, legal at the die top). No quarter cluster / no M8-PG quarter (pdn_qt '
                          'quarter routes finish as evidence only).',
                   seams='DIE closure, in the HC region route: half-cycle negedge chain seams abutted (<= 45 um), head '
                         'relays 3 posedge stages each way on the head-tile clock (first hq stage <= 50 um from the head), '
                         'clock entry = tile clk (M4 W), insertion max 267 / min 233 ps SS (FF 141/134)'),
    'hfd_su': dict(decision='hardened_cluster', count_rule='4 quarters', owner='el1011-hbm-sfu / hcvm',
                   tiles='SU lane tiles + ONE su_ctlw tile (sfu 19:00: 4 slices stacked N-S in one hard tile, sl_i strap '
                         '0..3, descriptors/go forward 1 cycle a hop, done/ovf backward 2 cycles a hop, go blanking BL 15, '
                         'control = -DOT_CTLW_HEAD_EXT; jobs hgi_suctlw_slice{,m}-c23c819c3-tc-cl; no hub) inside the '
                         'quarter cluster; lane ports wrq/wrr/wwq/lsw/ldc/ldr straight to VM bank b'),
    'hfd_sfu': dict(decision='two_level', count_rule='4 quarters', owner='el1011-hbm-sfu',
                    tiles='v1.1 (sfu 19:00 GLUE handoff): lanes = hardened lane CLUSTERS ot_su12_sfu SFUT=2 '
                          '-DOT_SFU_CHAIN_HARD (lane + hard chain macro inside 159.84 x 330.48, W-face pins, PG M6 -> die '
                          'straps M7 locally; chain PG M5 under lane M6 straps); ctlw = ONE hard tile (4 slices stacked '
                          'N-S, edge-registered links, control as -DOT_CTLW_HEAD_EXT), no hub; face/broadcast glue = die '
                          'relays; composition physical/hbm_accel_die_views/sfu/rtl_tiled_r25gq',
                    params='SFUT: die vec controller (ot_hdc_v41x_vec from vec_c12 inside ot_su13_ctl64) = routed lanes: '
                           'DENR=1 now; SFUT=2 when the lane cluster closes (controller formula 2*SFUT = +4 cycles exp/sigmoid/SiLU; bench hbm_su_c12.py --sfut 2)'),
    'hfd_sm': dict(decision='hardened_cluster', count_rule='32 SMs', owner='el1011-hbm-smh',
                   tiles='per SM: tile_eg / tile_wg each = pt_w + pt_e + 2 leaves (xs, bdc, 2 tcl, tct); the G1 select (gsel) goes INTO the '
                         'leaf tile (no gsel hub), gather relays = die/cluster relays; sm_pub 8:1 arbitration -> per-slice '
                         'credit slices in the 8 pub slices (glue rule item 1) unless one-cycle coupled (then cluster); '
                         'harden tile_eg / tile_wg ONCE (replicated 16x a die-column set) as the one intermediate level',
                   layers='SM sub-tiles PG M6 / signals <= M6; cluster (tile_eg/wg) straps M7 = its PG pins; die M8',
                   io='sub-tile seams 0.36 T a side (routed with ~300 ps IO + calibrated neighbour insertion)'),
    'hfd_attn_half_lo': dict(decision='hardened_cluster', count_rule='32 halves', owner='el1011-hbm-attn',
                             slot_change='v10 slot 1,778.52 x 1,263.6 (c07156bbc), unchanged'),
    'hfd_attn_half_hi': dict(decision='hardened_cluster', count_rule='32 halves', owner='el1011-hbm-attn',
                             slot_change='v10 slot 1,778.52 x 689.04 (c07156bbc), unchanged'),
    'hfd_idx_score_native_grid': dict(decision='two_level', count_rule='4 grids', owner='el1011-hbm-idx',
                                      v3='idx 22:05 GLUE update: chunk_el = 32 abutted hslices, no glue -> NO chunk cluster; '
                                         'the die places the 32 r2 hslices directly in each grid slot on the chunk_h '
                                         'lattice (column pitch 216, row pitch 138.24; seams abut ~28 um, FPL+2 a hop); '
                                         'grid face stages (ik/q/s) = die-region relays',
                                      tiles='ot_hdc_v41x_idx_chunk_el = 32 x ot_hdc_v41x_idx_hslice (180 x 110), 4 '
                                            'systolic columns x 8, wires only: harden the chunk ONCE (cluster, M7 '
                                            'straps over hslice r2 M6 PG) and replicate; r1 hslice views (M7 signals) '
                                            'are not usable'),
    'hfd_coll': dict(decision='hardened_cluster_unique', count_rule='1', owner='el1011-hbm-coll',
                     tiles='ONE hardened hierarchical cluster (GLUE rule item 2: the coll core = ep/amerge/record/decode/rgx + ~40 '
                           'SRAMs is substantial, one-cycle coupled): 9 x ot_hcoll_port (g5a/b/c ~404x386, PG M6, cluster '
                           'straps M7) + the core beside them with registered seams, in the 1,399.656 x 1,561.68 slot; no '
                           'standalone hub',
                     seams='link face -> llk die pins <= 500 um/stage (p2/p3 ~800 um -> 2 relays); core face -> hub '
                           '<= ~150 um, 1 stage; tile placement reference coll_r25gq_h (W MY p0/p5/p7, E R0 p1/p4/p8, '
                           'middle p3/p2 R0, p6 MY at y 10/416/822 in the 1,399.656 x 1,561.68 slot); COLL.TOPK_MERGE = '
                           '16 x ot_hgi_coll_tkm_tile (240x240, N/S chained, M2-M6) + hub TBD'),
    'hfd_hgi_idx': dict(decision='two_level', count_rule='1', owner='el1011-hbm-idx',
                        v3='hgi_idx_topk_w8 = ONE hardened cluster (idx 22:05): w8 hub logic (1250 x 440/520, W in / E out, '
                           't0..t3 S, t4..t7 N) + 8 heap tiles abutted 4 N / 4 S, seams <= 410 um; heap tile PG M5 must be '
                           're-exported PG M6 (cluster straps M7); slot grows to hold it (rf2 re-floorplan, >= 1,270 x 1,100 '
                           'for w8); IXW=1 request (idx as a 32-lane VM WIDE station on lgE, +1 reg each way) = D10; '
                           'TOPK_MERGE = 16 abutted tkm tiles, chain glue inside the tiles (no hub)',
                        tiles='hgi_idx_topk_w8 = 8 x ot_hgi_topk_heap_tile (260x260, CLOSED f87bdf90d; PG M5 -> hub/die '
                              'straps M6 -- NOT contract-conformant: re-export PG M6 or M7 stripes) + '
                              'the w8 merge logic (front f1/fc distribution, pipelined 2-way merge tree, 8 reverse-buffer SRAMs = '
                              'substantial) -> topk_w8 is ONE hardened cluster (heap tiles abut N/S 4+4, seams <= 410 um), '
                              'not tiles + hub; the submitted w8hub routes may finish but get no iterations; '
                              'idx chunk / TOPK_MERGE likewise: TOPK_MERGE = 16 tkm tiles + its pass sequencer/SRAM as one cluster'),
    'hfd_lk_ep': dict(decision='hardened_cluster', count_rule='9 (5 S + 4 N)', owner='el1011-hbm-coll',
                      tiles='3 x ot_lkep_sub (864 x 643.2, retry macro + TX bank + pin queues + relays, seam pins bottom) '
                            'side by side + glue strip (~25k flops: admission, CRC, gearbox, merge) below; die pins f_lk '
                            '(1,120) + phy (974) on the glue strip long face',
                      slot_change='v3 GRANTED 2,600 x 830 (was 1,728 x 1,015.2): S row x 7,570 / 10,254 / 12,938 / 15,622 / '
                                  '18,306 at y 6,016 (84 um channels, sm7..sm14 gap); N row x 9,984 / 12,668 / 15,352 / '
                                  '18,036, top edge 19,749 (MX); ep <-> lk link relays grow with the wider row',
                      layers='EXCEPTION (main): pg_layer M8 / die strap M9 over the slot'),
    'hfd_vm_sw': dict(decision='two_level', count_rule='1 (distinct master per quarter)', owner='hbm-vm8',
                      tiles='halves hfd_vm_<q>_<h> = 6 tiles t<k> each, abutted in the half slot, no hub; clock entry '
                            'M7 area pin ckt<k> per tile (+ face taps), die balances ckt<k> + taps to one REF'),
    'hfd_vm_se': dict(decision='two_level', count_rule='1', owner='hbm-vm8', tiles='as hfd_vm_sw'),
    'hfd_vm_nw': dict(decision='two_level', count_rule='1', owner='hbm-vm8', tiles='as hfd_vm_sw'),
    'hfd_vm_ne': dict(decision='two_level', count_rule='1', owner='hbm-vm8', tiles='as hfd_vm_sw'),
}
# main 10-11 layer exception: a cluster whose tiles contain a hard macro with M6 power puts tile PG on M7 and its own
# straps on M8 (pg_layer M8); the die connects on M9 over that slot (strap_layer M9).  Per slot:
LAYER_EXC = {'hfd_lk_ep': dict(pg_layer='M8', strap_layer='M9', signal_max_layer='M7',
                               why='3 x ot_lkep_sub tiles hold the retry macro (M6 PG) -> tile PG M7, cluster straps M8')}
# elements handed off with no R25GQ die master today (recorded, not placed)
UNPLACED = {
    'ot_hbm_native_frame_station_rb_NO2/NO3/NO3_SAFE (hbm-no3)': dict(
        status='handoff f5799aff4 (claude/el1011-hbm-no3-ph25): each station = ONE hardened cluster (4 x slice8 + 1 x '
               'slice5 in a row + control strip; NO3_split 630 x 196 variant a, first CLOSED route sets it; S face '
               'clk_sm/in_*/release_*, N face out_*/ACK_*/fclk_o). RECORDED, NOT PLACED: no r25gq die master '
               'instantiates the W2 native frame station. LAYER NON-CONFORMANT: cluster straps M8 over slice M7 '
               'stripes (pdn_hier_m8.tcl) -- M8 is die-only; a cluster must top out at M7 (slices PG M6 / signals <= '
               'M6, cluster M7 straps = its PG pins), or the station becomes a die region of its tiles with the '
               'control strip as its own hard tile.',
        ask='hbm-no3 / hgi-1010: which r25gq block hosts the W2 rb stations; hbm-no3: M7-top cluster PDN'),
    'ot_hbm_norm_engine_view (conservative-1011/F)': dict(
        status='8 x ot_hbm_norm_gtile8 (440x440, PG M7 stripes); the split-core glue is relay stages only (XI/YO 4, '
               'BD 4, RBD 3, OD 3, RR 3) -> GLUE rule: into the gtiles (edge stages) + die-top relays, no norm hub; '
               'no r25gq die master names the norm engine today',
        ask='conservative-1011: which r25gq slot carries it (SU quarter cluster -> then it is inside the hfd_su cluster)'),
}

# v3 (hbmdie-1011, 10-11 relaunch 3): die-placed TILE sub-slots (two-level elements) in the parent slot's frame, the
# NO3 decision, the VM tunit latency contract and the per-region die-top route plan.
TILE_SRC = ROOT / 'results/arch/hier_contract_1011/handoff/r25gq_die_tiles_src.json'
VM8_HALF_X = {'w': 0.0, 'e': 349.056}       # hfd_vm_<q> slot 699.816 = w half 349.056 + e half 350.76 (vm8 9adc3c44e)
SFU_LANE_XY = [(683.856, 55.62), (683.856, 388.8), (683.856, 721.98), (350.784, 721.98), (350.784, 388.8),
               (350.784, 55.62), (17.712, 55.62), (17.712, 388.8), (1016.928, 55.62), (1016.928, 388.8),
               (1016.928, 721.98), (1350.0, 721.98), (1350.0, 388.8), (1350.0, 55.62), (1683.072, 55.62),
               (1683.072, 388.8)]   # tools/hbm_hub_quarter_gen.py --quarter sfu lattice (claude/el1011-hbm-sfu); lanes keep
# their lower-left, the narrower lane cluster (159.84 vs 315.36) leaves 173-um channels for the face/broadcast relay stages
IDX_HSLICE = dict(w=180.0, h=110.0, pitch=(25 * 8.64, 16 * 8.64), off=(4 * 8.64, 8 * 8.64))  # physical/hgi_idx_chunk_h/place.tcl
TILE_STATUS = {   # child_lint (main) on the latest view, hbmdie-1011/lint 10-11 ~21:25 (/home/ubuntu/scratch-hbmdie/lint/summary.json)
    'hfd_hc_tile_xl': 'CLOSED 5c35b1a6e TT +10.37 / FF +4.70 / DRC 0; child_lint FAIL (f) 449/837 edge pins (acc M4 W) -> '
                      'conservative-1011 pka05 above-only pin-access re-route RUNNING',
    'hfd_vm8_tile': 'routes hbm_vm8st2/3_* running (36); no closed view',
    'ot_su12_sfu_lane_cluster': 'chain-hard lane cluster routing (el1011-hbm-sfu); ring3 view aa5dd28d5 child_lint FAIL (c) 4769 '
                                'M7 OBS, (f) 1186',
    'ot_hdc_v41x_idx_hslice': 'r2 121c75340 (signals <= M6, PG M6) in hold ECO (FF -1.6); r1 a791d4196 FAILS (c) M7 signals',
}
NO3_DECISION = dict(
    decision='NOT A R25GQ DIE ELEMENT (die lead, v3)',
    why='ot_hbm_native_frame_station_rb is the station of ot_hbm_native_quarter_chain_rb (physical/hbm_die_abstracts_20261006/'
        'links/native_quarter): the native-frame PUBLICATION quarter chain with SM taps, fanouts 3/3/3/2 (11 SMs a quarter, '
        'two SMs a column).  The only die variant with that W2 sender is R24W (spine slot w2_sender); R25GQ has 8 SMs a '
        'quarter and feeds them through the HGI VM lane stations (hfd_stn_* relays) and sm_pub, so no r25gq master '
        'instantiates it.  The cluster definition (handoff f5799aff4: one station = 4 x slice8 + 1 x slice5 + control '
        'strip, hub-to-slice <= 450 um inside, NO3_split 630 x 196 / NO3 850 x 178) is RECORDED as conformant for a die '
        'that carries the W2 chain (R24W / DS ROM re-index), not placed here.',
    layer='if placed: cluster tops at M7 (slices PG M6, cluster straps M7) -- pdn_hier_m8.tcl (M8 straps) breaks M8-die-only',
    ask='hbm-no3 / hgi-1010: object within one version if R25GQ needs a W2 publication path (then: one station cluster '
        'per SM column, slot in the SM column channel, contract v4)')
VM_TUNIT = dict(
    switch='physical/hbm_accel_die_views/hgi_vm5/rtl/spec.json instances[vmd].params TUNIT (default 0; e2e --g VM_TUNIT=1)',
    sources='rtl/hbm_accel/generic/vm/ot_hgi_vm_tunit.sv + ot_hgi_vm_btile.sv (hard bank tile) in every hgi_vm source list',
    die_config='NC 9, WP 32, WDIRECT 1, RP 96, W2 96, LQ 32, AP 1 (builds on main 20730548c; lockstep PASS seeds 11/23)',
    latency_cycles=dict(request_to_response=12, lane_read_rq_to_rr=8, rq_to_credit=6, w2q_to_credit=6, w2q_to_done=8,
                        wq_to_wq_done=8, aperture_ap_cr_to_ap_q=2, reset_release=3),
    client_rule='every lane client LQ >= its new credit round trip (LQ 32 ample)',
    flip='TUNIT=1 when hgi_vm_bt{a,b} + the 32-tile VM parent close (el1011-hbm-hcvm); until then 0')


def tile_slots(slots):
    """Die-placed tile sub-slots (TWO-LEVEL): {parent cell: [tile dicts in the parent frame]}."""
    src = json.loads(TILE_SRC.read_text()) if TILE_SRC.exists() else {}
    out = {}
    if 'hfd_hc' in src and 'hfd_hc' in slots:
        h = src['hfd_hc']
        out['hfd_hc'] = [dict(name=t['name'], cell=h['cell'], w=h['w'], h=h['h'], x=t['x'], y=t['y'], orient=t['orient'],
                              pg='M7', strap='M8', sig='M7', ck=dict(pin='clk', face='W', layer='M4'),
                              status=TILE_STATUS['hfd_hc_tile_xl']) for t in h['tiles']]
    for cell, tl in (src.get('vm8', {}).get('tiles') or {}).items():
        if cell in slots:
            out[cell] = [dict(name=t['name'], cell=t['name'], w=t['w'], h=t['h'],
                              x=round(VM8_HALF_X[t['half'].split('_')[-1]] + t['x'], 3), y=t['y'], orient='R0',
                              pg='M7', strap='M8', sig=f"M{t['obs_top']}", ck=dict(pin=f"ckt{t['name'][-1]}", face='N', layer='M7'),
                              status=TILE_STATUS['hfd_vm8_tile']) for t in tl]
    if 'hfd_sfu' in slots:
        out['hfd_sfu'] = [dict(name=f'u_tile_{k}', cell='ot_su12_sfu', w=159.84, h=330.48, x=x, y=y, orient='R0',
                               pg='M6', strap='M7', sig='M6', ck=dict(pin='clk', face='W', layer='M4'),
                               status=TILE_STATUS['ot_su12_sfu_lane_cluster']) for k, (x, y) in enumerate(SFU_LANE_XY)]
    if 'hfd_idx_score_native_grid' in slots:
        g = IDX_HSLICE
        out['hfd_idx_score_native_grid'] = [
            dict(name=f'g_col[{c}].g_s[{hs}].u_hs', cell='ot_hdc_v41x_idx_hslice', w=g['w'], h=g['h'],
                 x=round(g['off'][0] + c * g['pitch'][0], 3), y=round(g['off'][1] + (7 - hs) * g['pitch'][1], 3),
                 orient='R0', pg='M6', strap='M7', sig='M6', ck=dict(pin='clk', face='N', layer='M5'),
                 status=TILE_STATUS['ot_hdc_v41x_idx_hslice']) for c in range(4) for hs in range(8)]
    return out


def region_plan(m, slots, tiles):
    """Per die region: fixed macros (slots / die-placed tiles), relay + clock + reset waypoints, PDN, sign-off."""
    regs, taken = [], set()
    # disjoint partition: the specific regions first, the enclosing 'hub' band takes the remainder
    for r in sorted(m.get('regions', []), key=lambda r_: r_['name'] == 'hub'):
        x0, y0, x1, y1 = r['rect']
        inside = [i for i in m['insts'] if i.name not in taken and x0 <= i.x + i.w / 2 < x1 and y0 <= i.y + i.h / 2 < y1]
        taken.update(i.name for i in inside)
        mac = Counter(i.master for i in inside if not (WAYPOINT.match(i.master) or i.kind == 'waypoint'))
        wpn = Counter(i.master for i in inside if WAYPOINT.match(i.master) or i.kind == 'waypoint')
        nt = sum(len(tiles.get(mn, [])) * c for mn, c in mac.items())
        regs.append(dict(
            name=r['name'], kind=r.get('kind'), rect_um=[round(v, 3) for v in r['rect']],
            fixed_macros=dict(mac), die_placed_tiles=nt,
            logic=dict(relays=sum(c for k, c in wpn.items() if not k.startswith('hfd_ckb')),
                       clock_buffers=wpn.get('hfd_ckb', 0)),
            clock='H-tree from the die PLL spine to every slot/tile clock_entry; leaf targets = each child lib '
                  'max_clock_tree_path insertion (CLOCK LATENCY rule), parent sinks balanced to it; reserved spine channel',
            pdn='die M8 (H) / M9 (V) straps; local M7 straps over M6-PG tiles (sfu lanes, idx hslices); M9 over lk_ep (exception)',
            gate=[f'child_lint PASS on every macro/tile ({sum(mac.values())} slots + {nt} tiles)',
                  'region route: TT setup >= 0 / FF hold >= 0 / DRC 0 at 833.333 ps on the exact-shape abstracts'],
            flow=['1 die GRT on the physical-relay variant with every macro/tile from its exact-shape LEF: '
                  'python3 tools/hbm_accel_die_fp.py grt --ds-var r25gqn_pr --work <host scratch>/grt_<tag> (fleet host, not '
                  'localhost/EPYC4)',
                  '2 region DRT on the die-GRT guides: python3 tools/hbm_die_region_drt.py stage --case <grt case> --name '
                  f"{r['name']} --window {' '.join(str(round(v, 1)) for v in r['rect'])}; run start_region.sh on the host",
                  '3 sign-off: tools/hbm_die_region_drt.py compare (TT setup / FF hold on RCX, DRC 0; GRT-vs-DRT wire / slack '
                  'correlation = the die error bar); seams per the seam_check criteria'],
            status='blocked: child_lint (see lint table) + physical relays (rf2)'))
    rest = [i for i in m['insts'] if i.name not in taken and not (WAYPOINT.match(i.master) or i.kind == 'waypoint')]
    regs.append(dict(name='periphery', kind='periphery', fixed_macros=dict(Counter(i.master for i in rest)),
                     note='PHY / SerDes / svc / link-ep ring outside the named regions: routed as its own die-top region'))
    return regs


SEAM_CHECK = dict(
    tool='tools/hbm_accel_die_seam_check.py (preflight; hbmdie-1011, to land with contract v2)',
    region_gate='tools/hier_contract/child_lint.py PASS on every tile / cluster LEF+libs placed in a die region (incl. (f) pin access, (d) TT/FF/SS libs) before that region route is submitted; hfd_hc_tile_xl @5c35b1a6e FAILS (449 blocked pins, no TT view) -> cons re-route with the pin-access hook',
    preflight_criteria=[
        'every seam = flop -> wire -> flop: driver pin is a registered output and load pin a pin-flop input in the '
        'child abstract (lib timing arc from the clock pin only)',
        'per stage Manhattan pin-to-pin wire <= 500 um (ASAP7 SS repeated wire 261 ps + 1.135 ps/um, 504 um per stage)',
        'TT setup: clk->q(launch) + wire + setup(capture) + |insertion(launch) - insertion(capture)| <= T - 60 ps unc',
        'FF hold: clk->q_min + wire_min - hold(capture) - skew >= 25 ps unc',
        'half-cycle seams (negedge launch, e.g. hfd_hc chains) use T/2 and must abut (<= 45 um)',
        'clock insertion per slot from the routed tile lib (max_clock_tree_path) -- recorded in slots[].clock_entry',
    ],
    ownership='OWNER ELEMENT CLOSURE UNDER TWO-LEVEL: tile-to-tile seams are DIE closure (hbmdie-1011 die-top region routes), not element closure; tracked per seam in this contract',
    closure_evidence='NOT the preflight (owner amendment 2): each die REGION is routed as a real top (tiles/clusters '
                     'fixed macros; relays, hubs, clock H-tree to every clock entry, PDN straps as logic/wires) and '
                     'signed off TT setup >= 0 / FF hold >= 0 / DRC 0 at 833.333 ps.',
)


def git_head():
    try:
        return subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--short=9', 'HEAD'], text=True).strip()
    except Exception:
        return 'unknown'


def pinned_ports(master):
    p = PINNED / master / 'ports.json'
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    w, h = d['w_um'], d['h_um']
    out = {}
    for port, rec in d['ports'].items():
        pins = rec.get('pins') or []
        faces = Counter()
        lay = Counter()
        lo, hi = 1e18, -1e18
        for nm, l_, x0, y0, x1, y1 in pins:
            f = 'W' if x0 <= 0.5 else 'E' if x1 >= w - 0.5 else 'S' if y0 <= 0.5 else 'N' if y1 >= h - 0.5 else 'AREA'
            faces[f] += 1
            lay[l_] += 1
            a = (y0 + y1) / 2 if f in 'EW' else (x0 + x1) / 2
            lo, hi = min(lo, a), max(hi, a)
        out[port] = dict(bits=rec.get('bits', len(pins)), face=faces.most_common(1)[0][0] if faces else None,
                         layer='/'.join(sorted(lay)), span_um=[round(lo, 3), round(hi, 3)] if pins else None)
    return out


def gen_ports(mst):
    out = {}
    for port, p in mst.ports.items():
        if p[0] == 'face':
            _, width, face, layer, centre, _pitch = p
            out[port] = dict(bits=width, face=face, layer=layer, centre_um=round(centre, 3))
        elif p[0] == 'area' and len(p) == 5:
            _, width, x, yc, _pitch = p
            out[port] = dict(bits=width, face='AREA', layer=None, xy=[round(x, 3), round(yc, 3)])
        else:
            out[port] = dict(raw=[str(v) for v in p])
    return out


def _lay(v):
    m_ = re.findall(r'M[1-9]', v or '')
    return m_[0] if m_ else None


def to_schema(rec, a):
    """opentallas.hier_contract.v1 (tools/hier_contract/contract.schema.json): one slot per die instance; pins on the
    first instance of each cell (the others carry a note), the hbmdie-1011 detail in the _detail.json sidecar."""
    slots = [dict(name='die', cell='hbm_r25gq_top', kind='die', parent=None,
                  outline=dict(w=rec['die_outline_um'][0], h=rec['die_outline_um'][1]), origin=dict(x=0.0, y=0.0, orient='R0'),
                  io_budget=dict(in_delay_frac=0.2, out_delay_frac=0.2), clock_entry=dict(pin='pll_ck', face='S', layer='M9'),
                  pg_layer='M9', strap_layer='M9', signal_max_layer='M9', version=a.version,
                  notes='die top: M8/M9 straps + die-region routes (tiles / clusters fixed macros)')]
    for cell, sl in rec['slots'].items():
        pins = []
        for pn, pv in sl['pins'].items():
            f = pv.get('face')
            l_ = _lay(pv.get('layer'))
            if f not in ('N', 'S', 'E', 'W') or not l_:
                continue
            b_ = pv.get('bits') or 1
            pe = dict(name=f'{pn}[{b_ - 1}:0]' if b_ > 1 else pn, face=f, layer=l_)
            if pv.get('centre_um') is not None:
                pe['offset'] = pv['centre_um']
            elif pv.get('span_um'):
                pe['offset'] = round(sum(pv['span_um']) / 2, 3)
            pins.append(pe)
        ce = sl['clock_entry']
        ce0 = next((dict(pin=c['pin'], face=c['face'], layer=_lay(c.get('layer')),
                         **({'offset': c['centre_um']} if c.get('centre_um') is not None else {}))
                    for c in ce if isinstance(ce, list) and c.get('face') in ('N', 'S', 'E', 'W') and _lay(c.get('layer'))),
                   None) if isinstance(ce, list) else None
        ip = ('IP macro: own PDN, die connects at its pins' if sl['hierarchy']['decision'] == 'hard_macro_ip' else '')
        for k_, inst in enumerate(sl['instances']):
            s_ = dict(name=inst['name'], cell=cell, kind='element', parent='die',
                      outline=dict(w=sl['outline_um'][0], h=sl['outline_um'][1]),
                      origin=dict(x=inst['xy'][0], y=inst['xy'][1], orient=inst['orient'] if inst['orient'] in ('R0', 'MX', 'MY', 'R180') else 'R0'),
                      io_budget=dict(in_delay_frac=0.2, out_delay_frac=0.2, registered_in=True, registered_out=True),
                      clock_entry=ce0 or dict(pin='ck', face='N', layer='M7'),
                      **{**dict(pg_layer='M7', strap_layer='M8', signal_max_layer='M7'),
                         **{k2: v2 for k2, v2 in LAYER_EXC.get(cell, {}).items() if k2 != 'why'}},
                      version=a.version,
                      notes=(f"hierarchy {sl['hierarchy']['decision']}" + (f'; {ip}' if ip else '') +
                             ('' if ce0 else '; clock entry = die H-tree leaf at the block ck pin (phys_trees)') +
                             ('' if k_ == 0 else f"; pins as {sl['instances'][0]['name']}")))
            if k_ == 0:
                s_['pins'] = pins
            slots.append(s_)
            for t in rec.get('tiles', {}).get(cell, []):
                slots.append(dict(
                    name=f"{inst['name']}/{t['name']}", cell=t['cell'], kind='tile', parent=inst['name'],
                    outline=dict(w=t['w'], h=t['h']), origin=dict(x=t['x'], y=t['y'], orient=t['orient']),
                    io_budget=dict(in_delay_frac=0.2, out_delay_frac=0.2, registered_in=True, registered_out=True),
                    clock_entry=t['ck'], pg_layer=t['pg'], strap_layer=t['strap'], signal_max_layer=t['sig'],
                    version=a.version, notes=f"die-placed tile (two-level); {t['status']}"))
    return dict(schema='opentallas.hier_contract.v1', die='hbm_r25gq', version=a.version, owner='hbmdie-1011',
                updated=__import__('datetime').datetime.now().astimezone().isoformat(timespec='minutes'),
                clock_period_ps=PERIOD_PS,
                layer_defaults=dict(pg_layer='M7', strap_layer='M8', signal_max_layer='M7'),
                changelog=[dict(version=d.get('version', a.version), change=d['note']) for d in rec['versions']] +
                          [dict(version=a.version, change=f"{x['id']} {x['slot']}: {x['change']} [{x['status']}]")
                           for x in rec['deltas']],
                slots=slots)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=ROOT / 'results/arch/hier_contract_1011/r25gq.json')
    ap.add_argument('--version', type=int, default=1)
    ap.add_argument('--note', default='')
    ap.add_argument('--relays', action='store_true', help='also count segments over reach with no physical relay')
    ap.add_argument('--variant', default='r25gqn', help='hbm_accel_die_fp ds-var preset (r25gqn; r25gqn_pr = physical relays)')
    a = ap.parse_args(argv)
    sys.argv = [sys.argv[0]]
    import hbm_accel_die_fp as F
    V = F.variant_arg(a.variant)
    m = F.build(V)
    M = F.masters(m)
    by_m = defaultdict(list)
    for it in m['insts']:
        by_m[it.master].append(it)
    slots, wp = {}, Counter()
    for mn, its in sorted(by_m.items()):
        if WAYPOINT.match(mn) or its[0].kind == 'waypoint':
            wp[mn] += len(its)
            continue
        mst = M.get(mn)
        pins = pinned_ports(mn) or (gen_ports(mst) if mst else {})
        ck = {p: v for p, v in pins.items() if re.fullmatch(r'(ck|clk|ckt?)\d*|ck[wens]\d*|clk_\w+', p)}
        obs = getattr(mst, 'obs_top', 7) if mst else 7
        h = HIER.get(mn, dict(decision='hard_macro_ip' if its[0].kind in ('phy', 'serdes_slab') or mn.startswith('ot_')
                              else 'hardened_block' if len(its) < 4 else 'hardened_cluster',
                              count_rule=str(len(its))))
        viol = []
        if obs >= 8:
            viol.append(f'signals up to M{obs}: M8/M9 are die-only')
        slots[mn] = dict(
            kind=its[0].kind, count=len(its),
            outline_um=[round(its[0].w, 3), round(its[0].h, 3)],
            area_mm2=round(its[0].w * its[0].h / 1e6, 4),
            instances=[dict(name=i.name, xy=[round(i.x, 3), round(i.y, 3)], orient=i.orient) for i in its],
            hierarchy=h,
            clock_entry=[dict(pin=p, **v) for p, v in ck.items()] or 'die H-tree leaf at the block ck pin (phys_trees)',
            pins=pins,
            pin_source='ports_r25gqn (pinned)' if (PINNED / mn / 'ports.json').exists() else 'generator masters()',
            io_budget=dict(IO_DEFAULT),
            layers=dict(signal_top=f'M{min(obs, 7)}', pg='M7 stripes (PG pins)', die_strap='M8', violations=viol),
        )
    tiles = tile_slots(slots)
    rec = dict(
        schema='hier-contract/0 (provisional HBM R25GQ; migrate to tools/hier_contract/)',
        die='hbm_r25gq', variant=a.variant, version=a.version,
        source=f'tools/hbm_accel_die_fp.py {a.variant} @ {git_head()} (claude/hrl-die-1011)',
        owner='hbmdie-1011 (log /home/ubuntu/claude-takeover-20261007/el1011-hbmdie.log)',
        period_ps=PERIOD_PS,
        die_outline_um=[round(m['geo']['W'], 3), round(m['geo']['H'], 3)],
        die_mm2=round(m['geo']['W'] * m['geo']['H'] / 1e6, 2),
        layer_contract=LAYER_CONTRACT,
        hierarchy_rule='two-level (tiles -> die) except clusters instantiated >= 4x: ONE hardened intermediate level, '
                       'harden once / replicate, built top-down to this contract',
        slots=slots,
        waypoints=dict(wp),
        unplaced_handoffs=dict(UNPLACED, **{'ot_hbm_native_frame_station_rb_NO2/NO3/NO3_SAFE (hbm-no3)': NO3_DECISION}),
        tiles={k: v for k, v in tiles.items()},
        vm_tunit=VM_TUNIT,
        seam_check=SEAM_CHECK,
        die_top_implementation=dict(
            regions=region_plan(m, slots, tiles),
            plan='per region: tiles / clusters fixed macros from their exact-shape LEFs, relays + hubs + reset relays + '
                 'clock buffers as logic, die PDN M8/M9 + local M7 straps over M6-PG two-level tiles; route + sign off '
                 'TT/FF/DRC 0 at 833.333 ps per region (the die is not flat-routed)',
            status='planned: regions route after the physical-relay re-floorplan (relay status below)'),
        relays=dict(
            reach_um=504.0,
            note='margin lint PASS today credits ceil(L/430) budget hops; audit 08:20 counted 1,101 data segments > 504 '
                 'um with no physical relay. phys_relays (route-aware stations) + relay_tree (shared-prefix stations '
                 'for multicast) implemented but OFF: relay_tree on r25gqn = 17,650 overlaps -> channels too narrow; '
                 'next = data-flow re-floorplan / relay banks (v2)'),
        deltas=[
            dict(id='D1', slot='hfd_hc', change='v6: 2,032.944 x 1,684.8 -> 2,263.68 x 1,499.04 = the CLOSED tiled quarter '
                 '(88 hfd_hc_tile_xl 8 x 11, pka10 view; r25gqw ports): SU-facing edge fixed, grows away from the spine into '
                 'the HC | attention channel (345.6 -> 114.96 um); N tr row-1 att->SU relays back at their 1,499.04 '
                 'positions, rly_N[WE]_1_1 re-centred in the narrowed channel (hops 480 / 480 um); tile sub-slots '
                 'unchanged in the quarter frame (the 2,263.68 quarter = rtl_qt @9c9c1a34b, same grid)', status='decided v6'),
            dict(id='D2', slot='hfd_hc', change='v1.1: no quarter cluster / no M8-PG quarter; the 88 closed tiles (PG M7) '
                 'are placed by the die in an HC region, die straps M8 (supersedes v1 "tile_xl PG M6")', status='decided v1.1'),
            dict(id='D3', slot='hfd_coll', change='1,399.656 x 1,561.68 (c07156bbc)', status='in place'),
            dict(id='D4', slot='hfd_attn_half_lo/hi', change='v10 lo 1,778.52 x 1,263.6 / hi 689.04 (c07156bbc)',
                 status='in place'),
            dict(id='D5', slot='hfd_hgi_vm', change='v3: VM tunit builds at the die config (main 20730548c) + ot_hgi_vm_btile.sv; '
                 'latency contract request->response +12, rq->rr +8, rq->credit +6, w2q->credit +6 / ->done +8, wq->done +8, '
                 'ap RTT +2, reset +3 (vm_tunit record); TUNIT stays 0 until the btile + VM parent close', status='contract v3'),
            dict(id='D6', slot='hfd_sfu/su ctl', change='DENR=1 now; SFUT=2 when the lane cluster closes', status='open'),
            dict(id='D7', slot='hfd_hc', change='v3: 88 tile sub-slots per quarter from macro_place.tcl @87e02e7ad (8 x 11 '
                 'serpentine, v6: all inside 2,263.68 x 1,499.04, the closed quarter frame; the 316 um SU-side band x 1,947-2,263 holds the head relays / glue as in the closed quarter); region gate waits on tile '
                 'child_lint (f)', status='contract v3'),
            dict(id='D8', slot='hfd_vm_sw/se/nw/ne', change='v3: 36 VM8 tile sub-slots (6 open halves x 6, 9adc3c44e); '
                 'e half at x 349.056; clock entry ckt<k> M7 area pin; +1 cycle on the listed half seams', status='contract v3'),
            dict(id='D9', slot='hfd_sfu', change='v3: 16 lane-cluster sub-slots 159.84 x 330.48 per quarter on the old lane '
                 'lattice (173-um channels = face/broadcast relay stages); ctlw tile moves to hfd_su', status='contract v3'),
            dict(id='D10', slot='hfd_hgi_idx', change='w8 cluster slot growth (rf2) + IXW=1 lane-station request (idxs 20:45): '
                 'accepted in principle -- lgE KE 4 -> 5 once the IXW adapter passes its bench', status='open'),
            dict(id='D11', slot='hfd_idx_score_native_grid', change='v3: two-level, 32 r2 hslice sub-slots per grid (no chunk '
                 'cluster)', status='contract v3'),
            dict(id='D12', slot='NO3 station', change='v3: not a R25GQ element (R24W W2 publication chain); recorded only',
                 status='decided v3'),
            dict(id='D13', slot='die', change='v4: contract on r25gqn_pr (b4638437b): data segments > 504 um 985 -> 0, 0 '
                 'overlaps, die 856.95 mm2 (svc channels +108 um); residual check rc 3 = 8 clock/reset tree segments > 504 '
                 'um + 7 far-side data relays, all at the lk_ep S row (84-um gaps full) -> D16', status='v4; residual closed v5 (D18)'),
            dict(id='D14', slot='hfd_cmdproc / hfd_coll', change='coll_recx 554 b (TOPK_MERGE sideband): t_hgi_coll widens by '
                 '554 b when the TKM tiles compose on the die (die coll view TKM=0 today); lgEcp / lgEatt / t_hgi_e2* classed '
                 'OPEN with owners (main 04dad4b3a)', status='open'),
            dict(id='D15', slot='hfd_hgi_idx', change='v4: 640.008 x 600.48 -> 1,270.08 x 1,719.36 at (14,800.32, 7,112.88) for '
                 'the w8 cluster (43.2 um to idx_selector); spine above moves up: idx_selector y 8,875, coll 10,902, hgi_vm '
                 '12,506, cmdproc 14,623', status='v4'),
            dict(id='D16', slot='hfd_lk_ep S row', change='re-grant pending: the 84-um inter-ep channels carry every N-S crossing '
                 'of the row; widen to >= 200 um (pitch 2,800) or move the S row', status='closed v5 (D18)'),
            dict(id='D18', slot='hfd_lk_ep S row', change='v5 re-grant (closes D16): the one-row S band (5 x 2,600 in the 13,504-um '
                 'sm7 | sm14 gap, 84-um channels) becomes a 3 + 2 brick in the free band y 6,016-7,977: row 1 y 6,016 at x 7,886 '
                 '(ep_S0) / 11,500 (ep_S2) / 16,270 (ep_S3), row 2 y 7,046 at x 7,886 (ep_S1) / 16,270 (ep_S4); slot 2,600 x 830 '
                 'and the pg M8 / strap M9 exception unchanged; every channel >= 200 um (A2-A3 2,170 over the SerDes); '
                 'check rc 3 -> 0 (8 clock/reset tree segments + far-side relays -> 0)', status='v5'),
            dict(id='D17', slot='hfd_hc_eng', change='lane-major N-face re-pin accepted; needs per-lane ports in the die bus model '
                 '(generator places each port contiguous) and the lgE station spanning the full 4,384.8 face', status='open'),
            dict(id='D19', slot='hfd_hc', change='v7: the 19 die-wired ports shared with the closed quarter (f_sfu / t_sfu 1,024 b, '
                 'rst, ck0..7 e / w) take the CLOSED quarter\'s own pins and layers (hcp/r25gqw/ports/hfd_hc: f_sfu E M4 '
                 '404.4-600.8, t_sfu E M4 601.2-797.6, both 0.192 pitch; rst E M4 801.0; ck0/1/4-7e E M4, ck2e/ck3e E M6, '
                 'ck<c>w W M4), not the generator plan (closed_pin_records). Seam plan pin to pin, bit by bit: t_sfu -> '
                 'sfu f_hc 853 um -> one registered pitch-matched seam station per quarter in the HC | SFU channel '
                 '(hfd_stn_s1024E/W, MX copies on the N quarters; hops <= 429 um; +1 cycle on HC -> SFU); f_sfu 465 um '
                 'direct; ck / rst attach the die tree at the real pins (each ck<c>e / ck<c>w its own sink; leaf -> pin '
                 '<= 185 um). The 10 generator-only ports (t/f_hgi_vmap, f_hgi_vmr, t_hgi_vmq, f/t_hgi_cmdproc, '
                 'f/t_lgW_*) are NOT on the closed quarter: re-packed clear of its pins; the quarter owner must add them '
                 'or the die must re-home them', status='decided v7 (hgi ports open)'),
        ],
        versions=[dict(version=a.version, by='hbmdie-1011', note=a.note or 'v1 provisional')],
    )
    if a.relays:
        import hbm_accel_die_fp as F2
        import fp_margin_lint as FPL
        buses = [b_ for b_ in m['buses'] if b_[1] not in ('clock_trunk', 'reset_tree')]
        ml_ = FPL.die_margin(m['insts'], buses, F2.MARGIN_RELAY_KINDS, reach_um=F2.SS_REACH_UM,
                             stages=lambda bid, L: 0, limit=100000, edges=True)
        rec['relays']['segments_over_reach_physical_only'] = ml_.get('reach_violations')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    detail = a.out.with_name(a.out.stem + '_detail.json')
    rec['schema'] = 'hbmdie-1011 detail (sidecar of the opentallas.hier_contract.v1 file ' + a.out.name + ')'
    detail.write_text(json.dumps(rec, indent=1) + '\n')
    a.out.write_text(json.dumps(to_schema(rec, a), indent=1) + '\n')
    print(json.dumps(dict(out=str(a.out), slots=len(slots), waypoints=sum(wp.values()),
                          clusters=sorted(k for k, v in slots.items() if v['hierarchy']['decision'] == 'hardened_cluster'),
                          relays=rec['relays'].get('segments_over_reach_physical_only'))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
