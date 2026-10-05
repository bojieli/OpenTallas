#!/usr/bin/env python3
"""Bind the qualified full-goal q/column modes, including the column XF=8 FIFO.

The initial wake ledger remains immutable. This additive sizing explicitly
prices the qualified mode, rather than copying c8's undersized XF=4 column.
"""
import argparse
import hashlib
import json
from pathlib import Path
import uarch_model as U
from w10_wake_qualification import ROOT, validate_model, verify_sources


def bind(base):
    validate_model(base)
    verify_sources(base)
    rec = json.loads(json.dumps(base))
    golden_path = ROOT/'results/uarch/w10_baseline_wake/qualification/golden_n4_r1.json'
    golden = json.loads(golden_path.read_text())
    if golden['verdict'] != 'PASS' or golden['params']['LAT'] != 8:
        raise ValueError('full golden mode not qualified')
    q_depth, column_depth = golden['params']['XF_Q'], golden['params']['XF_BF']
    fifo_bits = (column_depth-q_depth) * 532  # two 256-bit payloads plus two 10-bit exponents/entry
    fifo_area = fifo_bits * U.DFF_UM2
    mux_area = fifo_bits * .2 + 16 * U.DFF_UM2  # assumed read mux/control upper estimate
    c = rec['elements']['column']
    c['extra_register_bits'] += fifo_bits + 16
    c['extra_area_um2_upper'] += fifo_area + mux_area
    c['incremental_placement_um2_at_50pct'] = 2*c['extra_area_um2_upper']
    c['incremental_slot_fraction'] = c['incremental_placement_um2_at_50pct']/c['tile_um2']
    c['local_signal_tracks_needed'] += fifo_bits
    c['track_fraction'] = c['local_signal_tracks_needed']/c['channel_tracks_estimate']
    # Actual c8 GRT cell area is only a sizing anchor, never a qualified abstract.
    anchor_path = ROOT/'results/uarch/w10_baseline_wake/c8_area_anchor.json'
    anchor = json.loads(anchor_path.read_text())['metrics']
    c['baseline_core_um2'] = anchor['globalroute__design__core__area']
    c['baseline_stdcell_um2'] = anchor['globalroute__design__instance__area__stdcell']
    c['baseline_macro_um2'] = anchor['globalroute__design__instance__area__macros']
    c['spare_placement_um2'] = c['baseline_core_um2']-c['baseline_stdcell_um2']-c['baseline_macro_um2']
    c['fit'] = c['incremental_placement_um2_at_50pct'] < c['spare_placement_um2'] and c['track_fraction'] < 1
    p = rec['clock_power_basis']
    fifo_clock = (fifo_bits+16)*p['dff_clk_ff']*1e-15*p['voltage_ss']**2*p['clock_hz']*3
    c['additional_busy_fifo_clock_w_3x_estimate'] = fifo_clock
    rec['full_size']['layer_die_busy_fifo_clock_w_3x_estimate'] = 1024*fifo_clock
    rec['full_size']['layer_die_all_busy_clock_w_3x_estimate'] = rec['full_size']['layer_die_clock_w_3x_estimate']+1024*fifo_clock
    rec['schema'] = 'opentallas.w10.wake.fullgoal_binding.v1'
    rec['verdict'] = 'PASS_SIZING_ONLY' if c['fit'] else 'FAIL_SIZING'
    rec['mode_binding'] = dict(q=dict(top='ot_v41_rom_elem_q_wake_w10',BF16=0,XF=q_depth,NB=2,FAST=1,PP=1,WAKE_REG=1),
                             column=dict(top='ot_v41_rom_elem_wake_w10',BF16=1,XF=column_depth,NB=2,FAST=1,PP=1,WAKE_REG=1),
                             common=dict(CUT=379,LAT=8,MTP=1,EARLY=1,FRONT_PAR=0,BP=0))
    rec['qualification_boundary'] = dict(N=4,NB=2,MTP_positions=6,cases=13,rows=240,
                                        completion_cycle_delta=0,
                                        note='N2 failures retained separately, not qualified or recast as passing; composed full-field RTL pending')
    rec['fifo_sizing'] = dict(column_original_depth=q_depth,column_qualified_depth=column_depth,
                             extra_storage_bits=fifo_bits,extra_storage_um2=fifo_area,
                             extra_mux_control_um2_estimate=mux_area,
                             latency_delta_cycles=0,read_bytes_per_cycle=532/8,
                             write_bytes_per_cycle=532/8,spine_port_delta_bits=0)
    rec['source_sha256']['tools/w10_wake_fullgoal.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    rec['source_sha256']['results/uarch/w10_baseline_wake/prebuild.json'] = hashlib.sha256((ROOT/'results/uarch/w10_baseline_wake/prebuild.json').read_bytes()).hexdigest()
    rec['source_sha256'][str(golden_path.relative_to(ROOT))] = hashlib.sha256(golden_path.read_bytes()).hexdigest()
    rec['source_sha256'][str(anchor_path.relative_to(ROOT))] = hashlib.sha256(anchor_path.read_bytes()).hexdigest()
    return rec


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    a = ap.parse_args()
    record = bind(json.loads((ROOT/'results/uarch/w10_baseline_wake/prebuild.json').read_text()))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:
        json.dump(record,f,indent=2); f.write('\n')
    print(json.dumps({k:record[k] for k in ['verdict','mode_binding','fifo_sizing','full_size']},indent=2))
    raise SystemExit(record['verdict'] != 'PASS_SIZING_ONLY')
