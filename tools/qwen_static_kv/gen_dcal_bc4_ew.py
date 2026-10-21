#!/usr/bin/env python3
"""KV-EMBWIN16 10-20: the bc4 KV link calendar tile (qkd_d2d_cal_seq_bc4.sv, gen_dcal_bc4.py) on a grown-embed-window pair
image d2d_cal_image_mu_ew<N>.svh (d2d_link_calendar --emb-window N).  The generated file differs from qkd_d2d_cal_seq_bc4.sv
ONLY in its `include line (the START table, token period and compile-time images); structure, ports, reset landing and
edges are byte-identical.  Refuses an image whose TXDP / seam stages / segment bases differ from the bc4 image (the seam
contract TXDP_K 22 and the boot STALE check stay valid).

    gen_dcal_bc4_ew.py 595
"""
import re
import sys
from pathlib import Path

D = Path(__file__).resolve().parents[2] / 'rtl/qwen_sys/d2d_static_20261015'
# KV-PROG17 10-20: the tag may carry the r16 suffix (595_r16 -> d2d_cal_image_mu_ew595_r16.svh, the ATTN_R16 pair image:
# K RESULT +1 / STATUS +213 a layer, so only the K TX / C RX images, START and the token period differ)
# ('r16' alone = the priced window with the r16 shift: d2d_cal_image_mu_r16.svh -> qkd_d2d_cal_seq_bc4_r16.sv)
N = sys.argv[1]
if not re.fullmatch(r'(\d+(_r16)?|r16)', N):
    raise SystemExit(f'gen_dcal_bc4_ew.py: tag {N!r}: <window>[_r16] or r16 expected')
SFX = N if N == 'r16' else f'ew{N}'
base, img = D / 'd2d_cal_image_mu.svh', D / f'd2d_cal_image_mu_{SFX}.svh'
keep = ('D2D_TXDP_C', 'D2D_TXDP_K', 'D2D_CAL_C_TX_SEG1', 'D2D_CAL_C_TX_SEG2', 'D2D_CAL_C_RX_SEG1', 'D2D_CAL_C_RX_SEG2',
        'D2D_CAL_K_TX_SEG1', 'D2D_CAL_K_TX_SEG2', 'D2D_CAL_K_RX_SEG1', 'D2D_CAL_K_RX_SEG2', 'D2D_ADM_OFS', 'D2D_ADM_LEN',
        'D2D_FIRST_TOKEN')
line = lambda t, n: re.search(rf'^localparam[^\n]*\b{n} = [^\n]*$', t, re.M).group(0)
bt, it = base.read_text(), img.read_text()
diff = [n for n in keep if line(bt, n) != line(it, n)]
if diff:
    raise SystemExit(f'{img.name}: {diff} differ from the bc4 image (seam / segment / admission contract)')
src = (D / 'qkd_d2d_cal_seq_bc4.sv').read_text()
inc = '`include "d2d_cal_image_mu.svh"'
assert src.count(inc) == 1, 'bc4 source must include the MU image exactly once'
out = D / f'qkd_d2d_cal_seq_bc4_{SFX}.sv'
out.write_text(f'// KV-EMBWIN16: qkd_d2d_cal_seq_bc4.sv on {img.name} (tools/qwen_static_kv/gen_dcal_bc4_ew.py {N}); only the include differs.\n'
               + src.replace(inc, f'`include "{img.name}"'))
print(f'{out.relative_to(D.parents[2])}: include {img.name}')
