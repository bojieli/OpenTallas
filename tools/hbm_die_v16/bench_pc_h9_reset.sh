#!/usr/bin/env bash
set -euo pipefail
out=${1:?output};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
p=results/arch/hbm_pc_cfg_h8_1623/source
python3 - "$p/tb_hbm_pc_ctrl_leaf_faults_miter.sv" "$out/tb.sv" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text().replace('ncyc=12000','ncyc=3000')
s=s.replace('acc_rd<2000||acc_wr<300||kr<3000||wdone<300||rows<2000','acc_rd<100||acc_wr<10||kr<100||wdone<10||rows<200')
s=s.replace('for(c=0;c<ncyc;c=c+1)begin @(negedge clk); #1 drive(phase==3 && c>9000 && c%97==0); end', '''for(c=0;c<ncyc;c=c+1)begin
        @(negedge clk); #1 drive(0);
        if(c>0 && c%257==0)begin
          if(impl[1].dut.count!=0)busy_resets=busy_resets+1;
          rst_n=0;repeat(6)@(posedge clk);@(negedge clk);#1 rst_n=1;
        end
      end''')
s=s.replace('  integer phase,c,ncyc;', '''  integer phase,c,ncyc;
  integer releases=0,busy_resets=0,alignment_checks=0;
  always @(posedge clk)begin
    #2;
    if(!rst_n)releases=0;else releases=releases+1;
    if(impl[1].dut.g_cand.u.reset_regions !== (releases>=3?8'hff:8'h00))
      $fatal(1,"H9_REGION_ALIGNMENT release_edge=%0d regions=%h",releases,impl[1].dut.g_cand.u.reset_regions);
    if(releases>=3 && {impl[1].dut.g_cand.u.pc_id_q,impl[1].dut.g_cand.u.pc_id_qq,impl[1].dut.g_cand.u.refresh_reload_q} !== {pc_id,pc_id,refresh_reload})
      $fatal(1,"H9_RESET_STRAP_STABILITY");
    alignment_checks=alignment_checks+1;
  end''')
s=s.replace('    $finish;','''    if(busy_resets<20||alignment_checks<12000)$fatal(1,"H9_RESET_VACUOUS busy=%0d align=%0d",busy_resets,alignment_checks);
    $display("H9_RESET_MIDTRAFFIC PASS busy_resets=%0d alignment_checks=%0d release_edges=3 straps_stable=1",busy_resets,alignment_checks);
    $finish;''')
Path(sys.argv[2]).write_text(s)
PY
first=${2:-0}
for m in $(seq "$first" 1);do
 sed 's/module ot_hbm_svc_pc_ctrl_leaf_cfg_h9 #(/module ot_hbm_svc_pc_ctrl_leaf_cfg_faults #(/' "$d/ot_hbm_svc_pc_ctrl_leaf_cfg_h9.sv" > "$out/candidate$m.sv"
 if [ "$m" = 1 ];then
  python3 - "$out/candidate1.sv" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text().replace('wire [7:0] reset_regions;',"wire [7:0] reset_regions_raw;reg delay_region;always @(posedge clk)if(!rst_n)delay_region<=1'b0;else delay_region<=reset_regions_raw[7];wire [7:0] reset_regions={delay_region,reset_regions_raw[6:0]};").replace('.rst_n(reset_regions));','.rst_n(reset_regions_raw));');p.write_text(s)
PY
 fi
 iverilog -g2012 -s tb -o "$out/m$m.vvp" rtl/lib/ot_rst_relay.sv rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv "$d/ot_hbm_svc_pin_skid2_h9.sv" "$p/ot_hbm_r14_stream_pc_strap_h7.sv" physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v "$d/ot_hbm_svc_pc_ctrl_leaf.sv" "$p/reference.sv" "$out/candidate$m.sv" "$p/miter_wrapper.sv" "$out/tb.sv" > "$out/m$m.build.log" 2>&1
 if vvp "$out/m$m.vvp" > "$out/m$m.log" 2>&1;then
  test "$m" = 0 || { echo H9_RESET_MUTANT_SURVIVED;exit 1; }
  grep 'H9_RESET_MIDTRAFFIC PASS' "$out/m$m.log"
 else
  test "$m" = 1 || { cat "$out/m$m.log";exit 1; }
  grep 'H9_REGION_ALIGNMENT' "$out/m$m.log"
  echo H9_RESET_REGION_MUTANT_REJECTED
 fi
done
