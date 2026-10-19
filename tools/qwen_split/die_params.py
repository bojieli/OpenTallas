#!/usr/bin/env python3
"""QLB-GEN 10-18 (LAYERBENCH-QWEN G-C1): compiler-assigned elaboration parameters of the Qwen compute-die masters.

The die netlist names every hardened master by its base module (OpenSTA reads no #(...) overrides), so the parameters a
master is elaborated with go to the sidecar DIE_V.params.json (tools/die_port_bind.py --params; the GEN writes it from
m['die_master_params'], tools/qwen_tp8/relay_data_run.py).  Two compute-die masters carry a SENTINEL default that traps
elaboration until the compiler assigns the value from the die as built:

  qfd_tt_ctlm_dv.XPF_TRANSPORT_EDGES (default -1 -> g_unassigned_arm_route $error at t = 0, LAYERBENCH G-C1)
      = the die pipeline from the xpf registered pins to the tap in the W5 slice column: the hr pin register (one edge,
        rtl/qwen_dv/qfd_tt_ctlm_dv.sv header: 'XPF_TRANSPORT_EDGES included') + the lane cycles of the tt_ctlm.hr ->
        dvs_W5 bus as built (tools/qwen_split/lane_groups.lane_cycles: forwarded lane E + 1 landing o register, plain
        relay chain n, direct 0).  ot_qfd_xpf_static_schedule checks every compiled arm cycle >= issue + this + 3.
  qfd_d2d_static.TXDP (default 0 with PR 1 -> D2D_TXDP_NOT_COMPILED module trap, QXF-LINK 6ef1a097f)
      = the compiler's per-TX-port producer capture latency, D2D_TXDP_C of the production die-sequencer image
        rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh (tools/qwen_split/d2d_cal_image_production.sh); the image
        records the die seam stages it was compiled with, and the layer compiler (tools/qwen_layerbench/layer_compile.py)
        re-derives TXD from the die-run table -- a die whose seam stages moved needs a recompiled image.

    die_params.py audit DIE_V --port-bind port_bind.json [--params DIE_V.params.json] [--lanes fwd_lanes.json] --out A.json
        fail closed (exit 1): (a) every die master whose RTL traps a sentinel-default parameter (a generate-if whose body
        raises $error / $fatal or instantiates a *NOT_COMPILED* / *__set_* trap module) must get that parameter from the
        sidecar, with a non-sentinel value; (b) XPF_TRANSPORT_EDGES == 1 + the hr lane cycles re-derived from die.v (+
        fwd_lanes.json E); (c) TXDP == D2D_TXDP_C of the committed image (all four bytes nonzero); (e) MU-DQ-TXDP: TXDP == the compiler's TXD C
        for THIS die's seam stages re-derived from die.v + fwd_lanes.json (record_bundles.seam_stages), and the image's
        recorded compute die stages == those stages.
"""
import os
import argparse
import ast
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'tools'))
import lane_groups as LG  # noqa: E402

TT_MASTER, TT_PORT, TT_SINK = 'qfd_tt_ctlm_dv', 'hr', 'dvs_W5'
TT_STAGE_ME = 1                                  # Q-DIE14 (QLB-PROG 3fac5f0ef): the compiled ctlm image needs STAGE_ME 1
HR_PIN_REG = 1                                   # qfd_tt_ctlm_dv: hr is one register after xpf (header 'hr -> W5 hr_wi')
D2D_MASTER = 'qfd_d2d_static'
DHOBS_MASTER = 'qfd_sys_face_mu_dhobs'           # MU-DQ-DHUSER: the die's tt_ctlm.dh_user observer (dv_case.DHOBS)
DHOBS_LISTS = ('NS', 'USER_SEQ', 'STG_SEQ', 'RES_SEQ')
IMAGE = ROOT / 'rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh'
TRAP_BODY = re.compile(r'\$error|\$fatal|\w*NOT_COMPILED\w*|\w+__set_\w+')
GEN_IF = re.compile(r'generate\s+if\s*\(', re.S)
SENTINELS = (-1, 0)


