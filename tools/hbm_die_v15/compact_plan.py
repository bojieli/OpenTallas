#!/usr/bin/env python3
"""HBM v15 compact die plan (owner 2026-10-15 12:05: 660 mm2 compact option; grow only on measured GRT congestion or
area misfit).  T_band2-style coherent groups rebuilt with MEASURED block areas (Codex 0bd + H-ELEM-B + H-DIE synth):

  per quadrant (SW frame; SE = x-mirror, NW/NE = y-mirror):
    PHY + PC row on the die edge, 2 x 4 SM block (6609.6 x 1712.08 frames) with a 1.8 mm VM band between SM rows 2/3;
    the VM band holds 4 bank-pair GROUPS  [bank pair (2 VM banks + LG chain) | HC shell | SFU port group] + SU slice G
    (SU slice G sits AT bank pair {2G,2G+1}: every fixed-return LG link stays inside its group), the VM hub column
    (hub >= 1.1 mm per the adoption condition, DMA back, IDX operand leaf on SW), the SU core (RF replica + reducer)
    and the quadrant COLL engine at the centre end of the band (rings + SerDes endpoints are in the centre column).
  centre column: SerDes + endpoints on the S and N shorelines, the 4 IDX scorer clusters (512 CLOSED hslices each,
    3008.88 x 3840.48 rotated) stacked SW, SE | glue | NE, NW so each stack's keys enter from its own die half,
    IDX query/selector/link glue in the middle; 0.93 mm routing channels either side of the column.
Areas (um): SU slice 1330 x 1780 (Codex 0bd lower bound 34.75 mm2 leaf outlines / 16 slices + 15 % RF/control/
channels, H-ELEM-B per-slice pins ~3.46 k), SU core 250 x 1780, SFU group 0.40 mm2 (quadrant macro floor 0.838 mm2
x 1.25 halo + logic), HC shell 500 x 500 (GEO-H combined-shell request), VM hub 1100 x 1100, COLL 963.36 x 721.44
(v15 grant), DMA back 432 x 360.72, IDX scorer 3840.48 x 3008.88.

    compact_plan.py --area 660 --out DIR [--graph G]      -> DIR/compact.P.json, compact.graph.json, compact.metrics.json

Scored with tools/hbm_globalfp.py `score` (same objective/cut model as GLOBAL-FP-H, die outline patched) and pinned with
tools/hbm_globalfp_pins.py so tools/hbm_die_v15/grants.py can consume the result exactly like T_band2.
"""
import argparse, copy, json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_globalfp as F  # noqa: E402

GAP = 20.0
SMW, SMH = 6609.6, 1712.08
BAND = 1800.0
SU_W, SU_H = 1250.0, 1780.0
CORE_W = 250.0
HC = 500.0
SFU_A = 400000.0
SFU_DIM = dict(core_h=1936.44, store_w=763.56, store_h=524.88, store_yoff=None)
HUB = 1100.0
COLL_W, COLL_H = 963.36, 721.44
DBK_W, DBK_H = 432.0, 360.72
SC_W, SC_H = 3008.88, 3840.48          # IDX scorer, rotated (w x h)
COLUMN_W = 3100.0
CHANNEL = 930.0
EDGE = 120.0
SM_PAIR_GAP = 0.0                    # d4f r4: extra gap inside each SM pair (XQL pair-store stack)
SUCX = (216.0, 194.4)                 # d4f r2: measured SYNTH cxport 264.6 square -> --sucx 270 270
SC_GAP = 100.0                         # relay row between the two scorers of a die half (cross-column relay homes)


