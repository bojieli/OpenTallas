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
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ab = json.loads(Path(a.asbuilt).read_text())
    die = T.Die(a.die, ab['transport'])
    remaster, rebuild, port_map, out_width, add_ports, drop_ports = {}, {}, {}, {}, {}, {}
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
               keep=dict(quadrants=list(KEEPQ), instances=['tkm_SW'], drop_instances=[]),
               strap_ports=[x.replace('.*\\.', '.*\\.') for x in ab.get('straps', [])],
               items=items, remaster=remaster, rebuild=rebuild, port_map=port_map, out_width=out_width,
               add_ports=add_ports, drop_ports=drop_ports)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps([dict(id=i['id'], status=i['status']) for i in items]))


if __name__ == '__main__':
    main()
