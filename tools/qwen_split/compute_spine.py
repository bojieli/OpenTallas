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
import collections
import json
import os

CH = 86.4                       # relay channel between spine slots (two 30-um relay rows + spacing)
CHE = 108.0                     # C7: spine EDGE channels (beside the tile fields): the E head root's last relay (1,567 b,
                                # ~80-um frame) must stand within 490 um of xcol_24's W face across tile column 24
PORT_WH = (float(os.environ.get('OT_SPLIT_PORT_W', '1036.8')), 2462.4)      # qfd_port_tiles_* slot: 2.553 mm2 >= the measured 2.536 mm2 need (blockers G7)
RES_WH = (777.6, 518.4)
LANES_WH = (881.28, 1131.84)
SU_WH = (3240.0, 3672.0)        # qfd_sp_su64_sfu: 64-lane component 4.84 mm2 children + reducer + glue (Codex 3434 x 2570 bbox)
VM_WH = (4708.8, 2203.2)        # TRIMMED central VM (owner 08:20 PT 10-14: distributed x slices adopted; banks / SU ports / row reads only, M7 cap, no wall)
CTLM_WH = (777.6, 1814.4)
UP4_WH = (345.6, 388.8)
CLKRX_WH = (412.488, 412.488)
# ---- C12 (compute lead r3, 2026-10-14 ~19:00, coordinator question B: relay stages on the token path 12 % of tok/s):
# the per-ME-op loop tt_ctlm -> tap -> head roots -> head row -> corridors -> tiles -> tree -> block words -> slabs ->
# res_ser -> VM -> tt_ctlm crossed 217 times a token, and C8 placed the whole controller stack (tap, tt_ctlm, seq_su,
# VM) 7 mm N of the head row (tap -> W root 25 stages, tt_ib 13, ctlm <-> seq_su 19 / 20, band 0 <-> top 31-38).
# STACK 'seam' puts the SU / VM seam just above the head row: SU above, VM below, preserving the existing 24-nm
# registered SU / VM abutment and zero added transport edges. Die M8/M9 over the M7-capped VM carry the two
# head-root words W / E at the head row; the x tap sits at the seam E of the constant group, tt_ctlm / tt_up4 / seq_su
# stacked above it in one E column (tt_ib, me_snap / su_snap / me_start adjacent), clock receiver under the VM; the
# band slab stacks that would straddle the head-row channel move below it (res_ser_1 lands beside the VM).
STACK = os.environ.get('OT_SPLIT_STACK', 'n')    # 'n' = C4..C11 (stack under the N-edge link), 'seam' = C12
HROW = 216.0                    # head-row channel half height kept free of slab stacks (1,567-b root relay 80 um + 2 channels)
# ---- v1.2 (compute lead r4, 2026-10-14 21:3x): strap ties from real tie cells.  The die top holds only hard masters, so
# a strap written as a netlist literal becomes an OpenROAD one_ / zero_ POWER net with no tie cell and no std-cell rail
# (C13 / C15 OT_PA FAIL DRT-0305).  A master listed here has two 1-b OUTPUT ports tie_hi / tie_lo driven by TIEHI /
# TIELO inside (owner hierarchy rule: glue into tiles); the die wires every strap bit of the instance to its OWN tie_hi /
# tie_lo, pins beside the strap input on the same face.  OT_SPLIT_TIE_SELF = comma list of masters ('all' = every strap
# master); a master whose RTL lacks the ports must stay out (port-bind reports the literal straps until it lands).
TIE_STRAP_MASTERS = ('qfd_tile_nk', 'qfd_tile_nl', 'qfd_xcst_n', 'qfd_xcst_s', 'qfd_xcol_e', 'qfd_xcol_w',
                     'qfd_su_cbuf_g', 'qfd_crom_g', 'qfd_sp_band_lanes')
# the contract straps (results/arch/qwen_split_compute_1014/straps.json): ONLY these are tie-driven; chain-terminus ties
# (tap_r, a_r, b_r, w_r, e_r, fault_i) stay literals so the port-bind keeps reporting them as INPUT_TIED defects
STRAP_PORTS = frozenset([('qfd_tile_nk', 'tile_id'), ('qfd_tile_nl', 'tile_id'), ('qfd_xcst_n', 'sidx'), ('qfd_xcst_s', 'sidx'),
                         ('qfd_xcol_e', 'tids'), ('qfd_xcol_w', 'tids'), ('qfd_xcol_e', 'fault_i'), ('qfd_xcol_w', 'fault_i'), ('qfd_su_cbuf_g', 'grp'), ('qfd_su_cbuf_g', 'f_lat'),
                         ('qfd_crom_g', 'crom_lb'), ('qfd_sp_band_lanes', 'b0'), ('qfd_sp_band_lanes', 'lnk'),
                         ('qfd_sp_band_lanes', 'tt')])
_ts = os.environ.get('OT_SPLIT_TIE_SELF', 'qfd_tile_nk,qfd_tile_nl,qfd_xcst_n,qfd_xcst_s,qfd_xcol_e,qfd_xcol_w').strip()   # tile RTL has tie_hi / tie_lo (q-tile r10)
TIE_SELF = frozenset(TIE_STRAP_MASTERS if _ts == 'all' else [s for s in _ts.split(',') if s])
assert TIE_SELF <= set(TIE_STRAP_MASTERS), f'OT_SPLIT_TIE_SELF: unknown masters {sorted(TIE_SELF - set(TIE_STRAP_MASTERS))}'


# ---- C4 (2026-10-14, compute-die lead r2): owner-adopted distributed x slices (HANDOFF 0aa, el1014-qwen-dvm-build.log)
DVM = os.environ.get('OT_SPLIT_DVM', '1') != '0'
XCOL_WH = (64.8, 1434.24)       # qfd_xcol_e/w: xhead + 8 x qfd_xs_leaf (two write chains N / S), in the column corridor,
                                # centred on the head row; 604.8 N + 103.68 head + 604.8 S (contract v1 slice slots)
