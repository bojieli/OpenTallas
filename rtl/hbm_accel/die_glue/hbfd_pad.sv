`timescale 1ns/1ps
`default_nettype none
// Static edge-count-preserving delay. SAFE_STORAGE remains opt-in until physical qualification.
module hbfd_pad #(parameter integer W=17, N=1, SAFE_STORAGE=0,
                  parameter integer TEST_MUTANT=0)(
 input wire ck, rs, input wire [W-1:0] i, output wire [W-1:0] o);
 generate if (!SAFE_STORAGE || N<3) begin:g_compat
   ot_hdc_delay #(.W(W),.D(N),.RESET(1)) u_dly(.clk(ck),.rst_n(rs),.d(i),.q(o));
 end else begin:g_ring
   localparam integer AW=$clog2(N), DEPTH=N;
   localparam integer CW=$clog2(N+1), NB=(W+255)/256;
   reg [AW-1:0] ptr;
   localparam integer NG=(W+31)/32;
   (* keep = 1 *) reg [CW-1:0] age [0:NG-1];
   reg [W-1:0] ingress;
   reg [W-1:0] capture;
   wire [NG-1:0] ready;
   for(genvar g=0;g<NG;g=g+1) begin:g_warmup
     always @(posedge ck or negedge rs)
       if(!rs) age[g]<='0;
       else if(age[g]<CW'(N)) age[g]<=age[g]+1'b1;
     assign ready[g]=age[g]>=CW'(N-1-(TEST_MUTANT==2));
   end
   always @(posedge ck or negedge rs)
     if (!rs) ptr<='0;
     else ptr<=(ptr==AW'(N-1)) ? '0 : ptr+1'b1;
   // Data array and ingress need no reset: the finite age certificate suppresses stale epochs.
   always @(posedge ck) ingress<=i;
   if (W*N>2048) begin:g_macro
     wire [6:0] wa=7'(ptr);
     // The extra synchronous macro read edge is paid by this lookahead, never added to N.
     wire [6:0] ra= TEST_MUTANT==4 ? wa :
          7'((ptr>=AW'(N-3+(TEST_MUTANT==1))) ?
             ptr-AW'(N-3+(TEST_MUTANT==1)) : ptr+AW'(N-(N-3+(TEST_MUTANT==1))));
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
       else for(integer k=0;k<W;k=k+1) capture[k]<=ready[k/32] ? rd[k] : 1'b0;
`ifndef SYNTHESIS
     initial if(N<4 || DEPTH>128) $fatal(1,"Unsupported SRAM pad N=%0d",N);
     always @(posedge ck) if(rs && TEST_MUTANT!=4 && ra==wa) $fatal(1,"PAD_READ_WRITE_COLLISION");
`endif
   end else begin:g_small
     // Finite circular array: only one row is written per edge, no shift chain or bulk reset.
     reg [W-1:0] mem [0:DEPTH-1];
     localparam integer NI=(N+15)/16;
     (* keep = 1 *) reg [W-1:0] ingress_local [0:NI-1];
     for(genvar g=0;g<NI;g=g+1) begin:g_ingress
       always @(posedge ck) ingress_local[g]<=i;
     end
     wire [AW-1:0] ra = TEST_MUTANT==4 ? ptr :
         ((ptr>=AW'(N-2+(TEST_MUTANT==1))) ?
          ptr-AW'(N-2+(TEST_MUTANT==1)) : ptr+AW'(N-(N-2+(TEST_MUTANT==1))));
     for(genvar row=0;row<N;row=row+1) begin:g_row
       always @(posedge ck) if(rs && ptr==AW'(row)) mem[row]<=ingress_local[row/16];
     end
     always @(posedge ck or negedge rs)
       if(!rs) capture<='0;
       else for(integer k=0;k<W;k=k+1) capture[k]<=ready[k/32] ? mem[ra][k] : 1'b0;
   end
   if(TEST_MUTANT==3) begin:g_latency_mutant
     reg[W-1:0] extra;
     always @(posedge ck or negedge rs) if(!rs) extra<='0; else extra<=capture;
     assign o=extra;
   end else assign o=capture;
 end endgenerate
endmodule
`default_nettype wire
