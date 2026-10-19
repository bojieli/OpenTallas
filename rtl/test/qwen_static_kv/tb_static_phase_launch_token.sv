`timescale 1ps/1fs
// KVJ-E2 2026-10-17: the compiled per-token phase launches of one per-group control tile through the actual
// qkd_static_kv_phase_launch, for NTOK token runs at the compiled token period (d2d_cal_image.svh D2D_TOKEN_PERIOD).
// +LAUNCH=<file>: one hex word per launch {toggle_offset[31:12] (core edges after the token run start), lanes[10:8]
// {vgo,kgo,ctrl_go}, layer[5:0]} from kv_static_programme.py (phase.launch_table).  Token n starts S0 + n*PERIOD core
// edges after the first rn-active edge (index 6, q = PH0 = 0, HBM edge shared: the declared die contract origin);
// S0 = 768 puts the first run on the reset-release beat phase.  Independent scoreboard: every launch must arrive on
// its fixed HBM output edge (phase_launch.launch: first HBM edge after the toggle + 2) with its held metadata, and the
// tile must never fault.  A period that is not a multiple of 768 core edges must fault (run_phase_launch_token.py).
module tb_static_phase_launch_token #(parameter integer PERIOD=249600, parameter integer NTOK=3, parameter integer NL=108);
 reg ck=0,hck=0,rst_n=0,hrst_n=0;
 initial begin #1000;forever begin ck=1;#312.5;ck=0;#312.5;end end
 initial begin #142;forever begin hck=1;#384;hck=0;#384;end end
 reg cg=0,kg=0,vg=0;reg[13:0]ctx=14'd4096;reg[15:0]ep=16'h0b0b;reg[5:0]layer=0;
 wire ch,kh,vh,fc,fh,ic,ih;wire[13:0]cth;wire[15:0]eph;wire[5:0]lh;
 qkd_static_kv_phase_launch #(.PH0(0),.SAFE_LOW_U(200),.SAFE_HIGH_U(600),.META_HOLD_CORE(8),.MUT(0))dut(
 .ck(ck),.rst_n(rst_n),.hck(hck),.hrst_n(hrst_n),.ctrl_go(cg),.kgo(kg),.vgo(vg),.ctx_t(ctx),.epoch(ep),.layer(layer),
 .ctrl_go_h(ch),.kgo_h(kh),.vgo_h(vh),.ctx_t_h(cth),.epoch_h(eph),.layer_h(lh),
 .fault_core(fc),.fault_hbm(fh),.idle_core(ic),.idle_hbm(ih));
 localparam integer S0=768;
 reg[31:0]lw[0:NL-1];
 longint core_i=-1,hbm_i=-7;integer received=0,scheduled=0,n,k;
 // expected outputs in HBM-edge order (launches are increasing, so their output edges are too)
 longint ee[0:NL*NTOK-1];reg[2:0]em[0:NL*NTOK-1];reg[5:0]ml[0:NL*NTOK-1];integer rp=0;
 always @(posedge ck)core_i<=core_i+1;
 always @(posedge hck)begin
  hbm_i=hbm_i+1;#1;
  if(hbm_i>=0)begin
   if(rp<scheduled&&ee[rp]==hbm_i)begin
    if({vh,kh,ch}!==em[rp])$fatal(1,"PHTOK FAIL HBM edge %0d lanes %b expected %b",hbm_i,{vh,kh,ch},em[rp]);
    if(lh!==ml[rp]||cth!==ctx||eph!==ep)$fatal(1,"PHTOK FAIL held metadata at HBM edge %0d",hbm_i);
    received=received+1;rp=rp+1;
   end else if({vh,kh,ch}!==3'b0)$fatal(1,"PHTOK FAIL unexpected launch at HBM edge %0d",hbm_i);
  end
 end
 always @(posedge ck)if(rst_n&&(fc||fh))$fatal(1,"PHTOK FAIL phase launch fault core %0d (token %0d) fc=%b fh=%b",core_i,n,fc,fh);
 reg[8*256-1:0]f;longint t,first;
 initial begin
  if(!$value$plusargs("LAUNCH=%s",f))$fatal(1,"+LAUNCH required");
  $readmemh(f,lw);
  repeat(5)@(posedge ck);@(negedge ck);rst_n=1;hrst_n=1;
  for(n=0;n<NTOK;n=n+1)for(k=0;k<NL;k=k+1)if(lw[k][10:8]!=0)begin
   t=6+S0+longint'(n)*PERIOD+lw[k][31:12];      // toggle core edge index; input set before edge t-1 (capture), toggles at t
   while(core_i<t-2)@(negedge ck);
   if(core_i!=t-2)$fatal(1,"PHTOK FAIL launch table not increasing");
   {vg,kg,cg}=lw[k][10:8];layer=lw[k][5:0];
   first=((t-6)*625)/768+1;
   ee[scheduled]=first+2;em[scheduled]=lw[k][10:8];ml[scheduled]=lw[k][5:0];scheduled=scheduled+1;
   @(negedge ck);cg=0;kg=0;vg=0;
  end
  repeat(40)@(posedge ck);
  if(received!=scheduled||!ic||!ih)$fatal(1,"PHTOK FAIL received %0d of %0d",received,scheduled);
  $display("PHTOK PASS tokens=%0d period=%0d launches=%0d received=%0d no fault",NTOK,PERIOD,scheduled,received);$finish;
 end
endmodule
