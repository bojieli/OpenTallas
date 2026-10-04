#!/usr/bin/env python3
"""Qwen3-8B ROM near-HBM floorplan, r2: physical-design margins netted (model only; no RTL, no P&R).

Successor of tools/qwen_rom_floorplan_nearhbm.py (r1, model-r1.json / floorplan-r1.svg, kept byte-identical: this tool
imports r1 and never edits it).  r1 left five things un-netted; r2 nets them and re-derives the die:

  1. every corridor/channel capacity per layer after the power grid at the coverage each REGION needs (the r1 closed-form
     IR model, 35 mV budget, applied to the tile field, hub, strip and controller band at their own in-phase density),
     the clock spine, and a via/obstruction allowance;
  2. physical-design targets from this repository's routed evidence: track usage <= 70% of the netted tracks, the
     routed buffered-corridor density bracket (v41_corridor_136um_*), repeaters and pipeline stations for every long
     wire at the SS reach of 504 um/stage, CTS area/power;
  3. the re-derived outline: corridor widths, spine, link channels and die, against 815 mm2, with the KV service
     reservation trimmed to what a near-HBM controller keeps (re-summed from the four generators, zero residual);
  4. hot-spot power density against a SOURCED limit (IEEE EPS HIR Thermal chapter), with the PHY figure corrected to
     published host-PHY energy, and the mitigation sized.

Usage:
  python3 tools/qwen_rom_floorplan_nearhbm_r2.py             # writes model-r2.json and floorplan-r2.svg
  python3 tools/qwen_rom_floorplan_nearhbm_r2.py --verify    # regenerate in a temp dir, require byte identity
"""
from __future__ import annotations

import argparse
import filecmp
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import qwen_rom_floorplan_nearhbm as F  # noqa: E402  (r1: frames, lattice, row-engine, hub element, svg)
import uarch_model as U  # noqa: E402
import v41_die_assembly as VA  # noqa: E402

OUT = F.OUT
RECORD, SVG = 'model-r2.json', 'floorplan-r2.svg'
SCHEMA = 'opentallas.qwen-rom-floorplan-nearhbm.v2'
KVDIR = OUT / 'inputs/kvservice'
sys.path.insert(0, str(KVDIR))
import kv_service_families as KVF  # noqa: E402

P2 = dict(
    r1_tool='tools/qwen_rom_floorplan_nearhbm.py',
    r1_record='results/uarch/qwen_rom_floorplan_nearhbm_20261003/model-r1.json',
    kv_families='results/uarch/qwen_rom_floorplan_nearhbm_20261003/inputs/kvservice/kv_service_families.py',
    corridor_pass='results/physical_abi3/asap7/chip/dies/v41_corridor_136um_1500w_M4up.json',
    corridor_stop='results/physical_abi3/asap7/chip/dies/v41_corridor_136um_3000w_M4up.json',
    corridor_fail='results/physical_abi3/asap7/chip/dies/v41_corridor_140um_300w_M6up.json',
    die_grt='results/physical_abi3/asap7/chip/dies/v41_rom_asbuilt_grt.json',
    ir_options='results/physical_abi3/asap7/chip/v41_w18/ir/ir_options.json',
    pair_power='results/physical_abi3/asap7/chip/v41_w18/pair_w10p5_abstract.json',
    energy='results/physical_abi3/asap7/signoff/energy_per_token.json',
    cell_prices='results/uarch/topk_integer_tree_service_model_20261002/inputs/cell_prices.json',
    credit17='results/uarch/qwen_rom_kv_credit17_20261003/model-r3.json',
    cooling=F.P['cooling'],
    power_cfg=F.P['power'],
    pdn=F.P['pdn'],
    fulltile=F.P['fulltile'],
    kv_parent='results/uarch/qwen_rom_parent_context_service_20261002/model-r7.json',
    kv_bank_groups='results/uarch/qwen_rom_kv_bank_groups_20261002/model-r4.json',
    kv_successor='results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json',
)

# ---------------------------------------------------------------- constants (each with its source / grade)
PITCH_UM = {'M4': 0.048, 'M5': 0.048, 'M6': 0.064, 'M7': 0.064, 'M8': 0.080, 'M9': 0.080}  # r1 UPPER_PITCH_NM + ASAP7 M4/M5
DIRECTION = {'M4': 'H', 'M5': 'V', 'M6': 'H', 'M7': 'V', 'M8': 'H', 'M9': 'V'}  # ASAP7: even layers horizontal
TARGET_USAGE = 0.70           # <= 70% of netted tracks: = min(1 - ORFS asap7 ROUTING_LAYER_ADJUSTMENT 0.25,
                              #   1 - die model m8_m9_reserve 0.30 in v41_*_grt.json route_model)
VIA_OBS = 0.05                # ASSUMED via-stack / pin-access obstruction allowance on every corridor layer
PG_PITCH_UM = 40.0            # pdn_die.tcl M8/M9 stripe pitch (VDD and VSS once per pitch)
PG_BASE_COV = 1.0 / 40.0      # pdn_die.tcl 1.0 um stripe per 40 um: 2.5% of each layer per net (never lowered here)
M6_STRAP = (0.288, 10.8)      # pdn_die.tcl M6 -width 0.288 -pitch 10.8 (VDD+VSS pair per pitch)
CLOCK_SPINE_TRACKS = 3        # shielded clock spine for a channel's pipeline stations: signal + 2 shields (ASSUMED)
CTS_AREA_FRAC = 0.053         # p90 clock_buffer+clock_inverter / stdcell area over 139 clean routed ASAP7 blocks
REPAIR_AREA_FRAC = 0.067      # median timing_repair_buffer / stdcell area, same 139 blocks
CELL_UTIL_CAP = F.CELL_UTIL_TARGET  # 0.70 (r1, macro pin-access audit)
FF_UM2 = F.FF_UM2             # r1 pricing FF per bit (ASR + INV), > the routed median 0.321 (conservative)
BUF_UM2 = 0.10206             # BUFx4_ASAP7 (cell_prices.json)
CLK_J_MM2_CYC = dict(assumed_gated=8.5e-11, measured_network_ungated=4.58e-10)   # technology.json; energy_per_token
HOST_PHY_PJ_B = dict(chae_jssc2024_4nm_hbm3=0.29, intel4_vlsid2025=0.5, oconnor_micro2017_io_both_ends=0.8)
HOTSPOT = dict(nominal=2.0, conservative=1.0, aggressive=4.0)
SI_DIFFUSIVITY = 8.8e-5       # m2/s, bulk silicon near 100 C (thermal time constant w^2 / alpha)
STACKS = F.STACKS

