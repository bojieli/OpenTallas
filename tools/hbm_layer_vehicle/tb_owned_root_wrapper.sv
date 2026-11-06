`timescale 1ns/1fs
module tb_owned_root_wrapper;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,cfg_v=0;reg[255:0]cfg_data=0;
 wire[1:0]aiv,biv,civ;wire[1:0]ak,bk,ck;wire[19:0]aw,bw,cw;
 reg[31:0]rng=32'h319b7d15;integer n,checks=0;reg prev=0;reg[31:0]prevdata;reg[2:0]prevpos;reg[4:0]expectrow=0,prevrow;
 `define PORTS .clk(clk),.rst_n(rst_n),.tgt(8'd164),.cfg_v(cfg_v),.cfg_target(8'd164),.cfg_addr(12'd0),.cfg_data(cfg_data),.desc_v(1'b0),.desc_base(12'd0),.desc_limit(13'd0),.desc_loops(16'd0),.launch_v(1'b0),.qps_v(2'd0),.qps(64'd0),.qps_f(2'd0),.q_fault(2'd0),.gathered_mix_v(2'd0),.gathered_mix_row(10'd0),.gathered_mix_pos(6'd0),.gathered_mix_data(64'd0)
 ot_hbm_hc_root_orig #(.NQ(2)) a(`PORTS,.qi_v(aiv),.qi_kind(ak),.qd_wa(aw));
 ot_hbm_hc_root_static #(.NQ(2)) b(`PORTS,.qi_v(biv),.qi_kind(bk),.qd_wa(bw));
 ot_hbm_hc_root_static #(.NQ(2),.NOUT(1),.WROW0(0),.OROW0(-1),.MUT(`MUT)) c(`PORTS,.qi_v(civ),.qi_kind(ck),.qd_wa(cw));
 initial begin
  repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
  for(n=0;n<1200;n++)begin
   @(negedge clk);rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};cfg_data=0;
   cfg_v=(n%3!=2);cfg_data[64]=(n%3==0);cfg_data[68:65]=4'((n%8)+1);
   cfg_data[70:69]=rng[1:0];cfg_data[102:71]=rng;
   cfg_data[104]=(n%37==0);cfg_data[20]=(n%3==1);cfg_data[22:21]={1'b0,rng[2]};
   cfg_data[23]=rng[3];cfg_data[25:24]=rng[5:4];cfg_data[30:26]=5'((n%3==0)?((n/3)%24):(n%8));
   `ifdef BAD_ROW
   if(n%3==0)cfg_data[30:26]=5'd24;
`endif
   cfg_data[37:31]=7'(n%40);cfg_data[49:38]=12'd40;cfg_data[59:50]=10'(n%320);
   @(posedge clk);#0.001;
   if(a.have!==b.have||a.fault!==b.fault||a.o_valid!==b.o_valid||a.o_idx!==b.o_idx||a.o_data!==b.o_data||aiv!==biv)
    $fatal(1,"default wrapper mismatch cycle%0d",n);
   if(a.u_core.cmd_nout!==6'd24||b.u_core.cmd_nout!==6'd24||a.u_core.cmd_wbase!==b.u_core.cmd_wbase)
    $fatal(1,"default command mismatch");
   if(aiv && ({a.qi_kind,a.qi_slot,a.qi_lo,a.qi_w,a.qi_cnt,a.qi_word}!=={b.qi_kind,b.qi_slot,b.qi_lo,b.qi_w,b.qi_cnt,b.qi_word}))
    $fatal(1,"default ingest mismatch");
   for(int k=0;k<192;k++)if(a.have[k])begin
    if(a.mixes[k*32+:32]!==b.mixes[k*32+:32])$fatal(1,"default mix store mismatch");checks++;
   end
   `ifdef BAD_ROW
   if(c.e_launch)begin
    if(!c.ev_fault)$fatal(1,"invalid global-row guard missing");
    $display("OWNED_ROOT_BAD_ROW_CAUGHT");$finish;
   end
`endif
   if(c.e_launch)begin
    if(c.u_core.cmd_nout!==6'd1||c.u_core.cmd_wbase!==10'(cfg_data[70:69]*256))$fatal(1,"owned weight-base mismatch");
    expectrow=c.e_lo;checks++;
   end
   if(c.o_valid)begin if(c.o_idx!==expectrow)$fatal(1,"owned global-row mismatch");checks++;end
   if(prev)begin
    if(!c.have[prevpos*24+prevrow]||c.mixes[(prevpos*24+prevrow)*32+:32]!==prevdata)$fatal(1,"owned mix-store mismatch");
    checks++;
   end
   prev=c.o_valid;prevdata=c.o_data;prevpos=c.o_pos;prevrow=expectrow;
  end
  $display("OWNED_ROOT_WRAPPER PASS checks=%0d cycles=1200 arithmetic_abstracted=1 protocol_abstracted=1",checks);$finish;
 end
endmodule
