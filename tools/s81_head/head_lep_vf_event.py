#!/usr/bin/env python3
"""Private LEP vF provider/placement/clock trial; die wire latency unchanged.

This composes the measured physical profile, explicit trial core taps and
provider calendar. Generated kit, child/cohort and programme qualification
are still required before a READY plan event.
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

PARAMS = dict(KTX="16'h0000", KRX="16'h1220", TXI="16'h1221", PIN=2, POUT=3, PLW=3, COL0=2)


def apply(raw):
    out = copy.deepcopy(raw)
    typ = out['partition_types']['hd_lep0N']
    core = [c for c in typ['contents'] if c['inst'] == 'u_core']
    if len(core) != 1 or core[0]['module'] != 'ot_s81hd_lep0N_noidx_core':
        raise ValueError('exact native LEP u_core content required')
    old = dict(core[0].get('params', {}))
    if old.get('CH_B') != "4'b1111" or old.get('PAIR') != 1:
        raise ValueError('event requires actual four-pair HEAD configuration')
    for name, value in PARAMS.items():
        if name in old and old[name] != value:
            raise ValueError('conflicting existing stage parameter: ' + name)
    core[0]['params'] = {**old, **PARAMS}
    # Every other plan field, including lane.fixed_cycles, stays exactly as read.
    check = copy.deepcopy(out)
    cc = next(c for c in check['partition_types']['hd_lep0N']['contents'] if c['inst'] == 'u_core')
    cc['params'] = old
    if check != raw:
        raise AssertionError('provider event changed a field outside native parameters')
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--calendar-tools', type=Path, default=Path(__file__).resolve().parent,
                    help='tools/s81_head directory carrying the composed provider calendar')
    args = ap.parse_args()
    sys.path.insert(0, str(args.calendar_tools.resolve()))
    from lep_calendar_1113.lep_calendar import (provider_port_contract,
                                                check_external_lane_calendar_unchanged)
    data = args.plan.read_bytes()
    raw = json.loads(data)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from head_lep_vf_physical import apply as apply_physical, load_profile
    from head_lep_vf_clock import apply as apply_clock
    contract = provider_port_contract(raw)
    out = apply_clock(apply_physical(apply(raw), load_profile()))
    check_external_lane_calendar_unchanged(raw, out, contract)
    args.out.mkdir(parents=True, exist_ok=False)
    candidate = args.out / 'source_plan.json'
    candidate.write_text(json.dumps(out, indent=1) + '\n')
    report = dict(schema='opentallas.head_lep_vf_event.v1', status='DRAFT_NOT_ADOPTED',
                  baseline_sha256=hashlib.sha256(data).hexdigest(),
                  candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
                  native_parameters=PARAMS, external_lane_fixed_cycles_delta=0,
                  bus_geometry_delta=0, native_sram_origin_updates=45, native_stage_pattern_groups=24,
                  native_stage_rectangles=19, manual_pair_core_taps=4, reset_delta=0,
                  pair_view_cohort="vE_1106_TRIAL_NOT_ADOPTED",
                  logical_stage_flop_bits=14023,
                  consumption='provider calendar consumed once; no added inter-partition wire delay',
                  model_entry='tools/uarch_model.py::s81_head_lep_vf_stage_calendar_model',
                  model_source='codex/svc-token-1113@48d092e2e0',
                  physical_form_source='codex/head-lep-reserve-form-0222@41a81fe176',
                  physical_native_proof='EQUIVALENT 107757/107757',
                  pending=['child vE_1106 phase/cohort and parent clock adoption remain HOLD',
                           'generated native placement hook must match measured profile',
                           'strict bind and count dry run on composed source',
                           'actual vF programme calendar and one-time compiler consumer',
                           'physical CTS/GRT/route signoff'])
    (args.out / 'provider_contract.json').write_text(json.dumps(contract, indent=1) + '\n')
    (args.out / 'provider_event.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
