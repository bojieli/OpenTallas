#!/usr/bin/env python3
"""HBM-ARCH concept die plan generator (owner 10-23 ~20:45 HBM structural redesign; spec lanes/HBM-ARCH.md).

Organisation ("quad-tile array"):
  * ONE compute tile type, the QUAD TILE = 4 SM sub-tiles + the quadrant services that the as-built RTL already shares
    over 4 SMs (VM hub + 8 banks, SFU core/store, IDX score quarter, SU programme/qcore, COLL engine, hc ring).  The
    quadrant is the RTL's own locality domain (HBM-ARCH-RTL audit: SFU / IDX / sucore / VM hub / COLL cannot be cut per
    SM without new RTL), so the tile reuses the verified leaves unchanged.  4 tiles: NW (R0), NE (MY), SW (MX), SE (R180).
  * Inside the tile (NW frame, memory side up):  [SM0 SM1] / [SU0 SU1] / [service band, 2 rows] / [SU2 SU3] / [SM2 SM3].
    Each SM sub-tile = SM (hard, P=3 slot 8x2 lane tiles) + its SU slice in 4 lane-group partitions (with its 2 VM
    banks: SU co-located with its VM slice, COORD lesson 2) + a side column (svc: svg / vmks / xc; HBM transit; SerDes on
    the die edge).  The service band holds the hc ring (8 banks, 1 per partition), SFU core (3), IDX score (4), SFU
    programme store, and in its 4 side partitions the VM hub + x-load, hc qhub, SU programme + qcore, COLL engine.
  * Beachfront: HBM PHY N / S (one stack per tile pair) with the pseudo-channel controllers beside it in the PHY row
    (mc_a above SM0's side column, mc_b above SM1's); 4 SerDes in the quad tiles' die-edge side columns, the 5th + the
    host UCIe in the PHY rows -- every PHY on the shoreline.
  * Fabric: neighbour-only registered links.  Inter-tile traffic (VM ring, COLL rings, die trees) crosses one seam: the
    vertical seam column (W|E tiles) or the horizontal seam row (N|S tiles).  The die-level tree roots (tkm, IDX
    selector/link/ctl, hc_eng, argmax, SU programme root, host cp) sit in the ROOT tile at the seam-row centre, one seam
    hop from every quad tile (balanced trees, fixed cycles); IO is not in it.
Lanes = the as-built r18h5 census re-mapped to these partitions (canonical tile = max over the 4 served quadrants), one
bundle per (src partition, dst partition, kind); census coverage is checked by G0 against the same census.

    python3 gen_arch.py --variant A --out DIR      (A: P=3 SM, 16 SM, 2 stacks; Ac: current SM; B: 8 SM, 1 stack)
"""
import argparse, collections, heapq, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'tools', 'die_plan'))
import roles                                       # noqa: E402
import schema as S                                 # noqa: E402

G = 8.64
LAYERS = {L['name']: L for L in S.ASAP7_LAYERS}
OPPF = {'E': 'W', 'W': 'E', 'N': 'S', 'S': 'N'}
HL = ['M6', 'M4', 'M8']     # E/W faces (M8 third layer from the die budget: type face_layers)
VL = ['M7', 'M5', 'M9']     # N/S faces (M9 third layer)
PIN_UM = 6.2                # usable face pins / um (budget 6 / um, 2 layers, PG bands)
LANE_MAX = 3000
FT_UM = 5.28                # M8 / M9 ft budget per um: 0.6 (cut_avail) x usable tracks off the die PG stripes (xdie)
TFRAC = 0.88                 # share of the M8 / M9 ft budget the router may fill with transit (rest: face pins)
STATION_UM = 850.0          # ft station spacing (<= 0.9 x M8/M9 reach 1001)
REACH = 900.0               # 0.9 x measured M8/M9 reach (reach.py: M8 1001, M9 1013)


def u(v):
    return round(v * G, 4)


# --------------------------------------------------------------------------------------------- variants (lattice units)
VAR = {
    # SM slot: P=3 = 8 x 2 hnx_rp3lp3x lane tiles (630.72 x 2246.4 each, HNX-SM4P halves) = 584u x 520u
    'A': dict(smw=584, smh=520, nq=4, label='A: P=3 SM, 16 SM / 4 quad tiles, 2 HBM3E stacks'),
    # current-release SM ot_hbm_accel_smh_attn as 2x2 QSPLIT quarters (1944 x 1737 each) = 450u x 402u
    'Ac': dict(smw=450, smh=402, nq=4, label='Ac: current SM (QSPLIT 2x2), 16 SM / 4 quad tiles, 2 stacks'),
    'B': dict(smw=584, smh=520, nq=2, phyh=200, bandh=200, hubw=640, label='B: P=3 SM, 8 SM / 2 quad tiles, 1 HBM3E stack'),
    # B2 (COORD 10-23 22:xx review): HBM access (svg / vmks / ctl) in the hub; SFU core 2x2 W and IDX score 2x2 E of the
    # hub (each a full hub face), hc ring 4 + 4 at the band ends; narrower seam; 3-layer endpoint faces where the M8 / M9
    # budget allows; NE = MY mirror of NW (one master per tile partition); SerDes S1 on the S edge (vsN0)
    'B2': dict(smw=584, smh=520, nq=2, phyh=240, bandh=240, hubw=560, seamv=160, dsu=40, band2='ringE', sp=210, spuhub=True,
               mirror=True, l3=True, label='B2: P=3 SM, 8 SM / 2 mirrored quad tiles, 1 HBM3E stack'),
    # B2c (HBM-ARCH G1 self-review 10-24): B2 + a 17.28-um std-cell channel across each SM between its two half-tile rows
    # (32 hnx_rp3lp3h halves tile the SM slot with zero gap, so the clock tap drivers, the halves' reset landings --
    # rst_n sits on the row-seam faces -- and spare repeaters had no sites).  smh 520 -> 522 lattice.
    'B2c': dict(smw=584, smh=522, nq=2, phyh=240, bandh=240, hubw=560, seamv=160, dsu=40, band2='ringE', sp=210,
                spuhub=True, mirror=True, l3=True, sm_channel=2,
                label='B2c: P=3 SM, 8 SM / 2 mirrored quad tiles, 1 HBM3E stack, SM driver channel'),
    'B2j': dict(smw=668, smh=522, nq=2, phyh=240, bandh=240, hubw=560, seamv=160, dsu=40, band2='ringE', sp=210,
                spuhub=True, mirror=True, l3=True, sm_channel=2, sm_col_channel=12,
                label='B2j: 8 SM with 103.68um column broadcast channels and 17.28um clock/reset row channels'),
}
SIDE = 96          # side column width
SUH = 180          # SU band height (4 lane-group partitions per SM)
BANDH0 = 150       # service band row height (2 rows)
PHYH0 = 140        # PHY row (HBM3E PHY 8501.76 x 1183.68 + pseudo-channel controllers + IO)
PHYW = 984
SEAMH = 120        # horizontal seam row (root tile at its centre)
SEAMV0 = 200       # vertical seam column
HUBW0 = 440        # hub width (tile centre)
SP0 = 236          # tile spine column width (SM0 | spine | SM1)
DSU0 = 30          # SU-row spine widening (each side)
NSP = 3            # spine partitions per SM row
IOW = 110           # SerDes io partition width (die edge, band row 0)
NSIDE = 3          # side-column partitions per SM


