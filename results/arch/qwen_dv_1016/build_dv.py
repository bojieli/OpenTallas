#!/usr/bin/env python3
"""Q-DV (owner 2026-10-16 ~22:00): distributed-vector Qwen compute die, as graph surgery on the q3h final corrected
relay-skip graph (dieplan2_1016/q3h_final_smoke_graph.json.gz, 178 inst; cuts / bit-mm with the SAME metrics as
Q-DIEPLAN3 / Q-VMSLICE).  Evaluation model, no RTL, no GEN.

Kept: 48 qfd_c_b16 clusters at their q3h2 homes, the 48 column x-slice heads h_c + head chain + column corridor
words, IO band (collective + 3 SerDes + peer UCIe), D2D (ucie_kv + d2d_rom), clock/reset entry, tt_ctlm, sys_face,
embedding provider.
Removed (the star): central VM, SU64+SFU, seq_su, xs_tap, 16 constant groups, 6 port-tile halves, 6 half-band lanes,
6 half result trains, 8 tree-top leaves, result-train issue, word status, 14 static forks.  native59 is kept as the
D2D-side formatter (KV/q export, attention return) and moved beside d2d_rom.
Added:
  dvr_<s><g>  12 head-gap REDUCTION STATIONS (one per column quad = side s, group g, bands 0-3): level 7 (b0+b1, b2+b3:
              gate/up done), level 8 (o/down done), level 9 with the pair station (qkv / LM head), BF16 row scale.
              b1/b2 rs abut the head gap; b0/b3 rs reach it through a registered 514-b feedthrough in the near
              cluster (as bc_o today).
  dvs_<k>     12 DV SLICES (VM slice + 8-lane SU/SFU slice + constants + gather / scalar / AR / D2D ports), one per
              column quad, 3 x 4 in the centre straddling the head row.  Slice k owns its quad's output rows.
  dvg_W/E     2 gather exits (replace xs_tap): full-x BF16 stream (64 / cycle) onto each side's head chain.
Links (bits):  quad lane dvr -> slice 530 (one 514-b result word + 16 slot/ctl; gate/up's two level-7 bursts serialise: +8 cycles a layer); pair level 9 dvr <-> dvr 514; gather merge tree
  1,088 (1,024 data + 64 slot/ctl) per hop toward both exits; slice neighbour mesh column links 2,312 (AR out 546 + AR return 518 +
  D2D out 548 + attention return 520 + scalar tree 64 + command 116), row links 180; collective <-> bottom-row slices; native59 <->
  top-row slices; tt_ctlm -> slices command tree 116; tt -> exits ib 380."""
import json, gzip, sys, math
from pathlib import Path
H = Path(__file__).resolve().parent
SRC = H.parent / 'qwen_split_compute_1014/dieplan2_1016/q3h_final_smoke_graph.json.gz'
SL = float(sys.argv[2]) if len(sys.argv) > 2 else 1944.0      # slice edge (square)
CH = 108.0                                                     # channel between slices
RM = ('sp_vector_memory', 'sp_su64_sfu', 'seq_su', 'xs_tap', 'tt_up4', 'sp_port', 'sp_halfband', 'sp_halfres',
      'cbuf_g', 'crom_g', 'res_train_issue', 'b2_word_status', 'selector_fork', 'command_fork')
