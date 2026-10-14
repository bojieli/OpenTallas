"""Qwen TP8 split COMPUTE die (owner 2026-10-14 06:45): the spine slot table of compute-die contract v1.

Called from tools/qwen_kv_die/tp8b_v5.apply (OT_TP8_SPLIT=compute) after every v5 rule and before the overlap / reticle
gate and the relay plan, so the relays, cuts, reset tree, pin_align and the assigned pin files are made on THIS placement.

Layout (top-down, generous margins; el1014-qwen-split-compute.log, contract v1):
  * tile field W / E of the spine (tp8b F2, 48 x 16, slot from OT_TP8_SPLIT_TILE), IO band on the S edge (unchanged).
  * spine = [x0, x1] between the W field's last station and the E field's first tile; MARGIN relay channel on each side.
  * W sub-area: per band b one slab group at the band's tile centroid: column A = res_ser / port_tiles_b / band_lanes_b
    (N -> S), column B = port_tiles_b_f1; slab frames sized to the measured need (2.536 mm2 per port frame, blockers G7)
  * E sub-area, N -> S: the die link (ucie_kv PHY on the N edge, qfd_d2d_rom below it, forwarded-clock bump + reset sync
    beside), the SU slot with the constant group (seq_su, 8 cbuf_g, 8 crom_g) E of it, the VM envelope (accepted
    4,838.4 x 2,546.64, M9 cap), the tree top (tt_ctlm + tt_up4), then the clock receiver + reset leaf at the die centre.
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

    # ---- W sub-area: band slab groups at the band centroids
    xa = x0 + CH
    xb = xa + PORT_WH[0] + CH
    bands = getattr(v, 'BAND_BLOCKS', None) or {}
    cents = []
    for b in range(3):
        cy = [(ys[r0] + ys[r0 + 3] + th) / 2 for c0, r0 in bands[b]]
        cents.append(sum(cy) / len(cy))
    gh = RES_WH[1] + PORT_WH[1] + LANES_WH[1] + 2 * 4.32
    lo = io_top + CH
    for b in range(3):
        y0 = max(lo, cents[b] - gh / 2)
        y0 = min(y0, top - gh) if b == 2 else y0
        put(f'sp_band_lanes_{b}', xa, y0, LANES_WH)
        put(f'sp_port_tiles_{b}', xa, y0 + LANES_WH[1] + 4.32, PORT_WH)
        put(f'sp_res_ser_{b}', xa, y0 + LANES_WH[1] + PORT_WH[1] + 8.64, RES_WH)
        put(f'sp_port_tiles_{b}_f1', xb, y0 + (gh - PORT_WH[1]) / 2, PORT_WH)
        rec.setdefault('band_centroid_y', []).append(round(cents[b], 1))
        lo = y0 + gh + CH
    xw_end = xb + PORT_WH[0] + CH
    # ---- E sub-area
    xe = xw_end
    we = x1 - CH - xe
    rec['e_area'] = [round(xe, 3), round(we, 3)]
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
    if gx + 2 * (cr[0].w + 4.32) > x1 - CH + 1e-3 or (sq is not None and sq.y < su.y - 1e-3):
        raise SystemExit(f'split compute spine: constant group does not fit E of the SU (gx {gx:.1f}, x1 {x1:.1f})')
    # The VM was placed with the SU above: S(SU) and N(VM) are abutted,
    # matching the existing zero-relay registered seam and its latency.
    # tree top below the VM, clock receiver + reset leaf at the die centre
    ct = put('tt_ctlm', cx - CTLM_WH[0] - 2.16, vm.y - CH - CTLM_WH[1], CTLM_WH)
    put('tt_up4_0', ct.x + CTLM_WH[0] + 4.32, ct.y + CTLM_WH[1] - UP4_WH[1], UP4_WH)
    ymid = (io_top + top) / 2
    ck = put('clk_rx', cx - CLKRX_WH[0] / 2, min(ymid - CLKRX_WH[1] / 2, ct.y - CH - CLKRX_WH[1]))
    put('rstseq_rom', ck.x + ck.w + 4.32, ck.y)
    # ---- containment: every spine slot inside [x0, x1] x [io_top, top]
    bad = [n for n, (x, y, w, h) in rec['slots'].items() if x < x0 - 1e-3 or x + w > x1 + 1e-3 or y < io_top - 1e-3 or y + h > top + 1e-3]
    rec['outside_spine'] = bad
    if bad:
        raise SystemExit(f'split compute spine: slots outside the spine: {bad[:8]}')
    if os.environ.get('OT_SPLIT_DUMP'):
        ins = [dict(n=i.name, m=i.master, x=i.x, y=i.y, w=i.w, h=i.h, o=i.orient) for i in m['insts']]
        json.dump(dict(die=m['die'], rec=rec, insts=ins), open(os.environ['OT_SPLIT_DUMP'], 'w'), default=str)
    m['split_compute'] = rec
    return rec
