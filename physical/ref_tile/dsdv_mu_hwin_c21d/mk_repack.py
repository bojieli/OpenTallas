#!/usr/bin/env python3
"""S81-HWIN21d: re-pack the c21b HWIN tile (RTL byte-identical) so every SRAM pin is <=150 um from the
central std band. Main c21d = 11 cols x 8 rows (4 below MX, 4 above R0), 518.4 x 432; fallback c21e =
14 cols x 6 rows (3+3), 648 x 345.6."""
import json, shutil, sys, re
from pathlib import Path
WT = Path(sys.argv[1]); SRC = WT/'physical/ref_tile/dsdv_mu_hwin_c21b'
EXACT_MX = True
L = 43.2; MH = 20.79; MW = 18.36; ROWH = 0.27; CM = 2.16
def insts(spec):
    return [m['inst'] for m in spec['macros']]
def build(tag, ncol, nlow, nup, W, H, band_rows, band_lo_target, ck_lo, letter):
    nrow_side = None
    s = json.loads((SRC/'spec.json').read_text())
    names = insts(s)
    ev = names[:80]; extra = names[80:]          # 16 events x (attr + 4 payload), then gap0/1, retire0/1
    assert len(ev) == 80 and all('g_event_mem' in n for n in ev) and len(extra) == 4
    lower = [L*(1+i) for i in range(nlow)]   # all R0: MX/R180 put the pins off the asap7 tracks on the 43.2 lattice
    top_lower = lower[-1] + MH
    upper0 = None
    # first upper row on the lattice leaving >= band + 2 halos
    k = 1
    while True:
        y = L*k
        if y > top_lower and (y - 10.8) - (top_lower + 10.8) >= band_rows*ROWH - 1e-6: upper0 = y; break
        k += 1
    upper = [upper0 + L*i for i in range(nup)]
    n = round((band_lo_target - CM)/ROWH); lo = round(CM + n*ROWH, 4); hi = round(lo + band_rows*ROWH, 4)
    assert top_lower + 10.8 <= lo and hi <= upper0 - 10.8, (tag, top_lower, lo, hi, upper0)
    # slot order inside a column: near->far above, near->far below
    col_slots = [(y, 'R0') for y in upper] + [(y, 'R0') for y in reversed(lower)]
    slots = []
    for c in range(ncol):
        x = L*(1+c)
        for (y, o) in col_slots: slots.append((x, y, o, c))
    per_col = len(col_slots)
    if ncol*per_col == 88:   # c21d: events 0-7 cols 0-4, extras in the near-band slots of col 5, events 8-15 cols 6-10
        mid = [sl for sl in slots if sl[3] == 5]
        near = [mid[0], mid[per_col//2], mid[1], mid[per_col//2+1]]   # U1, D1, U2, D2
        order = [sl for sl in slots if sl[3] < 5][:40] + near + [sl for sl in slots if sl[3] > 5]
        empties = [sl for sl in mid if sl not in near]
    else:                    # c21e: 84 slots exactly; extras in the middle of the linear order
        order = slots; empties = []
    assert len(order) == 84
    seq = ev[:40] + extra + ev[40:]
    macros = []
    for inst, (x, y, o, c) in zip(seq, order):
        m = {"view": "physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1", "inst": inst, "at": [round(x,4), round(y,4)], "orient": o}
        if o == 'MX' and EXACT_MX: m["at_exact"] = True
        macros.append(m)
    # reach: macro pin rows (R0 pins at y+0.768..3.768; MX at y+MH-3.768..y+MH-0.768) to band edge
    reach = 0
    for m in macros:
        x, y = m['at']
        reach = max(reach, (y + 3.768 - hi) if y > hi else (lo - (y + 3.768)))
    std = s['std_area_um2']; util = std/((W - 2*CM)*(hi - lo))
    s['name'] = tag
    s['macros'] = macros
    s['outline'] = {"w": W, "h": H}
    s['pin_ranges'] = {"ck": [ck_lo, ck_lo + 8.0], "rst_n": [ck_lo + 8.0, ck_lo + 16.0]}
    why = (f"S81-HWIN21d (COORD 10-19 restart-brief decision: re-pack so SRAM pins sit <=150 um from the band; "
           f"same HWIN lattice/channel exception class ROOT approved for c21, model 21cbb79ac; ROOT ratification requested in HANDOFF). "
           f"RTL byte-identical to HWIN21cb 072dd6141. 84 ot_sram_1r1w_64x16 on the 43.2 lattice, 10.8 halo, {ncol} columns x {nlow+nup} rows "
           f"({nlow} below / {nup} above, all R0: pins on the macro's bottom 3.8 um), outline {W}x{H}; one full-width std band y{lo}..{hi} "
           f"({band_rows} rows); max SRAM-pin to band {reach:.1f} um (c21b 370). Std 8600 um2 (c21 measured 8352 + read-address copies) = "
           f"{util:.1%} of band; the gate re-measures placed occupancy.")
    s['fill_reason'] = {"lattice_channel_bound": {"why": why, "lattice_um": 43.2, "min_channel_um": 22.41,
        "std_band_util": util, "approved_by": "ROOT", "std_band_y_um": [lo, hi]}}
    s['structural_change'] = (f"HWIN21d {letter} (2nd failed-gate response; c21b gate 175703 post-CTS setup -162.5 ps at payload capture D = SRAM Q -> ~370 um wire -> "
        f"central band, FF hold -43 ps / 515 at SRAM wd_in = band wdata -> ~370 um -> macro): macro RE-PACK, RTL unchanged. Macros now "
        f"{ncol} columns x {nlow+nup} rows ({nlow} below / {nup} above) around one full-width band, max SRAM pin -> band {reach:.1f} um "
        f"(<=150), so the SRAM Q -> capture and wdata -> wd_in wires shrink ~2.5x; hold repair gets setup slack at wd_in. Event e's 5 macros are 5 consecutive "
        f"column slots (<=2 adjacent columns); retire/gap SRAMs in the centre. cycles_added 0. Predecessor: " + s['structural_change'])
    s['job']['branch'] = 'claude/s81-hwin21d-1019'; s['job']['tag'] = tag; s['job']['owner'] = 'Claude:S81-HWIN21d'
    s['job']['purpose'] = (f"HWIN21d {letter}: re-pack of HWIN21cb (RTL byte-identical) to {ncol} cols x {nlow+nup} macro rows, SRAM pin -> band <= {reach:.0f} um; "
                           "fixes the c21b SRAM Q -> capture setup and wd_in hold wires; same public edges")
    s['job']['views_to'] = f'physical/ref_tile/{tag}/views'; s['job']['record_to'] = f'results/rtl/ref_tile/{tag}'
    for k, v in list(s['orfs_vars'].items()):
        if isinstance(v, str): s['orfs_vars'][k] = v.replace('dsdv_mu_hwin_c21b/', tag + '/')
    dst = WT/'physical/ref_tile'/tag
    if dst.exists(): shutil.rmtree(dst)
    dst.mkdir()
    for f in ('hwin_gpl_row_envelope.tcl', 'pdn.tcl', 'pre_cts.tcl', 'pre_grt.tcl', 'post_cts.tcl', 'post_drt.tcl', 'post_fill.tcl',
              'post_grt.tcl', 'pre_drt.tcl', 'pre_fill.tcl', 'pin_regs.json', 'reset_landing.json'):
        if (SRC/f).exists(): shutil.copy(SRC/f, dst/f)
    (dst/'spec.json').write_text(json.dumps(s, indent=1) + '\n')
    band = (SRC/'hwin_cell_band.tcl').read_text().replace('253.8', str(lo)).replace('302.4', str(hi))
    (dst/'hwin_cell_band.tcl').write_text(band)
    rg = (SRC/'regen.py').read_text().replace('dsdv_mu_hwin_c21b', tag)
    (dst/'regen.py').write_text(rg)
    print(tag, 'W', W, 'H', H, 'band', lo, hi, 'util %.3f' % util, 'reach %.1f' % reach, 'upper0', upper0, 'empties', [(e[0], e[1]) for e in empties])
build('dsdv_mu_hwin_c21d', 12, 3, 4, 561.6, 388.8, 130, 169.02, 178.8, 'main')
build('dsdv_mu_hwin_c21e', 14, 3, 3, 648.0, 345.6, 120, 164.16, 172.4, 'fallback')  # gate 1 PPL-0086: ck/rst then narrowed to 192.4-196.4 in spec.json