TAP_SLOT_WH = (345.6, 345.6)    # reserved control-stack envelope remains fixed
TAP_WH = (216.0, 216.0)         # qfd_xs_tap at the VM N face, E of the constant group (SU write tap + attention write tap)
XCOR_D = 516                    # corridor word {go 1, ib 379, xl 128, tag 8} (qfd_xcst / qfd_xcol n_d / s_d)
XHEAD_D = 1 + 379 + 73 + 1114                  # head-row word {go 1, ib 379, desc 73, fill 1114} (qfd_xcol w_d / e_d)
TAP_SW, TAP_AW, TAP_PF, TAP_GI = 1 + 24 + 64 + 2048, 1 + 24 + 16 + 512, 72, 380


# C5: masters whose hardened children each take their own die clock entry (delivered at phi - R of that child):
# die ports ck0 .. ck<n-1> = RTL clock port bits ck[n-1:0] (qfd_tt_up4: 5 = 4 leaves + cluster pin flops, r5 10-14;
# qfd_xcol_e/w: 9 = xhead + 8 leaves, ot_qfd_xslice_slots.sv)
CHILD_CK = {'qfd_tt_up4': ['ck_pin', 'ck_l0', 'ck_l1', 'ck_l2', 'ck_l3'],     # rtl/physical/ot_qwen_tt_up4_cluster.sv (+define OT_QFD_UP4_CK_ENTRIES)
            'qfd_xcol_e': [f'ck{k}' for k in range(9)], 'qfd_xcol_w': [f'ck{k}' for k in range(9)],
            'qfd_sp_vector_memory': ['ck'] + [f'ck_r{r}_{k}' for r in range(8) for k in range(56)]
                                     + [f'ck_r{r}_{k}' for r in (3, 4, 5, 6) for k in range(56, 64)]
                                     + [f'ck_r7_{k}' for k in range(56, 63)],
            'qfd_io_collective': ['clk'] + [f'clk_colr{k}' for k in range(4)] + [f'clk_ecol{k}' for k in range(5)]
                                + [f'clk_pfold{k}' for k in range(4)] + [f'clk_efold{k}' for k in range(4)],
            'qfd_d2d_rom': ['ck', 'mux_ck'] + [f'llr_ck{k}' for k in range(5)],
            'qfd_tile_nk': ['ck'] + [f'ck_rp{k}' for k in range(5)] + [f'ck_lsl{k}' for k in range(8)] + ['ck_node'],
            'qfd_tile_nl': ['ck'] + [f'ck_rp{k}' for k in range(5)] + [f'ck_lsl{k}' for k in range(8)],
            'qfd_sp_band_lanes': ['ck'] + [f'ck_l{k}' for k in range(16)]}
# v1.3 (compute lead r4): the static slab masters (rtl/qwen_split/qfd_port_tiles.sv @10c74d529) take 49 entries each
_SLAB_CK = (['ck'] + [f'ck_bw{k}' for k in range(8)] + [f'ck_pair{k}' for k in range(4)] + [f'ck_col{k}' for k in range(16)]
            + [f'ck_mul{k}' for k in range(16)] + [f'ck_group{k}' for k in range(4)])
for _b in range(3):
    CHILD_CK[f'qfd_port_tiles_{_b}'] = CHILD_CK[f'qfd_port_tiles_{_b}_f1'] = list(_SLAB_CK)



# ---- C10 (compute lead r3): the link words at their REAL RTL widths (die-bus audit, link rows; owner no-stub rule):
# qfd_d2d_rom = ot_qfd_split_romlink + ot_qkvd_d2d_llr (rtl/qwen_split/qfd_link_slots.sv).  Bundles pack LSB first in
# the listed order, the same order at both ends (the SU / VM wrappers take the same packing).
LINK_BITS = dict(x3=524, attn_ret=520, d2d_fdi=1169, o4_kvd=44, rs_0=551, rs_1=551, rs_2=551,
                 # C11 (lead answers 17:5x to the compute elements): the RTL is the width truth -- tt_ctlm c 341 / f 104,
                 # band_lanes lc 26 = {tv_e 13, sel_e 13}; SU issue si 482 (+ cb_stage 6, travels with each crom request);
                 # SU status sd 108 (no weight-ROM fields: the split SU issues no WROM reads)
                 tt_c0=341, tt_c1=341, tt_c2=341, tt_f0=104, tt_f1=104, tt_f2=104, tt_lc0=26, tt_lc1=26, tt_lc2=26,
                 o4_su_iss=482, o4_su_st=108)
LINK_SPLIT = {
    'qfd_d2d_rom': dict(
        x3=[('x3_d', 512), ('x3_tag', 11), ('x3_v', 1)],
        ar=[('ar_d', 519), ('ar_v', 1)],
        ea=[('ea_addr', 24), ('ea_kind', 1), ('ea_v', 1)],
        ecr=[('ea_cr', 1)],
        eq=[('eq_d', 512), ('eq_v', 1)],
        fdi=[('fdi_tx_up', 1), ('fdi_tx_v', 1), ('fdi_tx_flit', 583), ('fdi_rx_v', 1), ('fdi_rx_flit', 583)]),
    # the PHY hard macro (allowed behavioural model, its LEF ports): same FDI bit order as the adapter's bundle
    'ot_qkvd_ucie_x64_phy': dict(
        fdi=[('tx_up', 1), ('tx_v', 1), ('tx_flit', 583), ('rx_v', 1), ('rx_flit', 583)]),
}
LINK_CREDITS = [('x3_cr', 'spine_local', 1, [('d2d_rom', 'x3_cr'), ('sp_su64_sfu', 'q_cr')]),
                ('ar_cr', 'spine_local', 1, [('sp_vector_memory', 'ar_cr'), ('d2d_rom', 'ar_cr')])]


