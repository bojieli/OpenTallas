`timescale 1ns/1ps
`default_nettype none
// Adapter for CLOSED ot_su12_sfu, whose lane index is physically fixed at5.
// Four registered edges; native broadcast/retirement must price and bind them.
module ot_hgi_sfu_lane_map #(parameter integer MUT_LANE=0,
 // LH-SU (10-19): PASS_OHREP > 0 replicates the pass ring's one-hot per PASS_OHREP bits (ot_hdc_delay_ring OHREP)
 parameter integer PASS_OHREP=0) (
 input wire clk, rst_n,
 input wire [3:0] lane_j,
 input wire [479:0] ld_terms,
 input wire [23:0] i_o_v, i_i_v, i_krow,
 input wire [3:0] i_ls, i_lvw,
 input wire i_emit,
 input wire [460:0] i_pass,
 output reg [1199:0] o_ld_c,
 output reg [23:0] o_o_v, o_i_v, o_krow,
 output reg [3:0] o_ls, o_lvw,
 output reg o_emit,
 output wire [460:0] o_pass
);
 reg f_rst; always @(posedge clk) f_rst<=rst_n;
 reg [479:0] terms0;
 reg [23:0] ov0,iv0,row0;
 reg [3:0] ls0,lvw0,j0;
 reg emit0,emit1,emit2;
 reg [79:0] meta1,meta2;
 // ld is control, not retained payload: reset must not replay a ring slot.
 reg [3:0] ld_pipe;
 generate if(PASS_OHREP>0)begin:g_prep
  ot_hdc_delay_ring_rep #(.W(460),.D(4),.OHREP(PASS_OHREP)) u_pass (.clk(clk),.rst_n(rst_n),.d(i_pass[459:0]),.q(o_pass[459:0]));
 end else begin:g_pring
  ot_hdc_delay_ring #(.W(460),.D(4),.RING(3)) u_pass (.clk(clk),.rst_n(rst_n),.d(i_pass[459:0]),.q(o_pass[459:0]));
 end endgenerate
 assign o_pass[460]=ld_pipe[3];
 reg [23:0] term1[0:19],pair2[0:9];
 always @(posedge clk) begin
  terms0<=ld_terms; ov0<=i_o_v; iv0<=i_i_v; row0<=i_krow;
  ls0<=i_ls; lvw0<=i_lvw; j0<=lane_j ^ 4'(MUT_LANE);
  // All integer expressions wrap at24 bits, as the frozen lane's kadd.
  meta1<={24'(ov0 + (24'(j0)>>ls0) - (24'd5>>ls0)),
          24'(iv0 + (24'(j0)&((24'd1<<ls0)-1)) - (24'd5&((24'd1<<ls0)-1))),
          24'(row0 + (24'(j0)>>ls0) - (24'd5>>ls0)),
          ls0,(lvw0<3 ? 4'd3 : lvw0)};
  meta2<=meta1;
  {o_o_v,o_i_v,o_krow,o_ls,o_lvw}<=meta2;
  for(integer s=0;s<5;s=s+1) begin
   for(integer k=0;k<4;k=k+1)
    term1[s*4+k]<=j0[k] ? terms0[(s*4+k)*24+:24] : 24'd0;
   pair2[s*2]<=term1[s*4]+term1[s*4+1];
   pair2[s*2+1]<=term1[s*4+2]+term1[s*4+3];
   o_ld_c[s*240+:240]<={216'd0,24'(pair2[s*2]+pair2[s*2+1])};
  end
  if(!f_rst) begin emit0<=0;emit1<=0;emit2<=0;o_emit<=0;ld_pipe<=0;end
  else begin emit0<=i_emit;emit1<=emit0 && (24'(j0)<(24'd1<<lvw0));emit2<=emit1;o_emit<=emit2;ld_pipe<={ld_pipe[2:0],i_pass[460]};end
 end
endmodule
`default_nettype wire
// LH-SU (10-19, safe-design item 3): ot_hdc_delay_ring RING form (D >= 4: D-1 slots + output register, slot written at
// edge e read into q at edge e + D - 1) with REPLICATED one-hot slot registers: ceil(W / OHREP) kept copies
// ((* keep *), ot_keep_regs.tcl), copy c driving only bits [c*OHREP, (c+1)*OHREP), so each one-hot bit sees OHREP write
// enables + OHREP read ANDs instead of 2*W loads (W = 460: 1,381). Same q edge for edge as ot_hdc_delay_ring RING.
// (Kept in this file: the closed lane manifest freezes ot_hdc_delay_ring.sv, and every lane_map source list carries this file.)
module ot_hdc_delay_ring_rep #(
    parameter integer W = 32,
    parameter integer D = 4,
    parameter integer RESET = 0,
    parameter integer OHREP = 16
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D < 4) begin : g_bad
            ot_hdc_delay_ring_rep_requires_D_ge_4 u_refuse();
        end else begin : g_ringr
            localparam integer N = D - 1;
            localparam integer RW = (OHREP > 0 && OHREP < W) ? OHREP : W;   // bits per one-hot copy
            localparam integer NC = (W + RW - 1) / RW;          // one-hot copies
            genvar c, j;
            for (c = 0; c < NC; c = c + 1) begin : g_c
                localparam integer LO = c * RW, HI = ((c + 1) * RW > W) ? W : (c + 1) * RW, CW = HI - LO;
                (* keep = "true", dont_touch = "true" *) reg [N-1:0] oh;   // this copy's one-hot slot
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) oh <= {{(N-1){1'b0}}, 1'b1};
                    else oh <= {oh[N-2:0], oh[N-1]};
                wire [CW*N-1:0] slots;
                for (j = 0; j < N; j = j + 1) begin : g_s
                    reg [CW-1:0] m;
                    if (RESET != 0) begin : g_rst
                        always @(posedge clk or negedge rst_n)
                            if (!rst_n) m <= {CW{1'b0}}; else if (oh[j]) m <= d[HI-1:LO];
                    end else begin : g_nrst
                        always @(posedge clk) if (oh[j]) m <= d[HI-1:LO];
                    end
                    assign slots[j*CW +: CW] = m & {CW{oh[j]}};
                end
                reg [CW-1:0] r;
                integer i;
                always @(*) begin
                    r = {CW{1'b0}};
                    for (i = 0; i < N; i = i + 1) r = r | slots[i*CW +: CW];
                end
                reg [CW-1:0] qr;
                if (RESET != 0) begin : g_qrst
                    always @(posedge clk or negedge rst_n) if (!rst_n) qr <= {CW{1'b0}}; else qr <= r;
                end else begin : g_qnrst
                    always @(posedge clk) qr <= r;
                end
                assign q[HI-1:LO] = qr;
            end
        end
    endgenerate
endmodule
