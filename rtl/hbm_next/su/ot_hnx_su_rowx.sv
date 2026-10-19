`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hnx_su_rowx (HBM-NEXT-UNITS-SUDMA 2026-10-19): the SU.VOP ROW COUNTER of the next HBM die (HGI-1R ROWX, P = 4), one
// per SU quarter, between the quarter's programme producer (pgp_<q>, 2422-b command line) and the quarter
// (ot_hbm_su_static_quarter, d4g RTL unchanged). Control only: no datapath, no queue, no ready/credit.
// Why: the d4g SU runs a compiler-fixed per-edge command image (ot_hbm_su_programme_*: index table + per-column
// dictionaries). An N-row record unrolled with absolute addresses grows every address column's dictionary ~N x (the
// rows differ only in their VM sector, store row and control vector bases). Here the image holds ROW 0's commands and a
// per-edge ROW CODE (a 20-b programme column per quarter: the "4-b N field + stride select" of D2_PLAN 3.5); the record's
// ROWX strides (rs_k, converted by the CP to SU units) are static inputs for the record. Every row's words are row 0's,
// so the dictionaries do not grow with N; the index table grows by the record's edges only.
// Row code rc[19:0]: [3:0] vmr row r, [6:4] vmr operand (0 A, 1 B, 2 C, 3 D, 4 I), [11:8] vmw row, [12] vmw operand
// (0 O, 1 R), [19:16] control row. Strides st[294:0]: r_ss[5 x 16] VM sector (signed), r_sr[5 x 9] store row (signed),
// w_ss[2 x 16], w_sr[2 x 9], c_vb[5 x 24] control vector base (A B C D O, physical store words).
// Per valid command:  vmr  sector += r * r_ss[sel], store row += r * r_sr[sel];
//                     vmw  sector += r * w_ss[sel], store row += r * w_sr[sel] (src 0 = store drains only);
//                     ctl  vb[s] += r * c_vb[s] for s = A..O (ctl[314 + 24 s +: 24], su_arith_generate FIELDS).
// Row 0 (rc = 0) passes every word unchanged: N = 1 and every non-row record = the d4g command bit for bit (REG edges later).
// Checks (sticky FAULT, never a stall): a vmr/vmw sector leaves its quarter (sector[15:13] changes); a control vb leaves
// its 128-row frame / quarter (vb[23:14] changes).
// REG 1: one registered stage (+1 edge: the compiler's start advance + 1). MUT (bench only, must FAIL): 1 vmr sector
// stride dropped; 2 control vb stride dropped; 3 vmw sector stride dropped; 4 store-row strides dropped.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_su_rowx #(parameter integer REG=1,MUT=0)(
 input wire clk,rst_n,
 input wire [2421:0] line_in,                 // {ctl1742, vmr240, vmw312, rf54, red74} (row-0-relative)
 input wire [19:0] rc,                        // row code of this edge
 input wire [294:0] st,                       // record strides (static for the record)
 output reg [2421:0] line_out,
 output reg fault
);
 wire [3:0] r_r=rc[3:0], r_w=rc[11:8], r_c=rc[19:16];
 wire [2:0] s_r=rc[6:4]; wire s_w=rc[12];
 wire [15:0] r_ss [0:4]; wire [8:0] r_sr [0:4]; wire [15:0] w_ss [0:1]; wire [8:0] w_sr [0:1]; wire [23:0] c_vb [0:4];
 for(genvar k=0;k<5;k=k+1)begin:g_rs
  assign r_ss[k]=st[16*k+:16]; assign r_sr[k]=st[80+9*k+:9]; assign c_vb[k]=st[175+24*k+:24];
 end
 for(genvar k=0;k<2;k=k+1)begin:g_ws
  assign w_ss[k]=st[125+16*k+:16]; assign w_sr[k]=st[157+9*k+:9];
 end
 wire [2:0] sr_i=(s_r>3'd4)?3'd4:s_r;
 wire [15:0] o_rs=(MUT==1)?16'd0:16'(r_r*r_ss[sr_i]);
 wire [8:0]  o_rr=(MUT==4)?9'd0:9'(r_r*r_sr[sr_i]);
 wire [15:0] o_ws=(MUT==3)?16'd0:16'(r_w*w_ss[s_w]);
 wire [8:0]  o_wr=(MUT==4)?9'd0:9'(r_w*w_sr[s_w]);
 reg [2421:0] y; reg bad; integer p,s;
 reg [15:0] sec; reg [23:0] vb;
 always @*begin
  y=line_in; bad=1'b0;
  for(p=0;p<8;p=p+1)begin                     // vmr {v29, sector28:13, grp12:9, row8:0} at line[440 + 30 p]
   if(line_in[440+30*p+29])begin
    sec=line_in[440+30*p+13+:16]+o_rs;
    if(sec[15:13]!=line_in[440+30*p+13+13+:3])bad=1'b1;
    y[440+30*p+13+:16]=sec;
    y[440+30*p+:9]=line_in[440+30*p+:9]+o_rr;
   end
  end
  for(p=0;p<8;p=p+1)begin                     // vmw {v38, src37, grp36:33, row32:24, sector23:8, mask7:0} at 128 + 39 p
   if(line_in[128+39*p+38])begin
    sec=line_in[128+39*p+8+:16]+o_ws;
    if(sec[15:13]!=line_in[128+39*p+8+13+:3])bad=1'b1;
    y[128+39*p+8+:16]=sec;
    if(!line_in[128+39*p+37])y[128+39*p+24+:9]=line_in[128+39*p+24+:9]+o_wr;
   end
  end
  for(s=0;s<5;s=s+1)begin                     // control vb[s] at ctl[314 + 24 s] = line[680 + 314 + 24 s]
   vb=line_in[994+24*s+:24]+((MUT==2)?24'd0:24'(r_c*c_vb[s]));
   if(r_c!=4'd0&&c_vb[s]!=24'd0&&vb[23:14]!=line_in[994+24*s+14+:10])bad=1'b1;
   y[994+24*s+:24]=vb;
  end
 end
 if(REG!=0)begin:g_reg
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin line_out<='0; fault<=1'b0; end
   else begin line_out<=y; if(bad)fault<=1'b1; end
 end else begin:g_comb
  always @*line_out=y;
  always @(posedge clk or negedge rst_n)if(!rst_n)fault<=1'b0; else if(bad)fault<=1'b1;
 end
endmodule
`default_nettype wire
