#!/usr/bin/env python3
"""HA4 R5a: area, route and SS/FF timing gates of the SRAM-staging successor, and the composition row.

Joins three measured records into one verdict (no number here is estimated):
  --latency   tools/hbm_accel_expert_first_access.py --variant sram record (exact + first access + gain)
  --route     tools/run_abi3_physical.py routed record of ot_hbm_accel_expert_fetch_stream_sram
  --corner    tools/w18/corner_sta.py record of that route (setup SS / hold FF, 60 / 25 ps)
Area: the routed element's macros (64 x ot_sram_1r1w_512x128_m4_r2c2, v2 abstract) and standard cells, its
routed footprint, and the HBM die ledger (tools/uarch_model.py right_size_hbm_die, 4 stacks a die) re-sized
with one element per stack.  The latency gate is the user's 2026-10-04 decision: the 140 ns first-access
figure is a proxy target and its miss does not block adoption; the binding gates are area, route and timing.

    python3 tools/hbm_accel_r5a_gates.py --latency L.json --route P.json --corner C.json \\
        --out results/rtl/hbm_accel_ha4_r5a_gates_20261004/verdict.json --rows-out ROWS.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
COMP = ROOT / 'results/rtl/hbm_accel_composition_20261004/measured_composition.json'
MACRO = 'ot_sram_1r1w_512x128_m4_r2c2'
MACRO_LEF = ROOT / f'physical/asap7_memory_macros_v2/{MACRO}/{MACRO}.lef'
N_MACRO = 64                       # 8 SM x 4 quarter banks x 2 halves (128 b) of 512 words
STACKS_PER_DIE = 4
AR_BASE_US = 442.14                # composition base (W19 ablation token), as tools/hbm_accel_composition.py
GAIN_GATE_PCT = 1.0


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def macro_area_um2():
    w, h = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', MACRO_LEF.read_text()).groups())
    return w, h, w * h


def die_ledger(element_mm2):
    import uarch_model as u
    out = {}
    for model in ('v41', 'qwen'):
        b = u.right_size_hbm_die(model, STACKS_PER_DIE)
        o = u.CONS['overhead']
        bands = b['die_mm2'] * (1 - o) - b['logic_mm2']
        logic = b['logic_mm2'] + STACKS_PER_DIE * element_mm2
        area = (logic + bands) / (1 - o)
        H = area / b['die_w_mm']
        r = u.HBM_SHORE['reticle_mm']
        out[model] = dict(base_die_mm2=b['die_mm2'], base_logic_mm2=b['logic_mm2'],
                          added_logic_mm2=round(STACKS_PER_DIE * element_mm2, 3),
                          die_mm2=round(area, 1), die_w_mm=b['die_w_mm'], die_h_mm=round(H, 2),
                          growth_pct=round(100 * (area / b['die_mm2'] - 1), 3),
                          fits_reticle=bool(max(b['die_w_mm'], H) <= r[1] and min(b['die_w_mm'], H) <= r[0]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--latency', type=Path, required=True)
    ap.add_argument('--route', type=Path, required=True)
    ap.add_argument('--corner', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--rows-out', type=Path, required=True)
    a = ap.parse_args(argv)
    lat = json.loads(a.latency.read_text())
    pnr = json.loads(a.route.read_text())
    cs = json.loads(a.corner.read_text())
    m = pnr['place_and_route']['metrics']
    acc = pnr['acceptance']
    mw, mh, ma = macro_area_um2()
    macros_um2 = N_MACRO * ma
    std_um2 = m['standard_cell_area_um2']
    foot_um2 = m['die_area_um2']
    element_mm2 = foot_um2 / 1e6
    ledger = die_ledger(element_mm2)
    area_pass = all(v['fits_reticle'] for v in ledger.values())
    chk = acc['checks'][-1] if acc.get('checks') else {}
    route_clean = bool(chk.get('physically_clean')) and m.get('drc_errors', chk.get('drc_errors', 1)) == 0
    setup = cs['setup_ss']['worst_slack_ps']
    hold = cs['hold_ff']['worst_slack_ps']
    timing_pass = bool(cs.get('closes_signoff'))
    st = lat['stats']['refpb_notice']
    gain = lat['measured_r5a_gain_us_vs_central']
    pct = round(100 * gain / (AR_BASE_US - gain), 3)
    exact = lat['exact']['verdict'] == 'PASS' and all(n['verdict'] == 'FAIL' for n in lat['negative_controls'])
    gates = dict(exact='PASS' if exact else 'FAIL',
                 latency='PASS',
                 area='PASS' if area_pass else 'FAIL',
                 route='PASS' if route_clean else 'FAIL',
                 timing='PASS' if timing_pass else 'FAIL',
                 gain='PASS' if pct >= GAIN_GATE_PCT else 'FAIL')
    adopt = all(v == 'PASS' for v in gates.values())
    verdict = dict(
        schema='opentallas.hbm_accel.ha4.r5a_gates.v1',
        rung='R5a', element='ot_hbm_accel_expert_fetch_stream_sram',
        inputs={str(p): sha(p) for p in (a.latency, a.route, a.corner)},
        exact=dict(verdict=lat['exact']['verdict'], cases=lat['exact']['cases'],
                   backpressure_cases=lat['exact'].get('backpressure_cases'),
                   sectors_checked_per_case=lat['exact']['sectors_checked_per_case'],
                   negative_controls=lat['negative_controls']),
        latency=dict(first_access_worst_ns=st['max_ns'], mean_ns=st['mean_ns'], min_ns=st['min_ns'],
                     register_array_original_worst_ns=141.475, proxy_target_ns=140.0,
                     sram_cost='+2 clk per line (registered bank write, registered macro read)',
                     decision='proxy miss does not block adoption (user, 2026-10-04); binding gates are area, route, timing'),
        gain=dict(measured_us=gain, modelled_us=13.46, pct_of_rate=pct, base_ar_us=AR_BASE_US),
        area=dict(macro=MACRO, macro_abstract='physical/asap7_memory_macros_v2', macro_w_um=mw, macro_h_um=mh,
                  macros=N_MACRO, macro_um2=round(macros_um2, 1), std_cell_um2=std_um2,
                  sequential_um2=m.get('sequential_area_um2'), routed_core_um2=m.get('core_area_um2'),
                  routed_footprint_um2=foot_um2, staging_bits=N_MACRO * 512 * 128,
                  replaced='8 x 4 x 512 x 256 flops (4,194,304 bits) of the register-array staging',
                  per_die_stacks=STACKS_PER_DIE, die_ledger=ledger, verdict='PASS' if area_pass else 'FAIL'),
        route=dict(status=acc['status'], reason=acc.get('reason'), drc=m.get('drc_errors', chk.get('drc_errors')),
                   antenna=chk.get('antenna_violating_nets'), max_slew=chk.get('max_slew_violations'),
                   max_cap=chk.get('max_cap_violations'), max_fanout=chk.get('max_fanout_violations'),
                   wirelength_um=m.get('wirelength_um', m.get('routed_wirelength_um')),
                   utilization=m.get('utilization_fraction'), verdict='PASS' if route_clean else 'FAIL'),
        timing=dict(setup_ss_wns_ps=setup, setup_ss_tns_ps=cs['setup_ss']['tns_ps'], hold_ff_wns_ps=hold,
                    clocks='clk 0.833 ns (1.2 GHz SM/streaming), hclk 1.024 ns (976.6 MHz CK/2), async groups',
                    uncertainty='60 ps setup / 25 ps hold', verdict='PASS' if timing_pass else 'FAIL'),
        gates=gates,
        verdict='ADOPT' if adopt else 'REJECT',
    )
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(verdict, indent=1) + '\n')
    # composition successor row (latest revision's rows with R5a replaced)
    comp = json.loads(COMP.read_text())
    rows = [dict(r) for r in comp['revisions'][-1]['rows']]
    for r in rows:
        for k in ('diff_us', 'measured_gain_pct_of_rate', 'adopted'):
            r.pop(k, None)
    row = dict(rung='R5a', workstream='HA4', modelled_gain_us=13.46, measured_gain_us=gain,
               diff_cause=(f'SRAM-staging successor: worst first access {st["max_ns"]} ns (register array 141.5; '
                           f'+2 clk per line for the registered macro write/read); gain {gain} vs 13.46 us modelled'),
               gates=gates,
               area=(f'{N_MACRO} x {MACRO} ({macros_um2 / 1e6:.3f} mm2) + {std_um2 / 1e6:.3f} mm2 cells; routed '
                     f'{element_mm2:.3f} mm2/stack; V4.1 die {ledger["v41"]["base_die_mm2"]} -> '
                     f'{ledger["v41"]["die_mm2"]} mm2 ({ledger["v41"]["growth_pct"]}%), fits'),
               route=f'ORFS routed element: {acc["status"]}, DRC {m.get("drc_errors", chk.get("drc_errors"))}',
               timing=f'SS setup WNS {setup} ps / FF hold WNS {hold} ps (60/25 ps), clk 1.2 GHz + hclk 976.6 MHz',
               verdict=verdict['verdict'] + (' (all six gates PASS; 140 ns proxy miss non-blocking by user decision)'
                                             if adopt else ''),
               evidence=['results/rtl/hbm_accel_ha4_r5a_gates_20261004/verdict.json',
                         'results/rtl/hbm_accel_ha4_r5a_gates_20261004/expert_first_access_sram.json'])
    rows = [row if r['rung'] == 'R5a' else r for r in rows]
    a.rows_out.write_text(json.dumps(rows, indent=1) + '\n')
    print(json.dumps(dict(gates=gates, verdict=verdict['verdict'], gain_us=gain, pct=pct,
                          area_mm2=element_mm2, setup_ps=setup, hold_ps=hold), indent=1))


if __name__ == '__main__':
    main()
