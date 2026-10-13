"""qwen-tp8 tp8b, contract v5 stage (die lead r8, 2026-10-13): the die generator follows contract v4 / v4b and the
coordinator decisions of 10-13, so a regenerated case IS the contract (no patch-only slots).

Called at the end of before_relays (after _tp8b_kv), i.e. on the final placement and before the relay plan:

  T7   stations / heads: x[508:0] -> x_d[507:0] (with the flow) + x_r (against it); the relay frames carry both
       (m['bus_pair'], _relays); rst_n on N beside ck; tile pin tap[507:0], station tap_r tied high at the die (decision
       b: ot_qwen_rom_tile_nk has no ready port)
  T8   qkd_cdc_wleaf 183.6 x 183.6, RTL ports (port split of the die bundles co / hi / ho / wi / wr / cf)
  T9   qkd_rhead cluster 691.2 x 453.6 (R0 / MX origin - 43.2), pins per v4; KV relays left inside a grown head are torn
  T10  qfd_sp_vector_memory = region envelope 4708.8 x 2347.92 at (13284.0, 17249.76); head root xw / xe = 508 + ready
  T12  qfd_sp_res_ser 777.6 x 518.4 + rst_n / me_en / fault
  T13  qfd_tt_up4 one cluster in tt_up4_0, tt_up4_1..3 removed, sel 26 b
  T14  the SU group (sp_su64_sfu, 8 cbuf_g, 8 crom_g, seq_su) follows the VM: SU abutted on the VM N face, the group
       mirrored above it (placement mirrored, masters R0 with their N / S pin faces swapped: an MX master's M8 clock
       pins are not mirror-legal).  Cut reason: su_vm = 8,511 b; left at y 8.9-10.9 mm it needs 14.2 kb of vertical capacity at
       0.60 through the A|B channel (12.6 kb in all) for 6.3 mm, and every SU read pays ~15 stages each way
  T15  qfd_crom_g + 32.4 um N (194.376 x 550.776)
  T16  KV control strip = 32 x qkd_ctrl_pc (247.512 x 378) + qkd_ctrl_kc (kc async FIFO, 45.36 um, S end of every strip:
       one PC master, one pin plan); ot_hbm3e_phy re-pinned per PC (phy_repin): rsp_* of PC k faces leaf k, req_* at the
       S end beside the kc leaf
  T17  qfd_seq_su bundles (consumer side): ib dropped (the ME instruction is issued by the control tile: tt_ctlm.ib ->
       head root), dflt dropped (no link end on one die), dc 56 b / dh 187 b, cc 517 b valid only, cd = cd_d + cd_cr,
       cbr0..7 kept (8 producers; the cell owns the registered reducer)
  T18  reset: qkd_pll / qfd_clkrx are hard-macro abstracts; ot_qwen_sys_rst_seq is its own leaf (qkd_rstseq beside the
       PLL, qfd_rstseq beside the clock receiver); new reset nets rst_field (tiles, stations, heads) and rst_spine
       (res_ser, tt_up4, crom_g, cbuf_g) join the registered reset tree
Emission (masters / LEF / netlist): port kind 'pins' (explicit positions), PORT_SPLIT (a die bundle = several view ports,
LSB first), TIES (constants: straps, chain ends, tap_r), PHY pin groups ('*dfi:<group>').
"""
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'hier_contract'))

DW = 508
VM_ENV = dict(x=13284.0, y=17249.76, w=4708.8, h=2347.92)
SU_X = 16424.64                      # the VM stream's SU reservation column (el1011-qwen-tp8.log 04:20)
RHEAD_WH, RHEAD_OLD_W = (712.8, 453.6), 648.0   # coordinator 10-13: qkh_head_hs grant (v4 T9 was 691.2)
CDC_WH = 183.6
CROM_DH = 32.4
PC_H, KC_H, NPC = 378.0, 45.36, 32
SEL_BITS = 26
STATIONS = {'qfd_cst_s': dict(N=('a', 'in'), S=('b', 'out'), W=('tap', 'out')),
            'qfd_cst_n': dict(S=('b', 'in'), N=('a', 'out'), W=('tap', 'out')),
            'qfd_chead_w': dict(E=('e', 'in'), W=('w', 'out'), N=('n', 'out'), S=('s', 'out')),
            'qfd_chead_e': dict(W=('w', 'in'), E=('e', 'out'), N=('n', 'out'), S=('s', 'out'))}
SPLIT = {
    'qkd_cdc_wleaf': dict(
        co=[('l_v', 1), ('l_sec', 17), ('l_row', 8), ('l_data', 256), ('l_pop', 1)],
        hi=[('h_lv', 1), ('h_lsec', 17), ('h_lrow', 8), ('h_ldata', 256), ('h_hand', 1), ('h_wcon', 1), ('h_av', 1),
            ('h_atag', 9)],
        ho=[('h_cred', 3), ('h_wv', 1), ('h_wsec', 24), ('h_cv', 1), ('h_csec', 24), ('h_cdata', 256), ('h_ctag', 9),
            ('h_fault', 1)],
        wi=[('w_v', 1), ('w_sec', 24), ('w_data', 256), ('w_tag', 9)],
        wr=[('w_room', 1), ('wd_v', 1), ('wd_tag', 9)],
        cf=[('c_fault', 1)]),
    # closed qkd_kvwq_ctl_bin-sl1-ecdaf6345 (rtl/physical/ot_qwen_kv_slot_wrappers.sv)
    'qkd_kvwq_ctl_bin': dict(
        kvn=[('kvn_d', 1047), ('kvn_cr', 1)],
        **{f'f{g}': [('f%d_v' % g, 1), ('f%d_d' % g, 256), ('f%d_sec' % g, 24), ('f%d_lane' % g, 3), ('f%d_tag' % g, 9)]
           for g in range(4)},
        **{f'r{g}': [('r%d_v' % g, 1), ('r%d_bad' % g, 1)] for g in range(4)},
        durable=[('rw_v', 1), ('rw_id', 22)]),
    'qfd_seq_su': dict(cd=[('cd_d', 547), ('cd_cr', 1)]),
}
PHY_PC = (('rsp_v', 1), ('rsp_rdy', 1), ('rsp_beat', 4), ('rsp_tag', 16), ('rsp_data', 256))          # 278 b per PC
PHY_REQ = (('req_v', 1), ('req_rdy', 1), ('req_we', 1), ('req_len', 5), ('req_tag', 16), ('req_addr', 31),
           ('req_wdata', 256))                                                                          # 311 b