# ------------------------------------------------------------------------------------------------------------ values
def lane_age(row):
    """core edges a bus adds between its two blocks (None = reset lane: no data age)."""
    if row is None:
        return 0
    return LG.lane_cycles(row)


def xpf_transport_edges(hr_rows):
    """hr_rows: [(bid, row-or-None)] -- every bus leaving tt_ctlm.hr toward the W5 column (row None = direct wire).
    -> (T, record).  One bus, one latency: hr feeds ONE consumer column; several sink buses must agree."""
    if not hr_rows:
        raise ValueError(f'{TT_MASTER}.{TT_PORT}: no bus from the hr pins (no XPF transport to assign)')
    ages = {bid: lane_age(r) for bid, r in hr_rows}
    if None in ages.values() or len(set(ages.values())) != 1:
        raise ValueError(f'{TT_MASTER}.{TT_PORT}: hr buses arrive on different edges {ages} (one latency per bus)')
    age = next(iter(ages.values()))
    rows = [dict(bid=bid, kind='direct' if r is None else ('fwd' if r.get('E') is not None else 'plain'),
                 n=None if r is None else r.get('n'), E=None if r is None else r.get('E'),
                 K=None if r is None else r.get('K'), lane_cycles=ages[bid]) for bid, r in hr_rows]
    # Q-XPF 10-18: a land-plan lane (E_sta > 2) is reproduced by a netlist bench only with its lane timing
    # (tools/qwen_split/land_lag_sim.py annotate: LAG = E_sta - 2); the zero-delay netlist aliases E by the ring depth
    # D 4 when E_sta > 3 (dv2f14bi hr: E 18 reads as 14 -> XPF 20 measured as 16).  The value assigned is the plan's.
    lag = {bid: max(0, int(r.get('E_sta') or 2) - 2) for bid, r in hr_rows if r is not None and r.get('E') is not None}
    return HR_PIN_REG + age, dict(XPF_TRANSPORT_EDGES=HR_PIN_REG + age, hr_pin_register=HR_PIN_REG, lane_cycles=age,
                                  buses=rows, rule='1 (hr pin register) + lane_groups.lane_cycles(hr bus): fwd E + 1, '
                                                   'plain n, direct 0',
                                  sim_lag=lag, bench_rule='measure with land_lag_sim.py annotate (LAG = E_sta - 2) + '
                                  'xpf-check: 1 + measured == XPF; the zero-delay netlist aliases when E_sta > D - 1')


def txdp_from_image(path=IMAGE):
    t = Path(path).read_text()
    m = re.search(r"localparam\s*\[31:0\]\s*D2D_TXDP_C\s*=\s*32'h([0-9a-fA-F_]+)\s*;(.*)", t)
    if not m:
        raise ValueError(f'{path}: no D2D_TXDP_C line')
    v = int(m.group(1).replace('_', ''), 16)
    if any(((v >> (8 * p)) & 0xff) == 0 for p in range(4)):
        raise ValueError(f'{path}: D2D_TXDP_C {v:#010x} has an uncompiled (0) port')
    st = re.search(r"die stages (\{.*\})", m.group(2))
    return v, dict(TXDP=v, image=str(Path(path).relative_to(ROOT)) if str(path).startswith(str(ROOT)) else str(path),
                   ports=[(v >> (8 * p)) & 0xff for p in range(4)], die_stages=st.group(1) if st else None)