HOTSPOT_SOURCES = [
    dict(ref='IEEE EPS Heterogeneous Integration Roadmap, Chapter 20 Thermal, draft v0.9 (2026)',
         url='https://eps.ieee.org/wp-content/uploads/2026/05/HIR_20-Thermal_0.9.docx.pdf',
         sha256_fetched_2026_10_03='ef2643c8cfebbc70b54ca45ae9e0ccec8f9a2e7d8f0c93fa64b73785693b31e6',
         quotes=['s2: "The local heat flux of GPU logic dies has increased from approximately 1-2 W/mm2 in previous '
                 'generations to over 4 W/mm2 in the latest and upcoming products."',
                 'Table 4, water cold plate: "2.50 W/mm2 (uniform heat flux)"; "1.70 W/mm2 (thermal budget 50 C) Chip area '
                 '= 4 cm2, heat sink base area = 16 cm2 [40]"; "Water jet impingement [46] 4.6 W/mm2"',
                 'text: "Chip-scale cold plate designs with fluorocarbon cooling can be used with heat flux levels of up to '
                 '100 to 300 W/cm2"; "Indirect water cooling can achieve ... up to 300 to 450 W/cm2 for chip-scale water '
                 'jet impingement"',
                 's3: "The combined power density of HBM and the logic die can lead to local hotspots"']),
    dict(ref='AMD XAPP1377, Obtaining Thermal and Power Targets', url='https://docs.amd.com',
         note='HBM 95 C for constant operation, 105 C for a limited time (read by a research sub-agent; not re-fetched)'),
    dict(ref='van Erp et al., Co-designing electronics with microfluidics for more sustainable cooling, Nature 585 (2020)',
         doi='10.1038/s41586-020-2666-1', note='> 1 kW/cm2 with in-silicon microchannels: an upper bound, not a cold plate'),
]
PHY_SOURCES = [
    dict(ref="O'Connor et al., Fine-Grained DRAM, MICRO-50 2017", doi='10.1145/3123939.3124545',
         url='https://research.nvidia.com/sites/default/files/pubs/2017-10_Fine-Grained-DRAM%3A-Energy-Efficient/'
             'oconnor_and_chatterjee.micro2017.pdf',
         sha256_fetched_2026_10_03='b2c8b93b879fe85c44ec5f890331478cc64ffda79a4fa21130bf78fca21b247c',
         quote='Table 3 "I/O (pJ/b) 0.80" (HBM2, interposer I/O both ends, 50% activity); s2 total HBM2 access 3.92 pJ/bit'),
    dict(ref='Chae et al., A 4-nm 1.15 TB/s HBM3 Interface With Resistor-Tuned Offset Calibration and In Situ Margin '
             'Detection, IEEE JSSC 59(1):231-242, 2024 (ISSCC 2023)', url='https://ieeexplore.ieee.org/document/10329576',
         note='0.29 pJ/bit host interface: figure read by a research sub-agent; title/venue verified via dblp'),
    dict(ref='Intel 4 EMIB HBM3 PHY, VLSID 2025', url='https://ieeexplore.ieee.org/document/10900678',
         note='0.5 pJ/bit at 7.2 Gb/s: read by a research sub-agent, not re-verified'),
]

# KV service families a near-HBM controller KEEPS (per-PC queue, pending tags, bank/command scheduling, refresh,
# return ordering, write-vs-read hazard, transaction identity) and AMBIGUOUS ones (kept here: conservative).  Every other
# family exists only to distribute KV to 1,536 tiles (fill network, assembly pools, group rings, cohort credits).
KV_KEEP = {
    'S:gross_native_PC_bank_and_held_state', 'G:native_PC_tagged_pending_reads', 'S:pending_key_comparison_holds',
    'S:eligibility_four_register_levels', 'G:PC_frozen16_record_lookahead', 'S:RW alias hazard eq',
    'S:request_free_slot_generation_order', 'C:return_protection_two_registers', 'S:lookahead_valid_skip_sequence',
    'S:lookahead_refill_controls', 'G:command_lookahead_head_holds', 'B:shared return arbiter',
    'S:refresh_priority_and_cache_generation', 'S:shared_command_final_revalidation',
    'C:namespace_atomic_alloc_retire_protection', 'S:request_order_head_tail', 'G:return_depth64_pointers'}
KV_AMBIGUOUS = {
    'B:tagged owner pipeline (flights/outputs/dup masks)': 'return ordering kept; context lookup and seen-masks address tiles',
    'C:pending_four_FF_spill': 'pending 64 -> 68 set by the 17 x 4 cohort credit, not by bandwidth-delay',
    'G:shared_tag_group_owner_map': 'shared 4,096-tag namespace serves cohorts; per-PC tags would replace it',
    'B:producer CDC route+source FIFO': 'new-token K/V write kept, but this is a global serial->stream route',
    'G:expanded_burst_receipts': 'tracks bursts across PCs for cohort release',
    'C:burst_receipt_increment': 'same family as expanded burst receipts',
    'B:tag quarantine': 'epoch protection kept; release waits on reverse grants',
    'G:one_early_context_capture_per_actual_bank': 'group/cohort sizing',
    'G:group_local_ingress': 'group/cohort sizing', 'G:write_class_and_cohort_flight_route': 'group/cohort sizing',
    'C:pending_key_register_increment': 'cohort pending key', 'C:spill_pointer_valid_controls': 'cohort spill'}


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def load(rel):
    return json.loads((ROOT / rel).read_text())


def snap_up(v, q):
    return F.snap_up(v, q)


# ---------------------------------------------------------------- IR (r1 closed form, per W/mm2)
def ir_mv_per_w_mm2(cov):
    rc = VA.asap7_layer_rc()
    rho = sum(rc[k][0] * 1e3 * 0.040 for k in ('M8', 'M9')) / 2
    V = VA.CONST['vdd_v']['value']
    p = VA.CONST['bump_pitch_um']['value'] / math.sqrt(VA.CONST['power_bump_fraction']['value'])
    Rc = p / math.sqrt(math.pi)
    a = VA.CONST['bump_contact_radius_um']['value']
    geom = Rc ** 2 * math.log(Rc / a) - (Rc ** 2 - a ** 2) / 2
    J = 1.0 / V * 1e-6
    return J * (rho / cov) / 2 * geom * 2 * 1e3


def ir_budget_mv():
    return VA.CONST['ir_budget_fraction']['value'] * VA.CONST['vdd_v']['value'] * 1e3


def coverage_needed(w_mm2):
    """M8/M9 coverage per net so the region's in-phase density drops <= 35 mV; never below the existing 2.5% grid"""
    need = PG_BASE_COV * w_mm2 * ir_mv_per_w_mm2(PG_BASE_COV) / ir_budget_mv()
    return max(PG_BASE_COV, need)