PC_PHY_Y = 175.92          # PC-leaf local y of the centre of its PHY slice (E face)
STEP = 0.096


def _snap(y):
    return round(0.012 + 0.048 * round((y - 0.012) / 0.048), 3)


def phy_groups():
    """{group: [(pin base, bit)]} in bus-bit order: PC k = rsp_* of PC k, 'req' = the shared request port"""
    g = {}
    for k in range(NPC):
        g[str(k)] = [(b, k * n + j) for b, n in PHY_PC for j in range(n)]
    g['req'] = [(b, j) for b, n in PHY_REQ for j in range(n)]
    return g


def phy_pin_y():
    """PHY-local y of every signal pin after the per-PC re-pin.  The PHY sits 71.28 um above its strip's S end; PC leaf k
    spans strip y KC_H + 378 k .. + 378; its PHY slice is centred PC_PHY_Y above the leaf's S edge."""
    off = KC_H - 71.28
    y = {}
    for k in range(NPC):
        n = sum(b for _, b in PHY_PC)
        lo = off + PC_H * k + PC_PHY_Y - n * STEP / 2
        for i, (b, j) in enumerate(phy_groups()[str(k)]):
            y[(b, j)] = _snap(lo + i * STEP)
    for i, (b, j) in enumerate(phy_groups()['req']):
        y[(b, j)] = _snap(4.0 + i * STEP)
    return y


def phy_repin(text):
    """the ot_hbm3e_phy abstract LEF with every signal pin moved to its per-PC y (x extent, layer, width kept)"""
    ys = phy_pin_y()

    def one(pm):
        name, body = pm.group(1), pm.group(2)
        if 'USE POWER' in body or 'USE GROUND' in body:
            return pm.group(0)
        mm = re.match(r'^(.*)\[(\d+)\]$', name)
        key = (mm.group(1), int(mm.group(2))) if mm else (name, 0)
        if key not in ys:
            return pm.group(0)

        def rect(rm):
            x0, y0, x1, y1 = (float(rm.group(i)) for i in range(1, 5))
            hw = (y1 - y0) / 2
            return f'RECT {x0:.3f} {ys[key] - hw:.3f} {x1:.3f} {ys[key] + hw:.3f}'
        return f'  PIN {name}\n' + re.sub(r'RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', rect, body) + f'  END {name}\n'
    return re.sub(r'  PIN (\S+)\n(.*?)  END \1\n', one, text, flags=re.S)


def _pack(L, items, keep=()):
    """items [(port, span_um, want centre)] -> {port: centre}: in order of `want`, no overlap, 2 um apart, clear of the
    `keep` intervals, inside [4, L - 4]"""
    out, cur = {}, 4.0
    its = sorted(items, key=lambda t: t[2])
    for p, sp, want in its:
        lo = max(cur, want - sp / 2)
        for _ in range(len(keep) + 1):
            hit = [k for k in keep if k[0] < lo + sp + 2.0 and lo - 2.0 < k[1]]
            if not hit:
                break
            lo = max(k[1] for k in hit) + 2.0
        out[p] = lo
        cur = lo + sp + 2.0
    hi = L - 4.0
    for p, sp, want in reversed(its):
        if out[p] + sp > hi:
            out[p] = hi - sp
            for _ in range(len(keep) + 1):
                hit = [k for k in keep if k[0] < out[p] + sp + 2.0 and out[p] - 2.0 < k[1]]
                if not hit:
                    break
                out[p] = min(k[0] for k in hit) - 2.0 - sp
        hi = out[p] - 2.0
        if out[p] < 2.0:
            raise ValueError(f'v5 pin plan: {p} does not fit ({L:.1f} um face, {len(items)} groups)')
    return {p: out[p] + sp / 2 for p, sp, _ in its}


