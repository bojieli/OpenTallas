#!/usr/bin/env python3
"""Qwen ROM async collective: in-context physical evidence for ot_qwen_tp_seq_async_w12.

Three subcommands:

  sta     per-corner OpenSTA on a routed run_abi3_physical workdir (6_final.odb + RCX 6_final.spef):
          SS setup and FF hold, separately (one liberty corner per run), plus the worst paths that start
          at the ME-tap source registers (i_me_*) and that end in the scoreboard (seq lw).
              python3 tools/qwen_async_seq_incontext_physical.py sta --workdir W --nickname N --out sta.json
  hub     the hub routing-layer check of the 48-port ME-write tap on the Qwen ROM full-die floorplan
          (claude/qwen-rom-fulldie-20261003 placements, r2 netting rule, corridor-gate routed ratios).
              python3 tools/qwen_async_seq_incontext_physical.py hub --sta-a1 sta_a1.json --out hub.json
  summary A/B verdict from the two route records and their per-corner STA.
              python3 tools/qwen_async_seq_incontext_physical.py summary --dir D --out verdict.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERIOD_NS, UNC_SETUP_NS, UNC_HOLD_NS = 0.833333, 0.060, 0.025

STA_TCL = r'''
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(QA_LIBTAG)_*.lib*]] { read_liberty $f }
read_db $::env(QA_ODB)
read_sdc $::env(QA_SDC)
read_spef $::env(QA_SPEF)
set_propagated_clock [all_clocks]
report_units
puts "QASTA setup"; report_worst_slack -max -digits 4
puts "QASTA hold";  report_worst_slack -min -digits 4
puts "QASTA tns";   report_tns -digits 4
set nv 0; set nh 0; set eps [all_registers -data_pins]
foreach p $eps {
  set s [get_property $p slack_max]; if {$s != "INF" && $s < 0} { incr nv }
  set s [get_property $p slack_min]; if {$s != "INF" && $s < 0} { incr nh }
}
puts "QASTA failing setup $nv hold $nh of [llength $eps]"
puts "QASTA path worst_setup"
report_checks -path_delay max -group_path_count 1 -format full_clock_expanded -digits 4
puts "QASTA path worst_hold"
report_checks -path_delay min -group_path_count 1 -format full_clock_expanded -digits 4
set tap [get_cells -quiet -hierarchical *i_me_*]
puts "QASTA tap_sources [llength $tap]"
if {[llength $tap]} {
  puts "QASTA path tap_setup"
  report_checks -from $tap -path_delay max -group_path_count 1 -format full_clock_expanded -digits 4
  puts "QASTA path tap_hold"
  report_checks -from $tap -path_delay min -group_path_count 1 -format full_clock_expanded -digits 4
}
set lw [get_cells -quiet -hierarchical *lw*]
puts "QASTA lw_cells [llength $lw]"
puts "QASTA end"
'''


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def slack_of(block: str):
    m = re.search(r'(-?[0-9.]+)\s+slack \((?:MET|VIOLATED)\)', block)
    return float(m.group(1)) if m else None


def cmd_sta(a):
    work = Path(a.workdir).resolve()
    hits = sorted(work.rglob(f'results/asap7/{a.nickname}/base'))
    if not hits:
        raise SystemExit(f'no results/asap7/{a.nickname}/base under {work}')
    res = hits[0]
    mount = res.parents[3]
    odb, sdc, spef = res / '6_final.odb', res / '6_final.sdc', res / '6_final.spef'
    missing = [p.name for p in (odb, sdc, spef) if not p.is_file()]
    if missing:
        raise SystemExit(f'missing final artifacts {missing}')
    (mount / 'qa_sta.tcl').write_text(STA_TCL)
    rel = lambda p: '/work/' + str(p.relative_to(mount))
    out = dict(schema='opentallas.qwen-async-seq.corner-sta.v1', workdir=str(work), nickname=a.nickname,
               basis='OpenSTA on 6_final.odb + RCX 6_final.spef, one ASAP7 RVT liberty corner per run, '
                     'propagated clocks; uncertainties from the routed SDC (60 ps setup / 25 ps hold)',
               artifacts_sha256={p.name: sha(p) for p in (odb, sdc, spef)}, sdc_text=sdc.read_text()[:4000],
               corners={})
    for corner, tag in (('ss', 'SS'), ('ff', 'FF')):
        c = ['docker', 'run', '--rm', '-v', f'{mount}:/work', '-e', f'QA_LIBTAG={tag}', '-e', f'QA_ODB={rel(odb)}',
             '-e', f'QA_SDC={rel(sdc)}', '-e', f'QA_SPEF={rel(spef)}', 'openroad/orfs:latest', 'bash', '-lc',
             'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /work/qa_sta.tcl']
        p = subprocess.run(c, capture_output=True, text=True)
        log = p.stdout + p.stderr
        (work / f'qa_sta_{corner}.log').write_text(log)
        tu = re.search(r'time\s+1(\S*)s', log)
        scale = {'p': 1e-3, 'n': 1.0}.get(tu.group(1) if tu else 'p', 1e-3)
        r = dict(exit=p.returncode)
        for k in ('setup', 'hold'):
            m = re.search(rf'QASTA {k}\s+worst slack (?:max|min) (\S+)', log)
            r[f'{k}_wns_ns'] = round(float(m.group(1)) * scale, 5) if m else None
        m = re.search(r'QASTA tns\s+tns (?:max )?(\S+)', log)
        r['setup_tns_ns'] = round(float(m.group(1)) * scale, 5) if m else None
        m = re.search(r'QASTA failing setup (\d+) hold (\d+) of (\d+)', log)
        if m:
            r.update(failing_setup_endpoints=int(m.group(1)), failing_hold_endpoints=int(m.group(2)),
                     endpoints=int(m.group(3)))
        m = re.search(r'QASTA tap_sources (\d+)', log)
        r['tap_source_cells'] = int(m.group(1)) if m else None
        m = re.search(r'QASTA lw_cells (\d+)', log)
        r['lw_cells'] = int(m.group(1)) if m else None
        sections = re.split(r'QASTA path (\w+)\n', log)
        for i in range(1, len(sections) - 1, 2):
            name, body = sections[i], sections[i + 1].split('QASTA ')[0]
            s = slack_of(body)
            r[f'{name}_slack_ns'] = round(s * scale, 5) if s is not None else None
            sp = re.search(r'Startpoint: (\S+)', body)
            ep = re.search(r'Endpoint: (\S+)', body)
            r[f'{name}_path'] = dict(start=sp.group(1) if sp else None, end=ep.group(1) if ep else None)
        out['corners'][corner] = r
    ss, ff = out['corners']['ss'], out['corners']['ff']
    out['signoff'] = dict(ss_setup_met=ss.get('setup_wns_ns') is not None and ss['setup_wns_ns'] >= 0,
                          ff_hold_met=ff.get('hold_wns_ns') is not None and ff['hold_wns_ns'] >= 0)
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: out['corners'][k] for k in out['corners']} | out['signoff'], indent=1)[:3000])


# ------------------------------------------------------------------------------------------------ hub check
FULLDIE = dict(branch='claude/qwen-rom-fulldie-20261003', commit='c3a5675416cf435591a6213a88fe0c5f09956fed',
               files=['results/rtl/qwen_rom_fulldie_20261003/floorplan.json',
                      'results/rtl/qwen_rom_fulldie_20261003/floorplan.def',
                      'results/rtl/qwen_rom_fulldie_20261003/domains.sdc'])
CORRIDOR = dict(branch='claude/qwen-corridor-gate-20261003', commit='89e70dd784164f267f4679c108796f2f3148fac1',
                files=['tools/qwen_rom_floorplan_nearhbm_r2.py', 'results/rtl/qwen_corridor_gate_20261003/README.md'])
# full-die DEF placements (um) and column width; floorplan.json geometry
PLACE = dict(sp_tree_top=(11466.144, 15826.32), sp_vector_memory=(11466.144, 14031.36),
             hub_el=(11578.464, 15413.76), sp_constants_sequencer=(12165.12, 17966.88))
CW_UM, X_VCH, VCH_UM = 524.88, 11991.024, 174.096
MM2 = dict(sp_tree_top=2.3979, sp_vector_memory=0.7256, sp_constants_sequencer=2.1575)   # placed_mm2
# r2 netting rule (tools/qwen_rom_floorplan_nearhbm_r2.py) and ASAP7 pitches
PITCH_UM = {'M4': 0.048, 'M5': 0.048, 'M6': 0.064, 'M7': 0.064, 'M8': 0.080, 'M9': 0.080}
TARGET_USAGE, VIA_OBS, PG_PITCH_UM, HUB_PG_COV, M6_STRAP = 0.70, 0.05, 40.0, 0.025, (0.288, 10.8)
ROUTED_PASS_RATIO, ROUTED_CLEAN_MAX_RATIO = 0.225, 0.546   # corridor gate: earliest routed bus / densest clean
WIRE_OVERHEAD_PS, WIRE_PS_PER_UM, REACH_UM = 261.0, 1.135, 504.0   # W15 SS segment sweep (ss-wire-reach)


def layer_net(width_um, layer, cov):
    raw = math.floor(width_um / PITCH_UM[layer] + 1e-8)
    if layer in ('M8', 'M9'):
        f_pg = 2 * cov + 2 * 2 * PITCH_UM[layer] / PG_PITCH_UM
    elif layer == 'M6':
        f_pg = 2 * (M6_STRAP[0] + PITCH_UM['M6']) / M6_STRAP[1]
    else:
        f_pg = 0.0
    pg, via = math.ceil(raw * f_pg), math.ceil(raw * VIA_OBS)
    net = raw - pg - via
    return dict(raw=raw, pg=pg, via_obs=via, netted=net, target=math.floor(TARGET_USAGE * net))


def cmd_hub(a):
    NP, MAW, MASK = 48, 24, 16
    tap = NP * (1 + MAW + MASK)
    me_write_bus = NP * (1 + MAW + MASK + 512)        # the existing ME result-write bus to the VM (unmodelled in the die)
    # baseline sequencer buses to VM / collective / core, already present wherever the sequencer sits
    seq_base = 1 + 8 + 512 + 1 + 8 + 512 + 1 + 1 + 512 + 1 + 1 + 32 + 1 + 512 + 1 + 2 + 1
    h = {k: MM2[k] * 1e6 / CW_UM for k in MM2}
    tt_y0, tt_y1 = PLACE['sp_tree_top'][1], PLACE['sp_tree_top'][1] + h['sp_tree_top']
    cs_y0, cs_y1 = PLACE['sp_constants_sequencer'][1], PLACE['sp_constants_sequencer'][1] + h['sp_constants_sequencer']
    ov0, ov1 = max(tt_y0, cs_y0), min(tt_y1, cs_y1)
    window = ov1 - ov0
    # placement P1 (the baseline sequencer slab): the tap leaves tree_top's east face, crosses the vertical link
    # channel horizontally (M6/M8; the channel's M7/M9 carry the links), enters the sequencer slab's west face
    per = {l: layer_net(window, l, HUB_PG_COV) for l in ('M6', 'M8')}
    raw = sum(v['raw'] for v in per.values())
    target = sum(v['target'] for v in per.values())
    demand = tap + seq_base
    raw_per_um = sum(1 / PITCH_UM[l] for l in ('M6', 'M8'))
    band_conservative = demand / (ROUTED_PASS_RATIO * raw_per_um)
    band_clean = demand / (ROUTED_CLEAN_MAX_RATIO * raw_per_um)
    hop_um = VCH_UM
    p1 = dict(
        path='tree_top east face (x %.1f) -> vertical link channel (%.1f um, M7/M9 links) -> constants_sequencer '
             'west face (x %.1f); horizontal layers M6/M8 (corridor-gate layer rule)' %
             (X_VCH, VCH_UM, PLACE['sp_constants_sequencer'][0]),
        y_overlap_um=[round(ov0, 1), round(ov1, 1)], window_um=round(window, 1),
        capacity_per_layer=per, raw_tracks=raw, netted_target_tracks=target,
        modelled_existing_demand_in_window=0,
        modelled_existing_note='floorplan.json bus list: the horizontal links cross the channel at y 9,063 and '
                               '22,077 only; x3 / attn_ret are inside the west column',
        demand=dict(tap=tap, baseline_sequencer_buses_unmodelled=seq_base, total=demand),
        usage_of_netted_target=round(demand / target, 4), demand_over_raw=round(demand / raw, 4),
        band_needed_um_at_routed_pass_0p225=round(band_conservative, 1),
        band_needed_um_at_densest_clean_0p546=round(band_clean, 1),
        fits=demand <= target and band_conservative <= window,
        min_hop_um=hop_um, min_hop_wire_ps=round(WIRE_OVERHEAD_PS + WIRE_PS_PER_UM * hop_um, 1),
        max_source_offset_um_for_one_stage=round(REACH_UM - hop_um, 1))
    # the alternative P2 (sequencer beside the VM, tap riding with the ME->VM write bus across the hub row) is NOT
    # chosen: that cut already carries the 26,544-wire write bus
    row_cut = {l: layer_net(CW_UM, l, HUB_PG_COV) for l in ('M5', 'M7', 'M9')}
    row_raw = sum(v['raw'] for v in row_cut.values())
    p2 = dict(path='tree_top south face -> hub_el row (%.2f um) -> VM north face, vertical layers M5/M7/M9 over the '
                   '%.2f um column' % (PLACE['sp_tree_top'][1] - PLACE['hub_el'][1], CW_UM),
              raw_tracks=row_raw, existing_me_write_bus=me_write_bus,
              existing_over_raw=round(me_write_bus / row_raw, 4), with_tap_over_raw=round((me_write_bus + tap) / row_raw, 4),
              note='the existing ME result-write bus alone is above the densest clean routed ratio (0.546) on this cut: '
                   'a pre-existing full-die gap (the bus is not in the full-die bus list), not created by the tap; the '
                   'tap must not be added to it')
    out = dict(schema='opentallas.qwen-async-seq.hub-route-check.v1',
               question='does the 48-port ME-write observation tap (vw_me_we/addr/mask -> TP sequencer) route in the '
                        'Qwen ROM die hub at the corridor-gate layer rule, and within one SS wire stage?',
               sources=dict(fulldie=FULLDIE, corridor=CORRIDOR,
                            wire='W15 SS segment sweep: 261 ps + 1.135 ps/um, 504 um per stage at 0.833 ns'),
               tap=dict(ports=NP, bits_per_port=dict(we=1, addr=MAW, mask=MASK), wires=tap,
                        source='ME result-write registers (ot_qwen_w12_matvec o_we2/o_addr2/o_mask2) in the tree_top '
                               'result compaction', sink='TP sequencer scoreboard, constants_sequencer slab',
                        domain='stream 1.2 GHz both ends (fulldie tools/qwen_rom_fulldie.py SPINE_BLOCKS)'),
               placement_P1_baseline_slab=p1, placement_P2_rejected=p2)
    if a.sta_a1:
        s = json.loads(Path(a.sta_a1).read_text())['corners']['ss']
        tap_slack = s.get('tap_setup_slack_ns')
        if tap_slack is not None:
            budget_ps = tap_slack * 1000.0
            out['zero_latency_tap'] = dict(
                ss_tap_path_slack_ns=tap_slack,
                basis='routed block: the tap source registers (i_me_*) sit inside the 130 um block; a die wire of '
                      'L um adds 261 + 1.135 L ps only if the hop is NOT a separate register stage',
                extra_wire_allowed_um=round(max(0.0, (budget_ps - WIRE_OVERHEAD_PS) / WIRE_PS_PER_UM), 1)
                if budget_ps > WIRE_OVERHEAD_PS else 0.0,
                needed_um=hop_um,
                feasible=budget_ps >= WIRE_OVERHEAD_PS + WIRE_PS_PER_UM * hop_um)
    tl = out.get('zero_latency_tap', {})
    out['verdict'] = dict(
        routes=p1['fits'],
        timing=('one registered tap stage across the %.0f um hop (%.0f ps of a 773 ps budget); the measured RTL taps '
                'with zero latency, so the physical tap adds 1 cycle to each scoreboard set: sends move <= 1 cycle '
                'later per all-reduce (<= 2 cycles a layer of the 278 saved), never earlier (exactness unchanged)'
                % (hop_um, p1['min_hop_wire_ps'])) if not tl.get('feasible') else
               'zero-latency tap fits the measured SS slack across the hop',
        pass_=bool(p1['fits']))
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out['verdict'] | dict(p1_usage=p1['usage_of_netted_target'], p1_band=p1[
        'band_needed_um_at_routed_pass_0p225'], window=p1['window_um'], p2=p2['with_tap_over_raw']), indent=1))


def cmd_summary(a):
    d = Path(a.dir)
    rows = {}
    for tag in ('a0', 'a1'):
        rec = json.loads((d / f'route_{tag}.json').read_text())
        sta = json.loads((d / f'sta_{tag}.json').read_text())
        pr = rec.get('place_and_route', {}).get('metrics', {})
        ss, ff = sta['corners']['ss'], sta['corners']['ff']
        rows[tag] = dict(
            closed=rec['design'].get('closed'), acceptance=rec['acceptance']['status'],
            stdcell_area_um2=pr.get('standard_cell_area_um2'), stdcells=pr.get('standard_cell_count'),
            routed_fmax_hz=pr.get('fmax_hz'), drc=pr.get('drc_errors'), antenna=pr.get('antenna_violating_nets'),
            slew=pr.get('max_slew_violations'), cap=pr.get('max_cap_violations'), fanout=pr.get('max_fanout_violations'),
            flow_setup_wns_ns=pr.get('setup_wns_ns'), flow_hold_wns_ns=pr.get('hold_wns_ns'),
            ss_setup_wns_ns=ss.get('setup_wns_ns'), ss_setup_tns_ns=ss.get('setup_tns_ns'),
            ss_failing_setup=ss.get('failing_setup_endpoints'), ss_hold_wns_ns=ss.get('hold_wns_ns'),
            ff_hold_wns_ns=ff.get('hold_wns_ns'), ff_failing_hold=ff.get('failing_hold_endpoints'),
            ff_setup_wns_ns=ff.get('setup_wns_ns'),
            ss_worst_setup_path=ss.get('worst_setup_path'), ss_tap_setup_slack_ns=ss.get('tap_setup_slack_ns'),
            ss_tap_setup_path=ss.get('tap_setup_path'), ff_tap_hold_slack_ns=ff.get('tap_hold_slack_ns'))
    a0, a1 = rows['a0'], rows['a1']
    ok = lambda r: (r['ss_setup_wns_ns'] is not None and r['ss_setup_wns_ns'] >= 0 and r['ff_hold_wns_ns'] is not None
                    and r['ff_hold_wns_ns'] >= 0 and not any(r[k] for k in ('drc', 'antenna', 'slew', 'cap', 'fanout')))
    out = dict(schema='opentallas.qwen-async-seq.incontext-ab.v1', rows=rows,
               area_delta_um2=(round(a1['stdcell_area_um2'] - a0['stdcell_area_um2'], 3)
                               if a0['stdcell_area_um2'] and a1['stdcell_area_um2'] else None),
               a0_signoff=ok(a0), a1_signoff=ok(a1),
               ss_wns_delta_ns=(round(a1['ss_setup_wns_ns'] - a0['ss_setup_wns_ns'], 5)
                                if a0['ss_setup_wns_ns'] is not None and a1['ss_setup_wns_ns'] is not None else None))
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out, indent=1)[:4000])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('sta'); s.add_argument('--workdir', required=True); s.add_argument('--nickname', required=True)
    s.add_argument('--out', required=True); s.set_defaults(f=cmd_sta)
    h = sp.add_parser('hub'); h.add_argument('--sta-a1'); h.add_argument('--out', required=True); h.set_defaults(f=cmd_hub)
    m = sp.add_parser('summary'); m.add_argument('--dir', required=True); m.add_argument('--out', required=True)
    m.set_defaults(f=cmd_summary)
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
