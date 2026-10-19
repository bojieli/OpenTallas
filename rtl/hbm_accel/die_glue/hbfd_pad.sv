`timescale 1ns/1ps
`default_nettype none
// Static edge-count-preserving delay. SAFE_STORAGE remains opt-in until physical qualification.
module hbfd_pad #(parameter integer W=17, N=1, SAFE_STORAGE=0,
                  parameter integer TEST_MUTANT=0)(
 input wire ck, rs, input wire [W-1:0] i, output wire [W-1:0] o);
 generate if (!SAFE_STORAGE || N<3) begin:g_compat
   ot_hdc_delay #(.W(W),.D(N),.RESET(1)) u_dly(.clk(ck),.rst_n(rs),.d(i),.q(o));
 end else begin:g_ring
   localparam integer AW=$clog2(N), DEPTH=1<<AW;
   localparam integer CW=$clog2(N+1), NB=(W+255)/256;
   reg [AW-1:0] ptr;
   reg [CW-1:0] age;
   reg [W-1:0] ingress;
   reg [W-1:0] capture;
   wire ready = age >= CW'(N-1-(TEST_MUTANT==2));
   always @(posedge ck or negedge rs)
     if (!rs) begin ptr<='0; age<='0; end
     else begin ptr<=ptr+1'b1; if (age<CW'(N)) age<=age+1'b1; end
   // Data array and ingress need no reset: the finite age certificate suppresses stale epochs.
   always @(posedge ck) ingress<=i;
   if (W*N>2048) begin:g_macro
     wire [6:0] wa=7'(ptr);
     // The extra synchronous macro read edge is paid by this lookahead, never added to N.
     wire [6:0] ra= TEST_MUTANT==4 ? wa :
          7'((ptr-AW'(N-3+(TEST_MUTANT==1))) & AW'(DEPTH-1));
     wire [NB*256-1:0] padded={{(NB*256-W){1'b0}},ingress};
     wire [NB*256-1:0] rd;
     for(genvar b=0;b<NB;b=b+1) begin:g_bank
       ot_sram_1r1w_128x256_m1_r2c2 u_sram(
         .clk(ck),.r_ce_in(rs),.r_addr_in(ra),.rd_out(rd[b*256+:256]),
         .w_ce_in(rs),.w_addr_in(wa),.wd_in(padded[b*256+:256]),.w_mask_in({256{1'b1}}),
         .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
     end
     always @(posedge ck or negedge rs)
       if(!rs) capture<='0;
       else capture<=ready ? rd[W-1:0] : {W{1'b0}};
`ifndef SYNTHESIS
     initial if(N<4 || DEPTH>128) $fatal(1,"Unsupported SRAM pad N=%0d",N);
     always @(posedge ck) if(rs && TEST_MUTANT!=4 && ra==wa) $fatal(1,"PAD_READ_WRITE_COLLISION");
`endif
   end else begin:g_small
     // Finite circular array: only one row is written per edge, no shift chain or bulk reset.
     reg [W-1:0] mem [0:DEPTH-1];
     wire [AW-1:0] ra = TEST_MUTANT==4 ? ptr :
         ptr-AW'(N-2+(TEST_MUTANT==1));
     always @(posedge ck) if(rs) mem[ptr]<=ingress;
     always @(posedge ck or negedge rs)
       if(!rs) capture<='0;
       else capture<=ready ? mem[ra] : {W{1'b0}};
   end
   if(TEST_MUTANT==3) begin:g_latency_mutant
     reg[W-1:0] extra;
     always @(posedge ck or negedge rs) if(!rs) extra<='0; else extra<=capture;
     assign o=extra;
   end else assign o=capture;
 end endgenerate
endmodule
`default_nettype wire
