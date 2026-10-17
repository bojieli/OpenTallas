#!/usr/bin/env python3
"""S81 head-die MTP round-trip constants vs the die plan's relay stages (ROOT RELAY-SCHEMA 10-16).

The compiled S81 MTP schedule bakes the head-die hub relay latencies into RTL parameters (dsfd_mtp_seq_rtt FWD_R /
RET_R / FWD_V / RET_V; with --coll-mtp-lane dsfd_coll_mtp_lane FWD_C / RET_C).  This tool reads the stage counts of
those buses from the SELECTED die plan's opentallas.die_relay_stages.v1 file (fails closed if the plan lacks one),
compares them with the RTL constants, and writes the compiled-schedule table (the plan table with the RTL values
substituted) for tools/die_relay_check.py.

    mtp_rtt_stages.py PLAN_STAGES.json [--coll-lane] [--compiled-out SCHED.json] [--json REPORT.json]
        PLAN_STAGES '-' = env OT_DIE_RELAY_STAGES_S81
exit 1 when any constant differs from the plan (the same verdict die_relay_check gives on the compiled table).
"""
import argparse, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_relay_stages as DRS  # noqa: E402

RTT_RTL = 'rtl/dsrom_sys/mtp/dsfd_mtp_seq_rtt.sv'
LANE_RTL = 'rtl/dsrom_sys/s81_ph/coll/dsfd_coll_mtp_lane.sv'
BUSES = dict(FWD_R=DRS.bus_id('sp_capture', 't_mtp', 'sp_mtp', 'f_capture'),
             RET_R=DRS.bus_id('sp_mtp', 't_capture', 'sp_capture', 'f_mtp'),
             FWD_V=DRS.bus_id('sp_vm', 't_mtp', 'sp_mtp', 'f_vm'),
             RET_V=DRS.bus_id('sp_mtp', 't_vm', 'sp_vm', 'f_mtp'))
LANE_BUSES = dict(FWD_C=DRS.bus_id('sp_mtp', 't_collective', 'sp_collective', 'f_mtp'),
                  RET_C=DRS.bus_id('sp_collective', 't_mtp', 'sp_mtp', 'f_collective'))


def rtl_params(text, names):
    out = {}
    for k in names:
        m = re.search(rf'parameter integer {k} = (\d+)', text)
        if not m:
            raise SystemExit(f'mtp_rtt_stages: RTL parameter {k} not found')
        out[k] = int(m.group(1))
    return out


def run(plan, rtt_text, lane_text=None):
    t = DRS.Table(plan)
    want = dict(BUSES)
    have = rtl_params(rtt_text, BUSES)
    if lane_text is not None:
        want.update(LANE_BUSES)
        have.update(rtl_params(lane_text.split('`else', 1)[-1], LANE_BUSES))
    die = {k: t.stages(b) for k, b in want.items()}          # MissingBus = fail closed
    sched = DRS.compiled(plan, 'tools/s81/mtp_rtt_stages.py (RTL constants)',
                         used_by={b: [k] for k, b in want.items()}, scheduled={want[k]: v for k, v in have.items()})
    ok = all(die[k] == have[k] for k in want)
    return dict(verdict='PASS' if ok else 'FAIL', die=die, rtl=have, buses=want), sched


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('plan'); ap.add_argument('--coll-lane', action='store_true')
    ap.add_argument('--compiled-out'); ap.add_argument('--json')
    a = ap.parse_args(argv)
    p = DRS.plan_path('s81', None if a.plan == '-' else a.plan)
    plan = DRS.load(p)
    rep, sched = run(plan, (ROOT / RTT_RTL).read_text(), (ROOT / LANE_RTL).read_text() if a.coll_lane else None)
    rep.update(plan=plan['plan'], digest=plan['digest'], source=str(p))
    if a.compiled_out:
        DRS.write(a.compiled_out, sched)
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1) + '\n')
    print('MTP_RTT_STAGES', rep['verdict'], json.dumps(dict(die=rep['die'], rtl=rep['rtl'])))
    return 0 if rep['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
