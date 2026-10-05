"""Same-FEC link timing policy, retaining an NVLink-class switch tier.

Light FEC over a switch cable is a model sensitivity, not PHY qualification.
No runtime, RTL, measured accelerator rate or direct-mesh adoption lives here.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


def matched_fec_row(fec_class, *, switch_s=250e-9):
    if fec_class not in ('light', 'kp4'):
        raise ValueError('select light or kp4 on BOTH designs')
    if not math.isfinite(switch_s) or switch_s < 0:
        raise ValueError('finite nonnegative switch delay required')
    leg_s = {'light': 130e-9, 'kp4': 209e-9}[fec_class]
    return dict(name=f'{fec_class}_fec_switch', fec_class=fec_class,
                rom_board_hop_s=leg_s, hbm_switch_leg_s=leg_s,
                switch_tier_s=switch_s, hbm_switched_traversal_s=2*leg_s+switch_s,
                topology='NVLink-class switch: two SerDes legs + one switch tier',
                evidence='MODEL_ONLY_NOT_PHY_OR_MEASURED_RATE', adopted=False,
                published_accelerator_rate=None,
                reach_qualified=False if fec_class == 'light' else None,
                scope='same FEC class, not equal traversal count; keep serialization, bandwidth, UCIe, CDC, power and route costs')


def policy(root):
    root=Path(root)
    paths=('tools/arch_budget_v41.py','tools/decode_critical_path.py',
           'configs/hardware/technology.json')
    return dict(schema='matched_fec_switch_rom_policy_v1',
                rule='HBM switch legs and compared ROM board links MUST use the same FEC class',
                selected_comparison='light_fec_switch',
                rows=[matched_fec_row(c) for c in ('light','kp4')],
                historical_unequal_comparison=dict(rom_board_hop_s=130e-9,
                    hbm_switch_leg_s=209e-9, hbm_switched_traversal_s=668e-9,
                    comparable=False, preserved_as_history=True),
                direct_mesh='OWNER_REJECTED; retain NVLink-class switch',
                source_policy='arch_budget_v41.BASELINE light 130ns; technology.json KP4 209ns; decode_critical_path.SWITCH_LATENCY_S assumed 250ns',
                qualification='Light FEC is not qualified for rack-cable reach by the technology record. Applying it to both designs is an explicitly model-only sensitivity, never an analog guarantee.',
                rate_composition='No transfer into frozen HA ladder or legacy 125.9us fabric lump; re-evaluate the owning DAG before rate publication.',
                input_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})


if __name__ == '__main__':
    print(json.dumps(policy(Path(__file__).resolve().parents[1]),indent=2,allow_nan=False))
