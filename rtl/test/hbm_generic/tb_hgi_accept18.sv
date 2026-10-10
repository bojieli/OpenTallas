`timescale 1ns/1ps
module tb_hgi_accept18;
parameter integer PINREG=1;
reg clk=0; always #0.4166665 clk=~clk;
reg rst_n=0,start_v=0,tokx_v=0,amax_v=0,acc_v=0;
reg [17:0] start_tok=0,tokx_tok=0,amax_tok=0;
reg [2:0] tokx_slot=0,amax_slot=0,acc_g=0;
wire [143:0] stok,ttok; wire acc_done,acc_any; wire [2:0] acc_a; wire [3:0] n_emit; wire [17:0] bonus;
ot_hgi_mtp_accept18 #(.GENERIC18(1),.PINREG(PINREG)) dut(.*);
wire [135:0] ds_stok,ds_ttok; wire ds_done,ds_any; wire [2:0] ds_a; wire [3:0] ds_emit; wire [16:0] ds_bonus;
ot_hdc_accept #(.NSLOT(8),.NW(17)) ref17(.clk(clk),.rst_n(rst_n),.start_v(dut.start_v_i),.start_tok(dut.start_tok_i[16:0]),.tokx_v(dut.tokx_v_i),.tokx_slot(dut.tokx_slot_i),.tokx_tok(dut.tokx_tok_i[16:0]),.amax_v(dut.amax_v_i),.amax_slot(dut.amax_slot_i),.amax_tok(dut.amax_tok_i[16:0]),.acc_v(dut.acc_v_i),.acc_g(dut.acc_g_i),.stok(ds_stok),.ttok(ds_ttok),.acc_done(ds_done),.acc_any(ds_any),.acc_a(ds_a),.n_emit(ds_emit),.bonus(ds_bonus));
reg [17:0] targets[0:7]; reg [17:0] drafts[0:7];
integer mode,g,a,i,tests=0;
task tick; begin @(posedge clk); #0.001; @(negedge clk); end endtask
task check_ds; integer z; begin
 if({acc_done,acc_any,acc_a,n_emit,bonus} !== {ds_done,ds_any,ds_a,ds_emit,1'b0,ds_bonus}) $fatal(1,"DS lockstep scalar");
 for(z=0;z<8;z=z+1) if(stok[z*18+:18] !== {1'b0,ds_stok[z*17+:17]} || ttok[z*18+:18] !== {1'b0,ds_ttok[z*17+:17]}) $fatal(1,"DS lockstep slot %d",z);
end endtask
initial begin
 repeat(3) tick(); rst_n=1; tick();
 for(mode=0;mode<3;mode=mode+1) for(g=0;g<=7;g=g+1) for(a=0;a<=g;a=a+1) begin
  for(i=0;i<8;i=i+1) begin
   targets[i]=(mode==0) ? 18'd129000+i : (i%3==0 ? 18'd131071 : i%3==1 ? 18'd131072 : 18'd151935);
   drafts[i]=i==0 ? 18'd42 : targets[i-1];
   if(mode==2) targets[i]=18'd262143-i;
  end
  if(mode==2) for(i=1;i<8;i=i+1) drafts[i]=targets[i-1];
  // Every reject position; mode1 mismatch differs ONLY in bit17.
  if(a<g) drafts[a+1]=(mode==1) ? targets[a]^18'h20000 : targets[a]^18'd1;
  start_tok=drafts[0]; start_v=1; tick(); start_v=0;
  for(i=0;i<8;i=i+1) begin
   amax_v=1; amax_slot=i; amax_tok=targets[i];
   tokx_v=(i>0); tokx_slot=i; tokx_tok=drafts[i]; tick();
  end
  tokx_v=0; amax_v=0; acc_g=g; acc_v=1; tick(); acc_v=0; if(PINREG) tick();
  if(!acc_done || acc_a!==a[2:0] || n_emit!==a+1 || bonus!==targets[a]) $fatal(1,"ACCEPT mismatch mode%0d g%0d a%0d got%0d bonus%h",mode,g,a,acc_a,bonus);
  if(mode==0) check_ds();
  for(i=0;i<8;i=i+1) if(ttok[i*18+:18]!==targets[i]) $fatal(1,"target lost bit17");
  tests=tests+1; tick(); if(acc_done) $fatal(1,"done pulse stretched");
 end
 $display("HGI_ACCEPT18 PASS %0d cases DS lockstep/high-bit reject/bonus/all lengths",tests); $finish;
end
endmodule