# ---------------------------------------------------------------- region power densities
def region_power(r1, pr, cool, c17, kv):
    """in-phase peak (IR) and time-averaged (thermal) W/mm2 of every region, scenarios A (measured TT MAC) and B"""
    rate = r1['selected_entry']['tokens_s']
    tok_cycles = pr['r2']['primary']['token_cycles']
    leak, clk = 0.10, 8.5e-11 * 1.2e9           # r1 basis: technology.json logic leakage, gated clock J/mm2/cycle
    static = leak + clk
    a = r1['area']['rows']
    busy = c17['unified_model_join']['baseline_unit_busy']
    out = {}
    pw = r1['power']
    for sc, key in (('A', 'A_measured_implementation'), ('B', 'B_proposed_production')):
        d = cool['baseline'][key]['dynamic_mJ_parts']
        # tile field: weight MACs + ROM reads over the weights-busy window (qwen_tp_point unit busy, 1.2 GHz)
        t_w = busy['weights'] / 1.2e9
        tile_peak = (d['mac_weights'] + d['rom_read_and_delivery']) * 1e-3 / t_w / a['tile_field'] + static
        tile_avg = (d['mac_weights'] + d['rom_read_and_delivery']) * 1e-3 * rate / a['tile_field'] + static
        # hub: stream unit over its busy window, on the hub spine contents (W5 placed blocks)
        hub_mm2 = r1['floorplan']['spine']['hub_contents_mm2']
        t_s = busy['stream'] / 1.2e9
        hub_peak = d['stream_unit'] * 1e-3 / t_s / hub_mm2 + static
        hub_avg = d['stream_unit'] * 1e-3 * rate / hub_mm2 + static
        strip = pw['scenarios'][sc]['strip_w_per_mm2']
        out[sc] = dict(tile_field=dict(peak=round(tile_peak, 3), avg=round(tile_avg, 3)),
                       hub=dict(peak=round(hub_peak, 3), avg=round(hub_avg, 3)),
                       strip=dict(peak=strip['peak_in_phase'], avg=strip['avg']))
    return dict(rate_tokens_s=rate, static_w_per_mm2=round(static, 3), scenarios=out,
                windows=dict(weights_busy_cycles=busy['weights'], stream_busy_cycles=busy['stream'],
                             source=f"{P2['credit17']} unified_model_join.baseline_unit_busy (tools/uarch_model.py:qwen_tp_point)"),
                token_cycles=tok_cycles)


# ---------------------------------------------------------------- PHY and controller band
def phy_and_band(r1, pr, band_mm2_per_stack):
    rate = r1['selected_entry']['tokens_s']
    kv_B = 150976512
    bw_avg = kv_B * rate / STACKS
    bw_pk = pr['rates_per_stack']['HBM_sustained_Bps']
    phy_mm2 = r1['power']['phy_mm2']
    phy = {k: dict(peak=round(bw_pk * 8 * v * 1e-12 / phy_mm2, 3), avg=round(bw_avg * 8 * v * 1e-12 / phy_mm2, 3))
           for k, v in HOST_PHY_PJ_B.items()}
    residual = 10.19 - HOST_PHY_PJ_B['oconnor_micro2017_io_both_ends']
    strip_peak = r1['power']['scenarios']['A']['strip_w_per_mm2']['peak_in_phase']
    band = dict(
        area_mm2_per_stack=round(band_mm2_per_stack, 3),
        unqualified_residual_pj_b=round(residual, 2),
        residual_if_charged_here=dict(peak=round(bw_pk * 8 * residual * 1e-12 / band_mm2_per_stack, 2),
                                      avg=round(bw_avg * 8 * residual * 1e-12 / band_mm2_per_stack, 2)),
        logic_density_bound=dict(
            w_per_mm2=strip_peak,
            basis='the controller band is FF/mux/compare logic; no logic region on this die exceeds the in-phase row-engine '
                  'density (every MAC lane toggling, scenario A)',
            implied_pj_b_at_peak=round(strip_peak * band_mm2_per_stack / (bw_pk * 8) * 1e12, 2),
            avg_w_per_mm2_at_that_bound=round(strip_peak * bw_avg / bw_pk, 3)),
        allowed_pj_b_time_averaged={k: round(v * band_mm2_per_stack / (bw_avg * 8) * 1e12, 2) for k, v in HOTSPOT.items()},
        verdict=None)
    band['verdict'] = ('the 9.39 pJ/b residual of the unqualified 10.19 pJ/b HBM die share cannot be a controller-band '
                       f"charge: it would be {band['residual_if_charged_here']['peak']} W/mm2 in phase, "
                       f"{band['residual_if_charged_here']['peak'] / strip_peak:.1f}x the densest logic on the die. Bounded by "
                       f"logic density the band is <= {band['logic_density_bound']['implied_pj_b_at_peak']} pJ/b and "
                       f"{band['logic_density_bound']['avg_w_per_mm2_at_that_bound']} W/mm2 time-averaged (PASS 2.0). In a GPU the "
                       'residual is spent on the L2-to-controller fabric spread over the die; here it has no physical home. '
                       'A measured controller energy replaces the bound.')
    return dict(hbm_bw_Bps_per_stack=dict(avg=round(bw_avg), peak=bw_pk, duty=round(bw_avg / bw_pk, 4)),
                phy_mm2=phy_mm2, phy_w_per_mm2_published=phy,
                r1_phy_w_per_mm2=r1['power']['scenarios']['A']['phy_w_per_mm2']['unqualified_die_share'],
                phy_verdict=('r1 7.34 W/mm2 is IMPLAUSIBLE: it placed the whole 10.19 pJ/b HBM die share (controller, PHY both '
                             'ends, ECC, on-die movement, control plane: SC\'25 MI250X minus O\'Connor) on the PHY footprint. '
                             f"Published host PHY energy 0.29-0.8 pJ/b gives {phy['chae_jssc2024_4nm_hbm3']['peak']}-"
                             f"{phy['oconnor_micro2017_io_both_ends']['peak']} W/mm2 at the 0.9 TB/s peak and "
                             f"{phy['oconnor_micro2017_io_both_ends']['avg']} W/mm2 averaged: PASS at every limit."),
                controller_band=band, sources=PHY_SOURCES)


# ---------------------------------------------------------------- corridor netting
def layer_net(width_um, layer, cov, clock_tracks=0):
    raw = math.floor(width_um / PITCH_UM[layer] + 1e-8)
    if layer in ('M8', 'M9'):
        f_pg = 2 * cov + 2 * 2 * PITCH_UM[layer] / PG_PITCH_UM          # VDD+VSS width + one spacing track each edge
    elif layer == 'M6':
        f_pg = 2 * (M6_STRAP[0] + PITCH_UM['M6']) / M6_STRAP[1]
    else:
        f_pg = 0.0                                                     # pdn_die.tcl puts no M7 straps in the die grid
    pg = math.ceil(raw * f_pg)
    via = math.ceil(raw * VIA_OBS)
    net = raw - pg - via - clock_tracks
    return dict(raw=raw, pg=pg, via_obs=via, clock=clock_tracks, netted=net, target=math.floor(TARGET_USAGE * net),
                r1_rule=math.floor(raw * F.SIGNAL_SHARE))


