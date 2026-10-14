"""Qwen TP8 split COMPUTE die (owner 2026-10-14 06:45): the spine slot table of compute-die contract v1.

Called from tools/qwen_kv_die/tp8b_v5.apply (OT_TP8_SPLIT=compute) after every v5 rule and before the overlap / reticle
gate and the relay plan, so the relays, cuts, reset tree, pin_align and the assigned pin files are made on THIS placement.

Layout (top-down, generous margins; el1014-qwen-split-compute.log, contract v1 / C4):
  * tile field W / E of the spine (tp8b F2, 48 x 16, slot from OT_TP8_SPLIT_TILE, C4 449.28 x 1,442.88 / pitch 522.288),
    IO band on the S edge (unchanged).
  * spine = [x0, x1] between the W field's last station and the E field's first tile; MARGIN relay channel on each side.
  * W slab column: per band b the W-half slab stack at the band's tile centroid, centred on the port column (res_ser /
    port_tiles_b / band_lanes_b); E slab column (spine E edge): port_tiles_b_f1 at the band centroid (E-field block words
    land without crossing the spine; one 512-b pfrag word per band crosses).
  * middle, N -> S: the die link (ucie_kv PHY on the N edge, qfd_d2d_rom below it, forwarded-clock bump + reset sync
    beside), the SU slot with the constant group (seq_su, 8 cbuf_g, 8 crom_g) E of it and the x tap qfd_xs_tap E of
    that, the TRIMMED VM (4,708.8 x 2,203.2, M7 cap) abutted under the SU, the tree top (tt_ctlm + tt_up4), then the
    clock receiver + reset leaf at the die centre.
  * distributed x slices (owner 10-14): qfd_xcol_e/w in each column corridor on the head row, qfd_xcst_n/s stations.
Everything is a slot of the contract: a master that does not fit its slot files a slot change request in the log.
"""
import json
import os

CH = 86.4                       # relay channel between spine slots (two 30-um relay rows + spacing)
PORT_WH = (1036.8, 2462.4)      # qfd_port_tiles_* slot: 2.553 mm2 >= the measured 2.536 mm2 need (blockers G7)
RES_WH = (777.6, 518.4)
LANES_WH = (777.6, 1131.84)
SU_WH = (3240.0, 3672.0)        # qfd_sp_su64_sfu: 64-lane component 4.84 mm2 children + reducer + glue (Codex 3434 x 2570 bbox)
VM_WH = (4708.8, 2203.2)        # TRIMMED central VM (owner 08:20 PT 10-14: distributed x slices adopted; banks / SU ports / row reads only, M7 cap, no wall)
CTLM_WH = (777.6, 1814.4)
UP4_WH = (345.6, 388.8)
CLKRX_WH = (412.488, 412.488)
# ---- C4 (2026-10-14, compute-die lead r2): owner-adopted distributed x slices (HANDOFF 0aa, el1014-qwen-dvm-build.log)
DVM = os.environ.get('OT_SPLIT_DVM', '1') != '0'
XCOL_WH = (64.8, 1313.28)       # qfd_xcol_e/w: xhead + 8 x qfd_xs_leaf (two write chains N / S), in the column corridor,
                                # centred on the head row; 604.8 N + 103.68 head + 604.8 S (contract v1 slice slots)
TAP_WH = (345.6, 345.6)         # qfd_xs_tap at the VM N face, E of the constant group (SU write tap + attention write tap)
XCOR_D = 516                    # corridor word {go 1, ib 379, xl 128, tag 8} (qfd_xcst / qfd_xcol n_d / s_d)
XHEAD_D = 1567                  # head-row word {go 1, ib 379, desc 73, fill 1114} (qfd_xcol w_d / e_d)
TAP_SW, TAP_AW, TAP_PF, TAP_GI = 1 + 24 + 64 + 2048, 1 + 24 + 16 + 512, 74, 380


# C5: masters whose hardened children each take their own die clock entry (delivered at phi - R of that child):
# die ports ck0 .. ck<n-1> = RTL clock port bits ck[n-1:0] (qfd_tt_up4: 5 = 4 leaves + cluster pin flops, r5 10-14;
# qfd_xcol_e/w: 9 = xhead + 8 leaves, ot_qfd_xslice_slots.sv)
CHILD_CK = {'qfd_tt_up4': 5, 'qfd_xcol_e': 9, 'qfd_xcol_w': 9}


