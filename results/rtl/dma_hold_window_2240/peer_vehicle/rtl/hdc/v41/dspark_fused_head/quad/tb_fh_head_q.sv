`timescale 1ns/1ps
// Lockstep: ot_hdc_v41_fh_head_q (top + 4 hardened quadrants) == ot_hdc_v41_fh_macro_ctx MARGIN=1 HARD_LANE=1 (FPIPE as
// given), every output every cycle, open loop with a checked-endpoint responder (request -> commit -> checked reply ->
// warm ACK) driven from the reference. Valid-address fused traffic, SRAM writes, index writes, periodic resets.
module tb_fh_head_q #(parameter integer FPIPE = 1, parameter integer QPIN = 0, parameter integer SAFE = 0, parameter integer HQ = 0, parameter integer LRET = 0, parameter integer OREG = 0, parameter integer CYCLES = 9000);
 localparam integer W=16,G=4,AW=24,NW=16,TW=1+1+1+1+1+2+AW+AW+3*(NW+1)+2+AW+3+AW+1;
 import ot_dsrom_vm_pkg::*;
 reg clk=0; always #0.5 clk=~clk;
 reg rst_n=0,cold_n=0;
 wire rdy=!ref0.g_actual_native_load.u_native.guard_busy;
 reg commit_busy=0,commit_ack_v=0,s3_v_in=0,go_fus=0,tv_in=0,ov1_in=0;
 reg native_reply_capture=0,native_reply_v=0;
 reg [31:0] native_ordinal=0;
 reg [1266:0] native_checked_reply=0;
 reg [7:0] commit_ack_id=0; reg [23:0] commit_ack_word=0; reg [15:0] commit_ack_mask=0;
 reg [TW-1:0] tag=0; reg [G*W*32-1:0] res_in=0,wr_data=0; reg [G-1:0] wr_en=0,o_we1_in=0; reg [G*AW-1:0] wr_addr=0,o_addr1_in=0;
 reg [G*W-1:0] wr_mask=0,o_mask1_in=0,leaf_mask_in=0; reg [AW-1:0] i_iaddr=0; reg [4:0] busy_in=0;
 reg [NW-1:0] leaf_row_in=0,am_idx_in=0;
`define OUTS(s) wire rqv``s,rpv``s,cw``s,cd``s,rv``s,f``s; wire [3:0] pc``s,we``s,re``s; wire [2830:0] cr``s; wire [1266:0] cp``s; \
 wire [7:0] ci``s; wire [G*AW-1:0] ra``s,oa``s; wire [TW-1:0] rt``s; wire [49*64-1:0] lf``s; wire [63:0] om``s; wire [2047:0] od``s; wire [0:0] am``s,c1``s,c2``s,rc``s;
 `OUTS(0)
 `OUTS(1)