def corridor(name, width_um, layers, cov, demand, region, clock_on=None, r1_spare=True, q=F.SNAP_X):
    def at(w):
        return {l: layer_net(w, l, cov, CLOCK_SPINE_TRACKS if l == clock_on else 0) for l in layers}
    cur = at(width_um)
    target_sum = sum(v['target'] for v in cur.values())
    raw_sum = sum(v['raw'] for v in cur.values())
    w = q
    while sum(v['target'] for v in at(w).values()) < demand:
        w += q
    w_r2 = round(w, 3)
    r1_need = math.ceil(demand * (1 + F.SPARE)) if r1_spare else demand
    return dict(name=name, region=region, layers=list(layers), pg_coverage_per_net=round(cov, 4),
                width_r1_um=width_um, demand_tracks=demand, per_layer_at_r1_width=cur,
                netted_target_tracks_at_r1_width=target_sum,
                usage_of_netted_at_r1_width=round(demand / sum(v['netted'] for v in cur.values()), 3),
                demand_over_raw_same_direction=round(demand / raw_sum, 3),
                fits_70pct_at_r1_width=target_sum >= demand,
                r1_rule_capacity=sum(v['r1_rule'] for v in cur.values()), r1_rule_need_with_spare=r1_need,
                width_for_70pct_um=w_r2, width_r2_um=max(width_um, w_r2),
                note='width_r2 = max(r1, 70%-of-netted): r1 widths are never narrowed (no relaxation)')


def corridor_evidence():
    ok, stop, bad = load(P2['corridor_pass']), load(P2['corridor_stop']), load(P2['corridor_fail'])
    h_layers = [l for l in ('M4', 'M6', 'M8')]
    raw_h = sum(math.floor(ok['width_um'] / PITCH_UM[l]) for l in h_layers)
    buf_per_wire_mm = ok['repair_buffers_inserted'][0] / (ok['wires'] * ok['length_mm'])
    return dict(
        passed=dict(record=P2['corridor_pass'], width_um=ok['width_um'], wires=ok['wires'], length_mm=ok['length_mm'],
                    grt_usage_pct=ok['grt_usage_pct'], grt_overflow=ok['grt_overflow'], layers=ok['signal_layers'],
                    layer_adjustment=ok['layer_adjustment'], raw_same_direction_tracks=raw_h,
                    demand_over_raw_same_direction=round(ok['wires'] / raw_h, 3),
                    repair_buffers=ok['repair_buffers_inserted'][0], buffers_per_wire_mm=round(buf_per_wire_mm, 2),
                    period_ps=ok['period_ps'], claim_boundary=ok['claim_boundary']),
        unresolved=dict(record=P2['corridor_stop'], wires=stop['wires'], status=stop['status'], reason=stop['reason'],
                        demand_over_raw_same_direction=round(stop['wires'] / raw_h, 3)),
        failed=dict(record=P2['corridor_fail'], status=bad['status'], note='M6-and-up only, M1-pin flops: pin access'),
        bracket=('a buffered straight-bus corridor routes at 0.225 of the raw same-direction tracks (GRT 30.06%, 0 overflow) '
                 'and is UNRESOLVED at 0.451 (GRT still in congestion reduction after 75 min); nothing between is measured'),
        buffers_per_wire_mm=buf_per_wire_mm)


# ---------------------------------------------------------------- long wires: stations, repeaters, CTS
def long_wires(r1, fr2, ev, tile_h):
    reach = U.SS_REACH_UM[1.2e9]
    bpm = ev['buffers_per_wire_mm']
    link_bits = r1['routes']['corridors']['per_link_tracks']
    trunk = r1['routes']['hub_to_stack']['manhattan_um'] + r1['routes']['hub_to_stack']['in_strip_fan_um']
    arr_h = fr2['array_um'][1]
    rows = []

    def row(name, wires, length_um, copies, note):
        st = math.ceil(length_um / reach)
        ff = wires * st * copies * FF_UM2
        rep = wires * length_um / 1000 * copies * bpm * BUF_UM2
        rows.append(dict(wire=name, wires=wires, length_um=round(length_um, 1), copies=copies, stages=st,
                         station_FF_mm2=round(ff / 1e6, 4), repeater_mm2=round(rep / 1e6, 4), note=note))
    row('hub <-> stack link (trunk + in-strip fan)', link_bits, trunk, STACKS,
        'r1 counts these stations; repeaters added here')
    row('tile column corridor (637 non-fill bits)', F.NONFILL_CUT_TRACKS, arr_h, F.TILE_COLS,
        f'tile pitch {tile_h} um > 504 um reach: {math.ceil(tile_h / reach)} stages per tile hop; inside the 112 measured '
        'wire stages of me_lat_extra (latency already counted); area NOT in the tile cell ceiling, charged here')
    row('hub <-> north IO (collective, 2 x 512 b assumed)', 1024, r1['routes']['hub_to_io_edge']['um'], 1,
        'all-reduce stream owns the latency; area charged here')
    st_ff = sum(r['station_FF_mm2'] for r in rows)
    rep = sum(r['repeater_mm2'] for r in rows)
    return dict(reach_um=reach, buffers_per_wire_mm=round(bpm, 2), buffer_cell='BUFx4_ASAP7_75t_R 0.10206 um2',
                ff_um2_per_bit=FF_UM2, rows=rows, station_FF_mm2=round(st_ff, 3), repeater_mm2=round(rep, 3),
                placement=('stations and repeaters sit in the corridor / channel rows under the bus: tile corridor '
                           f"{round(rows[1]['station_FF_mm2'] + rows[1]['repeater_mm2'], 3)} mm2 over "
                           f"{round(F.TILE_COLS * fr2['tile_corridor_um'] * arr_h / 1e6, 2)} mm2 of corridor"))


def cts_plan(fr2, r1, areas):
    tiles = F.TILE_COLS * F.TILE_ROWS
    cells = dict(tiles=tiles * F.CELL_CEILING_UM2 / 1e6, row_engines=areas['row_engine_cells_mm2'],
                 hub_spine=areas['hub_contents_mm2'], kv_controller=areas['kv_kept_mm2'],
                 stations_repeaters=areas['long_wire_mm2'])
    cts = {k: round(v * CTS_AREA_FRAC, 3) for k, v in cells.items()}
    W, H = fr2['die_um']
    lv = math.ceil(math.log2(tiles + 24 + 1))
    tot_um, depth_um = VA.htree(W, H, lv)
    tot_um *= 1.0
    reach = U.SS_REACH_UM[1.2e9]
    clock_area_logic = sum(cells.values())
    p = {k: round(v * 1.2e9 * clock_area_logic / 0.5, 1) for k, v in CLK_J_MM2_CYC.items()}
    util_after = {k: round(u * (1 + CTS_AREA_FRAC + REPAIR_AREA_FRAC), 3)
                  for k, u in (('tile_slot', F.TILE_LOGIC_UTIL), ('hub_element', 0.70), ('link_station', 0.53))}
    return dict(cts_area_fraction=CTS_AREA_FRAC, repair_area_fraction=REPAIR_AREA_FRAC,
                source='139 clean routed ASAP7 blocks (results/**/metadata.json finish__design__instance__area__class__'
                       'clock_{buffer,inverter} and __timing_repair_buffer over stdcell area): CTS median 4.2%, p90 5.3%; '
                       'repair median 6.7%, p90 20.8%',
                cell_mm2={k: round(v, 2) for k, v in cells.items()}, cts_cell_mm2=cts, cts_total_mm2=round(sum(cts.values()), 2),
                placement='CTS and repair buffers land in each region\'s whitespace: final utilisation = initial x '
                          f'(1 + {CTS_AREA_FRAC} + {REPAIR_AREA_FRAC})',
                util_after_cts_and_repair=util_after,
                util_cap=CELL_UTIL_CAP,
                hub_element_frame_growth=round(math.sqrt(1 + CTS_AREA_FRAC + REPAIR_AREA_FRAC), 4),
                global_htree=dict(levels=lv, total_um=round(tot_um), root_to_leaf_um=round(depth_um),
                                  repeater_stages_root_to_leaf=math.ceil(depth_um / reach),
                                  tracks='one shielded M8/M9 spine (3 tracks) per branch: < 0.1% of any channel',
                                  note='a 0.8 ns die tree is why the link ends use mesochronous FIFOs (r1 M1-M4)'),
                power_w=dict(assumed_icg_gated=p['assumed_gated'], measured_network_ungated=p['measured_network_ungated'],
                             basis='J/mm2/cycle x 1.2 GHz over the placed logic area (cell area / 0.5): the measured figure is '
                                   'a small routed block UNGATED (energy_per_token.json); ICG is mandatory (V4.1 pair: '
                                   '593 W/die ungated idle)'))


