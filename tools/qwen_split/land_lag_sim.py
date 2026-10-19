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
KVR-LANDLAG 10-19: the KV die (tools/qwen_kv_die/kv_fwd_lanes.py lanes: qkd_rlysh0_<S> hop 0, qkd_rlysh_<S> half-cycle
stations, LANDING qkd_landsh_<S> / qkd_landsh0_<S> = ot_qfd_land D 4 over rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv;
there is no die_glue.sv: the wrappers are that RTL file, the glue is the die netlist case_kv/die.v):

    land_lag_sim.py annotate SLICE_DIR --lanes RUN/fwd_lanes.json [--zero]
        a KV slice (its .f lists qkd_rlysh.sv, no die_glue.sv) -> SLICE_DIR/qkd_rlysh_lag.sv with the qkd_landsh* wrappers on
        ot_qfd_land_lag; landing instances get #(.SIM_LAG(L)) from the lane row of their LAST station (fwd_lanes.json
        'stations'[-1]); L = max(0, E_sta - 2), E_sta = the row's measured E_sta, else E - fwd_e_est(n) + 2 (KV: E =
        E_planned = fwd_e_est(n) until the die STA measures S1, so L = 0).  Same record, fails closed the same way.
    land_lag_sim.py kv-check --die-v case_kv/die.v --lanes RUN/fwd_lanes.json [--relay-stages case_kv/relay_stages.json]
                             [--lane-stations RUN/lane_stations.json] --out case_kv/land_lag.json      (exit 1 on FAIL)
        every forwarded-clock landed crossing of the KV die netlist (one row per landing instance), fail closed on:
          structure  the lane traced on the netlist (landing ckf / ea <- n_<prev>__cko / __eb ... <- the qkd_rlysh0 hop 0,
                     one width S, landsh0 <=> n = 1, the landing read on a core root, the hop 0 on a core root) is not the
                     fwd_lanes.json row (stations, n, S); a netlist landing without a row or a row without a landing;
          strap      the K straps k2..k0 are not the instance's OWN tie_hi / tie_lo, or K != (E + cal + h0(n)) mod 8
                     (lane_groups rule: cal = G - R0, 0 on the KV die (G = R0, kv_fwd_lanes); h0 = HOP0_EN_REG = 1 for an
                     n = 1 landing: ot_qfd_land FIRST=1 registers en on ck_s, QK-LANDEN 10-19);
          window     the age the straps implement, E_hw = (K - cal - h0) (mod 8, the representative nearest the row E), is
                     outside the ring window: E_sta = E_hw - fwd_e_est(n) + 2 must be in [2, D - 1] (2 = the zero-delay
                     arrival; a measured row E_sta must equal it);
          latency    the fixed latency the hardware delivers, L_hw = E_hw + 1 (landing o register) + post_stages (o = w(t - L),
                     tools/qwen_split/bench_fwd_lane.sh; independent of n: the in-band epoch makes the ring absorb the
                     station delay) != the age the KV static compiler charges for the lane, ceil(landed - 1)
                     (kv_static_ages.fwd_overlay / kv_static_params.lane_ages).
        Recorded, never a failure: the n = 1 netlist-table age (netlist_relay_stages: age_edges = K), the generator's
        pre-lane bus stages (relay_stages.json), the plain stages kv_lane_stations inserted outside lanes, and the KV
        registered boundaries that are NOT forwarded-clock rings (slg landing groups qkd_kvs_grp*: landing seg latency 8;
        kvs_attn ATTN_LAND: kv_static_die.ATTN_LAND_EDGES; both priced / checked by kv_static_params, no K strap).
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
    if not any(ln.endswith('/die_glue.sv') for ln in flines) and any(ln.endswith('/' + KV_LANE_RTL) for ln in flines):
        return annotate_kv(S, fl[0], flines, lanes_path, zero)       # KVR-LANDLAG: a KV die slice (no die_glue.sv)
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