def gen_params(insts, hr_rows, image=IMAGE):
    """the GEN's assignments: insts = [(name, master)] of the die model -> {master: {param: value, _source}}."""
    masters = {mst for _, mst in insts}
    out, rec = {}, {}
    if TT_MASTER in masters:
        T, r = xpf_transport_edges(hr_rows)
        out[TT_MASTER] = dict(XPF_TRANSPORT_EDGES=T, STAGE_ME=TT_STAGE_ME,
                              _source='QLB-GEN G-C1: 1 hr pin register + hr lane cycles as built '
                              f"({', '.join(f'{b[0]} {b[1]}' for b in [(x['bid'], x['kind']) for x in r['buses']])}); "
                              'Q-DIE14: STAGE_ME 1 = the QLB-PROG deployment image (one image runs every stage)')
        rec['xpf'] = r
    # MU-DIE-QW 10-19 (owner 0kc: the release die is the multi-user die): OT_QWEN_MU_NU = users (2..4) elaborates the MU
    # RTL on this die: tt_ctlm NU + OPSEG 1 (MU-QW-B1 option 2: in-cluster op-start leaf, calendar qfd_dv_cmd_cal_mu) and
    # the slices' per-user LM-head argmax MU_NU (MU-ADOPT-SLICE; the slice2_e / slice2_wh kits are gated at MU_NU 4).
    # Strides stay the RTL defaults = tools/qwen_static_schedule/mu_calendar.py DV_UVM_STRIDE / DV_PIDX_STRIDE / UTAG_LSB.
    nu = int(os.environ.get('OT_QWEN_MU_NU', '1') or 1)
    if nu > 1:
        if not 2 <= nu <= 4:
            raise ValueError(f'OT_QWEN_MU_NU {nu} outside 2..4')
        src = f'MU-DIE-QW: OT_QWEN_MU_NU={nu} (owner 0kc release MU die; MU-QW-B1 OPSEG 1, MU-ADOPT-SLICE MU_NU)'
        if TT_MASTER in masters:
            out[TT_MASTER].update(NU=nu, OPSEG=1)
            out[TT_MASTER]['_source'] += '; ' + src
        for sm in ('qfd_dv_slice2_w', 'qfd_dv_slice2_e'):
            if sm in masters:
                out[sm] = dict(MU_NU=nu, _source=src)
        rec['mu'] = dict(nu=nu, opseg=1)
        if 'qfd_sys_face' in masters:
            # MU-DQ-SYSFACE (COORD 0kg (a)): qfd_sys_face #(MU 1) = MU d2d image (ot_qwen_d2d_cal_seq_dies_mu.sv) + filler
            # head contexts accepted by user on tt_native_pos[17:16]; the die stand-in view stays the MU 0 rs3 view until mu1 closes
            out['qfd_sys_face'] = dict(MU=1, _source='MU-DQ-SYSFACE 57d2bf14c: MU d2d image + filler head contexts '
                                       '(view of record pending mu1 re-close: STAND-IN)')
            rec['mu']['sys_face_mu'] = 1
        if DHOBS_MASTER in masters:
            # NU from the die; the compiled lists are the RTL defaults (384-b / 128-b vectors: no sidecar literal), checked
            # against mu_opcal.dhobs_lists by audit (e)
            out[DHOBS_MASTER] = dict(NU=nu, _source='MU-DQ-DHUSER (COORD 0kg): tt_ctlm.dh_user observer, OPSEG 0; NS / '
                                     'USER_SEQ / STG_SEQ / RES_SEQ = RTL defaults = mu_opcal.dhobs_lists(compile_frame(16))')
            rec['dhobs'] = dict(nu=nu)
    if D2D_MASTER in masters:
        v, r = txdp_from_image(image)
        out[D2D_MASTER] = dict(TXDP=v, _source=f"QXF-LINK/QLB-GEN: D2D_TXDP_C of {r['image']} (die stages {r['die_stages']})")
        rec['txdp'] = r
    return out, rec


