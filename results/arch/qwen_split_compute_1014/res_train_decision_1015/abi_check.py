#!/usr/bin/env python3
"""Q-ATTN r3: 4425-bit slab result bus -> serializer input ABI (fails closed).

Producer (actual): qfd_slab_result_half packs slot g = {addr[23:0], mask[15:0], data[511:0]} at [552 g +: 552],
we at [2211:2208], ov at 2212; qfd_port_tiles_b assembles slots 0..3 local + 4..7 rqe -> rq[552 s +: 552],
we[7:0] = rq[4423:4416], ov = rq[4424].  The adopted serializer qfd_res_train_static reads exactly that layout
(row = w[547:528], mask = w[527:512], data = w[511:0], wide-address check on [552 k + 548 +: 4], we@4416+k,
ov@4424).  The legacy credit qfd_sp_res_ser.i is {data, mask, addr, we@1, ov@0}: a direct rq -> i net is wrong.
"""
import re,sys
from pathlib import Path
R=Path(__file__).resolve().parents[4]
half=(R/'rtl/qwen_split/qfd_slab_result_half.sv').read_text()
ports=(R/'rtl/qwen_split/qfd_port_tiles.sv').read_text()
train=(R/'rtl/qwen_split/qfd_res_train_static.sv').read_text()
join=(R/'rtl/qwen_split/qfd_native_compute_join_961t.sv').read_text()
checks={
 'producer slot packing':'assign rq[552*g +: 552] = {addr[24*g +: 24],mask[16*g +: 16],data[512*g +: 512]};' in half,
 'producer we/ov':'assign rq[2211:2208] = we;' in half and 'assign rq[2212] = ov;' in half,
 'band assembly slots 0..3 local':ports.count('rq_q[2207:0] <= local_result[2207:0];')==3,
 'band assembly slots 4..7 rqe':ports.count('rq_q[4415:2208] <= rqe[2207:0];')==3,
 'band we/ov':ports.count('rq_q[4423:4416] <= rst_n ? {rqe[2211:2208],local_result[2211:2208]} : 8\'d0;')==3 and ports.count('rq_q[4424] <= rst_n & (rqe[2212] | local_result[2212]);')==3,
 'train slot fields':'w[547:528]' in train and 'w[527:512]' in train and 'w[511:0]' in train and 'wire[551:0]w=data[552*j+:552];' in train,
 'train capture data/we':'data<=rq[4415:0];we<=rq[4423:4416];' in train,
 'train ov/wide address':'rq[4424]!=expected' in train and 'rq[4416+k]&&|rq[552*k+548+:4]' in train,
}
for b in range(3):
    m=re.search(r'qfd_res_train_static #\(\.BAND\(%d\)[^;]*?\.rq\(([^)]*)\)'%b,join,re.S)
    checks[f'join961t band{b} rq net']=bool(m) and m.group(1)==f'w_pt{b}_rq'
    checks[f'join961t no legacy i']='qfd_sp_res_ser' not in join
bad=[k for k,v in checks.items() if not v]
print('ABI', 'PASS' if not bad else 'FAIL', {k:v for k,v in checks.items()})
sys.exit(1 if bad else 0)