def build(var):
    """Quad-tile array.  NW tile frame (x from the die W edge, y from the tile's seam edge; memory (PHY) side up):
        [SM0 | spT | SM1]      SM row under the PHY / controller row
        [SU0 | spU0| SU1]      SU strips: SU slice + its SFU / hc / cx slices (2 partitions per SM)
        [band | HUB | band]    2 rows: IDX score / SFU core / hc ring banks; HUB = VM slice (hub + 8 banks), x-load,
                               SU programme + qcore, COLL engine, IDX q, hc qhub -- at the tile centre, 1 hop from all 4 SUs
        [SU2 | spU1| SU3]
        [SM2 | spB | SM3]      seam side
    The spine (tile centre column) is the HBM / transit corridor; the vertical seam column and the seam row are the
    inter-tile corridors; the ROOT sits at the die centre in the seam row."""
    V = VAR[var]
    smw, smh, nq = V['smw'], V['smh'], V['nq']
    PHYH = V.get('phyh', PHYH0)
    BANDH = V.get('bandh', BANDH0)
    HUBW = V.get('hubw', HUBW0)
    SEAMV = V.get('seamv', SEAMV0)
    DSU = V.get('dsu', DSU0)
    SP = V.get('sp', SP0)
    QW = 2 * smw + SP
    QH = 2 * (smh + SUH) + 2 * BANDH
    W = 2 * QW + SEAMV
    H = 2 * PHYH + 2 * QH + SEAMH if nq == 4 else PHYH + QH
    parts = {}
    loc = []
    xs0, xs1 = smw, smw + SP
    for k, top in ((0, True), (1, True), (2, False), (3, False)):
        xm = 0 if k in (0, 2) else xs1
        ysm0 = QH - smh if top else 0
        ysu0 = ysm0 - SUH if top else smh
        loc.append((f'sm{k}', xm, ysm0, xm + smw, ysm0 + smh, 'sm'))
        # SU strip = SM width - DSU (the near half gives DSU to the spine's SU-row partition: wider hub <-> spine face)
        cw = smw // 2
        if k in (0, 2):
            xs = [(xm, xm + cw), (xm + cw, xm + smw - DSU)]
        else:
            xs = [(xm + DSU, xm + cw), (xm + cw, xm + smw)]
        for j, (xa, xb) in enumerate(xs):
            loc.append((f'su{k}{j}', xa, ysu0, xb, ysu0 + SUH, 'su'))
    for nm, y0, y1 in (('t', QH - smh, QH), ('b', 0, smh)):
        for j in range(NSP):
            ya = y0 + round(j * (y1 - y0) / NSP)
            yb = y1 if j == NSP - 1 else y0 + round((j + 1) * (y1 - y0) / NSP)
            loc.append((f'sp{nm}{j}', xs0, ya, xs1, yb, 'spine'))
    loc.append(('spu0', xs0 - DSU, QH - smh - SUH, xs1 + DSU, QH - smh, 'spine'))
    loc.append(('spu1', xs0 - DSU, smh, xs1 + DSU, smh + SUH, 'spine'))
    yb0 = smh + SUH
    hx0, hx1 = QW // 2 - HUBW // 2, QW // 2 + HUBW // 2
    loc.append(('hub', hx0, yb0, hx1, yb0 + 2 * BANDH, 'hub'))
    if V.get('band2'):
        # [io | hcb hcb | sfuc sfuc | HUB | idx idx | hcb hcb]: 2 rows; the SFU core / IDX score 2x2 blocks each give
        # the hub one whole face; the hc ring sits 4 + 4 at the band ends
        if V.get('band2') == 'ringE':      # hc ring whole at the E end (next to the root's hc_eng): no ring crossing
            cols = [(IOW, hx0, ['s0', 's1']), (hx1, QW, ['i0', 'i1', 'h0', 'h1', 'h2', 'h3'])]
        else:
            cols = [(IOW, hx0, ['h0', 'h1', 's0', 's1']), (hx1, QW, ['i0', 'i1', 'h2', 'h3'])]
        for xa0, xa1, names in cols:
            cw = (xa1 - xa0) // len(names)
            for j, c in enumerate(names):
                xa = xa0 + j * cw
                xb = xa1 if j == len(names) - 1 else xa + cw
                for r in range(2):
                    ya, yb = yb0 + r * BANDH, yb0 + (r + 1) * BANDH
                    if c[0] == 'h':
                        nm = f'b0{r}{c[1]}'
                    elif c[0] == 's':
                        nm = f'b11{2 * r + (1 - int(c[1]))}'      # inner column (next to the hub) = slices 0 / 2
                    else:
                        nm = f'b10{2 * r + int(c[1])}'
                    loc.append((nm, xa, ya, xb, yb, 'band'))
    for r in (range(2) if not V.get('band2') else ()):
        ya, yb = yb0 + r * BANDH, yb0 + (r + 1) * BANDH
        for h, (xa0, xa1) in enumerate(((IOW, hx0), (hx1, QW))):
            cw = (xa1 - xa0) // 4
            for j in range(4):
                xa = xa0 + j * cw
                xb = xa1 if j == 3 else xa + cw
                loc.append((f'b{h}{r}{j}', xa, ya, xb, yb, 'band'))
    loc.append(('io', 0, yb0, IOW, yb0 + 2 * BANDH, 'io'))      # SerDes (+ host UCIe in NW) on the die W / E edge
    quads = ['NW', 'NE', 'SW', 'SE'] if nq == 4 else ['NW', 'NE']
    OR = dict(NW='R0', NE='MY', SW='MX', SE='R180')
    yN0 = (PHYH + QH + SEAMH) if nq == 4 else 0
    for q in quads:
        for (ln, x0, y0, x1, y1, kind) in loc:
            X0, X1 = (x0, x1) if q in ('NW', 'SW') else (W - x1, W - x0)
            Y0, Y1 = (yN0 + y0, yN0 + y1) if q in ('NW', 'NE') else (PHYH + QH - y1, PHYH + QH - y0)
            parts[f'{q}_{ln}'] = dict(type=f'q_{ln}', rect=(X0, Y0, X1, Y1), orient=OR[q], quad=q, local=ln, kind=kind)
    px0 = (W - PHYW) // 2
    rows = [('N', H - PHYH, H)] + ([('S', 0, PHYH)] if nq == 4 else [])
    for side, y0, y1 in rows:
        ma = px0 // 2
        for xa, xb, o in ((0, ma, 'a'), (ma, px0, 'b')):
            parts[f'{side}W_mc{o}'] = dict(type=f'mc_{o}', rect=(xa, y0, xb, y1), quad=side + 'W',
                                           orient={'N': 'R0', 'S': 'MX'}[side], kind='mc', local=f'mc{o}')
            parts[f'{side}E_mc{o}'] = dict(type=f'mc_{o}', rect=(W - xb, y0, W - xa, y1), quad=side + 'E',
                                           orient={'N': 'MY', 'S': 'R180'}[side], kind='mc', local=f'mc{o}')
        parts[f'PHY_{side}'] = dict(type='phy', rect=(px0, y0, px0 + PHYW, y1), orient={'N': 'R0', 'S': 'MX'}[side],
                                    kind='phy', quad=None, local='phy')
    if nq == 2:
        return build_b_tail(parts, W, H, QW, QH, smh, V, var, quads, SEAMV)
    ys0 = PHYH + QH
    ys1 = ys0 + SEAMH
    # seam row: [hsW | ROOT (from the W spines to the E spines, under the vertical seam) | hsE]: the root abuts
    # all four tile spines directly (N / S faces), so every hub is spine -> root, no seam-row transit
    xr = [0, xs0, W - xs0, W]
    for nm, xa, xb in zip(['hsW', 'root', 'hsE'], xr, xr[1:]):
        parts[nm] = dict(type=nm, rect=(xa, ys0, xb, ys1), orient='R0', kind='root' if nm.startswith('root') else 'seam',
                         quad=None, local=nm)
    cuts = sorted({0, smh // 3, 2 * smh // 3, smh, smh + SUH, smh + SUH + BANDH, smh + SUH + 2 * BANDH, QH - smh,
                   QH - 2 * smh // 3, QH - smh // 3, QH})
    halves = [('N', yN0)] + ([('S', PHYH)] if nq == 4 else [])
    for hn, yb in halves:
        for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
            Y0, Y1 = (yb + a, yb + b) if hn == 'N' else (yb + QH - b, yb + QH - a)
            parts[f'vs{hn}{i}'] = dict(type=f'vs{hn}{i}', rect=(QW, Y0, QW + SEAMV, Y1), orient='R0', kind='seam',
                                       quad=None, local=f'vs{hn}{i}')
    return dict(W=W, H=H, QW=QW, QH=QH, parts=parts, quads=quads, V=V, var=var)


def build_b_tail(parts, W, H, QW, QH, smh, V, var, quads, SEAMV):
    """B (8 SM, 1 stack): the two quad tiles side by side under PHY_N; the vertical seam between them is the ROOT
    over the SU / band / SU rows (1 band-row hop from both hubs; VM ring = the one NW<->NE link through it) and a
    transit seam beside the two SM rows.  The S edge is the SM2/SM3 row (IO sits in the band-row io partitions)."""
    cuts = [0, smh // 3, 2 * smh // 3, smh, QH - smh, QH - 2 * smh // 3, QH - smh // 3, QH]
    for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
        nm = 'root' if a == smh else f'vsN{i}'
        parts[nm] = dict(type=nm, rect=(QW, a, QW + SEAMV, b), orient='R0', kind='root' if nm == 'root' else 'seam',
                         quad=None, local=nm)
    return dict(W=W, H=H, QW=QW, QH=QH, parts=parts, quads=quads, V=V, var=var)


# --------------------------------------------------------------------------------------------- census -> partitions
def assign(L):
    """role -> list of NW-local partitions (quad roles) or die partitions (G roles)."""
    def q(n):
        return n
    A = {}
    for k in range(4):
        near, far = (f'su{k}1', f'su{k}0') if k in (0, 2) else (f'su{k}0', f'su{k}1')   # near = hub side
        A[f'sm{k}'] = [f'sm{k}']
        near, far = (f'su{k}1', f'su{k}0') if k in (0, 2) else (f'su{k}0', f'su{k}1')   # near = hub side
        A[f'su_Q{k}'] = [far, near]
        for v in (2 * k, 2 * k + 1):
            A[f'vmb_Q{v}'] = ['hub']; A[f'vmdel_Q{v}'] = ['hub']; A[f'vmm_Q{v}'] = ['hub']   # VM slice = hub + banks
        A[f'sfu_Q{k}'] = [far]; A[f'fl_Q{k}'] = [far]
        A[f'hc_Q{k}'] = [far]; A[f'cxdl_Q{k}_q'] = [far]; A[f'cxdl_Q{k}_s'] = [far]
        top = k < 2
        # HBM access (vmks keyspace + svg scatter/gather) for all 4 SMs at the memory end of the spine
        SH = L['V'].get('spuhub')
        A[f'svg{k}'] = ['hub' if SH else 'spu0' if top else 'spu1']
        A[f'vmks{k}'] = ['hub' if SH else 'spu0' if top else 'spu1']
        A[f'cp_svg{k}'] = ['spt0' if top else f'spb{NSP - 1}']
        A[f'xc{k}'] = ['spt0' if top else f'spb{NSP - 1}']
        A[f'hcollks_Q_p{k}'] = ['hub']
    for p in range(16):           # pseudo-channel controllers next to the keyspace units (spine top, under the PHY row)
        A[f'ctl_p{p:02d}'] = ['hub' if L['V'].get('spuhub') else 'spu0' if p // 4 < 2 else 'spu1']  # with its SM's vmks
    # service band: hc ring (8 banks) in the SM1/SM3 half (b1*), SFU / IDX in the SM0/SM2 half (b0*); hub 2x2 centre
    # band (seam side): row 1 (SU2/3 side) = IDX score quarter x 3 + SFU store/programme; row 0 = hc ring + SFU core
    # band by area: W half = hc ring, one 0.54-mm2 bank per partition (ring order around the half);
    # E half = IDX score quarter (row 0, 4 slices) + SFU core (row 1, 4 slices); SFU store / programme in the hub
    for i, (r, j) in enumerate([(0, 0), (0, 1), (0, 2), (0, 3), (1, 3), (1, 2), (1, 1), (1, 0)]):
        A[f'hcb_Q{i}'] = [f'b0{r}{j}']
    A['hb_idx__s_Q'] = ['b100', 'b101', 'b102', 'b103']
    A['sfucore_Q'] = ['b110', 'b111', 'b112', 'b113']
    A['sfus_Q'] = ['hub']
    A['sfup_Q'] = ['hub']
    for r in ('hb_idx__q_Q', 'hb_idx__op_Q', 'hb_idx__qctl_Q', 'idx_share_Q', 'qdq', 'hb_dbk_Q', 'wbk_Q', 'wbc_Q'):
        A[r] = ['hub']
    for r in ('hb_vms_Q', 'xl_Q_ctl', 'xl_Q_aqhi', 'xl_Q_aqlo', 'smw_Q', 'calendar_Q', 'vmfc_Q', 'vmm_Q') + \
            tuple(f'xq_Q_p{p}_{t}' for p in (0, 1) for t in ('bd', 'eg', 'bfq0', 'bfq1', 'bfq2', 'bfq3')):
        A[r] = ['hub']
    for r in ('pgp_Q', 'sucore_Q', 'subr_Q', 'stl_Q', 'col_sfu_Q', 'cxij_Q_q', 'cxij_Q_s', 'cxrc_Q_q', 'cxrc_Q_s', 'cic_Q',
              'cij_Q', 'hleaf_Q'):
        A[r] = ['hub']
    for r in ('hb_coll_Q', 'hcollgi_Q', 'hcollgl_Q', 'hcollks_Q', 'hcollrs_Q', 'hcollb_Q', 'epcal_Q', 'hc_Q', 'obs_Q',
              'fr_Q', 'fs_Q', 'fcx_Q'):
        A[r] = ['hub']
    A['sfault_Q'] = ['@mcb']; A['refcfg_Q'] = ['@mcb']
    return A


DIE_ROLE = {
    'phy': '@phy', 'tkm_SW': 'root', 'hb_idx__selector': 'root', 'hb_idx__link': 'root', 'hb_idx__ctl': 'root',
    'hb_idx__xqr': 'root', 'hb_idx__xq_N': 'root', 'hb_idx__xq_S': 'root', 'col_idx': 'root',
    'hc_eng': 'root', 'hb_argmax': 'root', 'su_prog': 'root', 'str_C': 'root', 'col_su': 'root',
    'hb_router_ids': 'root', 'host_cp_ingress': 'root', 'host_cp_rxs': 'root', 'host_status': 'root',
    'obs_C': 'root', 'vm_status4': 'root', 'host_N': 'NW_io', 'host_ep': 'NW_io', 'lk_S1': 'SW_mca',
    'ep_S1': 'SW_mca', 'hb_ckgen': 'root',
}
SERDES_Q = {'lk_N0': 'NW', 'ep_N0': 'NW', 'lk_N2': 'NE', 'ep_N2': 'NE', 'lk_S0': 'SW', 'ep_S0': 'SW', 'lk_S3': 'SE',
            'ep_S3': 'SE'}
QDQ_RE = re.compile(r'^hb_quant_Q__')


def die_part(r, A, quads):
    return DIE_ROLE.get(r)


def mapping(T, census):
    """instance -> list of die partitions (as-built name)."""
    cen, blocks, role, bw = census
    A = assign(T)
    out = {}
    nq = len(T['quads'])
    for n, (q, r) in role.items():
        if n in SERDES_Q:
            qq = SERDES_Q[n]
            if qq not in T['quads'] and T['V'].get('mirror'):
                # B2: the d4f SerDes count per die is kept (5 x 6 lanes): the S-quadrant macros go to the S-edge
                # bottom-spine partitions (beachfront, empty corridor), one per tile (mirror pair)
                out[n] = ['NW_spb0' if qq == 'SW' else 'NE_spb0']
                continue
            if qq not in T['quads']:
                continue                       # B: the S quadrants' SerDes do not exist on this die
            out[n] = [f'{qq}_io']
            continue
        if nq == 2 and (q in ('SW', 'SE') or n == 'phy_SW'):
            continue                           # B: 2-quadrant die (NW / NE tiles); S quadrants and PHY_S not built
        if q == 'G':
            p = DIE_ROLE.get(r)
            if p is None:
                raise SystemExit(f'unmapped die role {n} {r}')
            if p == '@phy':
                p = 'PHY_N' if (n.endswith('NW') or nq == 2) else 'PHY_S'
            elif p == 'SW_mca' and nq == 2:
                p = 'vsN0' if T['V'].get('mirror') else 'NE_mca'   # B2: S-edge centre (keeps NW / NE symmetric)
            out[n] = [p]
            continue
        rr = 'qdq' if QDQ_RE.match(r) else r
        loc = A.get(rr)
        if loc is None:
            raise SystemExit(f'unmapped quad role {n} {r}')
        res = []
        for l in loc:
            if l.startswith('@mc'):
                res.append(f'{q[0]}{q[1]}_mc{l[3]}')
            else:
                res.append(f'{q}_{l}')
        out[n] = res
    return out


# --------------------------------------------------------------------------------------------- geometry helpers
def adjacency(parts):
    """partition adjacency: (a, b) -> (face of a, lo, hi) shared segment in um."""
    R = {n: tuple(u(v) for v in p['rect']) for n, p in parts.items()}
    adj = collections.defaultdict(dict)
    names = list(R)
    byx = collections.defaultdict(list)
    for n in names:
        x0, y0, x1, y1 = R[n]
        byx[('x', round(x0, 3))].append(n); byx[('X', round(x1, 3))].append(n)
        byx[('y', round(y0, 3))].append(n); byx[('Y', round(y1, 3))].append(n)
    for n in names:
        x0, y0, x1, y1 = R[n]
        for m in byx[('x', round(x1, 3))]:                       # m to the E of n
            a0, b0, a1, b1 = R[m]
            lo, hi = max(y0, b0), min(y1, b1)
            if hi - lo > MINC:
                adj[n][m] = ('E', lo, hi); adj[m][n] = ('W', lo, hi)
        for m in byx[('y', round(y1, 3))]:                       # m to the N of n
            a0, b0, a1, b1 = R[m]
            lo, hi = max(x0, a0), min(x1, a1)
            if hi - lo > MINC:
                adj[n][m] = ('N', lo, hi); adj[m][n] = ('S', lo, hi)
    return R, adj


def centre(R, n):
    x0, y0, x1, y1 = R[n]
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def plen(R, path):
    return sum(abs(centre(R, x)[0] - centre(R, y)[0]) + abs(centre(R, x)[1] - centre(R, y)[1]) for x, y in zip(path, path[1:]))


DETOUR = 1.8
MINC = 400.0                # min shared edge (um) for a port


def shortest(R, adj, parts, a, b, hard, ecost=None):
    """Dijkstra on partition centres, state = (partition, entry face): no U-turn (a ft slot needs in != out face);
    hard partitions are endpoints only; ecost(n, m) adds congestion cost (None = full)."""
    s0 = (a, None)
    dist = {s0: 0.0}
    prev = {}
    pq = [(0.0, s0)]
    end = None
    while pq:
        d, st = heapq.heappop(pq)
        n, fin = st
        if n == b:
            end = st
            break
        if d > dist.get(st, 1e18):
            continue
        if n != a and n in hard:
            continue
        cx, cy = centre(R, n)
        for m, (f, lo, hi) in adj[n].items():
            if m in hard and m != b:
                continue
            if fin is not None and f == fin:
                continue
            ec = ecost(n, m, fin if n != a else None, f) if ecost else 0.0
            if ec is None:
                continue
            mx, my = centre(R, m)
            nd = d + abs(mx - cx) + abs(my - cy) + 50.0 + ec
            sm = (m, OPPF[f])
            if nd < dist.get(sm, 1e18):
                dist[sm] = nd; prev[sm] = st
                heapq.heappush(pq, (nd, sm))
    if end is None:
        return None
    path = [end]
    while path[-1] != s0:
        path.append(prev[path[-1]])
    return [x[0] for x in path[::-1]]


# --------------------------------------------------------------------------------------------- traffic
def traffic(T, census, M):
    cen, blocks, role, bw = census
    R, adj = adjacency(T['parts'])
    exempt = collections.Counter()
    acc = collections.defaultdict(int)          # (src inst, src bus, dst part, kind) -> bits (capped at bus width)
    for g in cen['groups']:
        if g['kind'] in ('clock', 'reset') or re.match(r'^(por_|pll_|clk|rst)', g['src_bus']):
            exempt[g['kind']] += g['bits']
            continue
        if g['src'] not in M or g['dst'] not in M:
            continue                           # B: traffic of a quadrant this die does not build
        sp, dp = M[g['src']], M[g['dst']]
        # nearest pair of member partitions
        best = None
        for a in sp:
            for b in dp:
                (ax, ay), (bx, by) = centre(R, a), centre(R, b)
                d = abs(ax - bx) + abs(ay - by)
                if best is None or d < best[0]:
                    best = (d, a, b)
        _, a, b = best
        if a == b:
            continue
        acc[(g['src'], g['src_bus'], a, b, g['kind'])] += g['bits']
    pair = collections.defaultdict(int)
    for (si, sb, a, b, kd), bits in acc.items():
        w = bw.get(f'{si}.{sb}')
        pair[(a, b, 'ctl' if kd == 'ctl' else 'data')] += min(bits, w) if w else bits
    return pair, exempt


def canon(T, pair):
    """canonical quad tile: intra-tile pair widths = max over the 4 tiles (identical tiles); tile <-> die / tile <-> tile
    pairs per relation, max over tiles, re-emitted for every tile."""
    P = T['parts']
    qof = {n: p['quad'] if p['kind'] not in ('mc',) else None for n, p in P.items()}
    def tq(n):
        p = P[n]
        if p['kind'] in ('sm', 'su', 'spine', 'band', 'hub', 'io'):
            return p['quad'], p['local']
        if p['kind'] == 'mc':
            return p['quad'], p['local']          # mc partitions follow their tile (mirror)
        return None, n
    rel = {}
    quads = T['quads']
    def relq(a, b):
        if a == b:
            return 'L'
        if a[0] == b[0]:
            return 'h'
        if a[1] == b[1]:
            return 'v'
        return 'd'
    def partner(q, r):
        for b in quads:
            if relq(q, b) == r:
                return b
        return None
    agg = collections.defaultdict(int)
    for (a, b, kd), w in pair.items():
        qa, la = tq(a); qb, lb = tq(b)
        if qa and qb:
            key = ('QQ', la, relq(qa, qb), lb, kd)
        elif qa:
            key = ('QD', la, b, kd, qa if b.startswith('PHY') or b.startswith('root') or True else '')
            key = ('QD', la, b if not b.startswith('PHY') else 'PHY', kd)
        elif qb:
            key = ('DQ', a if not a.startswith('PHY') else 'PHY', lb, kd)
        else:
            key = ('DD', a, b, kd)
        agg[key] = max(agg[key], w)
    out = collections.defaultdict(int)
    def nm(q, l):
        if l.startswith('mc'):
            return f'{q}_{l}'
        return f'{q}_{l}'
    def phy_of(q):
        return 'PHY_N' if q[0] == 'N' else 'PHY_S'
    for key, w in agg.items():
        if key[0] == 'QQ':
            _, la, r, lb, kd = key
            for q in quads:
                b = partner(q, r) if r != 'L' else q
                if b:
                    out[(nm(q, la), nm(b, lb), kd)] = max(out[(nm(q, la), nm(b, lb), kd)], w)
        elif key[0] == 'QD':
            _, la, d, kd = key
            for q in quads:
                dd = phy_of(q) if d == 'PHY' else d
                if dd in P:
                    out[(nm(q, la), dd, kd)] = max(out[(nm(q, la), dd, kd)], w)
        elif key[0] == 'DQ':
            _, d, lb, kd = key
            for q in quads:
                dd = phy_of(q) if d == 'PHY' else d
                if dd in P:
                    out[(dd, nm(q, lb), kd)] = max(out[(dd, nm(q, lb), kd)], w)
        else:
            _, a, b, kd = key
            out[(a, b, kd)] = max(out[(a, b, kd)], w)
    return out


# --------------------------------------------------------------------------------------------- emit plan
def emit(T, bundles, M, census, outdir):
    P = T['parts']
    R, adj = adjacency(P)
    hard = {n for n, p in P.items() if p['kind'] in ('sm', 'phy')}
    # routes; NW-tile canonical routes for intra-tile + tile->die lanes are mirrored by construction of the geometry
    lanes = []
    unrouted = []
    use = collections.defaultdict(float)

    def cap(n, m):
        f, lo, hi = adj[n][m]
        return (hi - lo - 4.0) * PIN_UM

    tuse = collections.defaultdict(float)

    def tdirs(fin, fout):
        if fin is None:
            return ()
        if fin in 'EW' and fout in 'EW':
            return ('H',)
        if fin in 'NS' and fout in 'NS':
            return ('V',)
        return ('H', 'V')

    def tcap(n, d):
        x0, y0, x1, y1 = R[n]
        return FT_UM * ((y1 - y0) if d == 'H' else (x1 - x0)) * TFRAC

    def ecost(n, m, fin=None, fout=None):
        k = tuple(sorted((n, m)))
        c = cap(n, m)
        x = use[k] / c if c > 0 else 9.0
        for d in tdirs(fin, fout):                       # over-the-top (M8 / M9) transit budget of n
            x = max(x, tuse[(n, d)] / tcap(n, d))
        if x > 1.0:
            return None
        return 400.0 * x * x + (4000.0 if x > 0.85 else 0.0)
    # bundles wider than LANE_MAX bits are split into equal sub-lanes (each routed on its own: spreads a wide bundle
    # over parallel corridors; still whole as-built buses in the RTL binding)
    items = []
    for (a, b, kd), w in bundles.items():
        n = max(1, math.ceil(w / LANE_MAX))
        for j in range(n):
            items.append(((a, b, kd), w // n + (1 if j < w % n else 0)))
    order = sorted(items, key=lambda kv: -kv[1])
    for (a, b, kd), w in order:
        if w <= 0:
            continue
        base = shortest(R, adj, P, a, b, hard)
        path = shortest(R, adj, P, a, b, hard, ecost)
        if path is None or (base is not None and plen(R, path) > DETOUR * plen(R, base) + 1500.0):
            path = base
        if path is not None:
            for x, y in zip(path, path[1:]):
                use[tuple(sorted((x, y)))] += w + 1 + 3
            for h in range(1, len(path) - 1):
                fi = OPPF[adj[path[h - 1]][path[h]][0]]
                fo = adj[path[h]][path[h + 1]][0]
                for d in tdirs(fi, fo):
                    tuse[(path[h], d)] += w
        if path is None:
            unrouted.append((a, b, kd, w))
            continue
        lanes.append(dict(src=a, dst=b, kind=kd, width=int(w), path=path))
    util = sorted(((use[k] / max(cap(*k), 1.0), k[0], k[1], int(use[k])) for k in use), reverse=True)
    T['tutil'] = sorted(((v / tcap(n, d), n, d, int(v)) for (n, d), v in tuse.items()), reverse=True)[:25]
    T['util'] = util
    # window allocation per (die-frame shared segment): stack windows along the segment in a deterministic order
    seg_use = collections.defaultdict(float)
    ports, lane_out = [], []
    buses = collections.defaultdict(list)
    slots = collections.defaultdict(list)
    errs = []
    for i, L in enumerate(lanes):
        pids = []
        path = L['path']
        for h in range(len(path) - 1):
            a, b = path[h], path[h + 1]
            face, lo, hi = adj[a][b]
            lay = HL if face in ('E', 'W') else VL
            transit = 0 < h < len(path) - 2          # both ends ft slots: the M8 / M9 third layer is free here
            if not transit:
                lay = lay[:2]                         # an endpoint pin on M8 / M9 would eat the partition's ft budget
            key = tuple(sorted((a, b)))
            start = lo + 2.0 + seg_use[key]
            # window: smallest that fits the bits (+ epoch): 3 layers at <= 8.8 pins/um, 2 layers at <= 5.8
            n = L['width'] + 1
            hi_w = S.window_for(start, n, lay, LAYERS, per_um=8.8 if transit else 5.8, track_max=0.6)
            if hi_w > hi - 2.0:
                errs.append(f'segment {a}|{b} overflow: lane {i} needs up to {hi_w:.1f} > {hi - 2.0:.1f}')
            seg_use[key] = hi_w - lo - 2.0 + 0.48
            pid = f'L{i}_{h}'
            pr = dict(id=pid, src=dict(part=a, bus=(f'L{i}_o' if h == 0 else f'L{i}x{h}_o')),
                      dst=dict(part=b, bus=(f'L{i}_i' if h == len(path) - 2 else f'L{i}x{h + 1}_i')),
                      width=L['width'], kind=L['kind'], face=face, layers=lay,
                      window_um=[round(start, 4), round(hi_w, 4)])
            ports.append(pr)
            pids.append(pid)
            if h == 0:
                buses[a].append(dict(name=f'L{i}_o', dir='out', width=L['width'], kind=L['kind']))
            if h == len(path) - 2:
                buses[b].append(dict(name=f'L{i}_i', dir='in', width=L['width'], kind=L['kind']))
            else:
                # ft slot in b: in on the face opposite to `face`, out on the next hop's face
                pass
        for h in range(1, len(path) - 1):
            p = path[h]
            fin = OPPF[adj[path[h - 1]][p][0]]
            fout = adj[p][path[h + 1]][0]
            if fin == fout:
                errs.append(f'lane {i} u-turn in {p}')
            # station count from in/out window distance
            pin_in = ports[-(len(path) - 1) + h - 1]
            pin_out = ports[-(len(path) - 1) + h]
            def wc(pr):
                lo, hi = pr['window_um']; c = (lo + hi) / 2
                x0, y0, x1, y1 = R[p]
                f = pr['face'] if pr['src']['part'] == p else OPPF[pr['face']]
                return {'E': (x1, c), 'W': (x0, c), 'N': (c, y1), 'S': (c, y0)}[f]
            (xa, ya), (xb, yb) = wc(pin_in), wc(pin_out)
            dist = abs(xa - xb) + abs(ya - yb)
            st = max(1, math.ceil(dist / (REACH - 30)) - 1)
            slots[p].append(dict(name=f'L{i}x{h}', in_face=fin, out_face=fout, width=L['width'], stations=st))
        lane_out.append(dict(id=f'L{i}', ports=pids, note=f'{L["src"]}->{L["dst"]} {L["kind"]}'))
    return lanes, ports, lane_out, buses, slots, errs, unrouted, R


def plan_json(T, lanes, ports, lane_out, buses, slots, R, M, census, outdir):
    P = T['parts']
    cen, blocks, role, bw = census
    types = {}
    # contents per partition from the mapping
    contents = collections.defaultdict(list)
    for n, ps in M.items():
        for p in ps:
            contents[p].append(n)
    cells_ev = json.load(open(os.path.join(roles.D4G, 'inputs', 'cells_evidence.json')))['masters']
    def cells_of(inst, share):
        m = blocks.get(inst, {}).get('master', '')
        c = cells_ev.get(m, {}).get('cells') or cells_ev.get(re.sub(r'__pv\d+$', '', m), {}).get('cells') or 0
        return int(c / share)
    parts_out = []
    fit = {}
    MIR = T['V'].get('mirror')
    import emit_mirror as EM

    def sig(n):
        # role signature (as-built per-quadrant parameter variants __pvN / glue_nw_t are one master + a quad-ID strap)
        return sorted((census[2].get(i, (None, i))[1] if census[2].get(i, ('G',))[0] != 'G' else re.sub(r'^(lk|ep)_[NS]\d$', r'\1', i), len(M[i])) for i in contents.get(n, []))
    order_ = sorted(P, key=lambda n: (n.startswith('NE_'), n))      # NW masters first
    tname = {}
    for n in order_:
        sa, sb_ = sig(n), sig(EM.mir(n))
        # NW-only as-built blocks (quant / idx_share / vmm live in quadrant NW of the r18h5 census): the tile master
        # carries them, the NE copy is the same master (lanes are already canonical = max over the quadrants)
        sub = n.startswith('NW_') and set(sb_) <= set(sa) or n.startswith('NE_') and set(sa) <= set(sb_)
        if sub and sa != sb_:
            T.setdefault('master_superset', {})[n[3:]] = sorted({r for r, _ in set(sa) ^ set(sb_)})
        if MIR and not EM.single(n) and P[n]['kind'] not in ('sm',) and (sa == sb_ or (sub and P[n]['kind'] == 'hub')):
            tname[n] = 'q_' + n[3:]
        elif MIR and P[n]['kind'] == 'sm':
            tname[n] = 'q_' + n[3:]
        else:
            tname[n] = n
    FL = {'E': 'W', 'W': 'E', 'N': 'N', 'S': 'S'}
    for n in order_:
        p = P[n]
        x0, y0, x1, y1 = (u(v) for v in p['rect'])
        tn = tname[n]
        flip = MIR and n.startswith('NE_') and tn.startswith('q_')
        if tn in types:                 # mirror instance of a shared master: check buses / slots, then place it MY
            t0 = types[tn]
            sl = sorted((x['name'], FL[x['in_face']], FL[x['out_face']], x['width']) for x in slots.get(n, []))
            s0 = sorted((x['name'], x['in_face'], x['out_face'], x['width']) for x in t0['ft_slots'])
            b0 = sorted(x['name'] for x in t0['buses'])
            if sl != s0 or sorted(x['name'] for x in buses.get(n, [])) != b0:
                T.setdefault('mirror_errs', []).append(n)
            parts_out.append(dict(name=n, type=tn, origin_um=[x0, y0], orient='MY'))
            continue
        w, h = round(x1 - x0, 4), round(y1 - y0, 4)
        insts = sorted(contents.get(n, []))
        cells = sum(cells_of(i, len(M[i])) for i in insts)
        cont, hcs, used = [], [], 0.0
        if p['kind'] == 'sm':
            sm_mod = 'hnx_sm_p3_rp3lp3x_8x2' if T['var'] != 'Ac' else 'ot_hbm_accel_smh_attn_qsplit'
            cont.append(dict(inst='u_sm', module=sm_mod, status='reuse', cells=0,
                             note='SM slot = 8 x 2 hnx_rp3lp3x lane tiles (630.72 x 2246.4, HNX-SM4P halves)'
                             if T['var'] != 'Ac' else 'current SM as 2 x 2 QSPLIT quarters'))
            hcs.append(dict(inst='u_sm', module=sm_mod, origin_um=[0.0, 0.0], outline_um=[w, h], track_offset_um=[0.0, 0.0]))
            used = w * h
        else:
            # as-built blocks (reused leaves); a block shared by k partitions is split into k cores of area/k
            rects = []
            for i in insts:
                b = blocks.get(i)
                if not b:
                    continue
                k = len(M[i])
                bw_, bh_ = b['w'], b['h']
                if k > 1 or (bh_ > h - 2 * G and not re.search(r'phy|ucie|serdes', b['master'])):
                    a = bw_ * bh_ / k
                    bh_ = min(bh_, h - 2 * G)
                    bw_ = a / bh_
                if bw_ > w - 2 * G and not re.search(r'phy|ucie|serdes', b['master']):
                    a = bw_ * bh_
                    bw_ = w - 2 * G
                    bh_ = a / bw_
                rects.append((i, b['master'], bw_, bh_, k))
            rects.sort(key=lambda r: -r[3])
            cx, cy, rowh = G, G, 0.0
            for (i, mod, bw_, bh_, k) in rects:
                bw_ = math.ceil(bw_ / G) * G; bh_ = math.ceil(bh_ / G) * G
                if cx + bw_ > w - G:
                    cx, cy, rowh = G, cy + rowh + G, 0.0
                ok = cx + bw_ <= w - G + 1e-6 and cy + bh_ <= h - G + 1e-6
                if not ok:
                    fit.setdefault(n, []).append(i)
                inst = 'u_' + re.sub(r'[^A-Za-z0-9_]', '_', i)
                cont.append(dict(inst=inst, module=mod, status='reuse' if k == 1 else 'rework',
                                 cells=cells_of(i, k), note=f'as-built {i}' + (f' (1/{k} slice)' if k > 1 else '')))
                hcs.append(dict(inst=inst, module=mod, origin_um=[round(cx, 4), round(cy, 4)], track_offset_um=[0.0, 0.0],
                                outline_um=[round(bw_, 4), round(bh_, 4)]))
                used += bw_ * bh_
                cx += bw_ + G
                rowh = max(rowh, bh_)
            if not cont:
                cont.append(dict(inst='u_ft', module=f'hbm_arch_ft_{tn}', status='new', cells=0,
                                 note='transit only: ft stations + pin registers'))
        if MIR:
            for c in cont:
                c['inst'] = re.sub(r'_NW(?=\d|_|$)', '_Q', c['inst'])
            for c in hcs:
                c['inst'] = re.sub(r'_NW(?=\d|_|$)', '_Q', c['inst'])
        t = dict(module=f'hbm_arch_{tn}', outline_um=[w, h], hard=p['kind'] in ('phy', 'sm'),
                 face_layers=dict(E=HL, W=HL, N=VL, S=VL),
                 buses=buses.get(n, []), ft_slots=slots.get(n, []),
                 clock=dict(tap_um=[round(w / 2, 3), round(h / 2, 3)], layer='M9', insertion_ps=250,
                            **({'tap_pitch_um': float(max(w, h))} if p['kind'] in ('phy', 'sm') else {})),  # hard macro: one clock pin, own tree
                 reset=dict(tap_um=[round(w / 2, 3), round(h / 2, 3)], sync_stages=2),
                 contents=cont, cells=max(cells, 1000))
        if p['kind'] == 'sm' and T['V'].get('sm_channel'):
            chh = T['V']['sm_channel'] * G
            t['channels'] = [dict(rect_um=[0.0, round((h - chh) / 2, 4), w, round(chh, 4)],
                                  reason='SM driver channel between the two half-tile rows: clock tap drivers (tap at its '
                                         'centre), the halves rst_n landings / reset sync, spare repeaters')]
        if p['kind'] == 'sm' and T['V'].get('sm_col_channel'):
            gap = T['V']['sm_col_channel'] * G
            for col in range(1,8):
                t.setdefault('channels', []).append(dict(rect_um=[round(col*630.72+(col-1)*gap,4),0.0,gap,h],
                    reason='SM column broadcast channel: 2069 bits into both halves, M4/M6 at 0.048um pitch and 60% usable tracks; no new pipeline stage'))
        if p['kind'] == 'phy':
            fit.pop(n, None)
        if p['kind'] not in ('phy',) and hcs:
            t['hard_cores'] = hcs
        t['_fill'] = round(used / (w * h), 3)
        types[tn] = t
        parts_out.append(dict(name=n, type=tn, origin_um=[x0, y0], orient='R0'))
    T['fit'] = fit
    T['fill'] = {tn: t.pop('_fill') for tn, t in types.items()}
    plan = dict(schema='opentallas.die_plan.v1',
                note=f'HBM-ARCH concept ({T["V"]["label"]}); gen_arch.py; quad-tile array, beachfront PHYs, seam fabric, root tile',
                die=dict(name=f'hbm_arch_{T["var"]}', label=T['V']['label'], tech='asap7',
                         outline_um=[u(T['W']), u(T['H'])], period_ps=833, reach_um=1000.0, rep_um=450.0, grid_um=G,
                         layer_budget=dict(partition_signal_max='M7', die_layers=['M8', 'M9'],
                                           die_use=['clock_spine', 'pg', 'ft_reserved'], cut_avail=dict(M8=0.6, M9=0.6)),
                         pg=dict(partition_pg_max='M7', grid=[dict(layer='M8', width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=['VDD', 'VSS']),
                                                              dict(layer='M9', width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=['VDD', 'VSS'])])),
                partition_types=types, partitions=parts_out, ports=ports, lanes=lane_out,
                clock=dict(source=dict(part='@die', bus='clk'), insertion_ps=250, common_latency_ps=250, insertion_tol_ps=40,
                           neighbour_skew_ps=80, face_xing='budgeted',
                           spine=dict(layers=['M8', 'M9'], root_um=[u(T['W']) / 2, u(T['H']) / 2], topology='htree')),
                reset=dict(source=dict(part='@die', bus='rst_n'), sync_stages=2, data_reset=False, epoch_bit=True, release='counted'),
                budgets=dict(face_pins_per_um=6, face_pin_layers=2, face_window_um=10, pin_track_max=0.6, cut_ratio_max=0.6,
                             cut_step_um=250, pin_reg_p90_um=30, ft_station_max_um=REACH),
                latency=dict(lanes={}),
                census=[dict(rows='../../hbm/census/hbm_r18h5_rows.tsv.gz', map='census_map.json',
                             note='r18h5 FT census re-mapped by HBM-ARCH roles (gen_arch.mapping)')]
                if len(T['quads']) == 4 else
                {'none': 'B is a 2-quadrant die: lanes = the 16-SM r18h5 census folded (SW->NW, SE->NE; per-pair width = '
                         'max over the folded quadrants); no as-built census of this die exists'})
    return plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', default='A')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    T = build(a.variant)
    census = roles.load()
    M = mapping(T, census)
    pair, exempt = traffic(T, census, M)
    bundles = canon(T, pair)
    if T['V'].get('mirror'):
        import emit_mirror as EM, clock_htree as CH
        rects = {n: tuple(u(v) for v in p['rect']) for n, p in T['parts'].items()}
        hsegs, hleaves, hres = CH.build(u(T['W']), u(T['H']), rects)
        lanes, ports, lane_out, buses, slots, errs, unrouted, R = EM.emit_mirror(
            T, bundles, G, u, adjacency, shortest, plen, OPPF, HL, VL, LAYERS, FT_UM, LANE_MAX, DETOUR, REACH, reserve=hres)
    else:
        lanes, ports, lane_out, buses, slots, errs, unrouted, R = emit(T, bundles, M, census, a.out)
    plan = plan_json(T, lanes, ports, lane_out, buses, slots, R, M, census, a.out)
    if T['V'].get('mirror'):
        # clock spine reservation -> per-type ft_budget (M8 for H, M9 for V): cut_avail minus the spine's NDR tracks
        tracks = {}
        for pt in plan['partitions']:
            tn = pt['type']; w, h = plan['partition_types'][tn]['outline_um']
            for d, ln, ext_ in (('H', 'M8', h), ('V', 'M9', w)):
                r = hres.get((pt['name'], d), 0)
                if r:
                    ut = S.usable_tracks(LAYERS[ln], ln, 0.0, ext_)
                    fb = plan['partition_types'][tn].setdefault('ft_budget', {})
                    fb[ln] = round(min(fb.get(ln, 0.6), 0.6 - r / ut), 6)
                    tracks[f"{pt['name']}.{ln}"] = r
        json.dump(dict(rule=CH.__doc__, ndr_tracks=CH.NDR_TRACKS, root_um=[u(T['W']) / 2, u(T['H']) / 2],
                       segments=[dict(xy=[s_[0], s_[1], s_[2], s_[3]], level=s_[4], layer=s_[5]) for s_ in hsegs],
                       leaves=hleaves, reserved_tracks=tracks,
                       hard_core_comp='SM / PHY clock pin: leaf delay = common latency 250 - core lib insertion',
                       gate='related-pair skew with CPPR <= 80 ps at TT and FF (seam pairs share the trunk)'),
                  open(os.path.join(a.out, 'clock_htree.json'), 'w'), indent=0)
        CH.render(plan, hsegs, hleaves, os.path.join(a.out, 'clock_htree.png'),
                  f"{plan['die']['name']}: MSCTS H-tree, seam trunk M9 + mirrored M8/M9 ribs, {len(hleaves)} tap drivers, "
                  f"NDR {CH.NDR_TRACKS} tracks/wire reserved in ft_budget")
    # ft stations from the checker's own route geometry (zroute between the slot's in / out windows): <= 850 um apart
    import check as CK
    Pl = S.Plan(plan)
    slot_k = {}
    for L in plan['lanes']:
        for part, slot, pa_, pb_ in Pl.lane_crossings(L['id']):
            sl = Pl.slot(part, slot)
            seg = CK.zroute(Pl.port_point(pa_), Pl.port_point(pb_), Pl.die_face(part, sl['in_face']),
                            Pl.die_face(part, sl['out_face']))
            k_ = (Pl.parts[part]['type'], slot)
            slot_k[k_] = max(slot_k.get(k_, 1), math.ceil(CK.plen(seg) / STATION_UM))
    for tn, t in plan['partition_types'].items():
        for sl in t['ft_slots']:
            sl['stations'] = slot_k.get((tn, sl['name']), sl['stations'])
    # latency table
    Pl = S.Plan(plan)
    for L in plan['lanes']:
        lat = Pl.lane_latency(L['id'])
        plan['latency']['lanes'][L['id']] = lat
    json.dump(plan, open(os.path.join(a.out, 'die_plan.json'), 'w'), indent=0)
    groups = {f'g_{n}': ps for n, ps in M.items() if len(ps) > 1}
    for q in ('NW', 'NE', 'SW', 'SE'):           # SM QSPLIT quarters: SM-internal traffic
        for k in range(4):
            for c in 'abcd':
                if f'sm_{q}{k}' in M or any(n.startswith(f'sm{k}') for n in ()):
                    pass
    smq = {}
    rl = census[2]
    for n, ps in M.items():
        q, r = rl.get(n, (None, None))
        mm = re.match(r'^sm(\d)$', r or '')
        if mm and q in ('NW', 'NE', 'SW', 'SE'):
            for c in 'abcd':
                smq[f'smq_{q}{mm.group(1)}{c}'] = ps[0]
    cmap = dict(bus_widths='../../hbm/census/bus_widths.json.gz', parts=dict({n: ps[0] for n, ps in M.items() if len(ps) == 1}, **smq),
                rules=[[f'^{re.escape(n)}$', f'g_{n}'] for n, ps in M.items() if len(ps) > 1],
                groups=groups,
                exempt=[dict(match='^(clock|reset)$', kind='clock', replaced_by='die clock spine + per-partition reset sync',
                             reason='clock/reset are spine nets, not lanes')])
    json.dump(cmap, open(os.path.join(a.out, 'census_map.json'), 'w'), indent=0)
    tot = sum(L['width'] for L in lanes)
    summ = dict(fit_fail=T['fit'], fill_max=sorted(((v, k) for k, v in T['fill'].items()), reverse=True)[:12], variant=a.variant, label=T['V']['label'], die_um=[u(T['W']), u(T['H'])],
                die_mm2=round(u(T['W']) * u(T['H']) / 1e6, 1), partitions=len(T['parts']), lanes=len(lanes),
                bits=tot, util_top=[list(x) for x in T['util'][:25]], tutil_top=[list(x) for x in T['tutil']], errs=errs[:50], n_errs=len(errs), unrouted=unrouted, exempt=dict(exempt),
                face_occ_top=[list(x) for x in T.get('focc', [])[:25]], ft_top=[list(x) for x in T.get('ftu', [])[:25]],
                mirror_errs=T.get('mirror_errs', []), master_superset=T.get('master_superset', {}), types=len(plan['partition_types']), need3=len(T.get('need3', ())))
    json.dump(summ, open(os.path.join(a.out, 'gen_summary.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in summ.items() if k not in ('errs',)}, indent=1)[:3000])
    for e in errs[:20]:
        print('ERR', e)


if __name__ == '__main__':
    main()