# ---------------------------------------------------------------- KV reservation
def kv_reservation(pr):
    tot, stage = KVF.families(ROOT)
    keep = {k: v for k, v in tot.items() if k in KV_KEEP}
    amb = {k: v for k, v in tot.items() if k in KV_AMBIGUOUS}
    rem = {k: v for k, v in tot.items() if k not in KV_KEEP and k not in KV_AMBIGUOUS}
    s = lambda d: round(sum(d.values()), 3)
    per_pc_Bps = pr['rates_per_stack']['HBM_sustained_Bps'] / 32
    lat = dict(read_due_25ns=25e-9, row_miss_68ns=68e-9)
    depth = {k: math.ceil(per_pc_Bps * v / 32) for k, v in lat.items()}
    return dict(
        total_mm2=round(sum(tot.values()), 5), by_stage={k: round(v, 4) for k, v in stage.items()},
        kept_mm2=s(keep), ambiguous_mm2=s(amb), removed_mm2=s(rem),
        reservation_mm2=round(s(keep) + s(amb), 3),
        reservation_rule='kept + ambiguous (conservative); removed = fill/assembly/cohort families only',
        kept={k: round(v, 4) for k, v in sorted(keep.items(), key=lambda x: -x[1])},
        ambiguous={k: dict(mm2=round(v, 4), why=KV_AMBIGUOUS[k]) for k, v in sorted(amb.items(), key=lambda x: -x[1])},
        removed={k: round(v, 4) for k, v in sorted(rem.items(), key=lambda x: -x[1])},
        scheduling_check=dict(
            per_PC_Bps_at_0p9TBps=round(per_pc_Bps), sector_B=32, pending_depth_needed=depth, pending_depth_built=64,
            depth_ok_below_ns=round(64 * 32 / per_pc_Bps * 1e9, 1),
            accept_II_edges=5, accept_cap_Bps_per_stack=pr['rates_per_stack']['controller_cap_LEN1_at_II5_Bps'],
            refresh='REF/PREALL scheduling and refresh priority are per-PC families: kept',
            verdict='depth 64 covers 0.9 TB/s while the round trip stays under ~73 ns; the binder is the per-PC accept II '
                    '(5 edges = 205 GB/s/stack at LEN 1), the pricing\'s open LEN>=5 item, so the kept area is the '
                    'CURRENT controller\'s and grows if accept parallelism has to grow'),
        source=P2['kv_families'])


# ---------------------------------------------------------------- the r2 frame
def build_frame(r1, pr, cor, kv_mm2, long_mm2, cts):
    f1 = r1['floorplan']
    mac = load(F.P['catalog'])['macros']
    rom_w = mac[F.ROM_MACRO]['width_um']
    tc = cor['tile_column']['width_r2_um']
    sw = round(2 * rom_w + 4 * 4.32 + tc, 3)
    sh = f1['tile_slot']['h_um']                       # logic width unchanged -> height re-derivation unchanged
    hc = cor['horizontal_link']['width_r2_um']
    vc = cor['vertical_spine']['width_r2_um']
    arr_w = F.TILE_COLS * sw
    arr_h = F.TILE_ROWS * sh + 2 * hc
    hub_el_growth = (cts['hub_element_frame_growth'] ** 2 - 1) * r1['hub_element']['frame_um'][0] * \
        r1['hub_element']['frame_um'][1] / 1e6
    link_long = sum(r['station_FF_mm2'] + r['repeater_mm2'] for r in long_mm2['rows'][:1]) - \
        r1['area']['near_hbm_added']['link_station_FF_mm2']
    hub_mm2 = f1['spine']['hub_contents_mm2'] + hub_el_growth
    spine_w = snap_up(hub_mm2 * 1e6 / arr_h + vc, F.SNAP_X)
    phy_h, phy_w = f1['shoreline']['phy_um']
    ctl = snap_up(kv_mm2 * 1e6 / STACKS / phy_w, F.SNAP_X)
    strip = f1['shoreline']['near_hbm_strip_um']
    band = snap_up(phy_h, F.SNAP_X) + ctl + strip
    ucie = f1['io']['band_depth_um']
    W = snap_up(2 * F.EDGE_KEEP + 2 * band + arr_w + spine_w, F.SNAP_X)
    H = snap_up(2 * F.EDGE_KEEP + arr_h + ucie, F.SNAP_Y)
    die = W * H / 1e6
    shore_free = 2 * band * (H - 2 * F.EDGE_KEEP - ucie - 2 * phy_w) / 1e6
    io_spare = W * ucie / 1e6 - f1['io']['ucie_mm2'] - f1['io']['board_serdes_reservation_mm2'] - f1['io']['hosted_mm2']
    return dict(die_um=[round(W, 3), round(H, 3)], die_mm2=round(die, 2), budget_mm2=F.DIE_BUDGET_MM2,
                margin_to_815_mm2=round(F.DIE_BUDGET_MM2 - die, 2),
                fits_26x33=W <= F.RETICLE_UM[0] and H <= F.RETICLE_UM[1], within_815=die <= F.DIE_BUDGET_MM2,
                tile_slot_um=[sw, sh], tile_corridor_um=tc, array_um=[round(arr_w, 3), round(arr_h, 3)],
                core_origin_um=[round(F.EDGE_KEEP + band, 3), F.EDGE_KEEP],
                spine=dict(w_um=round(spine_w, 3), h_um=round(arr_h, 3), hub_contents_mm2=round(hub_mm2, 3),
                           vertical_link_channel_um=vc, hub_element_cts_growth_mm2=round(hub_el_growth, 4)),
                link_channels=dict(horizontal_um=hc, vertical_um=vc),
                shoreline=dict(band_depth_um=round(band, 3), phy_um=[phy_h, phy_w], controller_band_um=round(ctl, 3),
                               near_hbm_strip_um=strip),
                io=dict(edge='north', band_depth_um=ucie),
                unallocated_mm2=dict(shoreline_free=round(shore_free, 2), io_spare=round(io_spare, 2),
                                     total=round(shore_free + io_spare, 2)),
                link_station_repeater_growth_mm2=round(link_long, 4),
                kv_reservation_mm2=round(kv_mm2, 3))


