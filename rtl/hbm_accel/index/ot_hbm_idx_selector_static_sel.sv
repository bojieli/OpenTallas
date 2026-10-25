`default_nettype none
// LH-UNREAD F-S 2026-10-19: ot_hbm_idx_selector_static_sel = the die's SELECTED-ONLY IDX selector master.
// Successor of ot_hbm_idx_selector_static (canonical file unchanged; benches/other users keep it). The die (GEN2e2
// contract) reads only selected_v / selected_line / fault; the emit-readback face (op 8: out_v, out_line) and the
// observation face (threshold_observe, selected_observe) had no consumer (2,444 unread bits, ROOT held class
// selector_optional_readback). They are REMOVED here, with their registers (core out_line 2368 FF + shell pin flops
// 2368+4+16+56): no tie-off, no spare port. The production IDX compiler (tools/hbm_idx_static_calendar.py) issues
// selector ops 1..6 only; op 8 (emit) would read into a face that no longer exists, so it raises the existing sticky
// fault one core edge after issue (MUT=3 drops that check: negative bench). Op 7 (flush) is kept (SRAM write path,
// same as the canonical). selected_v / selected_line / fault are cycle-exact with the canonical master for every
// op stream without op 8 (tb_hbm_idx_selector_sel_eq). Pin latency unchanged (+1 in, +1 out).
// SAFE-DESIGN checklist (owner 10-19):
//  1 Pins: every input/output keeps its one kept pin flop; rst_n 2-flop release (unchanged)            PASS
//  2 Reach: no new wire; port count drops by 2,444 bits                                               PASS
//  3 Fanout: no new fan-out; fault gains one 2-input term (op==8)                                      PASS
//  4 Depth: op==8 compare is 4-bit, one OR into the existing fault flop; no in->out comb path          PASS
//  5 Storage: 12 SRAM macros unchanged; 4,816 flops removed, none added                               PASS
//  6 Floorplan: smaller pin face (die soft SYNTH block, no hard view); outline from synthesis           PASS (re-synth)
//  7 Clock: one clk_ctl root as canonical (IDX-SMALL)                                                  PASS
//  8 Schedule: static; no added cycle; compiler unchanged (op 8 never issued)                         PASS
// NL (HBM-BIND B2 2026-10-24, lane hbm-bind-idx): number of 16-lane score lists (592 b each: one SRAM row group of 3
// macros, one histogram, one tie share, one compactor). Default 4 = as built (bit-identical, bench
// rtl/test/hbm_idx_static/run_idx_selector_nl.sh). The 4-quadrant r18h5 die fills lists 0 = {SE, SW} and 1 = {NE, NW}
// (lists 2, 3 are fed 1184'd0 by that die); the B2 die (NW + NE) instantiates NL 1 with list 0 = {NE, NW}
// (xq_N.y): the same lanes, the same records and the same selected_v / selected_line / fault edges as list 1 of the
// as-built master with the other lists empty. Ports scale: in_line / selected_line NL*592, selected_v NL, clk_q NL,
// clk_mem 3*NL. Latency unchanged (+1 in, +1 out pin flops; core edges per op as before).
// MUT 4 (bench only): the op-5 bin count sums lists 0..NL-2 only (the last list is left out of the threshold search).
module ot_hbm_idx_selector_static_sel_core #(parameter integer MUT=0, parameter integer NL=4)(
 input wire clk_ctl,input wire [NL-1:0] clk_q,input wire [3*NL-1:0] clk_mem,
 input wire rst_n,input wire [3:0] op,input wire [1:0] pass,
 input wire [7:0] addr,input wire [9:0] k,
 input wire [NL*592-1:0] in_line,
 output reg [NL-1:0] selected_v,output reg [NL*592-1:0] selected_line,
 output reg fault
);
 localparam integer EW=37,W=16,LW=592;
 function automatic [15:0] orderkey(input [15:0] x);
  orderkey=x[15]?~x:(x^16'h8000);
 endfunction
 reg [15:0] threshold;
 reg [13:0] rank_left;
 reg found;
 reg [13:0] hist[0:NL-1][0:63];
 reg [13:0] ties[0:NL-1];
 reg [13:0] selected[0:NL-1];
 reg [NL-1:0] qfault;
 wire [15:0] prior_mask=(pass==0)?16'd0:((pass==1)?16'hf800:16'hffc0);
 wire [3:0] shift=(pass==0)?4'd11:((pass==1)?4'd6:4'd0);
 wire [15:0] binmask=(pass==2)?16'd63:16'd31;
 integer allcount,remain;
 always @(posedge clk_ctl or negedge rst_n)begin
  if(!rst_n)begin threshold<=0;rank_left<=0;found<=0;fault<=0;for(integer q=0;q<NL;q=q+1)ties[q]<=0;end
  else begin
   if(|qfault)fault<=1;
   if(op==8&&MUT!=3)fault<=1; // emit readback face removed: op8 is illegal on this master
   if(op==1)begin threshold<=0;rank_left<={4'b0,k};found<=0;if(k>512||k==0)fault<=1;end
   if(op==3)found<=0;
   if(op==5&&!found)begin
    allcount=0;for(integer q=0;q<((MUT==4)?NL-1:NL);q=q+1)allcount=allcount+int'(hist[q][addr[5:0]]);
    if(int'(rank_left)>allcount)rank_left<=rank_left-14'(allcount);
    else begin
     threshold <= (threshold & prior_mask) | (16'(addr[5:0]) << shift);found<=1;
     if(pass==2)begin
      remain=int'(rank_left);
      for(integer q=0;q<NL;q=q+1)begin
       ties[q]<=14'((remain>int'(hist[q][addr[5:0]]))?int'(hist[q][addr[5:0]]):remain);
       remain=remain-int'(hist[q][addr[5:0]]);if(remain<0)remain=0;
      end
     end
    end
   end
  end
 end
 for(genvar q=0;q<NL;q=q+1)begin:gq
  reg rv;reg[3:0]rop;reg[1:0]rpass;reg[7:0]raddr;
  wire re=op==4||op==6;
  wire [767:0] raw;
  reg [1183:0] buf_q;
  reg [4:0] fill;
  reg [5:0] wp;
  reg [13:0] tie_rem;
  reg comp_started;
  reg [1183:0] packed_next;
  reg [5:0] fill_next;
  reg [13:0] ties_next;
  reg [13:0] chosen_next;
  reg [15:0] mask_choose;
  reg [19:0] last_id;
  integer count;
  reg [15:0] ky;
  reg choose;
  wire compact=rv&&rop==6;
  wire pack_write=compact&&fill_next>=16;
  wire flush=op==7&&fill!=0;
  wire we=op==2||pack_write||flush;
  wire [7:0]wa=(op==2)?addr:{2'd0,wp};
  wire [591:0] wd=(op==2)?in_line[q*LW+:LW]:(pack_write?packed_next[591:0]:buf_q[591:0]);
  wire [767:0]wide_wd={176'd0,wd};
  for(genvar m=0;m<3;m=m+1)begin:gm
   ot_sram_1r1w_256x256_m2_r2c2 mem(.clk(clk_mem[q*3+m]),.r_ce_in(re),.r_addr_in(addr),.rd_out(raw[m*256+:256]),
    .w_ce_in(we),.w_addr_in(wa),.wd_in(wide_wd[m*256+:256]),.w_mask_in({256{1'b1}}),
    .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
  end
  always @*begin
   packed_next=buf_q;fill_next={1'b0,fill};ties_next=comp_started?tie_rem:ties[q];chosen_next=0;mask_choose=0;
   for(integer l=0;l<W;l=l+1)begin
    ky=orderkey(raw[l*EW+1+:16]);
    choose=raw[l*EW]&&(ky>threshold||(ky==threshold&&ties_next!=0));
    if(MUT==1)choose=raw[l*EW]&&(ky>=threshold);
    if(compact&&choose)begin
     packed_next[fill_next*EW+:EW]=raw[l*EW+:EW];fill_next=fill_next+1;chosen_next=chosen_next+1;mask_choose[l]=1;
     if(ky==threshold&&ties_next!=0)ties_next=ties_next-1;
    end
   end
  end
  always @(posedge clk_q[q] or negedge rst_n)begin
   if(!rst_n)begin
    rv<=0;buf_q<=0;fill<=0;wp<=0;tie_rem<=0;comp_started<=0;selected[q]<=0;qfault[q]<=0;selected_v[q]<=0;last_id<=0;
    for(integer b=0;b<64;b=b+1)hist[q][b]<=0;
   end else begin
    rv<=re;rop<=op;rpass<=pass;raddr<=addr;selected_v[q]<=compact;
    for(integer l=0;l<W;l=l+1)begin selected_line[q*LW+l*EW+:EW]<=raw[l*EW+:EW];selected_line[q*LW+l*EW]<=compact&&mask_choose[l];end
    if(op==1)begin buf_q<=0;fill<=0;wp<=0;tie_rem<=0;comp_started<=0;selected[q]<=0;last_id<=0;end
    if(op==3)for(integer b=0;b<64;b=b+1)hist[q][b]<=0;
    if((rv&&rop==4)||op==2)begin
     for(integer b=0;b<64;b=b+1)begin
      count=0;
      for(integer l=0;l<W;l=l+1)begin
       if(op==2)begin
        if(in_line[q*LW+l*EW]&&(orderkey(in_line[q*LW+l*EW+1+:16])>>11)==16'(b))count=count+1;
       end else if(raw[l*EW]&&((orderkey(raw[l*EW+1+:16])&prior_mask)==(threshold&prior_mask))&&
         ((orderkey(raw[l*EW+1+:16]) >> shift)&binmask)==16'(b))count=count+1;
      end
      hist[q][b]<=hist[q][b]+14'(count);
     end
    end
    if(compact)begin
     comp_started<=1;tie_rem<=ties_next;selected[q]<=selected[q]+chosen_next;
     if(pack_write)begin buf_q<=packed_next>>LW;fill<=5'(fill_next-16);wp<=wp+1;end
     else begin buf_q<=packed_next;fill<=5'(fill_next);end
     if(selected[q]+chosen_next>512)qfault[q]<=1;
     if(pack_write&&wa>raddr)qfault[q]<=1; // never overwrite an unread source line
     for(integer l=0;l<W;l=l+1)if(raw[l*EW])begin
      if((raddr!=0||l!=0)&&raw[l*EW+17+:20]<=last_id)qfault[q]<=1;
      last_id<=raw[l*EW+17+:20];
     end
    end
    if(flush)begin wp<=wp+1;buf_q<=0;fill<=0;end
    if((op==2&&(compact||flush))||(op==3&&rv&&rop==4))qfault[q]<=1;
   end
  end
 end
endmodule
`default_nettype wire
`default_nettype none
module ot_hbm_idx_selector_static_sel #(parameter integer MUT=0, parameter integer NL=4)(   // NL: see the core
 input wire clk_ctl,input wire [NL-1:0] clk_q,input wire [3*NL-1:0] clk_mem,
 input wire rst_n,input wire [3:0] op,input wire [1:0] pass,
 input wire [7:0] addr,input wire [9:0] k,
 input wire [NL*592-1:0] in_line,
 output reg [NL-1:0] selected_v,output reg [NL*592-1:0] selected_line,
 output reg fault
);
 // rst_n: async assert, 2-edge release on clk_ctl; the core's resets (async and synchronous uses on every
 // same-PLL phase-0 root) come from this one kept register, so no input port feeds another root's data pins.
 (* keep *) reg [1:0] rst_sync;
 always @(posedge clk_ctl or negedge rst_n) if(!rst_n) rst_sync<=2'b00; else rst_sync<={rst_sync[0],1'b1};
 wire rst_core_n=rst_sync[1];
 (* keep *) reg [3:0] op_r;(* keep *) reg [1:0] pass_r;(* keep *) reg [7:0] addr_r;(* keep *) reg [9:0] k_r;
 (* keep *) reg [NL*592-1:0] in_r;
 wire [NL-1:0] c_sel_v;wire [NL*592-1:0] c_sel_line;wire c_fault;
 always @(posedge clk_ctl)begin
  op_r<=op;pass_r<=pass;addr_r<=addr;k_r<=k;in_r<=in_line;
  selected_v<=c_sel_v;selected_line<=c_sel_line;fault<=c_fault;
 end
 ot_hbm_idx_selector_static_sel_core #(.MUT(MUT),.NL(NL)) core(.clk_ctl(clk_ctl),.clk_q({NL{clk_ctl}}),.clk_mem({(3*NL){clk_ctl}}),.rst_n(rst_core_n),
  .op(op_r),.pass(pass_r),.addr(addr_r),.k(k_r),.in_line(in_r),
  .selected_v(c_sel_v),.selected_line(c_sel_line),.fault(c_fault));
endmodule
`default_nettype wire
