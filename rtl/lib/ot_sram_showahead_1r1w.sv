`timescale 1ns/1ps
`ifndef OT_LEP_AR
`ifdef OT_S81SL_LEP_SYNCRST
// R7 (ELEM-LEP/A 10-21, opt-in): reset only gates control/valid D inputs (synchronous); no async RESETN pin, so no
// removal check sits on two different clock leaves (r6v FF -34.22: local_r -> frame flop 1.7 um, 51 ps leaf skew).
// Release edges are unchanged; assertion needs the clock running for >= 4 cycles (benches hold reset 8).
`define OT_LEP_AR(r)
`else
`define OT_LEP_AR(r) or negedge r
`endif
`endif
// Registered continuous SRAM read, NEW on a current logical same-address write.
// WREG=1 registers macro write pins; its previous logical write also forwards.
// Caller supplies ra = NEXT head and independent same-depth resets per16-bit slice.
// No reset/storage ECC is added to the SRAM. Two unconditional payload registers
// avoid a W-bit hit-enable cone; reset-distinct kept flags each select <=16 bits.
module ot_sram_showahead_1r1w #(
 parameter integer W=553, AW=3, WREG=1, NS=(W+SB-1)/SB, MUT=0, LOCAL_HIT=0, SB=16, LOCAL_RA=0, LOCAL_WA=0, DEPTH=(1<<AW)
)(input wire clk, input wire [NS-1:0] rst_n,
 input wire we, input wire [AW-1:0] wa, input wire [W-1:0] wd,
 input wire [AW-1:0] ra, output wire [W-1:0] q,
 input wire advance_a,advance_b);
 localparam integer NB=(W+127)/128;
 wire [NB*AW-1:0] read_addr_local;
 generate for(genvar ar=0;ar<NB;ar=ar+1) begin:g_read_region
  if(LOCAL_RA!=0) begin:g_local
   (* keep=1 *) ot_sram_showahead_readptr #(.AW(AW),.DEPTH(DEPTH)) u_ptr(
    .clk(clk),.rn(rst_n[(ar*128)/SB]),.advance_a(advance_a),.advance_b(advance_b),
    .next_addr(read_addr_local[ar*AW+:AW]));
  end else begin:g_shared assign read_addr_local[ar*AW+:AW]=ra;end
 end endgenerate
 reg wv; reg [AW-1:0] waddr; reg [W-1:0] wdata, prevdata;
 always @(posedge clk `OT_LEP_AR(rst_n[0])) if(!rst_n[0]) wv<=1'b0; else wv<=we;
 always @(posedge clk) begin waddr<=wa; wdata<=wd; prevdata<=wdata; end
 wire current_hit=we && wa==ra;
 wire previous_hit=(WREG!=0) && wv && waddr==ra;
 localparam integer HG=(NS+15)/16;
 wire [HG-1:0] local_current_hit,local_previous_hit;
 genvar h;
 generate for(h=0;h<HG;h=h+1) begin:g_hit
  if(LOCAL_HIT) begin:g_local
   // Fixed width avoids paramod keep-name mismatch. Each output drives <=16
   // distinct slice flag D pins; no extra clock edge or shared35-load hit.
   (* keep=1 *) ot_sram_showahead_hit5 u_current(.enable(we),.a(5'(wa)),.b(5'(read_addr_local[((h*16*SB)/128)*AW+:AW])),.hit(local_current_hit[h]));
   (* keep=1 *) ot_sram_showahead_hit5 u_previous(.enable((WREG!=0)&&wv),.a(5'(waddr)),.b(5'(read_addr_local[((h*16*SB)/128)*AW+:AW])),.hit(local_previous_hit[h]));
  end else begin:g_legacy
   assign local_current_hit[h]=current_hit;
   assign local_previous_hit[h]=previous_hit;
  end
 end endgenerate
 wire mw=(WREG!=0) ? wv : we;
 wire [AW-1:0] mwa=(WREG!=0) ? waddr : wa;
 wire [W-1:0] mwd=(WREG!=0) ? wdata : wd;
 wire [NB*128-1:0] padded={{(NB*128-W){1'b0}},mwd}, raw;
 genvar b,s;
 generate for(b=0;b<NB;b=b+1) begin:g_bank
  wire bank_we; wire [AW-1:0] bank_wa;
  if(LOCAL_WA!=0 && WREG!=0) begin:g_local_write
   // Same original WREG edge, one retained address/enable copy per128-bit
   // physical SRAM bank. No added write/read/forwarding edge.
   (* keep=1 *) ot_sram_showahead_writepins #(.AW(AW)) u_wp(
    .clk(clk),.rn(rst_n[(b*128)/SB]),.we(we),.wa(wa),
    .qwe(bank_we),.qwa(bank_wa));
  end else begin:g_shared_write
   assign bank_we=mw;assign bank_wa=mwa;
  end
  ot_sram_1r1w_32x128_m1 u_m(.clk(clk),.r_ce_in(1'b1),.r_addr_in(5'(read_addr_local[b*AW+:AW])),
   .rd_out(raw[b*128+:128]),.w_ce_in(bank_we),.w_addr_in(5'(bank_wa)),
   .wd_in(padded[b*128+:128]),.w_mask_in({128{1'b1}}));
 end
 for(s=0;s<NS;s=s+1) begin:g_slice
  localparam integer LO=s*SB, SW=(W-LO<SB)?W-LO:SB;
  (* keep="true" *) reg cur_q, prev_q;
  always @(posedge clk `OT_LEP_AR(rst_n[s]))
   if(!rst_n[s]) begin cur_q<=1'b0; prev_q<=1'b0; end
   else begin cur_q<=(MUT==1)?1'b0:local_current_hit[s/16]; prev_q<=(MUT==2)?1'b0:local_previous_hit[s/16]; end
  assign q[LO+:SW]=cur_q ? wdata[LO+:SW] : prev_q ? prevdata[LO+:SW] : raw[LO+:SW];
 end endgenerate