`define CONN(s) .clk(clk),.rst_n(rst_n),.commit_busy(commit_busy),.commit_ack_v(commit_ack_v),.native_cold_n(cold_n),.native_request_ready(rdy), \
 .native_reply_capture(native_reply_capture),.native_reply_v(native_reply_v),.native_ordinal(native_ordinal),.native_request_owner(47'h123456789ab), \
 .native_checked_reply(native_checked_reply),.native_request_checked_v(rqv``s),.native_reply_checked_v(rpv``s),.native_permission_capture(pc``s), \
 .native_captured_request(cr``s),.native_captured_request_check(c1``s),.native_captured_reply(cp``s),.native_captured_reply_check(c2``s), \
 .commit_ack_id(commit_ack_id),.commit_ack_word(commit_ack_word),.commit_ack_mask(commit_ack_mask),.commit_warm(cw``s),.commit_debt(cd``s),.commit_id(ci``s), \
 .s3_v_in(s3_v_in),.a_tag_p_in(tag),.res_in(res_in),.wr_en(wr_en),.wr_addr(wr_addr),.wr_mask(wr_mask),.wr_data(wr_data),.ra_re(re``s),.ra_addr(ra``s), \
 .go_fus(go_fus),.i_iaddr(i_iaddr),.busy_in(busy_in),.o_we1_in(o_we1_in),.o_addr1_in(o_addr1_in),.o_mask1_in(o_mask1_in),.leaf_mask_in(leaf_mask_in), \
 .leaf_row_in(leaf_row_in),.tv_in(tv_in),.ov1_in(ov1_in),.am_idx_in(am_idx_in),.r_tag(rt``s),.r_v(rv``s),.leaf(lf``s),.o_we(we``s),.o_addr(oa``s), \
 .o_mask(om``s),.o_data(od``s),.fault(f``s),.result_capture(rc``s),.argmax_level1(am``s)
 ot_hdc_v41_fh_macro_ctx #(.ALAT(7),.CAPTURE(1),.RETURN_EXTRA(5+QPIN),.PROTECT_SPLIT(1),.RETIRE(1),.VM_ENDPOINT(1),.VM_GUARD(1),
   .HARD_LANE(1),.MARGIN(1),.FPIPE(FPIPE),.QPIN(QPIN),.SAFE(SAFE)) ref0(`CONN(0));
 ot_hdc_v41_fh_head_q #(.FPIPE(FPIPE),.QPIN(QPIN),.SAFE(SAFE),.HQ(HQ),.LRET(LRET),.OREG(OREG)) dut(`CONN(1));
 // checked endpoint responder (as tb_hdc_core_v41_mtp_slice_checked), driven by the reference
 reg [1:0] cv=0; request_t pk0,pk1; reg sent=0;
 integer i,j,seed=11,writes=0,acks=0,fused=0,iws=0,faults=0,leafv=0;
 function [TW-1:0] mktag(input integer s);
  reg [23:0] oa; reg [2:0] m;
  begin
   oa=24'(4*($urandom(s)%400)); m=3'(1+($urandom%7));
   mktag={1'($urandom),1'($urandom),1'($urandom),1'($urandom),1'($urandom),2'b00,oa,24'd1,17'($urandom),17'($urandom),17'($urandom),
          2'b00,24'($urandom),m,24'($urandom),1'($urandom)};
  end
 endfunction
 function [31:0] fin(input [31:0] v); fin={v[31],1'b0,v[29:0]}; endfunction
 initial begin
  for(i=0;i<CYCLES;i=i+1) begin
   @(negedge clk);
   if(i>8 && rst_n && cold_n && ({rqv0,rpv0,pc0,cr0,cp0,cw0,cd0,ci0,re0,ra0,rt0,rv0,lf0,we0,oa0,om0,od0,f0,am0,c10,c20,rc0}!==
       {rqv1,rpv1,pc1,cr1,cp1,cw1,cd1,ci1,re1,ra1,rt1,rv1,lf1,we1,oa1,om1,od1,f1,am1,c11,c21,rc1})) begin
    if({cr0,cp0,rqv0,rpv0,pc0}!=={cr1,cp1,rqv1,rpv1,pc1}) $display("diff endpoint"); if({cw0,cd0,ci0}!=={cw1,cd1,ci1}) $display("diff commit");
    if(lf0!==lf1) $display("diff leaf"); if(od0!==od1) $display("diff o_data"); if(om0!==om1) $display("diff o_mask");
    if(oa0!==oa1) $display("diff o_addr"); if(we0!==we1) $display("diff o_we"); if(rt0!==rt1||rv0!==rv1) $display("diff tag");
    if(f0!==f1) $display("diff fault"); if({ra0,re0}!=={ra1,re1}) $display("diff ra");
    $fatal(1,"head_q lockstep %0d",i);
   end
   if(|we0) writes=writes+1; if(ref0.g_actual_native_load.u_native.head_ack_v) acks=acks+1;
   if(ref0.u_head.u_fh.protected_v) fused=fused+1; if(ref0.u_head.iw_go) iws=iws+1; if(f0) faults=faults+1; if(ref0.child_leaf_v) leafv=leafv+1;
   // resets
   rst_n=!((i%2000)<3) || (i>=4 && i<520); cold_n=rst_n;
   // traffic: busy windows and quiet windows (index writes drain)
   s3_v_in=((i%200)<120)&&(($urandom%3)==0); tag=mktag(i);
   go_fus=(($urandom%48)==0); tv_in=((i%200)<120)&&($urandom%2); ov1_in=((i%200)<120)&&($urandom%2);
   busy_in=((i%200)<120&&($urandom%4)==0)?5'($urandom):0; o_we1_in=((i%200)<120)?4'($urandom):4'b0;
   commit_busy=((i%200)<120)&&(($urandom%16)==0);
   for(j=0;j<G*W;j=j+1) begin res_in[32*j+:32]=fin($urandom); wr_data[32*j+:32]=fin($urandom); end
   for(j=0;j<G;j=j+1) begin wr_addr[24*j+:24]=24'(4*($urandom%505)+j); o_addr1_in[24*j+:24]=24'($urandom%32768); end
   wr_en=(($urandom%4)==0)?4'($urandom):0; wr_mask={$urandom,$urandom}; o_mask1_in={$urandom,$urandom}; leaf_mask_in={$urandom,$urandom};
   i_iaddr=24'($urandom%524288); leaf_row_in=16'($urandom); am_idx_in=16'($urandom);
   if((i%2000)==1500) wr_addr[23:0]=24'hffffff; wr_en[0]=wr_en[0]||((i%2000)==1500);           // rare address fault
   if(i>=4 && i<4+505) begin                                   // initialise every SRAM row once (contents survive resets)
    {s3_v_in,go_fus,tv_in,ov1_in,busy_in,o_we1_in,commit_busy}=0; wr_en=4'hf; wr_mask='1;
    for(j=0;j<G;j=j+1) wr_addr[24*j+:24]=24'(4*(i-4)+j);
   end
  end
  if(faults<100||writes<50||fused<200||iws<10||acks<3||leafv<200) $fatal(1,"coverage writes=%0d fused=%0d iw=%0d acks=%0d leaf=%0d",writes,fused,iws,acks,leafv);
  $display("PASS head_q (HQ=%0d) == macro_ctx QPIN=%0d FPIPE=%0d cycles=%0d writes=%0d fused=%0d index_writes=%0d acks=%0d leaf=%0d fault_cycles=%0d",
           HQ,QPIN,FPIPE,CYCLES,writes,fused,iws,acks,leafv,faults);
  $finish;
 end
 always @(posedge clk) begin
  if(!cold_n) begin cv<=0;sent<=0;native_reply_capture<=0;native_reply_v<=0;native_ordinal<=0; end
  else begin
   if(|we0) native_ordinal<=native_ordinal+1;
   if(!ref0.g_actual_native_load.u_native.guard_busy) sent<=0;
   cv[0]<=rqv0&&!sent; cv[1]<=cv[0];
   if(rqv0&&!sent) begin pk0<=cr0; sent<=1; end
   if(cv[0]) pk1<=pk0;
   native_reply_capture<=cv[1];
   if(cv[1]) begin native_checked_reply<={1'b1,pk1.ordinal,pk1.owner,2'b0,1024'b0,pk1.we,pk1.wa,pk1.wm,1'b0}; native_reply_v<=1; end
   if(native_reply_v&&rpv0) native_reply_v<=0;
  end
 end
endmodule