def _child_clocks(m, rec):
    n_of = {i.name: CHILD_CK[i.master] for i in m['insts'] if i.master in CHILD_CK}
    nb = []
    for b, c, n, e in m['buses']:
        if c == 'clock_trunk' and any(i in n_of and p == 'ck' for i, p in e):
            e2 = []
            for i, p in e:
                e2 += [(i, f'ck{k}') for k in range(n_of[i])] if (i in n_of and p == 'ck') else [(i, p)]
            e = e2
        nb.append((b, c, n, e))
    m['buses'] = nb
    rec['child_clocks'] = {k: v for k, v in CHILD_CK.items()}


def _dvm(v, m, put, rec, vm, su, xt):
    """Distributed x slices in the die (C4): stations -> qfd_xcst_n/s (516-b corridor word), column heads ->
    qfd_xcol_e/w (one cluster slot per column in the corridor, centred on the head row), the x tap qfd_xs_tap at the VM
    N face.  The two head roots take ONE word each from the tap (hw / he = {go, ib, desc, fill}); the tree top's go / ib
    (tt_ib, was ctlm -> VM) goes to the tap, which aligns it with the fill in its own pipeline (DIE REQUEST to the DVM
    builder: tap RTL takes gi[379:0] and drives two registered copies hw / he; the central VM loses its x ports xw / xe /
    ib).  Straps (constant ties of strap ports, as the RTL wrappers declare): xcst sidx = station index from the head
    outward, xcol tid0 = column * 16, tile_id = column * 16 + (N half: die row - 8, S half: 15 - die row)."""
    S = v.SHAVE
    by = {i.name: i for i in m['insts']}
    mid = m['geo']['mid']
    heads = sorted((i for i in m['insts'] if i.kind == 'head'), key=lambda i: i.x)
    half = len(heads) // 2
    ties = m.setdefault('ties', [])
    for c, h in enumerate(heads):
        cy = h.y + h.h / 2
        h.master = 'qfd_xcol_w' if c < half else 'qfd_xcol_e'
        h.w, h.h = XCOL_WH[0] - S, XCOL_WH[1] - S
        h.y = round(v.dn(cy - XCOL_WH[1] / 2, v.GY), 4)
        ties.append((h.name, 'tid0', 16, c * 16))
    rows = {}
    for i in m['insts']:
        if i.kind == 'station':
            i.master = 'qfd_xcst_n' if i.y >= mid else 'qfd_xcst_s'
            c, r = (int(q) for q in i.name.split('_')[1:3])
            rows.setdefault(c, []).append(r)
    nr = max(max(q) for q in rows.values()) + 1
    for i in m['insts']:
        if i.kind == 'station':
            c, r = (int(q) for q in i.name.split('_')[1:3])
            ties.append((i.name, 'sidx', 3, (r - nr // 2) if r >= nr // 2 else (nr // 2 - 1 - r)))
        elif i.kind == 'tile' and i.name.startswith('t_'):
            c, r = (int(q) for q in i.name.split('_')[1:3])
            ties.append((i.name, 'tile_id', 16, c * 16 + ((r - nr // 2) if r >= nr // 2 else (nr - 1 - r))))
    tap = v.Inst('xs_tap', 'qfd_xs_tap', 0.0, 0.0, TAP_WH[0] - S, TAP_WH[1] - S, kind='spine', region='hub',
                 domain=vm.domain)
    m['insts'].append(tap)
    tap.x, tap.y = _snap(v, xt, v.GX), _snap(v, su.y, v.GY)
    rec['slots']['xs_tap'] = [tap.x, tap.y, round(tap.w, 3), round(tap.h, 3)]
    roots = {}
    nb = []
    for b, c, n, e in m['buses']:
        if c == 'corridor':
            n = XCOR_D if n > 1 else n
        elif c == 'head_chain':
            e = [(('xs_tap', {'xw': 'hw', 'xe': 'he'}[p.rsplit('_', 1)[0]] + '_' + p.rsplit('_', 1)[1])
                  if i == 'sp_vector_memory' else (i, p)) for i, p in e]
            n = XHEAD_D if n > 1 else n
            if any(i == 'xs_tap' for i, p in e):
                roots[b] = e
        elif b == 'tt_ib':
            e = [(i, p) if i != 'sp_vector_memory' else ('xs_tap', 'gi') for i, p in e]
        nb.append((b, c, n, e))
    nb += [('xs_sw', 'spine_local', TAP_SW, [('sp_su64_sfu', 'xsw'), ('xs_tap', 'sw')]),
           ('xs_aw', 'spine_local', TAP_AW, [('sp_vector_memory', 'xaw'), ('xs_tap', 'aw')]),
           ('xs_pf', 'sequencer', TAP_PF, [('tt_ctlm', 'xpf'), ('xs_tap', 'xpf')]),
           ('xs_fault', 'spine_local', 1, [('xs_tap', 'fault'), ('tt_ctlm', 'xflt')])]
    # xcol 'fault' outputs (48): NOT wired (port-bind lists them as unread outputs); die request to the DVM builder: chain
    # the column fault inward along the head row (fault_i input) so one fault per root reaches the tap
    m['buses'] = nb
    rec['dvm'] = dict(xcol=len(heads), xcst=sum(1 for i in m['insts'] if i.kind == 'station'), tap=list(rec['slots']['xs_tap']),
                      xcol_wh=list(XCOL_WH), corridor_bits=XCOR_D, head_bits=XHEAD_D, roots=sorted(roots),
                      straps=dict(sidx='station index from the head outward', tid0='column*16',
                                  tile_id='column*16 + (N: row-8, S: 15-row)'))


def _snap(v, x, g):
    return round(v.dn(x, g), 4)


def _place_su_vm(put, cx, su_y):
    """Keep the r21v registered SU/VM seam at its actual abutted pin faces.

    The VM is wider than the SU. Leave one channel of positive face offset
    inside the VM span; the E-side constant group still fits in that span.
    put() snaps both origins and subtracts SHAVE from their outlines, leaving
    the existing 24-nm contact gap and no additional RTL transport edge.
    """
    vm_x = cx - VM_WH[0] / 2
    su = put('sp_su64_sfu', vm_x + CH, su_y, SU_WH)
    vm = put('sp_vector_memory', vm_x, su.y - VM_WH[1], VM_WH)
    return su, vm


def place(v, m, G):
    by = {i.name: i for i in m['insts']}
    tiles = [i for i in m['insts'] if i.master == 'qfd_tile_nk']
    xs = sorted({round(i.x, 4) for i in tiles})
    ys = sorted({round(i.y, 4) for i in tiles})
    th = tiles[0].h
    half = len(xs) // 2
    pitch = xs[1] - xs[0]
    x0 = round(xs[half - 1] + pitch, 4)          # W field end (its last station column + gap)
    x1 = xs[half]                                # E field start
    H = m['die']['h']
    top = H - 21.6
    io_top = max(i.y + i.h for i in m['insts'] if i.kind in ('io', 'xfifo'))
    rec = dict(spine_x=[x0, x1], spine_w=round(x1 - x0, 3), die=[m['die']['w'], H], slots={})

    def put(name, x, y, wh=None):
        i = by[name]
        if wh is not None:
            i.w, i.h = wh[0] - v.SHAVE, wh[1] - v.SHAVE
        i.x, i.y = _snap(v, x, v.GX), _snap(v, y, v.GY)
        rec['slots'][name] = [i.x, i.y, round(i.w, 3), round(i.h, 3)]
        return i

    # ---- W column: the band's W-half slab stack (C4: band_lanes / port_tiles / res_ser CENTRED on the port column so
    # the abutted tw / ty / rq faces stand face to face; v1-a left them off-centre and the 8,192-b tw / ty pair read as a
    # 1.485 horizontal cut).  E column (C4, as the merged tp8b): the band's E-half slab port_tiles_<b>_f1 on the spine's E
    # edge at the band centroid, so the 24 E-field block words land without crossing the VM / SU sub-area (v1-a put
    # _f1 in the W sub-area: 24 x 512 b across the spine); only the band's one 512-b pfrag word crosses.
    xa = x0 + CH
    xf = x1 - CH - PORT_WH[0]
    dl = (PORT_WH[0] - LANES_WH[0]) / 2
    dr = (PORT_WH[0] - RES_WH[0]) / 2
    bands = getattr(v, 'BAND_BLOCKS', None) or {}
    cents = []
    for b in range(3):
        cy = [(ys[r0] + ys[r0 + 3] + th) / 2 for c0, r0 in bands[b]]
        cents.append(sum(cy) / len(cy))
    gh = RES_WH[1] + PORT_WH[1] + LANES_WH[1] + 2 * 4.32
    lo = io_top + CH
    lo_f = io_top + CH
    for b in range(3):
        y0 = max(lo, cents[b] - gh / 2)
        y0 = min(y0, top - gh) if b == 2 else y0
        put(f'sp_band_lanes_{b}', xa + dl, y0, LANES_WH)
        put(f'sp_port_tiles_{b}', xa, y0 + LANES_WH[1] + 4.32, PORT_WH)
        put(f'sp_res_ser_{b}', xa + dr, y0 + LANES_WH[1] + PORT_WH[1] + 8.64, RES_WH)
        yf = max(lo_f, cents[b] - PORT_WH[1] / 2)
        yf = min(yf, top - PORT_WH[1])
        put(f'sp_port_tiles_{b}_f1', xf, yf, PORT_WH)
        rec.setdefault('band_centroid_y', []).append(round(cents[b], 1))
        lo = y0 + gh + CH
        lo_f = yf + PORT_WH[1] + CH
    xw_end = xa + PORT_WH[0] + CH
    # ---- E sub-area (between the W slab column and the E slab column)
    xe = xw_end
    we = xf - CH - xe
    rec['e_area'] = [round(xe, 3), round(we, 3)]
    rec['slab_cols'] = dict(W=round(xa, 3), E=round(xf, 3))
    if we < VM_WH[0]:
        raise SystemExit(f'split compute spine: E sub-area {we:.1f} um < VM {VM_WH[0]} (raise OT_TP8_SPLIT_SPINE)')
    cx = xe + we / 2
    # die link at the N edge (centred on the E sub-area): PHY on the edge, adapter under it, bump + reset sync W of it
    ph = put('ucie_kv', cx - 777.6 / 2, top - 777.6)
    ad = put('d2d_rom', ph.x, ph.y - 4.32 - by['d2d_rom'].h)
    put('rs_bump', ph.x - 4.32 - by['rs_bump'].w - 4.32, ph.y - by['rs_bump'].h / 2)
    put('ckb_rom', ph.x - 4.32 - by['ckb_rom'].w - 4.32, ph.y + 30.0)
    # SU slot below the link, constant group E of it
    su, vm = _place_su_vm(put, cx, ad.y - CH - SU_WH[1])
    gx = su.x + SU_WH[0] + CH
    cb = sorted((i for i in m['insts'] if i.master == 'qfd_su_cbuf_g'), key=lambda i: int(i.name.rsplit('_', 1)[1]))
    cr = sorted((i for i in m['insts'] if i.master == 'qfd_crom_g'), key=lambda i: int(i.name.rsplit('_', 1)[1]))
    yy = su.y + SU_WH[1]
    for k, i in enumerate(cr):                   # 2 columns x 4: crom (583.2 tall) at the SU top, cbuf below
        put(i.name, gx + (k % 2) * (i.w + 4.32), yy - (k // 2 + 1) * (i.h + 4.32))
    yc = yy - 4 * (cr[0].h + 4.32) - 21.6
    for k, i in enumerate(cb):
        put(i.name, gx + (k % 2) * (i.w + 4.32), yc - (k // 2 + 1) * (i.h + 4.32))
    yq = yc - 4 * (cb[0].h + 4.32) - 21.6
    sq = by.get('seq_su')
    if sq is not None:
        put('seq_su', gx, yq - sq.h)
    if gx + 2 * (cr[0].w + 4.32) > xf - CH + 1e-3 or (sq is not None and sq.y < su.y - 1e-3):
        raise SystemExit(f'split compute spine: constant group does not fit E of the SU (gx {gx:.1f}, xf {xf:.1f})')
    # The VM was placed with the SU above: S(SU) and N(VM) are abutted,
    # matching the existing zero-relay registered seam and its latency.
    # tree top below the VM, clock receiver + reset leaf at the die centre
    ct = put('tt_ctlm', cx - CTLM_WH[0] - 2.16, vm.y - CH - CTLM_WH[1], CTLM_WH)
    put('tt_up4_0', ct.x + CTLM_WH[0] + 4.32, ct.y + CTLM_WH[1] - UP4_WH[1], UP4_WH)
    if DVM:
        _dvm(v, m, put, rec, vm, su, gx + max(2 * (cr[0].w + 4.32), sq.w if sq is not None else 0.0) + CH)
    ymid = (io_top + top) / 2
    ck = put('clk_rx', cx - CLKRX_WH[0] / 2, min(ymid - CLKRX_WH[1] / 2, ct.y - CH - CLKRX_WH[1]))
    put('rstseq_rom', ck.x + ck.w + 4.32, ck.y)
    # ---- containment: every spine slot inside [x0, x1] x [io_top, top]
    bad = [n for n, (x, y, w, h) in rec['slots'].items() if x < x0 - 1e-3 or x + w > x1 + 1e-3 or y < io_top - 1e-3 or y + h > top + 1e-3]
    rec['outside_spine'] = bad
    if bad:
        raise SystemExit(f'split compute spine: slots outside the spine: {bad[:8]}')
    _child_clocks(m, rec)
    if os.environ.get('OT_SPLIT_DUMP'):
        ins = [dict(n=i.name, m=i.master, x=i.x, y=i.y, w=i.w, h=i.h, o=i.orient) for i in m['insts']]
        json.dump(dict(die=m['die'], rec=rec, insts=ins), open(os.environ['OT_SPLIT_DUMP'], 'w'), default=str)
    m['split_compute'] = rec
    return rec
