#!/usr/bin/env python3
"""HEAD boot-path reset roles: raw transport only, mission operators unchanged.

The exact paths are HOST0/HOST1 KP4 ingress (u/d), and HOST<->CTL configuration
through the spine hu/hd stations. The spine spo/spr operators remain gated by
START, as do unrelated station and arithmetic consumers. Zero data cycles added.
"""
import argparse
import copy
import json
from pathlib import Path

SCOPES = {
    'hd_serdes': (['coll_i0', 'coll_o0'], ['u_phy']),
    'hd_st_k5': (['u_i', 'u_o', 'd_i', 'd_o'], []),
    'hd_spn': (['hu_i', 'hu_o', 'hd_i', 'hd_o'], []),
    'hd_spn_end': (['hu_i', 'hu_o', 'hd_i', 'hd_o'], []),
}

# l48x routes HOST-to-CTL through this new, transport-only north strip.
# Older source plans have no strip and retain their original delta exactly.
OPTIONAL_SCOPES = {'hd_host_n': (['h_rx_ft_i', 'h_rx_ft_o'], [])}


def apply(plan):
    out = copy.deepcopy(plan)
    if out.get('reset', {}).get('start') != 'broadcast':
        raise ValueError('HEAD bootstrap requires the actual broadcast START plan')
    scopes = dict(SCOPES)
    scopes.update({tn: spec for tn, spec in OPTIONAL_SCOPES.items()
                   if tn in out['partition_types']})
    for tn, (buses, contents) in scopes.items():
        ty = out['partition_types'][tn]
        if ty.get('reset', {}).get('start_role', 'mission') != 'mission':
            raise ValueError(f'{tn}: transport delta must not promote a whole mixed type')
        modules = {c['inst']: c['module'] for c in ty.get('contents', [])}
        if tn == 'hd_serdes' and modules.get('u_phy') != 'ot_s81hd_serdes_link':
            raise ValueError('hd_serdes provider is not the inspected transport')
        if tn.startswith('hd_spn') and modules != {'u_spo': 'ot_s81hd_spo', 'u_spr': 'ot_s81hd_spr'}:
            raise ValueError('spine content changed: review mission/transport reset ownership')
        if tn == 'hd_host_n' and modules:
            raise ValueError('HOST north strip now has operators; review raw transport reset ownership')
        reset = ty.setdefault('reset', {})
        reset['bootstrap_buses'] = list(dict.fromkeys(reset.get('bootstrap_buses', []) + list(buses)))
        reset['bootstrap_contents'] = list(dict.fromkeys(reset.get('bootstrap_contents', []) + list(contents)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path); ap.add_argument('out', type=Path)
    a = ap.parse_args(); a.out.parent.mkdir(parents=True, exist_ok=True)
    out = apply(json.loads(a.plan.read_text()))
    from head_source_delta import rebase_pin_assets
    rebase_pin_assets(out, a.plan, a.out, Path('.'))
    a.out.write_text(json.dumps(out, indent=2)+'\n')


if __name__ == '__main__':
    main()