# ------------------------------------------------------------------------------------------------------------ RTL traps
def dhobs_check(mod, frame=16):
    """(e) the observer's RTL default lists == the compiled 4-user calendar's (mu_opcal.dhobs_lists): a drift between the
    face's T image and the observer's list would raise mu_fault on the die.  -> list of failures."""
    from qwen_static_schedule import mu_opcal as O
    want = O.dhobs_lists(O.compile_frame(frame))
    env = mod.env()
    return [f'{DHOBS_MASTER}.{k} = {env.get(k)!r} (RTL default) != {want[k]:#x} compiled (mu_opcal.dhobs_lists F{frame})'
            for k in DHOBS_LISTS if env.get(k) != want[k]]


def trapped_params(mod):
    """sentinel-default parameters a module traps on: identifiers of a generate-if condition whose body raises."""
    import die_port_bind as DPB
    body = DPB.strip_comments(mod.body)
    env = mod.env()
    out = {}
    for m in GEN_IF.finditer(body):
        j = m.end() - 1
        k = DPB._closing_paren(body, j)
        cond = body[j + 1:k]
        blk = body[k + 1:k + 400]
        end = re.search(r'\bend\b', blk)
        if not TRAP_BODY.search(blk[:end.start() if end else len(blk)]):
            continue
        for p in sorted(set(re.findall(r'[A-Za-z_]\w*', cond)) & set(mod.params)):
            if env.get(p) in SENTINELS:
                out[p] = dict(default=mod.params[p], condition=' '.join(cond.split()))
    return out