# ---------------------------------------------------------------------------------------------------------------------
# KVR-LANDLAG 10-19: the KV die (see the module docstring)
# ---------------------------------------------------------------------------------------------------------------------
KV_LANE_RTL = 'rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv'
KV_LAND_INST = re.compile(r'^(\s*)(qkd_landsh0?_\d+)\s+(\w+)\s*\(', re.M)
KV_LAND_MOD = re.compile(r'^module (qkd_landsh0?_\d+) \(')
KV_FAM = re.compile(r'^qkd_(rlysh0|rlysh|landsh0|landsh)_(\d+)$')
KV_INST = re.compile(r'^\s+(qkd_(?:rlysh0?|landsh0?)_\d+) (\S+) \((.*)\);\s*$')
KV_CONN = re.compile(r'\.(\w+)\(([^()]*)\)')
KV_CORE_CK = re.compile(r'^n_clk_core_(\w+)\[0\]$')
KV_D = 4                                       # qkd_landsh*: ot_qfd_land #(.D(4))
KV_CAL = 0                                     # kv_fwd_lanes: K = E mod 8, i.e. the calendar G - R0 taken as 0


def kv_e(row):
    """the lane's compiled total age E (a land-plan row 'E', else the KV GEN's 'E_planned')"""
    return int(row['E'] if row.get('E') is not None else row['E_planned'])


def kv_e_sta(row):
    """the landing residual: a measured row E_sta, else what the row's E leaves over the zero-delay estimate"""
    if row.get('E_sta') is not None:
        return int(row['E_sta'])
    return kv_e(row) - LG_fwd_e_est(int(row['n'])) + FWD_E0


def LG_fwd_e_est(n):
    """= tools/qwen_rom_fulldie_b3r2.fwd_e_est = kv_fwd_lanes.planned_e (pre-STA E of an n-station lane)"""
    import math
    return max(2, math.ceil((n - 1) / 2) + 1)


def kv_rows(lanes):
    """landing instance (the lane's LAST station) -> fwd_lanes.json row"""
    out = {}
    for r in lanes['lanes']:
        st = r['stations'] if isinstance(r['stations'], list) else json.loads(r['stations'].replace("'", '"'))
        out[st[-1]] = r
    return out