def _link_words(m, rec):
    if os.environ.get('OT_SPLIT_LINK_WORDS', '1') == '0':
        return
    have = {b for b, _, _, _ in m['buses']}
    m['buses'] = [(b, c, 2050 if b.startswith('pfrag_') else LINK_BITS.get(b, n), e) for b, c, n, e in m['buses']] + [x for x in LINK_CREDITS if x[0] not in have]
    split = m.setdefault('port_split', {})
    for mst, d in LINK_SPLIT.items():
        split.setdefault(mst, {}).update({k: list(q) for k, q in d.items()})
    rec['link_words'] = dict(bits=LINK_BITS, credits=[x[0] for x in LINK_CREDITS], rtl='rtl/qwen_split/qfd_link_slots.sv')
    # C11: band lanes (rtl/physical/ot_qwen_band_lanes_slots.sv): reset from the spine domain; straps b0 (band 0) and
    # lnk[5:0] (relay stages on the band <-> tree-top links: written by the netlist writer from the build's stage count,
    # as the cbuf f_lat); tt (the tree-top word) reaches band 0 only, bands 1 / 2 take it as the strap-gated 0 the RTL
    # contract names (b0 = 0 ignores it)
    bands = sorted(i.name for i in m['insts'] if i.master == 'qfd_sp_band_lanes')
    nb = []
    for b, c, n, e in m['buses']:
        if b == 'rst_spine' or any(i == 'sp_res_ser_0' and p == 'rst_n' for i, p in e) and c == 'reset':
            e = list(e) + [(x, 'rst_n') for x in bands + ['sp_su64_sfu', 'sp_vector_memory'] if (x, 'rst_n') not in e]
        nb.append((b, c, n, e))
    # Real full-address sequencer row service; old 8-bit shells cannot address
    # the native VM rows (e.g. Q at 13696 and attention return at 50672).
    nb = [(b, c, 21 if any(i == 'seq_su' and p == 'vrd' for i, p in e) else
                  533 if any(i == 'seq_su' and p == 'vwr' for i, p in e) else n, e)
          for b, c, n, e in nb]
    m['buses'] = nb
    ties = m.setdefault('ties', [])
    have_tt = {i for b, c, n, e in m['buses'] for i, p in e if p == 'tt'}
    for x in bands:
        k = int(x.rsplit('_', 1)[1])
        ties.append((x, 'b0', 1, 1 if k == 0 else 0))
        ties.append((x, 'lnk', 6, 0))                  # value set by the netlist writer (stage count)
        if x not in have_tt:
            ties.append((x, 'tt', 1538, 0))


def _pair_mirror_hs(m, keep_rows=(7, 8)):
    """PM-H-S (GEO-Q 2026-10-15, coordinator ADOPT; results/arch/qwen_split_compute_1014/system_geometry/pair_mirror):
    each column pair (2k, 2k+1) of each 24-column half becomes [64.776 | even tile MY | 16.440 | odd tile R0 | 64.800]:
    the even tile's W-face tree words face the odd tile's across the inner channel, each station abuts its own tile's
    tap face (even: W side, MY, -30 nm so its M3 ck / rst_n sit on the die M3 track).  Head rows 7 / 8 (and the head-row
    DVM columns) keep the uniform pitch.  Same pitch, area, masters, rows; positions only."""
    TW, PITCH, GAPL, INNER = 449.28, 522.288, 64.776, 16.44
    tiles = [i for i in m['insts'] if i.master in ('qfd_tile_nk', 'qfd_tile_nl')]
    xs = sorted({round(i.x, 4) for i in tiles})
    if len(xs) != 48:
        raise ValueError(f'PM-H-S expects 48 tile columns, found {len(xs)}')
    newx = {}
    for half in (xs[:24], xs[24:]):
        for k in range(12):
            L, R = half[2 * k], half[2 * k + 1]
            if abs(R - L - PITCH) > 1e-3:
                raise ValueError(f'PM-H-S: column pair {L}/{R} not at the {PITCH} pitch')
            ex = round(L + GAPL, 4)
            ox = round(ex + TW + INNER, 4)
            newx[L] = (ex, 'MY', 'L')
            newx[R] = (ox, 'R0', 'R')
    row = lambda n: int(n.split('_')[2])
    moved_t = moved_s = 0
    for i in tiles:
        if row(i.name) in keep_rows:
            continue
        if i.orient != 'R0':
            raise ValueError(f'PM-H-S expects R0 tiles, {i.name} is {i.orient}')
        i.x, i.orient, _ = newx[round(i.x, 4)]
        moved_t += 1
    colmap = {round(x + TW, 4): x for x in xs}
    for i in m['insts']:
        if i.master not in ('qfd_xcst_s', 'qfd_xcst_n') or row(i.name) in keep_rows:
            continue
        tx = colmap[round(i.x, 4)]
        nx, o, side = newx[tx]
        if side == 'L':
            i.x, i.orient = round(nx - i.w - 0.030, 4), 'MY'
        else:
            i.x = round(nx + TW, 4)
        moved_s += 1
    # relay corridor lanes (the relay planner's per-column station lane): even columns W of the MY tile (64.776),
    # odd columns E of the R0 tile (64.800); head rows 7 / 8 keep the old station x (their hop costs the +1 stage)
    lanes = []
    for x in xs:
        nx, o, side = newx[x]
        lanes.append((round(nx - GAPL, 4), GAPL) if side == 'L' else (round(nx + TW, 4), 64.8))
    m['corridor_lanes'] = lanes
    return dict(scheme='PM-H-S', kept_rows=list(keep_rows), corridor_lanes_um=[64.776, 64.8], inner_um=INNER, gapL_um=GAPL, gapR_um=64.8,
                my_station_shift_nm=-30, mirrored_tiles=sum(1 for i in tiles if i.orient == 'MY'),
                moved_tiles=moved_t, moved_stations=moved_s, source='GEO-Q pmh_legality.py (main 48fab3baf)')


