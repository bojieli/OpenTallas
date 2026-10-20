`timescale 1ns/1ps
`default_nettype none
// Static edge-count-preserving delay. SAFE_STORAGE remains opt-in until physical qualification.
//
// SAFE_STORAGE=1, N>=3 (L2H-PAD 10-19, successor of codex 0c3eecf04/366dc27e7):
//  * reset lands in 2 registered stages (async assert, 2-edge release): stage 1 rs_s1 (the only rs sink), stage 2 =
//    KEPT copies (hbfd_pad_rst_land, keep_hierarchy, non-parameterised, reset by rs_s1) each driving <= 16 flops;
//  * the 2 landing edges are paid by 2 face data stages (face0 = registered input pin, face1), so the core
//    is an exact (N-2)-edge store whose clock-0 is the landed reset: total stays exactly N edges, II1,
//    zero added external edges, identical async zero-reset ABI;
//  * core ingress copies are KEPT hierarchy instances (hbfd_pad_icopy, keep_hierarchy on the definition so
//    the $paramod derivative keeps it): one copy per 16 ring rows, <= 16 row loads per Q
//    (0c3eecf04 used an unpacked array that Yosys aliased to one FF per bit: 17 Q x 115 loads).
module hbfd_pad #(parameter integer W=17, N=1, SAFE_STORAGE=0,
                  parameter integer TEST_MUTANT=0)(
 input wire ck, rs, input wire [W-1:0] i, output wire [W-1:0] o);
 generate if (!SAFE_STORAGE || N<3) begin:g_compat
   ot_hdc_delay #(.W(W),.D(N),.RESET(1)) u_dly(.clk(ck),.rst_n(rs),.d(i),.q(o));
 end else begin:g_ring
   localparam integer NC=N-2;              // core edges after the two face stages
   localparam integer NG=(W+31)/32;        // 32-bit warmup groups
   // reset groups of <= 16 flops: capture bits (ring core) or all W*NC stage bits (tiny core)
   localparam integer NH=(N-2<3) ? (W*(N-2)+15)/16 : (W+15)/16;
   localparam integer MACRO=(W*N>2048);
   // ---- reset landing: stage 1 (one flop, drives the stage-2 copies only) ----
   (* keep = 1 *) reg rs_s1;
   always @(posedge ck or negedge rs)
     if(!rs) rs_s1<=1'b0; else rs_s1<=1'b1;
   wire rl_ctl;                            // ptr + macro enables
   wire [NG-1:0] rl_age;                   // one copy per warmup counter
   wire [NH-1:0] rl_cap;                   // one copy per 16 capture/output flops
   hbfd_pad_rst_land u_rl_ctl(.ck(ck),.rn(rs_s1),.q(rl_ctl));
   for(genvar g=0;g<NG;g=g+1) begin:g_rl_age
     hbfd_pad_rst_land u_rl(.ck(ck),.rn(rs_s1),.q(rl_age[g]));
   end
   for(genvar h=0;h<NH;h=h+1) begin:g_rl_cap
     hbfd_pad_rst_land u_rl(.ck(ck),.rn(rs_s1),.q(rl_cap[h]));
   end
   // ---- face data stages: pay the two landing edges (no reset: the core masks stale epochs) ----
   reg [W-1:0] face0, face1;
   always @(posedge ck) begin
     face0<=i;
     face1<=(TEST_MUTANT==1 && NC<3) ? i : face0;   // tiny-core wrong-slot mutant
   end
   wire [W-1:0] core_o;
   if (NC<3) begin:g_tiny
     // N=3/4: core of 1/2 reset stages (a ring would cost more flops than it saves).
     reg [W*NC-1:0] dl;
     wire [NH-1:0] rl_dl = (TEST_MUTANT==4) ? {NH{rs}} : rl_cap;   // mutant 4: unlanded reset
     // stage bit s*W+k resets from copy (s*W+k)/16
     for(genvar k=0;k<W;k=k+1) begin:g_bit
       for(genvar s=0;s<NC;s=s+1) begin:g_st
         if (TEST_MUTANT==2) begin:g_nrst                          // mutant 2: no warmup mask
           always @(posedge ck) dl[s*W+k]<=(s==0)?face1[k]:dl[(s-1)*W+k];
         end else begin:g_rst
           always @(posedge ck or negedge rl_dl[(s*W+k)/16])
             if(!rl_dl[(s*W+k)/16]) dl[s*W+k]<=1'b0;
             else dl[s*W+k]<=(s==0)?face1[k]:dl[(s-1)*W+k];
         end
       end
     end
     assign core_o=dl[W*NC-1 -: W];
   end else begin:g_core
     localparam integer AW=$clog2(NC), DEPTH=NC;
     localparam integer CW=$clog2(NC+1), NB=(W+255)/256;
     reg [AW-1:0] ptr;
     (* keep = 1 *) reg [CW-1:0] age [0:NG-1];
     reg [W-1:0] capture;
     wire [NG-1:0] ready;
     for(genvar g=0;g<NG;g=g+1) begin:g_warmup
       always @(posedge ck or negedge rl_age[g])
         if(!rl_age[g]) age[g]<='0;
         else if(age[g]<CW'(NC)) age[g]<=age[g]+1'b1;
       assign ready[g]=age[g]>=CW'(NC-1-(TEST_MUTANT==2));
     end
     always @(posedge ck or negedge rl_ctl)
       if (!rl_ctl) ptr<='0;
       else ptr<=(ptr==AW'(NC-1)) ? '0 : ptr+1'b1;
     if (MACRO) begin:g_macro
       // core ingress: one registered copy feeding the macro write port (1 load per Q)
       reg [W-1:0] ingress;
       always @(posedge ck) ingress<=face1;
       wire [6:0] wa=7'(ptr);
       // The extra synchronous macro read edge is paid by this lookahead, never added to N.
       wire [6:0] ra= TEST_MUTANT==4 ? wa :
            7'((ptr>=AW'(NC-3+(TEST_MUTANT==1))) ?
               ptr-AW'(NC-3+(TEST_MUTANT==1)) : ptr+AW'(NC-(NC-3+(TEST_MUTANT==1))));
       wire [NB*256-1:0] padded={{(NB*256-W){1'b0}},ingress};
       wire [NB*256-1:0] rd;
       for(genvar b=0;b<NB;b=b+1) begin:g_bank
         ot_sram_1r1w_128x256_m1_r2c2 u_sram(
           .clk(ck),.r_ce_in(rl_ctl),.r_addr_in(ra),.rd_out(rd[b*256+:256]),
           .w_ce_in(rl_ctl),.w_addr_in(wa),.wd_in(padded[b*256+:256]),.w_mask_in({256{1'b1}}),
           .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
       end
       for(genvar k=0;k<W;k=k+1) begin:g_cap
         always @(posedge ck or negedge rl_cap[k/16])
           if(!rl_cap[k/16]) capture[k]<=1'b0;
           else capture[k]<=ready[k/32] ? rd[k] : 1'b0;
       end
`ifndef SYNTHESIS
       initial if(NC<4 || DEPTH>128) $fatal(1,"Unsupported SRAM pad N=%0d",N);
       always @(posedge ck) if(rl_ctl && TEST_MUTANT!=4 && ra==wa) $fatal(1,"PAD_READ_WRITE_COLLISION");
`endif
     end else begin:g_small
       // Finite circular array: only one row is written per edge, no shift chain or bulk reset.
       // Rows written during reset/landing are stale epochs masked by the age certificate.
       reg [W-1:0] mem [0:DEPTH-1];
       localparam integer NI=(NC+15)/16;
       wire [W-1:0] ingress_local [0:NI-1];
       for(genvar g=0;g<NI;g=g+1) begin:g_ingress
         hbfd_pad_icopy #(.W(W)) u_ic(.ck(ck),.d(face1),.q(ingress_local[g]));
       end
       wire [AW-1:0] ra = TEST_MUTANT==4 ? ptr :
           ((ptr>=AW'(NC-2+(TEST_MUTANT==1))) ?
            ptr-AW'(NC-2+(TEST_MUTANT==1)) : ptr+AW'(NC-(NC-2+(TEST_MUTANT==1))));
       for(genvar row=0;row<NC;row=row+1) begin:g_row
         always @(posedge ck) if(ptr==AW'(row)) mem[row]<=ingress_local[row/16];
       end
       for(genvar k=0;k<W;k=k+1) begin:g_cap
         always @(posedge ck or negedge rl_cap[k/16])
           if(!rl_cap[k/16]) capture[k]<=1'b0;
           else capture[k]<=ready[k/32] ? mem[ra][k] : 1'b0;
       end
     end
     assign core_o=capture;
   end
   if(TEST_MUTANT==3) begin:g_latency_mutant
     reg[W-1:0] extra;
     always @(posedge ck or negedge rl_cap[0]) if(!rl_cap[0]) extra<='0; else extra<=core_o;
     assign o=extra;
   end else assign o=core_o;
 end endgenerate
endmodule

// Reset landing stage 2: one kept copy (non-parameterised, keep_hierarchy) per <=16 reset loads.
(* keep_hierarchy *)
// Asynchronous assert through stage 1 (rn = rs_s1), release on the edge after stage 1 releases: the rs port has ONE
// sink (rs_s1) and rs_s1 drives only the copies' reset pins (<= 28 copies at W=274).
module hbfd_pad_rst_land(input wire ck, rn, output reg q);
 always @(posedge ck or negedge rn)
   if(!rn) q<=1'b0; else q<=1'b1;
endmodule

// Core ingress copy: kept hierarchy so synthesis cannot alias the copies back into one FF per bit.
(* keep_hierarchy *)
module hbfd_pad_icopy #(parameter integer W=17)(input wire ck, input wire [W-1:0] d, output reg [W-1:0] q);
 always @(posedge ck) q<=d;
endmodule

// Standalone tile wrapper for the worst ring shape of the d4g pad inventory (17 b x 115 edges).
module hbfd_pad_r17x115(input wire ck, rs, input wire [16:0] i, output wire [16:0] o);
 hbfd_pad #(.W(17),.N(115),.SAFE_STORAGE(1)) u_pad(.ck(ck),.rs(rs),.i(i),.o(o));
endmodule
`default_nettype wire