def annotate_kv(S, f, flines, lanes_path, zero):
    wr = [ln for ln in flines if ln.endswith('/' + KV_LANE_RTL)]
    lane_rtl = [ln for ln in flines if ln.endswith('/rtl/qwen_split/qfd_fwd_lane.sv')]
    if len(wr) != 1 or len(lane_rtl) != 1:
        raise SystemExit(f'land_lag_sim: {f}: a KV slice needs exactly one qkd_rlysh.sv and one qfd_fwd_lane.sv ({wr}, {lane_rtl})')
    lanes = json.loads(Path(lanes_path).read_text())
    by_land = kv_rows(lanes)
    out, nmod = [], 0
    for ln in Path(wr[0]).read_text().splitlines():
        m = KV_LAND_MOD.match(ln)
        if m:
            ln = ln.replace(f'module {m.group(1)} (', f'module {m.group(1)} #(parameter integer SIM_LAG = 0) (', 1)
            nmod += 1
        if 'ot_qfd_land #(' in ln:
            ln = ln.replace('ot_qfd_land #(', 'ot_qfd_land_lag #(.LAG(SIM_LAG), ', 1)
        out.append(ln)
    (S / 'qkd_rlysh_lag.sv').write_text('\n'.join(out) + '\n')
    svs = [p for p in S.glob('*.sv') if p.name != 'qkd_rlysh_lag.sv']
    rec, missing = [], []
    for sv in svs:
        t = sv.read_text()

        def sub(m):
            inst = m.group(3)
            r = by_land.get(inst)
            if r is None:
                missing.append(inst)
                return m.group(0)
            es = kv_e_sta(r)
            L = 0 if zero else max(0, es - FWD_E0)
            rec.append(dict(inst=inst, master=m.group(2), bid=r.get('bid') or kv_bid(inst), n=r.get('n'), E=kv_e(r),
                            E_sta=es, K=r.get('K'), LAG=L))
            return f'{m.group(1)}{m.group(2)} #(.SIM_LAG({L})) {inst} ('
        t2 = KV_LAND_INST.sub(sub, t)
        if t2 != t:
            sv.write_text(t2)
    if missing:
        raise SystemExit(f'land_lag_sim: FAIL slice landings without a lane row in {lanes_path}: {missing[:8]} '
                         f'({len(missing)})')
    model = str(Path(lane_rtl[0]).parent / 'ot_qfd_land_lag.sv')
    nf = []
    for ln in flines:
        if ln == wr[0]:
            ln = str((S / 'qkd_rlysh_lag.sv').resolve())
        nf.append(ln)
        if ln == lane_rtl[0]:
            nf.append(model)
    f.write_text('\n'.join(nf) + '\n')
    r = dict(schema='opentallas.qwen.land-lag-sim.v1', die='qwen_kv', slice=str(S), lanes=str(lanes_path),
             lanes_sha256=hashlib.sha256(Path(lanes_path).read_bytes()).hexdigest(), zero=zero,
             rule='LAG = max(0, E_sta - 2) lane-clock periods on the landing write side (sim only, ot_qfd_land_lag.sv); '
                  'KV E_sta = row E_sta, else E - fwd_e_est(n) + 2',
             wrappers=nmod, landings=sorted(rec, key=lambda x: x['inst']),
             lag_hist={str(L): sum(1 for x in rec if x['LAG'] == L) for L in sorted({x['LAG'] for x in rec})})
    (S / 'land_lag.json').write_text(json.dumps(r, indent=1) + '\n')
    print(f"LAND_LAG_SIM KV {'ZERO' if zero else 'PLAN'} wrappers {nmod} landings {len(rec)} lag_hist {r['lag_hist']}")
    return r


def kv_bid(station):
    """= kv_static_ages.lane_bid (rly_<bid>_<k>__s<j>; pin-repair chains rly_pinfix_<bid>_r<i>_<k>)"""
    n = re.sub(r'__s\d+$', '', station)
    n = re.sub(r'^rly_', '', n).rsplit('_', 1)[0]
    return re.sub(r'_r\d+$', '', re.sub(r'^pinfix_', '', n))


def kv_parse(die_v):
    """lane masters of the KV netlist: inst -> (master, fam, S, {port: expr})"""
    insts = {}
    with open(die_v) as fh:
        for ln in fh:
            if 'qkd_rlysh' not in ln and 'qkd_landsh' not in ln:
                continue
            m = KV_INST.match(ln)
            if not m:
                continue
            mst, nm, body = m.groups()
            fm = KV_FAM.match(mst)
            insts[nm] = (mst, fm.group(1), int(fm.group(2)), dict(KV_CONN.findall(body)))
    return insts


def kv_trace(land, insts, by_cko):
    """the lane of a landing on the netlist: [hop 0, ..., landing] + structural problems"""
    probs = []
    mst, fam, S, cs = insts[land]
    chain = [land]
    if fam == 'landsh0':
        return chain, probs
    cur = land
    while True:
        ckf, ea = insts[cur][3].get('ckf', ''), insts[cur][3].get('ea', '')
        m = re.fullmatch(r'n_(\S+)__cko\[0\]', ckf)
        prev = m.group(1) if m else None
        if prev is None or prev not in insts or by_cko.get(ckf) != prev:
            probs.append(f'{cur}: ckf {ckf} is not a lane station ck_o')
            break
        if ea != f'n_{prev}__eb[0]' or insts[prev][3].get('eb') != ea:
            probs.append(f'{cur}: ea {ea} is not the epoch of {prev}')
        if insts[prev][2] != S:
            probs.append(f'{prev}: width {insts[prev][2]} != lane width {S}')
        if prev in chain:
            probs.append(f'{prev}: lane loop')
            break
        chain.insert(0, prev)
        if insts[prev][1] == 'rlysh0':
            break
        if insts[prev][1] != 'rlysh':
            probs.append(f'{prev}: {insts[prev][0]} inside a lane')
            break
        cur = prev
    return chain, probs


