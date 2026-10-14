`timescale 1ns/1ps
`default_nettype none
// Distinct F2 local quadrant variant. Original CLOSED ctlw_slice is preserved.
// Descriptors are local word offsets; aperture ownership is external and retained to drain.
module ot_hgi_su_ctlw_native_q #(
    parameter integer SL = 0, parameter integer NL = 8, parameter integer LWB = 17, parameter integer LQ = 10,
    parameter integer MUT_W = 0, parameter integer MUT_DIRTY = 0,
    parameter integer LQSRAM = 0          // 1: each lane's landing FIFO in a 64x16 1R1W SRAM (FWFT), not 64 x LSW flops
) (
    input  wire clk, input wire rst_n,
    input  wire wst_go_i, input wire wdr_go_i,
    input  wire [6*24-1:0] lo_i, input wire [6*24-1:0] hi_i, input wire [6*(LWB+1)-1:0] lb_i, input wire [5:0] rv_i,
    input  wire [6*21-1:0] dsec_i,
    input  wire [2*24-1:0] d_lo_i, input wire [2*24-1:0] d_hi_i, input wire [2*(LWB+1)-1:0] d_lb_i, input wire [1:0] d_rv_i,
    input  wire [2*21-1:0] d_dsec_i, input wire d_os_i,
    // GLUE PLACEMENT (el1011-hbm-sfu 10-11): slice id strap (one hard tile for every slice), the forward link (this
    // slice's descriptor / go pin registers, to the next slice) and the backward done / overflow combine link
    input  wire [1:0] sl_i,
    output wire wst_go_o, output wire wdr_go_o, output wire d_os_o,
    output wire [6*24-1:0] lo_o, output wire [6*24-1:0] hi_o, output wire [6*(LWB+1)-1:0] lb_o, output wire [5:0] rv_o,
    output wire [6*21-1:0] dsec_o, output wire [2*24-1:0] d_lo_o, output wire [2*24-1:0] d_hi_o,
    output wire [2*(LWB+1)-1:0] d_lb_o, output wire [1:0] d_rv_o, output wire [2*21-1:0] d_dsec_o,
    input  wire wst_dn_i, input wire wdr_dn_i, input wire ovf_i,
    output reg  [NL*16-1:0] wrq, input wire [NL-1:0] wrq_cr, input wire [NL*257-1:0] wrr,
    output reg  [NL*280-1:0] wwq, input wire [NL-1:0] wwq_cr, input wire [NL-1:0] wwq_done,
    output reg  [NL-1:0] lsw_v, output reg [NL*(LWB-3)-1:0] lsw_sec, output reg [NL*256-1:0] lsw_d,
    output reg  [NL-1:0] ldc_v, output reg [NL*(LWB-3)-1:0] ldc_sec,
    output reg  [NL-1:0] ldr_v, output reg [NL*(LWB-3)-1:0] ldr_sec,
    input  wire [NL*256-1:0] ldr_d, input wire [NL*8-1:0] ldr_dm, input wire [NL-1:0] ldr_rv,
    output reg  wst_dn, output reg wdr_dn, output reg ovf
);
    localparam integer LSW = LWB - 3, QB = $clog2(LQ);
    reg rst_l; always @(posedge clk) rst_l <= rst_n;          // the slice's reset pin flop
    reg wst_go, wdr_go;
    always @(posedge clk or negedge rst_l) if (!rst_l) begin wst_go <= 1'b0; wdr_go <= 1'b0; end
                                           else begin wst_go <= wst_go_i; wdr_go <= wdr_go_i; end
    reg [23:0] lo [0:5]; reg [23:0] hi [0:5]; reg [LWB:0] lb [0:5]; reg rv [0:5]; reg [20:0] dsec [0:5];
    reg [23:0] d_lo [4:5]; reg [23:0] d_hi [4:5]; reg [LWB:0] d_lb [4:5]; reg d_rv [4:5]; reg [20:0] d_dsec [4:5]; reg d_os;
    always @(posedge clk) begin
        for (integer q = 0; q < 6; q = q + 1) begin
            lo[q] <= lo_i[q*24 +: 24]; hi[q] <= hi_i[q*24 +: 24]; lb[q] <= lb_i[q*(LWB+1) +: LWB+1]; rv[q] <= rv_i[q];
            dsec[q] <= dsec_i[q*21 +: 21];
        end
        for (integer q = 4; q < 6; q = q + 1) begin
            d_lo[q] <= d_lo_i[(q-4)*24 +: 24]; d_hi[q] <= d_hi_i[(q-4)*24 +: 24]; d_lb[q] <= d_lb_i[(q-4)*(LWB+1) +: LWB+1];
            d_rv[q] <= d_rv_i[q-4]; d_dsec[q] <= d_dsec_i[(q-4)*21 +: 21];
        end
        d_os <= d_os_i;
    end
    reg [1:0] sl_q; always @(posedge clk) sl_q <= sl_i;      // strap pin flop
    assign wst_go_o = wst_go; assign wdr_go_o = wdr_go; assign d_os_o = d_os;
    for (genvar q = 0; q < 6; q = q + 1) begin : g_fo
        assign lo_o[q*24 +: 24] = lo[q]; assign hi_o[q*24 +: 24] = hi[q]; assign lb_o[q*(LWB+1) +: LWB+1] = lb[q];
        assign rv_o[q] = rv[q]; assign dsec_o[q*21 +: 21] = dsec[q];
    end
    for (genvar q = 4; q < 6; q = q + 1) begin : g_fd
        assign d_lo_o[(q-4)*24 +: 24] = d_lo[q]; assign d_hi_o[(q-4)*24 +: 24] = d_hi[q];
        assign d_lb_o[(q-4)*(LWB+1) +: LWB+1] = d_lb[q]; assign d_rv_o[q-4] = d_rv[q]; assign d_dsec_o[(q-4)*21 +: 21] = d_dsec[q];
    end
    reg dn_st_q, dn_dr_q, dn_ov_q;                           // the next slice's combined flags, pin-flopped
    always @(posedge clk or negedge rst_l) if (!rst_l) begin dn_st_q <= 1'b1; dn_dr_q <= 1'b1; dn_ov_q <= 1'b0; end
                                           else begin dn_st_q <= wst_dn_i; dn_dr_q <= wdr_dn_i; dn_ov_q <= ovf_i; end
    reg [NL-1:0] wrq_cr_q, wwq_cr_q, wwq_done_q; reg [NL*257-1:0] wrr_q;
    always @(posedge clk or negedge rst_l)
        if (!rst_l) begin wrq_cr_q <= '0; wwq_cr_q <= '0; wwq_done_q <= '0; wrr_q <= '0; end
        else begin wrq_cr_q <= wrq_cr; wwq_cr_q <= wwq_cr; wwq_done_q <= wwq_done; wrr_q <= wrr; end
    reg [NL*256-1:0] ldr_d_q; reg [NL*8-1:0] ldr_dm_q;
    reg [NL-1:0] ldr_rv_q;
    always @(posedge clk) begin ldr_d_q <= ldr_d; ldr_dm_q <= ldr_dm; end
    always @(posedge clk or negedge rst_l) if (!rst_l) ldr_rv_q <= '0; else ldr_rv_q <= ldr_rv;
    // drain reads are VALID-driven: each lane keeps the VM sector of every read in flight (in order); a returned
    // {data, dirty} (ldr_rv, pin-flopped) pops it, whatever the memory latency
    reg [20:0] dq_s [0:NL-1][0:LQ-1]; reg [QB-1:0] dq_h [0:NL-1], dq_t [0:NL-1]; reg [QB:0] dq_n [0:NL-1];
    // per-lane state
    reg [2:0]  sg_r [0:NL-1]; reg sg_on [0:NL-1]; reg [20:0] sg_nx [0:NL-1]; reg [20:0] sg_end [0:NL-1];
    // landing FIFO: LQ queued at the VM + the accepted-not-landed pipe (VM core + relays): power of two >= 2 LQ + 32
    localparam integer LFB = $clog2(2 * LQ + 32), LFD = 1 << LFB;
    reg [QB:0] cr [0:NL-1]; reg [LSW-1:0] lq [0:NL-1][0:LFD-1]; reg [LFB-1:0] lqh [0:NL-1], lqt [0:NL-1]; reg [LFB:0] lqn [0:NL-1];
    reg [5:0] wpend [0:NL-1]; reg lane_ovf;
    reg [2:0]  cl_r [0:NL-1]; reg cl_on [0:NL-1]; reg [LSW-1:0] cl_nx [0:NL-1]; reg [LSW-1:0] cl_end [0:NL-1];
    reg [2:0]  dg_r [0:NL-1]; reg dg_on [0:NL-1]; reg [LSW-1:0] dg_nx [0:NL-1]; reg [LSW-1:0] dg_end [0:NL-1];
    reg [QB:0] wcr [0:NL-1]; reg [NL-1:0] dp1, dp2, dp3; reg [20:0] dp1_s [0:NL-1]; reg [20:0] dp2_s [0:NL-1]; reg [20:0] dp3_s [0:NL-1];
    reg [NL-1:0] wst_ldone, wdr_ldone;
    function automatic [20:0] first_of(input [20:0] lo_s, input integer b);
        first_of = lo_s + 21'((3'(b) - lo_s[2:0]) & 3'd7);
    endfunction
    // landing FIFO head per lane: flops (LQSRAM 0) or an SRAM first-word-fall-through FIFO (LQSRAM 1); lq_first = slot 0
    wire [LSW-1:0] lq_head [0:NL-1]; reg [LSW-1:0] lq_first [0:NL-1];
    generate if (LQSRAM != 0) begin : g_lqm
        initial if (LFD != 64 || LSW > 16) $error("ot_hgi_su_ctlw_slice LQSRAM: needs LFD 64 and LSW <= 16");
        for (genvar g = 0; g < NL; g = g + 1) begin : g_l
            wire push = !wst_go && sg_r[g] < 3'd4 && sg_on[g] && cr[g] != 0;
            // MUT_W 4 (bench mutant, el1011-hbm-sfu 10-11): the SRAM FIFO pop one edge late -> a back-to-back landing
            // reads the previous head (wrong sector); the only mutant that exercises this FIFO's read-ahead (MUT_DIRTY is
            // unobservable on the production shapes: every drained sink sector is whole, dirty mask 8'hFF)
            reg pop_d;
            always @(posedge clk or negedge rst_l) if (!rst_l) pop_d <= 1'b0; else pop_d <= wrr_q[g*257 + 256];
            wire pop = (MUT_W == 4) ? pop_d : wrr_q[g*257 + 256];
            wire hv, ovf_l;
            ot_fifo_sram_fwft #(.W(LSW), .DEPTH(64), .MACRO(3)) u_lq (.clk(clk), .rst_n(rst_l), .push(push),
                .wdata(LSW'(sg_nx[g] + dsec[sg_r[g]])), .pop(pop), .hv(hv), .head(lq_head[g]), .ovf(ovf_l));
            // synthesis translate_off
            always @(posedge clk) if (rst_l && pop && !hv)
                $error("ctlw slice %0d lane %0d: a response landed before its FIFO head was readable", SL, g);
            // synthesis translate_on
        end
    end else begin : g_lqf
        for (genvar g = 0; g < NL; g = g + 1) begin : g_l
            assign lq_head[g] = lq[g][lqh[g]];
        end
    end endgenerate
    always @(posedge clk or negedge rst_l) begin
        if (!rst_l) begin
            wrq <= '0; wwq <= '0; lsw_v <= '0; ldc_v <= '0; ldr_v <= '0; dp1 <= '0; dp2 <= '0; dp3 <= '0;
            for (integer b = 0; b < NL; b = b + 1) begin dq_h[b] <= '0; dq_t[b] <= '0; dq_n[b] <= '0; end
            wst_ldone <= '1; wdr_ldone <= '1; lane_ovf <= 1'b0;
            for (integer b = 0; b < NL; b = b + 1) begin
                sg_r[b] <= 3'd7; sg_on[b] <= 1'b0; cl_r[b] <= 3'd7; cl_on[b] <= 1'b0; dg_r[b] <= 3'd7; dg_on[b] <= 1'b0;
                cr[b] <= (QB+1)'(LQ); wcr[b] <= (QB+1)'(LQ); lqh[b] <= '0; lqt[b] <= '0; lqn[b] <= '0; wpend[b] <= '0;
            end
        end else begin
            for (integer b = 0; b < NL; b = b + 1) begin : lane
                reg iss, land, dr_iss, wsend, wfree;
                reg [20:0] f;
                iss = 1'b0; land = 1'b0; dr_iss = 1'b0; wsend = 1'b0; wfree = 1'b0;
                wrq[b*16 + 15] <= 1'b0; lsw_v[b] <= 1'b0; ldc_v[b] <= 1'b0; ldr_v[b] <= 1'b0; wwq[b*280 + 279] <= 1'b0;
                // ---------------- stage: source region walk (regions 0..3)
                if (wst_go) begin sg_r[b] <= 3'd0; sg_on[b] <= 1'b0; cl_r[b] <= 3'd4; cl_on[b] <= 1'b0; wst_ldone[b] <= 1'b0; end
                else if (sg_r[b] < 3'd4) begin
                    if (!sg_on[b]) begin
                        f = first_of(21'(lo[sg_r[b]] >> 3), b);
                        if (rv[sg_r[b]] && f <= 21'(hi[sg_r[b]] >> 3)) begin
                            sg_nx[b] <= f; sg_end[b] <= 21'(hi[sg_r[b]] >> 3); sg_on[b] <= 1'b1;
                        end else sg_r[b] <= sg_r[b] + 3'd1;
                    end else if (cr[b] != 0) begin
                        iss = 1'b1;
                        wrq[b*16 +: 16] <= {1'b1, sg_nx[b][14:0]};
                        if (LQSRAM == 0) lq[b][lqt[b]] <= LSW'(sg_nx[b] + dsec[sg_r[b]]);
                        if (lqt[b] == '0) lq_first[b] <= LSW'(sg_nx[b] + dsec[sg_r[b]]);
                        lqt[b] <= lqt[b] + 1'b1;
                        if (sg_nx[b] + 21'd8 > sg_end[b]) begin sg_on[b] <= 1'b0; sg_r[b] <= sg_r[b] + 3'd1; end
                        else sg_nx[b] <= sg_nx[b] + 21'd8;
                    end
                end
                // responses land in request order
                if (wrr_q[b*257 + 256]) begin
                    land = 1'b1;
                    lsw_v[b] <= 1'b1; lsw_sec[b*LSW +: LSW] <= (MUT_W == 1) ? lq_first[b] : lq_head[b];
                    lsw_d[b*256 +: 256] <= wrr_q[b*257 +: 256];
                    lqh[b] <= lqh[b] + 1'b1;
                end
                lqn[b] <= lqn[b] + iss - land;
                if (lqn[b] == (LFB+1)'(LFD) && iss && !land) lane_ovf <= 1'b1;
                cr[b] <= cr[b] - iss + wrq_cr_q[b];
                // sink dirty-mask clears (regions 4, 5; the local span), one sector a lane an edge
                if (!wst_go && cl_r[b] < 3'd6) begin
                    if (!cl_on[b]) begin
                        f = first_of(21'(lb[cl_r[b]] >> 3), b);
                        if (rv[cl_r[b]] && f <= 21'((lb[cl_r[b]] + (hi[cl_r[b]] - lo[cl_r[b]])) >> 3)) begin
                            cl_nx[b] <= LSW'(f); cl_end[b] <= LSW'((lb[cl_r[b]] + (hi[cl_r[b]] - lo[cl_r[b]])) >> 3);
                            cl_on[b] <= 1'b1;
                        end else cl_r[b] <= cl_r[b] + 3'd1;
                    end else begin
                        ldc_v[b] <= 1'b1; ldc_sec[b*LSW +: LSW] <= cl_nx[b];
                        if (21'(cl_nx[b]) + 21'd8 > 21'(cl_end[b])) begin cl_on[b] <= 1'b0; cl_r[b] <= cl_r[b] + 3'd1; end
                        else cl_nx[b] <= cl_nx[b] + LSW'(8);
                    end
                end
                if (!wst_go && sg_r[b] >= 3'd4 && sg_r[b] != 3'd7 && cl_r[b] >= 3'd6 &&
                    ((lqn[b] + iss - land) == 0 && (cr[b] - iss + wrq_cr_q[b]) == (QB+1)'(LQ))) wst_ldone[b] <= 1'b1;
                // ---------------- drain: sink regions 4 (O, unless STREAM) and 5 (R)
                if (wdr_go) begin dg_r[b] <= 3'd4; dg_on[b] <= 1'b0; wdr_ldone[b] <= 1'b0; end
                else if (dg_r[b] < 3'd6) begin
                    if (!dg_on[b]) begin
                        f = first_of(21'(d_lb[dg_r[b]] >> 3), b);
                        if (d_rv[dg_r[b]] && !(dg_r[b] == 3'd4 && d_os) &&
                            f <= 21'((d_lb[dg_r[b]] + (d_hi[dg_r[b]] - d_lo[dg_r[b]])) >> 3)) begin
                            dg_nx[b] <= LSW'(f); dg_end[b] <= LSW'((d_lb[dg_r[b]] + (d_hi[dg_r[b]] - d_lo[dg_r[b]])) >> 3);
                            dg_on[b] <= 1'b1;
                        end else dg_r[b] <= dg_r[b] + 3'd1;
                    end else if (wcr[b] != 0) begin
                        if (!(MUT_W == 2 && 21'(dg_nx[b]) + 21'd8 > 21'(dg_end[b]))) begin
                            dr_iss = 1'b1;
                            ldr_v[b] <= 1'b1; ldr_sec[b*LSW +: LSW] <= dg_nx[b];
                            dq_s[b][dq_t[b]] <= 21'(dg_nx[b]) - d_dsec[dg_r[b]]; dq_t[b] <= (dq_t[b] == QB'(LQ-1)) ? '0 : dq_t[b] + 1'b1;
                        end
                        if (21'(dg_nx[b]) + 21'd8 > 21'(dg_end[b])) begin dg_on[b] <= 1'b0; dg_r[b] <= dg_r[b] + 3'd1; end
                        else dg_nx[b] <= dg_nx[b] + LSW'(8);
                    end
                end
                // read return: valid-driven (ldr_rv pin flop), the sector identity from the lane's in-flight FIFO
                begin : wpub
                    reg [7:0] mk; reg v3; reg [20:0] s3;
                    mk = MUT_DIRTY ? 8'hFF : ldr_dm_q[b*8 +: 8];
                    v3 = ldr_rv_q[b]; s3 = dq_s[b][dq_h[b]];
                    if (v3) dq_h[b] <= (dq_h[b] == QB'(LQ-1)) ? '0 : dq_h[b] + 1'b1;
                    dq_n[b] <= dq_n[b] + dr_iss - v3;
                    if (v3) begin
                        if (mk != 8'd0) begin
                            wsend = 1'b1;
                            wwq[b*280 +: 280] <= {1'b1, s3[14:0], ldr_d_q[b*256 +: 256], mk};
                        end else wfree = 1'b1;
                    end
                end
                wcr[b] <= wcr[b] - dr_iss + wfree + wwq_cr_q[b];
                wpend[b] <= wpend[b] + wsend - wwq_done_q[b];
                if (!wdr_go && dg_r[b] >= 3'd6 && dg_r[b] != 3'd7 && !dr_iss && (dq_n[b] - ldr_rv_q[b]) == 0 &&
                    (MUT_W == 3 || ((wpend[b] + wsend - wwq_done_q[b]) == 0 && (wcr[b] - dr_iss + wfree + wwq_cr_q[b]) == (QB+1)'(LQ)))) wdr_ldone[b] <= 1'b1;
            end
        end
    end
    always @(posedge clk or negedge rst_l)
        if (!rst_l) begin wst_dn <= 1'b1; wdr_dn <= 1'b1; ovf <= 1'b0; end
        else begin wst_dn <= (&wst_ldone) && dn_st_q; wdr_dn <= (&wdr_ldone) && dn_dr_q; ovf <= lane_ovf || dn_ov_q; end
endmodule
`default_nettype wire
