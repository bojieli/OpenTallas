`timescale 1ns/1ps
// KV-P2-RTL 10-23: results/rtl/kv_hostp_local_program_1023 (Codex HOSTP 9aeab8718) bench on the OBSX source after the
// raw_hc tie removal: the START-only station is qkd_host_hc_station HCW 39 on raw_hc[38:0] (no 143-bit constant).
// MUT 1 = remove the hc[181:39] bypass; MUT 2 = unmask the station (the original 182-bit station on the full raw hc).
module tb_hostp_local_program;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,begin_image=0,word_v=0,word_desc=0,seal=0,auth_v=0,execution_active=0;
 reg[15:0]image_epoch=9,auth_epoch=9;reg[10:0]pw_count=1024;reg[3:0]dw_count=8;
 reg[9:0]word_addr=0;reg[63:0]word_data=0,auth_digest=0;
 wire authorized_footer_valid;wire[63:0]authorized_footer;reg[63:0]actual_hc_footer=0;
 wire[142:0]pr;wire program_ready,fault;wire[63:0]digest;wire[15:0]program_epoch;
 wire[3:0]replay_target;
 qkd_host_program_loader_target dut(.image_target(4'd0),.auth_target(4'd0),.*);
 wire[181:0]raw_hc,transport_hc=0;
 wire[181:0]hc;
 wire cmd_v,source_cr,available,source_fault;
 // Exact source-bound obsx output splice and station instance, audited by check_source.py.
 assign hc=(MUT==1)?{143'd0,transport_hc[38:0]}:{raw_hc[181:39],transport_hc[38:0]};
 generate if(MUT==2)begin:g_unmasked wire[181:0]cmd_hc;
  qkd_host_hc_station station(.ck(ck),.rst_n(rst_n),.die_id(3'd0),.raw_hc(raw_hc),.cmd_cr(1'b0),.cmd_v(cmd_v),.cmd_hc(cmd_hc),.source_cr(source_cr),.available(available),.fault(source_fault));
 end else begin:g_start wire[38:0]cmd_hc;
  qkd_host_hc_station #(.HCW(39))station(.ck(ck),.rst_n(rst_n),.die_id(3'd0),.raw_hc(raw_hc[38:0]),.cmd_cr(1'b0),.cmd_v(cmd_v),.cmd_hc(cmd_hc),.source_cr(source_cr),.available(available),.fault(source_fault));
 end endgenerate
 qkd_host_ctl #(.ND(1))ctl(.ck(ck),.rst_n(rst_n),.ready(1'b0),.req(61'b0),.pr(pr),.tk(93'b0),.hc(raw_hc),.res());
 integer p=0,d=0,cycles=0,first=-1,last=-1,hp=0,hd=0;
 always @(posedge ck)if(rst_n)begin
  cycles++;
  if(cmd_v||source_fault)$fatal(1,"HOSTP_LOCAL FAIL program traffic consumed broadcast credit");
  if(pr[74])begin
   if(pr[73:64]!=p||pr[63:0]!=(64'h1234000000000000+p))$fatal(1,"program replay mismatch");
   if(first<0)first=cycles;p++;last=cycles;
  end
  if(pr[142])begin
   if(pr[141:139]!=d||pr[138:75]!=(64'h5678000000000000+d))$fatal(1,"descriptor replay mismatch");
   d++;last=cycles;
  end
  if(hc[113])begin if(hc[112:103]!=hp||hc[102:39]!=(64'h1234000000000000+hp))$fatal(1,"HOSTP_LOCAL FAIL local PW data");hp++;if(hc[112:103]==1023)actual_hc_footer=hc[102:39];end
  if(hc[181])begin if(hc[180:178]!=hd||hc[177:114]!=(64'h5678000000000000+hd))$fatal(1,"HOSTP_LOCAL FAIL local DW data");hd++;end
  if(program_ready&&(p!=1024||d!=8))$fatal(1,"program readiness before actual writes");
 end
 task tick;@(negedge ck);endtask
 initial begin
  repeat(4)tick();rst_n=1;tick();begin_image=1;tick();begin_image=0;
  for(integer i=0;i<1032;i++)begin
   word_v=1;word_desc=i>=1024;word_addr=10'(i>=1024?i-1024:i);
   word_data=i>=1024?64'h5678000000000000+(i-1024):64'h1234000000000000+i;tick();
  end
  word_v=0;tick();seal=1;tick();seal=0;tick();
  repeat(6)tick();if(p||d||program_ready||authorized_footer_valid)$fatal(1,"unauthorized image emitted");
  auth_digest=digest;auth_v=1;tick();auth_v=0;
  wait(program_ready);repeat(5)tick();
  if(!authorized_footer_valid||authorized_footer!=actual_hc_footer)$fatal(1,"authorized footer differs from actual HC PW1023");
  if(last-first!=1031||hp!=1024||hd!=8||fault)$fatal(1,"static timeline/actual HC broadcast failed");
  // Fresh transaction invalidates readiness; stale external authorization fails.
  begin_image=1;image_epoch=10;pw_count=1;dw_count=1;tick();begin_image=0;
  word_v=1;word_desc=0;word_addr=0;word_data=1;tick();word_desc=1;word_data=2;tick();word_v=0;
  tick();seal=1;tick();seal=0;tick();auth_digest=digest;auth_epoch=9;auth_v=1;tick();auth_v=0;tick();
  if(!fault||program_ready||authorized_footer_valid)$fatal(1,"stale auth accepted");
  $display("HOSTP_LOCAL PASS target0 production1024pw8dw fixed1032cycles localHC allwrites noBroadcastCredit staleauth");$finish;
 end
 initial begin #100000;$fatal(1,"watchdog");end
endmodule
