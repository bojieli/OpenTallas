"""DIAGNOSTIC dv2r8f2 die case (Q-DIEPLAN3 2026-10-17; Q-DV adopted geometry, Q-CLUSTER cluster 2,285.28 x 5,184).

apply_dv(v, m) runs in qwen_rom_fulldie_b3r2.selected() right after the q3h hook (OT_SPLIT_Q3H=1 + grid/contract), when
OT_SPLIT_DV=<dv model json> is set.  The q3h model carries the REAL ports of every retained master; Q-DV's model
(results/arch/qwen_dv_1016/dv2r8f2.json, instance-level, no ports) gives the geometry and the new connectivity, and its
bus map (bus_map_dv2r8f2.json, roles in Q-DV's 10-17 message) the port roles:

  * removed: every instance the dv model does not place (VM, SU, seq_su, xs_tap, cbuf/crom, column heads, port halves,
    halfbands, res trains, word status, upper leaves, forks, ...) and every bus that ends only on them;
  * retained: positions from the dv model, ports unchanged;
  * clusters: qfd_c_b16_dv = the CB contract ports scaled to the Q-CLUSTER width + rs_i (N) / rs_o (S) in corridor T;
  * slices: 12 x qfd_dv_slice2, SYNTHETIC role ports (slice RTL step 2 pending): cw_n0..3 / rs_n0..1 on N (band 2),
    cw_s0..3 / rs_s0..1 on S (band 1), st_dn_o / ch_dn_o / ch_dn_i / l9_w_* / hr_i on W, st_dn_i / ch_up_i / ch_up_o /
    l9_e_* / hr_o / st_up_o on E (dn = toward W5 = west, up = east), ck / rst_n on N, W5 re-home ports r_<bus> on W;
  * W-column re-partition (open in RTL): every q3h bus that joined a retained W-column master (collective, native59,
    tt_ctlm, embed_prov, sys_face) to a removed master is re-homed to dvs_W5 (port r_<bus>, same width), so the real
    port of the retained master is kept;
  * clocks / resets: the q3h trunks without the removed sinks + one ck / rst_n per slice (regions re-filed from the
    placement afterwards).
FACE MODE (Q-SLICE 10-17, coordinator 0de; OT_SPLIT_DV_FACES=rtl/qwen_dv/qfd_dv_slice2_faces.json): the slices are the
two RTL face variants qfd_dv_slice2_w (W row, R0) / qfd_dv_slice2_e (E row, MY) with their REAL ports (dn face = W5
side); every lateral link takes the RTL port names; W5 binds the collective whole-port (in_* / out_* / cmd_*) and, when
the re-ported masters carry them, native59 (dd_i / dr_o) and tt_ctlm (hr / cmd / ss5 / ag5); no r_<bus> re-home ports;
the chain-end idle inputs are tied (rule c, straps manifest).
The strict port bind fails by construction (synthetic slice ports, qfd_c_b16_dv not on the source): chains run
OT_CHAIN_DIAGNOSTIC=1.  Relay planning, per-bit reach, GRT and die STA are real on this geometry.
"""
import json
import os
import re
from pathlib import Path

from qwen_split import q3h_cluster as Q

SLICE = 'qfd_dv_slice2'
SLICE_W, SLICE_E = 'qfd_dv_slice2_w', 'qfd_dv_slice2_e'
# face mode: lateral link kinds in one fixed slot order (dn-face member, up-face member travel opposite ways), so the
# W face of a slice and the E face of its west neighbour (or, across the MY seam, the two E faces) line up slot by slot
#   (kind, travels 'dn' or 'up', [parts (suffix, bits)])
LINKS = [('cmd', 'up', [('cmd', 116)]), ('hr', 'up', [('hr', 453)]),
         ('st_d', 'dn', [('st', 1088)]), ('st_u', 'up', [('st', 1088)]),
         ('sc_d', 'dn', [('sc', 48)]), ('sc_u', 'up', [('sc', 48)]),
         ('ar', 'dn', [('arv', 1), ('art', 32), ('arm', 1), ('arl', 1), ('ard', 512)]),
         ('dd', 'dn', [('dd', 548)]),
         ('rt', 'up', [('rv', 1), ('re', 1), ('rr', 3), ('rl', 1), ('rd', 512)]),
         ('dr', 'up', [('dr', 520)]), ('ag', 'dn', [('ag', 10)])]
# W5 <-> W column (face mode): (W5 port, peer instance, peer port); a pair is emitted only when the peer master has it
W5_COLL = [('arv_wo', 'in_valid'), ('ard_wo', 'in_data'), ('arl_wo', 'in_last'), ('arm_wo', 'in_mode'),
           ('art_wo', 'in_tag'), ('rv_wi', 'out_valid'), ('rd_wi', 'out_data'), ('rl_wi', 'out_last'),
           ('rr_wi', 'out_rank'), ('re_wi', 'out_err'), ('ccv_wo', 'cmd_v'), ('ccm_wo', 'cmd_mode'),
           ('ccw_wo', 'cmd_words'), ('cct_wo', 'cmd_tag')]
W5_PEERS = [('dd_wo', 'native59', 'dd_i'), ('dr_wi', 'native59', 'dr_o'), ('hr_wi', 'tt_ctlm', 'hr'),
            ('cmd_wi', 'tt_ctlm', 'cmd'), ('ss_wo', 'tt_ctlm', 'ss5'), ('ag_wo', 'tt_ctlm', 'ag5'),
            # QLB-C4b 10-18: the slice stream TABLE words (PROG / CROM / BTAB, stream kinds 1..3) -- tt_ctlm's calendar
            # TLOAD entries play them from the installed image onto the up-travelling stream at W5 (was a tie: no load
            # path for the slice tables on the die)
            ('st_wi', 'tt_ctlm', 'tl')]
CDV = 'qfd_c_b16_dv'
WCOL = ('io_collective', 'native59', 'tt_ctlm', 'embed_prov', 'sys_face')
# Q-DIEPLAN6 10-17 (face mode, OT_SPLIT_DV_WCOL_RTL != 0): the W-column masters re-ported to the DV slices, bound on
# their REAL RTL port lists with top-down pins assigned from the dv positions (native_graph_bind.assign_pins: every port
# on the face toward its die peers).  dv2f8 drew native59 / sys_face pins for their pre-dv q3h sites, so two W-column
# hops u-turned past reach (ng_native_native_ret_0 773 um, sf_complete_slot 598 um).
#   native59: qfd_native59_dv_service (Q-N59 dd73225e0), tt_ctlm: qfd_tt_ctlm_dv (Q-CTLM d8f159727 + Q-DIEPLAN6 status
#   widening ss5 107 / ag5 10), sys_face: qfd_sys_face (Q-CTLM G8: crom_fault_code / res_issue_fault dropped)
WCOL_RTL = {'native59': ('qfd_native59_dv_service', 'rtl/qwen_split/qfd_native59_dv_service.sv'),
            'tt_ctlm': ('qfd_tt_ctlm_dv', 'rtl/qwen_dv/qfd_tt_ctlm_dv.sv'),
            'sys_face': ('qfd_sys_face', 'rtl/qwen_split/qfd_sys_face.sv')}
