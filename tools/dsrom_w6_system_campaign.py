#!/usr/bin/env python3
"""Opt-in parent event measurement using the existing actual DS system campaign.

--w6-trace selects the additive source. Other arguments go to the existing
campaign unchanged. This does not supply a Scenario C allocation or wavefront
scheduler; those must be integrated before measuring the combined candidate.
"""
import os
import sys
from pathlib import Path


def select(campaign, enabled):
    if not enabled:
        return
    campaign.TB = Path(__file__).resolve().parents[1] / 'rtl/test/dsrom_sys/w6/tb_dsrom_system.sv'
    params = os.environ.get('OT_SYS_GPARAMS', '').split()
    if any(p.startswith('W6_TRACE=') for p in params):
        raise ValueError('Conflicting W6_TRACE parameter')
    os.environ['OT_SYS_GPARAMS'] = ' '.join([*params, 'W6_TRACE=1'])


def main():
    enabled = '--w6-trace' in sys.argv
    if enabled:
        sys.argv.remove('--w6-trace')
    import dsrom_system_campaign as campaign
    select(campaign, enabled)
    return campaign.main()

if __name__ == '__main__':
    raise SystemExit(main())
