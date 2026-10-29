"""TOK-HBM-2: fold root_service.json + lane_service.log into service_segments.json (every constant re-derived + checked)."""
import json, re, sys
from pathlib import Path
d = Path(sys.argv[1])
rs = json.loads((d / 'root_service.json').read_text())
rows = [dict(re.findall(r'(\w+)=\s*(\S+)', l)) for l in (d / 'lane_service.log').read_text().splitlines() if 'LANE_SERVICE' in l]
I = lambda r, k: int(r[k])
pre = [r for r in rows if r['op'] == 'HC_PRE']; post = [r for r in rows if r['op'] == 'HC_POST']
# lane constants (each asserted on every measured row)
for r in rows:
    assert I(r, 'scrd_to_up') == 14 and I(r, 'tnode_up_scalar') == 4 and I(r, 'tnode_up_fin') == 4 and I(r, 'tnode_down') == 2
for r in pre:
    n = I(r, 'n'); assert I(r, 'tnode_up_chunk') == 9 and I(r, 'go_to_cs_last_rowN') == 188 + 80 * (n - 1)
    assert I(r, 'ncs') == 20 * n and I(r, 'nwq') == 20 * n and I(r, 'nr') == n
    if I(r, 'flt') == 0: assert I(r, 'r_last_to_fin') == 36
    assert (I(r, 'flt') != 0) == (n > 4 and I(r, 'rd') > 174), r
for r in post:
    n = I(r, 'n'); assert I(r, 'go_to_fin') == 50 + 100 * n and I(r, 'nwq') == 80 * n and I(r, 'flt') == 0
for k, e in rs['per_op_n'].items():
    op, n = k.split('/'); n = int(n); nbt = 5 if op == 'HC_POST' else 1; nsc = 3 * n if op == 'HC_POST' else n
    assert e['go_minus_wsc'] == nsc + 5 + min(n, 2) * nbt
    for w in ('wsc63', 'wsc115'):
        assert e[w]['fin_to_done'] == 1 and (op == 'HC_POST' or e[w]['sum_to_r'] == 114)
seg = dict(schema='opentallas.hbm.fused_service_segments.v1', rgap='affine: row II + rgap per row, x-slot limit + KX rgap; measured at rgap 0/4/12 (lane_rgap_sweep.log, root_rgap_sweep.log)',
    source='results/tok_hbm_2_1028: root_service.json (native root wrapper bench, 16 op/n x wsc 63/115) + lane_service.log '
           '(one native lane + one native tnode, 16 op/n x r-return 150/200 + sweep 170..180) at 833 ps, rtl/hbm_next/fused '
           'tree sha256 838587d4 / hub_n4ext 09a34eff; rgap 0 only',
    root=dict(go_const=5, pre_sum_to_r=114, fin_to_done=1),
    lane=dict(kx=4, pre_go_to_cs_last_const=188, pre_row_ii=80, pre_r_to_fin=36, post_go_to_fin_const=50,
              post_go_to_fin_per_row=100, pre_r_return_max=174, scrd_to_scalar_up=14),
    tnode=dict(levels=5, down=2, up_scalar=4, up_chunk=9),
    sweep_note='PRE n>=5: r returned <= 174 + 4 rgap edges after the row last chunk sum leaves the lane PASS, one more = lane FAULT (x slot of row 0 still busy for row 4): rgap 0 174/175, rgap 4 190/191, rgap 12 222/223',
    status='COMPONENT SEGMENTS CHECKED (benches); composition into root capture->done UNCHECKED until the full-tree vehicle runs')
(d / 'service_segments.json').write_text(json.dumps(seg, indent=1) + '\n'); print('ok', len(rows))
