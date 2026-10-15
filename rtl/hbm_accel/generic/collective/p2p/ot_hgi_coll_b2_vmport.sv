`timescale 1ns/1ps
// HISTORICAL (OWNER 2026-10-14T23:16 HANDOFF 0an): credit/ready flow control on an on-chip HBM path. Diagnostic/component
// evidence only; NOT the production schedule. Being replaced by compiler-assigned fixed transfer slots (H-COLL plan, el1014-hbm-p2p-coll.log).
`default_nettype none
// Native B2 writer: local main sectors use one dedicated eight-bank credit group; every other
// slice and every mirror write uses the real B2 packet hub/ring. Credits return to COLL only
// after both sectors have committed (packet responses include remote/mirror acknowledgements).
// Glue only (hardening): five receive leaves (ot_hgi_coll_rx_native_w552 x4 / _w568) + the writer core leaf
// ot_hgi_coll_b2_vmcore; no logic of its own.
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
    wire [4:0] hv, qfault, epoch; wire [4:0] pop_cmd;
    wire [4*552-1:0] hrx; wire [567:0] th;
    for (genvar l = 0; l < 4; l = l + 1) begin : g_rx
        wire [551:0] h;
        // CRD 16 = the closed hard master _w552; any other depth is a bench-only generic instance.
        if (CRD == 16) begin : g_hard
            ot_hgi_coll_rx_native_w552 u_rx (.clk(clk_rx[l]), .rst_n(rst_n),
                .t_v(rgx_t_v[l]), .t_d({rgx_t_addr[l*40 +: 40],rgx_t_data[l*512 +: 512]}),
                .out_v(hv[l]), .out_d(h), .out_rdy(pop_cmd[l]), .epoch(epoch[l]), .fault(qfault[l]));
        end else begin : g_gen
            ot_hgi_coll_rx_native #(.W(552), .CRD(CRD)) u_rx (.clk(clk_rx[l]), .rst_n(rst_n),
                .t_v(rgx_t_v[l]), .t_d({rgx_t_addr[l*40 +: 40],rgx_t_data[l*512 +: 512]}),
                .out_v(hv[l]), .out_d(h), .out_rdy(pop_cmd[l]), .epoch(epoch[l]), .fault(qfault[l]));
        end
        assign hrx[l*552 +: 552] = h;
    end
    // TCRD 8 = the closed hard master _w568.
    if (TCRD == 8) begin : g_thard
        ot_hgi_coll_rx_native_w568 u_trx (.clk(clk_rx[4]), .rst_n(rst_n), .t_v(tkw_t_v), .t_d(tkw_t_d),
            .out_v(hv[4]), .out_d(th), .out_rdy(pop_cmd[4]), .epoch(epoch[4]), .fault(qfault[4]));
    end else begin : g_tgen
        ot_hgi_coll_rx_native #(.W(568), .CRD(TCRD)) u_trx (.clk(clk_rx[4]), .rst_n(rst_n), .t_v(tkw_t_v), .t_d(tkw_t_d),
            .out_v(hv[4]), .out_d(th), .out_rdy(pop_cmd[4]), .epoch(epoch[4]), .fault(qfault[4]));
    end
    ot_hgi_coll_b2_vmcore #(.CRD(CRD), .WCRD(WCRD), .MUT(MUT)) u_core (.clk(clk), .rst_n(rst_n), .sid(sid),
        .rgx_t_v(rgx_t_v), .rgx_t_vm(rgx_t_vm), .hv(hv), .hrx(hrx), .th(th), .epoch(epoch), .qfault(qfault), .pop_cmd(pop_cmd),
        .rgx_f_cr(rgx_f_cr), .tkw_f_cr(tkw_f_cr), .fault(fault), .wq(wq), .wq_cr(wq_cr), .wq_done(wq_done), .cq(cq), .cr(cr),
        .xw(xw), .xwa(xwa));
endmodule