def audit(die_v, port_bind, params=None, lanes=None, image=IMAGE, src=ROOT, compiled=None):
    import die_port_bind as DPB
    import lane_latency_audit as LLA
    pj = Path(params) if params else Path(str(die_v) + '.params.json')
    prm = json.loads(pj.read_text()).get('masters', {}) if pj.exists() else {}
    pb = json.loads(Path(port_bind).read_text())
    fails, req = [], {}
    for mst, r in sorted(pb['masters'].items()):
        path = r.get('rtl')
        if not path:
            continue                                   # model / no RTL (die_port_bind reports it)
        path = str(path if Path(path).is_absolute() else Path(src) / path)
        if not Path(path).exists():
            fails.append(f'{mst}: RTL {path} not found (cannot audit its parameters)')
            continue
        mods = {m_.name: m_ for m_ in DPB.parse_modules(Path(path).read_text(errors='replace'), path)}
        if mst not in mods:
            continue
        if mst == DHOBS_MASTER:
            fails += dhobs_check(mods[mst])
            if prm.get(mst, {}).get('NU') != prm.get(TT_MASTER, {}).get('NU'):
                fails.append(f'{mst}.NU {prm.get(mst, {}).get("NU")} != {TT_MASTER}.NU {prm.get(TT_MASTER, {}).get("NU")}')
        tp = trapped_params(mods[mst])
        if not tp:
            continue
        req[mst] = tp
        for p, d in tp.items():
            v = prm.get(mst, {}).get(p)
            if v is None:
                fails.append(f'{mst}.{p}: trapped sentinel parameter (default {d["default"]}, trap if {d["condition"]}) '
                             f'not assigned in {pj.name if pj.exists() else "the params sidecar (missing)"}')
            elif v in SENTINELS:
                fails.append(f'{mst}.{p} = {v}: the sentinel value')
    # (b) XPF re-derived from the netlist as built
    text = Path(die_v).read_text()
    ins = {m.group(2): (m.group(1), dict(re.findall(r'\.(\w+)\(([^()]*)\)', m.group(3))))
           for m in re.finditer(r'^\s*(\w+)\s+(\w+)\s*\((.*)\);\s*$', text, re.M)}
    xr = None
    tt = [(n, c) for n, (mst, c) in ins.items() if mst == TT_MASTER]
    if tt:
        net = LLA.parse(die_v)
        fl = {r['bid']: r for r in (json.loads(Path(lanes).read_text()).get('lanes', []) if lanes and Path(lanes).exists() else [])}
        hr_net = tt[0][1].get(TT_PORT)
        rows = []
        if hr_net is None:
            fails.append(f'{TT_MASTER}.{TT_PORT} not connected in die.v')
        else:
            bid = hr_net[2:] if hr_net.startswith('n_') else hr_net
            sink = [(n, p) for n, (mst, c) in ins.items() if n != tt[0][0] and not n.startswith('rly_')
                    for p, x in c.items() if re.sub(r'__r\d+$', '', x) == hr_net]
            L = net.get(bid)
            if L is None:
                rows.append((bid, None))
            elif 'fwd' in L['kind']:
                E = (fl.get(bid) or {}).get('E')
                if E is None:
                    fails.append(f'{bid}: forwarded hr lane without an E (no fwd_lanes.json record)')
                rows.append((bid, dict(n=L['n'], E=E, K=L['K'])))
            else:
                rows.append((bid, dict(n=L['n'], E=None, K=None)))
            if not sink:
                fails.append(f'{bid}: no consumer of the hr bus in die.v')
        try:
            T, xr = xpf_transport_edges(rows) if rows and all(r is None or r.get('E') is not None or r.get('n') for _, r in rows) else (None, None)
        except ValueError as e:
            T = None
            fails.append(str(e))
        if xr is not None:
            xr['sinks'] = [f'{n}.{p}' for n, p in sink]
        got = prm.get(TT_MASTER, {}).get('XPF_TRANSPORT_EDGES')
        if T is not None and got is not None and int(got) != T:
            fails.append(f'{TT_MASTER}.XPF_TRANSPORT_EDGES {got} != {T} re-derived from die.v (1 hr reg + lane cycles '
                         f'{xr["lane_cycles"]})')
    # (b2) Q-DIE14: tt_ctlm runs the QLB-PROG deployment image (ctlm_image.py) -> STAGE_ME must be 1 (as built 0 starts
    # the layer programme in stage 0 and faults 'start while active' in stage 1)
    if tt and prm.get(TT_MASTER, {}).get('STAGE_ME') != TT_STAGE_ME:
        fails.append(f'{TT_MASTER}.STAGE_ME = {prm.get(TT_MASTER, {}).get("STAGE_ME")} (the deployment image needs {TT_STAGE_ME})')
    # (c) TXDP == the committed production image
    tr = None
    if any(mst == D2D_MASTER for mst, _ in ins.values()):
        try:
            v, tr = txdp_from_image(image)
            got = prm.get(D2D_MASTER, {}).get('TXDP')
            if got is not None and int(got) != v:
                fails.append(f'{D2D_MASTER}.TXDP {int(got):#010x} != image D2D_TXDP_C {v:#010x}')
        except ValueError as e:
            fails.append(str(e))
    # (e) MU-DQ-TXDP 10-19 (COORD 0ki): TXDP against THIS die's seam as built.  The compute seam stages are re-derived
    # from die.v + fwd_lanes.json (record_bundles.seam_stages: tx_slot / rx_record / kv_x3_slot / tx_record / x3_record
    # lane cycles); the compiler's TXD C (d2d_link_calendar.producer_txd + PINREG_EXT) for those stages must equal the
    # bound TXDP, and the image must have been compiled for those stages (its RX calendar depends on them).  dv2f18mu
    # landed kv_x3_slot at E 2 (3 cycles) and bound the CS_X3S 2 image's 0x09010308: the seam co-sim faulted (KVN abort).
    if tr is not None:
        import record_bundles as RB
        import d2d_link_calendar as DLC
        st, srec, sprob = RB.seam_stages(die_v, lanes)
        tr['seam'] = srec
        if sprob:
            fails.extend(f'TXDP seam: {x}' for x in sprob)
        else:
            full = dict(st, **{k: 0 for k in DLC.STAGE_NAMES if k not in st})
            want = [x + q for x, q in zip(DLC.producer_txd(full)['C'], DLC.PINREG_EXT['C'])]
            wv = DLC.txdp_word(want)
            tr.update(seam_txd_c=want, seam_txdp=wv, seam_stages=RB.seam_stages_str(st))
            got = prm.get(D2D_MASTER, {}).get('TXDP')
            if got is not None and int(got) != wv:
                fails.append(f'{D2D_MASTER}.TXDP {int(got):#010x} != {wv:#010x} = TXD C {want} compiled for THIS die\'s '
                             f'seam (stages {RB.seam_stages_str(st)}): recompile the pair image with D2D_DIE_STAGES='
                             f'{RB.seam_stages_str(st)}/<KV seam> tools/qwen_split/d2d_cal_image_production.sh and re-GEN')
            img = tr.get('die_stages')
            try:
                ist = ast.literal_eval(img) if img else None
            except (ValueError, SyntaxError):
                ist = None
            if not isinstance(ist, dict):
                fails.append(f'TXDP seam: image {tr["image"]} records no die stages (cannot prove it was compiled for this seam)')
            else:
                bad = {k: (ist.get(k), v) for k, v in st.items() if ist.get(k) != v}
                if bad:
                    fails.append(f'image {tr["image"]} compiled for another compute seam: (image, die) {bad}')
    # (d) the layer compiler's TXD for THIS die (tools/qwen_layerbench/layer_compile.py manifest on this die's table):
    # the image's die stages must be this die's seam ages, else the D2D calendar is compiled for another die
    if compiled and tr is not None:
        man = json.loads(Path(compiled).read_text())
        want = man['txd']['C']
        wv = sum(int(x) << (8 * i) for i, x in enumerate(want))
        tr.update(compiled_txd_c=want, compiled_stages=man.get('stages'), compiled_manifest=str(compiled))
        got = prm.get(D2D_MASTER, {}).get('TXDP')
        if got is not None and int(got) != wv:
            fails.append(f'{D2D_MASTER}.TXDP {int(got):#010x} != {wv:#010x} = the layer compiler\'s TXD {want} for this die '
                         f'(stages {man.get("stages")}); recompile the image: D2D_DIE_STAGES=<these stages> '
                         'tools/qwen_split/d2d_cal_image_production.sh')
    return dict(schema='opentallas.qwen_split.die_param_audit.v1', die_v=str(die_v), params=str(pj) if pj.exists() else None,
                lanes=str(lanes) if lanes else None, trapped=req, xpf=xr, txdp=tr,
                assigned={m: {k: v for k, v in p.items() if not k.startswith('_')} for m, p in prm.items()},
                verdict='FAIL' if fails else 'PASS', fails=fails)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    a_ = sp.add_parser('audit')
    a_.add_argument('die_v')
    a_.add_argument('--port-bind', required=True)
    a_.add_argument('--params')
    a_.add_argument('--lanes')
    a_.add_argument('--image', default=str(IMAGE))
    a_.add_argument('--src', default=str(ROOT), help='source root the port-bind record\'s relative RTL paths resolve against')
    a_.add_argument('--compiled', help='layer_compile.py manifest.json compiled on this die (TXD check)')
    a_.add_argument('--out')
    a = ap.parse_args(argv)
    lanes = a.lanes or (str(Path(a.die_v).parent / 'fwd_lanes.json') if (Path(a.die_v).parent / 'fwd_lanes.json').exists() else None)
    rec = audit(a.die_v, a.port_bind, a.params, lanes, a.image, a.src, a.compiled)
    if a.out:
        Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    for f in rec['fails']:
        print('FAIL ' + f)
    x = rec['xpf'] or {}
    print(f"DIE_PARAM_AUDIT {rec['verdict']} trapped={sum(len(v) for v in rec['trapped'].values())} "
          f"XPF_TRANSPORT_EDGES={x.get('XPF_TRANSPORT_EDGES')} TXDP={hex(rec['txdp']['TXDP']) if rec['txdp'] else None} "
          f"fails={len(rec['fails'])}")
    return 0 if rec['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