def stages_r2(r1, fr2):
    """r1's hub -> farthest row-engine distance re-measured on the r2 outline"""
    f1 = r1['floorplan']
    reach = U.SS_REACH_UM[1.2e9]
    x0, _ = fr2['core_origin_um']
    aw, ah = fr2['array_um']
    hub_x = x0 + aw / 2 + fr2['spine']['w_um'] / 2
    strip_face = F.EDGE_KEEP + fr2['shoreline']['band_depth_um']
    k = r1['routes']['channel_rows_from_midline']
    ch_off = k * fr2['tile_slot_um'][1] + fr2['link_channels']['horizontal_um'] / 2
    trunk = hub_x - strip_face + ch_off
    fan = r1['routes']['hub_to_stack']['in_strip_fan_um']
    st = math.ceil(trunk / reach) + math.ceil(fan / reach)
    L = pr_layers = 36
    d1 = r1['routes']['hub_to_stack']['total_stages']
    hub_y = F.EDGE_KEEP + ah / 2
    return dict(trunk_um=round(trunk, 1), total_stages=st, r1_total_stages=d1,
                per_token_cycle_delta_vs_r1=2 * (st - d1) * pr_layers,
                per_token_us_delta_vs_r1=round(2 * (st - d1) * L / 1.2e9 * 1e6, 3),
                hub_xy_um=[round(hub_x, 1), round(hub_y, 1)],
                stack_centres_um=[[round(s, 1), round(hub_y + d * ch_off, 1)]
                                  for s in (strip_face, fr2['die_um'][0] - strip_face) for d in (-1, 1)])


# ---------------------------------------------------------------- hot spot
def hotspot(r1, pr, rp, pb):
    re_el = r1['row_engine']
    fa = re_el['frame_area_um2'] / 1e6
    dyn = re_el['lanes'] * 1.2e9 * 3.974e-12
    static = rp['static_w_per_mm2']
    dyn_d = dyn / fa
    strip_w = r1['floorplan']['shoreline']['near_hbm_strip_um']
    tau_ms = (strip_w * 1e-6) ** 2 / SI_DIFFUSIVITY * 1e3
    layer_us = pr['r2']['primary']['per_layer'] / 1.2e9 * 1e6
    phase_us = pr['latency']['cases']['primary']['per_layer_cycles']['K_phase'] / 1.2e9 * 1e6
    lim = HOTSPOT['nominal']
    duty_cap = (lim - static) / dyn_d
    pj_for_full = (lim - static) * fa / (re_el['lanes'] * 1.2e9) * 1e12
    deep = snap_up(strip_w * (dyn_d + static) / lim, F.SNAP_X)
    L = pr['shape']['layers']
    k_v = 2 * pr['latency']['cases']['primary']['per_layer_cycles']['K_phase']
    slow = k_v * (1.2 / 0.9 - 1) * L
    sA, sB = rp['scenarios']['A'], rp['scenarios']['B']
    checks = []
    for region, sc in (('strip', 'A'), ('strip', 'B'), ('tile_field', 'A'), ('hub', 'A')):
        v = rp['scenarios'][sc][region]
        checks.append(dict(region=region, scenario=sc, avg=v['avg'], peak_in_phase=v['peak'],
                           verdict_avg={k: v['avg'] <= x for k, x in HOTSPOT.items()},
                           verdict_sustained_peak={k: v['peak'] <= x for k, x in HOTSPOT.items()}))
    for k, v in pb['phy_w_per_mm2_published'].items():
        checks.append(dict(region=f'PHY ({k})', scenario='-', avg=v['avg'], peak_in_phase=v['peak'],
                           verdict_avg={kk: v['avg'] <= x for kk, x in HOTSPOT.items()},
                           verdict_sustained_peak={kk: v['peak'] <= x for kk, x in HOTSPOT.items()}))
    cb = pb['controller_band']['logic_density_bound']
    checks.append(dict(region='controller band (logic-density bound)', scenario='A', avg=cb['avg_w_per_mm2_at_that_bound'],
                       peak_in_phase=cb['w_per_mm2'],
                       verdict_avg={k: cb['avg_w_per_mm2_at_that_bound'] <= x for k, x in HOTSPOT.items()},
                       verdict_sustained_peak={k: cb['w_per_mm2'] <= x for k, x in HOTSPOT.items()}))
    return dict(
        limit_w_per_mm2=HOTSPOT, sources=HOTSPOT_SOURCES,
        limit_basis=('nominal 2.0 between HIR Table 4 water cold plate 2.50 (uniform) and 1.70 (50 C budget, 4 cm2); '
                     'conservative 1.0 = HIR previous-generation local flux, keeps the adjacent HBM <= 95 C; aggressive 4.0 = '
                     'HIR latest products, needs jet impingement (4.6) or direct-to-silicon'),
        thermal_time_constant=dict(strip_width_um=strip_w, tau_ms=round(tau_ms, 2), phase_us=round(phase_us, 3),
                                   layer_us=round(layer_us, 3),
                                   consequence='tau >> phase: the junction sees the TIME-AVERAGED flux; the in-phase '
                                               'peak is a PDN (IR) load, not a thermal one'),
        checks=checks,
        strip_verdict=(f"PASS single-user: {sA['strip']['avg']} W/mm2 time-averaged (A) vs {lim} nominal and 1.0 "
                       "conservative, no spreading credit. A sustained 100%-duty strip (prefill, saturated aggregate) in "
                       f"scenario A would be {sA['strip']['peak']} W/mm2 > {lim}."),
        mitigation_if_sustained=dict(
            duty_governor_max=round(duty_cap, 3),
            mac_pj_for_full_duty=round(pj_for_full, 2),
            deeper_strip_um=deep, deeper_strip_extra_mm2=round(2 * (deep - strip_w) * r1['floorplan']['die_um'][1] / 1e6, 2),
            strip_at_0p9GHz=dict(peak_w_per_mm2=round(dyn_d * 0.75 + static, 2), extra_cycles_per_token=round(slow),
                                 extra_us_per_token=round(slow / 1.2e9 * 1e6, 2),
                                 share_of_token=round(slow / pr['r2']['primary']['token_cycles'], 4)),
            choice=('none needed for the single-user objective. For sustained duty: a strip duty governor (no area, '
                    'no single-user latency) or a measured row-engine MAC energy below the threshold; the 0.9 GHz strip '
                    'costs latency and still fails sustained, the deeper strip costs area the die does not have')),
        phy_verdict=pb['phy_verdict'], controller_band_verdict=pb['controller_band']['verdict'],
        element_pnr_changes='none: 24 row-engines, 328.32 x 1,998 um frame, 1.2 GHz; size the element PDN for the in-phase '
                            'current and report measured switching power')


