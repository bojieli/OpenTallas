`timescale 1ns/1ps
`default_nettype none
// L2H-COLLP 10-19: shift-equivalence bench of the v74p COLL protocol leaf (ot_hgi_coll_ctl_v5_core_safephys MUL_PIPE 1)
// against the v74 leaf (MUL_PIPE 0) on random traffic. The parent contract of v74p is a uniform +1 COLL issue edge:
//   inst            = the uop-pipe word one edge later than v74 (d3 instead of d2)
//   tap_iteration / tap_steps, hgi_start, hgi_busy, issue_done = the SAME edges as v74 (the leaf delays them inside)
//   tkm_done/tkm_busy, dest_v, rc_v/rc_tag, vm_rv, rst_n = one edge later (siblings / VM on the shifted timeline)
// PASS: every output bit of v74p after edge t equals the v74 output after edge t-1, for every edge after reset, with
// non-vacuity counters (address / injection / fault activity). Mutants (must FAIL):
//   MUT 1 v74p RTL with MUL_PIPE 0 (products one edge early vs the instruction)   MUT 2 taps one edge late
//   MUT 3 hgi_start/hgi_busy/issue_done fed one edge late as well (double delay)    MUT 4 s_rgx low byte cut (rgx products)
module tb_hgi_coll_ctl_mulpipe_safephys;
 parameter integer MUT=0,SHAPE=0,NCYC=6000;
 localparam integer NPT=SHAPE==0?1:2, SOLO=SHAPE==0?0:1, ND=NPT+13;
 localparam integer OW=136+2+32+160*3+2+66+132+4+NPT*8+NPT*16*3+1+32+24;
 reg clk=0; always #0.416 clk=~clk;
 reg rst_n=0,rst_d=0;
 reg [1535:0] inst=0,inst_d=0; reg [31:0] it=0,it_d=0; reg [87:0] st=0;
 reg hs=0,hb=0,idn=0,hs_d=0,hb_d=0,idn_d=0;
 reg tkd=0,tkb=0,rcv=0,tkd_d=0,tkb_d=0,rcv_d=0; reg [2:0] rct=0,rct_d=0; reg [ND-1:0] dv=0,dv_d=0; reg [7:0] vrv=0,vrv_d=0;
 always @(posedge clk) begin
  rst_d<=rst_n; inst_d<=inst; it_d<=it; hs_d<=hs; hb_d<=hb; idn_d<=idn;
  tkd_d<=tkd; tkb_d<=tkb; rcv_d<=rcv; rct_d<=rct; dv_d<=dv; vrv_d<=vrv;
 end
 wire [OW-1:0] ro,dout;
 `define COLLP_PORTS(o) .vm_req_pin(o[0+:136]),.inj_req_pin(o[136+:2]),.inj_idx_pin(o[138+:32]),.inj_addr_pin(o[170+:160]), \
   .delivery_obase_pin(o[330+:160]),.rgx_addr_pin(o[490+:160]),.inj_source_v(o[650+:2]),.inj_source_meta(o[652+:66]), \
   .vm_source_meta(o[718+:132]),.vm_assembled_v(o[850+:4]),.held_epoch(o[854+:NPT*8]), \
   .wr_sequence_pin(o[854+NPT*8+:NPT*16]),.rd_sequence_pin(o[854+NPT*24+:NPT*16]),.rx_sequence_pin(o[854+NPT*40+:NPT*16]), \
   .protocol_fault(o[854+NPT*56]),.cycles(o[855+NPT*56+:32]),.vm_sel_d(o[887+NPT*56+:24])
 ot_hgi_coll_ctl_v5_core_safephys #(.NPT(NPT),.SOLO(SOLO),.VM_RT(74),.SAFE_DELAY(1),.MUL_PIPE(0)) ref_l(
  .clk_control(clk),.rst_n(rst_n),.inst(inst),.tap_iteration(it),.tap_steps(st),.hgi_start(hs),.hgi_busy(hb),.issue_done(idn),
  .tkm_done(tkd),.tkm_busy(tkb),.dest_v(dv),.rc_v(rcv),.rc_tag(rct),.vm_rv(vrv),`COLLP_PORTS(ro));
 ot_hgi_coll_ctl_v5_core_safephys #(.NPT(NPT),.SOLO(SOLO),.VM_RT(74),.SAFE_DELAY(1),.MUL_PIPE(MUT==1?0:1)) dut(
  .clk_control(clk),.rst_n(rst_d),.inst(inst_d),.tap_iteration(MUT==2?it_d:it),
  .tap_steps(MUT==4?{st[87:72],st[71:64]&8'h00,st[63:0]}:st),
  .hgi_start(MUT==3?hs_d:hs),.hgi_busy(MUT==3?hb_d:hb),.issue_done(MUT==3?idn_d:idn),
  .tkm_done(tkd_d),.tkm_busy(tkb_d),.dest_v(dv_d),.rc_v(rcv_d),.rc_tag(rct_d),.vm_rv(vrv_d),`COLLP_PORTS(dout));
 reg [OW-1:0] ro_q=0; always @(posedge clk) ro_q<=ro;
 integer cyc=0,checked=0,errors=0,act_rgx=0,act_del=0,act_inj=0,act_vm=0,act_fault=0,act_asm=0;
 integer first_bad=-1;
 always @(negedge clk) begin
  cyc=cyc+1;
  if(rst_d && rst_n && cyc>400) begin
   checked=checked+1;
   if(dout!==ro_q) begin
    if(errors<6) for(integer b=0;b<OW;b=b+1) if(dout[b]!==ro_q[b]) begin $display("COLL_MULP mismatch cyc%0d bit%0d dut=%b ref_d1=%b",cyc,b,dout[b],ro_q[b]); b=OW; end
    errors=errors+1;
   end
   if(|dout[490+:160]) act_rgx=act_rgx+1; if(|dout[330+:160]) act_del=act_del+1; if(|dout[170+:160]) act_inj=act_inj+1;
   if(|dout[0+:136]) act_vm=act_vm+1; if(dout[854+NPT*56]) act_fault=act_fault+1; if(|dout[850+:4]) act_asm=act_asm+1;
  end
 end
 initial begin
  repeat(300) @(negedge clk); rst_n=1; repeat(4) @(negedge clk);
  for(integer t=0;t<NCYC;t=t+1) begin
   // phases: random dense instruction words, sparse words, and quiet stretches; fault-free stretches re-arm via reset pulses
   if((t%1500)<1000 && ($urandom%2)) begin for(integer w=0;w<48;w=w+1) inst[w*32+:32]=$urandom; end else inst=0;
   it=$urandom; st={$urandom,$urandom,$urandom};
   hs=($urandom%8)==0; hb=($urandom%3)==0; idn=($urandom%16)==0;
   tkd=($urandom%16)==0; tkb=($urandom%4)==0; rcv=($urandom%8)==0; rct=3'($urandom); dv=ND'($urandom%4==0?$urandom:0);
   vrv=8'($urandom%4==0?$urandom:0);
   if((t%1500)==1490) rst_n=0; else if((t%1500)==1499) rst_n=1;
   @(negedge clk);
  end
  inst=0; repeat(200) @(negedge clk);
  if(errors==0 && checked>0 && act_rgx>0 && act_del>0 && act_inj>0 && act_vm>0)
   $display("COLL_MULP_PASS SHAPE%0d NPT%0d checked%0d out_bits%0d act rgx%0d del%0d inj%0d vm%0d asm%0d fault%0d",SHAPE,NPT,checked,OW,act_rgx,act_del,act_inj,act_vm,act_asm,act_fault);
  else begin
   $display("COLL_MULP_FAIL MUT%0d SHAPE%0d errors%0d checked%0d act rgx%0d del%0d inj%0d vm%0d",MUT,SHAPE,errors,checked,act_rgx,act_del,act_inj,act_vm);
   $fatal(1,"COLL MULP");
  end
  $finish;
 end
endmodule
`default_nettype wire
