#!/usr/bin/env python3
"""Q-DV dv2 (coordinator 10-16 ~23:00, principle 1): each column quad's slice CO-LOCATED in the head gap beside its own
column group.  Graph surgery on the q3h final corrected relay-skip graph (same metrics as dv1 / q3h).

  * head gap widened to GAP_H (bands 2-3 move up); per quad one slice qfd_dv_slice2 (cluster pitch wide x SLH tall)
    that ABSORBS the quad's reduction station (levels 7-9 + row scale), its 4 column x-slice heads and the VM / 8-lane
    SU / constants slice.  Corridor words to the clusters leave the slice's N / S faces (bands 1 / 2 abut the gap).
  * next-layer input: bidirectional neighbour stream slice -> slice along the gap (1,088 b each way), crossing the centre
    column through a relay lane W g0 <-> E g0; tt_ctlm's ib / go rides the same stream from the centre.
  * reduce ends in the group's own slice (b1 / b2 rs abut it; b0 / b3 through the near-cluster feedthrough).
  * global scalars: 96-b tree along the gap (norm sums, argmax), root in the centre.
  * edge endpoints: AR (546 out / 518 back) and D2D (548 / 520) chains slice -> slice toward g0, then own relay lanes
    g0 -> io_collective (S) and g0 -> native59 -> d2d_rom (N).
  * centre column keeps IO band, collective, D2D, tt_ctlm, sys_face, embed, clock / reset; all VM / SU / port / heads gone.
    python3 build_dv2.py OUT.json [GAP_H]"""
import json, gzip, sys
from pathlib import Path
H = Path(__file__).resolve().parent
SRC = H.parent / 'qwen_split_compute_1014/dieplan2_1016/q3h_final_smoke_graph.json.gz'
RM = ('sp_vector_memory', 'sp_su64_sfu', 'seq_su', 'xs_tap', 'tt_up4', 'sp_port', 'sp_halfband', 'sp_halfres',
      'cbuf_g', 'crom_g', 'res_train_issue', 'b2_word_status', 'selector_fork', 'command_fork', 'h_')