def apply(v, m, G):
    S = v.SHAVE
    by = {i.name: i for i in m['insts']}
    rec = m.setdefault('tp8b_v5', {})
    ties = m.setdefault('ties', [])            # (inst, port, bits, value)
    pair = m.setdefault('bus_pair', {})
    split = m.setdefault('port_split', {})
    split.update({k: dict(q) for k, q in SPLIT.items()})
    B = list(m['buses'])

    def drop_insts(names):
        names = set(names)
        m['insts'] = [i for i in m['insts'] if i.name not in names]

    # ---------------------------------------------------------------- T13 tt_up4: one cluster, sel 26 b
    ug = [i.name for i in m['insts'] if i.master == 'qfd_tt_up4_g']
    drop_insts(ug)
    B = [(b, c, SEL_BITS if b == 'o4_sel' else n, e) for b, c, n, e in B if not any(x[0] in ug for x in e)]
    rec['tt_up4'] = dict(removed=ug, sel_bits=SEL_BITS)

    # ---------------------------------------------------------------- T17 seq_su bundles
    nb = []
    for b, c, n, e in B:
        if b in ('seq_ib', 'd2d_flt'):
            continue
        if b == 'seq_d2d':
            n = 56
        elif b == 'd2d_seq':
            n = 187
        elif b == 'coll_seq_x':
            n = 517
        nb.append((b, c, n, e))
    B = nb
    B.append(('tt_ib', 'tree_spine', 380, [('tt_ctlm', 'ib'), ('sp_vector_memory', 'ib')]))
    rec['seq_su'] = dict(dropped=['seq_ib', 'd2d_flt'], dc=56, dh=187, cc=517, cd='cd_d[546:0] + cd_cr',
                         ib='tt_ctlm.ib[379:0] -> sp_vector_memory.ib (head root)')

    # ---------------------------------------------------------------- T10 / T14 VM envelope, SU group follows
    vm, su = by['sp_vector_memory'], by['sp_su64_sfu']
    grp = [i for i in m['insts'] if i.name == 'seq_su' or i.master in ('qfd_su_cbuf_g', 'qfd_crom_g')]
    old = dict(vm=[vm.x, vm.y, vm.w, vm.h], su=[su.x, su.y])
    vm.x, vm.y, vm.w, vm.h = VM_ENV['x'], VM_ENV['y'], VM_ENV['w'], VM_ENV['h']
    su_new = (SU_X, round(VM_ENV['y'] + VM_ENV['h'], 4))
    dx = su_new[0] - su.x
    for i in grp:
        d = su.y - (i.y + i.h)                       # gap below the SU (old), kept above it (new)
        if i.master == 'qfd_crom_g':
            i.h = round(i.h + CROM_DH, 4)            # T15: grows N, away from the buffer rows
        i.x, i.y = round(i.x + dx, 4), round(su_new[1] + su.h + d, 4)
    su.x, su.y = su_new[0], su_new[1]
    v.SU_VM_NORTH = True
    ck = by.get('clk_rx')
    bl = by.get('sp_band_lanes_1')
    if ck is not None and bl is not None:
        # the clock receiver leaves the strip under the VM's centre relief bays for the W sub-column
        ck.x, ck.y = round(bl.x, 4), round(v.up(bl.y + bl.h + 43.2, v.GY), 4)
    rec['vm'] = dict(old=old, envelope=VM_ENV, su=[su.x, su.y, 'R0, N / S pin faces swapped'], group=sorted(i.name for i in grp),
                     clk_rx=[ck.x, ck.y] if ck is not None else None)

    # ---------------------------------------------------------------- T12 res_ser cluster slot
    for i in m['insts']:
        if i.master == 'qfd_sp_res_ser':
            i.w, i.h = 777.6, 518.4
    for k, i in enumerate(sorted((i for i in m['insts'] if i.master == 'qfd_sp_res_ser'), key=lambda i: i.name)):
        B += [(f'o4_me_en_rs{k}', 'spine_local', 1, [('tt_ctlm', f'mer{k}'), (i.name, 'me_en')]),
              (f'rs_fault_{k}', 'spine_local', 1, [(i.name, 'fault'), ('tt_ctlm', f'rf{k}')])]

    # ---------------------------------------------------------------- T8 cdc_wleaf, T9 rhead
    for i in m['insts']:
        if i.master == 'qkd_cdc_wleaf':
            i.w = i.h = CDC_WH
        elif i.master == 'qkd_rhead':
            if i.orient in ('R0', 'MX'):
                i.x = round(i.x + i.w + (RHEAD_OLD_W - i.w) - RHEAD_WH[0], 4)
            i.w, i.h = RHEAD_WH

    # ---------------------------------------------------------------- T16 KV control strips
    strips = [i for i in m['insts'] if i.master in ('qkd_ctrl', 'qkd_ctrl_n')]
    v.PIN_POS_EXTRA = dict(getattr(v, 'PIN_POS_EXTRA', None) or {})
    pys = phy_pin_y()
    gy = {g: sum(pys[q] for q in l) / len(l) for g, l in phy_groups().items()}
    rec['ctrl'] = {}
    for cs in strips:
        st = cs.name.split('_', 1)[1]
        ph = by[f'phy_{st}']
        if ph.orient in ('MX', 'R180') or abs((ph.y - cs.y) - 71.28) > 1e-3:
            raise ValueError(f'v5 ctrl: {ph.name} {ph.orient} at dy {ph.y - cs.y:.3f}: the per-PC PHY pin plan assumes '
                             f'an unflipped PHY 71.28 um above the strip end')
        px = ph.x + ph.w - 0.096 if ph.orient == 'MY' else ph.x + 0.096
        kc = v.Inst(f'ctrlkc_{st}', 'qkd_ctrl_kc', cs.x, cs.y, cs.w, round(KC_H - S, 4), cs.orient, kind=cs.kind,
                    region=cs.region, domain=cs.domain)
        new = [kc]
        for k in range(NPC):
            new.append(v.Inst(f'ctrlpc_{st}_{k}', 'qkd_ctrl_pc', cs.x, round(cs.y + KC_H + PC_H * k, 4), cs.w,
                              round(PC_H - S, 4), cs.orient, kind=cs.kind, region=cs.region, domain=cs.domain))
            v.PIN_POS_EXTRA[(ph.name, f'*dfi:{k}')] = (px, ph.y + gy[str(k)])
            ties.append((f'ctrlpc_{st}_{k}', 'pc', 5, k))
        v.PIN_POS_EXTRA[(ph.name, '*dfi:req')] = (px, ph.y + gy['req'])
        ties.append((f'ctrlpc_{st}_{NPC - 1}', 'rqi', 311, 0))          # request chain end: idle
        nb = []
        for b, c, n, e in B:
            if not any(x[0] == cs.name for x in e):
                nb.append((b, c, n, e))
                continue
            if c == 'phy_dfi':
                continue
            e2 = []
            for inst, port in e:
                if inst != cs.name:
                    e2.append((inst, port))
                    continue
                mm = re.fullmatch(r'c(\d+)([io])', port)
                if mm:
                    e2.append((f'ctrlpc_{st}_{mm.group(1)}', 'c' + mm.group(2)))
                elif port in ('kc', 'ck', 'rsi'):
                    e2.append((kc.name, port))
                elif port == 'pll_hbm':
                    e2 += [(kc.name, 'pll_hbm')]
                elif port == 'hrst':
                    e2 += [(kc.name, 'hrst')]
                else:
                    raise ValueError(f'v5 ctrl: {cs.name}.{port} on {b} has no leaf port')
            if b.startswith('clk_hbm_'):
                e2 += [(f'ctrlpc_{st}_{k}', 'hclk') for k in range(NPC)]
            elif b.startswith('rst_hbm_'):
                e2 += [(f'ctrlpc_{st}_{k}', 'h_arst_n') for k in range(NPC)]
            nb.append((b, c, n, e2))
        B = nb
        for k in range(NPC):
            B.append((f'dfi_{st}_{k}', 'phy_dfi', 278, [(f'ctrlpc_{st}_{k}', 'phy'), (ph.name, f'*dfi:{k}')]))
            up = f'ctrlpc_{st}_{k - 1}' if k else kc.name
            B.append((f'kcc_{st}_{k}', 'hbm_cdc', 33, [(up, 'kco'), (f'ctrlpc_{st}_{k}', 'kci')]))
            B.append((f'rqc_{st}_{k}', 'hbm_cdc', 311, [(f'ctrlpc_{st}_{k}', 'rqo'), (up, 'rqi')]))
        B.append((f'dfi_{st}_req', 'phy_dfi', 311, [(kc.name, 'req'), (ph.name, '*dfi:req')]))
        drop_insts([cs.name])
        m['insts'] += new
        rec['ctrl'][st] = dict(strip=[cs.x, cs.y, cs.w, cs.h], kc=kc.name, pc=NPC)
    by = {i.name: i for i in m['insts']}

    # ---------------------------------------------------------------- T18 reset sequencer leaves, new reset nets
    pll, ck = by['pll'], by['clk_rx']
    rk = v.Inst('rstseq', 'qkd_rstseq', round(v.dn(pll.x - 54.0 - 4.32, v.GX), 4), pll.y, 54.0 - S, 54.0 - S,
                kind='ctl', region='kv_centre', domain=pll.domain)
    rr = v.Inst('rstseq_rom', 'qfd_rstseq', round(v.up(ck.x + ck.w + 4.32, v.GX), 4), ck.y, 54.0 - S, 54.0 - S,
                kind='ctl', region='hub', domain='stream_1p2')
    m['insts'] += [rk, rr]
    nb, ckr = [], False
    for b, c, n, e in B:
        if b == 'rst_fwd_s':
            e = [('rstseq', 'rso_fwd'), ('rstseq_rom', 'rsi')]
        else:
            e = [('rstseq', p) if (i, p[:4]) == ('pll', 'rso_') else ('rstseq_rom', p) if (i, p[:4]) == ('clk_rx', 'rso_')
                 else (i, p) for i, p in e]
        if b == 'clk_core_c':
            e = e + [('rstseq', 'ck')]
        if re.fullmatch(r'clk_r\d+', b) and not ckr:
            e, ckr = e + [('rstseq_rom', 'ck')], True
        nb.append((b, c, n, e))
    B = nb
    B.append(('pll_lock', 'spine_local', 1, [('pll', 'lock'), ('rstseq', 'rsi')]))
    field = [(i.name, 'rst_n') for i in m['insts'] if i.master in STATIONS or i.master == 'qfd_tile_nk']
    spine = [(i.name, 'rst_n') for i in m['insts'] if i.master in ('qfd_sp_res_ser', 'qfd_tt_up4', 'qfd_crom_g',
                                                                    'qfd_su_cbuf_g')]
    B += [('rst_field', 'reset', 1, [('rstseq_rom', 'rso_f')] + field),
          ('rst_spine', 'reset', 1, [('rstseq_rom', 'rso_s')] + spine)]
    rec['reset'] = dict(rst_field=len(field), rst_spine=len(spine), leaves=['rstseq', 'rstseq_rom'])

    # ---------------------------------------------------------------- T7 station word: _d / _r pairs, tap, tie
    nb, npair = [], 0
    for b, c, n, e in B:
        if c in ('corridor', 'head_chain') and len(e) == 2:
            (i0, p0), (i1, p1) = e
            nb.append((b, c, DW, [(i0, p0 + '_d'), (i1, p1 + '_d')]))
            nb.append((b + '_rdy', c, 1, [(i1, p1 + '_r'), (i0, p0 + '_r')]))
            pair[b] = b + '_rdy'
            npair += 1
        elif c == 'tap' and len(e) == 2:
            (i0, p0), (i1, p1) = e
            s_, t_ = ((i0, p0), (i1, p1)) if by[i0].master in STATIONS else ((i1, p1), (i0, p0))
            nb.append((b, c, DW, [(s_[0], 'tap_d'), (t_[0], 'tap')]))
            ties.append((s_[0], 'tap_r', 1, 1))
        else:
            nb.append((b, c, n, e))
    B = nb
    rec['station_word'] = dict(pairs=npair, data_bits=DW, tap_r_tied_high=sum(1 for t in ties if t[1] == 'tap_r'))

    m['buses'] = B

    # ---------------------------------------------------------------- KV relays inside a moved / grown block are torn
    torn = _tear_overlapped(v, m)
    rec['torn_kv_chains'] = torn
    if torn:
        m.setdefault('tp8b_kv', {}).setdefault('torn_chains', []).extend(torn)

    # ---------------------------------------------------------------- overlap / outline gate
    ins = sorted(m['insts'], key=lambda i: i.x)
    ov = []
    for a_ in range(len(ins)):
        p = ins[a_]
        for b_ in range(a_ + 1, len(ins)):
            q = ins[b_]
            if q.x >= p.x + p.w - 1e-3:
                break
            if q.y < p.y + p.h - 1e-3 and p.y < q.y + q.h - 1e-3:
                ov.append((p.name, q.name))
    W, H = m['die']['w'], m['die']['h']
    out = [i.name for i in ins if i.x < -1e-3 or i.y < -1e-3 or i.x + i.w > W + 1e-3 or i.y + i.h > H + 1e-3]
    rec.update(n_overlaps=len(ov), overlaps=ov[:20], outside=out[:20])
    if ov or out:
        raise SystemExit(f'tp8b v5: {len(ov)} overlaps {ov[:8]}, {len(out)} outside {out[:6]}')

    peers = {}
    for b, c, n, e in m['buses']:
        if c in ('clock_trunk', 'reset'):
            continue
        for j, (i, p) in enumerate(e):
            peers.setdefault((i, p.lstrip('*')), []).extend(x[0] for q, x in enumerate(e) if q != j)
    _wrap(v, m, G, peers)
    return rec