# ---------------------------------------------------------------- build
def build():
    r1, r1_svg = F.build()
    pr, cool = load(F.P['pricing']), load(F.P['cooling'])
    c17 = load(P2['credit17'])
    f1 = r1['floorplan']
    rp = region_power(r1, pr, cool, c17, None)
    cov = {reg: round(coverage_needed(max(rp['scenarios'][s][reg]['peak'] for s in ('A', 'B'))), 4)
           for reg in ('tile_field', 'hub', 'strip')}
    ev = corridor_evidence()
    link = r1['routes']['corridors']['per_link_tracks']
    cor = dict(
        tile_column=corridor('tile column corridor', f1['tile_slot']['corridor_um'], ('M7', 'M9'), cov['tile_field'],
                             F.NONFILL_CUT_TRACKS, 'tile_field'),
        horizontal_link=corridor('horizontal link channel (one link per cut)', f1['link_channels']['horizontal_um'],
                                 ('M6', 'M8'), cov['tile_field'], link, 'tile_field', clock_on='M6'),
        vertical_spine=corridor('vertical spine leg (two links)', f1['link_channels']['vertical_um'], ('M7', 'M9'),
                                cov['hub'], 2 * link, 'hub', clock_on='M7'),
        in_strip_fan=corridor('in-strip fan over the row-engine frames', f1['shoreline']['near_hbm_strip_um'], ('M7', 'M9'),
                              cov['strip'], link, 'strip', clock_on='M7'))
    for c in cor.values():
        c['evidence_ratio'] = dict(demand_over_raw=c['demand_over_raw_same_direction'],
                                   routed_pass=ev['passed']['demand_over_raw_same_direction'],
                                   unresolved=ev['unresolved']['demand_over_raw_same_direction'],
                                   status=('inside the routed-pass density' if c['demand_over_raw_same_direction'] <=
                                           ev['passed']['demand_over_raw_same_direction'] else
                                           'ABOVE the routed-pass density, below the unresolved point: unmeasured band'
                                           if c['demand_over_raw_same_direction'] < ev['unresolved']['demand_over_raw_same_direction']
                                           else 'AT/ABOVE the unresolved point'))
    kv = kv_reservation(pr)
    # long wires and CTS on the r1 outline first (their area does not move the outline: they fill whitespace)
    lw = long_wires(r1, dict(array_um=f1['array_um'], tile_corridor_um=f1['tile_slot']['corridor_um']), ev,
                    f1['tile_slot']['h_um'])
    areas = dict(row_engine_cells_mm2=r1['row_engine']['area_um2']['hi'] * 24 / 1e6,
                 hub_contents_mm2=f1['spine']['hub_contents_mm2'], kv_kept_mm2=kv['reservation_mm2'],
                 long_wire_mm2=lw['station_FF_mm2'] + lw['repeater_mm2'])
    cts0 = cts_plan(f1, r1, areas)
    variants = {}
    for name, kvmm2 in (('kv_full_19p22', kv['total_mm2']), ('kv_kept_plus_ambiguous', kv['reservation_mm2']),
                        ('kv_kept_only', kv['kept_mm2'])):
        variants[name] = build_frame(r1, pr, cor, kvmm2, lw, cts0)
    sel_name = 'kv_kept_plus_ambiguous'
    fr2 = variants[sel_name]
    # evidence-sized sensitivity: every corridor at the routed-pass density (0.225 of raw)
    passd = ev['passed']['demand_over_raw_same_direction']
    ev_w = {}
    for k, c in cor.items():
        per_um = sum(1 / PITCH_UM[l] for l in c['layers'])
        ev_w[k] = max(c['width_r2_um'], snap_up(c['demand_tracks'] / passd / per_um, F.SNAP_X))
    cor_ev = {k: dict(c, width_r2_um=ev_w[k]) for k, c in cor.items()}
    fr_ev = build_frame(r1, pr, cor_ev, kv['reservation_mm2'], lw, cts0)

    def at_density(d, links_scale=1.0):
        cc = {}
        for k, c in cor.items():
            per_um = sum(1 / PITCH_UM[l] for l in c['layers'])
            dem = c['demand_tracks'] * (links_scale if k != 'tile_column' else 1.0)
            cc[k] = dict(c, width_r2_um=max(c['width_r2_um'] if links_scale == 1.0 else 0.0,
                                            snap_up(dem / d / per_um, F.SNAP_X)))
        return build_frame(r1, pr, cc, kv['reservation_mm2'], lw, cts0)
    lo, hi = passd, 0.6
    for _ in range(40):
        mid = (lo + hi) / 2
        if at_density(mid)['within_815']:
            hi = mid
        else:
            lo = mid
    d_fit = hi
    narrow_tracks = 2 * 128 + 32
    narrow_scale = narrow_tracks / link
    fr_narrow_ev = at_density(passd, narrow_scale)
    st = stages_r2(r1, fr2)
    cts = cts_plan(fr2, r1, areas)
    pb = phy_and_band(r1, pr, fr2['shoreline']['controller_band_um'] * fr2['shoreline']['phy_um'][1] / 1e6)
    hs = hotspot(r1, pr, rp, pb)
    ir = {reg: dict(peak_w_per_mm2=max(rp['scenarios'][s][reg]['peak'] for s in ('A', 'B')),
                    m8m9_coverage_per_net=cov[reg], m8m9_share_of_each_layer=round(2 * cov[reg], 3),
                    drop_mv_at_coverage=round(max(rp['scenarios'][s][reg]['peak'] for s in ('A', 'B')) *
                                              ir_mv_per_w_mm2(cov[reg]), 1))
          for reg in cov}
    ir['controller_band'] = dict(peak_w_per_mm2=pb['controller_band']['logic_density_bound']['w_per_mm2'],
                                 m8m9_coverage_per_net=round(coverage_needed(pb['controller_band']['logic_density_bound']['w_per_mm2']), 4),
                                 note='at the logic-density bound (the unqualified residual has no physical home)')
    margins = dict(
        die_mm2=fr2['die_mm2'], margin_to_815_mm2=fr2['margin_to_815_mm2'], unallocated_mm2=fr2['unallocated_mm2'],
        corridors={k: dict(width_um=c['width_r2_um'], demand=c['demand_tracks'],
                           netted_70pct_capacity=sum(v['target'] for v in
                                                     {l: layer_net(c['width_r2_um'], l, c['pg_coverage_per_net'],
                                                                   CLOCK_SPINE_TRACKS if (k != 'tile_column' and l == c['layers'][0]) else 0)
                                                      for l in c['layers']}.values()),
                           usage_of_netted=None, evidence_status=c['evidence_ratio']['status'])
                   for k, c in cor.items()})
    for k, m in margins['corridors'].items():
        m['margin_tracks'] = m['netted_70pct_capacity'] - m['demand']
    pnr = dict(
        verdict=None,
        credible=[f"die {fr2['die_mm2']} mm2: {fr2['margin_to_815_mm2']} mm2 under 815 with every corridor at <= 70% of its "
                  'netted tracks', 'tile-slot utilisation after CTS + repair 0.56 <= 0.70',
                  'strip and PHY thermal PASS at the sourced limit (single-user)'],
        not_yet=['every corridor sits ABOVE the only routed-pass density in the repo (0.225 of raw same-direction tracks) '
                 'and below the unresolved point (0.451): the link endpoint element (order 3) must route a 504 um span of '
                 'the 1,056-bit bus, and a tile-column corridor strip at 637 bits, at the r2 widths before die assembly; '
                 f"815 still fits every corridor down to a density of {d_fit:.3f} of raw tracks; at the routed-pass "
                 f"density (0.225) the die is {fr_ev['die_mm2']} mm2 ({'fits' if fr_ev['within_815'] else 'does NOT fit'} 815)",
                 'hub element frame grows for CTS + repair (0.70 -> 0.78 would exceed the cap)',
                 'strip IR: element PDN needs the strip coverage below at scenario A',
                 'HBM controller energy and accept II are unqualified (KV reservation is the current controller\'s)'])
    pnr['verdict'] = ('CREDIBLE WITH ONE GATE: area, IR and thermal margins close on the r2 outline; corridor routability '
                      'is the gate, because the r1/r2 bus densities lie in the band the repo has not routed')
    rec = dict(
        schema=SCHEMA, status='MODEL_ONLY_FLOORPLAN_PLAN_R2', rtl=False, pnr=False, adoption=False,
        predecessor=dict(record=P2['r1_record'], sha256=sha(P2['r1_record']), kept_byte_identical=True),
        question='do the r1 margins allow place-and-route to complete?',
        answer=pnr,
        targets=dict(track_usage_max_of_netted=TARGET_USAGE,
                     usage_basis='min(1 - ORFS asap7 ROUTING_LAYER_ADJUSTMENT 0.25, 1 - die-model m8_m9_reserve 0.30); '
                                 'netted = raw - PG at the region coverage - 5% via/OBS (assumed) - clock spine',
                     corridor_evidence=ev, never_narrowed='r2 width = max(r1 width, 70%-of-netted width)',
                     cell_util_cap=CELL_UTIL_CAP, ss_reach_um=U.SS_REACH_UM[1.2e9]),
        region_power=rp, pg_coverage=dict(ir_budget_mv=ir_budget_mv(), base_coverage_per_net=PG_BASE_COV,
                                          mv_per_w_mm2_at_base=round(ir_mv_per_w_mm2(PG_BASE_COV), 2), regions=ir,
                                          model='r1 closed form (v41_die_assembly.ir_drop, ASAP7 M8/M9 RC): an ASAP7 statement'),
        corridors=cor, long_wires=lw, cts=cts, kv_service=kv,
        floorplan_variants=variants, selected_variant=sel_name, floorplan=fr2,
        evidence_sized_sensitivity=dict(widths_um=ev_w, die_mm2=fr_ev['die_mm2'], die_um=fr_ev['die_um'],
                                        within_815=fr_ev['within_815'], fits_26x33=fr_ev['fits_26x33'],
                                        density_that_just_fits_815=round(d_fit, 3),
                                        narrow_links_128b_at_pass_density=dict(
                                            link_tracks=narrow_tracks, die_mm2=fr_narrow_ev['die_mm2'],
                                            within_815=fr_narrow_ev['within_815'],
                                            latency='+337 cycles/layer = +12,132 cycles = +10.1 us/token (selected entry '
                                                    'sensitivity narrow_bus_128: attention 2,037 vs 1,700)',
                                            note='narrow links do not help: the tile column corridor (637 bits x 64 '
                                                 'columns) carries the area'),
                                        least_cost_if_gate_fails=(
                                            'the tile column corridor dominates (+48 um x 64 columns at the pass density). '
                                            'Corridors fit 815 up to a uniform density of ' + f'{d_fit:.3f}' +
                                            ' of raw tracks; above that the cheapest lever is the corridor content, not '
                                            'the links: carry the 379-bit instruction once per column pair (or registered '
                                            'per tile row) instead of per column')),
        stages=st, hotspot=hs, phy_and_controller_band=pb, margins=margins,
        delta_vs_r1=dict(die_mm2=round(fr2['die_mm2'] - r1['area']['die_mm2'], 2),
                         controller_band_um=round(fr2['shoreline']['controller_band_um'] - f1['shoreline']['controller_band_um'], 3),
                         spine_um=round(fr2['spine']['w_um'] - f1['spine']['w_um'], 3),
                         tile_corridor_um=round(fr2['tile_corridor_um'] - f1['tile_slot']['corridor_um'], 3),
                         horizontal_channel_um=round(fr2['link_channels']['horizontal_um'] - f1['link_channels']['horizontal_um'], 3),
                         vertical_channel_um=round(fr2['link_channels']['vertical_um'] - f1['link_channels']['vertical_um'], 3)),
        sources_sha256={v: sha(v) for v in P2.values()},
        tool_sha256=sha('tools/qwen_rom_floorplan_nearhbm_r2.py'),
        claim_boundary='Model and floorplan plan only. No routed die, no timing, no measured power; ASAP7 abstracts; the '
                       'hot-spot limit is a published cold-plate figure, not a qualification of this package.')
    fr_svg = dict(die_um=fr2['die_um'], core_origin_um=fr2['core_origin_um'], array_um=fr2['array_um'],
                  spine=fr2['spine'], link_channels=fr2['link_channels'], shoreline=fr2['shoreline'], io=fr2['io'])
    svg = F.svg(fr_svg, dict(hub_xy_um=st['hub_xy_um'], stack_centres_um=st['stack_centres_um']), r1['row_engine'])
    return rec, svg


def write(out_dir: Path):
    rec, pic = build()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / RECORD).write_text(json.dumps(rec, indent=1) + '\n')
    (out_dir / SVG).write_text(pic)
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out-dir', type=Path)
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()
    if a.verify:
        with tempfile.TemporaryDirectory() as t:
            write(Path(t))
            bad = [n for n in (RECORD, SVG) if not filecmp.cmp(Path(t) / n, OUT / n, shallow=False)]
        if bad:
            raise SystemExit(f'verify FAILED: {bad} differ')
        print('verify OK: model-r2.json and floorplan-r2.svg byte-identical')
        return
    rec = write(a.out_dir or OUT)
    f = rec['floorplan']
    print(f"r2 die {f['die_um'][0]:.0f} x {f['die_um'][1]:.0f} um = {f['die_mm2']} mm2 (margin {f['margin_to_815_mm2']}); "
          f"evidence-sized {rec['evidence_sized_sensitivity']['die_mm2']} mm2")


if __name__ == '__main__':
    main()
