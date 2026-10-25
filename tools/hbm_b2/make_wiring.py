#!/usr/bin/env python3
"""HBM-BIND (2026-10-24): write the machine-readable B2 bind delta (results/arch/hbm_arch_1024/b2_bind_wiring.json)
that tools/hbm_b2/b2_top.py applies to the r18h5 as-built die to get the 8-SM B2 die top (NW + NE + die level).

    python3 tools/hbm_b2/make_wiring.py --die physical/die_plan/hbm/bind/inputs/die_r18h5.v.gz \
        --asbuilt physical/die_plan/hbm/bind/asbuilt.json [--rtl-items RTL.json] --out b2_bind_wiring.json

Every entry is derived from the r18h5 netlist itself (transport-collapsed sources), so the delta is reproducible.
Items (see `items` in the output for status / owner):
  W-RING   COLL ring A (hb_coll pr_*) and ring B (hcollb cw/ccw): 4-stop rings -> 2-stop NW<->NE rings (wiring; the
           compiler's ring programme (tx_dst / ttl / forward) addresses qid 2 / 3 only).
  W-OBS    observation chain ingress -> obs_C -> obs_NE -> obs_NW -> ingress (obs_SW / obs_SE leave; LIDs unchanged, the
           ingress waits for the returning packet, so the chain length is not scheduled).
  W-HLEAF  status of die-level targets the S-quadrant leaves carried (col_su, col_idx, hc_eng, ep_S* faults) re-homed
           onto hleaf_NE / hleaf_NW (ot_hbm_host_cfg_leaf2 NT / NF params); host_status (ot_hbm_status_join_fa) slots
           compacted over the surviving drivers, TGTS target ids carried with their slots.
  W-CFG    col_su cfg / desc / launch from hleaf_NE copy group a (was hleaf_SE a); c_busy / c_done from pgp_NW (SU
           programme part 0 in B2; was pgp_SW).
  W-EP     S-edge SerDes endpoints re-attached: ep_S0 / ep_S1 to hb_coll_NW (now ot_hfd_coll_q3_hard_v8x NLINK 3:
           lanes N0, S0, S1; it also takes the TKM interface to tkm_SW and the ARGMAX engine, the as-built SW role),
           ep_S3 to hb_coll_NE (ot_hfd_coll_q2_hard_v8g NLINK 2: lanes N2, S3); link calendars epcal_NW W 57 /
           epcal_NE W 38 (param only, same per-endpoint 19-bit field).  PLAN CHANGE: the two hub COLL masters differ.
  W-RID    hb_router_ids run_v / run_layer from cp_svg_NW0 (was cp_svg_SW0; same ot_static_run_target master).
  P-VMST   vm_status4 NQ 2 (exists, bench run_vms_status_nq.sh).
  RTL items (VM ring stop NSTOP 2, IDX / argmax 2-quadrant, SU tree / programme root, HC root) come from --rtl-items
  (the sub-agents' binding tables) and are merged in as `remaster` / `port_map` / `rebuild` entries.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2_top as T  # noqa: E402

KEEPQ = ('NW', 'NE')


def src_list(die, inst, port):
    """resolved LSB-first source list of a leaf input: [[src_inst, src_port, lo, hi] | ['const', w, v]]."""
    i = die.insts[inst]
    segs = T.parse_expr(i['conns'][port], die.widths)
    out = []
    for s, _ in die.resolve(segs):
        if s[0] == 'c':
            out.append(['const', s[1], s[2]])
        else:
            si, sp = s[1].rsplit('__', 1) if '__' in s[1] else (None, s[1])
            out.append([si, sp, s[2], s[3]])
    return out


def is_kept(n):
    m = T.QTAG.search(n)
    return m is None or m.group(1) in KEEPQ or n == 'tkm_SW'


def one(si, sp, w=1, lo=0):
    return [si, sp, lo, lo + w - 1]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--die', required=True)
    ap.add_argument('--asbuilt', required=True)
    ap.add_argument('--rtl-items', action='append', default=[])
    ap.add_argument('--delays', help='b2_delays.json (tools/hbm_b2/b2_delays.py): B2-derived transport-delay params')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ab = json.loads(Path(a.asbuilt).read_text())
    die = T.Die(a.die, ab['transport'])
    remaster, rebuild, port_map, out_width, add_ports, drop_ports = {}, {}, {}, {}, {}, {}
    out_remap = {}
    items = []
    clk = ['hb_ckgen', 'pll_stream', 0, 0]

    # ---- W-RING
    for a_, b_, ci, co in (('hb_coll_NE', 'hb_coll_NW', 'pr_cw_i', 'pr_cw_o'), ('hb_coll_NW', 'hb_coll_NE', 'pr_ccw_i', 'pr_ccw_o'),
                           ('hcollb_NE', 'hcollb_NW', 'cw_i', 'cw_o'), ('hcollb_NW', 'hcollb_NE', 'ccw_i', 'ccw_o')):
        rebuild.setdefault(a_, {})[ci] = [[b_, co, 0, 279]]
    items.append(dict(id='W-RING', kind='wiring', status='done',
                      what='COLL ring A hb_coll_{NW,NE}.pr_* and ring B hcollb_{NW,NE}.cw/ccw closed as 2-stop rings: '
                           'NW.cw_o->NE.cw_i (new), NE.cw_o->NW.cw_i (as built), NE.ccw_o->NW.ccw_i (new), '
                           'NW.ccw_o->NE.ccw_i (as built); qid straps 2/3 unchanged; ring programme addresses qid 2/3 only'))

    # ---- W-OBS
    rebuild.setdefault('obs_NE', {}).update(q_v=[one('obs_C', 'r_v')], q_idx=[one('obs_C', 'r_idx', 8)],
                                             q_d=[one('obs_C', 'r_d', 32)])
    items.append(dict(id='W-OBS', kind='wiring', status='done',
                      what='observation ring ingress->obs_C->obs_NE->obs_NW->ingress (LID 0/3/4 kept; LID 1/2 absent: '
                           'host reads of SW/SE words return d=0 unmatched)'))

    # ---- W-HLEAF + host_status compaction
    hs = die.insts['host_status']
    tr = src_list(die, 'host_status', 't_ready')
    nt_old = sum(e[3] - e[2] + 1 for e in tr)
    tg = re.search(r"\.TGTS\((\d+)'h([0-9a-fA-F]+)\)", hs['params'])
    tgts = int(tg.group(2), 16)
    slot_id = {}
    k = 0
    for e in tr:   # (src, port, bit) -> target id, in old slot order
        for b in range(e[2], e[3] + 1):
            slot_id[(e[0], e[1], b)] = (tgts >> (8 * k)) & 0xFF
            k += 1
    assert k == nt_old
    # hleaf inputs: old lists, dropped sources removed, S-leaf survivors appended
    leaf_new = {}
    moved = {'hleaf_NE': [], 'hleaf_NW': []}
    for q in ('SW', 'SE'):
        for p in ('t_ready', 't_active', 't_fault'):
            for e in src_list(die, f'hleaf_{q}', p):
                if e[0] != 'const' and is_kept(e[0]):
                    tgt_leaf = 'hleaf_NW' if e[0] in ('ep_S0', 'ep_S1') else 'hleaf_NE'
                    moved[tgt_leaf].append((p, e, q))
    sid_of_leaf_slot = {}
    for L in ('hleaf_NW', 'hleaf_NE'):
        cur = {p: [e for e in src_list(die, L, p)] for p in ('t_ready', 't_active', 't_fault')}
        q_old = L.split('_')[1]
        for p, e, q in moved[L]:
            cur[p].append(e)
        nt, nf = sum(e[3] - e[2] + 1 for e in cur['t_ready']), sum(e[3] - e[2] + 1 for e in cur['t_fault'])
        assert nt == sum(e[3] - e[2] + 1 for e in cur['t_active'])
        leaf_new[L] = (nt, nf)
        rebuild.setdefault(L, {}).update(cur)
        remaster[L] = dict(master='ot_hbm_host_cfg_leaf2', params=f'.NT({nt}), .NF({nf})')
        out_width[L] = dict(s_ready=nt, s_active=nt, s_fault=nf)
    # target id of every new hleaf slot: the old host_status slot of (old S leaf, its s_ready bit) -> id
    def old_leaf_slot_id(qleaf, bit):
        return slot_id[(qleaf, 's_ready', bit)]
    hs_ready, hs_active, hs_fault, ids = [], [], [], []
    for e in tr:
        if e[0] in ('hleaf_SW', 'hleaf_SE'):
            continue
        if e[0] in ('hleaf_NW', 'hleaf_NE'):
            continue
        if is_kept(e[0]):
            hs_ready.append(e)
            ids += [slot_id[(e[0], e[1], b)] for b in range(e[2], e[3] + 1)]
    ta = [e for e in src_list(die, 'host_status', 't_active') if e[0] not in ('hleaf_SW', 'hleaf_SE', 'hleaf_NW', 'hleaf_NE')
          and is_kept(e[0])]
    hs_active = ta
    for L in ('hleaf_NW', 'hleaf_NE'):
        nt, nf = leaf_new[L]
        hs_ready.append([L, 's_ready', 0, nt - 1]); hs_active.append([L, 's_active', 0, nt - 1])
        # ids: original slots of L keep theirs; appended slots take the id they had under their S leaf
        q_old = L.split('_')[1]
        nold = sum(e[3] - e[2] + 1 for e in src_list(die, L, 't_ready'))
        ids += [slot_id[(L, 's_ready', b)] for b in range(nold)]
        # appended t_ready entries, in append order, map to their S-leaf slot position
        used = set()
        for p, e, q in moved[L]:
            if p != 't_ready':
                continue
            sl = src_list(die, f'hleaf_{q}', 't_ready')
            pos, base = None, 0
            for x in sl:   # k-th occurrence of a repeated source (hc_eng.configured x2) takes the k-th slot
                if x[0] == e[0] and x[1] == e[1] and x[2] <= e[2] <= x[3] and (q, base + e[2] - x[2]) not in used:
                    pos = base + e[2] - x[2]
                    break
                base += x[3] - x[2] + 1
            assert pos is not None, e
            used.add((q, pos))
            ids.append(old_leaf_slot_id(f'hleaf_{q}', pos))
    assert len(set(ids)) == len(ids), 'duplicate host_status target id'
    tf = [e for e in src_list(die, 'host_status', 't_fault') if e[0] not in ('hleaf_SW', 'hleaf_SE', 'hleaf_NW', 'hleaf_NE')
          and is_kept(e[0])]
    for L in ('hleaf_NW', 'hleaf_NE'):
        tf.append([L, 's_fault', 0, leaf_new[L][1] - 1])
    hf = [e for e in src_list(die, 'host_status', 'h_fault') if e[0] == 'const' or is_kept(e[0])]
    af = [e for e in src_list(die, 'host_status', 'a_fault') if e[0] == 'const' or is_kept(e[0])]
    nt = sum(e[3] - e[2] + 1 for e in hs_ready); nf = sum(e[3] - e[2] + 1 for e in tf)
    nh = sum(e[3] - e[2] + 1 for e in hf); na = sum(e[3] - e[2] + 1 for e in af)
    assert len(ids) == nt, (len(ids), nt)
    tg_new = f"{8 * nt}'h" + ''.join(f'{x:02x}' for x in reversed(ids))
    par = hs['params']
    par = re.sub(r'\.NT\(\d+\)', f'.NT({nt})', par); par = re.sub(r'\.NF\(\d+\)', f'.NF({nf})', par)
    par = re.sub(r'\.NH\(\d+\)', f'.NH({nh})', par)
    par = re.sub(r"\.TGTS\(\d+'h[0-9a-fA-F]+\)", f'.TGTS({tg_new})', par)
    par = re.sub(r'\.NA\(\d+\)', f'.NA({na})', par) if '.NA(' in par else par + f', .NA({na})'
    remaster['host_status'] = dict(master=hs['master'], params=par)
    out_width['host_status'] = dict(a_cause=na)
    # obs_C observes host_status.a_cause[NA-1:0]: the observed vector shrinks with NA (obs_C N re-derived)
    ob = src_list(die, 'obs_C', 'obs')
    nob = []
    for e in ob:
        if e[0] == 'host_status' and e[1] == 'a_cause':
            if not any(x[0] == 'host_status' and x[1] == 'a_cause' for x in nob):
                nob.append(['host_status', 'a_cause', 0, na - 1])
        else:
            nob.append(e)
    nobw = sum(e[3] - e[2] + 1 if e[0] != 'const' else e[1] for e in nob)
    rebuild.setdefault('obs_C', {})['obs'] = nob
    ocp = die.insts['obs_C']['params']
    remaster['obs_C'] = dict(master=die.insts['obs_C']['master'], params=re.sub(r'\.N\(\d+\)', f'.N({nobw})', ocp))
    rebuild.setdefault('host_status', {}).update(t_ready=hs_ready, t_active=hs_active, t_fault=tf, h_fault=hf, a_fault=af)
    items.append(dict(id='W-HLEAF', kind='param+wiring', status='done',
                      what=f"hleaf_NW NT/NF {leaf_new['hleaf_NW']}, hleaf_NE NT/NF {leaf_new['hleaf_NE']} "
                           f"(ot_hbm_host_cfg_leaf2); host_status NT {nt} NF {nf} NH {nh} NA {na}, TGTS re-derived per slot",
                      moved={L: [f'{p}:{e[0]}.{e[1]}[{e[2]}]' for p, e, q in v] for L, v in moved.items()},
                      host_fault_map='hleaf s_fault bit order = rebuild t_fault order (host software map changes)'))

    # ---- W-CFG (col_su cfg from hleaf_NE a; programme part 0 = pgp_NW)
    rebuild.setdefault('col_su', {}).update(
        cfg_v=[one('hleaf_NE', 'a_cfg_v')], cfg_target=[one('hleaf_NE', 'a_cfg_target', 8)],
        cfg_addr=[one('hleaf_NE', 'a_cfg_addr', 12)], cfg_data=[one('hleaf_NE', 'a_cfg_data', 256)],
        desc_v=[one('hleaf_NE', 'a_desc_v')], launch_v=[one('hleaf_NE', 'a_launch_v')],
        c_busy=[one('pgp_NW', 'busy'), one('pgp_NW', 'valid')], c_done=[one('pgp_NW', 'done')])
    for inst in ('col_idx', 'hc_eng'):   # die-level targets the as-built hleaf_SE copy a fed
        for p in die.insts[inst]['conns']:
            sl = src_list(die, inst, p)
            if sl and all(e[0] == 'hleaf_SE' for e in sl):
                rebuild.setdefault(inst, {})[p] = [['hleaf_NE'] + e[1:] for e in sl]
    items.append(dict(id='W-CFG', kind='wiring', status='done',
                      what='col_su / col_idx / hc_eng cfg/desc/launch <- hleaf_NE copy a (as-built hleaf_SE a); c_busy {valid,busy} / '
                           'c_done <- pgp_NW (SU programme part 0 of the 2-part root; as-built pgp_SW)'))

    # ---- W-EP / COLL masters / epcal
    nw_par = '.NLINK(3), .TP(192), .AR_ITER(1), .ROWS(256), .VM_RT(81)'
    remaster['hb_coll_NW'] = dict(master='ot_hfd_coll_q3_hard_v8x', params=nw_par)
    remaster['hb_coll_NE'] = dict(master='ot_hfd_coll_q2_hard_v8g', params='.NLINK(2), .TP(192), .AR_ITER(1), .ROWS(256), .VM_RT(81)')
    rebuild.setdefault('hb_coll_NW', {}).update(
        phy_up=[one('ep_N0', 'phy_up'), one('ep_S0', 'phy_up'), one('ep_S1', 'phy_up')],
        rx_pin_v=[one('ep_N0', 'rx_pin_v'), one('ep_S0', 'rx_pin_v'), one('ep_S1', 'rx_pin_v')],
        rx_pin_flit=[one('ep_N0', 'rx_pin_flit', 612), one('ep_S0', 'rx_pin_flit', 612), one('ep_S1', 'rx_pin_flit', 612)],
        clk_link=[clk] * 15, clk_arg=[clk], clk_qslots=[clk] * (3 + 8 + 18),
        tkx_w_v=[one('tkm_SW', 'w_v')], tkx_w_addr=[one('tkm_SW', 'w_addr', 40)], tkx_w_mask=[one('tkm_SW', 'w_mask', 16)],
        tkx_w_data=[one('tkm_SW', 'w_data', 512)], tkx_busy=[one('tkm_SW', 'busy')], tkx_done=[one('tkm_SW', 'done')],
        tkx_fault=[one('tkm_SW', 'fault')])
    add_ports['hb_coll_NW'] = dict(clk_arg='in', tkx_w_v='in', tkx_w_addr='in', tkx_w_mask='in', tkx_w_data='in',
                                   tkx_busy='in', tkx_done='in', tkx_fault='in',
                                   tkx_start='out', tkx_arg_mode='out', tkx_cfg_n='out', tkx_cfg_k='out',
                                   tkx_cfg_nout='out', tkx_cfg_g='out', tkx_cfg_gbase='out', tkx_cfg_pf='out',
                                   tkx_cfg_obase='out', tkx_cfg_rbase='out', tkx_cfg_has_r='out', tkx_del_slot='out',
                                   tkx_del_valid='out', tkx_del_flit='out')
    out_width['hb_coll_NW'] = dict(tx_pin_v=3, tx_pin_flit=3 * 612, retry_requested=3, tkx_start=1, tkx_arg_mode=1,
                                   tkx_cfg_n=12, tkx_cfg_k=13, tkx_cfg_nout=13, tkx_cfg_g=8, tkx_cfg_gbase=8,
                                   tkx_cfg_pf=16, tkx_cfg_obase=40, tkx_cfg_rbase=40, tkx_cfg_has_r=1, tkx_del_slot=4,
                                   tkx_del_valid=4, tkx_del_flit=2180)
    rebuild.setdefault('hb_coll_NE', {}).update(
        phy_up=[one('ep_N2', 'phy_up'), one('ep_S3', 'phy_up')],
        rx_pin_v=[one('ep_N2', 'rx_pin_v'), one('ep_S3', 'rx_pin_v')],
        rx_pin_flit=[one('ep_N2', 'rx_pin_flit', 612), one('ep_S3', 'rx_pin_flit', 612)],
        clk_link=[clk] * 10, clk_qslots=[clk] * (2 + 7 + 18))
    out_width['hb_coll_NE'] = dict(tx_pin_v=2, tx_pin_flit=2 * 612, retry_requested=2)
    for ep, coll, lane in (('ep_N0', 'hb_coll_NW', 0), ('ep_S0', 'hb_coll_NW', 1), ('ep_S1', 'hb_coll_NW', 2),
                           ('ep_N2', 'hb_coll_NE', 0), ('ep_S3', 'hb_coll_NE', 1)):
        rebuild.setdefault(ep, {}).update(tx_v=[one(coll, 'tx_pin_v', 1, lane)],
                                          tx_frame=[one(coll, 'tx_pin_flit', 612, 612 * lane)])
    # tkm_SW fed by the NW q3 TKM interface
    rebuild.setdefault('tkm_SW', {}).update({p: [one('hb_coll_NW', 'tkx_' + p, w)] for p, w in dict(
        start=1, arg_mode=1, cfg_n=12, cfg_k=13, cfg_nout=13, cfg_g=8, cfg_gbase=8, cfg_pf=16, cfg_obase=40,
        cfg_rbase=40, cfg_has_r=1, del_slot=4, del_valid=4, del_flit=2180).items()})
    # link calendars: NW W 57 (N0, S0, S1), NE W 38 (N2, S3); 19-bit field per endpoint (as epcal_SW W 38)
    remaster['epcal_NW'] = dict(master='hfd_hgi_vm_calendar_f20_role', params='.W(57)')
    remaster['epcal_NE'] = dict(master='hfd_hgi_vm_calendar_f20_role', params='.W(38)')
    out_width['epcal_NW'] = dict(payload=57); out_width['epcal_NE'] = dict(payload=38)
    epf = dict(rx_arm_v=(0, 1), rx_arm_bank=(1, 1), rx_block_words=(2, 7), rx_release_v=(9, 1), rx_release_bank=(10, 1),
               rx_slot_v=(11, 1), rx_slot_bank=(12, 1), rx_slot_index=(13, 6))
    # check the as-built field layout on ep_N0 (epcal_NW payload[18:0])
    for p, (o, w) in epf.items():
        s = src_list(die, 'ep_N0', p)
        assert s == [['epcal_NW', 'payload', o, o + w - 1]], (p, s)
    for ep, cal, k in (('ep_N0', 'epcal_NW', 0), ('ep_S0', 'epcal_NW', 1), ('ep_S1', 'epcal_NW', 2),
                       ('ep_N2', 'epcal_NE', 0), ('ep_S3', 'epcal_NE', 1)):
        rebuild.setdefault(ep, {}).update({p: [one(cal, 'payload', w, 19 * k + o)] for p, (o, w) in epf.items()})
    items.append(dict(id='W-EP', kind='param+wiring', status='done (plan change owed)',
                      what='hb_coll_NW -> ot_hfd_coll_q3_hard_v8x NLINK 3 (lanes N0,S0,S1) + TKM interface to tkm_SW + '
                           'ARGMAX engine (as-built SW q3 role); hb_coll_NE q2 NLINK 2 (N2,S3); epcal_NW W 57, epcal_NE W 38 '
                           '(19-bit endpoint field k at [19k+18:19k]); ep faults to hleaf_NW (S0,S1) / hleaf_NE (S3)',
                      plan='B2l q_hub type carries u_hb_coll_Q = q2_hard_v8g for BOTH hubs (mirrored); the 5 SerDes need '
                           'q3 NLINK 3 on one hub and q2 NLINK 2 on the other -> NW_hub / NE_hub become two types (or one '
                           'superset type), and tkm_SW (root) must face the q3 hub. VM_RT 81 kept from the as-built NW/NE '
                           'engines: re-derive from the B2 plan VM round trip.'))

    # ---- W-RID
    rebuild.setdefault('hb_router_ids', {}).update(run_v=[one('cp_svg_NW0', 'run_v')],
                                                   run_layer=[one('cp_svg_NW0', 'run_arg', 8)])
    items.append(dict(id='W-RID', kind='wiring', status='done',
                      what='hb_router_ids run_v/run_layer <- cp_svg_NW0 (as-built cp_svg_SW0, same master and run_arg slice)'))

    # ---- P-VMST
    qs = src_list(die, 'vm_status4', 'quadrant_status')
    nw = [e for e in qs if e[0] == 'hb_vms_NW']; ne = [e for e in qs if e[0] == 'hb_vms_NE']
    remaster['vm_status4'] = dict(master='ot_vms_status4_static', params='.NQ(2)')
    rebuild.setdefault('vm_status4', {})['quadrant_status'] = nw + ne
    items.append(dict(id='P-VMST', kind='param', status='done',
                      what='vm_status4 NQ 2 {hb_vms_NE, hb_vms_NW} (bench rtl/hbm_accel/generic/vm/static/run_vms_status_nq.sh)'))

    # ---- R-VM: two-stop VM ring (sub-agent VM, claude/hbm-bind-1024r-vm@19cfa3d9c): hb_vms_NW -> NC=2 NW2 master
    # (takes hb_argmax / hb_idx__ctl, the as-built hb_vms_SW clients), hb_vms_NE -> NE2 glue; ring = the two as-built
    # links NW.ccw_out -> NE.ccw_in and NE.cw_out -> NW.cw_in.  Calendar fields from the universal calendars.
    remaster['hb_vms_NW'] = dict(master='hfd_hgi_vms_glue_nw2_t', params='')
    remaster['hb_vms_NE'] = dict(master='hfd_hgi_vms_static_NE2_glue', params='')
    drop_ports['hb_vms_NW'] = ['cw_out', 'ccw_in', 'replay_source']
    drop_ports['hb_vms_NE'] = ['ccw_out', 'cw_in', 'replay_source']
    add_ports['hb_vms_NW'] = dict(cq='in', cr='out')
    out_width['hb_vms_NW'] = dict(cr=548)
    cn = 'calendar_NW'
    rebuild.setdefault('hb_vms_NW', {}).update(
        cq=[one('hb_argmax', 'cq', 338), one('hb_idx__ctl', 'cq', 338)],
        client_seq=[one(cn, 'client_seq', 6)], response_enable=[one(cn, 'response_enable', 3)],
        response_seq=[one(cn, 'response_seq', 6)], bank_enable=[one(cn, 'bank_enable', 8)],
        bank_client=[one(cn, 'bank_client', 16)], hub_ring_enable=[one(cn, 'hub_ring_enable', 1, 1)],
        hub_ring_client=[one(cn, 'hub_ring_client', 2, 2)], ring_tx_enable=[one(cn, 'ring_tx_enable', 1, 1)],
        ring_tx_source=[one(cn, 'ring_tx_source', 3, 3)], replay_enable=[one(cn, 'replay_enable')],
        cw_in=[one('hb_vms_NE', 'cw_out', 2224)])
    ce = 'calendar_NE'
    rebuild.setdefault('hb_vms_NE', {}).update(
        client_seq=[one(ce, 'client_seq', 2)], response_enable=[one(ce, 'response_enable')],
        response_seq=[one(ce, 'response_seq', 2)], bank_enable=[one(ce, 'bank_enable', 8)],
        bank_client=[one(ce, 'bank_client', 8)], hub_ring_enable=[one(ce, 'hub_ring_enable')],
        hub_ring_client=[one(ce, 'hub_ring_client')], ring_tx_enable=[one(ce, 'ring_tx_enable')],
        ring_tx_source=[one(ce, 'ring_tx_source', 3)], replay_enable=[one(ce, 'replay_enable')],
        ccw_in=[one('hb_vms_NW', 'ccw_out', 2224)])
    rebuild.setdefault('hb_argmax', {})['cr'] = [one('hb_vms_NW', 'cr', 274)]
    rebuild.setdefault('hb_idx__ctl', {})['cr'] = [one('hb_vms_NW', 'cr', 274, 274)]
    items.append(dict(id='R-VM', kind='rtl+wiring', status='done (sub-agent VM 19cfa3d9c)',
                      what='hb_vms_NW -> hfd_hgi_vms_glue_nw2_t (NC 2: cq {idx_ctl.cq, argmax.cq}, cr[273:0] argmax / '
                           '[547:274] idx_ctl; calendar_NW fields at the SW NC 2 widths, ring controls = ccw halves), '
                           'hb_vms_NE -> hfd_hgi_vms_static_NE2_glue (ring controls = cw halves); ring links as built '
                           '(NW.ccw_out->NE.ccw_in, NE.cw_out->NW.cw_in); replay_source removed',
                      plan='NW and NE hubs become different VM masters (NW2 NC 2 vs NE2); VM_RT / CR_RT and the die cr '
                           'padding of argmax (6) / idx (8) must be re-derived for the B2 NW path; one dead bank port '
                           '(xq or xq2, 8 x 276 b constant inside the glue) per hub until a one-port bank variant exists'))

    # ---- R-SU: SU scalar tree 2 legs + SU programme root PARTS 2 + 2-writer SU cores (sub-agent SU cc8b2b937 + here)
    up = {q: src_list(die, 'str_C', f'up{k}_i') for k, q in ((2, 'NW'), (3, 'NE'))}
    assert up['NW'] == [['stl_NW', 'up_o', 0, 40]] and up['NE'] == [['stl_NE', 'up_o', 0, 40]], up
    for q, k in (('NW', 2), ('NE', 3)):
        assert src_list(die, f'stl_{q}', 'dn_i') == [['str_C', f'dn{k}_o', 0, 163]], src_list(die, f'stl_{q}', 'dn_i')
        assert src_list(die, f'sucore_{q}', 'rf_wv') == [[f'stl_{q}', 'rf_wv', 0, 3]]
    remaster['str_C'] = dict(master='ot_hbm_su_stree_root2', params='.MUT(0)')
    drop_ports['str_C'] = ['up2_i', 'up3_i', 'dn2_o', 'dn3_o']
    rebuild.setdefault('str_C', {}).update(up0_i=[one('stl_NW', 'up_o', 41)], up1_i=[one('stl_NE', 'up_o', 41)])
    out_width['str_C'] = dict(dn0_o=82, dn1_o=82)
    for q, k in (('NW', 0), ('NE', 1)):
        remaster[f'stl_{q}'] = dict(master='ot_hbm_su_stree_leaf', params='.MUT(0), .NLEG(2)')
        rebuild.setdefault(f'stl_{q}', {})['dn_i'] = [one('str_C', f'dn{k}_o', 82)]
        out_width[f'stl_{q}'] = dict(rf_wv=2, rf_wa=16, rf_wd=64)
        par = die.insts[f'sucore_{q}']['params']
        remaster[f'sucore_{q}'] = dict(master='ot_hbm_su_static_qcore_r13_w2', params=par)
        rebuild.setdefault(f'sucore_{q}', {}).update(rf_wv=[one(f'stl_{q}', 'rf_wv', 2)], rf_wa=[one(f'stl_{q}', 'rf_wa', 16)],
                                                     rf_wd=[one(f'stl_{q}', 'rf_wd', 64)])
    remaster['su_prog'] = dict(master='ot_hbm_su_programme_root_h5', params='.PARTS(2)')
    rebuild.setdefault('su_prog', {})['p_fault'] = [one('pgp_NW', 'fault'), one('pgp_NE', 'fault')]
    out_width['su_prog'] = dict(r_we=2, r_bank=32)
    out_remap = {'su_prog': dict(r_we=[[2, 2, 0], [3, 3, 1]], r_bank=[[32, 47, 0], [48, 63, 16]])}
    items.append(dict(id='R-SU', kind='rtl+wiring', status='done (sub-agent SU cc8b2b937; qcore w2 here)',
                      what='str_C -> ot_hbm_su_stree_root2 (up0/dn0 = NW leg, up1/dn1 = NE leg; dn 82 b = {NE head, NW head}); '
                           'stl_NW/NE -> ot_hbm_su_stree_leaf NLEG 2 (writer 0 NW, 1 NE); sucore_NW/NE -> '
                           'ot_hbm_su_static_qcore_r13_w2 (2-writer port bound to core writers 2/3 = as built; writers '
                           '0/1 removed inside the master); su_prog -> root_h5 PARTS 2 (part 0 pgp_NW banks 0..319, '
                           'part 1 pgp_NE 320..639; r_we/r_bank remapped, p_fault {NE, NW})',
                      plan='sucore_NW/NE become a new hard master (w2 wrapper: writer 0/1 logic pruned -> re-close the SU core '
                           'tile); compiler lower_root5(parts=2) exists, --root5 CLI lacks a parts option'))

    # ---- W-FLT: region fault leaves observe every retry lane of the regrown COLL masters (fr_NW / fr_NE N, SYNC_MASK)
    def regrow_leaf(leaf, src, sport, new_w, port='in'):
        old = src_list(die, leaf, port)
        par = die.insts[leaf]['params']
        mm = re.search(r"\.SYNC_MASK\((\d+)'h([0-9a-fA-F]+)\)", par)
        mw, mask = int(mm.group(1)), int(mm.group(2), 16)
        new, nmask, pos, opos = [], 0, 0, 0
        for e in old:
            w = e[1] if e[0] == 'const' else e[3] - e[2] + 1
            if e[0] == src and e[1] == sport:
                new.append([src, sport, 0, new_w - 1]); opos += w; pos += new_w; continue
            for b in range(w):
                if (mask >> (opos + b)) & 1:
                    nmask |= 1 << (pos + b)
            new.append(e); opos += w; pos += w
        rebuild.setdefault(leaf, {})[port] = new
        par = re.sub(r'\.N\(\d+\)', f'.N({pos})', par)
        par = re.sub(r"\.SYNC_MASK\(\d+'h[0-9a-fA-F]+\)", f".SYNC_MASK({mw}'h{nmask:x})", par)
        remaster[leaf] = dict(master=die.insts[leaf]['master'], params=par)
        return pos
    nfw = regrow_leaf('fr_NW', 'hb_coll_NW', 'retry_requested', 3)
    nfe = regrow_leaf('fr_NE', 'hb_coll_NE', 'retry_requested', 2)
    # tkm_SW (root) statistics: as built read by obs_SW (dropped) -> appended to obs_C (die level)
    ob = rebuild['obs_C']['obs'] + [['tkm_SW', 'stat_cycles', 0, 31]]
    rebuild['obs_C']['obs'] = ob
    nobw = sum(e[3] - e[2] + 1 if e[0] != 'const' else e[1] for e in ob)
    remaster['obs_C']['params'] = re.sub(r'\.N\(\d+\)', f'.N({nobw})', remaster['obs_C']['params'])
    items.append(dict(id='W-FLT', kind='param+wiring', status='done',
                      what=f'fr_NW N {nfw} / fr_NE N {nfe} take every hb_coll retry lane (SYNC_MASK bits re-positioned); '
                           f'tkm_SW.stat_cycles observed by obs_C (N {nobw}; as built by obs_SW)'))

    # ---- W-HOST: in-band host on the N0 link (OWNER 10-24): host_N (UCIe) dropped, ep_N0 carries VC 1
    drop_inst = ['host_N']
    remaster['ep_N0'] = dict(master='hfd_ep_static_vc2', params='.IDLE_K(204), .HQ(4)')
    add_ports['ep_N0'] = dict(h_tx_v='in', h_tx_frame='in', h_rx_v='out', h_rx_frame='out', h_up='out', h_cause='out')
    out_width['ep_N0'] = dict(h_rx_v=1, h_rx_frame=612, h_up=1, h_cause=3)
    rebuild.setdefault('ep_N0', {}).update(h_tx_v=[one('host_ep', 'vc_tx_v')], h_tx_frame=[one('host_ep', 'vc_tx_frame', 612)])
    remaster['host_ep'] = dict(master='hfd_ep_host_vc', params='')
    drop_ports['host_ep'] = ['sd_tx', 'sd_rx', 'sd_st']
    add_ports['host_ep'] = dict(vc_tx_v='out', vc_tx_frame='out', vc_rx_v='in', vc_rx_frame='in', vc_up='in', vc_cause='in')
    out_width['host_ep'] = dict(vc_tx_v=1, vc_tx_frame=612)
    rebuild.setdefault('host_ep', {}).update(vc_rx_v=[one('ep_N0', 'h_rx_v')], vc_rx_frame=[one('ep_N0', 'h_rx_frame', 612)],
                                             vc_up=[one('ep_N0', 'h_up')], vc_cause=[one('ep_N0', 'h_cause', 3)])
    items.append(dict(id='W-HOST', kind='rtl+wiring', status='rtl+bench (see b2_native_bind_rtl.json)',
                      what='host_N (ot_pdie_ucie_col) dropped; ep_N0 -> hfd_ep_static_vc2 (slot {vc,frame,v} 614 b, COLL VC0 '
                           'calendar priority +1 TX edge, host VC1 4-deep elastic queue on free take slots, RX vc demux); '
                           'host_ep -> hfd_ep_host_vc (pingpong + pin regs on the ep_N0 host face; host_cp_rxs unchanged). '
                           'The N0 peer (switch / neighbour) must run the vc2 lane format.',
                      plan='B2l/B2m: io_NW_io_u_host_N window removed; u_host_ep stays (smaller: no gearbox); '
                           'ep_N0<->host_ep 612+612+5 b frame faces inside NW_io; root keeps u_host_cp_ingress'))

    # ---- R-IDX: IDX / ARGMAX root on two quadrants (RTL straps: codex/hbm-bind-idx-r2-1024@8d607ca2e = claude/hbm-bind-
    # 1024r-idx@2353af4c8, gates rtl/test/hbm_idx_static/run_idx_b2_bind.sh).  The as-built root shared quadrant SW's VM
    # read group 4 (vmb_SW*.rq4/rr4, operand reader op_SW behind the share).  B2: the root serves NE (SID 3): it shares
    # vmb_NE*.rq4/rr4 with op_NE (now behind the share, like op_SW was); NW keeps its own share2 (hb_idx__nwsh, untouched).
    # Score tree: xq_N (level 1 {NE, NW}) feeds the selector directly (NL 1, its 592 data bits = the as-built in_line
    # list 1); xq_S / xqr (level 1 S, level 2 root) leave; tree_ev from xq_N's two list valids (NQ 2, list 0 = NW).
    # TOPK / ARGMAX cq/cr stay on hb_vms_NW (R-VM, the NW2 ring master): SID 3 requests reach the NE sector over the ring.
    dl = json.loads(Path(a.delays).read_text()).get('params', {}) if a.delays else {}
    def prm(inst, base):
        """param string: as-built params with the B2-derived delay params (b2_delays.json) substituted."""
        p = die.insts[inst]['params']
        for k, v in dl.get(inst, {}).items():
            if re.search(r'\.' + k + r'\(', p):
                p = re.sub(r'\.' + k + r'\(\d+\)', f'.{k}({v})', p)
            else:
                p = (p + ', ' if p else '') + f'.{k}({v})'
        return (p + ', ' + base) if base else p
    assert src_list(die, 'hb_idx__ctl', 'index_rq') == [['hb_idx__op_SW', 'vm_rq', 0, 135]]
    assert src_list(die, 'hb_idx__op_SW', 'vm_rr')[0][:2] == ['hb_idx__ctl', 'index_rr']
    xn = src_list(die, 'hb_idx__xqr', 'b')
    assert xn == [['hb_idx__xq_N', 'y', 0, 593]], xn
    assert src_list(die, 'hb_idx__xq_N', 'a')[0][0] == 'hb_idx__s_NW' and src_list(die, 'hb_idx__xq_N', 'b')[0][0] == 'hb_idx__s_NE'
    il = src_list(die, 'hb_idx__selector', 'in_line')    # as built: xqr.y lists {SE,SW}=list 0, {NE,NW}=list 1, 1184'0
    assert il[2:4] == [['hb_idx__xqr', 'y', 594, 889], ['hb_idx__xqr', 'y', 891, 1186]], il
    remaster['hb_idx__ctl'] = dict(master='ot_hbm_idx_rootctl_static_am', params=prm('hb_idx__ctl', ".SID(2'd3), .NQ(2), .NL(1)"))
    ne_rr = src_list(die, 'hb_idx__op_NE', 'vm_rr')        # vmb_NE0..7.rr4 (as op_NE read them)
    assert [e[0] for e in ne_rr if e[1] == 'rr4'] and all(e[1] == 'rr4' for e in ne_rr), ne_rr
    rebuild.setdefault('hb_idx__ctl', {}).update(
        index_rq=[one('hb_idx__op_NE', 'vm_rq', 136)], vm_rr=ne_rr,
        tree_ev=[one('hb_idx__xq_N', 'y', 1, 296), one('hb_idx__xq_N', 'y', 1, 593)],
        qfault=[one('hb_idx__qctl_NW', 'fault'), one('hb_idx__qctl_NE', 'fault')],
        selected_v=[one('hb_idx__selector', 'selected_v', 1)])
    rebuild.setdefault('hb_idx__op_NE', {})['vm_rr'] = [one('hb_idx__ctl', 'index_rr', 2056)]
    remaster['hb_idx__op_NE'] = dict(master=die.insts['hb_idx__op_NE']['master'], params=prm('hb_idx__op_NE', ''))
    for b in range(8):
        sw = src_list(die, f'vmb_SW{b}', 'rq4')
        assert len(sw) == 1 and sw[0][:2] == ['hb_idx__ctl', 'vm_rq'], sw
        assert src_list(die, f'vmb_NE{b}', 'rq4') == [['hb_idx__op_NE', 'vm_rq', sw[0][2], sw[0][3]]]
        rebuild.setdefault(f'vmb_NE{b}', {})['rq4'] = sw          # the share's per-bank request slice, as for vmb_SW<b>
    remaster['hb_idx__selector'] = dict(master='ot_hbm_idx_selector_static_sel', params='.NL(1)')
    rebuild.setdefault('hb_idx__selector', {}).update(
        in_line=[one('hb_idx__xq_N', 'y', 296, 0), one('hb_idx__xq_N', 'y', 296, 297)],
        clk_q=[clk], clk_mem=[clk] * 3)
    out_width['hb_idx__selector'] = dict(selected_v=1, selected_line=592)
    remaster['hb_idx__link'] = dict(master='ot_hbm_idx_topk_link_static', params='.NL(1)')
    rebuild.setdefault('hb_idx__link', {})['selected_line'] = [one('hb_idx__selector', 'selected_line', 592)]
    remaster['hb_argmax'] = dict(master='ot_hbm_argmax_static_sw_vm_r2', params=prm('hb_argmax', ".SID(2'd3)"))
    if 'hb_idx__nwsh' in dl:
        remaster['hb_idx__nwsh'] = dict(master=die.insts['hb_idx__nwsh']['master'], params=prm('hb_idx__nwsh', ''))
    if 'hb_idx__op_NW' in dl:
        remaster['hb_idx__op_NW'] = dict(master=die.insts['hb_idx__op_NW']['master'], params=prm('hb_idx__op_NW', ''))
    drop_inst += ['hb_idx__xq_S', 'hb_idx__xqr']
    items.append(dict(id='R-IDX', kind='rtl+wiring', status='done (straps 8d607ca2e; delays from b2_delays.json)' if dl
                      else 'done (straps 8d607ca2e); delay params as built (placeholders)',
                      what="hb_idx__ctl SID 3 / NQ 2 / NL 1: shares vmb_NE*.rq4/rr4 (vm_rq / vm_rr) with op_NE (index_rq / "
                           "index_rr; op_NE no longer drives the banks), tree_ev {xq_N.y[593] NE, xq_N.y[296] NW}, qfault "
                           "{qctl_NE, qctl_NW}, selected_v 1 b; hb_idx__selector NL 1 in_line = xq_N.y without the two list "
                           "valid bits ({NE 296, NW 296} = as-built list 1); hb_idx__link NL 1; hb_argmax SID 3; hb_idx__xq_S "
                           "and hb_idx__xqr dropped; cq / cr via hb_vms_NW (R-VM) -> NE sector over the two-stop ring; "
                           "hb_idx__nwsh / op_NW (NW share2) kept",
                      plan='root<->NE_hub carries the root share (vm_rq 136 + index_rr 2056 b out, vm_rr 2056 + index_rq '
                           '136 b in): see b2_delays.json lane capacity; score chain is one xq node (2 edges) shorter '
                           '(compiler --score-chain); delay params from b2_delays.json'))

    # ---- RTL items from sub-agents
    for f in a.rtl_items:
        r = json.loads(Path(f).read_text())
        for k_, dst in (('remaster', remaster), ('rebuild', rebuild), ('port_map', port_map), ('out_width', out_width),
                        ('add_ports', add_ports), ('drop_ports', drop_ports)):
            for inst, v in r.get(k_, {}).items():
                if isinstance(v, dict) and k_ != 'remaster':
                    dst.setdefault(inst, {}).update(v)
                else:
                    dst[inst] = v
        items += r.get('items', [])

    out = dict(schema='opentallas.hbm_b2.bind_wiring.v1',
               rule='HBM-BIND 10-24: machine-readable B2 (8-SM, NW+NE) native-bind delta over the r18h5 as-built die '
                    '(tools/hbm_b2/b2_top.py applies it; tools/hbm_b2/make_wiring.py writes it).',
               keep=dict(quadrants=list(KEEPQ), instances=['tkm_SW'], drop_instances=drop_inst),
               strap_ports=[x.replace('.*\\.', '.*\\.') for x in ab.get('straps', [])],
               items=items, remaster=remaster, rebuild=rebuild, port_map=port_map, out_width=out_width,
               add_ports=add_ports, drop_ports=drop_ports, out_remap=out_remap)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps([dict(id=i['id'], status=i['status']) for i in items]))


if __name__ == '__main__':
    main()