// Writer core leaf of the SW VM slice's COLL port: decodes the five receive-leaf heads, issues local wide writes and
// B2 packets, retires per-lane returns.
// Timing structure (r2, coll_vmcore gate 10-14: 31-level oh->ack_rem chain, 31-level port->owners decode, 5,198-load reset):
//   D stage   every receive-leaf output lands in a register together with a shallow decode (local/aligned flag, one-hot
//             bank selects); the epoch travels with its head, so the issue rule (blocked = epoch == issued) is unchanged.
//   issue     five lanes in fixed priority over one-hot bank masks; each bank lane's payload is a constant-index AND-OR.
//   retire    a completing bank's owner lane is read into a registered one-hot (R stage); the next edge adds a popcount
//             tree per lane.  Same credit counters as before (no new credit logic); returns are one edge later.
// Payload registers carry no reset; only valid/state bits do.
module ot_hgi_coll_b2_vmcore #(
    parameter integer CRD = 16, WCRD = 10, MUT = 0
) (
    input wire clk, rst_n,
    input wire [1:0] sid,
    input wire [3:0] rgx_t_v,
    input wire rgx_t_vm,
    input wire [4:0] hv,
    input wire [4*552-1:0] hrx,
    input wire [567:0] th,
    input wire [4:0] epoch, qfault,
    output reg [4:0] pop_cmd,
    output reg [3:0] rgx_f_cr,
    output reg tkw_f_cr,
    output reg fault,
    output wire [8*281-1:0] wq,
    input wire [7:0] wq_cr, wq_done,
    output wire [5*338-1:0] cq,
    input wire [5*274-1:0] cr,
    output wire [651:0] xw,
    input wire [1:0] xwa
);
    reg [1:0] me;
    always @(posedge clk) me <= sid;
    // ---------------- D stage: registered heads + shallow decode ----------------
    wire [199:0] ha_i; wire [2559:0] hd_i; wire [79:0] hm_i;
    for (genvar l = 0; l < 4; l = l + 1) begin : g_h
        assign ha_i[l*40 +: 40] = hrx[l*552 + 512 +: 40]; assign hd_i[l*512 +: 512] = hrx[l*552 +: 512];
        assign hm_i[l*16 +: 16] = 16'hffff;
    end
    assign ha_i[160 +: 40] = th[567:528]; assign hm_i[64 +: 16] = th[527:512]; assign hd_i[2048 +: 512] = th[511:0];
    reg [199:0] ha; reg [2559:0] hd; reg [79:0] hm;
    reg [4:0] hv_d, ep_d, okl, abad; reg [7:0] bo0 [0:4], bo1 [0:4]; reg [4:0] qf_d;
    always @(posedge clk) begin
        ha <= ha_i; hd <= hd_i; hm <= hm_i;
        for (integer l = 0; l < 5; l = l + 1) begin
            reg [39:0] a; a = ha_i[l*40 +: 40];
            // s0 = a[18:3]; local and aligned: s0[15] = 0, s0[14:13] = me, no carry into bit 13 (s1 = s0 + 1 local too)
            okl[l] <= !a[18] && a[17:16] == me && !(&a[15:3]) && a[2:0] == 0 && a[39:19] == 0;
            abad[l] <= a[2:0] != 0 || |a[39:19];
            bo0[l] <= 8'b1 << a[5:3]; bo1[l] <= 8'b1 << 3'(a[5:3] + 3'd1);
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin hv_d <= 0; ep_d <= 0; qf_d <= 0; end
        else begin hv_d <= hv; ep_d <= epoch; qf_d <= qfault; end
    reg [4:0] issued_epoch;
    wire [4:0] blocked = ~(ep_d ^ issued_epoch);
    reg vm_q, vm_run; reg [3:0] rv_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin vm_q <= 0; vm_run <= 0; rv_q <= 0; end
        else begin vm_q <= rgx_t_vm; rv_q <= rgx_t_v; if (|rv_q) vm_run <= vm_q; end
    // Preserve the existing real HBM write clients for HBM-space ROW_GATHER.
    wire [3:0] hpop; wire hf;
    ot_hgi_coll_rgx_snk #(.LQ(8)) u_hbm (.clk(clk), .rst_n(rst_n), .rg_w_v(hv_d[3:0] & ~blocked[3:0] & {4{!vm_run}}),
        .rg_w_addr(ha[159:0]), .rg_w_vm(1'b0), .rg_w_data(hd[2047:0]), .rg_w_rdy(hpop),
        .c_req(), .c_gnt(1'b0), .c_q(), .c_cr(32'd0), .c_rsp(32'd0), .xw(xw), .xwa(xwa), .fault(hf));
    localparam integer OD = WCRD + 16, BW = $clog2(OD), CW = $clog2(WCRD+1), OW = $clog2(OD+1), AW = $clog2(2*CRD+1);
    reg [CW-1:0] wc [0:7]; reg [7:0] wcnz;
    reg [2:0] owners [0:7][0:OD-1]; reg [BW-1:0] oh [0:7], ot [0:7]; reg [OW-1:0] on [0:7];
    reg [2:0] pc [0:4]; reg half [0:4]; reg [15:0] itag [0:4], rtag [0:4]; reg [AW-1:0] ack_rem [0:4];
    reg [5*274-1:0] cr_q; reg [7:0] wcr_q, wdone_q;
    always @(posedge clk) begin cr_q <= cr; wcr_q <= wq_cr; wdone_q <= wq_done; end
    // ---------------- issue ----------------
    reg [4:0] wp, pp, go; reg [7:0] take;
    always @* begin
        reg [7:0] used;
        wp = 0; pp = 0; take = 0; used = 0;
        for (integer l = 0; l < 5; l = l + 1) begin
            go[l] = hv_d[l] && !blocked[l] && (l == 4 || vm_run);
            if (go[l] && okl[l]) begin
                if (!(|(used & (bo0[l] | bo1[l]))) && |(bo0[l] & wcnz) && |(bo1[l] & wcnz)) begin
                    wp[l] = 1; used = used | bo0[l] | bo1[l];
                end
            end else if (go[l] && pc[l] != 0) pp[l] = 1;
        end
        take = used;
    end
    // bank lane b payload: constant-index AND-OR over the lanes that won it (sector 0 or sector 1 of that lane)
    reg [7:0] wq_v; reg [8*280-1:0] wq_p; reg [4:0] cq_v; reg [5*337-1:0] cq_p;
    assign wq = {wq_v[7], wq_p[7*280 +: 280], wq_v[6], wq_p[6*280 +: 280], wq_v[5], wq_p[5*280 +: 280], wq_v[4], wq_p[4*280 +: 280],
                 wq_v[3], wq_p[3*280 +: 280], wq_v[2], wq_p[2*280 +: 280], wq_v[1], wq_p[1*280 +: 280], wq_v[0], wq_p[0 +: 280]};
    for (genvar l = 0; l < 5; l = l + 1) begin : g_cq
        assign cq[l*338 +: 338] = {cq_v[l], cq_p[l*337 +: 337]};
    end
    always @(posedge clk) begin
        for (integer b = 0; b < 8; b = b + 1) begin
            reg [279:0] y; y = 0;
            for (integer l = 0; l < 5; l = l + 1) begin
                reg [15:0] s0, s1; s0 = ha[l*40+3 +: 16]; s1 = s0 + 1'b1;
                if (wp[l] && bo0[l][b]) y = y | {s0, hd[l*512 +: 256], hm[l*16 +: 8]};
                if (wp[l] && bo1[l][b]) y = y | {s1, hd[l*512+256 +: 256], hm[l*16+8 +: 8]};
            end
            wq_p[b*280 +: 280] <= y;
        end
        for (integer l = 0; l < 5; l = l + 1) begin
            reg [15:0] s0, s1; reg [31:0] bm;
            s0 = ha[l*40+3 +: 16]; s1 = s0 + 1'b1;
            bm = 0; for (integer j = 0; j < 8; j = j + 1) bm[j*4 +: 4] = {4{hm[l*16 + (half[l] ? 8 : 0) + j]}};
            // old/native B2 packet ABI: v,we,byte address,data,byte mask,transaction tag.
            cq_p[l*337 +: 337] <= {1'b1,11'd0,(half[l] ? s1 : s0),5'd0,(half[l] ? hd[l*512+256 +: 256] : hd[l*512 +: 256]),bm,itag[l]};
        end
        for (integer b = 0; b < 8; b = b + 1)
            if (take[b]) for (integer l = 0; l < 5; l = l + 1) if (wp[l] && (bo0[l][b] || bo1[l][b])) owners[b][ot[b]] <= 3'(l);
    end
    wire [4:0] pop;
    for (genvar l = 0; l < 5; l = l + 1) begin : g_pop
        if (l < 4) assign pop[l] = wp[l] || (pp[l] && half[l]) || hpop[l];
        else assign pop[l] = wp[l] || (pp[l] && half[l]);
    end
    // ---------------- retire: R stage (owner one-hot) then per-lane popcount ----------------
    reg [4:0] dn_own [0:7]; reg [4:0] crr;
    reg [3:0] cnt [0:4];
    always @* for (integer l = 0; l < 5; l = l + 1) begin
        cnt[l] = 4'(crr[l]);
        for (integer b = 0; b < 8; b = b + 1) cnt[l] = cnt[l] + 4'(dn_own[b][l]);
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wq_v <= 0; cq_v <= 0; rgx_f_cr <= 0; tkw_f_cr <= 0; fault <= 0; issued_epoch <= '1; pop_cmd <= 0; crr <= 0; wcnz <= '1;
            for (integer b = 0; b < 8; b = b + 1) begin wc[b] <= CW'(WCRD); oh[b] <= 0; ot[b] <= 0; on[b] <= 0; dn_own[b] <= 0; end
            for (integer l = 0; l < 5; l = l + 1) begin pc[l] <= 4; half[l] <= 0; itag[l] <= 0; rtag[l] <= 0; ack_rem[l] <= 0; end
        end else begin
            wq_v <= take; cq_v <= pp; pop_cmd <= pop; rgx_f_cr <= 0; tkw_f_cr <= 0;
            if ((|qf_d) || hf) fault <= 1;
            for (integer l = 0; l < 5; l = l + 1) begin
                if (pop[l]) issued_epoch[l] <= ep_d[l];
                pc[l] <= pc[l] - 3'(pp[l]) + 3'(cr_q[l*274+273]);
                if (pp[l]) begin half[l] <= !half[l]; itag[l] <= itag[l] + 1'b1; end
                crr[l] <= cr_q[l*274+273];
                if (cr_q[l*274+273]) begin
                    if (!cr_q[l*274+256] || cr_q[l*274+257 +: 16] != rtag[l]) fault <= 1;
                    rtag[l] <= rtag[l] + 1'b1;
                end
                if (hv_d[l] && (l == 4 || vm_run) && abad[l]) fault <= 1;
            end
            for (integer b = 0; b < 8; b = b + 1) begin
                reg [CW-1:0] wn; wn = wc[b] - CW'(take[b]) + CW'(wcr_q[b]);
                wc[b] <= wn; wcnz[b] <= wn != 0;
                if (take[b]) ot[b] <= (ot[b] == BW'(OD-1)) ? '0 : ot[b] + 1'b1;
                dn_own[b] <= 0;
                if (wdone_q[b]) begin
                    if (on[b] == 0) fault <= 1;
                    else dn_own[b] <= 5'b1 << owners[b][oh[b]];
                    oh[b] <= (oh[b] == BW'(OD-1)) ? '0 : oh[b] + 1'b1;
                end
                on[b] <= on[b] + OW'(take[b]) - OW'(wdone_q[b]);
            end
            for (integer l = 0; l < 5; l = l + 1) begin
                reg [AW:0] na; na = (AW+1)'(ack_rem[l]) + (AW+1)'(cnt[l]);
                if (na >= 2) begin
                    if (l < 4) rgx_f_cr[l] <= 1; else tkw_f_cr <= 1;
                    na = na - 2;
                end
                ack_rem[l] <= AW'(na);
                if (l < 4 && hpop[l]) rgx_f_cr[l] <= 1;
            end
            if (MUT == 1) begin rgx_f_cr <= pop[3:0]; tkw_f_cr <= pop[4]; end
        end
    end
endmodule
`default_nettype wire
