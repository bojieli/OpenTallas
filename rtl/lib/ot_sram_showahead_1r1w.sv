`timescale 1ns/1ps
// Registered continuous SRAM read, NEW on a current logical same-address write.
// WREG=1 registers macro write pins; its previous logical write also forwards.
// Caller supplies ra = NEXT head and independent same-depth resets per16-bit slice.
// No reset/storage ECC is added to the SRAM. Two unconditional payload registers
// avoid a W-bit hit-enable cone; reset-distinct kept flags each select <=16 bits.
module ot_sram_showahead_1r1w #(
 parameter integer W=553, AW=3, WREG=1, NS=(W+SB-1)/SB, MUT=0, LOCAL_HIT=0, SB=16, LOCAL_RA=0, LOCAL_WA=0, DEPTH=(1<<AW),
 // S81-LEPENH2 10-20 opt-in (default 0 = unchanged): LOCAL_WD gives every 128-bit bank its own retained write-data
 // register (same WREG edge, D = wd) driving ONLY that macro's wd_in.  The shared wdata register keeps its forwarding
 // loads (prevdata, the q select) in the logic band; the macro copy can sit at the band edge under the bank's pins
 // (row-constrained packing 10-20: 41 of 42 nets > 405 um were wdata -> top-row wd_in, max 443.7 um).
 parameter integer LOCAL_WD=0
)(input wire clk, input wire [NS-1:0] rst_n,
 input wire we, input wire [AW-1:0] wa, input wire [W-1:0] wd,
 input wire [AW-1:0] ra, output wire [W-1:0] q,
 // advance_a/b feed ONLY the opt-in LOCAL_RA read pointer; callers without LOCAL_RA may omit them (default 0, unused).
 input wire advance_a=1'b0, input wire advance_b=1'b0);
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
 always @(posedge clk or negedge rst_n[0]) if(!rst_n[0]) wv<=1'b0; else wv<=we;
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
 wire [NB*128-1:0] padded_wd={{(NB*128-W){1'b0}},wd};
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
  wire [127:0] bank_wd;
  if(LOCAL_WD!=0 && WREG!=0) begin:g_local_wd
   (* keep=1 *) ot_sram_showahead_writedata u_wd(.clk(clk),.d(padded_wd[b*128+:128]),.q(bank_wd));
  end else begin:g_shared_wd
   assign bank_wd=padded[b*128+:128];
  end
`ifdef OT_SRAM_P192
  // pitch-192 pin-limited 32x128 (51.408x39.960, W/E 4.98/4.95 pins/um); same ports/timing contract (a87cecc1e)
  ot_sram_1r1w_32x128_m1_p192_rc u_m(.clk(clk),
`else
  ot_sram_1r1w_32x128_m1 u_m(.clk(clk),
`endif
   .r_ce_in(1'b1),.r_addr_in(5'(read_addr_local[b*AW+:AW])),
   .rd_out(raw[b*128+:128]),.w_ce_in(bank_we),.w_addr_in(5'(bank_wa)),
   .wd_in(bank_wd),.w_mask_in({128{1'b1}}));
 end
 for(s=0;s<NS;s=s+1) begin:g_slice
  localparam integer LO=s*SB, SW=(W-LO<SB)?W-LO:SB;
  (* keep="true" *) reg cur_q, prev_q;
  always @(posedge clk or negedge rst_n[s])
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
 always @(posedge clk or negedge rn) if(!rn) ptr<=0;else ptr<=next_addr;
endmodule

// Opt-in same-age write-pin copies; distinct retained flop drivers prevent a
// shared write address/CE net spanning all five physical SRAM banks.
(* keep_hierarchy=1 *) module ot_sram_showahead_writepins #(
 parameter integer AW=3)(input wire clk,rn,we,input wire [AW-1:0] wa,
 output wire qwe,output wire [AW-1:0] qwa);
 (* keep=1 *) reg valid_q;
 (* keep=1 *) reg [AW-1:0] addr_q;
 always @(posedge clk or negedge rn) if(!rn) valid_q<=0;else valid_q<=we;
 always @(posedge clk) addr_q<=wa;
 assign qwe=valid_q;assign qwa=addr_q;
endmodule

// Opt-in (LOCAL_WD) same-age write-data copy of one 128-bit bank: retained flops whose only loads are that macro's
// wd_in pins (no reset: write data is qualified by the bank's registered CE, as the shared wdata register).
(* keep_hierarchy=1 *) module ot_sram_showahead_writedata(
 input wire clk,input wire [127:0] d,output wire [127:0] q);
 (* keep=1 *) reg [127:0] data_q;
 always @(posedge clk) data_q<=d;
 assign q=data_q;
endmodule