# the embedding provider is CLOSED (rr1, native audit PASS): its die master is drawn as the closed view (outline + pins)
WCOL_VIEW = {'embed_prov': ('qfd_embedding_word_provider', 'rtl/qwen_split/qfd_embedding_word_provider.sv')}
# one regional clock / reset per re-ported master (the pre-DV multi-root pins fold onto them)
WCOL_REN = {'rsi': 'rst_n'}
# MU-DQ-DHUSER 10-19 (COORD 0kg item 2: no constant strap on qfd_tt_ctlm_dv.dh_user): on the multi-user die
# (OT_QWEN_MU_NU > 1) the die-level observer qfd_sys_face_mu_dhobs (= qfd_sys_face_mu_dhuser NU, OPSEG 0, compiled lists
# from mu_opcal.dhobs_lists) sits in the channel between tt_ctlm's N face (its dh / dh_user pins) and native59, joins the
# face's seq_dh bus as a third endpoint (the same landed hops as tt_ctlm.dh: dh_user names the h_start on the edge
# tt_ctlm samples it) and drives tt_ctlm.dh_user directly (one 2-b wire, no relay).  Its res_user / mu_fault stay open
# outputs (strict bind: output_open is not a failure; no die consumer port exists on the closed face / the ctlm today).
DHOBS = ('mu_dhobs', 'qfd_sys_face_mu_dhobs', 'rtl/qwen_split/mu/qfd_sys_face_mu_dhobs.sv')
DHOBS_WH = (43.2, 43.2)          # outline (um): ~60 flops + the 45-entry stage list; 187 + 6 pins on its faces
DHOBS_GAP = 17.28                # above tt_ctlm's N face (the tt_ctlm | native59 channel is 108 um)


def _load(env):
    p = os.environ.get(env, '').strip()
    return json.loads(Path(p).read_text()) if p else None


def _place(q, ports, w, h, fixed=None):
    """synthetic pin frame: ports with a fixed [lo, hi] range (mirrored abutting pins) spread over it; the rest per face
    packed at the 0.192 pitch (<= 6 pins/um), centred, on track"""
    fixed = fixed or {}
    for p, (bits, face) in ports.items():
        if p in fixed:
            a_, b_ = fixed[p]
            ps = [Q._trk(a_ + (b_ - a_) * k / max(1, bits - 1)) for k in range(bits)]
            q.ports[p] = ('pins', bits, face, 'M5' if face in 'NS' else 'M4', ps, 1)
            q.order.append(p)
    faces = {}
    for p, (bits, face) in ports.items():
        if p not in fixed:
            faces.setdefault(face, []).append((p, bits))
    for f, items in faces.items():
        L = w if f in 'NS' else h
        need = sum((b - 1) * Q.PITCH + 4.0 for _, b in items)
        if need > L - 8.0:
            raise ValueError(f'dv slice {f} face: {need:.0f} um of pins exceed {L:.0f}')
        cur = (L - need) / 2 if f in 'NS' else 40.0     # W / E: one fixed start, so facing slots line up
        for p, b in items:
            ps = [Q._trk(cur + k * Q.PITCH) for k in range(b)]
            q.ports[p] = ('pins', b, f, 'M5' if f in 'NS' else 'M4', ps, 1)
            q.order.append(p)
            cur = ps[-1] + 4.0


def _wcol_rebind(v, m, M, keep, out, wrtl):
    """face mode: the re-ported W-column masters on their RTL ports.  Every die endpoint on a port the new RTL lacks is
    folded onto the master's one regional clock / reset (ck*, rsi) or dropped (pre-DV faces whose peers left the die);
    buses left with one endpoint go.  Then pins: assign_pins (face toward the peers, from the dv positions) for the
    unclosed masters, the closed view (closed_view.install_master) for the embedding provider."""
    from qwen_split.native_graph_bind import assign_pins
    from qwen_split.direct_up4 import partition_master
    from qwen_split import closed_view as CV
    dropped, folded = [], []
    for j, (bid, cl, bits, eps) in enumerate(out):
        e2 = []
        for i_, p_ in eps:
            if i_ in wrtl:
                rp = wrtl[i_][2]
                al = m.get('port_join', {}).get(wrtl[i_][0], {})
                if p_ not in rp and p_ not in al:
                    q_ = 'ck' if p_.startswith('ck') and 'ck' in rp else WCOL_REN.get(p_, p_)
                    if q_ in rp:
                        folded.append(f'{i_}.{p_}->{q_}')
                        p_ = q_
                    else:
                        dropped.append(f'{bid}:{i_}.{p_}')
                        continue
            if (i_, p_) not in e2:
                e2.append((i_, p_))
        out[j] = (bid, cl, bits, e2)
    out[:] = [b for b in out if len(b[3]) > 1]
    used = {(i_, p_) for b in out for i_, p_ in b[3]}
    for inst, (mst, src, rp) in wrtl.items():
        pj = m.get('port_join', {})
        if mst in pj:      # aliases (port fragments) of ports the new RTL lacks / no die net uses any more go
            pj[mst] = {a: rb for a, rb in pj[mst].items() if rb[0] in rp and (inst, a) in used}
    byn = {i.name: i for i in keep}
    peers = {}
    for bid, cl, bits, eps in out:
        if cl in ('clock_trunk', 'reset'):
            continue
        for i_, p_ in eps:
            others = [byn[x] for x, _ in eps if x != i_]
            if others:
                peers.setdefault((i_, p_), []).extend(others)
    rec = dict(masters={k: w[0] for k, w in wrtl.items()}, folded=folded, dropped=dropped, views={})
    for inst, (mst, src, rp) in wrtl.items():
        if inst in WCOL_VIEW:
            rec['views'][inst] = CV.install_master(M, m, v.Master, byn[inst], mst, rp, partition_master)
        else:
            assign_pins(M, m, v.Master, byn[inst], mst, src, peers, partition_master)
    m.setdefault('q3h', {})['dv_wcol_rebind'] = rec
    return rec


def _dhobs_inst(v, m, M, keep):
    """MU-DQ-DHUSER: the observer instance on the MU die (None on a single-user die or without tt_ctlm.dh_user).
    Placed in the tt_ctlm | native59 channel, its E edge 86.4 um W of tt_ctlm's NE corner (the dh pins sit at the E end of
    tt_ctlm's N face, dh_user near its middle); OT_SPLIT_DV_DHOBS_XY=x,y overrides.  Fail closed on any overlap."""
    nu = int(os.environ.get('OT_QWEN_MU_NU', '1') or 1)
    tt = next((i for i in keep if i.name == 'tt_ctlm'), None)
    if os.environ.get('OT_SPLIT_DV_DHOBS', '1') == '0':
        m.setdefault('q3h', {})['dv_dhobs_off'] = 'OT_SPLIT_DV_DHOBS=0: DIAGNOSTIC control only (tt_ctlm.dh_user undriven)'
        return None
    if nu <= 1 or tt is None:
        return None
    w, h = DHOBS_WH
    xy = os.environ.get('OT_SPLIT_DV_DHOBS_XY', '').strip()
    if xy:
        x, y = (float(z) for z in xy.split(','))
    else:
        x, y = tt.x + tt.w - 86.4 - w, tt.y + tt.h + DHOBS_GAP
    x, y = round(round(x / 0.216) * 0.216, 3), round(y, 3)
    hit = [i.name for i in keep if x < i.x + i.w - 1e-3 and i.x < x + w - 1e-3 and y < i.y + i.h - 1e-3 and i.y < y + h - 1e-3]
    if hit:
        raise ValueError(f'dv: {DHOBS[0]} at ({x}, {y}) {w} x {h} overlaps {hit[:6]}')
    i = v.Inst(DHOBS[0], DHOBS[1], x, y, w, h, orient='R0', kind=tt.kind, region=tt.region, domain=tt.domain)
    keep.append(i)
    m.setdefault('q3h', {})['dv_dhobs'] = dict(inst=DHOBS[0], master=DHOBS[1], rtl=DHOBS[2], xy=[x, y], wh=[w, h], nu=nu,
                                                rule='COORD 0kg: tt_ctlm.dh_user driven by the MU observer (no strap)')
    return i