def kv_check(die_v, lanes_path, relay_stages=None, lane_stations=None):
    import math
    lanes = json.loads(Path(lanes_path).read_text())
    rows = kv_rows(lanes)
    insts = kv_parse(die_v)
    by_cko = {cs.get('ck_o'): nm for nm, (_, fam, _, cs) in insts.items() if fam in ('rlysh0', 'rlysh')}
    lands = sorted(nm for nm, v in insts.items() if v[1] in ('landsh', 'landsh0'))
    gen = {}
    if relay_stages:
        for b in json.loads(Path(relay_stages).read_text())['buses']:
            if b.get('bid'):
                gen[b['bid']] = max(gen.get(b['bid'], 0), int(b['stages']))
    xs, fails = [], dict(structure=[], strap=[], window=[], latency=[])
    on_lane = set()
    for land in lands:
        mst, fam, S, cs = insts[land]
        chain, probs = kv_trace(land, insts, by_cko)
        on_lane.update(chain)
        n = len(chain)
        r = rows.get(land)
        x = dict(landing=land, master=mst, S=S, n_netlist=n, bid=kv_bid(land), chain_head=chain[0])
        mr = KV_CORE_CK.match(cs.get('ck', ''))
        h0 = insts[chain[0]][3].get('ck_s' if fam == 'landsh0' else 'ck', '')
        ms = KV_CORE_CK.match(h0)
        x['src_tree'], x['dst_tree'] = (ms.group(1) if ms else None), (mr.group(1) if mr else None)
        x['en'] = insts[chain[0]][3].get('en')
        x['rs'] = cs.get('rs')
        if not mr:
            probs.append(f'{land}: read clock {cs.get("ck")} is not a core root')
        if not ms:
            probs.append(f'{chain[0]}: hop-0 clock {h0} is not a core root')
        if (fam == 'landsh0') != (n == 1):
            probs.append(f'{land}: {mst} with n {n}')
        # strap: k2..k0 from the instance's OWN tie cells
        hi, lo = cs.get('tie_hi'), cs.get('tie_lo')
        kb = []
        for q in range(3):
            v = cs.get(f'k{q}')
            kb.append(1 if v == hi else 0 if v == lo else None)
        if None in kb or not hi or not lo or hi == lo:
            fails['strap'].append(f'{land}: K strap k2..k0 not from its own tie_hi / tie_lo '
                                  f'({[cs.get(f"k{q}") for q in range(3)]}, hi {hi}, lo {lo})')
            K = None
        else:
            K = kb[0] | kb[1] << 1 | kb[2] << 2
        x['K_netlist'] = K
        if r is None:
            probs.append(f'{land}: no fwd_lanes.json row')
            fails['structure'] += probs
            x['verdict'] = 'FAIL'
            xs.append(x)
            continue
        rst = r['stations'] if isinstance(r['stations'], list) else json.loads(r['stations'].replace("'", '"'))
        if rst != chain:
            probs.append(f'{land}: netlist lane {chain[:2]}..({n}) != row stations {rst[:2]}..({len(rst)})')
        if int(r['n']) != n or int(r.get('S', S)) != S:
            probs.append(f'{land}: row n {r["n"]} / S {r.get("S")} != netlist n {n} / S {S}')
        if probs:
            fails['structure'] += probs
        E = kv_e(r)
        raw_cal = int(r.get('cal', KV_CAL)) if r.get('cal') is not None else KV_CAL
        h = LG.HOP0_EN_REG if n == 1 else 0
        # Canonical seam tables use cal=G-R0+h0; legacy KV rows use
        # cal=G-R0. Do not add the registered hop-0 epoch twice.
        basis = r.get('cal_basis')
        canonical = basis == 'G-R0+h0' or (basis is None and
                    str(r.get('age_contract', '')).startswith('KVR-FWDAGE: G=R0;'))
        if basis not in (None, 'G-R0', 'G-R0+h0'):
            fails['structure'].append(f'{land}: unknown calendar basis {basis!r}')
        cal = raw_cal - h if canonical else raw_cal
        total_cal = raw_cal if canonical else cal + h
        if canonical and r.get('h0', h) != h:
            fails['structure'].append(f'{land}: recorded h0 {r.get("h0")} != actual lane hop-0 epoch {h}')
        if canonical and r.get('reset_cal', cal) != cal:
            fails['structure'].append(f'{land}: total cal {raw_cal} != reset_cal {r.get("reset_cal")} + h0 {h}')
        k_exp = (E + total_cal) % 8
        x.update(E=E, cal=cal, cal_total=total_cal, cal_basis='G-R0+h0', h0=h, K_row=r.get('K'), K_expected=k_exp, post_stages=int(r.get('post_stages') or 0),
                 inserted_stations=len(r.get('inserted_stations') or []), fwd_e_est=LG_fwd_e_est(n))
        if K is not None and K != k_exp:
            fails['strap'].append(f'{land}: K {K} != (E {E} + cal {cal} + h0 {h}) mod 8 = {k_exp} (n {n})')
        if K is not None:
            v = (K - total_cal) % 8
            E_hw = E + ((v - E + 4) % 8) - 4
            es = E_hw - LG_fwd_e_est(n) + FWD_E0
            x.update(E_hw=E_hw, E_sta_hw=es, LAG=max(0, es - FWD_E0))
            if not (FWD_E0 <= es <= KV_D - 1) or (r.get('E_sta') is not None and int(r['E_sta']) != es):
                fails['window'].append(f'{land}: strap age E_hw {E_hw} -> E_sta {es} outside [{FWD_E0}, {KV_D - 1}] '
                                       f'(fwd_e_est({n}) {LG_fwd_e_est(n)}; row E_sta {r.get("E_sta")})')
            L_hw = E_hw + LG.LAND_O + x['post_stages']
            comp = math.ceil(float(r['landed']) - 1) if r.get('landed') is not None else LG.lane_cycles(r) + x['post_stages']
            x.update(L_hw=L_hw, compiled_age=comp, compiled_rule='ceil(landed - 1)' if r.get('landed') is not None
                     else 'lane_groups.lane_cycles + post_stages', table_age_n1=K if n == 1 else None,
                     gen_stages=gen.get(x['bid']))
            if L_hw != comp:
                fails['latency'].append(f'{land}: hardware lane latency {L_hw} (E_hw {E_hw} + o 1 + post '
                                        f'{x["post_stages"]}) != compiled age {comp} ({x["compiled_rule"]}, landed '
                                        f'{r.get("landed")}, n {n})')
        x['verdict'] = 'PASS' if not any(s.startswith(land + ':') for v in fails.values() for s in v) else 'FAIL'
        xs.append(x)
    for land in sorted(set(rows) - set(lands)):
        fails['structure'].append(f'{land}: fwd_lanes.json row without a netlist landing')
    stray = sorted(nm for nm, v in insts.items() if v[1] in ('rlysh0', 'rlysh') and nm not in on_lane)
    if stray:
        fails['structure'].append(f'{len(stray)} lane stations on no landed lane (e.g. {stray[:4]})')
    with open(die_v) as fh:
        dv = fh.read()
    other = dict(slg_landing_groups=len(re.findall(r'^\s+qkd_kvs_grp\w* ', dv, re.M)),
                 kvs_attn=[m for m in re.findall(r'^\s+(qkd_kvs_attn\w*) ', dv, re.M)],
                 note='registered boundaries, NOT forwarded-clock rings (no K strap): slg = landing seg latency 8 '
                      '(kv_static_ages.LANDING_SEG_LAT), kvs_attn ATTN_LAND = kv_static_die.ATTN_LAND_EDGES / face-landed '
                      '_fl tiles; priced and checked against die.v by kv_static_params (RELAY_CHECK)')
    del dv
    nfail = sum(1 for x in xs if x['verdict'] == 'FAIL')
    from collections import Counter
    rec = dict(schema='opentallas.qwen_kv.land-lag-check.v1', die_v=str(die_v), lanes=str(lanes_path),
               lanes_sha256=hashlib.sha256(Path(lanes_path).read_bytes()).hexdigest(),
               die_v_sha256=hashlib.sha256(Path(die_v).read_bytes()).hexdigest(),
               relay_stages=str(relay_stages) if relay_stages else None, lane_stations=str(lane_stations) if lane_stations else None,
               rules=dict(strap='K = (E + cal + h0(n)) mod 8 (lane_groups; h0 = HOP0_EN_REG for n = 1); straps from the '
                                'instance own tie cells', calendar=f'cal = G - R0 = {KV_CAL} (KV GEN: G = R0; en / rs nets recorded)',
                          window=f'E_sta = E_hw - fwd_e_est(n) + 2 in [{FWD_E0}, {KV_D - 1}]',
                          latency='L_hw = E_hw + 1 + post_stages == compiled ceil(landed - 1)',
                          lag='annotate LAG = max(0, E_sta - 2)'),
               crossings=len(xs), failing_crossings=nfail,
               fail_counts={k: len(v) for k, v in fails.items()}, fails={k: v[:200] for k, v in fails.items()},
               by_n_E_K=sorted([list(k) + [c] for k, c in Counter((x['n_netlist'], x.get('E'), x['K_netlist'])
                                                                   for x in xs).items()], key=lambda z: (z[0], str(z[1]))),
               latency_delta_hist={str(k): c for k, c in sorted(Counter(x['compiled_age'] - x['L_hw'] for x in xs
                                                                        if 'L_hw' in x).items())},
               lag_hist={str(k): c for k, c in sorted(Counter(x.get('LAG') for x in xs if 'LAG' in x).items())},
               plain_added_stages=lanes.get('plain_added_stages') or {}, other_landings=other,
               crossings_detail=xs, verdict='PASS' if not any(fails.values()) else 'FAIL')
    if lane_stations:
        ls = json.loads(Path(lane_stations).read_text())
        rec['lane_stations_summary'] = ls.get('summary')
    return rec


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
    k = sp.add_parser('kv-check')
    k.add_argument('--die-v', required=True)
    k.add_argument('--lanes', required=True)
    k.add_argument('--relay-stages')
    k.add_argument('--lane-stations')
    k.add_argument('--out', required=True)
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
    elif x.cmd == 'kv-check':
        r = kv_check(x.die_v, x.lanes, x.relay_stages, x.lane_stations)
        Path(x.out).write_text(json.dumps(r, indent=1) + '\n')
        for k_, v in r['fails'].items():
            for s in v[:3]:
                print(f'  FAIL {k_}: {s}')
        print(f"LAND_LAG_KV {r['verdict']} crossings {r['crossings']} failing {r['failing_crossings']} "
              f"(structure {r['fail_counts']['structure']}, strap {r['fail_counts']['strap']}, window "
              f"{r['fail_counts']['window']}, latency {r['fail_counts']['latency']}) compiled-hw latency delta "
              f"{r['latency_delta_hist']} lag {r['lag_hist']} -> {x.out}")
        sys.exit(0 if r['verdict'] == 'PASS' else 1)
    else:
        r = ages(x.lanes, x.die)
        Path(x.out).write_text(json.dumps(r, indent=1) + '\n')
        print(f"LANE_AGES R_CMD {r['R_CMD']} R_HR {r['R_HR']} R_SS {r['R_SS']} R_AG {r['R_AG']} "
              f"XPF_TRANSPORT_EDGES {r['XPF_TRANSPORT_EDGES']}")


if __name__ == '__main__':
    main()