`ifndef SYNTHESIS
 initial begin
  if(AW>5 || AW<1 || W<1 || NS!=(W+SB-1)/SB || (SB!=8 && SB!=16)) $fatal(1,"ot_sram_showahead_1r1w invalid shape");
 end
`endif
endmodule

// Unparameterized kept comparator: independent physical copies per <=16 slices.
(* keep_hierarchy=1 *) module ot_sram_showahead_hit5(
 input wire enable,input wire [4:0] a,b,output wire hit);
 assign hit=enable&&(a==b);
endmodule

// Opt-in replicated circular read pointer. The next address is combinational
// from the same logical pair-pop; no additional SRAM read/capture edge.
(* keep_hierarchy=1 *) module ot_sram_showahead_readptr #(
 parameter integer AW=3,DEPTH=(1<<AW))(
 input wire clk,rn,advance_a,advance_b,output wire [AW-1:0] next_addr);
 (* keep=1 *) reg [AW-1:0] ptr;
 wire advance=advance_a && advance_b;
 assign next_addr=advance?((ptr==AW'(DEPTH-1))?'0:ptr+1'b1):ptr;
 always @(posedge clk `OT_LEP_AR(rn)) if(!rn) ptr<=0;else ptr<=next_addr;
endmodule

// Opt-in same-age write-pin copies; distinct retained flop drivers prevent a
// shared write address/CE net spanning all five physical SRAM banks.
(* keep_hierarchy=1 *) module ot_sram_showahead_writepins #(
 parameter integer AW=3)(input wire clk,rn,we,input wire [AW-1:0] wa,
 output wire qwe,output wire [AW-1:0] qwa);
 (* keep=1 *) reg valid_q;
 (* keep=1 *) reg [AW-1:0] addr_q;
 always @(posedge clk `OT_LEP_AR(rn)) if(!rn) valid_q<=0;else valid_q<=we;
 always @(posedge clk) addr_q<=wa;
 assign qwe=valid_q;assign qwa=addr_q;
endmodule

// STW-S81c-COLLA2-LEP (10-22, opt-in OT_S81SL_LEP_RXLAND): same logical FIFO head as ot_sram_showahead_1r1w
// (LOCAL_HIT/LOCAL_RA/LOCAL_WA/WREG=1 form), but q is a LANDING REGISTER beside the macros instead of the macro
// rd_out + bypass mux.  The macro now reads ONE ROW AHEAD (bank pointer copies reset to 1 = rp+1, same advance), so
// during every cycle qn = current logical mem[rp+1] (same cur/prev write forwarding as before).  On each edge the
// landing register loads the row the head pointer will hold:
//   logical write on this edge to rp_nx (we && wa==rp_nx)  -> wd           (empty FIFO, or n==1 with pop)
//   else pop (advance_a && advance_b)                      -> qn = mem[rp+1]
//   else                                                   -> hold (= mem[rp])
// => q == mem[rp] in every cycle the FIFO is non-empty (induction), i.e. the old q; same edge, 0 added cycles.
// Per 16-bit group: own kept write-hit comparator + kept pop AND (each select drives <= 32 mapped mux pins); per
// bank: head pointer copy (reset 0) for the hit compare and read-ahead pointer copy (reset 1) for the macro /
// forwarding.  Native fan-out: advance copy 0 feeds the 2x5 pointers, copies 1/2 the pop ANDs of groups <18 / >=18;
// write-hit enable / address copy 0 / 1 likewise (callers pass kept same-value copies).
module ot_sram_showahead_1r1w_land #(
 parameter integer W=553, AW=4, SB=8, NS=(W+SB-1)/SB, DEPTH=(1<<AW)
)(input wire clk, input wire [NS-1:0] rst_n,
 input wire we, input wire [AW-1:0] wa, input wire [W-1:0] wd,
 input wire [1:0] we_l, input wire [2*AW-1:0] wa_l,
 input wire [2:0] advance_a,advance_b,
 output wire [W-1:0] q);
 localparam integer NB=(W+127)/128, GB=16, NG=(W+GB-1)/GB, GH=18;
 wire [NB*AW-1:0] ra1, ra0;
 genvar ar,h,b,s,g;
 generate for(ar=0;ar<NB;ar=ar+1) begin:g_read_region
   // read-ahead copy on a mid-bank slice reset leaf (same release edge; keeps the bank's first leaf <= 32 loads)
   localparam integer R1S=(ar*128)/SB + (((W-ar*128)>64)?8:2);
   (* keep=1 *) ot_sram_showahead_readptr1 #(.AW(AW),.DEPTH(DEPTH)) u_ptr1(
    .clk(clk),.rn(rst_n[R1S]),.advance_a(advance_a[0]),.advance_b(advance_b[0]),.next_addr(ra1[ar*AW+:AW]));
   (* keep=1 *) ot_sram_showahead_readptr #(.AW(AW),.DEPTH(DEPTH)) u_ptr(
    .clk(clk),.rn(rst_n[(ar*128)/SB]),.advance_a(advance_a[0]),.advance_b(advance_b[0]),.next_addr(ra0[ar*AW+:AW]));
 end endgenerate
 reg wv; reg [AW-1:0] waddr; reg [W-1:0] wdata, prevdata;
 always @(posedge clk `OT_LEP_AR(rst_n[0])) if(!rst_n[0]) wv<=1'b0; else wv<=we;
 always @(posedge clk) begin waddr<=wa; wdata<=wd; prevdata<=wdata; end
 localparam integer HG=(NS+15)/16;
 wire [HG-1:0] local_current_hit,local_previous_hit;
 generate for(h=0;h<HG;h=h+1) begin:g_hit
   (* keep=1 *) ot_sram_showahead_hit5 u_current(.enable(we),.a(5'(wa)),.b(5'(ra1[((h*16*SB)/128)*AW+:AW])),.hit(local_current_hit[h]));
   (* keep=1 *) ot_sram_showahead_hit5 u_previous(.enable(wv),.a(5'(waddr)),.b(5'(ra1[((h*16*SB)/128)*AW+:AW])),.hit(local_previous_hit[h]));
 end endgenerate
 wire [NB*128-1:0] padded={{(NB*128-W){1'b0}},wdata}, raw;
 generate for(b=0;b<NB;b=b+1) begin:g_bank
  wire bank_we; wire [AW-1:0] bank_wa;
  (* keep=1 *) ot_sram_showahead_writepins #(.AW(AW)) u_wp(
   .clk(clk),.rn(rst_n[(b*128)/SB]),.we(we),.wa(wa),.qwe(bank_we),.qwa(bank_wa));
  ot_sram_1r1w_32x128_m1 u_m(.clk(clk),.r_ce_in(1'b1),.r_addr_in(5'(ra1[b*AW+:AW])),
   .rd_out(raw[b*128+:128]),.w_ce_in(bank_we),.w_addr_in(5'(bank_wa)),
   .wd_in(padded[b*128+:128]),.w_mask_in({128{1'b1}}));
 end endgenerate
 wire [W-1:0] qn;
 generate for(s=0;s<NS;s=s+1) begin:g_slice
  localparam integer LO=s*SB, SW=(W-LO<SB)?W-LO:SB;
  (* keep="true" *) reg cur_q, prev_q;
  always @(posedge clk `OT_LEP_AR(rst_n[s]))
   if(!rst_n[s]) begin cur_q<=1'b0; prev_q<=1'b0; end
   else begin cur_q<=local_current_hit[s/16]; prev_q<=local_previous_hit[s/16]; end
  assign qn[LO+:SW]=cur_q ? wdata[LO+:SW] : prev_q ? prevdata[LO+:SW] : raw[LO+:SW];
 end endgenerate
 generate for(g=0;g<NG;g=g+1) begin:g_land
  localparam integer LO=g*GB, GW=(W-LO<GB)?W-LO:GB, C=(g<GH)?0:1;
  wire sel_w, sel_p;
  (* keep=1 *) ot_sram_showahead_hit5 u_whit(.enable(we_l[C]),.a(5'(wa_l[C*AW+:AW])),.b(5'(ra0[((g*GB)/128)*AW+:AW])),.hit(sel_w));
  (* keep=1 *) ot_sram_showahead_pop2 u_pop(.a(advance_a[1+C]),.b(advance_b[1+C]),.q(sel_p));
  reg [GW-1:0] hd;