def _dhobs_buses(m, out, dh_crt, has):
    """the observer's die nets: a third endpoint on the face's seq_dh bus (whole 187 b; the observer reads [43:0]) and
    its dh_user -> tt_ctlm.dh_user (2 b, direct).  Fail closed if the seq_dh bus, the ports or the clock / reset are
    missing: the MU die must never fall back to an undriven / tied dh_user."""
    n_ = DHOBS[0]
    j = next((k for k, b in enumerate(out) if b[0] == 'dvw_sys_face_seq_dh'), None)
    miss = [p for p in (('sys_face', 'seq_dh'), ('tt_ctlm', 'dh'), ('tt_ctlm', 'dh_user'), (n_, 'seq_dh'), (n_, 'dh_user'))
            if not has(*p)]
    if j is None or miss or len(dh_crt) != 2:
        raise ValueError(f'dv: {n_}: seq_dh bus {"found" if j is not None else "MISSING"}, missing ports {miss}, '
                         f'clock / reset {sorted(dh_crt.values())}')
    b0, c0, n0, e0 = out[j]
    out[j] = (b0, c0, n0, list(e0) + [(n_, 'seq_dh')])
    out.append((f'dvw_{n_}_dh_user', 'spine_local', 2, [(n_, 'dh_user'), ('tt_ctlm', 'dh_user')]))
    m['q3h']['dv_dhobs'].update(seq_dh_bus=b0, dh_user_bus=f'dvw_{n_}_dh_user', clock_reset=dict(
        (f'{k[1]}', v_) for k, v_ in sorted(dh_crt.items())), open_outputs=['res_user', 'mu_fault'])


