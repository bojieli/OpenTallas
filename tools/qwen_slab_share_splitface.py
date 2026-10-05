#!/usr/bin/env python3
"""Item 7 recipe variant 1: disjoint slab pins, no arithmetic or timing change.

The old combined top-edge constraint must be replaced, rather than followed
by an overlapping constraint whose precedence would depend on OpenROAD.
"""
import argparse
import json
import shlex

import qwen_slab_share as baseline


def args(height):
    height = baseline.snap(height)
    original = baseline.args(height)
    combined = '^(res_in|tw_)=top'
    if original.count(combined) != 1:
        raise ValueError('baseline combined top constraint changed')
    pos = original.index(combined)
    # Keep the existing central right-face tag/clock/reset range. The tree
    # word occupies the lower right segment, separated by one 2.16um step.
    end = baseline.snap(height / 2 - 35.0) - baseline.LAT_Y
    if end <= baseline.EDGE:
        raise ValueError('no disjoint lower-right tree-word interval')
    original[pos:pos + 1] = [
        '^res_in=top', '--pin-region',
        f'^tw_=right:{baseline.EDGE:g}-{end:g}',
    ]
    return original


def model(height=570.24):
    height = baseline.snap(height)
    per_group = baseline.W * height / 1e6
    original = baseline.W * baseline.BASE_H / 1e6
    return {
        'schema': 'opentallas.qwen_slab_splitface.v1',
        'variant': 's570_l6_splitface_m7',
        'recipe_variant_index': 1,
        'source_rtl_changed': False,
        'mul_lat': 6,
        'additional_cycles_vs_inherited_lat6': 0,
        'inherited_postscale_cycles_vs_lat5_per_token': 217,
        'boundary_changes': {'res_in_bits': 512, 'tw_d_bits': 512,
                             'tw_v_bits': 1, 'tw_rdy_bits': 1},
        'new_boundary_bits': 0,
        'new_memory_ports_or_bytes_per_cycle': 0,
        'new_macs_per_cycle': 0,
        'new_mux_demux_replicas_or_fanout': 0,
        'scale_banks_per_group': 16,
        'groups_per_die': 96,
        'share_mm2': per_group,
        'combined_port_scale_96_groups_mm2': 96 * per_group,
        'combined_port_scale_growth_mm2': 96 * (per_group - original),
        'historical_die_mm2': 811.763,
        'conditional_die_plus_share_growth_mm2': 811.763 + 96 * (per_group - original),
        'reticle_mm2': 858,
        'growth_is_combined_port_scale_not_two_debits': True,
        'die_repack_widening_area': None,
        'routing_capacity_proof': 'requires routed GRT/DRT; two disjoint faces replace one top face',
        'ss_setup_uncertainty_ps': 60,
        'ff_hold_uncertainty_ps': 25,
        'period_ns': 0.833333,
        'routing_layers': ['M2', 'M7'],
        'entry_strip_um': 40,
        'entry_strip_obstructed_layers': ['M6', 'M7'],
        'hardware_admission': False,
        'die_fit_or_timing_claim': False,
        'physical_args': args(height),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['args', 'model'])
    p.add_argument('--height', type=float, default=570.24)
    a = p.parse_args()
    if a.mode == 'args':
        print(shlex.join(args(a.height)))
    else:
        print(json.dumps(model(a.height), indent=2))


if __name__ == '__main__':
    main()