`ifdef OT_SRAM_LAND_MUT_NOAHEAD
  always @(posedge clk) hd <= sel_w ? wd[LO+:GW] : sel_p ? raw[LO+:GW] : hd;   // MUTANT: no read-ahead forwarding
`elsif OT_SRAM_LAND_MUT_NOWHIT
  always @(posedge clk) hd <= sel_p ? qn[LO+:GW] : hd;                         // MUTANT: no same-edge write landing
`else
  always @(posedge clk) hd <= sel_w ? wd[LO+:GW] : sel_p ? qn[LO+:GW] : hd;
`endif
  assign q[LO+:GW]=hd;
 end endgenerate
`ifndef SYNTHESIS
 initial begin
  if(AW>5 || AW<1 || W<1 || NS!=(W+SB-1)/SB || (SB!=8 && SB!=16) || DEPTH<2) $fatal(1,"ot_sram_showahead_1r1w_land invalid shape");
 end
`endif
endmodule

// Read-ahead pointer copy: identical advance to ot_sram_showahead_readptr, reset to 1 (= head pointer + 1).
(* keep_hierarchy=1 *) module ot_sram_showahead_readptr1 #(
 parameter integer AW=3,DEPTH=(1<<AW))(
 input wire clk,rn,advance_a,advance_b,output wire [AW-1:0] next_addr);
 (* keep=1 *) reg [AW-1:0] ptr;
 wire advance=advance_a && advance_b;
 assign next_addr=advance?((ptr==AW'(DEPTH-1))?'0:ptr+1'b1):ptr;
 always @(posedge clk `OT_LEP_AR(rn)) if(!rn) ptr<=AW'(1);else ptr<=next_addr;
endmodule

// Kept pop select copy: one per 32 landing bits.
(* keep_hierarchy=1 *) module ot_sram_showahead_pop2(input wire a,b,output wire q);
 assign q=a && b;
endmodule
