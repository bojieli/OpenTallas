`timescale 1ns/1ps
// Actual multi-root return-ring (qkd_static_kv_return_slots_mc) drain exports; storage roots = pll_hbm (same phase).
// No parent or physical timing claim. Copy of tb_static_return_idle.sv for the mc master (Q-ELEM-RING 10-16).
module tb_static_return_idle_mc;
 parameter integer PHASE_PS=137;
 parameter integer DEPTH=64;
 reg hc=0,ck=0,rst=0,put=0,expected=0;
 reg [293:0] co=0;
 always #0.512 hc=~hc;
 initial begin #(PHASE_PS*0.001);forever #0.416667 ck=~ck;end
 wire ih,ic,av,hf,cf;wire[255:0]data;
 qkd_static_kv_return_slots_mc #(.DEPTH(DEPTH)) dut(.pll_hbm(hc),.pll_hbm_data({4{hc}}),.hrst(rst),.ck(ck),.rsi(rst),
 .controller_co(co),.controller_epoch(16'd7),.compiled_hbm_put(put),
 .expected_put(expected),.expected_sector(10'd0),.expected_epoch(16'd7),.expected_layer(6'd0),
 .actual_valid(av),.actual_sector(),.actual_epoch(),.actual_layer(),.actual_data(data),
 .fault_hbm(hf),.fault_core(cf),.idle_hbm(ih),.idle_core(ic));
 // Reference: the original single-root ring (qkd_static_kv_return_slots, unchanged) on the same stimulus. The mc
 // drain observations are the reference ones exactly one local edge later (idle_hbm: mc3b, idle_core: mc_r3c), and
 // the data/valid/fault exports are cycle-identical. Checked on every edge once the first reset has settled.
 wire rih,ric,rav,rhf,rcf;wire[255:0]rdata;
 qkd_static_kv_return_slots #(.DEPTH(DEPTH)) ref_ring(.pll_hbm(hc),.hrst(rst),.ck(ck),.rsi(rst),
 .controller_co(co),.controller_epoch(16'd7),.compiled_hbm_put(put),
 .expected_put(expected),.expected_sector(10'd0),.expected_epoch(16'd7),.expected_layer(6'd0),
 .actual_valid(rav),.actual_sector(),.actual_epoch(),.actual_layer(),.actual_data(rdata),
 .fault_hbm(rhf),.fault_core(rcf),.idle_hbm(rih),.idle_core(ric));
 reg chk=0,ric_d=0,rih_d=0;integer ncmp=0;
 always @(posedge ck)begin #0.05;
  if(chk && (ic!==ric_d || av!==rav || cf!==rcf || data!==rdata))
   $fatal(1,"IDLE mc core export differs from reference (+1 ck idle) ic=%b ref_prev=%b av=%b/%b",ic,ric_d,av,rav);
  ric_d=ric;if(chk)ncmp=ncmp+1;
 end
 always @(posedge hc)begin #0.05;
  if(chk && (ih!==rih_d || hf!==rhf))$fatal(1,"IDLE mc hbm export differs from reference (+1 hclk idle) ih=%b ref_prev=%b",ih,rih_d);
  rih_d=rih;
 end
 task wait_quiet;
 begin repeat(8)@(negedge hc);repeat(8)@(negedge ck);#0.01;end
 endtask
 task landing;
 begin @(negedge hc);put=1;co[0]=1;co[281:26]=256'h12345678;
 @(negedge hc);put=0;co=0;end
 endtask
 initial begin
 repeat(4)@(negedge hc);rst=1;wait_quiet();chk=1;
 if(ih!==1||ic!==1)$fatal(1,"IDLE empty reset ring");
 landing();wait_quiet();
 if(ih!==0||ic!==0)$fatal(1,"IDLE outstanding publication lost");
 @(negedge ck);expected=1;
 // Current input slot must suppress idle on its capture edge.
 @(negedge ck);if(ic!==0)$fatal(1,"IDLE core pending slot ignored");expected=0;
 wait_quiet();
 if(ih!==1||ic!==1||hf||cf)$fatal(1,"IDLE consumed ring failed to drain");
 landing();wait_quiet();
 if(ih!==0||ic!==0)$fatal(1,"IDLE reused entry falsely drained");
 @(negedge hc);chk=0;rst=0;repeat(4)@(negedge hc);
 if(ih!==0||ic!==0)$fatal(1,"IDLE reset must not advertise drained");
 rst=1;wait_quiet();chk=1;
 if(ih!==1||ic!==1)$fatal(1,"IDLE reset ring failed to drain");
 // second publish + consume on the reset ring, drain; every edge compared with the reference
 landing();wait_quiet();@(negedge ck);expected=1;@(negedge ck);expected=0;wait_quiet();
 if(ih!==1||ic!==1||hf||cf)$fatal(1,"IDLE second consume failed to drain");
 // unpublished consume on the drained ring (a schedule fault: fault_core rises in both rings): the core put term
 // of the drain observation is only visible here; both exports keep being compared edge by edge
 @(negedge ck);expected=1;@(negedge ck);expected=0;repeat(4)@(negedge ck);#0.01;
 if(cf!==1||ic!==0)$fatal(1,"IDLE unpublished consume: fault_core %b idle_core %b",cf,ic);
 $display("PASS actual return-ring idle mc phase%0d outstanding/consume/reuse/reset; %0d ck edges equal to reference +1 edge",PHASE_PS,ncmp);$finish;
 end
 initial begin #2000;$fatal(1,"IDLE timeout");end
endmodule