def main(out, gap_h):
    d = json.loads(gzip.decompress(SRC.read_bytes()))
    I = {i['n']: dict(i) for i in d['insts']}
    gap_lo = I['c16_W0_1']['y'] + I['c16_W0_1']['h']; gap_hi0 = I['c16_W0_2']['y']
    dy = gap_lo + gap_h - gap_hi0
    for n, i in I.items():                       # everything at / above the old gap top moves up by dy
        if i['y'] >= gap_hi0 - 1: i['y'] = round(i['y'] + dy, 3)
    for n in list(I):
        if n.startswith(RM): del I[n]
    xw1 = I['c16_W0_1']['x'] + I['c16_W0_1']['w']; xe0 = I['c16_E0_1']['x']
    LANE = 129.6                                  # relay lane above and below the slice row
    sy = gap_lo + LANE; slh = gap_h - 2 * LANE; ym = gap_lo + gap_h / 2
    for s in 'WE':
        for g in range(6):
            q = I[f'c16_{s}{g}_1']
            I[f'dvs_{s}{g}'] = dict(n=f'dvs_{s}{g}', m='qfd_dv_slice2', x=q['x'], y=round(sy, 3), w=q['w'], h=round(slh, 3))
    # centre: tt_ctlm / sys_face / embed on the gap row, native59 beside d2d (top), clock / reset below the row
    cx = (xw1 + xe0) / 2
    I['tt_ctlm'].update(x=round(cx - I['tt_ctlm']['w'] / 2, 3), y=round(ym - I['tt_ctlm']['h'] / 2, 3))
    I['sys_face'].update(x=round(I['io_collective']['x'] + I['io_collective']['w'] + 108, 3), y=round(I['io_collective']['y'] + 400, 3))
    I['embed_prov'].update(x=round(cx - 1200, 3), y=round(ym + 300, 3))
    I['native59'].update(x=round(I['d2d_rom']['x'] - 108 - I['native59']['w'], 3), y=round(I['d2d_rom']['y'] - 108, 3))
    I['rstseq_rom'].update(x=round(cx + 900, 3), y=round(ym - 500, 3))
    I['clk_rx'].update(x=round(cx + 600, 3), y=round(ym - 1400, 3))
    def relay(n, x, y):
        I[n] = dict(n=n, m='qfd_dv_lane_relay', x=round(x, 3), y=round(y, 3), w=10.8, h=10.8); return n
    B = []
    for b, cl, bits, eps in d['buses']:
        if b.startswith(('bword', 'head_', 'xfault_')): continue
        if b.startswith('q3h_col_'):              # head h_c -> cluster corridor word: now from the quad's slice
            c = int(b.split('_')[2]); side = 'W' if c < 24 else 'E'
            g = (23 - c) // 4 if side == 'W' else (c - 24) // 4
            B.append([b, cl, bits, [f'dvs_{side}{g}', eps[1]]]); continue
        eps2 = [e for e in eps if e in I]
        if len(eps2) >= 2 and eps2[0] == eps[0]:
            B.append([b, cl, bits, eps2])
    # reduce: b1 / b2 rs abut the slice; b0 / b3 enter the near cluster (rs_i) and leave with it (rs_o)
    for s in 'WE':
        for g in range(6):
            sl = f'dvs_{s}{g}'
            for far, near in ((0, 1), (3, 2)):
                B.append([f'dv_rsi_{s}{g}_{far}', 'dv_reduce', 514, [f'c16_{s}{g}_{far}', f'c16_{s}{g}_{near}']])
                B.append([f'dv_rs_{s}{g}_{near}', 'dv_reduce', 1028, [f'c16_{s}{g}_{near}', sl]])
            if g % 2 == 0:
                B.append([f'dv_l9_{s}{g}', 'dv_reduce', 514, [f'dvs_{s}{g+1}', sl]])
            if g < 5:                             # neighbour links (abutted faces): stream both ways + scalar + AR/D2D chains
                B.append([f'dv_st_{s}{g}', 'dv_gather', 2 * 1088 + 96, [sl, f'dvs_{s}{g+1}']])
                B.append([f'dv_ch_{s}{g}', 'dv_ring', 546 + 518 + 548 + 520, [f'dvs_{s}{g+1}', sl]])
    # centre crossing W g0 <-> E g0 (stream + scalar), relay lane on the gap row
    a = relay('dvx_w', xw1 + 20, ym - 200); b_ = relay('dvx_e', xe0 - 30, ym - 200)
    B.append(['dv_x0', 'dv_gather', 2 * 1088 + 96, ['dvs_W0', a]]); B.append(['dv_x1', 'dv_gather', 2 * 1088 + 96, [a, b_]])
    B.append(['dv_x2', 'dv_gather', 2 * 1088 + 96, [b_, 'dvs_E0']])
    B.append(['dv_ib_W', 'tree_spine', 380, ['tt_ctlm', 'dvs_W0']]); B.append(['dv_ib_E', 'tree_spine', 380, ['tt_ctlm', 'dvs_E0']])
    # edge endpoints, each its own relay lane: g0 -> collective (down the centre), g0 -> native59 (up the centre)
    for s, xo in (('W', 260), ('E', -260)):
        xl = (xw1 + 300) if s == 'W' else (xe0 - 310)
        lo = relay(f'dva_{s}', xl, I['io_collective']['y'] + I['io_collective']['h'] + 108)
        hi = relay(f'dvk_{s}', xl, I['native59']['y'])
        B.append([f'dv_ar_{s}', 'dv_coll', 1064, [f'dvs_{s}0', lo]]); B.append([f'dv_ar2_{s}', 'dv_coll', 1064, [lo, 'io_collective']])
        B.append([f'dv_kv_{s}', 'dv_d2d', 1068, [f'dvs_{s}0', hi]]); B.append([f'dv_kv2_{s}', 'dv_d2d', 1068, [hi, 'native59']])
    B.append(['dv_emb', 'spine_local', 528, ['embed_prov', 'tt_ctlm']])
    for k in [n for n in I if n.startswith('dvs_')]:
        B.append([f'dv_rst_{k}', 'reset', 1, ['rstseq_rom', k]]); B.append([f'dv_ck_{k}', 'clock_trunk', 1, ['clk_rx', k]])
    json.dump(dict(insts=list(I.values()), buses=B, gap_h=gap_h, slice=[I['dvs_W0']['w'], slh]), open(out, 'w'))
    print(out, len(I), 'insts', len(B), 'buses', 'slice', round(I['dvs_W0']['w'], 1), 'x', round(slh, 1), '=', round(I['dvs_W0']['w'] * slh / 1e6, 2), 'mm2')
if __name__ == '__main__':
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 2462.4)