def _tear_overlapped(v, m):
    """a kept KV chain ('<cl>@kv' segments, relays as placed on the KV die) with a relay frame inside a block of this
    die is handed to _relays whole (its relays dropped, one bus source -> sink of the plain class)"""
    blocks = [i for i in m['insts'] if not i.master.startswith(('qkd_rly', 'qfd_rly'))]
    BK = 500.0
    grid = {}
    for i in blocks:
        for gx in range(int(i.x // BK), int((i.x + i.w) // BK) + 1):
            for gy in range(int(i.y // BK), int((i.y + i.h) // BK) + 1):
                grid.setdefault((gx, gy), []).append(i)
    bad = set()
    for r in m['insts']:
        if not r.master.startswith('qkd_rly'):
            continue
        for gx in range(int(r.x // BK), int((r.x + r.w) // BK) + 1):
            for gy in range(int(r.y // BK), int((r.y + r.h) // BK) + 1):
                for i in grid.get((gx, gy), ()):
                    if i.x < r.x + r.w - 1e-3 and r.x < i.x + i.w - 1e-3 and i.y < r.y + r.h - 1e-3 and r.y < i.y + i.h - 1e-3:
                        bad.add(r.name)
    if not bad:
        return []
    rl = {i.name for i in m['insts'] if i.master.startswith('qkd_rly')}
    chains = {}
    for j, (b, c, n, e) in enumerate(m['buses']):
        if c.endswith('@kv') and len(e) == 2:
            chains.setdefault(b.split('__r')[0], []).append(j)
    torn, drop_b, drop_i, add = [], set(), set(), []
    for b0, idxs in sorted(chains.items()):
        mem = {x[0] for j in idxs for x in m['buses'][j][3]}
        if not (mem & bad):
            continue
        segs = sorted((m['buses'][j] for j in idxs), key=lambda s_: (int(s_[0].split('__r')[1]) if '__r' in s_[0] else 0))
        torn.append(b0)
        drop_b |= set(idxs)
        drop_i |= mem & rl
        add.append((b0, segs[0][1][:-3], segs[0][2], [segs[0][3][0], segs[-1][3][-1]]))
    left = bad - drop_i
    if left:
        raise SystemExit(f'tp8b v5: {len(left)} kept KV relays inside a block belong to no 2-pin chain: {sorted(left)[:6]}')
    m['buses'] = [b for j, b in enumerate(m['buses']) if j not in drop_b] + add
    # multi-pin nets (clock trunks) lose the dropped relays
    m['buses'] = [(b, c, n, [x for x in e if x[0] not in drop_i]) if len(e) != 2 else (b, c, n, e) for b, c, n, e in m['buses']]
    m['insts'] = [i for i in m['insts'] if i.name not in drop_i]
    return torn


def _wrap(v, m, G, peers):
    import contract_v4_tp8 as V4
    base_m, base_pw, base_pr, base_case = v.masters, v.port_widths, v.pin_rects, v.case_real
    ties = m['ties']
    split = m['port_split']
    S = v.SHAVE
    plan_cache = {}

    def lay(f):
        return 'M5' if f in 'NS' else 'M4'

    def replan(model, M, inst_name, ports=None, skip=(), keep_extra=None):
        """single-instance master: the named face ports (default: all with a die peer) go to the die face toward their
        peer, ordered by the peer's projection; the instance orientation is applied (MX: N <-> S, MY: E <-> W)"""
        it = next(i for i in model['insts'] if i.name == inst_name)
        mst = M[it.master]
        if inst_name not in plan_cache:
            byi = {i.name: i for i in model['insts']}
            want = {}
            for p, sp in mst.ports.items():
                if sp[0] != 'face' or p in skip or (ports is not None and p not in ports):
                    continue
                pp = [byi[x] for x in peers.get((inst_name, p), ()) if x in byi and not x.startswith('rly_')]
                if not pp:
                    continue
                o = pp[0]
                ox, oy = o.x + o.w / 2, o.y + o.h / 2
                dxo = max(it.x - ox, 0.0, ox - (it.x + it.w))
                dyo = max(it.y - oy, 0.0, oy - (it.y + it.h))
                if dyo >= dxo:
                    f, a = ('N' if oy > it.y + it.h / 2 else 'S'), ox - it.x
                else:
                    f, a = ('E' if ox > it.x + it.w / 2 else 'W'), oy - it.y
                # die face / die-local coordinate -> master face / master-local coordinate
                if it.orient in ('MX', 'R180'):
                    f = {'N': 'S', 'S': 'N'}.get(f, f)
                    if f in 'EW':
                        a = it.h - a
                if it.orient in ('MY', 'R180'):
                    f = {'E': 'W', 'W': 'E'}.get(f, f)
                    if f in 'NS':
                        a = it.w - a
                want[p] = (f, a)
            plan_cache[inst_name] = want
        want = plan_cache[inst_name]
        for f in 'NSEW':
            L = mst.w if f in 'NS' else mst.h
            mine = [p for p, (ff, _) in want.items() if ff == f]
            if not mine:
                continue
            keep = [(sp[4] - sp[1] * 0.048 * sp[5] / 2, sp[4] + sp[1] * 0.048 * sp[5] / 2)
                    for p, sp in mst.ports.items() if sp[0] == 'face' and sp[2] == f and p not in want]
            keep += list((keep_extra or {}).get(f, ()))
            items = [(p, mst.ports[p][1] * 0.048, min(max(want[p][1], 4.0), L - 4.0)) for p in mine]
            for p, c in _pack(L, items, keep).items():
                mst.ports[p] = ('face', mst.ports[p][1], f, lay(f), round(c, 4), 1)

    def add_face(mst, port, bits, f, centre, pitch=1, layer=None):
        if port in mst.ports:
            mst.ports.pop(port)
            mst.order[:] = [q for q in mst.order if q != port]
        mst.face(port, bits, f, layer or lay(f), centre, pitch)

    def masters(model, k=1, port_bits=None):
        M = base_m(model, k, port_bits)
        byi = {i.name: i for i in model['insts']}
        Master = type(next(iter(M.values())))
        # ---- T7 stations / heads / tile
        for cell, faces in STATIONS.items():
            q = M.get(cell)
            if q is None:
                continue
            for f, (b, d) in faces.items():
                L = q.w if f in 'NS' else q.h
                sl = V4.band(L, DW + 3)
                mid = (DW + 3) // 2
                data = sl[:mid] + sl[mid + 2:-1]
                if b in q.ports:
                    q.ports.pop(b)
                    q.order[:] = [x for x in q.order if x != b]
                q.ports[b + '_d'] = ('pins', DW, f, lay(f), data, 1)
                q.ports[b + '_r'] = ('pins', 1, f, lay(f), [sl[-1]], 1)
                q.order += [b + '_d', b + '_r']
                if f == 'N':
                    q.ports['rst_n'] = ('pins', 1, 'N', 'M5', [sl[mid + 1]], 1)
                    q.order.append('rst_n')
        t = M.get('qfd_tile_nk')
        if t is not None:
            sp = t.ports['tap']
            t.ports['tap'] = (sp[0], DW) + tuple(sp[2:])
            add_face(t, 'rst_n', 1, sp[2], sp[4] - 30.0, 2)
        # ---- T8 cdc_wleaf
        q = M.get('qkd_cdc_wleaf')
        if q is not None:
            sc = CDC_WH / q.w
            q.w = q.h = CDC_WH
            for p, sp in list(q.ports.items()):
                if sp[0] == 'face':
                    q.ports[p] = sp[:4] + (min(round(sp[4] * sc, 4), CDC_WH - sp[1] * 0.048 * sp[5] / 2 - 1.0),) + sp[5:]
        # ---- T9 rhead cluster
        q = M.get('qkd_rhead')
        if q is not None:
            r = Master('qkd_rhead', RHEAD_WH[0], RHEAD_WH[1], 7, q.note + ' | contract v4 T9: hardened-once cluster 691.2 x '
                       '453.6 (16 x ot_qkh_lane8 + ot_qkh_ktree, 43.2-um centre relay channel)')
            x = 217.0
            for p, pitch in (('rst_n', 2), ('e', 2), ('s', 2), ('ti', 2)):
                n = q.ports[p][1]
                r.face(p, n, 'S', 'M5', x + n * 0.048 * pitch / 2, pitch)
                x += n * 0.048 * pitch + 2.0
            assert x <= 475.2, x
            r.face('nb', q.ports['nb'][1], 'E', 'M6', 226.8, 2)
            r.face("ck", 1, "N", "M7", 356.4, 1)
            M['qkd_rhead'] = r
        # ---- T12 res_ser
        q = M.get('qfd_sp_res_ser')
        if q is not None:
            q.w, q.h = 777.6, 518.4
            add_face(q, 'rst_n', 1, 'N', 392.0, 1)
            add_face(q, 'me_en', 1, 'N', 396.0, 1)
            add_face(q, 'fault', 1, 'E', 360.0, 1)
        # ---- T13 tt_up4 / tt_ctlm sel, rst_n; T15 crom; cbuf rst_n
        for mn in ('qfd_tt_up4', 'qfd_tt_ctlm'):
            q = M.get(mn)
            if q is not None and 'sel' in q.ports:
                sp = q.ports['sel']
                q.ports['sel'] = (sp[0], SEL_BITS) + tuple(sp[2:])
        q = M.get('qfd_tt_up4')
        if q is not None:
            add_face(q, 'rst_n', 1, 'N', 176.0, 1)
        q = M.get('qfd_crom_g')
        if q is not None:
            q.h = round(next(i.h for i in model['insts'] if i.master == 'qfd_crom_g'), 4)
            add_face(q, 'rst_n', 1, 'N', 180.0, 1)
        q = M.get('qfd_su_cbuf_g')
        if q is not None:
            add_face(q, 'rst_n', 1, 'N', 185.0, 1)
        M.pop('qfd_tt_up4_g', None)
        # ---- T16 control strip leaves
        cs = M.get('qkd_ctrl')
        note = 'KV control strip leaf (contract v5 T16, el1013-qwen-kvstrips 08:06)'
        pc = Master('qkd_ctrl_pc', cs.w if cs is not None else 247.512, PC_H - S, 5, note + ': per-PC controller = head + '
                    'pcport KVW 2 + kcmd tap, PC id as a strap; registers at every pin')
        pc.face('ci', 319, 'W', 'M4', 161.27 - KC_H, 1)
        pc.face('co', 294, 'W', 'M4', 300.25 - KC_H, 1)
        pc.face('phy', 278, 'E', 'M4', PC_PHY_Y, 2)
        pc.face('kci', 33, 'S', 'M5', 40.0, 2)
        pc.face('kco', 33, 'N', 'M5', 40.0, 2)
        pc.face('rqo', 311, 'S', 'M5', 150.0, 2)
        pc.face('rqi', 311, 'N', 'M5', 150.0, 2)
        pc.face('pc', 5, 'W', 'M4', 20.0, 2)
        pc.area('hclk', 1, pc.w / 2, pc.h / 2, 1)
        pc.area('h_arst_n', 1, pc.w / 2 + 1.6, pc.h / 2, 1)
        M['qkd_ctrl_pc'] = pc
        kc = Master('qkd_ctrl_kc', pc.w, KC_H - S, 5, note + ': kc async FIFO (core -> hclk), HBM clock / reset entry, '
                    'PHY request port')
        kc.face('kc', 33, 'S', 'M5', 123.76, 1)
        kc.face('kco', 33, 'N', 'M5', 40.0, 2)
        kc.face('rqi', 311, 'N', 'M5', 150.0, 2)
        kc.face('req', 311, 'E', 'M4', 22.0, 1)
        kc.area('ck', 1, 196.0, 10.0, 1)
        kc.area('rsi', 1, 198.0, 10.0, 1)
        kc.area('pll_hbm', 1, 200.0, 10.0, 1)
        kc.area('hrst', 1, 202.0, 10.0, 1)
        M['qkd_ctrl_kc'] = kc
        M.pop('qkd_ctrl', None)
        M.pop('qkd_ctrl_n', None)
        # ---- T18 reset sequencer leaves; PLL lock
        rk = Master('qkd_rstseq', 54.0 - S, 54.0 - S, 5, 'ot_qwen_sys_rst_seq (KV centre): PLL lock in, one registered '
                    'reset root per quadrant + centre + forward')
        rk.face('ck', 1, 'N', 'M5', 27.0, 1)
        rk.face('rsi', 1, 'W', 'M4', 27.0, 1)
        for j, p in enumerate(('rso_WS', 'rso_WN', 'rso_ES', 'rso_EN', 'rso_c', 'rso_fwd')):
            rk.face(p, 1, 'E' if j % 2 else 'S', 'M4' if j % 2 else 'M5', 10.0 + 6.0 * j, 1)
        M['qkd_rstseq'] = rk
        rr = Master('qfd_rstseq', 54.0 - S, 54.0 - S, 5, 'ot_qwen_sys_rst_seq (ROM side): forwarded reset in, roots for '
                    'seq_su, tt_ctlm, the tile field and the spine blocks')
        rr.face('ck', 1, 'N', 'M5', 27.0, 1)
        rr.face('rsi', 1, 'W', 'M4', 27.0, 1)
        for j, p in enumerate(('rso_seq', 'rso_ctlm', 'rso_f', 'rso_s')):
            rr.face(p, 1, 'E' if j % 2 else 'S', 'M4' if j % 2 else 'M5', 12.0 + 8.0 * j, 1)
        M['qfd_rstseq'] = rr
        q = M.get('qkd_pll')
        if q is not None and 'lock' not in q.ports:
            q.area('lock', 1, q.w / 2, q.h / 2 + 8.0, 1)
        # ---- T14: the mirrored group keeps R0; its N / S pin faces swap (same x)
        for mn in ('qfd_su_cbuf_g', 'qfd_crom_g', 'qfd_sp_su64_sfu'):
            q = M.get(mn)
            if q is None:
                continue
            for p, sp in list(q.ports.items()):
                if sp[0] == 'face' and sp[2] in 'NS' and p not in ('va', 'vq'):
                    q.ports[p] = sp[:2] + ('S' if sp[2] == 'N' else 'N',) + sp[3:]
        # ---- T10 / T14 / T17: VM region, SU, seq_su, control tile: pins toward their peers on the final placement
        vmm = M.get('qfd_sp_vector_memory')
        if vmm is not None:
            vi, si = byi['sp_vector_memory'], byi['sp_su64_sfu']
            sx, sy = VM_ENV['w'] / vmm.w, VM_ENV['h'] / vmm.h
            n = Master(vmm.name, VM_ENV['w'], VM_ENV['h'], vmm.obs_top, vmm.note + ' | contract v4 T10: region of hardened '
                       'leaves 4708.8 x 2347.92; pins toward their peers (faces provisional until the leaves close)')
            for p in dict.fromkeys(vmm.order):
                sp = vmm.ports.get(p)
                if sp is None or p in ('xw', 'xe', 'ckx'):
                    continue
                if sp[0] == 'area':
                    n.ports[p] = (sp[0], sp[1], round(sp[2] * sx, 3), round(sp[3] * sy, 3)) + tuple(sp[4:])
                else:
                    n.ports[p] = sp
                n.order.append(p)
            for p in ('xw', 'xe'):
                n.face(p + '_d', DW, 'S', 'M5', 0.0, 1)
                n.face(p + '_r', 1, 'S', 'M5', 0.0, 1)
            if 'ib' not in n.ports:
                n.face('ib', 380, 'S', 'M5', 0.0, 1)
            else:
                n.ports['ib'] = ('face', 380) + tuple(n.ports['ib'][2:])
            M[vmm.name] = n
            # ready pins ride beside their data group: planned as one group, then split
            replan(model, M, 'sp_vector_memory', skip=('sa', 'sq', 'xw_r', 'xe_r'),
                   keep_extra={'N': [(si.x - vi.x - 4.0, si.x + si.w - vi.x + 4.0)]})
            for p in ('xw', 'xe'):
                d = n.ports[p + '_d']
                n.ports[p + '_r'] = ('face', 1, d[2], d[3], round(d[4] + DW * 0.048 / 2 + 0.6, 4), 1)
        for inst, mn, kw in (('seq_su', 'qfd_seq_su', {}),
                             ('sp_su64_sfu', 'qfd_sp_su64_sfu', dict(ports=('si', 'sd', 'acc', 'q', 'eq', 'ea', 'ecr'))),
                             ('tt_ctlm', 'qfd_tt_ctlm', None)):
            q = M.get(mn)
            if q is None or inst not in byi:
                continue
            if mn == 'qfd_seq_su':
                for p in ('ib', 'dflt'):
                    if p in q.ports:
                        q.ports.pop(p)
                        q.order[:] = [x for x in q.order if x != p]
                for p, nbit in (('dc', 56), ('dh', 187), ('cc', 517)):
                    q.ports[p] = ('face', nbit) + tuple(q.ports[p][2:])
            if mn == 'qfd_tt_ctlm':
                q.face('ib', 380, 'N', 'M5', 0.0, 1)
                for j in range(3):
                    q.face(f'mer{j}', 1, 'W', 'M4', 0.0, 1)
                    q.face(f'rf{j}', 1, 'W', 'M4', 0.0, 1)
                kw = dict(ports=tuple(p for p in q.ports if 'sp_vector_memory' in peers.get((inst, p), ())
                                      or p.startswith(('mer', 'rf'))))
            replan(model, M, inst, **kw)
        return M

    def port_widths(model, k=1):
        w = base_pw(model, k)
        byi = {i.name: i for i in model['insts']}
        live = {}
        for bid, cls, bits, eps in model['buses']:
            n = bits if k == 1 else max(1, math.ceil(bits / k))
            for inst, port in eps:
                key = (byi[inst].master, port.lstrip('*'))
                live[key] = max(live.get(key, 0), n)
        for inst, port, bits, val in ties:
            if inst in byi:
                key = (byi[inst].master, port)
                live[key] = max(live.get(key, 0), bits)
        # a port without a die net on THIS die is not emitted (the KV-die widths carried D2D faces: qkd_seq rf / tf)
        return {key: live[key] for key in set(w) | set(live) if key in live}

    def pin_rects(mst, k, wmap):
        mine = {p: sp for p, sp in mst.ports.items() if sp[0] == 'pins'}
        if mine:
            cp = type(mst)(mst.name, mst.w, mst.h, mst.obs_top, mst.note)
            cp.ports = {p: sp for p, sp in mst.ports.items() if p not in mine}
            cp.order = [p for p in mst.order if p not in mine]
            out = base_pr(cp, k, wmap)
            depth = 0.192
            for p in dict.fromkeys(q for q in mst.order if q in mine):
                _, n0, f, layer, poss, _ = mine[p]
                n = min(wmap.get(p, n0), len(poss))
                for i in range(n):
                    pos = poss[i]
                    hw = 0.012
                    r = {'W': (0.0, pos - hw, depth, pos + hw), 'E': (mst.w - depth, pos - hw, mst.w, pos + hw),
                         'S': (pos - hw, 0.0, pos + hw, depth), 'N': (pos - hw, mst.h - depth, pos + hw, mst.h)}[f]
                    out.append((f'{p}[{i}]', layer, r))
        else:
            out = base_pr(mst, k, wmap)
        sp_ = split.get(mst.name)
        if sp_ and k == 1 and getattr(v, 'EMIT_SPLIT', False):
            ren = {}
            for bundle, parts in sp_.items():
                j = 0
                for pn, nb in parts:
                    for b in range(nb):
                        ren[f'{bundle}[{j}]'] = f'{pn}[{b}]'
                        j += 1
            out = [(ren.get(nm, nm), layer, r) for nm, layer, r in out]
        return out

    def write_netlist(model, k, path, top='qfd_die'):
        byi = {it.name: it for it in model['insts']}
        conns = {it.name: [] for it in model['insts']}
        phyb = {}                                   # phy instance -> {pin base: {bit: expr}}
        V = [f'// tools/qwen_kv_die/tp8b_v5.py: die-level nets only (k = {k}); constants = straps, chain ends, tap_r',
             f'module {top} ();']
        groups = phy_groups()
        phyn = [p[0] for p in v.phy_pins()]

        def phy_all(inst, net):
            for i, pn in enumerate(phyn):
                mm = re.match(r'^(.*)\[(\d+)\]$', pn)
                b, j = (mm.group(1), int(mm.group(2))) if mm else (pn, 0)
                phyb.setdefault(inst, {}).setdefault(b, {})[j] = f'{net}[{i}]'
        for bid, cls, bits, eps in model['buses']:
            n = bits if k == 1 else max(1, math.ceil(bits / k))
            net = f'n_{bid}'
            V.append(f'  wire [{n - 1}:0] {net};')
            for inst, port in eps:
                if port.startswith('*dfi:') and k == 1:
                    for i, (b, j) in enumerate(groups[port[5:]]):
                        phyb.setdefault(inst, {}).setdefault(b, {})[j] = f'{net}[{i}]'
                elif port == '*dfi' and k == 1:
                    phy_all(inst, net)
                else:
                    pn = port.lstrip('*')
                    parts = split.get(byi[inst].master, {}).get(pn) if k == 1 else None
                    if parts:
                        j = 0
                        for sub, nb in parts:
                            conns[inst].append(f'.{sub}({net}[{j + nb - 1}:{j}])')
                            j += nb
                    else:
                        conns[inst].append(f'.{pn}({net})')
        for inst, port, bits, val in ties:
            if inst in conns:
                conns[inst].append(f".{port}({bits}'d{val})")
        for inst, d in phyb.items():
            for b, bits_ in sorted(d.items()):
                hi = max(bits_)
                if hi == 0 and not any(pn.startswith(b + '[') for pn in phyn):
                    conns[inst].append(f'.{v.esc(b)}({bits_[0]})')
                else:
                    cat = ', '.join(bits_.get(j, "1'b0") for j in range(hi, -1, -1))
                    conns[inst].append(f'.{v.esc(b)}({{{cat}}})')
        for it in model['insts']:
            V.append(f'  {it.master} {it.name} (' + ', '.join(conns[it.name]) + ');')
        V.append('endmodule\n')
        Path(path).write_text('\n'.join(V))

    base_phy = v.phy_pins

    def phy_pins():
        ys = phy_pin_y()
        out = []
        for pn, yc in base_phy():
            mm = re.match(r'^(.*)\[(\d+)\]$', pn)
            key = (mm.group(1), int(mm.group(2))) if mm else (pn, 0)
            out.append((pn, ys.get(key, yc)))
        return out

    def case_real(model, work):
        v.EMIT_SPLIT = True
        try:
            r = base_case(model, work)
        finally:
            v.EMIT_SPLIT = False
        f = Path(work) / 'phy_ew.lef'
        if f.exists():
            f.write_text(phy_repin(f.read_text()))
        return r

    v.masters, v.port_widths, v.pin_rects, v.write_netlist, v.phy_pins, v.case_real = \
        masters, port_widths, pin_rects, write_netlist, phy_pins, case_real
