#!/usr/bin/env python3
"""HBM-SFU9 10-17: column-form r9 store leaf specs (c1).  Usage: mkspec.py WT"""
import json, sys, copy
from pathlib import Path

WT = Path(sys.argv[1])
RT = WT / 'physical/ref_tile'
# width per leaf sized for util ~0.55 (gate rule 0.45-0.60); the W band (register mass, A edges) gets the larger share
GEOM = {2: (280.8, 60.48), 3: (298.08, 64.8)}   # (outline W, macro origin x; all R0: A edge faces the W band)
Y0 = 23.76
PITCH = 70.512      # abutted N-S stack pitch (array height 70.47 + track fit, as leaf3 r9)
MAC_H = 70.47


def ranges(order, spans, lo, hi):
    """split [lo,hi] among ports in order, proportional to spans (bits); 1-bit ports get 1 um"""
    fixed = sum(1.0 for p in order if spans[p] == 1)
    var = [p for p in order if spans[p] > 1]
    tot = sum(spans[p] for p in var)
    room = hi - lo - fixed
    out, y = {}, lo
    for p in order:
        w = 1.0 if spans[p] == 1 else room * spans[p] / tot
        out[p] = [round(y, 3), round(y + w, 3)]
        y += w
    return out


def mk(ns):
    old = json.loads((RT / f'hbm_sfu_store_leaf{ns}_r9_1017/spec.json').read_text())
    s = copy.deepcopy(old)
    W, X0 = GEOM[ns]
    name = f'hbm_sfu_store_leaf{ns}_r9d_1017'
    s['name'] = name
    nm = 2 * ns
    CH = 21.6   # r9d: one >=20 um W->E crossing channel at mid-stack (r9c: M4 overflow 307/921, no horizontal layer over the macros)
    top_mac = Y0 + (nm - 1) * PITCH + MAC_H + CH
    H = round(2.16 * -(-(top_mac + 20.0 + 2.16) // 2.16), 2)
    s['outline'] = {'w': W, 'h': H, 'exact': True}
    s['macros'] = []
    for st in range(ns):
        for pg in range(2):
            k = 2 * st + pg
            s['macros'].append({'view': 'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2', 'count': 1,
                                'inst': f'*g_stripe?{st}?.u_program.g_page?{pg}?.u_program',
                                'at': [X0, round(Y0 + k * PITCH + (CH if k >= ns else 0), 3)], 'at_exact': True, 'orient': 'R0'})
    AW = 11
    bits = dict(clk=1, rst_a=1, in_we=ns, in_addr=AW, in_start_v=1, in_start_base=AW, in_legal=1, in_span=AW + 1,
                in_loops=16, in_loops_one=1, out_v=ns, out_active=ns, out_done=ns, out_fault=ns, out_ord=32,
                out_mm=max(1, ns - 1), in_data_lo=136, in_data_hi=120)
    for i in range(ns):
        bits[f'out_cal{i}'] = 222
    ctl_in = ['in_we', 'in_addr', 'in_start_v', 'in_start_base', 'in_legal', 'in_span', 'in_loops', 'in_loops_one', 'rst_a']
    ctl_out = ['out_v', 'out_active', 'out_done', 'out_fault', 'out_ord', 'out_mm']
    # W face, bottom -> top.  Each stripe's calendar leaves at its own rows; the configuration bus and the control /
    # clock group sit in the middle of the face, the clock pin at mid-height beside the W-band register mass.
    mid = H / 2.0
    if ns == 2:
        segs = [('out_cal0', 3.0, mid - 60.0), ('in_data_lo', mid - 60.0, mid - 16.0), ('ctl', mid - 16.0, mid + 16.0),
                ('out_cal1', mid + 16.0, H - 3.0)]
    else:
        segs = [('out_cal0', 3.0, mid - 65.0), ('in_data_lo', mid - 65.0, mid - 18.0), ('ctl', mid - 18.0, mid + 18.0),
                ('out_cal1', mid + 18.0, mid + 100.0), ('out_cal2', mid + 100.0, H - 3.0)]
    pr = {}
    wface = []
    for nmn, lo, hi in segs:
        if nmn == 'ctl':
            order = ctl_in + ['clk'] + ctl_out
            r = ranges(order, bits, lo, hi)
            pr.update(r); wface += order
        else:
            pr[nmn] = [round(lo, 3), round(hi, 3)]; wface.append(nmn)
    pr['in_data_hi'] = [3.0, round(H - 3.0, 3)]
    s['pins'] = {'W': wface, 'E': ['in_data_hi']}
    s['pin_ranges'] = pr
    s['structural_change'] = (
        f'r9c (HBM-SFU9 10-17, coordinator HANDOFF 0db rejected r9 leaf2: clock + every pin on the W face of 425x194, '
        f'TT insertion 525 / spread 160): COLUMN leaf, {nm} SRAMs as one abutted N-S stack, all R0, so every macro A edge '
        f'(clk, rd_out, addr, wd_in[0:135]) faces ONE W band that holds the register mass (cfg copy low half, captured, '
        f'calendar, stripe control) and every B edge (wd_in[136:255] + ties) faces a thin E band. Each data bit has ONE '
        f'physical destination side: in_data_lo[135:0] W face, in_data_hi[119:0] E face over its full length (wrapper '
        f'port split only, bit-identical). Stripe pages are vertically adjacent (page mux local). Pins spread over the full '
        f'W and E faces (M4), each stripe calendar leaves at its own rows, clock pin at W mid-height beside the register '
        f'mass. r9d: the r9c gates FAILED trial GRT (M4 overflow 307 / 921: the abutted stack left no horizontal crossing under the M5 cap, so E-band clock/control went round the stack, TT insertion 449/507, spread 204/156); r9d splits the stack into two halves with one 21.6 um crossing channel at mid-height, exactly where the clock and control pins enter. Outline {W} x {H} ({H / W:.2f}:1). Cycles unchanged vs r9.')
    s['job']['purpose'] = (f'SFU programme store r9c column leaf ({ns} stripes, {nm} SRAMs) for ot_hgi_sfu_programme_store_r9 '
                           f'(3x leaf3 + 1x leaf2). CRITICAL (hbm_sfu_programme_store): coordinator reviews the gate PNG before submit.')
    s['job']['owner'] = 'Claude:HBM-SFU9'
    s['job']['branch'] = 'claude/hbm-sfu9-1017'
    s['job']['tag'] = 'r9d'
    s['job']['views_to'] = f'physical/ref_tile/{name}/views'
    s['job']['record_to'] = f'results/rtl/ref_tile/{name}'
    d = RT / name
    d.mkdir(exist_ok=True)
    (d / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
    print(name, W, H, f'{H / W:.2f}', json.dumps(pr))


for ns in (2, 3):
    mk(ns)
