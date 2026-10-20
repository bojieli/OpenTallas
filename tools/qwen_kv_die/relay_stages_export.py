#!/usr/bin/env python3
"""Qwen KV/system die -> opentallas.die_relay_stages.v1 (ROOT RELAY-SCHEMA 10-16; additive, no placement change).

    from qwen_kv_die import relay_stages_export as X; X.export_model(m, plan_id)    (kv_die.py writes it next to
                                                                                     plan.json as relay_stages.json)
kv_die._relays replaces a point-to-point bus bid by relay instances rly_<bid>_<k> (kind 'relay', a -> b) and records
m['relay_stages'][bid] = number of relays.  The table walks m['insts'] / m['buses'] after the relay plan through the
relays (one stage each, the same rule as tools/qwen_split/relay_stages_export.py) and cross-checks every
point-to-point origin bus against m['relay_stages'] (a mismatch is a problem, the walked netlist count wins).
Abutted / band classes (ABUT), clock / reset trees and constants are not die data buses.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from qwen_split import relay_stages_export as QX  # noqa: E402

ABUT = ('stack_local', 'phy_dfi', 'd2d_fdi', 'hbm_cdc', 'cdc_core')
SKIP = ABUT + ('clock_trunk', 'reset', 'constant', 'clock')


def export_model(m, plan_id, commit=None, sources=(), reach=None):
    doc = QX.export_model(m, plan_id, commit, sources, reach, design='qwen_kv', skip_cls=SKIP)
    # Mixed-clock static tiles carry a historical instance-wide 'hbm' label. A core control word or EST
    # crossing is clocked by its actual port, not that instance label (the planner uses the same rule).
    import kv_pin_repair as PR
    by = {it.name: it for it in m['insts']}
    for bus in doc['buses']:
        src, dst = bus['src'], bus['dst']
        sd = PR.port_domain(src.get('master'), src['port'])
        dd = PR.port_domain(dst.get('master'), dst['port'])
        if sd is not None or dd is not None:
            bus['domain'] = PR.launch_domain(by, (src['inst'], src['port']), (dst['inst'], dst['port']))
    doc['digest'] = QX.DRS.digest(doc['buses'])
    rs = m.get('relay_stages') or {}
    mism = []
    for b in doc['buses']:
        for bid in (b.get('bid') or '').split('+'):
            if bid in rs and rs[bid] != b['stages']:
                mism.append(f"{b['id']}: kv_die relay_stages[{bid}] = {rs[bid]}, netlist walk {b['stages']}")
    doc['problems'] = (mism + doc['problems'])[:200]
    doc['problem_count'] += len(mism)
    doc['relay_stages_crosscheck'] = dict(buses_in_kv_die_record=len(rs), mismatches=len(mism))
    return doc
