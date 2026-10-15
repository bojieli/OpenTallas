`timescale 1ns/1ps
`default_nettype none
// Native B2 writer: local main sectors use one dedicated eight-bank credit group; every other
// slice and every mirror write uses the real B2 packet hub/ring. Credits return to COLL only
// after both sectors have committed (packet responses include remote/mirror acknowledgements).
module ot_hgi_coll_b2_vmport #(
    parameter integer CRD = 16, TCRD = 8, WCRD = 10, MUT = 0
) (
    input wire clk, rst_n,
    input wire [4:0] clk_rx,
    input wire [1:0] sid,
    input wire [3:0] rgx_t_v,
    input wire [159:0] rgx_t_addr,
    input wire [2047:0] rgx_t_data,
    input wire rgx_t_vm,
    output reg [3:0] rgx_f_cr,
    input wire tkw_t_v,
    input wire [567:0] tkw_t_d,
    output reg tkw_f_cr,
    output reg fault,
    output reg [8*281-1:0] wq,
    input wire [7:0] wq_cr, wq_done,
    output reg [5*338-1:0] cq,
    input wire [5*274-1:0] cr,
    output wire [651:0] xw,
    input wire [1:0] xwa
);
    wire [4:0] hv, pop, qfault; reg [4:0] pop_cmd;
    wire [199:0] ha; wire [2559:0] hd; wire [79:0] hm;
    wire [4:0] epoch; reg [4:0] issued_epoch;
    wire [4:0] blocked = ~(epoch ^ issued_epoch);
    for (genvar l = 0; l < 4; l = l + 1) begin : g_rx
        wire [551:0] h;
        ot_hgi_coll_rx_native #(.W(552), .CRD(CRD)) u_rx (.clk(clk_rx[l]), .rst_n(rst_n),
            .t_v(rgx_t_v[l]), .t_d({rgx_t_addr[l*40 +: 40],rgx_t_data[l*512 +: 512]}),
            .out_v(hv[l]), .out_d(h), .out_rdy(pop_cmd[l]), .epoch(epoch[l]), .fault(qfault[l]));
        assign ha[l*40 +: 40] = h[551:512]; assign hd[l*512 +: 512] = h[511:0];
        assign hm[l*16 +: 16] = 16'hffff;
    end
    wire [567:0] th;
    ot_hgi_coll_rx_native #(.W(568), .CRD(TCRD)) u_trx (.clk(clk_rx[4]), .rst_n(rst_n), .t_v(tkw_t_v), .t_d(tkw_t_d),
        .out_v(hv[4]), .out_d(th), .out_rdy(pop_cmd[4]), .epoch(epoch[4]), .fault(qfault[4]));
    assign ha[160 +: 40] = th[567:528]; assign hm[64 +: 16] = th[527:512]; assign hd[2048 +: 512] = th[511:0];
    reg vm_q, vm_run; reg [3:0] rv_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin vm_q <= 0; vm_run <= 0; rv_q <= 0; end
        else begin vm_q <= rgx_t_vm; rv_q <= rgx_t_v; if (|rv_q) vm_run <= vm_q; end
    // Preserve the existing real HBM write clients for HBM-space ROW_GATHER.
    wire [3:0] hpop; wire hf;
    ot_hgi_coll_rgx_snk #(.LQ(8)) u_hbm (.clk(clk), .rst_n(rst_n), .rg_w_v(hv[3:0] & ~blocked[3:0] & {4{!vm_run}}),
        .rg_w_addr(ha[159:0]), .rg_w_vm(1'b0), .rg_w_data(hd[2047:0]), .rg_w_rdy(hpop),
        .c_req(), .c_gnt(1'b0), .c_q(), .c_cr(32'd0), .c_rsp(32'd0), .xw(xw), .xwa(xwa), .fault(hf));
    localparam integer OD = WCRD + 16, BW = $clog2(OD), CW = $clog2(WCRD+1), OW = $clog2(OD+1);
    reg [CW-1:0] wc [0:7];
    reg [2:0] owners [0:7][0:OD-1]; reg [BW-1:0] oh [0:7], ot [0:7]; reg [OW-1:0] on [0:7];
    reg [2:0] pc [0:4]; reg half [0:4]; reg [15:0] itag [0:4], rtag [0:4]; reg [$clog2(2*CRD+1)-1:0] ack_rem [0:4];
    reg [5*274-1:0] cr_q; reg [7:0] wcr_q, wdone_q; reg [1:0] me;
    always @(posedge clk) begin cr_q <= cr; wcr_q <= wq_cr; wdone_q <= wq_done; me <= sid; end
    reg [4:0] wp, pp; reg [7:0] take; reg [8*281-1:0] wnext; reg [5*338-1:0] cnext;
    always @* begin
        reg [7:0] used;
        wp = 0; pp = 0; take = 0; used = 0; wnext = 0; cnext = 0;
        for (integer l = 0; l < 5; l = l + 1) begin
            reg [39:0] a; reg [15:0] s0, s1; reg [2:0] b0, b1; reg [31:0] bm;
            a = ha[l*40 +: 40]; s0 = a[18:3]; s1 = s0 + 1'b1; b0 = s0[2:0]; b1 = s1[2:0];
            bm = 0; for (integer j = 0; j < 8; j = j + 1) bm[j*4 +: 4] = {4{hm[l*16 + (half[l] ? 8 : 0) + j]}};
            if (hv[l] && !blocked[l] && (l == 4 || vm_run)) begin
                if (!s0[15] && s0[14:13] == me && s1[14:13] == me && !s1[15] && a[2:0] == 0 && a[39:19] == 0) begin
                    if (!used[b0] && !used[b1] && wc[b0] != 0 && wc[b1] != 0) begin
                        wp[l] = 1; used[b0] = 1; used[b1] = 1; take[b0] = 1; take[b1] = 1;
                        wnext[b0*281 +: 281] = {1'b1,s0,hd[l*512 +: 256],hm[l*16 +: 8]};
                        wnext[b1*281 +: 281] = {1'b1,s1,hd[l*512+256 +: 256],hm[l*16+8 +: 8]};
                    end
                end else if (pc[l] != 0) begin
                    pp[l] = 1;
                    // old/native B2 packet ABI: v,we,byte address,data,byte mask,transaction tag.
                    cnext[l*338 +: 338] = {1'b1,1'b1,11'd0,(half[l] ? s1 : s0),5'd0,
                        (half[l] ? hd[l*512+256 +: 256] : hd[l*512 +: 256]),bm,itag[l]};
                end
            end
        end
    end
    for (genvar l = 0; l < 5; l = l + 1) begin : g_pop
        if (l < 4) assign pop[l] = wp[l] || (pp[l] && half[l]) || hpop[l];
        else assign pop[l] = wp[l] || (pp[l] && half[l]);
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wq <= 0; cq <= 0; rgx_f_cr <= 0; tkw_f_cr <= 0; fault <= 0; issued_epoch <= '1; pop_cmd <= 0;
            for (integer b = 0; b < 8; b = b + 1) begin wc[b] <= CW'(WCRD); oh[b] <= 0; ot[b] <= 0; on[b] <= 0; end
            for (integer l = 0; l < 5; l = l + 1) begin pc[l] <= 4; half[l] <= 0; itag[l] <= 0; rtag[l] <= 0; ack_rem[l] <= 0; end
        end else begin
            integer na [0:4];
            wq <= wnext; cq <= cnext; pop_cmd <= pop; rgx_f_cr <= 0; tkw_f_cr <= 0;
            if ((|qfault) || hf) fault <= 1;
            for (integer l = 0; l < 5; l = l + 1) begin
                na[l] = ack_rem[l];
                if (pop[l]) issued_epoch[l] <= epoch[l];
                pc[l] <= pc[l] - 3'(pp[l]) + 3'(cr_q[l*274+273]);
                if (pp[l]) begin half[l] <= !half[l]; itag[l] <= itag[l] + 1'b1; end
                if (cr_q[l*274+273]) begin
                    if (!cr_q[l*274+256] || cr_q[l*274+257 +: 16] != rtag[l]) fault <= 1;
                    rtag[l] <= rtag[l] + 1'b1; na[l] = na[l] + 1;
                end
                if (hv[l] && (l == 4 || vm_run) && (ha[l*40 +: 3] != 0 || |ha[l*40+19 +: 21])) fault <= 1;
            end
            for (integer b = 0; b < 8; b = b + 1) begin
                wc[b] <= wc[b] - CW'(take[b]) + CW'(wcr_q[b]);
                if (take[b]) begin
                    for (integer l = 0; l < 5; l = l + 1) if (wp[l] &&
                        (ha[l*40+3 +: 3] == 3'(b) || (ha[l*40+3 +: 3] + 3'd1) == 3'(b))) owners[b][ot[b]] <= 3'(l);
                    ot[b] <= (ot[b] == BW'(OD-1)) ? '0 : ot[b] + 1'b1;
                end
                if (wdone_q[b]) begin
                    if (on[b] == 0) fault <= 1;
                    else na[owners[b][oh[b]]] = na[owners[b][oh[b]]] + 1;
                    oh[b] <= (oh[b] == BW'(OD-1)) ? '0 : oh[b] + 1'b1;
                end
                on[b] <= on[b] + OW'(take[b]) - OW'(wdone_q[b]);
            end
            for (integer l = 0; l < 5; l = l + 1) begin
                if (na[l] >= 2) begin
                    if (l < 4) rgx_f_cr[l] <= 1; else tkw_f_cr <= 1;
                    na[l] = na[l] - 2;
                end
                ack_rem[l] <= $clog2(2*CRD+1)'(na[l]);
                if (l < 4 && hpop[l]) rgx_f_cr[l] <= 1;
            end
            if (MUT == 1) begin rgx_f_cr <= pop[3:0]; tkw_f_cr <= pop[4]; end
        end
    end
endmodule
`default_nettype wire
