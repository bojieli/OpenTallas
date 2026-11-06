#!/usr/bin/env bash
# HBM-REFORM-B9 PD=3 form (outputs declared 3 edges late) of the part 30 lock-step: ot_hbm_idx_topk_link_static with WRITE_PIPE_STAGES=2 (kit face shell) vs ingest + store. run_p30.sh OUT [CYCLES]. MUT 0 PASS; 1 stale write after clear, 2 write address rotated, 3 write data rotated, 4 store gbase wrong must FAIL.
set -u
OUT=$(realpath -m "$1"); CYC=${2:-6000}; H=$(cd "$(dirname "$0")" && pwd); W=$H/../../../..; O=$OUT; mkdir -p $O
RT=$W/rtl/hbm_accel/cores_split/reform_1105s/topk; BB=$W/physical/die_plan/hbm/over_cap_split/reform_1103; IDX=$W/rtl/hbm_accel/index; V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}
CT=$(ls $W/rtl/hbm_accel/index/ot_hbm_idx_compact_tree.sv $W/rtl/hbm_accel/index/*/ot_hbm_idx_compact_tree.sv 2>/dev/null | head -1)
FR=$W/rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192_face/ot_hbm_face_reg.sv
cat > $O/sram.sv <<'E'
`timescale 1ns/1ps
module ot_sram_1r1w_64x512_m1_r2c2(input wire clk,r_ce_in,input wire[5:0]r_addr_in,output reg[511:0]rd_out,input wire w_ce_in,input wire[5:0]w_addr_in,input wire[511:0]wd_in,w_mask_in,input wire[1:0]rr_en,input wire[11:0]rr_addr,input wire[1:0]cr_en,input wire[17:0]cr_sel);
 reg[511:0]mem[0:63]; integer i; initial for(i=0;i<64;i=i+1)mem[i]={16{i[31:0]*32'h9e3779b9}};
 always @(posedge clk)begin if(r_ce_in)rd_out<=mem[r_addr_in];if(w_ce_in)mem[w_addr_in]<=(mem[w_addr_in]&~w_mask_in)|(wd_in&w_mask_in);end
endmodule
E
cat > $O/ref.sv <<'E'
`default_nettype none
module topk_ref(input wire clk,input wire[7:0]clk_mem,input wire rst_n,input wire clear,ingest_v,input wire[2367:0]selected_line,input wire flush,emit_v,input wire[3:0]emit_group,input wire[7:0]rank,gbase,output wire[3:0]tx_v,output wire[2179:0]tx,output wire fault,output wire[9:0]selected_count);
 ot_hbm_idx_topk_link_static #(.WRITE_PIPE_STAGES(2)) u(.*);
endmodule
`default_nettype wire
E
CK='^clk(_mem)?$'
python3 -I $BB/facewrap.py --top topk_ref --clk-re "$CK" --rst-re '^rst_n$' --out $O/ref__fs.sv $O/ref.sv $IDX/ot_hbm_idx_topk_link_static.sv $CT $O/sram.sv > $O/ref.json || exit 1
python3 -I $BB/facewrap.py --top ot_hbm_idx_topk_ingest --clk-re "$CK" --rst-re '^rst_n$' --pass-param MUT --out $O/ing__fs.sv $RT/ot_hbm_idx_topk_tiles.sv $CT $O/sram.sv > $O/ing.json || exit 1
python3 -I $BB/facewrap.py --top ot_hbm_idx_topk_store --clk-re "$CK" --rst-re '^rst_n$' --pass-param MUT --out $O/sto__fs.sv $RT/ot_hbm_idx_topk_tiles.sv $CT $O/sram.sv > $O/sto.json || exit 1
sed -e "s/ot_hbm_idx_topk_store__fs u_sto/ot_hbm_idx_topk_store__fs #(.MUT(MUT)) u_sto/" -e "s/module ot_hbm_idx_topk__comp/module topk_dut/" $H/topk__comp.sv > $O/dut.sv
python3 -I - $O <<'P'
import json,sys
O=sys.argv[1]; p=json.load(open(O+"/ref.json")); P=p["ports"]
st={"clear":"1'(($urandom % 64) == 0)","ingest_v":"1'(($urandom % 3) != 0)","emit_v":"1'(($urandom % 7) == 0)","flush":"1'(($urandom % 256) == 0)"}
json.dump(dict(ref="topk_ref__fs",dut="topk_dutw",ports=P,clocks=["clk","clk_mem"],resets=["rst_n"],reset_cycles=10,warmup=150,cycles=6000,stim=st,hold={},shift={"tx_v":3,"tx":3,"fault":3,"selected_count":3}),open(O+"/spec.json","w"),indent=1)
P
cat > $O/dutw.sv <<'E'
`default_nettype none
module topk_dutw(input wire clk,input wire[7:0]clk_mem,input wire rst_n,input wire clear,ingest_v,input wire[2367:0]selected_line,input wire flush,emit_v,input wire[3:0]emit_group,input wire[7:0]rank,gbase,output wire[3:0]tx_v,output wire[2179:0]tx,output wire fault,output wire[9:0]selected_count);
 topk_dut #(.MUT(`OT_MUT)) u(.*);
endmodule
`default_nettype wire
E
python3 -I $BB/lockstep_gen.py $O/spec.json $O/tb.sv
grep -c "topk_ref__fs\|topk_dutw" $O/tb.sv
for M in 0 1 2 3 4; do ( D=$O/obj_m$M; $V --binary -j 8 -Wno-fatal -Wno-lint -Wno-style -DOT_MUT=$M --top-module tb -Mdir $D -o sim $O/tb.sv $O/dutw.sv $O/dut.sv $O/ref__fs.sv $O/ref.sv $O/ing__fs.sv $O/sto__fs.sv $RT/ot_hbm_idx_topk_tiles.sv $IDX/ot_hbm_idx_topk_link_static.sv $CT $O/sram.sv $FR > $O/b$M.log 2>&1 || { tail -12 $O/b$M.log | cut -c1-230; exit 2; }; $D/sim > $O/s$M.log 2>&1; echo "MUT $M: $(grep LOCKSTEP $O/s$M.log | cut -c1-170)" ) & done; wait