def apply_dv(v, m):
    D = _load('OT_SPLIT_DV')
    C = _load('OT_SPLIT_Q3H_CONTRACT')
    CWN = float(D.get('cluster_w', 2285.28))
    # W | E seam channel (Q-DV 2026-10-17, contract_deltas_dv2r8f5 afe950b84): MY keeps the y order, so the abutted
    # dvs_W0 | dvs_E0 faces meet out-to-out; a full-height channel of OT_SPLIT_DV_SEAM_UM between the halves carries the
    # die-level in / out swap of the lateral bundle as a jog (no cell, no stage). Everything from dvs_E0's x moves E.
    seam = float(os.environ.get('OT_SPLIT_DV_SEAM_UM', '0') or 0)
    if seam:
        xs = next(i['x'] for i in D['insts'] if i['n'] == 'dvs_E0') - 1e-3
        for d in D['insts']:
            if d['x'] >= xs:
                d['x'] = round(d['x'] + seam, 3)
    # slice reach channel (Q-DIE9 10-17, OT_SPLIT_DV_SLICE_GAP_UM, default 0 = abutted): dv2f11 abutted the slice row to
    # the S faces of cluster rows 1-2, burying their rst_n / ck_w0 / ck_e0 entry pins (and the slices' own ck / rst_n,
    # W face against the neighbour slice): GEN rst_field tree 34 sink_unreachable -> one 44.7-mm net.  A channel of G
    # above and below the slice row (the slice row moves N by G, rows 2-3 by 2 G; G on the 43.2 lattice) makes those
    # pins reachable; the slice's ck / rst_n move to its N face (in the channel); the cw / rs words become G-um wires.
    sgap = float(os.environ.get('OT_SPLIT_DV_SLICE_GAP_UM', '0') or 0)
    if sgap:
        ys = next(i['y'] for i in D['insts'] if i['n'] == 'dvs_W0')
        for d in D['insts']:
            if d['n'].startswith('dvs_'):
                d['y'] = round(d['y'] + sgap, 3)
            elif d['n'].startswith('c16_') and d['y'] > ys:
                d['y'] = round(d['y'] + 2 * sgap, 3)
    SLF = 'N' if sgap else 'W'
    # W-column channel width (Q-DV option (i), 2026-10-17): every PHY stays on the W die edge, single file; the far
    # SerDes (io_serdes_2, under io_serdes_1) reaches the collective's S face over a relayed FDI lane in this channel
    wchan = float(os.environ.get('OT_SPLIT_DV_WCHAN_UM', '0') or 0)
    if wchan:
        colr = max(d['x'] + d['w'] for d in D['insts'] if d['n'] == 'io_collective')
        x0a = min(d['x'] for d in D['insts'] if d['n'].startswith(('c16_', 'dvs_')))
        dx = round(wchan - (x0a - colr), 3)
        for d in D['insts']:
            if d['x'] > colr + 1.0:
                d['x'] = round(d['x'] + dx, 3)
    # W-column top cluster (OT_SPLIT_DV_TOPFIX, Q-DIEPLAN3 10-17; dv2f5 GEN: 31 sf_* pass-2 failures with no free relay
    # site at die-edge faces): d2d_rom R180 (its N-face payload pins face native59 / sys_face below, its FDI faces
    # ucie_kv above, its W-face x3 / result pins turn to the column interior), ucie_kv R180 above it across 130 um
    # (FDI down, beachfront on the N die edge), FDI centres x-aligned; native59 MY (q / vm_ar face E toward the
    # array); the cluster leaves the W die edge by 216 um
    orient = {}
    if os.environ.get('OT_SPLIT_DV_TOPFIX') == '1':
        top = ('tt_ctlm', 'rstseq_rom', 'clk_rx', 'embed_prov', 'native59', 'sys_face', 'd2d_rom', 'ucie_kv',
               'ckb_rom', 'rs_bump', 'bump_fwd_epoch', 'bump_fwd_lrst')
        T = {d['n']: d for d in D['insts'] if d['n'] in top}
        for d in T.values():
            d['x'] = round(d['x'] + 216.0, 3)
        dd, uk = T['d2d_rom'], T['ucie_kv']
        # FDI centres (local, R180): d2d 237.2 (rx 9.3 .. tx 465.0), ucie_kv 388.5 (rx 276.6 .. tx 500.4)
        uk['x'] = round(round((dd['x'] + 237.2 - 388.5) / 0.216) * 0.216, 3)
        uk['y'] = round(dd['y'] + dd['h'] + 129.6, 3)
        bumps = [T[b_] for b_ in ('ckb_rom', 'rs_bump', 'bump_fwd_epoch', 'bump_fwd_lrst')]
        sh = max(0.0, uk['x'] + uk['w'] + 21.6 - min(d['x'] for d in bumps))       # the bump row clears ucie_kv
        for d in bumps:
            d['x'] = round(d['x'] + sh, 3)
            d['y'] = round(uk['y'] + uk['h'] - d['h'], 3)
        orient.update(d2d_rom='R180', ucie_kv='R180', native59='MY')
    DI = {i['n']: i for i in D['insts'] if i['m'] != 'outline_marker'}
    for n, d in DI.items():                   # the model's own orientations (dv2r8f6+: 'o', e.g. the top cluster)
        if d.get('o') and not n.startswith(('c16_', 'dvs_')):
            orient.setdefault(n, d['o'])
    # Q-DIEPLAN7 10-17 (HANDOFF 0de++++): explicit orientation overrides, e.g. "d2d_rom=MX,ucie_kv=MX". The closed
    # qfd_d2d_static view has vertical pins on BOTH M3 and M5: under any y-axis mirror (MY / R180) the M3 and M5
    # origin residues differ by 6 mod 12 nm, so no legal origin exists (ot_mts). MX keeps R180's vertical sense
    # (N-face payload down to native59 / sys_face, FDI up to ucie_kv) but leaves the W / E faces unswapped;
    # ucie_kv MX keeps FDI tx-over-tx (both tx halves on the W). FDI centres (local, MX = unmirrored x):
    # d2d 238.0 (tx 10.2 .. rx 465.9), ucie_kv 389.1 (tx 277.2 .. rx 501.0). GEN re-plans every link from the
    # oriented pins. OT_SPLIT_DV_D2D_DX (um) moves d2d_rom E, ucie_kv follows on its FDI centre, the bump row clears it.
    for kv in filter(None, os.environ.get('OT_SPLIT_DV_ORIENT', '').split(',')):
        k_, o_ = kv.split('=')
        orient[k_.strip()] = o_.strip()
    d2d_dx = float(os.environ.get('OT_SPLIT_DV_D2D_DX', '0') or 0)
    if (d2d_dx or orient.get('d2d_rom') == 'MX') and 'd2d_rom' in DI and 'ucie_kv' in DI:
        dd, uk = DI['d2d_rom'], DI['ucie_kv']
        dd['x'] = round(round((dd['x'] + d2d_dx) / 0.216) * 0.216, 3)
        fc = {'MX': (238.0, 389.1), 'R0': (238.0, 389.1)}.get(orient.get('d2d_rom'), (237.2, 388.5))
        if orient.get('ucie_kv') in ('MX', 'R0'):
            fc = (fc[0], 389.1)
        uk['x'] = max(0.0, round(round((dd['x'] + fc[0] - fc[1]) / 0.216) * 0.216, 3))
        bumps = [DI[b_] for b_ in ('ckb_rom', 'rs_bump', 'bump_fwd_epoch', 'bump_fwd_lrst') if b_ in DI]
        if bumps:
            sh = max(0.0, uk['x'] + uk['w'] + 21.6 - min(d['x'] for d in bumps))
            for d in bumps:
                d['x'] = round(d['x'] + sh, 3)
    # Q-DIE13 10-18 landing channels (dv2f14bg LAND_CROSS GEN: 10 native59 <-> d2d_rom / sys_face landing hops 411-470 um
    # > 405: the blocks abut native59 across 108-um gaps that the bulk relays fill, no free station site in reach).
    # OT_SPLIT_DV_D2D_DY (um) moves d2d_rom, ucie_kv and the N bump row up (the die top grows with them: H is the max
    # instance top below); OT_SPLIT_DV_SYSFACE_DX (um) moves sys_face E. Both widen the native59 N / E gaps into a
    # landing channel for the OT_SPLIT_LAND_CROSS stations. Keep both on the 43.2-um lattice (129.6 = one 548-b
    # landing frame 60 um + its hop room).
    d2d_dy = float(os.environ.get('OT_SPLIT_DV_D2D_DY', '0') or 0)
    if d2d_dy:
        for n_ in ('d2d_rom', 'ucie_kv', 'ckb_rom', 'rs_bump', 'bump_fwd_epoch', 'bump_fwd_lrst'):
            if n_ in DI:
                DI[n_]['y'] = round(DI[n_]['y'] + d2d_dy, 3)
    sf_dx = float(os.environ.get('OT_SPLIT_DV_SYSFACE_DX', '0') or 0)
    if sf_dx and 'sys_face' in DI:
        DI['sys_face']['x'] = round(DI['sys_face']['x'] + sf_dx, 3)
    by = {i.name: i for i in m['insts']}
    # retained instances take the dv model's places BEFORE the masters are drawn (the collective / PHY frames follow
    # their instance outline: OT_SPLIT_PHY_TALL edge variants, collective re-kitted tall; PHYs above it are MX)
    tall = os.environ.get('OT_SPLIT_PHY_TALL') == '1'
    coll = DI.get('io_collective')
    for n, i in by.items():
        if n in DI and not n.startswith('c16_'):
            i.x, i.y = DI[n]['x'], DI[n]['y']
            if n in orient:
                i.orient = orient[n]
            if tall and (n == 'io_collective' or n.startswith(('io_serdes', 'io_ucie'))):
                i.w, i.h = DI[n]['w'], DI[n]['h']
                if n != 'io_collective' and coll and DI[n]['y'] >= coll['y'] + coll['h'] - 1e-3:
                    i.orient = 'MX'
    M = v.masters(m, 1)
    if tall:
        # the frozen master set (b2 / q3h wrappers) still holds the collective / PHY frames of the old outline
        from qwen_split import native_static_io_bind as NB
        m['dv_io_placed'] = True
        NB.install_master(M, m, v.Master)
    # ---- cluster master: Q-CLUSTER's dv contract (OT_SPLIT_DV_CONTRACT, cluster_contract_dv.json: ports / faces /
    # ranges incl. rs_i / rs_o and the four quadrant clock entries); without it the CB contract scaled + rs_i / rs_o
    CD = _load('OT_SPLIT_DV_CONTRACT')
    ck_pins = ['ck']
    rst_pins = []
    if CD:
        CWN, ch = CD['outline_um']['w'], CD['outline_um']['h']
        dirs = {'bco': 'output', 'rs_o': 'output', 'rs': 'output', 'tie_hi': 'output', 'tie_lo': 'output'}
        ports = {}
        for p_ in CD['ports']:
            n_ = p_['port']
            d_ = dirs.get(n_) or ('output' if n_.startswith('bco') else 'input')
            ports[n_] = dict(dir=d_, bits=p_['bits'], face=p_['face'], layer=p_['layer'], range=list(p_['range_um']))
        ck_pins = [p for p in ports if p.startswith('ck')]
        # Q-CB16RST 10-19 (claude/q-cb16rst-1019 ac8e4c483): a contract with regional resets rst_c<c>r<r> (beside each
        # ck_c<c>r<r>, registered on that region's clock at entry) replaces the cluster's single rst_n
        rst_pins = sorted(p for p in ports if re.fullmatch(r'rst_c\d+r\d+', p))
        if os.environ.get('OT_SPLIT_DV_RSI_AT_RS') == '1':
            # the far cluster's rs (S face, 488.9-660.2) feeds the near cluster's rs_i (N face) across the 130-um band
            # gap; the contract's rs_i sits under rs_o (1093.7-1265.0): a 605-um jog per bit (735 um each, one relay
            # stage in the gap, dv2f3 GEN: no free spot).  rs_i on the N face straight above rs (free there): a 130-um
            # face-to-face crossing, no relay; the cluster carries rs_i -> rs_o inside (its registered feedthrough).
            ports['rs_i']['range'] = list(ports['rs']['range'])
    else:
        sc = CWN / C['outline_um']['w']
        ports = Q._contract_ports(C)
        for p, d in ports.items():
            d['range'] = [round(d['range'][0] * sc, 3), round(d['range'][1] * sc, 3)]
        rs = ports['rs']['range']
        ports['rs_i'] = dict(dir='input', bits=514, face='N', layer='M5', range=[rs[0], rs[0] + 513 * Q.PITCH])
        ports['rs_o'] = dict(dir='output', bits=514, face='S', layer='M5',
                             range=[round(rs[1] + 6.0, 3), round(rs[1] + 6.0 + 513 * Q.PITCH, 3)])
        ch = 5184.0
    # Q-DIE11b 10-18 (Q-CLUSTER16 die_clock_contract / Q-CLUSTER5 centre feed): OT_SPLIT_DV_CLUSTER_CENTRE_CLOCKS=<json>
    # drops every regional clock of the cluster at an interior AREA pin at its region centre (clocks.<r>.pin /
    # centre_pin_um, cluster frame) instead of the contract's face entry: the die clock tree enters each region at its
    # centre (no face-fed H-tree across the 1.2 x 1.3-mm region).  port_domains (port -> region clock, default the
    # core_region clock) become the stand-in lib's related pins, so die STA times each cluster port against the region
    # that holds its pin register.  The contract's face entries for those clocks only seed the cluster IO placer.
    centre = _load('OT_SPLIT_DV_CLUSTER_CENTRE_CLOCKS')
    centre_pins = {}
    if centre:
        for r, c_ in centre['clocks'].items():
            pn = c_['pin']
            x_, y_ = c_['centre_pin_um']
            if pn not in ports:
                raise ValueError(f'centre clocks: {pn} is not a {CDV} contract port')
            if not (0 < x_ < CWN - Q.SHAVE and 0 < y_ < ch - Q.SHAVE):
                raise ValueError(f'centre clocks: {pn} centre {x_},{y_} outside the {CWN} x {ch} cluster outline')
            centre_pins[pn] = (round(x_, 3), round(y_, 3))
        stray = sorted(p_ for p_ in ports if p_.startswith('ck') and p_ not in centre_pins)
        if stray:
            raise ValueError(f'centre clocks: contract clock ports {stray} have no centre pin')
        # OT_SPLIT_DV_CLUSTER_CLOCK_AT=face (Q-DIE11b 10-18, dv2f14bn case PLACE 'qfd_c_b16_dv MX y: site grid (0 + k*270)
        # never meets the legal residues mod 80'): an interior M6-M9 pin cannot be on track in both R0 and MX / MY with
        # this outline (H = 5227.176: H mod 10 = 6 vs the 270 row grid on M8; W, H mod 64 = 40 vs M5 / M4 on M6 / M7),
        # so the drops stay at the contract's per-region FACE entries (M4 / M5) until the cluster outline / pin layer is
        # chosen for centre pins; the related pins (port -> region clock) apply either way.
        at_face = os.environ.get('OT_SPLIT_DV_CLUSTER_CLOCK_AT', 'centre') == 'face'
        clk_ports = {pn: dict(ports[pn]) for pn in centre_pins}
        for pn in centre_pins:
            ports.pop(pn)
    M[CDV] = Q._master(v, CWN - Q.SHAVE, ch - Q.SHAVE, dict(ports, **(clk_ports if centre and at_face else {})))
    M[CDV].name = CDV
    if centre_pins:
        for pn, (x_, y_) in sorted(centre_pins.items()):
            if at_face:
                continue
            M[CDV].ports[pn] = ('area', 1, x_, y_, 1)
            M[CDV].order.append(pn)
        dom = dict(centre.get('port_domains') or {})
        dflt = centre.get('default_domain') or next(
            (centre['clocks'][r]['pin'] for r in centre['clocks']
             if r in str(centre.get('core_region_ports', '')).split(' ')[0]), sorted(centre_pins)[0])
        bad = sorted(set(dom) - set(ports)) + sorted(set(dom.values()) - set(centre_pins))
        if bad:
            raise ValueError(f'centre clocks: port_domains name unknown ports / clocks {bad}')
        rel = {p_: [dom.get(p_, dflt)] * d_['bits'] for p_, d_ in ports.items()}
        m['dv_cluster_clocks'] = dict(master=CDV, source=os.environ['OT_SPLIT_DV_CLUSTER_CENTRE_CLOCKS'],
                                      clocks={pn: list(xy) for pn, xy in sorted(centre_pins.items())},
                                      layer=('contract face entry (M4/M5): centre pins blocked by MX/MY track legality'
                                             if at_face else 'M8 area pin (die drop; the hardened cluster keeps the chimney free)'),
                                      default_domain=dflt, port_domains=dom, related_pins=rel)
    # Q-DIEPLAN8 10-17: dv2f10 PDN-0006 (die VDD M8 blocked by the abstract's M9 OBS on c16_E0_0).  The two-level
    # cluster contract (cluster_level 2: PG M8, signals M2-M7) leaves M9 to the die; the synthetic cluster and slice
    # abstracts obstructed M1-M9.  OT_SPLIT_DV_OBS_TOP=8 obstructs M1-M8 only (default 9 = the dv2f10 abstracts).
    obs_top = int(os.environ.get('OT_SPLIT_DV_OBS_TOP', '9'))
    if obs_top not in (8, 9):
        raise ValueError(f'OT_SPLIT_DV_OBS_TOP must be 8 or 9, got {obs_top}')
    M[CDV].obs_top = obs_top
    # Q-DIE11 10-18 (coordinator 0ea item 2): dv2f12 GRT overflow 72,022, all in capacity-0 GCells in the bottom 240 um
    # of the slice row: the synthetic slice abstract obstructed M1-M8 over its whole footprint, so its 3,095 S-face M5
    # pins had no access.  The slice uses M1-M5 inside (its SRAM macros obstruct M1-M4, tile signal cap M5), so
    # OT_SPLIT_DV_SLICE_OBS_TOP=5 obstructs only those, and OT_SPLIT_DV_PIN_WINDOW_UM=<d> keeps a d-um pin-access window
    # (M4..obs_top) along every pin cluster of every face (qwen_rom_fulldie.pin_windows).  Defaults keep dv2f13 abstracts.
    slice_obs = int(os.environ.get('OT_SPLIT_DV_SLICE_OBS_TOP', str(obs_top)))
    if not 5 <= slice_obs <= 9:
        raise ValueError(f'OT_SPLIT_DV_SLICE_OBS_TOP must be 5..9, got {slice_obs}')
    slice_win = float(os.environ.get('OT_SPLIT_DV_PIN_WINDOW_UM', '0') or 0)
    # the same windows on the synthetic cluster abstract (coordinator 10-18: every placeholder abstract; its OBS
    # stays M1-M<OT_SPLIT_DV_OBS_TOP>: the two-level cluster contract routes signals M2-M7 + PG M8 inside)
    M[CDV].pin_window = slice_win
    if slice_win:
        m.setdefault('dv_slice_abstract', {}).update(obs_top=slice_obs, pin_window_um=slice_win, window_layers=f'M4-M{slice_obs}',
                                                     rule='hardened slice keeps OBS within M1-M%d and the face windows free on M4-M%d' % (slice_obs, slice_obs))
    # ---- slice master (synthetic role ports)
    sw, sh = DI['dvs_W0']['w'], DI['dvs_W0']['h']
    # slice ports (SYNTHETIC, Q-DV roles): N / S faces MIRROR the abutting clusters' S-face pins (bc<lc> -> cw_*<lc>,
    # rs -> rs_*0, rs_o -> rs_*1 at the contract's exact x ranges: face to face, no die wire, Q-DV dv2r8f5 slice_abut);
    # W / E faces are SYMMETRIC (each side has an in and an out of every lateral kind) so one master serves the W row
    # (R0) and the E row (MY, mirroring the MY / R180 clusters): a link takes the ports on the die faces that face
    sp = {}
    fixed_rng = {}
    rng = {p_['port']: p_['range_um'] for p_ in (CD['ports'] if CD else [])}
    for f, tag in (('N', 'n'), ('S', 's')):
        for k in range(4):
            sp[f'cw_{tag}{k}'] = (516, f)
            if f'bc{k}' in rng:
                fixed_rng[f'cw_{tag}{k}'] = rng[f'bc{k}']
        for k, src in ((0, 'rs'), (1, 'rs_o')):
            sp[f'rs_{tag}{k}'] = (514, f)
            if src in rng:
                fixed_rng[f'rs_{tag}{k}'] = rng[src]
    LAT = dict(st=1136, ch=1094, l9=514, hr=453, cmd=116)
    # abutted neighbours face each other: W-face (in, out) slot k lines up with the E-face (out, in) slot k
    for kind, bits in LAT.items():
        sp[f'{kind}_wi'] = (bits, 'W')
        sp[f'{kind}_wo'] = (bits, 'W')
    for kind, bits in LAT.items():
        sp[f'{kind}_eo'] = (bits, 'E')
        sp[f'{kind}_ei'] = (bits, 'E')
    sp.update({'ck': (1, SLF), 'rst_n': (1, SLF)})
    FX = _load('OT_SPLIT_DV_FACES')           # face mode: real RTL face variants, no re-home stand-ins
    # W5 re-home ports (one per re-homed q3h bus, same width) go on the W face too
    removed = {n for n in by if n not in DI}
    rehome = []
    for bid, cl, bits, eps in m['buses']:
        if cl in ('clock_trunk', 'reset'):
            continue
        ins = {i for i, _ in eps}
        if ins & removed and ins & set(WCOL) and not ins - removed - set(WCOL):
            rehome.append((bid, cl, bits, eps))
    # Q-DV role table: only the W5 chain ends are re-homed, at their bit widths (W5 ch_dn_o AR 546 -> collective,
    # collective 518 -> W5; W5 D2D 548 -> native59, native59 520 -> W5; tt_ctlm hr 453 + cmd 116 = 569 -> W5); every other q3h port of a
    # retained W-column master whose peer was removed stays OPEN (the re-partition is not in RTL yet).  Budgets are
    # filled with the largest q3h buses of that master and direction (diagnostic stand-ins for the role words).
    budget = {('io_collective', 'in'): 546, ('io_collective', 'out'): 518, ('native59', 'in'): 548,
              ('native59', 'out'): 520, ('tt_ctlm', 'out'): 569}
    pick = []
    for bid, cl, bits, eps in sorted(rehome, key=lambda t: -t[2]):
        drv = eps[0][0]
        key = (drv, 'out') if drv in WCOL else (next((i for i, _ in eps if i in WCOL), None), 'in')
        if key in budget and budget[key] >= bits:
            budget[key] -= bits
            pick.append((bid, cl, bits, eps))
    rehome = pick if not FX else []
    # re-home ports fill the faces with room (W first: the W column is west), at the same 0.192 pitch
    room = {f: (sw if f in 'NS' else sh) - 8.0 - sum((b_ - 1) * Q.PITCH + 4.0 for b_, f_ in sp.values() if f_ == f)
            for f in 'WSNE'}
    for bid, cl, bits, eps in sorted(rehome, key=lambda t: -t[2]):
        need = (bits - 1) * Q.PITCH + 4.0
        f = next((f for f in 'WSNE' if room[f] >= need), None)
        if f is None:
            raise ValueError(f'dv slice: no face room for the re-home port of {bid} ({bits} b): {room}')
        sp[f'r_{bid}'] = (bits, f)
        room[f] -= need
    if FX:
        ns = {k: v_ for k, v_ in sp.items() if v_[1] in 'NS'}
        for mn, dn in ((SLICE_W, 'w'), (SLICE_E, 'e')):
            up = 'e' if dn == 'w' else 'w'
            fd, fu = [('l9_wi' if dn == 'w' else 'l9_eo', 514)], [('l9_eo' if dn == 'w' else 'l9_wi', 514)]
            for kind, trav, parts in LINKS:
                for suf, b in parts:
                    fd.append((f'{suf}_{dn}{"o" if trav == "dn" else "i"}', b))
                    fu.append((f'{suf}_{up}{"i" if trav == "dn" else "o"}', b))
            fd += [(f'ss_{dn}o', 107), (f'ccv_{dn}o', 1), (f'ccm_{dn}o', 1), (f'ccw_{dn}o', 16), (f'cct_{dn}o', 32)]
            sp2 = dict(ns)
            for n_, b in fd:
                sp2[n_] = (b, dn.upper())
            for n_, b in fu:
                sp2[n_] = (b, up.upper())
            sp2.update({'ck': (1, SLF), 'rst_n': (1, SLF)})
            rtl = {p_['port']: p_['bits'] for p_ in FX[mn]['ports']}
            bad = sorted(set(sp2) ^ set(rtl)) + sorted(k for k in sp2 if k in rtl and rtl[k] != sp2[k][0])
            if bad:
                raise ValueError(f'dv face mode: {mn} frame vs RTL face map mismatch {bad[:12]}')
            qs = v.Master(mn, sw - Q.SHAVE, sh - Q.SHAVE, slice_obs, f'Q-DV slice2 face variant {mn} (RTL ports, dn = {dn})'
                          + (f'; OBS M1-M{slice_obs}, pin windows {slice_win} um' if slice_win else ''))
            qs.pin_window = slice_win
            _place(qs, sp2, sw - Q.SHAVE, sh - Q.SHAVE, fixed_rng)
            M[mn] = qs
    else:
        qs = v.Master(SLICE, sw - Q.SHAVE, sh - Q.SHAVE, slice_obs, 'Q-DV slice2 (SYNTHETIC role ports, RTL step 2 pending)')
        qs.pin_window = slice_win
        _place(qs, sp, sw - Q.SHAVE, sh - Q.SHAVE, fixed_rng)
        M[SLICE] = qs
    # ---- instances: retained / clusters / slices at the dv model's positions
    keep = []
    for i in m['insts']:
        if i.name in removed:
            continue
        d = DI[i.name]
        i.x, i.y = d['x'], d['y']
        if i.name.startswith('c16_'):
            i.master, i.w, i.h = CDV, CWN - Q.SHAVE, ch - Q.SHAVE
            if getattr(i, 'orient', 'R0') in ('MY', 'R180') and sw > CWN + 1e-3:
                # dv2r8f7 lattice: the slot (= slice) is wider than the cluster; an x-mirrored cluster right-aligns
                # in it so its mirrored N / S pins land on the mirrored slice's (both mirror about their own width)
                i.x = round(i.x + sw - CWN, 3)
        keep.append(i)
    have = {i.name for i in keep}
    for n, d in DI.items():
        if n in have:
            continue
        if d['m'] in (SLICE, 'qfd_dv_slice2'):
            mn = SLICE if not FX else (SLICE_E if n.startswith('dvs_E') else SLICE_W)
            keep.append(v.Inst(n, mn, d['x'], d['y'], sw - Q.SHAVE, sh - Q.SHAVE,
                               orient='MY' if n.startswith('dvs_E') else 'R0', kind='cluster', region='field',
                               domain='stream_1p2'))
        elif d['m'] == 'qfd_dv_lane_relay':
            continue                       # the relay planner places the lane relays itself
        else:
            raise ValueError(f'dv: instance {n} ({d["m"]}) not in the q3h model')
    dhobs = _dhobs_inst(v, m, M, keep)
    if dhobs is not None:
        by[dhobs.name] = dhobs
    m['insts'][:] = keep
    names = {i.name for i in keep}
    # final placement gate (fail closed): no two instances overlap
    srt = sorted(keep, key=lambda i: i.x)
    ovl = []
    for a_ in range(len(srt)):
        p_ = srt[a_]
        for q_ in srt[a_ + 1:]:
            if q_.x >= p_.x + p_.w - 1e-3:
                break
            if q_.y < p_.y + p_.h - 1e-3 and p_.y < q_.y + q_.h - 1e-3:
                ovl.append((p_.name, q_.name))
    if ovl:
        raise ValueError(f'dv: {len(ovl)} overlapping instances {ovl[:8]}')
    # ---- buses
    out, dropped, partial = [], {}, []
    dh_crt = {}
    slices = sorted(n for n in names if n.startswith('dvs_'))
    for bid, cl, bits, eps in m['buses']:
        if cl in ('clock_trunk', 'reset'):
            e2 = [e for e in eps if e[0] in names]
            if cl == 'clock_trunk':           # a cluster's die clock entries (Q-CLUSTER: four quadrant pins)
                e2 = [x for e in e2 for x in ([(e[0], p) for p in ck_pins] if e[0].startswith('c16_') and e[1] == 'ck'
                                              else [e])]
            if cl == 'reset' and rst_pins:   # Q-CB16RST: a cluster's reset = 16 regional drops (one per clock region)
                e2 = [x for e in e2 for x in ([(e[0], p) for p in rst_pins] if e[0].startswith('c16_') and e[1] == 'rst_n'
                                              else [e])]
            if cl == 'clock_trunk' and any(e[0].startswith('c16_') for e in e2):
                e2 += [(s, 'ck') for s in slices if not any(x == s for x, _ in e2)]
            if bid == 'rst_field':
                e2 += [(s, 'rst_n') for s in slices]
            if dhobs is not None and any(e[0] == 'tt_ctlm' and (cl == 'reset' or e[1].startswith('ck')) for e in e2):
                k_ = 'ck' if cl == 'clock_trunk' else 'rst_n'
                if (dhobs.name, k_) not in dh_crt:          # tt_ctlm's FIRST clock / reset net (it folds onto one)
                    e2.append((dhobs.name, k_))
                    dh_crt[(dhobs.name, k_)] = bid
            if len(e2) > 1:
                out.append((bid, cl, bits, e2))
            continue
        if bid.startswith('bword') or bid.startswith('q3h_col_'):
            continue                       # replaced by the dv reduce / column words below
        if all(e[0] in names for e in eps):
            out.append((bid, cl, bits, eps))
            continue
        kept = [e for e in eps if e[0] in names]
        if eps[0][0] in names and any(e[0] == 'sys_face' for e in kept[1:]):
            # Q-DIE11b 10-18 (dv2f14bn strict bind: qfd_sys_face.emb_prov_fault input_unconnected): sys_face_bind appends
            # its inputs to the producer's existing net (ng_embed_fault_0 = embed_prov.fault -> sp_su64_sfu, sys_face);
            # the DV case removes sp_su64_sfu, which dropped the whole net.  Keep the net on its surviving endpoints when
            # the driver stays and a sys_face input is among them (every sys_face input is mandatory).
            # added at the end only for sys_face inputs no other net feeds (the dv face rebinds some, e.g. io_cmd_free)
            partial.append((bid, cl, bits, kept, [list(e) for e in eps if e[0] not in names]))
            continue
        dropped[cl] = dropped.get(cl, 0) + 1
    for bid, cl, bits, eps in rehome:
        e2 = [e if e[0] not in removed else ('dvs_W5', f'r_{bid}') for e in eps]
        seen, e3 = set(), []
        for e in e2:
            if e not in seen:
                seen.add(e)
                e3.append(e)
        if len(e3) > 1:
            out.append((f'dvr_{bid}', cl, bits, e3))
    x_of = {n: DI[n]['x'] for n in DI}
    for bid, cl, bits, eps in D['buses']:
        if cl in ('clock_trunk', 'reset'):
            continue
        a = eps[0]
        if bid.startswith('q3h_col_'):
            c, band = map(int, bid.split('_')[2:4])
            lc = c % 4 if c < 24 else 3 - c % 4
            out.append((bid, 'tree_spine', 516, [(a, f'cw_{"s" if band == 1 else "n"}{lc}'), (eps[1], f'bc{lc}')]))
        elif bid.startswith('dv_rsi_'):
            out.append((bid, 'tree_spine', 514, [(eps[0], 'rs'), (eps[1], 'rs_i')]))
        elif bid.startswith('dv_rs_'):
            band = int(bid.rsplit('_', 1)[1])
            s = 's' if band == 1 else 'n'
            out.append((bid + '_a', 'tree_spine', 514, [(eps[0], 'rs'), (eps[1], f'rs_{s}0')]))
            out.append((bid + '_b', 'tree_spine', 514, [(eps[0], 'rs_o'), (eps[1], f'rs_{s}1')]))
        elif FX and bid.startswith(('dv_st_', 'dv_x0', 'dv_ch_')):
            wst, est = sorted(eps, key=lambda n: x_of[n])
            def fl(n, role):                    # master face letter of slice n's dn / up face
                return ('w' if role == 'dn' else 'e') if n.startswith('dvs_W') else ('e' if role == 'dn' else 'w')
            # dv_x0 (the W0 | E0 seam) carries the outbound / return chains too: the Q-DV model has no dv_ch seam bus,
            # so without this the E row's AR / D2D words would never reach W5
            ch_k, st_k = ('ar', 'dd', 'rt', 'dr', 'ag'), ('cmd', 'hr', 'st_d', 'st_u', 'sc_d', 'sc_u')
            kinds = ch_k if bid.startswith('dv_ch_') else st_k + ch_k if bid.startswith('dv_x0') else st_k
            for kind, trav, parts in LINKS:
                if kind not in kinds:
                    continue
                for suf, b in parts:
                    if trav == 'dn':
                        e2 = [(est, f'{suf}_{fl(est, "dn")}o'), (wst, f'{suf}_{fl(wst, "up")}i')]
                    else:
                        e2 = [(wst, f'{suf}_{fl(wst, "up")}o'), (est, f'{suf}_{fl(est, "dn")}i')]
                    out.append((f'{bid}_{kind}_{suf}', 'tree_spine', b, e2))
        elif bid.startswith(('dv_l9_', 'dv_st_', 'dv_x0', 'dv_ch_')):
            wst, est = sorted(eps, key=lambda n: x_of[n])
            def lp(n, dieface, kind, d_):       # port on the die face of slice n (MY swaps the master W / E faces)
                f_ = dieface if not n.startswith('dvs_E') else {'W': 'E', 'E': 'W'}[dieface]
                return (n, f'{kind}_{f_.lower()}{d_}')
            if bid.startswith('dv_l9_'):
                src, dst = eps
                if src == wst:
                    out.append((bid, 'tree_spine', 514, [lp(src, 'E', 'l9', 'o'), lp(dst, 'W', 'l9', 'i')]))
                else:
                    out.append((bid, 'tree_spine', 514, [lp(src, 'W', 'l9', 'o'), lp(dst, 'E', 'l9', 'i')]))
            elif bid.startswith('dv_ch_'):
                out += [(bid + '_dn', 'tree_spine', 1094, [lp(est, 'W', 'ch', 'o'), lp(wst, 'E', 'ch', 'i')]),
                        (bid + '_up', 'tree_spine', 1094, [lp(wst, 'E', 'ch', 'o'), lp(est, 'W', 'ch', 'i')])]
            else:
                out += [(bid + '_dn', 'tree_spine', 1136, [lp(est, 'W', 'st', 'o'), lp(wst, 'E', 'st', 'i')]),
                        (bid + '_up', 'tree_spine', 1136, [lp(wst, 'E', 'st', 'o'), lp(est, 'W', 'st', 'i')]),
                        (bid + '_hr', 'tree_spine', 453, [lp(wst, 'E', 'hr', 'o'), lp(est, 'W', 'hr', 'i')]),
                        (bid + '_cmd', 'tree_spine', 116, [lp(wst, 'E', 'cmd', 'o'), lp(est, 'W', 'cmd', 'i')])]
        # dv_ar_W / dv_kv_* / dv_ib_W / dv_emb: the W-column re-partition is carried by the r_<bus> re-homes
    wrtl = {}
    if FX and os.environ.get('OT_SPLIT_DV_WCOL_RTL', '1') != '0':
        from qwen_split.source_pin_plan import rtl_ports
        root = Path(__file__).resolve().parents[2]
        for inst, (mst, src) in list(WCOL_RTL.items()) + list(WCOL_VIEW.items()) + [(DHOBS[0], DHOBS[1:])]:
            if inst not in names:
                continue
            rp = rtl_ports(root / src, mst)
            wrtl[inst] = (mst, src, rp)
            old = by[inst].master
            by[inst].master = mst
            q = v.Master(mst, by[inst].w, by[inst].h, 7, f'{mst} (re-ported W-column master; pins assigned below)')
            for p_, (n_, _d) in rp.items():
                q.ports[p_] = ('pins', n_, None, None, [], 1)
                q.order.append(p_)
            M[mst] = q
            if old != mst and not any(i.master == old for i in keep):
                M.pop(old, None)
    if FX:
        # W5 <-> W column on real ports (whole-port; a pair only when the peer master has the port)
        def has(inst, port):
            i_ = by.get(inst)
            return i_ is not None and inst in names and port in M[i_.master].ports
        miss = []
        for a_, b_ in W5_COLL:
            if has('io_collective', b_):
                src = [('dvs_W5', a_), ('io_collective', b_)]
                out.append((f'dvw_{a_}', 'tree_spine', M[by['io_collective'].master].ports[b_][1],
                            src if a_.endswith('o') else src[::-1]))
            else:
                miss.append(f'io_collective.{b_}')
        for a_, inst, b_ in W5_PEERS:
            if has(inst, b_):
                src = [('dvs_W5', a_), (inst, b_)]
                out.append((f'dvw_{a_}', 'tree_spine', M[by[inst].master].ports[b_][1],
                            src if a_.endswith('o') else src[::-1]))
            else:
                miss.append(f'{inst}.{b_}')
        for si, sp_, di, dp_ in (('io_collective', 'cmd_free', 'sys_face', 'io_cmd_free'),
                                 ('tt_ctlm', 'emb_start', 'embed_prov', 'core_start'),
                                 ('tt_ctlm', 'emb_token', 'embed_prov', 'core_token'),
                                 ('native59', 'emb_code_re', 'embed_prov', 'embed_code_re'),
                                 ('native59', 'emb_code_addr', 'embed_prov', 'embed_code_addr'),
                                 ('native59', 'emb_scale_re', 'embed_prov', 'embed_scale_re'),
                                 ('native59', 'emb_scale_addr', 'embed_prov', 'embed_scale_addr'),
                                 ('embed_prov', 'embed_code_q', 'native59', 'emb_code_q'),
                                 ('embed_prov', 'embed_scale_q', 'native59', 'emb_scale_q'),
                                 # Q-CTLM: tt_ctlm took seq_su's sys_face faces (token / position levels, the program
                                 # record port's calendar sink, the dc status word)
                                 ('sys_face', 'seq_dh', 'tt_ctlm', 'dh'),
                                 ('tt_ctlm', 'cal_program_obs', 'sys_face', 'seq_program_obs'),
                                 ('tt_ctlm', 'cal_descriptor_obs', 'sys_face', 'seq_descriptor_obs'),
                                 ('tt_ctlm', 'cal_image_ready', 'sys_face', 'seq_cfg_image_ready'),
                                 ('tt_ctlm', 'dc', 'sys_face', 'seq_dc')):
            if has(si, sp_) and has(di, dp_):
                out.append((f'dvw_{si}_{sp_}', 'spine_local', M[by[si].master].ports[sp_][1], [(si, sp_), (di, dp_)]))
            else:
                miss.append(f'{si}.{sp_}->{di}.{dp_}')
        if dhobs is not None:
            _dhobs_buses(m, out, dh_crt, has)
        m.setdefault('q3h', {}).setdefault('dv_face_missing', miss)
        if wrtl:
            _wcol_rebind(v, m, M, keep, out, wrtl)
        # chain-end idle inputs (rule c): W5 sc up-travelling input from the W column side (no scalar producer west of
        # W5: the scalar chain is slice-to-slice, its ROOT is on W5), E5 up-face inputs, the l9_wi of an unpaired slice --
        # only where no bus lands.  QLB-C4b 10-18: W5 st_wi is NOT a chain-end idle input any more (tt_ctlm.tl drives
        # it, W5_PEERS); without that bus it stays unconnected and the strict bind fails (never tied).
        conn = {e for b in out for e in b[3]}
        east = max((n for n in names if n.startswith('dvs_E')), key=lambda n: x_of[n], default=None)
        for n in sorted(names):
            if not n.startswith('dvs_'):
                continue
            mst = M[SLICE_E if n.startswith('dvs_E') else SLICE_W]
            for p_, pv in mst.ports.items():
                if (n, p_) in conn or not (p_.endswith('i') and p_ not in ('rst_n',)):
                    continue
                up_in = n == east and p_.endswith('_wi') and not p_.startswith(('l9', 'cmd', 'hr', 'rv', 're', 'rr',
                                                                                'rl', 'rd', 'dr'))
                if (n == 'dvs_W5' and p_ == 'sc_wi') or up_in or p_ == 'l9_wi':
                    m['ties'].append((n, p_, pv[1], 0))
    # far-band clusters: rs_i tied low (Q-CLUSTER: the far bands tie the feedthrough input)
    fed = {e[0] for b in out for e in b[3] if e[1] == 'rs_i'}
    for n in sorted(names):
        if n.startswith('c16_') and n not in fed:
            m['ties'].append((n, 'rs_i', 514, 0))
    m['ties'][:] = [t for t in m['ties'] if t[0] in names]
    conn = {tuple(e) for b in out for e in b[3]}
    for bid, cl, bits, kept, gone in partial:
        sf_ = [e for e in kept[1:] if e[0] == 'sys_face' and tuple(e) not in conn]
        if not sf_:
            dropped[cl] = dropped.get(cl, 0) + 1
            continue
        kept2 = [kept[0]] + [e for e in kept[1:] if tuple(e) not in conn]
        j_ = next((j for j, b in enumerate(out) if tuple(b[3][0]) == tuple(kept[0])), None)
        if j_ is not None:       # the driver already drives a net: the sys_face inputs join it (one net per port)
            b0, c0, n0, e0 = out[j_]
            out[j_] = (b0, c0, n0, e0 + kept2[1:])
        else:
            out.append((bid, cl, bits, kept2))
        conn.update(tuple(e) for e in kept2)
        m.setdefault('dv_partial_buses', []).append(dict(bus=bid, endpoints=[list(e) for e in kept2], removed=gone))
    m['buses'] = out
    # relay routing on the dv array (b3r2 _poly0): field-to-field links stay in their band gap / the W|E seam
    m['dv_gap_route'] = True
    w0, e0 = DI['dvs_W0'], DI['dvs_E0']
    if e0['x'] - (w0['x'] + w0['w']) > 1.0:
        m['dv_seam'] = (round(w0['x'] + w0['w'], 3), round(e0['x'], 3))
        # Q-DIEPLAN6 10-17 (OT_SPLIT_DV_SEAM_LANE=1): the outbound / return chain words of the W0 | E0 seam (ar, dd, rt,
        # dr, ag: 2,143 b) leave the stream bundle's crossing and take their own registered seam lane: one relay
        # station per word in the seam channel at the word's own face rows (dv2f8: all 4,985 seam bits in one 260-um
        # window, cut 0.608).  +1 edge on each E-row chain crossing (relay_stages.json carries it to the calendar).
        if FX and os.environ.get('OT_SPLIT_DV_SEAM_LANE') == '1':
            m['dv_seam_lane'] = sorted(b[0] for b in out if b[0].startswith(tuple(f'dv_x0_{k}_' for k in
                                                                                   ('ar', 'dd', 'rt', 'dr', 'ag'))))
    # ---- die / relay geometry
    W = max(i.x + i.w for i in keep) + 21.6
    H = max(d['y'] + d['h'] for d in D['insts']) + 21.6
    m['die']['w'], m['die']['h'] = round(W, 3), round(H, 3)
    m['die']['mm2'] = round(W * H / 1e6, 3)
    g = m['geo']
    g['y0'], g['y_top'], g['y_io'] = 0.0, H, H
    arr = [i for i in keep if i.name.startswith(('c16_', 'dvs_'))]
    xm = (min(i.x for i in arr) + max(i.x + i.w for i in arr)) / 2
    xw, xe = m.get('dv_seam') or (xm, xm)      # the W|E seam channel is not tile field: relays may stand in it
    rects = [[min(i.x for i in arr if i.cx < xm), min(i.y for i in arr), xw, max(i.y + i.h for i in arr)],
             [xe, min(i.y for i in arr), max(i.x + i.w for i in arr), max(i.y + i.h for i in arr)]]
    fields = sorted([r for r in m['regions'] if r['kind'] == 'tile_field'], key=lambda r: r['rect'][0])
    for r, rr in zip(fields, rects):
        r['rect'] = [round(z, 3) for z in rr]
    # vertical relay lanes: the W-column channel beside the array (the only vertical die channel; clusters abut)
    wcol = max(by[n].x + by[n].w for n in WCOL if n in names)
    x0 = min(i.x for i in arr)
    nl = max(1, min(2, int((x0 - wcol - 8.64) // (v.CORR + 8.64))))
    lanes = [round(wcol + 4.32 + k * (v.CORR + 8.64), 3) for k in range(nl)]
    m['corridor_lanes'] = [(lanes[c % nl], v.CORR) for c in range(v.COLS)]
    m['q3h']['dv'] = dict(model=os.environ.get('OT_SPLIT_DV'), die=m['die'], removed=len(removed), slices=len(slices),
                          rehomed=len(rehome), dropped_buses=dropped, lanes=lanes, diagnostic=True,
                          synthetic_ports=[SLICE, CDV + ' rs_i/rs_o (scaled CB contract)'])

    def fixed(model, k=1, port_bits=None):
        return dict(M)
    v.masters = fixed
    return m['q3h']['dv']