def build(G0, area_mm2, channel=CHANNEL, band=None, hub_w=0.0, su_w=None, su_h=None, smw=None, smh=None, carry=False, layout='v5', core_at=4, sfu_at_hub=False, mirror_east=False, sfu_at_group=None, core_w=None, core_h=None, core_column_w=None, sfu_store_side=False, hc_eng_mm2=None, hc_links_v16=False, hc_x_beats=1, hc_client_inner=False, sm_columns=None, band_low=False, sm_portrait=False, qw_extra=0.0, pocket=False, sfucore_w=763.56, pocket_core_up=False, slim_column=False, sm_rows='abcd', centre_strip=0.0, sm_col_real=False, half_die=False, full_core=False, serdes=0, core_channel=None, sm_band_channel=None, fill='a', pc_h=399.6):
    """v6 (H-DIE-V6PLAN 10-16, OWNER 02:15 die may grow): su_w/su_h = SU slice outline (default 1250 x 1780), smw/smh = SM
    slot (default 6609.6 x 1712.08), carry = also place the v5 grants that are not graph nodes (sfucore_<q> 763.56 x
    1936.44 after the SU core; DMA back at its granted 511.92 width, shifted 79.92 um west as hb_dbk_<q>).  Defaults
    reproduce compact660_v5 exactly."""
    BAND = band or globals()['BAND']
    SU_W = su_w or globals()['SU_W']; SU_H = su_h or globals()['SU_H']
    SMW = smw or globals()['SMW']; SMH = smh or globals()['SMH']
    core_width=core_w or CORE_W; core_height=core_h or SU_H
    G = copy.deepcopy(G0)
    N = G['nodes']
    P = {}
    qw = ((4 * SMW + 3 * GAP) if sm_portrait else (2 * SMW + GAP)) + qw_extra
    W = EDGE + qw + channel + COLUMN_W + channel + qw + EDGE
    H = area_mm2 * 1e6 / W
    # one quadrant's vertical stack (SW frame)
    y_pc = 21.6 + 1177.2 + 20.0
    y_a = y_pc + pc_h + 20.0
    y_b = y_a + SMH + GAP
    y_band = y_b + SMH + GAP
    y_c = y_band + BAND + GAP
    y_d = y_c + SMH + GAP
    top = y_d + SMH
    if sm_portrait:
        # H-DIE d4c (coordinator 10-16 21:40, owner (b)): portrait 2-row SM tile (~2782 x 3698), each SM group ONE row of
        # 4 per quadrant: lower row on the PC strip, VM band, upper row; every SM has a face on the band (no enclosed row)
        y_band = y_a + SMH + GAP
        y_c = y_band + BAND + GAP
        top = y_c + SMH
    if sm_columns is not None:
        # H-DIE-V790 10-16 (OWNER 07:30 SM<->HBM hops): the 8 SMs of a quadrant as COLUMNS directly over the PC row
        # (same slot area: 8 x (CW + GAP) = the two-SM row width, CH = SMW*SMH/CW), a sm_columns-um chain channel between
        # the PC row and the column bottoms, the VM band on top of the columns; the N half mirrors, so the S and N bands
        # meet at the die centre.  SM k sits over PC k: every SM<->HBM chain stays in the channel (no SM row crossing).
        CW = round((2 * SMW + GAP - 7 * GAP) / 8, 3)
        CH = round(SMW * SMH / CW, 3)
        if sm_col_real:   # OWNER 10-16 half die: the real rp4e single-row frame rotated R90 (SM_HBM face to the PC row, xw to the band)
            CW, CH = SMH, SMW
        y_a = y_pc + pc_h + sm_columns
        y_band = y_a + CH + (sm_band_channel if sm_band_channel is not None else GAP)
        top = y_band + BAND
        if band_low:   # option 4: band between the PC row and the SM columns (hub/COLL near the PC row and endpoints)
            y_band = y_pc + pc_h + sm_columns
            y_a = y_band + BAND + GAP
            top = y_a + CH
    if sm_rows != 'abcd':
        # OWNER 10-16 ~19:15 (more dies, fewer SMs per die): keep only the SM rows in sm_rows (a = enclosed row on the PC
        # strip, b = band-side lower row, c = band-side upper row, d = enclosed row at the die centre); kept rows close up
        # (a dropped: row b sits on the PC strip; d dropped: the half ends at row c)
        y = y_a; ry = {}
        for r_ in 'ab':
            if r_ in sm_rows:
                ry[r_] = y; y += SMH + GAP
        y_band = y; y = y_band + BAND + GAP
        for r_ in 'cd':
            if r_ in sm_rows:
                ry[r_] = y; y += SMH + GAP
        top = y - GAP
        y_a, y_b, y_c, y_d = (ry.get(r_) for r_ in 'abcd')
    if half_die:
        if full_core:      # HBM-ARRAY 10-16: full core on the 16-SM die -> a second band row per half (the E quadrant's band)
            top += BAND + (core_channel if core_channel is not None else GAP)
        H = 2 * top + GAP + centre_strip
    if 2 * top + GAP + centre_strip > H:
        raise SystemExit(f'area {area_mm2} mm2 too small: H {H:.0f} < {2 * top + GAP + centre_strip:.0f}')

    def setn(i, w, h, src):
        if i not in N:
            N[i] = dict(id=i, kind=src.split(':')[0], w=w, h=h, area_mm2=w * h / 1e6, area_src='measured', provenance=src)
        else:
            N[i] = dict(N[i], w=w, h=h, area_mm2=round(w * h / 1e6, 4), area_src='measured (H-DIE compact plan)', provenance=src)

    def put(i, x, y, q):
        w, h = N[i]['w'], N[i]['h']
        if q in ('SE', 'NE'):
            x = W - x - w
        if q in ('NW', 'NE'):
            y = H - y - h
        P[i] = dict(x=round(x, 3), y=round(y, 3), w=w, h=h, orient='R0')

    def shift(i, q, dx, dy):
        b = P[i]
        P[i] = dict(b, x=round(b['x'] + (-dx if q in ('SE', 'NE') else dx), 3), y=round(b['y'] + (-dy if q in ('NW', 'NE') else dy), 3))

    def core_stack(q, x):
        """v6b quarter core (H-DIE 0300/0330 10-16), SW frame, x = west edge: SU quarter core (full band height) | 21.6 |
        cij_<q> (COLL inject/IDX join leaf 43.2 x 138.24, centred on the COLL west face) | 21.6 | COLL (band bottom);
        on the COLL: sucx_<q> (SU cross-port 216 x 194.4, abuts the SU core east face and the COLL north face), the DMA
        back (granted 511.92 x 360.72, right-aligned on the COLL), the IDX operand leaf (SW) over the DMA back; then the
        granted SFU core sfucore_<q> 763.56 x 1936.44 with sfus_<q> (SU SFU store 763.56 x 524.88 = 0.40 mm2) abutting
        its north face (0 relays).  Returns the east edge + 21.6."""
        setn(f'sucore_{q}', core_width, core_height, 'SU:ot_hbm_su_static_qcore RF replica + reducer (H-ELEM-B); native compact gate pending')
        put(f'sucore_{q}', x, y_band + SU_H-core_height, q)
        x += (core_column_w or core_width) + 21.6
        setn(f'cij_{q}', 43.2, 138.24, 'COLL inject/IDX join leaf ot_hgi_coll_inj_idx_join (H-NETLIST)')
        put(f'cij_{q}', x, y_band + GAP + (COLL_H - 138.24) / 2, q)
        x += 43.2 + 21.6
        xc = x
        setn(f'coll_{q}', COLL_W, COLL_H, 'COLL v15 grant')
        put(f'coll_{q}', xc, y_band + GAP, q)
        yo = y_band + GAP + COLL_H + 21.6
        setn(f'sucx_{q}', SUCX[0], SUCX[1], 'SU cross-port ot_hbm_su_static_cxport (~0.04 mm2, H-NETLIST suport)')
        put(f'sucx_{q}', xc - 43.2 - 21.6 - 21.6 + 21.6, yo, q)       # west edge = sucore east edge + 21.6
        dw = 511.92 if carry else DBK_W
        setn(f'dbk_{q}', dw, DBK_H, 'DMA back (vp4 grant 2330 width when carried)')
        put(f'dbk_{q}', xc + COLL_W - dw, yo, q)
        if q == 'SW':
            setn('idx_op', 360.72, 317.52, 'IDX:ot_hbm_idx_vm_query_static grant')
            put('idx_op', xc + COLL_W - 360.72, yo + DBK_H + 21.6, q)
        x = xc + COLL_W + 21.6
        return sfu_stack(q, x) if not sfu_at_hub and sfu_at_group is None else x

    def sfu_stack(q, x):
        if carry:
            # H-DIE 0600 10-16: SFU_DIM overrides (H-SU sfucore_sizing_0600: measured core does not fit sfucore_w x 1936.44)
            ch, sw_, sh_, syo = SFU_DIM['core_h'], SFU_DIM['store_w'], SFU_DIM['store_h'], SFU_DIM['store_yoff']
            syo = (21.77 + ch + 21.6) if syo is None else syo
            setn(f'sfucore_{q}', sfucore_w, ch, 'SFU core grant sfucore_<q> (H-SU accepted 10-16)')
            put(f'sfucore_{q}', x, y_band + 21.77, q)
            setn(f'sfus_{q}', sw_, sh_, 'SU SFU store ot_hbm_su_static_sfustore (abuts sfucore, 0 relays)')
            put(f'sfus_{q}', x + (sfucore_w + 21.6 if sfu_store_side else 0), y_band + syo, q)
            assert syo + sh_ <= BAND - 21.6 + 1e-6, (q, 'band too short for sfus')
            assert sfu_store_side or 21.77 + ch + 21.6 <= syo + 1e-6, (q, 'sfus overlaps sfucore')
            assert 21.77 + ch <= BAND - 21.6 + 1e-6, (q, 'band too short for sfucore')
            x += sfucore_w + 21.6
        return x

    pocket_w = {}
    for q in F.QS:
        # PHY + PC row
        put(f'phy_{q}', 1455.84, 21.6, q)
        pcs = sorted([k for k in N if k.startswith(f'pc_{q}')])
        if pc_h != 399.6:   # d4f (H-DIE-B d4c finding / d4b --pc-strip 237.6): PC controller leaves + service groups need a taller PC band
            for p_ in pcs:
                N[p_] = dict(N[p_], h=pc_h, area_mm2=round(N[p_]['w'] * pc_h / 1e6, 4))
        for k, p in enumerate(pcs):
            put(p, 1457.8 + k * (N[p]['w'] + GAP), y_pc, q)
        sms = sorted([k for k in N if k.startswith(f'sm_{q}')], key=lambda s: int(s[len(f'sm_{q}'):]))
        rows = [y_a, y_b, y_c, y_d]
        if sm_rows != 'abcd':
            rows = [r_ for r_ in rows if r_ is not None]
            keep = 2 * len(rows)
            drop = sms[keep:] + [f'pc_{q}{k}' for k in range(keep, 8)]
            for d_ in drop:
                N.pop(d_, None); P.pop(d_, None)
            G['links'] = [l for l in G['links'] if l['src'] not in drop and l['dst'] not in drop]
            sms = sms[:keep]
            pcs = [p for p in pcs if p not in drop]
        for k, s in enumerate(sms):
            if sm_columns is not None:
                setn(s, CW, CH, f'SM column slot {CW} x {CH} (same area as {SMW} x {SMH}; H-SM 4x4-tile column, not built)')
                # d4f r4 (H-DIE 10-17): XQL pair store p (SMs 2p, 2p+1) lives in a widened gap between its two SM columns
                put(s, EDGE + k * (CW + GAP) + ((k + 1) // 2) * SM_PAIR_GAP, y_a, q)
                continue
            if smw or smh:
                setn(s, SMW, SMH, f'SM slot v6 {SMW} x {SMH} (H-SM real single-row body + front)')
            if sm_portrait:
                put(s, EDGE + (k % 4) * (SMW + GAP), (y_a if k < 4 else y_c), q)
                continue
            put(s, EDGE + (k % 2) * (SMW + GAP), rows[k // 2], q)
        # VM band
        x = EDGE
        banks = sorted([k for k in N if k.startswith(f'vmb_{q}')], key=lambda s: int(s[len(f'vmb_{q}'):]))
        su = sorted([k for k in N if k.startswith(f'su_{q}')])
        sfu = sorted([k for k in N if k.startswith(f'sfu_{q}')])
        hc = sorted([k for k in N if k.startswith(f'hc_{q}')])
        for g in range(4):
            if layout == 'col' and g == sfu_at_group:
                x=sfu_stack(q,x)
            if layout == 'col' and g == core_at and core_at < 4:
                x = core_stack(q, x)
            bw = N[banks[2 * g]]['w']
            bh = N[banks[2 * g]]['h']
            if layout == 'col':
                # v6 'col' group (H-DIE-V6PLAN): bank pair stacked at the band's SM side, HC shell | SFU group side by
                # side on top of the pair (both abut bank 1, <= 385 um from bank 0), QUANT (NW) over the HC; the SU
                # slice takes the full band height to the right, so the band grows by SU area / SU_W only
                cw = max(bw, 2 * HC + GAP)
                if q == 'NW':   # v6b: QUANT beside its bank pair (QUANT_VM 0 stages), not over the HC shell
                    cw = max(cw, bw + GAP + 245)
                mir = mirror_east and core_at < 4 and g >= core_at
                if mir:         # east of the quarter core: SU slice first (its core face abuts the core), then its column
                    setn(su[g], SU_W, SU_H, 'SU slice v6 (H-SU 77 mm2 at 60 % util: 4.8 mm2 per port group)')
                    put(su[g], x, y_band, q)
                    x += SU_W + GAP
                put(banks[2 * g], x, y_band, q)
                put(banks[2 * g + 1], x, y_band + bh + GAP, q)
                yh = y_band + 2 * (bh + GAP)
                setn(hc[g], HC, HC, 'HC combined shell 500 x 500 (GEO-H)')
                put(hc[g], x, yh, q)
                sh = round(SFU_A / HC, 3)
                setn(sfu[g], HC, sh, 'SFU port group 0.40 mm2 (quadrant macro floor 0.838 mm2 x1.25 + logic, Codex 0bd)')
                put(sfu[g], x + HC + GAP, yh, q)
                top_c = yh + sh
                if q == 'NW':
                    put(f'quant_NW{g}', x + bw + GAP, y_band + (2 * bh + GAP - 245) / 2, q)
                assert top_c <= y_band + BAND + 1e-6, (q, g, 'col group taller than band', top_c - y_band)
                x += cw + GAP
                if not mir:
                    setn(su[g], SU_W, SU_H, 'SU slice v6 (H-SU 77 mm2 at 60 % util: 4.8 mm2 per port group)')
                    put(su[g], x, y_band, q)
                    x += SU_W + GAP
                continue
            # left column (500 wide): HC shell / QUANT (NW) / SFU group, each within 500 um of BOTH banks of the pair
            setn(hc[g], HC, HC, 'HC combined shell 500 x 500 (GEO-H)')
            put(hc[g], x, y_band, q)
            yq = y_band + HC + GAP
            if q == 'NW':
                put(f'quant_NW{g}', x, yq, q)
                yq += 245 + GAP
            sh = round(SFU_A / HC, 3)
            setn(sfu[g], HC, sh, 'SFU port group 0.40 mm2 (quadrant macro floor 0.838 mm2 x1.25 + logic, Codex 0bd)')
            put(sfu[g], x, yq, q)
            assert yq + sh <= y_band + BAND + 1e-6, (q, g, yq + sh - y_band)
            x += HC + GAP
            yb = y_band + 400.0
            put(banks[2 * g], x, yb, q)
            put(banks[2 * g + 1], x, yb + bh + GAP, q)
            x += bw + GAP
            setn(su[g], SU_W, SU_H, 'SU slice (Codex 0bd 34.75 mm2 leaf lower bound /16, +2.4 %)')
            put(su[g], x, y_band, q)
            x += SU_W + GAP
        if layout != 'col':
            setn(f'sucore_{q}', CORE_W, SU_H, 'SU:ot_hbm_su_static_qcore RF replica + reducer (H-ELEM-B)')
            put(f'sucore_{q}', x, y_band, q)
            x += CORE_W + GAP
        if carry and layout != 'col':   # granted SFU core (main 818f005b6): band gap between the SU core and the COLL/DMA-back stack
            x += 1.6
            setn(f'sfucore_{q}', 763.56, 1936.44, 'SFU core grant sfucore_<q> (H-SU accepted 10-16)')
            put(f'sfucore_{q}', x, y_band + 21.77, q)
            x += 763.56
        if hub_w and layout == 'col':
            hh = BAND - 2 * GAP
            hx = EDGE + qw - hub_w
            if core_at >= 4 and not pocket:
                x = core_stack(q, x)
            if pocket:
                # d4c (coordinator 10-16 22:50, structural fit): the band row is wider than the portrait SM row, so the
                # quarter core/COLL stack goes to the SM-row pocket at the quadrant inner end, UPPER SM-row level, and the
                # SFU store to the pocket at the LOWER SM-row level; the hub stays at band level at the inner edge
                px = EDGE + 4 * SMW + 4 * GAP
                before = set(P)
                xe = core_stack(q, px)
                for i in set(P) - before:
                    shift(i, q, 0.0, (y_c - y_band) if pocket_core_up else (y_a - y_band))
                for i in ('idx_op',) if q == 'SW' else ():
                    if i in P:
                        pass
                assert xe <= EDGE + qw - hub_w - GAP + 1e-6 or True
                pocket_w[q] = xe - px
                if f'sfus_{q}' in P:
                    b = P[f'sfus_{q}']
                    # move sfus to (px, y_a + GAP) in SW frame
                    bx = b['x'] if q in ('SW', 'NW') else W - b['x'] - b['w']
                    by = b['y'] if q in ('SW', 'SE') else H - b['y'] - b['h']
                    shift(f'sfus_{q}', q, px - bx, ((y_a if pocket_core_up else y_c) + GAP) - by)
            if sfu_at_hub and sfu_at_group is None:      # SFU core + store at the inner end beside the hub (COLL faces slices on both sides)
                x = sfu_stack(q, x)
                put(f'sfucore_{q}', hx - 21.6 - 763.56, y_band + 21.77, q)
                put(f'sfus_{q}', hx - 21.6 - 763.56, y_band + 21.77 + 1936.44 + 21.6, q)
            slack = hx - x
            assert slack >= -1e-6, (q, 'band too long for the v6b core', slack)
            setn(f'vmh_{q}', hub_w, hh, f'VM hub reshaped tall {hub_w:.0f} x {hh:.0f}')
            put(f'vmh_{q}', hx, y_band + GAP, q)
            if hc_client_inner:
                # H-DIE-V790 10-16 (H-DIE decision v3): quadrant HC client hc_<q> (ot_hbm_hc_q_static, x_wave source) in the
                # inner-end pocket: west of the calendar column (220.32 + 2 x 21.6 + 2.16 from the hub), above the
                # COLL / DMA back / IDX operand stack.  432 x 432 candidate (pin-limited: ~7.6 kb incl. 4-beat x_wave)
                setn(f'hc_{q}', 432.0, 432.0, 'HC_Q:ot_hbm_hc_q_static quadrant HC client (pin-limited 432 x 432 candidate, synth pending)')
                put(f'hc_{q}', hx - 21.6 - 220.32 - 21.6 - 2.16 - 432.0, y_band + GAP + COLL_H + 21.6 + 360.72 + 21.6 + 317.52 + 21.6, q)
            if pocket and f'hc_{q}' in P:      # quadrant HC client to the pocket, lower SM-row level beside the SFU store
                b = P[f'hc_{q}']
                bx = b['x'] if q in ('SW', 'NW') else W - b['x'] - b['w']
                by = b['y'] if q in ('SW', 'SE') else H - b['y'] - b['h']
                shift(f'hc_{q}', q, (EDGE + 4 * SMW + 4 * GAP + 1020 + GAP) - bx, ((y_a if pocket_core_up else y_c) + GAP) - by)
            x = hx + hub_w
        elif hub_w:
            # TALL HUB (H-DIE r2 cut fix): hub reshaped to hub_w x (BAND - 2 GAP) at the quadrant's inner edge, so its
            # band-facing (W) and channel-facing (E) faces are ~1.8 mm long (pin density and the face cut both drop by
            # 1.1/1.76); COLL, DMA back and the IDX operand leaf stack in one column west of the hub.
            hh = BAND - 2 * GAP
            hx = EDGE + qw - hub_w
            cx = hx - GAP - COLL_W
            slack = cx - GAP - x
            assert slack >= -1e-6, (q, 'band too long for the tall hub', slack)
            setn(f'coll_{q}', COLL_W, COLL_H, 'COLL v15 grant')
            put(f'coll_{q}', cx, y_band + GAP, q)
            if carry:   # granted vp4 DMA parent home 511.92 x 360.72, 79.92 um west of the COLL column (hardening_grants_2330)
                setn(f'dbk_{q}', 511.92, DBK_H, 'DMA:ot_hgi_dma_back_static_vp4_banks grant 2330')
                put(f'dbk_{q}', cx - 79.92, y_band + GAP + COLL_H + GAP, q)
                slack = cx - 79.92 - 21.6 - x
                assert slack >= -1e-6, (q, 'band too long for sfucore + granted DMA back', slack)
            else:
                setn(f'dbk_{q}', DBK_W, DBK_H, 'DMA:ot_hgi_dma_back_static v15 grant (no T_band2 block)')
                put(f'dbk_{q}', cx, y_band + GAP + COLL_H + GAP, q)
            if q == 'SW':
                setn('idx_op', 360.72, 317.52, 'IDX:ot_hbm_idx_vm_query_static grant')
                put('idx_op', cx + DBK_W + GAP, y_band + GAP + COLL_H + GAP, q)
            setn(f'vmh_{q}', hub_w, hh, f'VM hub reshaped tall {hub_w:.0f} x {hh:.0f} (area >= 1.1 mm square; faces >= 1.1 mm on W/E)')
            put(f'vmh_{q}', hx, y_band + GAP, q)
            x = hx + hub_w
        else:
            # COLL then the VM hub column at the CENTRE end of the band: VM ring / COLL ring / COLL endpoint traffic
            # enters from the centre channel without running along the band (worst-cut driver in the first compact try)
            setn(f'coll_{q}', COLL_W, COLL_H, 'COLL v15 grant')
            put(f'coll_{q}', x, y_band + (BAND - COLL_H) / 2, q)
            x += COLL_W + GAP
            setn(f'vmh_{q}', HUB, HUB, 'VM hub >= 1.1 mm (T_band2 adoption condition)')
            put(f'vmh_{q}', x, y_band, q)
            setn(f'dbk_{q}', DBK_W, DBK_H, 'DMA:ot_hgi_dma_back_static v15 grant (no T_band2 block)')
            put(f'dbk_{q}', x, y_band + HUB + GAP, q)
            if q == 'SW':
                setn('idx_op', 360.72, 317.52, 'IDX:ot_hbm_idx_vm_query_static grant')
                put('idx_op', x + DBK_W + GAP, y_band + HUB + GAP, q)
            x += HUB + GAP
        assert x <= EDGE + qw + 1e-6, (q, x, EDGE + qw)
    # centre column
    c0 = EDGE + qw + channel
    # HC engine (estimate 1.0 mm2, single NE engine) in the NE-side channel at the NE band height
    setn('hc_eng', channel - 2 * GAP, round(1.0e6 / (channel - 2 * GAP), 3), 'HC_ENGINE 1.0 mm2 estimate in the NE channel')
    P['hc_eng'] = dict(x=c0 + COLUMN_W + GAP, y=H - y_band - N['hc_eng']['h'], w=N['hc_eng']['w'], h=N['hc_eng']['h'], orient='R0')
    for side, n, q0 in (('S', 5, 'SW'), ('N', 4, 'NW')):
        lks = sorted([k for k in N if k.startswith(f'lk_{side}')])
        eps = sorted([k for k in N if k.startswith(f'ep_{side}')])
        for k, l in enumerate(lks):
            put(l, c0 + k * (250.056 + GAP), 20.0, q0)
        ex = c0 + len(lks) * (250.056 + GAP)
        for k, e in enumerate(eps):
            put(e, ex + (k % 2) * (434.72 + GAP), 20.0 + (k // 2) * (515.2 + GAP), q0)
    ys = 20.0 + 2250.216 + GAP
    for i, sc in enumerate(('idx_s0', 'idx_s1')):       # SW, SE stacks from the south half
        setn(sc, SC_W, SC_H, 'IDX scorer: 512 CLOSED hslices 172.8x103.68 + glue (v15 grant, rotated)')
        P[sc] = dict(x=c0 + (COLUMN_W - SC_W) / 2, y=ys + i * (SC_H + SC_GAP), w=SC_W, h=SC_H, orient='R90')
    yg = ys + 2 * SC_H + SC_GAP + GAP
    if layout == 'col':   # v6: taller die -> N scorers mirror the S ones from the top (relay row inside the N SU core), glue centred
        yg = round(H / 2 - 449.28 / 2, 3)
    glue = [('idx_q', 449.28, 449.28), ('idx_sel', 1164.24, 317.52), ('idx_link', 745.2, 317.52)]
    gx = c0
    for g, w, h in glue:
        setn(g, w, h, 'IDX glue (v15 grant, measured synth)')
        P[g] = dict(x=gx, y=yg, w=w, h=h, orient='R0')
        gx += w + GAP
    yn = yg + 449.28 + GAP
    if layout == 'col':
        yn = round(H - ys - 2 * SC_H - SC_GAP, 3) - 0.001
    if hc_eng_mm2:
        # H-DIE-V790 10-16 (H-NETLIST main 406a2d5f9: hc_eng = ot_hbm_hc_eng_static, ~9.5 mm2): the engine takes the
        # centre-column void between the S and N scorer stacks, full column width, with a SC_GAP relay row (RF cross
        # corridor) against idx_s1 and one against idx_s3; the IDX glue row moves above the engine and the two programme
        # collars hc_eng_tgt / hc_tbl_tgt (ot_static_program_target, candidate 86.4 x 64.8) close the glue row on the E.
        assert layout == 'col', 'centre hc_eng needs the col layout'
        s1_top = ys + 2 * SC_H + SC_GAP
        hw = COLUMN_W
        hh = round(hc_eng_mm2 * 1e6 / hw, 3)
        setn('hc_eng', hw, hh, 'HC:ot_hbm_hc_eng_static (H-NETLIST 406a2d5f9, ~9.5 mm2 model hbm_hc_eng_0030) centre-column void')
        P['hc_eng'] = dict(x=c0, y=round(s1_top + SC_GAP, 3), w=hw, h=hh, orient='R0')
        yg = round(s1_top + SC_GAP + hh + GAP, 3)
        if yg + 449.28 + SC_GAP > yn + 1e-6:
            raise SystemExit(f'centre void too short for hc_eng {hh:.0f} + glue: {yg + 449.28 + SC_GAP:.0f} > {yn:.0f}')
        for g, _, _ in glue:
            P[g]['y'] = yg
        for k, t in enumerate(('hc_eng_tgt', 'hc_tbl_tgt')):
            setn(t, 86.4, 64.8, 'PROG:ot_static_program_target collar (H-NETLIST hceng, TARGET 164/165); candidate outline, synth pending')
            P[t] = dict(x=round(c0 + COLUMN_W - 86.4, 3), y=round(yg + k * (64.8 + 21.6), 3), w=86.4, h=64.8, orient='R0')
    if hc_client_inner:
        # v16 hc_<q> <-> group leaves hc_<q><k> (k = 0..3): lg_rq 34 + lg_wq 562 = 596 b out, c_rr 514 + c_w_done 2 = 516 b back;
        # the old estimated HC_CORE links into hc_<q>0 and the HC_ENG source move to the client
        old = [l for l in G['links'] if l['cls'] == 'HC_CORE']
        tmpl = old[0] if old else None
        G['links'] = [l for l in G['links'] if l['cls'] != 'HC_CORE']
        for q in ('SW', 'SE', 'NW', 'NE'):
            for k in range(4):
                for src, dst, b, why in ((f'hc_{q}', f'hc_{q}{k}', 596, 'lg_rq 34 + lg_wq 562'), (f'hc_{q}{k}', f'hc_{q}', 516, 'c_rr 514 + c_w_done 2')):
                    G['links'].append(dict(tmpl, id=f'{src}>{dst}:HC_CORE', src=src, dst=dst, bits=b, fixed_return=False, rule=None,
                                           provenance=f'v16 ot_hbm_hc_q_static <-> ot_hgi_sfu_lg_pair_leaf: {why} (H-NETLIST 406a2d5f9)'))
        for l in G['links']:
            if l['cls'] == 'HC_ENG' and l['src'].startswith('hc_') and l['src'] != 'hc_eng':
                q = l['src'][3:5]; l.update(src=f'hc_{q}', id=f"hc_{q}>hc_eng:HC_ENG")
    if hc_links_v16:
        # H-NETLIST v16 edges hceng_30..: per quadrant x_wave_v 1 + x_wave_word 10 + x_wave 8192 + gathered_mix (v 1, row 5,
        # pos 3, data 32) = 8,244 b to the engine every 4 edges; result_v 1 + pos 3 + result 768 = 772 b back
        for l in list(G['links']):
            if l['dst'] == 'hc_eng' and l['cls'] == 'HC_ENG':
                # hc_x_beats > 1: UNADOPTED what-if, x_wave serialised over that many of its 4 edges (needs an RTL change)
                l.update(bits=8192 // hc_x_beats + 52, provenance=f'v16 hceng_30..: x_wave 8192/{hc_x_beats} beat(s) + word/valid 11 + gathered_mix 41 (H-NETLIST 406a2d5f9)')
                G['links'].append(dict(l, id=f"hc_eng>{l['src']}:HC_ENG", src='hc_eng', dst=l['src'], bits=772,
                                       bytes_per_token={k: v * 772 / 8244 for k, v in l['bytes_per_token'].items()},
                                       provenance='v16: result_v 1 + position 3 + result 768 (bytes scaled from the forward link; estimate)'))
    for i, sc in enumerate(('idx_s3', 'idx_s2')):       # NE, NW from the north half
        setn(sc, SC_W, SC_H, 'IDX scorer (v15 grant, rotated)')
        P[sc] = dict(x=c0 + (COLUMN_W - SC_W) / 2, y=yn + i * (SC_H + SC_GAP), w=SC_W, h=SC_H, orient='R90')
    assert yn + 2 * SC_H + SC_GAP + GAP <= H - 20 - 2250.216 + 1e-6, ('centre column too tall', yn + 2 * SC_H + 2 * GAP, H - 2270)
    if slim_column:
        # d4c (H-DIE 10-16 23:55): 4 x rp4e SM (7,756 um) per die row leaves only a slim centre column. The v15 IDX
        # scorer/glue nodes are not in the v16 contract (ghosts) -> removed; lk/ep restacked inside the column width;
        # hc_eng re-aspected to the column width (same area), centred between the S and N lk/ep stacks.
        ghosts = [k for k in list(P) if k.startswith('idx_')]
        for k in ghosts:
            P.pop(k, None); N.pop(k, None)
        G['links'] = [l for l in G['links'] if l['src'] not in ghosts and l['dst'] not in ghosts]
        c0 = EDGE + qw + channel
        for side, q0 in (('S', 'SW'), ('N', 'NW')):
            lks = sorted([k for k in N if k.startswith(f'lk_{side}')])
            eps = sorted([k for k in N if k.startswith(f'ep_{side}')])
            per = max(1, int((COLUMN_W + GAP) // (250.056 + GAP)))
            for k, l in enumerate(lks):
                put(l, c0 + (k % per) * (250.056 + GAP), 20.0 + (k // per) * (2250.216 + GAP), q0)
            y0 = 20.0 + ((len(lks) + per - 1) // per) * (2250.216 + GAP)
            per = max(1, int((COLUMN_W + GAP) // (434.72 + GAP)))
            for k, e in enumerate(eps):
                put(e, c0 + (k % per) * (434.72 + GAP), y0 + (k // per) * (515.2 + GAP), q0)
        if 'hc_eng' in N:
            hw = COLUMN_W; hh = round((hc_eng_mm2 or 9.5) * 1e6 / hw, 3)
            N['hc_eng'] = dict(N['hc_eng'], w=hw, h=hh)
            P['hc_eng'] = dict(x=c0, y=round(H / 2 - hh / 2, 3), w=hw, h=hh, orient='R0')
            if centre_strip:
                # OWNER 10-16 (hc_eng stick rejected): normal-aspect engine centred in the die-centre strip between the
                # S and N halves (strip = centre_strip um incl. GAP each side)
                hh = round(centre_strip - 2 * GAP, 3); hw = round((hc_eng_mm2 or 9.5) * 1e6 / hh, 3)
                N['hc_eng'] = dict(N['hc_eng'], w=hw, h=hh)
                P['hc_eng'] = dict(x=round(W / 2 - hw / 2, 3), y=round(H / 2 - hh / 2, 3), w=hw, h=hh, orient='R0')
            for k, t in enumerate(('hc_eng_tgt', 'hc_tbl_tgt')):
                if t in P:
                    P[t] = dict(P[t], x=round(P['hc_eng']['x'] + P['hc_eng']['w'] + GAP, 3) if centre_strip else round(c0 + k * (86.4 + GAP), 3),
                                y=round(H / 2 - hh / 2 + k * (64.8 + GAP), 3) if centre_strip else round(H / 2 + hh / 2 + GAP, 3))
    if half_die:
        # OWNER 10-16 refinement (option A): 16 SMs + 2 HBM stacks = the W half (SW, NW quadrants: one PHY on the S and one
        # on the N edge) + the centre column moved to the E die edge; E-half nodes and their links dropped
        Wf = W
        E = [k for k in list(P) if k.endswith(('_SE', '_NE')) or any(f'_{q}' in k and k.split('_')[-1].startswith(q) for q in ('SE', 'NE'))]
        if full_core:
            # HBM-ARRAY 10-16 (TP-192 census): keep the full core (4 COLL engines / delivery lanes, 16 SU slices = 1,024
            # lanes, VM 2^18 words); only SMs, PCs and PHYs halve.  The SE/NE band content is un-mirrored into the W half
            # as a second band row next to the die centre; links to the dropped E SMs/PCs re-target the W ones (k -> k)
            def is_e(k):
                return k in E
            sm_side = [k for k in E if k.startswith(('sm_', 'pc_', 'phy_'))]
            for k in E:
                if k in sm_side or k not in P:
                    continue
                b = P[k]; north = k.split('_')[-1].startswith('NE') or '_NE' in k
                x_ = Wf - b['x'] - b['w']
                cc_ = core_channel if core_channel is not None else GAP
                y_ = b['y'] - (BAND + cc_) if north else b['y'] + (BAND + cc_)
                P[k] = dict(b, x=round(x_, 3), y=round(y_, 3))
            if fill == 'b':     # cross-quadrant fill: the E core's SM-side links re-target the W SM side (k -> k)
                rt = {k: k.replace('_SE', '_SW').replace('_NE', '_NW') for k in sm_side}
                for l in G['links']:
                    l['src'] = rt.get(l['src'], l['src']); l['dst'] = rt.get(l['dst'], l['dst'])
            # fill 'a' (H-NETLIST P1, VMS client-absent): the E hubs have no SM side; their SM-side links are dropped
            E = sm_side
        for k in E:
            P.pop(k, None); N.pop(k, None)
        if serdes:
            # H-DIE 10-16 (H-NETLIST P1): one switch link per COLL engine + host/spare = S0 (SW), S3 (SE), N0 (NW), N2 (NE), S1
            keep = {'S0', 'S3', 'N0', 'N2', 'S1', 'S2', 'N1', 'N3', 'S4'}
            keep = set(['S0', 'S3', 'N0', 'N2', 'S1', 'S2', 'N1', 'N3', 'S4'][:serdes])
            for k in [k for k in list(P) if k.startswith(('lk_', 'ep_')) and k[3:] not in keep]:
                P.pop(k, None); N.pop(k, None)
        G['links'] = [l for l in G['links'] if l['src'] in P and l['dst'] in P]
        W = EDGE + qw + channel + COLUMN_W + EDGE
    return G, P, W, H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--graph', default='results/arch/hbm_globalfp_1015/noatt/graph_sm_npg4.json')
    ap.add_argument('--ref', default='results/arch/hbm_globalfp_1015/noatt/ref_sm.json')
    ap.add_argument('--area', type=float, default=660.0)
    ap.add_argument('--channel', type=float, default=CHANNEL)
    ap.add_argument('--band', type=float, default=BAND, help='VM band height (SM row 2 to row 3 gap) in um')
    ap.add_argument('--hub-w', type=float, default=0.0, help='tall VM hub of this width (0 = 1.1 mm square hub)')
    ap.add_argument('--fit', action='store_true', help='grow --area to the smallest outline that fits (10 mm2 steps of 0.1)')
    ap.add_argument('--edge', type=float, help='die edge margin (default 120 um)')
    ap.add_argument('--column', type=float, help='centre column width (default 3100 um; IDX scorer 3008.88 rotated)')
    ap.add_argument('--su-w', type=float); ap.add_argument('--su-h', type=float)
    ap.add_argument('--smw', type=float); ap.add_argument('--smh', type=float)
    ap.add_argument('--layout', default='v5', choices=('v5', 'col'), help="band group layout ('col' = v6 bank-pair column)")
    ap.add_argument('--mirror-east', action='store_true', help='col layout: groups east of the core put their SU slice first (slice faces the core)')
    ap.add_argument('--sfu-at-hub', action='store_true', help='col layout: SFU core + store beside the hub, not in the core stack')
    ap.add_argument('--sfu-at-group',type=int,choices=range(4),help='col layout: independent SFU core/store inserted before this bank-pair group')
    ap.add_argument('--core-w',type=float);ap.add_argument('--core-h',type=float)
    ap.add_argument('--sfu-store-side',action='store_true',help='unqualified SFU store in side-upper bay, opens north core access')
    ap.add_argument('--core-column-w',type=float,help='compact core horizontal column pitch; upper core may overhang low join with exact overlap checks')
    ap.add_argument('--core-at', type=int, default=4, help="col layout: band groups west of the quarter core (4 = inner end)")
    ap.add_argument('--sfucore-h', type=float, default=1936.44, help='sfucore_<q> height (width 763.56)')
    ap.add_argument('--sfus-wh', nargs=2, type=float, default=[763.56, 524.88], help='sfus_<q> SU SFU store w h')
    ap.add_argument('--sfus-yoff', type=float, help='sfus_<q> y offset from the band bottom (default: on top of sfucore)')
    ap.add_argument('--hc-eng-mm2', type=float, help='col layout: ot_hbm_hc_eng_static of this area in the centre-column void (+ collars)')
    ap.add_argument('--hc-links-v16', action='store_true', help='HC_ENG links at the v16 widths (8,244 b in, 772 b back per quadrant)')
    ap.add_argument('--hc-x-beats', type=int, default=1, choices=(1, 2, 4), help='what-if: x_wave serialised over N of its 4 edges (RTL change, unadopted)')
    ap.add_argument('--hc-client-inner', action='store_true', help='col layout: quadrant HC client hc_<q> at the band inner end + v16 group links')
    ap.add_argument('--sm-columns', type=float, help='SM column layout with this PC-row chain channel (um); see build()')
    ap.add_argument('--band-low', action='store_true', help='with --sm-columns: VM band under the SM columns (next to the PC row)')
    ap.add_argument('--gap', type=float, default=GAP, help='d4c: inter-block channel (um) used everywhere the plan abuts blocks')
    ap.add_argument('--qw-extra', type=float, default=0.0, help='d4c: quadrant width beyond the SM row (band row needs it)')
    ap.add_argument('--slim-column', action='store_true', help='d4c: drop IDX ghosts, restack lk/ep and hc_eng in the --column width')
    ap.add_argument('--pocket', action='store_true', help='d4c: core/COLL stack + SFU store in the SM-row pocket')
    ap.add_argument('--sfucore-w', type=float, default=763.56)
    ap.add_argument('--sm-portrait', action='store_true', help='d4c: 4 SMs per row, one row per group (portrait 2-row tile)')
    ap.add_argument('--carry', action='store_true', help='place the non-graph v5 grants (sfucore, granted DMA back width)')
    ap.add_argument('--sm-rows', default='abcd', help="OWNER 10-16 fewer-SM die: SM rows kept per quadrant (a PC-side enclosed, b/c band-side, d centre enclosed)")
    ap.add_argument('--centre-strip', type=float, default=0.0, help='die-centre strip height (um) between the S and N halves; hc_eng centred in it at normal aspect')
    ap.add_argument('--sm-col-real', action='store_true', help='with --sm-columns: real rp4e frame rotated (CW = smh, CH = smw)')
    ap.add_argument('--half-die', action='store_true', help='OWNER 10-16 option A: W half only (2 stacks, 16 SMs), column at the E edge')
    ap.add_argument('--full-core', action='store_true', help='with --half-die: keep all 4 quadrant cores (2nd band row per half)')
    ap.add_argument('--core-channel', type=float, help='with --full-core: channel between the two band rows of a half (default --gap)')
    ap.add_argument('--sm-band-channel', type=float, help='with --sm-columns: channel between the SM column tops (xw windows) and the band')
    ap.add_argument('--fill', default='a', choices=('a', 'b'), help="--full-core E hubs: a = no SM side (VM ring only), b = cross-quadrant fill")
    ap.add_argument('--pc-h', type=float, default=399.6, help='PC band height (d4b GEN needed 399.6 + 237.6 strip = 637.2)')
    ap.add_argument('--serdes', type=int, default=0, help='with --half-die: keep this many lk/ep pairs (S gets the odd one)')
    ap.add_argument('--sm-pair-gap', type=float, default=0.0, help='d4f r4: extra gap between SM 2p and 2p+1 columns for the XQL pair store')
    ap.add_argument('--sucx', type=float, nargs=2, help='SU cross-port block w h (d4f r2: 270 270)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    global EDGE, COLUMN_W
    if a.edge is not None:
        EDGE = a.edge
    if a.column is not None:
        COLUMN_W = a.column
    globals()['SM_PAIR_GAP'] = a.sm_pair_gap
    if a.sucx:
        globals()['SUCX'] = tuple(a.sucx)
    SFU_DIM.update(core_h=a.sfucore_h, store_w=a.sfus_wh[0], store_h=a.sfus_wh[1], store_yoff=a.sfus_yoff)
    globals()['GAP'] = a.gap
    kw = dict(su_w=a.su_w, su_h=a.su_h, smw=a.smw, smh=a.smh, carry=a.carry, layout=a.layout, core_at=a.core_at, sfu_at_hub=a.sfu_at_hub, mirror_east=a.mirror_east,sfu_at_group=a.sfu_at_group,core_w=a.core_w,core_h=a.core_h,core_column_w=a.core_column_w,sfu_store_side=a.sfu_store_side,hc_eng_mm2=a.hc_eng_mm2,hc_links_v16=a.hc_links_v16,hc_x_beats=a.hc_x_beats,hc_client_inner=a.hc_client_inner,sm_columns=a.sm_columns,band_low=a.band_low,sm_portrait=a.sm_portrait,qw_extra=a.qw_extra,pocket=a.pocket,sfucore_w=a.sfucore_w,slim_column=a.slim_column,sm_rows=a.sm_rows,centre_strip=a.centre_strip,sm_col_real=a.sm_col_real,half_die=a.half_die,full_core=a.full_core,serdes=a.serdes,core_channel=a.core_channel,sm_band_channel=a.sm_band_channel,fill=a.fill,pc_h=a.pc_h)
    G0 = json.loads((ROOT / a.graph).read_text())
    if a.fit:
        area = a.area
        while True:
            try:
                G, P, W, H = build(G0, area, a.channel, a.band, a.hub_w, **kw); break
            except SystemExit:
                area = round(area + 0.1, 1)
    else:
        G, P, W, H = build(G0, a.area, a.channel, a.band, a.hub_w, **kw)
    F.W_DIE, F.H_DIE = W, H
    missing = [i for i in G['nodes'] if i not in P]
    ov = F.overlaps(P)
    out = F.outside(P)
    m = F.score(G, P, json.loads((ROOT / a.ref).read_text()), cut_detail=False)
    placed = sum(r['w'] * r['h'] for r in P.values()) / 1e6
    o = Path(a.out)
    o.mkdir(parents=True, exist_ok=True)
    (o / 'compact.P.json').write_text(json.dumps(P, indent=1))
    (o / 'compact.graph.json').write_text(json.dumps(G, indent=1))
    keep = {k: v for k, v in m.items() if not isinstance(v, (list, dict)) or k in ('worst_cut_where',)}
    rec = dict(die_um=[round(W, 3), round(H, 3)], die_mm2=round(W * H / 1e6, 2), placed_mm2=round(placed, 2),
               density=round(placed * 1e6 / (W * H), 3), unplaced=missing, overlaps=ov[:20], n_overlaps=len(ov),
               outside=out, metrics=keep)
    (o / 'compact.metrics.json').write_text(json.dumps(rec, indent=1))
    print(json.dumps(dict((k, rec[k]) for k in ('die_um', 'die_mm2', 'placed_mm2', 'density', 'n_overlaps', 'unplaced', 'outside'))))
    print(json.dumps(keep)[:1500])


if __name__ == '__main__':
    main()