def _child_clocks(m, rec):
    n_of = {i.name: CHILD_CK[i.master] for i in m['insts'] if i.master in CHILD_CK}
    nb = []
    for b, c, n, e in m['buses']:
        if c == 'clock_trunk':
            # The collective is digital RTL with clock inputs, never a PLL.
            # All delivered IO roots originate at the actual forwarded-clock
            # receiver. Their frequency/phase qualification remains required.
            e = [('clk_rx', p) if i == 'io_collective' and p.startswith('pll_') else (i, p) for i, p in e]
            e2 = []
            for i, p in e:
                if i in n_of and p in ('ck', 'clk'):
                    e2 += [(i, q) for q in n_of[i]]
                elif i in n_of and p == 'ckx' and i == 'sp_vector_memory':
                    continue  # obsolete common transport root; native child clocks above
                else:
                    e2.append((i, p))
            e = e2
        nb.append((b, c, n, e))
    m['buses'] = nb
    rec['child_clocks'] = {k: list(v) for k, v in CHILD_CK.items()}


def _slab_links(m, rec):
    """v1.3: the static slab pair of each band (qfd_port_tiles_<b> W half, _f1 E half, RTL 10c74d529) exchange five
    registered words: W tc_e 341 -> f1 tc, W tye 2,048 -> f1 ty, f1 rq 2,213 -> W rqe, f1 am 52 -> W ame (f1 cw0 2,050
    -> W cf1 is the existing pfrag bus).  No ready / credit: fixed stages, priced by the compiler."""
    have = {b_ for b_, *_ in m['buses']}
    nb = []
    for b in range(3):
        w, e = f'sp_port_tiles_{b}', f'sp_port_tiles_{b}_f1'
        for name, cls, n, src, dst in ((f'slab_tc_{b}', 'tree_spine', 341, (w, 'tc_e'), (e, 'tc')),
                                       (f'slab_ty_{b}', 'tree_spine', 2048, (w, 'tye'), (e, 'ty')),
                                       (f'slab_rq_{b}', 'tree_spine', 2213, (e, 'rq'), (w, 'rqe')),
                                       (f'slab_am_{b}', 'tree_spine', 52, (e, 'am'), (w, 'ame'))):
            if name not in have:
                nb.append((name, cls, n, [src, dst]))
    m['buses'] += nb
    rec['slab_links'] = [x[0] for x in nb]


def morton(c, r):
    z = 0
    for i in range(4):
        z |= ((c >> i) & 1) << (2 * i) | ((r >> i) & 1) << (2 * i + 1)
    return z


