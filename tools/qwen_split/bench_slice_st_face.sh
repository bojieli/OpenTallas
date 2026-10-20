#!/bin/bash
set -eu
cd "$(dirname "$0")/../.."
O=$1; mode=${2:-pass}; mkdir -p "$O"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
python3 - "$O/tb.sv" <<'GEN'
import sys
from tools.qwen_split import bench_land8w as b
rows=[]
for i in range(4):
 ph=9.158957 if i%2==0 else 0.675872
 L=4 if i%2==0 else 5
 K=[3,11,6,14][i]; R0=20; G=18+((K-L+R0+2-18)%16)
 rows.append(dict(i=i,doff=ph,L=L,K=K,G=G,R0=R0,SC=i,SR=1))
b.lanes=lambda sr:rows
sys.argv=['bench','qfd_slice_st_face_land','1088',sys.argv[1],'--sram']
b.main()
from pathlib import Path
p=Path(sys.argv[3]);s=p.read_text()
s=s.replace('.a(a)', '.i(a)').replace('.b(o)', '.o(o)')
s=s.replace('.k0(kk[0]), .k1(kk[1]), .k2(kk[2]), .k3(kk[3]),', '.k(rs ? ~kk : kk),')
s=s.replace('.tie_hi(hi), .tie_lo(lo), ', '')
s=s.replace('u_l.u_land.rc', 'u_l.g_bank[0].u_ring.rc').replace('u_l.u_land.wc', 'u_l.g_bank[0].u_ring.wc').replace('u_l.u_land.warm', 'u_l.g_bank[0].u_ring.warm')
s=s.replace('tc < 20000', 'tc < 1500').replace('K 0..15)', 'K 3/6/11/14)')
p.write_text(s)
GEN
DEF=+define+OT_MEM_NO_INIT
if [ "$mode" = rsel ]; then DEF="$DEF +define+OT_QFD_LAND8_MUT_RSEL"; fi
verilator --binary --timing -j 2 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-COMBDLY -Wno-LATCH -Wno-INITIALDLY --x-assign unique --x-initial unique --top-module tb $DEF -Mdir "$O/obj" -o tb "$O/tb.sv" rtl/qwen_dv/qfd_slice_st_face_land.sv rtl/qwen_split/qfd_land8.sv rtl/qwen_split/qfd_land8s.sv rtl/hdc/ot_hdc_cg.sv physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v > "$O/build.log" 2>&1
"$O/obj/tb" +verilator+rand+reset+2 +verilator+seed+2026 > "$O/bench.log" 2>&1
grep LAND8_BENCH "$O/bench.log"
if [ "$mode" = rsel ]; then grep -q 'LAND8_BENCH FAIL' "$O/bench.log"; else grep -q 'LAND8_BENCH PASS' "$O/bench.log"; fi
