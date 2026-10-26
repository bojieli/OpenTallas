"""Real 39-bit first Engram-tap request ABI; candidate source/plan delta, no added cycle."""

def apply(plan):
    part = next(p for p in plan['partitions'] if p['name'] == 'svc_14')
    if sum(p['type'] == part['type'] for p in plan['partitions']) != 1:
        raise ValueError('entry-only delta requires a unique svc_14 type')
    t = plan['partition_types'][part['type']]
    tap = next(c for c in t['contents'] if c['inst'] == 'u_etap_b')
    if tap['module'] not in ('dsdv_eng_tap','dsdv_eng_tap_entry39'):
        raise ValueError('unexpected first Engram tap provider')
    tap['module'] = 'dsdv_eng_tap_entry39'
    return dict(type=part['type'], part=part['name'], new_partition_types=0,
                public_bus_width_changes=0, cycles_added=0, private_input_bits_removed=4,
                downstream_request_bits=43, candidate_only=True)
