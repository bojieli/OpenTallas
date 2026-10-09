#!/usr/bin/env python3
"""Source-pinned geometry comparison; no network or timing qualification."""
import json
import hbm_accel_die_fp as H

SOURCE_PIN = '0cb3d962452b9a627de3a386cd4e0baf5be0c7bf'

def main():
    cases = {
        'r25_adopted': dict(H.R25),
        'r25_wide_4x2_rejected': dict(H.R25, sm_wh=(3214.08, 1131.84)),
        'r25_sm3_reference_unadopted': dict(H.R25, sm_wh=(3075.84, 1131.84),
            sm_physical_grid=(3, 3), side_padding_um=207.36),
        'r25_fmt3_wide_3x3': dict(H.R25, sm_wh=(3214.08, 1131.84),
            sm_physical_grid=(3, 3), side_padding_um=207.36),
    }
    out = {'generator_source_pin': SOURCE_PIN, 'scope': 'geometry_only',
           'network_qualified': False, 'timing_qualified': False, 'cases': {}}
    for name, variant in cases.items():
        try:
            m = H.build(variant, geometry_only=True)
            g = m['geo']
            leg = H.legality(m)
            out['cases'][name] = {'geometry_um': g, 'area_mm2': g['W'] * g['H'] / 1e6,
                'reticle_margin_um': {'x': 33000-g['W'], 'y': 26000-g['H']},
                'legality': leg, 'fit': leg['overlaps'] == 0 and leg['outside'] == 0,
                'physical_grid': variant.get('sm_physical_grid', [4, 2]),
                'group_count': len(m['groups']), 'sm_per_group': 8,
                'column_corridor_um': H.CH, 'side_padding_um': variant.get('side_padding_um', 0),
                'notes': m['notes']}
        except (AssertionError, ValueError) as error:
            out['cases'][name] = {'fit': False, 'error': str(error), 'error_type': type(error).__name__}
    ref = out['cases']['r25_sm3_reference_unadopted']
    wide = out['cases']['r25_fmt3_wide_3x3']
    if 'area_mm2' in ref and 'area_mm2' in wide:
        wide['area_delta_vs_unadopted_sm3_mm2'] = wide['area_mm2'] - ref['area_mm2']
        wide['area_delta_vs_adopted_r25_mm2'] = wide['area_mm2'] - out['cases']['r25_adopted']['area_mm2']
    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    main()
