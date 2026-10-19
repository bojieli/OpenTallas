#!/usr/bin/env python3
"""Q-XPF 10-18: the lane ages of a land-plan compute die, for its netlist benches and the tt_ctlm image compiler.

A land-plan GEN (OT_SPLIT_LAND_PLAN) gives every forwarded lane E = fwd_e_est(n) + E_sta - 2 and ties the landing's K
strap to that E.  E_sta (the landing residual the die STA measured: forwarded-clock insertion) is NOT in a zero-delay
simulation, so a landing with E_sta > D - 1 aliases by the ring depth D (dv2f14br / dv2f14bi tt_ctlm.hr: E 18 reads as
14, the landing epoch check faults).  The netlist with its lane timing is the hardware; this tool makes a bench copy
of a die slice carry it (rtl/qwen_split/ot_qfd_land_lag.sv, simulation only) and derives the compiler's lane ages from
the same GEN record:

    land_lag_sim.py annotate SLICE_DIR --lanes fwd_lanes.json [--zero]
        rewrites SLICE_DIR in place: every qfd_landh* wrapper of the slice's die_glue (copied to SLICE_DIR/die_glue_lag.sv)
        instantiates ot_qfd_land_lag #(.LAG(SIM_LAG)); every landing instance of the slice gets
        #(.SIM_LAG(max(0, E_sta - 2))) from its lane row (--zero: SIM_LAG 0 everywhere = the zero-delay netlist, with the
        fault report).  Fails closed (exit 3) when a slice landing has no lane row.  Record SLICE_DIR/land_lag.json.
    land_lag_sim.py ages --lanes fwd_lanes.json --out lane_ages.json [--die NAME]
        R_CMD / R_HR / R_SS / R_AG = lane_groups.lane_cycles of dvw_cmd_wi / dvw_hr_wi / dvw_ss_wo / dvw_ag_wo (E + 1
        landing o register), XPF_TRANSPORT_EDGES = 1 + R_HR (die_params.py rule); input of ctlm_image.py --lane-ages.
    land_lag_sim.py xpf-check RUN_LOG --slice SLICE_DIR --lanes fwd_lanes.json --params DIE_V.params.json --out A.json
        fail closed (exit 1) unless: the slice is lane-timed (land_lag.json, not --zero, same fwd_lanes.json), the XPF
        probe (drive_qwc_slice_ctl.svh SMOKE_XPF) measured the hr lane, XPF_TRANSPORT_EDGES of the die sidecar ==
        elaborated == 1 + measured == 1 + lane_cycles(dvw_hr_wi), and no landing of the tt_ctlm lanes (hr / cmd / ss /
        ag) reported OT_QFD_LAND_FAULT.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import lane_groups as LG  # noqa: E402

FWD_E0 = 2                      # the E_sta a zero-delay netlist reproduces (fwd_e_est, measured dv2f14bq: hr 14 = 13 + 1)
AGE_BUSES = dict(R_CMD='dvw_cmd_wi', R_HR='dvw_hr_wi', R_SS='dvw_ss_wo', R_AG='dvw_ag_wo')
LAND_INST = re.compile(r'^(\s*)(qfd_landh0?_\w+)\s+(\w+)\s*\(', re.M)
LAND_MOD = re.compile(r'^module (qfd_landh0?_\w+) \(')


def sim_lag(row):
    return max(0, int(row.get('E_sta') if row.get('E_sta') is not None else FWD_E0) - FWD_E0)


def annotate(slice_dir, lanes_path, zero=False):
    S = Path(slice_dir)
    fl = sorted(S.glob('*.f'))
    if len(fl) != 1:
        raise SystemExit(f'land_lag_sim: {S}: expected one .f file, got {fl}')
    flines = fl[0].read_text().splitlines()
    glue = [ln for ln in flines if ln.endswith('/die_glue.sv')]
    lane_rtl = [ln for ln in flines if ln.endswith('/rtl/qwen_split/qfd_fwd_lane.sv')]
    if len(glue) != 1 or len(lane_rtl) != 1:
        raise SystemExit(f'land_lag_sim: {fl[0]}: needs exactly one die_glue.sv and one qfd_fwd_lane.sv ({glue}, {lane_rtl})')
    lanes = json.loads(Path(lanes_path).read_text())
    by_land = {r['landing']: r for r in lanes['lanes'] if r.get('landing')}
    # 1. wrappers: ot_qfd_land -> ot_qfd_land_lag #(.LAG(SIM_LAG))
    g = Path(glue[0]).read_text().splitlines()
    out, nmod = [], 0
    for ln in g:
        m = LAND_MOD.match(ln)
        if m:
            ln = ln.replace(f'module {m.group(1)} (', f'module {m.group(1)} #(parameter integer SIM_LAG = 0) (', 1)
            nmod += 1
        if 'ot_qfd_land #(' in ln:
            ln = ln.replace('ot_qfd_land #(', 'ot_qfd_land_lag #(.LAG(SIM_LAG), ', 1)
        out.append(ln)
    (S / 'die_glue_lag.sv').write_text('\n'.join(out) + '\n')
    # 2. instances: #(.SIM_LAG(L)) per landing from its lane row
    svs = [p for p in S.glob('*.sv') if p.name != 'die_glue_lag.sv']
    rec, missing = [], []
    for sv in svs:
        t = sv.read_text()

        def sub(m):
            inst = m.group(3)
            r = by_land.get(inst)
            if r is None:
                missing.append(inst)
                return m.group(0)
            L = 0 if zero else sim_lag(r)
            rec.append(dict(inst=inst, master=m.group(2), bid=r['bid'], n=r.get('n'), E=r.get('E'), E_sta=r.get('E_sta'),
                            K=r.get('K'), LAG=L))
            return f'{m.group(1)}{m.group(2)} #(.SIM_LAG({L})) {inst} ('
        t2 = LAND_INST.sub(sub, t)
        if t2 != t:
            sv.write_text(t2)
    if missing:
        raise SystemExit(f'land_lag_sim: FAIL slice landings without a lane row in {lanes_path}: {missing[:8]} '
                         f'({len(missing)})')
    # 3. file list: the lag glue + the simulation model
    model = str(Path(lane_rtl[0]).parent / 'ot_qfd_land_lag.sv')
    nf = []
    for ln in flines:
        if ln == glue[0]:
            ln = str((S / 'die_glue_lag.sv').resolve())
        nf.append(ln)
        if ln == lane_rtl[0]:
            nf.append(model)
    fl[0].write_text('\n'.join(nf) + '\n')
    r = dict(schema='opentallas.qwen.land-lag-sim.v1', slice=str(S), lanes=str(lanes_path),
             lanes_sha256=hashlib.sha256(Path(lanes_path).read_bytes()).hexdigest(), zero=zero,
             rule='LAG = max(0, E_sta - 2) lane-clock periods on the landing write side (sim only, ot_qfd_land_lag.sv)',
             wrappers=nmod, landings=sorted(rec, key=lambda x: x['inst']),
             lag_hist={str(L): sum(1 for x in rec if x['LAG'] == L) for L in sorted({x['LAG'] for x in rec})})
    (S / 'land_lag.json').write_text(json.dumps(r, indent=1) + '\n')
    print(f"LAND_LAG_SIM {'ZERO' if zero else 'PLAN'} wrappers {nmod} landings {len(rec)} lag_hist {r['lag_hist']}")
    return r


def ages(lanes_path, die=None):
    lanes = json.loads(Path(lanes_path).read_text())
    by = {r['bid']: r for r in lanes['lanes']}
    out = dict(schema='opentallas.qwen.ctlm-lane-ages.v1', die=die or str(lanes_path),
               why='Q-XPF: lane ages of a land-plan die = lane_groups.lane_cycles (E + 1 landing o) of the GEN fwd_lanes.json; '
                   'the netlist bench reproduces them only with the lane timing (land_lag_sim.py annotate)',
               source=str(lanes_path), source_sha256=hashlib.sha256(Path(lanes_path).read_bytes()).hexdigest())
    for k, bid in AGE_BUSES.items():
        r = by.get(bid)
        if r is None:
            raise SystemExit(f'land_lag_sim ages: no lane {bid} in {lanes_path}')
        out[k] = LG.lane_cycles(r)
        out.setdefault('lanes', {})[k] = dict(bid=bid, n=r.get('n'), E=r.get('E'), E_sta=r.get('E_sta'), K=r.get('K'))
    out['XPF_TRANSPORT_EDGES'] = 1 + out['R_HR']
    return out


XPF_RX = re.compile(r'SMOKE_XPF hr lane edges (-?\d+) .*XPF_TRANSPORT_EDGES elaborated (\d+)')
CTLM_LAND = re.compile(r'^OT_QFD_LAND_FAULT \S*\.(rly_dvw_(?:hr_wi|cmd_wi|ss_wo|ag_wo)_\d+)\.', re.M)


def xpf_check(log, slice_dir, lanes_path, params_path):
    fails = []
    ll = json.loads((Path(slice_dir) / 'land_lag.json').read_text())
    sha = hashlib.sha256(Path(lanes_path).read_bytes()).hexdigest()
    if ll.get('zero'):
        fails.append('slice is the zero-delay netlist (land_lag_sim annotate --zero): lane ages alias by the ring depth')
    if ll.get('lanes_sha256') != sha:
        fails.append(f'slice lane timing from another fwd_lanes.json ({ll.get("lanes")})')
    t = Path(log).read_text()
    m = XPF_RX.search(t)
    meas = elab = None
    if not m:
        fails.append('no SMOKE_XPF probe line in the run log')
    else:
        meas, elab = int(m.group(1)), int(m.group(2))
    lanes = json.loads(Path(lanes_path).read_text())
    hr = next((r for r in lanes['lanes'] if r['bid'] == AGE_BUSES['R_HR']), None)
    want = 1 + LG.lane_cycles(hr) if hr else None
    side = json.loads(Path(params_path).read_text())['masters'].get('qfd_tt_ctlm_dv', {}).get('XPF_TRANSPORT_EDGES')
    if meas is not None and not (side == elab == 1 + meas == want):
        fails.append(f'XPF_TRANSPORT_EDGES sidecar {side} / elaborated {elab} / 1 + measured {1 + meas} / '
                     f'1 + lane_cycles(fwd_lanes) {want} disagree')
    lf = sorted(set(CTLM_LAND.findall(t)))
    if lf:
        fails.append(f'tt_ctlm lane landings faulted (read slot epoch != rc - K): {lf}')
    return dict(schema='opentallas.qwen.xpf-check.v1', log=str(log), slice=str(slice_dir), lanes=str(lanes_path),
                params=str(params_path), measured_hr_lane_edges=meas, elaborated=elab, sidecar=side,
                derived=want, hr_lane=hr and {k: hr.get(k) for k in ('n', 'E', 'E_sta', 'K')}, ctlm_land_faults=lf,
                lag_hist=ll.get('lag_hist'), fails=fails, verdict='PASS' if not fails else 'FAIL')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    a = sp.add_parser('annotate')
    a.add_argument('slice_dir')
    a.add_argument('--lanes', required=True)
    a.add_argument('--zero', action='store_true')
    g = sp.add_parser('ages')
    g.add_argument('--lanes', required=True)
    g.add_argument('--out', required=True)
    g.add_argument('--die')
    c = sp.add_parser('xpf-check')
    c.add_argument('log')
    c.add_argument('--slice', required=True)
    c.add_argument('--lanes', required=True)
    c.add_argument('--params', required=True)
    c.add_argument('--out', required=True)
    x = ap.parse_args()
    if x.cmd == 'annotate':
        annotate(x.slice_dir, x.lanes, x.zero)
    elif x.cmd == 'xpf-check':
        r = xpf_check(x.log, x.slice, x.lanes, x.params)
        Path(x.out).write_text(json.dumps(r, indent=1) + '\n')
        print(f"XPF_CHECK {r['verdict']} measured {r['measured_hr_lane_edges']} elaborated {r['elaborated']} "
              f"sidecar {r['sidecar']} derived {r['derived']} fails {len(r['fails'])}")
        for f in r['fails']:
            print('  FAIL ' + f)
        sys.exit(0 if r['verdict'] == 'PASS' else 1)
    else:
        r = ages(x.lanes, x.die)
        Path(x.out).write_text(json.dumps(r, indent=1) + '\n')
        print(f"LANE_AGES R_CMD {r['R_CMD']} R_HR {r['R_HR']} R_SS {r['R_SS']} R_AG {r['R_AG']} "
              f"XPF_TRANSPORT_EDGES {r['XPF_TRANSPORT_EDGES']}")


if __name__ == '__main__':
    main()
