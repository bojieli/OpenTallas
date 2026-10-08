#!/usr/bin/env python3
"""Size SMH tile area alternatives before admitting new physical variants."""
import argparse
import hashlib
import json
from pathlib import Path

import hbm_accel_die_fp as die
import hbm_accel_smh_physical as sm

ROOT = Path(__file__).resolve().parents[1]


def model():
    receipt_path = 'results/uarch/hbm_smh_tile_headroom_20261007/measurement.json'
    measured_area = float(json.loads((ROOT / receipt_path).read_text())['area_um2'])
    base_width, height = sm.GEOM['tile_w'], sm.GEOM['tile_h']
    base_element = sm.floorplan(sm.GEOM)[1]
    base = die.build(die.R24SM3, network_probe=True)
    base_die = [base['geo']['W'], base['geo']['H']]
    candidates = []
    for width in (354.24, 362.88, 397.44):
        geom = dict(sm.GEOM, tile_w=width, be_w=base_width)
        element = sm.floorplan(geom)[1]
        outlined_width = base_die[0] + 6 * (element[0] - base_element[0])
        core_area = (width - 2.16) * (height - 2.16)
        center_shift = (width - base_width) / 2
        old_lanes = sm.lane_slots(base_width, sm.P['SUB'], sm.P['GLW'])
        new_lanes = sm.lane_slots(width, sm.P['SUB'], sm.P['GLW'])
        lane_residual = max(abs(new_lanes[k] - (old_lanes[k] + center_shift)) for k in old_lanes)
        candidates.append(dict(tile_geometry_um=geom, element_um=element,
            measured_tile_instance_area_um2=measured_area,
            gross_utilization=measured_area / (width * height),
            core_utilization=measured_area / core_area,
            core_utilization_at_most_60_percent=measured_area / core_area <= 0.60,
            die_um=[round(outlined_width, 3), base_die[1]],
            outline_33mm_headroom_um=round(33000 - outlined_width, 3),
            legal_outline=outlined_width <= 33000,
            all_512_tile_outline_delta_mm2=512 * (width - base_width) * height / 1e6,
            die_outline_delta_mm2=(outlined_width - base_die[0]) * base_die[1] / 1e6,
            changed_backend_views=0, backend_instances=256,
            backend_preservation=dict(selected_first_alternative=True,
                actual_macro_width_um=base_width,
                placement_shift_inside_wider_tile_slot_um=center_shift,
                tile_gout_to_backend_gin_x_residual_um=round(lane_residual, 6),
                adjacent_backend_wire_gap_um=round(sm.GEOM['gap'] + width - base_width, 3),
                adjacent_backend_added_wire_um=round(width - base_width, 3),
                backend_to_front_added_wire_um=round(center_shift, 3),
                wire_timing_requalification_required=True,
                generator_centered_backend_option_implemented=True),
            nominal_added_cycles=0, arithmetic_changed=False,
            wire_timing_and_clock_not_qualified=True, ready_for_route=False))
    return dict(schema='opentallas.hbm.smh.tile_headroom_model.v1',
        basis='tileW m3f CTS 108103 um2 instance area; apply conservatively to E/W, not an E measurement',
        baseline_tile_um=[base_width, height], baseline_element_um=base_element,
        baseline_die_um=base_die, SM_count=32, tiles_per_SM=16,
        candidates=candidates,
        compute_and_memory_delta=dict(MACs_per_cycle=0, memory_bytes_per_cycle=0,
            boundary_bits_per_cycle=0, replicas=0, mux_bits=0, fanout_sinks=0),
        selection=None, adoption=False,
        requirements_before_route=['Expose this sizing through the unified uarch model',
            'Verify new 32-SM geometry, all pin positions, relay corridors and track capacity',
            'Implement centered original-width backend placement; use actual unchanged E/W views and requalify longer parent wires',
            'Source pin and isolate candidate jobs; measured host admission',
            'Actual CTS/route growth may exceed area measured on the original tile'],
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
            ['tools/hbm_accel_die_fp.py', 'tools/hbm_accel_smh_physical.py',
             'tools/hbm_smh_tile_headroom_model.py', receipt_path]})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    result = model()
    p.write_text(json.dumps(result, indent=2) + '\n')
    for c in result['candidates']:
        print(c['tile_geometry_um']['tile_w'], c['core_utilization'], c['die_um'], c['legal_outline'])