def ref_tile_id(c, r, rows=16, bc=4, br=4):
    """the reference ot_qwen_me_array_w12 tile index of die tile (c, r): the die's split tree pairs tiles in
    morton order inside each 4 x 4 block (host_level: node at level LT+k on tile t, t % 2^k == 2^(k-1) - 1) and block b
    = (c // 4) * (rows // 4) + r // 4 is top word b; so t = 16 b + morton(c % 4, r % 4).  t sets the tile's output rows
    (i_gbase = t * TG), its ROM image and its x chunk (TG * t mod S): ONE map for tree, ROM content and x slices."""
    return bc * br * ((c // bc) * (rows // br) + r // br) + morton(c % bc, r % br)


# C6 (die-bus audit vs ot_qwen_me_array_w12): tree words carry the tile's valid (t_vout -> n_va: the reference node
# takes valid from leg a) and the fault (reference fab_fault = OR of every tile fault: the die ORs it up the tree, so
# every block word brings its block's fault to the slab): every tree word (t_out / n_a / n_b / n_y, one width for the
# one tile master) and every block word = {fault, valid, 512}; the node may check va == vb (an alignment check: a
# misaligned leg then faults instead of summing wrong data)
TREE_A, TREE_B, BWORD = 514, 514, 514


def _tree_widths(m, rec):
    import re as _re
    nb, n_ = [], collections.Counter()
    for b, c, n, e in m['buses']:
        if c == 'tree_block' and _re.fullmatch(r'tree_\d+_\d_\d+a', b) and n == 512:
            n = TREE_A; n_['a'] += 1
        elif c == 'tree_block' and _re.fullmatch(r'tree_\d+_\d_\d+b', b) and n == 512:
            n = TREE_B; n_['b'] += 1
        elif _re.fullmatch(r'bword_\d+', b) and n == 512:
            n = BWORD; n_['bword'] += 1
        nb.append((b, c, n, e))
    m['buses'] = nb
    rec['tree_widths'] = dict(leg_a=TREE_A, leg_b=TREE_B, bword=BWORD, buses=dict(n_))


def _dvm(v, m, put, rec, vm, su, xt, ty=None):
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
    # The density-qualified1434.24um stack is taller than the old1313.28
    # envelope. Move only its nearest corridor stations out into the existing
    # tile-row space; shrinking the leaves or overlapping them is not legal.
    head_by_column={int(h.name.split('_')[-1]):h for h in heads}
    station_moves=[]
    for station in m['insts']:
        if station.kind!='station':continue
        c=int(station.name.split('_')[1]);h=head_by_column[c]
        if station.y<h.y+h.h and h.y<station.y+station.h:
            old_y=station.y
            station.y=(_snap(v,h.y+h.h+4.32,v.GY) if station.y+station.h/2>h.y+h.h/2
                       else _snap(v,h.y-4.32-station.h,v.GY))
            station_moves.append(dict(instance=station.name,old_y=old_y,new_y=station.y,dy_um=round(station.y-old_y,4)))
    rec['dvm_station_clearance_moves']=station_moves
    rows = {}
    for i in m['insts']:
        if i.kind == 'station':
            i.master = 'qfd_xcst_n' if i.y >= mid else 'qfd_xcst_s'
            c, r = (int(q) for q in i.name.split('_')[1:3])
            rows.setdefault(c, []).append(r)
    nr = max(max(q) for q in rows.values()) + 1
    # Static DVM has no ready ports or ready terminus ties.
    rec['dvm_termini'] = 0
    for i in m['insts']:
        if i.kind == 'station':
            c, r = (int(q) for q in i.name.split('_')[1:3])
            ties.append((i.name, 'sidx', 3, (r - nr // 2) if r >= nr // 2 else (nr // 2 - 1 - r)))
        elif i.kind == 'tile' and i.name.startswith('t_'):
            c, r = (int(q) for q in i.name.split('_')[1:3])
            ties.append((i.name, 'tile_id', 16, ref_tile_id(c, r, nr)))
    # C6 (die-bus audit): the head computes its 16 tiles' x windows from a per-row id table (the reference ids of a
    # column are not affine in the row: 16 x block + morton), N stations 0..7 outward then S 8..15 outward
    for c, h in enumerate(heads):
        order = list(range(nr // 2, nr)) + list(range(nr // 2 - 1, -1, -1))
        val = 0
        for k, r in enumerate(order):
            val |= ref_tile_id(c, r, nr) << (16 * k)
        ties.append((h.name, 'tids', 16 * nr, val))
    tap = v.Inst('xs_tap', 'qfd_xs_tap', 0.0, 0.0, TAP_WH[0], TAP_WH[1], kind='spine', region='hub',
                 domain=vm.domain)
    m['insts'].append(tap)
    tap.x, tap.y = _snap(v, xt, v.GX), _snap(v, su.y if ty is None else ty, v.GY)
    rec['slots']['xs_tap'] = [tap.x, tap.y, round(tap.w, 3), round(tap.h, 3)]
    roots = {}
    nb = []
    for b, c, n, e in m['buses']:
        if c in ('corridor', 'head_chain') and n == 1 and any(p.endswith('_r') for _, p in e):
            continue  # obsolete per-hop ready; compiler assigns every on-chip slot
        if c == 'corridor':
            n = XCOR_D if n > 1 else n
        elif c == 'head_chain':
            e = [(('xs_tap', {'xw': 'hw', 'xe': 'he'}[p.rsplit('_', 1)[0]] + '_' + p.rsplit('_', 1)[1])
                  if i == 'sp_vector_memory' else (i, p)) for i, p in e]
            n = XHEAD_D if n > 1 else n
            if any(i == 'xs_tap' for i, p in e):
                roots[b] = e
        elif b == 'rst_spine':
            e = list(e) + [('xs_tap', 'rst_n')]
        elif c == 'clock_trunk' and ('sp_vector_memory', 'ck') in e:
            e = list(e) + [('xs_tap', 'ck')]
        elif b == 'tt_ib':
            e = [(i, p) if i != 'sp_vector_memory' else ('xs_tap', 'gi') for i, p in e]
        nb.append((b, c, n, e))
    nb += [('xs_sw', 'spine_local', TAP_SW, [('sp_su64_sfu', 'xsw'), ('xs_tap', 'sw')]),
           ('xs_aw', 'spine_local', TAP_AW, [('sp_vector_memory', 'xaw'), ('xs_tap', 'aw')]),
           ('xs_pf', 'sequencer', TAP_PF, [('tt_ctlm', 'xpf'), ('xs_tap', 'xpf')]),
           ('xs_fault', 'spine_local', 1, [('xs_tap', 'fault'), ('tt_ctlm', 'xflt')])]
    # Head words broadcast outward; sticky faults return inward on real RTL
    # ports, so no column can silently drop a storage/read ownership fault.
    for side in (heads[:half], list(reversed(heads[half:]))):
        ties.append((side[0].name, 'fault_i', 1, 0))  # declared outer chain terminus
        for outer, inner in zip(side, side[1:]):
            nb.append((f'xfault_{outer.name}', 'head_chain', 1,
                       [(outer.name, 'fault'), (inner.name, 'fault_i')]))
    nb += [('xfault_w', 'head_chain', 1, [(heads[half - 1].name, 'fault'), ('xs_tap', 'hw_f')]),
           ('xfault_e', 'head_chain', 1, [(heads[half].name, 'fault'), ('xs_tap', 'he_f')])]
    m['buses'] = nb
    rec['dvm'] = dict(xcol=len(heads), xcst=sum(1 for i in m['insts'] if i.kind == 'station'), tap=list(rec['slots']['xs_tap']),
                      xcol_wh=list(XCOL_WH), corridor_bits=XCOR_D, head_bits=XHEAD_D, roots=sorted(roots),
                      straps=dict(sidx='station index from the head outward',
                                  tids='16 x 16-b reference tile ids of the column, N stations 0..7 then S 8..15',
                                  tile_id='16 * block + morton(c % 4, r % 4) (ref_tile_id)'))


def _snap(v, x, g):
    return round(v.dn(x, g), 4)


def _place_su_vm(put, cx, su_y, xe=None):
    """Keep the r21v registered SU/VM seam at its actual abutted pin faces.

    The VM is wider than the SU. Leave one channel of positive face offset
    inside the VM span; the E-side constant group still fits in that span.
    put() snaps both origins and subtracts SHAVE from their outlines, leaving
    the existing 24-nm contact gap and no additional RTL transport edge.
    """
    vm_x = cx - VM_WH[0] / 2 if STACK != 'seamw' else xe
    # C16 'seamw' (owner 21:35: communicating blocks adjacent): the tree-top column (tap / tt_ctlm / tt_up4) moves W of
    # the SU, beside the W slab column it talks to (band_lanes tt_ty / pword / tt_lc, port_tiles tt_c / tt_f); the VM
    # aligns to the E sub-area's W edge and the SU shifts E by one control column (still inside the VM N face).
    su = put('sp_su64_sfu', vm_x + (CH if STACK != 'seamw' else CTLM_WH[0] + CH), su_y, SU_WH)
    vm = put('sp_vector_memory', vm_x, su.y - VM_WH[1], VM_WH)
    return su, vm


def place(v, m, G):
    # C7: die timing by construction on the split die too.  The tp8b reach gate (pin-to-pin hop gate, load-aware span
    # search, registered reset tree) was switched on only inside the merged die's KV surgery (_tp8b_kv), which the
    # split compute die skips: C1..C6 ran WITHOUT it (C3: no reset tree, rst_field 52 mm unrelayed, no p2p record)
    v.RELAY_REACH_GATE = True
    by = {i.name: i for i in m['insts']}
    tiles = [i for i in m['insts'] if i.master == 'qfd_tile_nk']
    xs = sorted({round(i.x, 4) for i in tiles})
    ys = sorted({round(i.y, 4) for i in tiles})
    th = tiles[0].h
    head_y = (ys[7] + th + ys[8]) / 2
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
            shave = 0 if name.startswith('sp_band_lanes_') else v.SHAVE
            i.w, i.h = wh[0] - shave, wh[1] - shave
        i.x, i.y = _snap(v, x, v.GX), _snap(v, y, v.GY)
        rec['slots'][name] = [i.x, i.y, round(i.w, 3), round(i.h, 3)]
        return i

    # ---- W column: the band's W-half slab stack (C4: band_lanes / port_tiles / res_ser CENTRED on the port column so
    # the abutted tw / ty / rq faces stand face to face; v1-a left them off-centre and the 8,192-b tw / ty pair read as a
    # 1.485 horizontal cut).  E column (C4, as the merged tp8b): the band's E-half slab port_tiles_<b>_f1 on the spine's E
    # edge at the band centroid, so the 24 E-field block words land without crossing the VM / SU sub-area (v1-a put
    # _f1 in the W sub-area: 24 x 512 b across the spine); only the band's one 512-b pfrag word crosses.
    xa = x0 + CHE
    xf = x1 - CHE - PORT_WH[0]
    # v1.3 (owner 21:35 adjacency): the slab pair of a band exchanges 6,704 b (tc_e, tye, rq, am, cw0, RTL 10c74d529)
    # vs 8 x 514 = 4,112 b of E-field block words; with _f1 abutted E of its W half in the W column only the block words
    # cross the spine (C16 with _f1 on the E edge: worst cut 1.551).  The E slab column disappears.
    F1W = STACK == 'seamw' and os.environ.get('OT_SPLIT_F1_WEST', '1') != '0'
    if F1W:
        xf = x1 - CHE + CH
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
        if STACK in ('seam', 'seamw') and y0 < head_y + HROW and y0 + gh > head_y - HROW:
            y0 = head_y - HROW - gh
            if y0 < lo:
                raise SystemExit('split compute seam: slab stack cannot clear the head-row channel')
        if b == 0 and STACK == 'seamw' and os.environ.get('OT_SPLIT_BAND0_FLIP', '0') != '0':
            # C17: band 0's stack mirrored (MX): band_lanes on top, nearest the tree top (pword_0 / tt_ty / tt_lc0),
            # res_ser at the bottom; the abutted tw / ty and rs faces keep facing each other under the mirror
            r_ = put(f'sp_res_ser_{b}', xa + dr, y0, RES_WH)
            p_ = put(f'sp_port_tiles_{b}', xa, y0 + RES_WH[1] + 4.32, PORT_WH)
            l_ = put(f'sp_band_lanes_{b}', xa + dl, y0 + RES_WH[1] + PORT_WH[1] + 8.64, LANES_WH)
            r_.orient = p_.orient = l_.orient = 'MX'
            rec['band0_flip'] = True
        else:
            put(f'sp_band_lanes_{b}', xa + dl, y0, LANES_WH)
            put(f'sp_port_tiles_{b}', xa, y0 + LANES_WH[1] + 4.32, PORT_WH)
            put(f'sp_res_ser_{b}', xa + dr, y0 + LANES_WH[1] + PORT_WH[1] + 8.64, RES_WH)
        if F1W:
            pt_ = by[f'sp_port_tiles_{b}']
            put(f'sp_port_tiles_{b}_f1', pt_.x + PORT_WH[0] + 4.32, pt_.y, PORT_WH)
            rec.setdefault('band_centroid_y', []).append(round(cents[b], 1))
            lo = y0 + gh + CH
            continue
        yf = max(lo_f, cents[b] - PORT_WH[1] / 2)
        yf = min(yf, top - PORT_WH[1])
        if STACK in ('seam', 'seamw') and yf < head_y + HROW and yf + PORT_WH[1] > head_y - HROW:
            yf = head_y - HROW - PORT_WH[1]
            if yf < lo_f:
                raise SystemExit('split compute seam: east slab cannot clear the head-row channel')
        put(f'sp_port_tiles_{b}_f1', xf, yf, PORT_WH)
        rec.setdefault('band_centroid_y', []).append(round(cents[b], 1))
        lo = y0 + gh + CH
        lo_f = yf + PORT_WH[1] + CH
    xw_end = xa + PORT_WH[0] + CH + ((PORT_WH[0] + 4.32) if F1W else 0.0)
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
    # C9 (compute lead r3): both link masters MIRRORED about x (MX).  The PHY abstract has its FDI / clk / rst on the N
    # face and the adapter its FDI on the S face: at R0 under a PHY on the N die edge the FDI faced the die edge and the
    # 1,099-b FDI took 4 relays (C3 d2d_fdi 5 stages: the FDI must abut, no logic between macro pins and adapter flops),
    # and the adapter's SU / VM / sequencer faces (x3, ea, eq, ar, dc, dh) faced the PHY (x3 4 stages, dh 13).  MX puts
    # the FDI faces together across the 4.32-um gap and the adapter's word faces toward the SU below.
    if os.environ.get('OT_SPLIT_LINK_MX', '1') != '0':
        ph.orient = ad.orient = 'MX'
        rec['link_orient'] = 'MX'
    # v1.3 (compute lead r4, elements r11): the CLOSED + native-PASS static x3 mux (kit qfd_x3_mux_nativer, RTL
    # ot_qfd_x3_mux_native, 129.6 x 129.6) between the SU q word and the adapter's x3 word, right under the adapter's
    # word face.  Its kvn / slot inputs have no die producer yet (Q-control: KVN sender + compiler slot issuer): left
    # unconnected so the port-bind names them, never tied.
    if os.environ.get('OT_SPLIT_X3MUX', '1') != '0':
        mx = v.Inst('x3_mux', 'ot_qfd_x3_mux_native', 0.0, 0.0, 129.6, 129.6, kind='spine', region='hub', domain=ad.domain)
        m['insts'].append(mx)
        by['x3_mux'] = mx
        put('x3_mux', ad.x + ad.w / 2 - 64.8, ad.y - CH - 129.6)
        nb_ = []
        for b_, c_, n_, e_ in m['buses']:
            if b_ == 'x3':
                nb_.append((b_, c_, n_, [x for x in e_ if x[0] != 'd2d_rom'] + [('x3_mux', 'q')]))
                nb_.append(('x3m', c_, n_, [('x3_mux', 'x3'), ('d2d_rom', 'x3')]))
                continue
            if c_ == 'clock_trunk' and ('d2d_rom', 'ck') in [tuple(x) for x in e_]:
                e_ = list(e_) + [('x3_mux', 'ck')]
            if b_ == 'rst_spine':
                e_ = list(e_) + [('x3_mux', 'rst_n')]
            nb_.append((b_, c_, n_, e_))
        m['buses'] = nb_
        rec['x3_mux'] = list(rec['slots']['x3_mux'])
    put('rs_bump', ph.x - 4.32 - by['rs_bump'].w - 4.32, ph.y - by['rs_bump'].h / 2)
    put('ckb_rom', ph.x - 4.32 - by['ckb_rom'].w - 4.32, ph.y + 30.0)
    # SU slot below the link, constant group E of it
    su_y = head_y + HROW if STACK in ('seam', 'seamw') else ad.y - CH - SU_WH[1]
    su, vm = _place_su_vm(put, cx, su_y, xe)
    rec['stack'] = dict(mode=STACK, head_y=round(head_y, 3), su_vm_gap=round(su.y - vm.y - vm.h, 4))
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
    if gx + 2 * (cr[0].w + 4.32) > xf - CH + 1e-3 or (sq is not None and (sq.y < su.y - 1e-3 or gx + sq.w > xf - CH + 1e-3)):
        raise SystemExit(f'split compute spine: constant group does not fit E of the SU (gx {gx:.1f}, xf {xf:.1f})')
    # The VM was placed with the SU above: S(SU) and N(VM) are abutted,
    # matching the existing zero-relay registered seam and its latency.
    # tree top below the VM, clock receiver + reset leaf at the die centre
    xt = gx + max(2 * (cr[0].w + 4.32), sq.w if sq is not None else 0.0) + CH
    if STACK == 'seamw':
        # tap at the VM N face W end; tt_up4 right above it (its band words tt_ty / pword reach bands 0 and 2 from
        # the band-1 height), tt_ctlm above tt_up4 (tt_ib to the tap: one up4 height away)
        xt = su.x - CH - TAP_WH[0]             # tap against the SU's W face (xs_sw 2,137 b), as far E as the column allows
        u4 = put('tt_up4_0', vm.x, su.y + TAP_SLOT_WH[1] + CH, UP4_WH)
        ct = put('tt_ctlm', vm.x, u4.y + UP4_WH[1] + CH, CTLM_WH)
    elif STACK == 'seam':
        # The tap sits beside the SU, above the VM's abutted face. The controls form
        # one column above it rather than sending every ME command around the VM.
        ct = put('tt_ctlm', xf - CH - CTLM_WH[0], su.y + TAP_SLOT_WH[1] + CH, CTLM_WH)
        put('tt_up4_0', ct.x, ct.y + CTLM_WH[1] + CH, UP4_WH)
    else:
        ct = put('tt_ctlm', cx - CTLM_WH[0] - 2.16, vm.y - CH - CTLM_WH[1], CTLM_WH)
        put('tt_up4_0', ct.x + CTLM_WH[0] + 4.32, ct.y + CTLM_WH[1] - UP4_WH[1], UP4_WH)
    if DVM:
        _dvm(v, m, put, rec, vm, su, xt)
    ymid = (io_top + top) / 2
    ck_y = vm.y - CH - CLKRX_WH[1] if STACK in ('seam', 'seamw') else min(ymid - CLKRX_WH[1] / 2, ct.y - CH - CLKRX_WH[1])
    ck = put('clk_rx', cx - CLKRX_WH[0] / 2, ck_y)
    put('rstseq_rom', ck.x + ck.w + 4.32, ck.y)
    # ---- containment: every spine slot inside [x0, x1] x [io_top, top]
    bad = [n for n, (x, y, w, h) in rec['slots'].items() if x < x0 - 1e-3 or x + w > x1 + 1e-3 or y < io_top - 1e-3 or y + h > top + 1e-3]
    rec['outside_spine'] = bad
    if bad:
        raise SystemExit(f'split compute spine: slots outside the spine: {bad[:8]}')
    if os.environ.get('OT_SPLIT_TREE_HOSTS', 'baseline') == 'dp':
        from qwen_split.tree_hosts import apply as tree_hosts_apply
        rec['tree_hosts'] = tree_hosts_apply(v, m, pitch=490.0)
    # Actual hardened parent outlines have no legacy24-nm shape shave.
    for parent in m['insts']:
        if parent.master in ('qfd_tile_nk','qfd_tile_nl'):
            parent.w, parent.h = 449.28, 1442.88
        elif parent.master.startswith('qfd_port_tiles_'):
            parent.w, parent.h = PORT_WH
        elif parent.master=='qfd_sp_band_lanes':
            parent.w,parent.h=LANES_WH
    if os.environ.get('OT_SPLIT_PMHS', '1') != '0':
        rec['pair_mirror'] = _pair_mirror_hs(m)
    _slab_links(m, rec)
    from qwen_split.direct_up4 import apply as direct_up4
    rec['direct_up4'] = direct_up4(v, m)
    from qwen_split.native_control_contract import apply as native_control_apply
    rec['native_control_contract'] = native_control_apply(m)
    # static production collective + PHYs replace the credit IO row (OT_SPLIT_IO=legacy keeps the historical graph)
    if os.environ.get('OT_SPLIT_IO', 'static') == 'static':
        from qwen_split.native_static_io_bind import apply as static_io_bind
        rec['native_static_io_bind'] = static_io_bind(m)
    _child_clocks(m, rec)
    # GEO-Q 2026-10-15 (codex/geometry-qwen-1015 be0856ede), coordinator ADOPT: x3_mux R0 -> MY (x3m 512 b loses its
    # only relay), xs_tap R0 -> MX (head_23 1,567 b -1 relay; xfault_e 1 b +1).  Same rectangles; pins follow orient.
    if os.environ.get('OT_SPLIT_GEOQ_ORIENT', '1') != '0':
        flips = dict(x3_mux='MY', xs_tap='MX')
        for i in m['insts']:
            if i.name in flips:
                if i.orient != 'R0':
                    raise ValueError(f'GEO-Q orientation expects {i.name} R0, found {i.orient}')
                i.orient = flips[i.name]
        rec['geoq_orient'] = flips
    m['tie_self'] = sorted(TIE_SELF)
    rec['tie_self'] = sorted(TIE_SELF)
    # RTL is the truth (owner no-stub rule): the static DVM stations (rtl/qwen_sys/dvm_20261014 qfd_xcst_n/s) have no
    # tap_r ready input, so the die must not drive one; the qfd_d2d_rom RTL (rtl/qwen_split/qfd_link_slots.sv) has ONE
    # clock input, so its per-child clock entries wait for the Q-link-replay successor that actually has them.
    byi_ = {i.name: i.master for i in m['insts']}
    ties_ = m.setdefault('ties', [])
    ties_[:] = [t for t in ties_ if not (t[1] == 'tap_r' and byi_.get(t[0]) in ('qfd_xcst_n', 'qfd_xcst_s'))]
    nb_ = []
    for b, c, n, e in m['buses']:
        if c == 'clock_trunk':
            e = [(i, p) for i, p in e if not (byi_.get(i) == 'qfd_d2d_rom' and p != 'ck')]
            if any(byi_.get(i) == 'qfd_d2d_rom' for i, _ in e) and ('d2d_rom', 'ck') not in e:
                e = e + [('d2d_rom', 'ck')]
        nb_.append((b, c, n, e))
    m['buses'] = nb_
    rec['rtl_truth_fixes'] = dict(xcst_tap_r_untied=True, d2d_rom_clocks=['ck'])
    _link_words(m, rec)
    if os.environ.get('OT_SPLIT_TREE_VF', '1') != '0':
        _tree_widths(m, rec)
    # actual source join (tt / seq / su / vm / native59 / io / embed) replaces the historical spine words
    if 'native_static_io_bind' in m and os.environ.get('OT_SPLIT_NATIVE_GRAPH', '1') != '0':
        from qwen_split.native_graph_bind import apply as native_graph_apply
        rec['native_graph_bind'] = native_graph_apply(m)
        if os.environ.get('OT_SPLIT_STATIC_LINK', '1') != '0':
            from qwen_split.static_link_bind import apply as static_link_apply
            rec['static_link_bind'] = static_link_apply(m)
        # Q-ATTN r3 (2026-10-15): band result serializer = static train24 banks (legacy res_ser rq bit order was wrong)
        if os.environ.get('OT_SPLIT_RES_TRAIN', '1') != '0':
            from qwen_split.res_train_bind import apply as res_train_apply
            rec['res_train_bind'] = res_train_apply(m)
    # Source-pinned complete block placement; subsequent pins, relays, clocks and cuts use these homes.
    if os.environ.get('OT_SPLIT_HOMES'):
        from qwen_split.gfp_homes import apply as gfp_homes_apply
        rec['gfp_homes'] = gfp_homes_apply(m, os.environ['OT_SPLIT_HOMES'])
    if os.environ.get('OT_SPLIT_DUMP'):
        ins = [dict(n=i.name, m=i.master, x=i.x, y=i.y, w=i.w, h=i.h, o=i.orient) for i in m['insts']]
        bus = [dict(b=b_, c=c_, n=n_, e=[list(x) for x in e_]) for b_, c_, n_, e_ in m.get('buses', [])]
        json.dump(dict(die=m['die'], rec=rec, insts=ins, buses=bus), open(os.environ['OT_SPLIT_DUMP'], 'w'), default=str)
    if 'native_static_io_bind' not in m:
        from qwen_split.static_io_contract import build as static_io_build
        m['native_static_io_contract'] = static_io_build(next(i for i in m['insts'] if i.name == 'io_xfifo'))
        rec['native_static_io_contract'] = dict(children=12, roots=24, native_endpoint_binding='OPEN; legacy IO graph remains diagnostic')
    m['split_compute'] = rec
    return rec