def main(out):
    d = json.loads(gzip.decompress(SRC.read_bytes()))
    I = {i['n']: dict(i) for i in d['insts']}
    for n in list(I):
        if n.startswith(RM): del I[n]
    c = {n: I[n] for n in I if n.startswith('c16_')}
    gap_lo = c['c16_W0_1']['y'] + c['c16_W0_1']['h']; gap_hi = c['c16_W0_2']['y']; ym = (gap_lo + gap_hi) / 2
    xw1 = c['c16_W0_1']['x'] + c['c16_W0_1']['w']; xe0 = c['c16_E0_1']['x']
    new = {}
    def add(n, m, x, y, w, h): new[n] = dict(n=n, m=m, x=round(x, 3), y=round(y, 3), w=w, h=h)
    # head-gap reduction stations: centred on the group, between the two middle heads
    for s in 'WE':
        for g in range(6):
            q = c[f'c16_{s}{g}_1']; add(f'dvr_{s}{g}', 'qfd_dv_redstn', q['x'] + q['w'] / 2 - 172.8, ym - 432.0, 345.6, 864.0)
    # slices: 3 columns x 4 rows centred on (centre column, head row)
    bw = 3 * SL + 2 * CH; bh = 4 * SL + 3 * CH
    x0 = (xw1 + xe0) / 2 - bw / 2; y0 = ym - bh / 2
    pos = {}
    K3 = lambda col, row: col * 4 + row
    for col in range(3):
        for row in range(4):
            k = col * 4 + row; pos[k] = (col, row)
            add(f'dvs_{k}', 'qfd_dv_slice', x0 + col * (SL + CH), y0 + row * (SL + CH), SL, SL)
    add('dvg_W', 'qfd_dv_gather_exit', x0 - CH - 216.0, ym - 108.0, 216.0, 216.0)
    add('dvg_E', 'qfd_dv_gather_exit', x0 + bw + CH, ym - 108.0, 216.0, 216.0)
    # relocate the blocks the slice block displaces: tt_ctlm / sys_face / native59 / embed above, rstseq / clk_rx below
    top = y0 + bh + 216.0
    I['tt_ctlm'].update(x=round(x0 + bw / 2 - I['tt_ctlm']['w'] / 2, 3), y=round(top, 3))
    I['native59'].update(x=round(I['d2d_rom']['x'] - 108 - I['native59']['w'], 3), y=round(I['d2d_rom']['y'] - 108, 3))
    I['sys_face'].update(x=round(x0 + bw - I['sys_face']['w'], 3), y=round(top, 3))
    I['embed_prov'].update(x=round(x0, 3), y=round(top, 3))
    I['rstseq_rom'].update(x=round(x0 + bw / 2, 3), y=round(y0 - 216, 3))
    I['clk_rx'].update(x=round(x0 + bw / 2 - 500, 3), y=round(y0 - 216 - I['clk_rx']['h'], 3))
    I.update(new)
    # slice ownership: W groups g0..g5 -> W column (rows 0-3) + middle rows 1, 2 ... E symmetric
    # slice ownership: the pair-finishing quads of qkv / LM head (even g) own top-half slices (rows 2-3: next to the
    # D2D / native59), odd g bottom-half (rows 0-1: next to the collective); W groups use column 0 + middle, E column 2
    own = {('W', 0): K3(0, 2), ('W', 2): K3(0, 3), ('W', 4): K3(1, 3), ('W', 1): K3(0, 1), ('W', 3): K3(0, 0), ('W', 5): K3(1, 0),
           ('E', 0): K3(2, 2), ('E', 2): K3(2, 3), ('E', 4): K3(1, 2), ('E', 1): K3(2, 1), ('E', 3): K3(2, 0), ('E', 5): K3(1, 1)}
    B = []
    keep_tt = ('tt_ctlm', 'sys_face', 'native59', 'embed_prov', 'io_collective', 'd2d_rom', 'ucie_kv', 'clk_rx', 'rstseq_rom')
    for b, cl, bits, eps in d['buses']:
        if b.startswith('bword'): continue
        eps2 = [e for e in eps if e in I]
        if b in ('head_23', 'head_24'):
            eps2 = ['dvg_W' if b == 'head_23' else 'dvg_E', eps[1]]
        if len(eps2) >= 2 and eps2[0] == eps[0]:
            B.append([b, cl, bits, eps2])
    for s in 'WE':
        for g in range(6):
            r = f'dvr_{s}{g}'
            # far band rs enters the near cluster across the band gap (rs_i) and leaves on its head-gap face (rs_o):
            # a registered feedthrough in the near cluster's corridor, as bc_o today
            for far, near in ((0, 1), (3, 2)):
                B.append([f'dv_rsi_{s}{g}_{far}', 'dv_reduce', 514, [f'c16_{s}{g}_{far}', f'c16_{s}{g}_{near}']])
                B.append([f'dv_rs_{s}{g}_{near}', 'dv_reduce', 1028, [f'c16_{s}{g}_{near}', r]])
            # lane: along the head gap to the array's inner edge (relay waypoint), then into the owning slice
            wp = f'dvw_{s}{g}'
            xin = xw1 + 30.0 if s == 'W' else xe0 - 40.0
            yg = ym - 420 + 168 * g + (84 if s == 'E' else 0)       # each lane on its own track band in the gap
            I[wp] = dict(n=wp, m='qfd_dv_lane_relay', x=round(xin, 3), y=round(yg, 3), w=10.8, h=10.8)
            w0 = f'dvo_{s}{g}'; rr = new[r]
            I[w0] = dict(n=w0, m='qfd_dv_lane_relay', x=round(rr['x'] + (rr['w'] if s == 'W' else -10.8), 3), y=round(yg, 3), w=10.8, h=10.8)
            B.append([f'dv_lane0_{s}{g}', 'dv_lane', 530, [r, w0]])
            B.append([f'dv_lane_{s}{g}', 'dv_lane', 530, [w0, wp]])
            B.append([f'dv_lane2_{s}{g}', 'dv_lane', 530, [wp, f"dvs_{own[(s, g)]}"]])
            if g % 2 == 0:
                B.append([f'dv_l9_{s}{g}', 'dv_reduce', 514, [f'dvr_{s}{g+1}', r]])
            B.append([f'dv_cmd_r_{s}{g}', 'sequencer', 24, [wp, r]])
    # gather merge tree (both exits): columns merge toward rows 1/2, rows 1/2 merge horizontally to both exits
    K = {pos[k]: k for k in pos}
    for col in range(3):
        B.append([f'dv_gv_{col}_0', 'dv_gather', 1088, [f'dvs_{K[(col,0)]}', f'dvs_{K[(col,1)]}']])
        B.append([f'dv_gv_{col}_3', 'dv_gather', 1088, [f'dvs_{K[(col,3)]}', f'dvs_{K[(col,2)]}']])
    for row in (1, 2):
        B.append([f'dv_gw_{row}_a', 'dv_gather', 1088, [f'dvs_{K[(2,row)]}', f'dvs_{K[(1,row)]}']])
        B.append([f'dv_gw_{row}_b', 'dv_gather', 1088, [f'dvs_{K[(1,row)]}', f'dvs_{K[(0,row)]}']])
        B.append([f'dv_gw_{row}_x', 'dv_gather', 1088, [f'dvs_{K[(0,row)]}', 'dvg_W']])
        B.append([f'dv_ge_{row}_a', 'dv_gather', 1088, [f'dvs_{K[(0,row)]}', f'dvs_{K[(1,row)]}']])
        B.append([f'dv_ge_{row}_b', 'dv_gather', 1088, [f'dvs_{K[(1,row)]}', f'dvs_{K[(2,row)]}']])
        B.append([f'dv_ge_{row}_x', 'dv_gather', 1088, [f'dvs_{K[(2,row)]}', 'dvg_E']])
    # neighbour mesh: column links carry AR out/in (to the bottom row -> collective), D2D out/in (to the top row ->
    # native59), scalar tree and command (2,312 b); row links carry the scalar tree + command only (180 b)
    order = []
    for col in range(3):
        for r in range(3):
            B.append([f'dv_mv_{col}_{r}', 'dv_ring', 2312, [f'dvs_{K[(col,r)]}', f'dvs_{K[(col,r+1)]}']])
    for row in range(4):
        for col in range(2):
            B.append([f'dv_mh_{col}_{row}', 'dv_ring', 180, [f'dvs_{K[(col,row)]}', f'dvs_{K[(col+1,row)]}']])
    for col in range(3):
        B.append([f'dv_ar_o_{col}', 'dv_coll', 546, [f'dvs_{K[(col,0)]}', 'io_collective']])
        B.append([f'dv_ar_i_{col}', 'dv_coll', 518, ['io_collective', f'dvs_{K[(col,0)]}']])
        B.append([f'dv_kv_o_{col}', 'dv_d2d', 548, [f'dvs_{K[(col,3)]}', 'native59']])
        B.append([f'dv_kv_i_{col}', 'dv_d2d', 520, ['native59', f'dvs_{K[(col,3)]}']])
        B.append([f'dv_cmd_{col}', 'sequencer', 116, ['tt_ctlm', f'dvs_{K[(col,3)]}']])
    B.append(['dv_emb', 'spine_local', 528, ['embed_prov', f'dvs_{K[(0,3)]}']])
    for x in ('dvg_W', 'dvg_E'):
        B.append([f'dv_ib_{x}', 'tree_spine', 380, ['tt_ctlm', x]])
    for x in ('dvg_W', 'dvg_E'):
        B.append([f'dv_rst_{x}', 'reset', 1, ['rstseq_rom', x]])
    for k in range(12):
        B.append([f'dv_rst_s{k}', 'reset', 1, ['rstseq_rom', f'dvs_{k}']])
        B.append([f'dv_ck_s{k}', 'clock_trunk', 1, ['clk_rx', f'dvs_{k}']])
    json.dump(dict(insts=list(I.values()), buses=B, own={f'{s}{g}': k for (s, g), k in own.items()}, ring=order), open(out, 'w'))
    print(out, len(I), 'insts', len(B), 'buses')
if __name__ == '__main__':
    main(sys.argv[1])
