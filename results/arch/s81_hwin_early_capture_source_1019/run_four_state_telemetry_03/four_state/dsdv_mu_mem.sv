`timescale 1ns/1ps
// Small 1R1W SRAM banks with registered write pins and exact registered OLD-data read.
// A read after the previous cycle write forwards its registered payload. No schedule cycles added.
module dsdv_mu_mem #(parameter integer W=64, parameter integer AW=6, parameter integer N=(W+15)/16, parameter integer S=(W+7)/8)(
 input wire ck, we, input wire [S-1:0] rst_n, input wire [AW-1:0] wa, input wire [W-1:0] wd,
 input wire [AW-1:0] ra, output wire [W-1:0] q);
 reg wv; wire [S-1:0] hitq; reg [AW-1:0] waddr; reg [W-1:0] wdata, fd;
 wire hit=wv && ra==waddr;
 always @(posedge ck or negedge rst_n[0])
   if (!rst_n[0]) wv<=1'b0; else wv<=we;
 // Reset-distinct registered addresses keep event-bank ports physically independent.
 always @(posedge ck or negedge rst_n[0]) if(!rst_n[0]) waddr<={AW{1'b0}}; else waddr<=wa;
 always @(posedge ck) begin wdata<=wd; fd<=wdata; end
 wire [N*16-1:0] padded, raw;
 assign padded={{(N*16-W){1'b0}},wdata};
 wire [N*16-1:0] forwarded, picked;
 assign forwarded={{(N*16-W){1'b0}},fd};
 genvar k; generate
 for(k=0;k<S;k=k+1) begin:g_select
   localparam integer LO=8*k, SW=(W-LO<8)?W-LO:8;
   // Each reset-distinct select drives at most eight payload mux bits.
   (* keep *) reg hit_r;
   assign hitq[k]=hit_r;
   always @(posedge ck or negedge rst_n[k]) if(!rst_n[k]) hit_r<=1'b0; else hit_r<=hit;
   assign picked[LO+:SW]=hitq[k] ? forwarded[LO+:SW] : raw[LO+:SW];
 end
 for(k=0;k<N;k=k+1) begin:g_bank
   ot_sram_1r1w_64x16_m1 u_m(.clk(ck), .r_ce_in(1'b1), .r_addr_in(6'(ra)),
    .rd_out(raw[16*k+:16]), .w_ce_in(wv), .w_addr_in(6'(waddr)),
    .wd_in(padded[16*k+:16]), .w_mask_in(16'hffff));
 end endgenerate
 assign q=picked[W-1:0];
`ifndef SYNTHESIS
 initial if(AW>6) $fatal(1,"dsdv_mu_mem requires depth <=64");
`endif
endmodule

// Balanced synchronous-release reset tree. The root, group and local flops
// release on edges1/2/3, exactly the existing SYNC_STAGES2+TREE_STAGES1 contract.
// Async assertion cascades through reset pins; constant D=1 means each group
// drives only <=32 reset pins, without a matching wide D broadcast.
module dsdv_mu_reset_tree #(parameter integer REGIONS=32, parameter integer LEAVES=32,
                           parameter integer GROUPS=(REGIONS+LEAVES-1)/LEAVES)(
 input wire clk, rst_n_in, output wire [REGIONS-1:0] rst_n);
 (* keep="true",dont_touch="true",async_reg="true" *) reg root_r;
 wire [GROUPS-1:0] group_q;
 always @(posedge clk or negedge rst_n_in)
     if(!rst_n_in) root_r<=1'b0; else root_r<=1'b1;
 genvar g,l;
 generate for(g=0;g<GROUPS;g=g+1) begin:g_group
     (* keep="true",dont_touch="true",async_reg="true" *) reg group_r;
     assign group_q[g]=group_r;
     always @(posedge clk or negedge root_r)
         if(!root_r) group_r<=1'b0; else group_r<=1'b1;
 end
 for(l=0;l<REGIONS;l=l+1) begin:g_local
     (* keep="true",dont_touch="true" *) reg local_r;
     assign rst_n[l]=local_r;
     always @(posedge clk or negedge group_q[l/LEAVES])
         if(!group_q[l/LEAVES]) local_r<=1'b0; else local_r<=1'b1;
 end endgenerate
`ifndef SYNTHESIS
 initial if(GROUPS>32 || LEAVES>32) $fatal(1,"reset fanout requires another explicitly priced tree shape");
`endif
endmodule
