#!/usr/bin/env python3
"""Size the necessary W10 registered-wake baseline correction through the unified model.

No product constants, original RTL or failed records are modified. This is a
prebuild ledger, not a timing or numerical adoption gate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uarch_model as U

ROOT = Path(__file__).resolve().parents[1]


def ledger(lib):
    baseline = U.w10_baseline_model()
    q_bits = 1 + 8 + 3 + 2 + 512 + 20 + 3
    bf_bits = 1 + 3 + 3 + 4 + 32 + 1024
    leaves = 8  # four pipeline groups plus four physical ping-pong macros
    # SS Liberty CLK capacitances in fF; actual cells, not area-clock proxies.
    cap_dff, cap_icg = 0.446638, 2.0635
    voltage, freq = 0.63, 1.2e9
    copies = baseline['composition']['stage_count'] * 4
    owners = json.loads((ROOT / 'results/arch/v41_stage_owner_product.json').read_text())
    pairs = max(owners['pairs_per_die_by_stage'])
    rows = {}
    for name, bits, outline in [('q', q_bits, U.CONS_PITCH[U.PRODUCT_PITCH]['q_um']),
                                ('column', q_bits + bf_bits, U.CONS_PITCH[U.PRODUCT_PITCH]['bf16_outline_um'])]:
        tile = outline[0] * outline[1]
        # The boundary registers already exist; only their clock policy changes.
        area = leaves * U.DFF_UM2 + (leaves - 1) * 0.26244 + 32 * U.DFF_UM2
        tracks = U.FLOORPLAN['over_rom_tracks_per_100um'] * outline[0] / 100 * .5
        signal_bits = 548 + bits + leaves * 2
        cap_ff = (bits + leaves) * cap_dff + (leaves - 1) * cap_icg
        pin_w = cap_ff * 1e-15 * voltage**2 * freq
        # Explicit 3x bound for clock buffers/wires plus internal pin energy.
        rows[name] = dict(outline_um=outline, tile_um2=tile,
                          existing_boundary_register_bits=bits, extra_register_bits=leaves,
                          extra_gate_count=leaves-1, extra_area_um2_upper=area,
                          incremental_placement_um2_at_50pct=area/.5,
                          incremental_slot_fraction=(area/.5)/tile,
                          allocated_slots_per_element=1, boundary_bits_per_cycle=bits,
                          local_signal_tracks_needed=signal_bits,
                          channel_tracks_estimate=tracks, track_fraction=signal_bits/tracks,
                          additional_clock_pin_cap_ff=cap_ff,
                          additional_clock_pin_w_ss=pin_w,
                          additional_clock_w_3x_estimate=3*pin_w,
                          fit=area/.5 < .01*tile and signal_bits < tracks)
    per_die = rows['q']['additional_clock_w_3x_estimate'] * (pairs - 1024) + rows['column']['additional_clock_w_3x_estimate'] * 1024
    return dict(schema='opentallas.w10.wake.prebuild.v1',
                verdict='PASS_SIZING_ONLY' if all(r['fit'] for r in rows.values()) else 'FAIL_SIZING',
                kind='MANDATORY_BASELINE_IMPLEMENTATION_CORRECTION', adopted=False,
                parameters=dict(WAKE_REG=1, default=0, FAST=1, PP=1, FRONT_PAR=0, NB=2, LAT=8),
                original_modules_preserved=True,
                compute=baseline['compute'], ports=baseline['ports'],
                latency=dict(boundary_cycles=1, added_walker_cycles=0,
                             rationale='go and x captured on free edge; registered wake opens next edge when existing go_e is consumed',
                             actual_lat8=baseline['composition']['checked_in_lat8_audit'],
                             one_added_cycle_fallback='Must reprice and rerun exact gate before any build if protocol requires a cycle'),
                full_size=dict(stages=copies//4, layer_dies=copies, maximum_pairs_per_die=pairs,
                               bf16_column_pairs_per_die=1024, macros_per_element=4,
                               local_icgs_per_element=leaves, wake_ff_fanout_per_leaf=1,
                               wake_next_fanout=leaves, external_port_fanout_delta=0,
                               mux_demux='existing PP muxes and alternating bank enables unchanged; no FRONT_PAR',
                               layer_die_clock_w_3x_estimate=per_die,
                               conservative_all_layer_dies_clock_w=per_die*copies),
                elements=rows,
                clock_power_basis=dict(voltage_ss=voltage, clock_hz=freq,
                                       dff_clk_ff=cap_dff, icg_clk_ff=cap_icg,
                                       lib_sha256=hashlib.sha256(lib.read_bytes()).hexdigest(),
                                       margin='3x pin C*V^2*f estimate, not measured CTS power; always-clocked activation stage',
                                       excludes='Always-on upstream trunk already priced by model; actual internal/CTS power must replace estimate'),
                boundaries=dict(hub_port_bits_delta=0, shared_memory_bytes_delta=0,
                                clock_domains='same source clock, local gated leaves; physical skew and min paths must close',
                                layer_restriction='local strip wiring; inherited hub layer contract unchanged, post-route audit required'),
                gates=['exact startup/reset/idle-to-work, immediate beat, final partial and drain',
                       'leaf wake registers must survive synthesis, no raw go/reset path to ICG ENA',
                       'same fixed 0.833ns /60ps setup /25ps hold and original I/O delays',
                       'SS setup and FF hold with actual macro own-corner views',
                       'full-size macro pin access and clean route, ROM slew/fanout, measured power',
                       'actual abstracts then W18 composed root/region and die route/IR'],
                other_designs={'qwen_rom':'unchanged','qwen_hbm':'unchanged','v41_hbm':'unchanged'},
                source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                               ['tools/uarch_model.py','rtl/v41rom/ot_v41_rom_elem_w10.sv',
                                'results/arch/v41_stage_owner_product.json',
                                'results/uarch/w10_baseline_main_prequalification_bb01.json',
                                'results/quality/w10_parent_model_pin_refresh_20261001.json',
                                'tools/w10_wake_prebuild.py']})


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ss-lib', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    record = ledger(a.ss_lib)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as f:
        json.dump(record, f, indent=2); f.write('\n')
    print(json.dumps(record, indent=2))
    raise SystemExit(record['verdict'] != 'PASS_SIZING_ONLY')
