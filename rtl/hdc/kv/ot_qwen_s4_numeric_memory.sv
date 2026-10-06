`timescale 1ns/1ps
// SIMULATION ONLY: existing STREAM4 HBM3E timing checker and exact backing.
// No controller, transport, PHY hardware or physical signoff is claimed here.
// One instance per TP rank; each rank has 128 PCs and all 36 layer regions.
// Host preload/readback uses public_flat_rw mem, 8 little-endian uint32 limbs
// per 256-bit word. Cold POR resets protocol state, never the backing contents;
// warm reset is intentionally absent: all pending return/WR debt survives it.
// Consumers must use canonical Verilator 5.050 alongside the retained engine.
module ot_qwen_s4_numeric_memory #(
    parameter integer MEM_WORDS=36*131072,
    parameter integer PHASE=0,
    parameter integer PULLIN=0
)(
    input wire hclk, rst_n,
    input wire [127:0] row_v,col_v,col_we,
    input wire [128*3-1:0] row_op,
    input wire [128*5-1:0] row_bank,col_bank,col_col,
    input wire [128*19-1:0] row_row,
    input wire [127:0] h_cv,
    input wire [128*24-1:0] h_csec,
    input wire [128*256-1:0] h_cdata,
    input wire [128*9-1:0] h_ctag,
    input wire [128*3-1:0] cred_ret,
    output wire [127:0] h_lv,h_av,
    output wire [128*17-1:0] h_lsec,
    output wire [128*8-1:0] h_lrow,
    output wire [128*256-1:0] h_ldata,
    output wire [128*9-1:0] h_atag,
    output wire phy_fault,
    output wire [15:0] fault_code
);
    localparam integer NPC=128,TAGW=9,CRED=32;
    initial if(MEM_WORDS != 36*131072)
        $fatal(1,"full numerical provider requires all 36 layer regions");
    wire h_rst_n;
    ot_reset_sync u_hrst(.clk(hclk),.async_rst_n(rst_n),.sync_rst_n(h_rst_n));
    reg h_fault; reg [15:0] h_code;
    longint hcyc;
    reg [NPC-1:0] lp_v,ap_v;
    reg [16:0] lp_sec[0:NPC-1]; reg [7:0] lp_row[0:NPC-1];
    reg [255:0] lp_dat[0:NPC-1]; reg [TAGW-1:0] ap_tag[0:NPC-1];
    assign h_lv=lp_v; assign h_av=ap_v;
    assign phy_fault=h_fault; assign fault_code=h_code;
    for(genvar p=0;p<NPC;p=p+1)begin:outputs
        assign h_lsec[p*17+:17]=lp_sec[p];
        assign h_lrow[p*8+:8]=lp_row[p];
        assign h_ldata[p*256+:256]=lp_dat[p];
        assign h_atag[p*TAGW+:TAGW]=ap_tag[p];
    end
    localparam integer LR = 64;
    localparam integer CYC = 1024;
    localparam longint BURST=1024, TCCDL=2560, CL=12500, CWL=6250, RCD=19375, RCDW=9375, RP=16250, RAS=28125,
                       RTP=5625, WR=20625, WTRS=4375, WTRL=6250, RTW=9948, RRDS=2500, RRDL=3125, FAW=15000,
                       RFC=350000, RFCPB=200000, REFI=3900000, RSP=10000, RREFD=8000;

    reg [255:0] mem [0:MEM_WORDS-1] /*verilator public_flat_rw*/;

    function automatic [16:0] p2l(input integer port, input [4:0] bk, input [4:0] cl);
        reg [9:0] j; reg [4:0] q; reg [1:0] k;
        begin
            j = {bk[4:2], cl, bk[1:0]}; q = 5'(port % 32); k = 2'(port / 32);
            p2l = {j[0], q[4], j[9:1], q[3:0], k};
        end
    endfunction
    function automatic integer l2port(input [16:0] l);
        l2port = integer'(l[1:0]) * 32 + integer'({l[15], l[5:2]});
    endfunction
    function automatic [4:0] l2bank(input [16:0] l);
        reg [9:0] j; begin j = {l[14:6], l[16]}; l2bank = {j[9:7], j[1:0]}; end
    endfunction
    function automatic [4:0] l2col(input [16:0] l);
        reg [9:0] j; begin j = {l[14:6], l[16]}; l2col = j[6:2]; end
    endfunction

    longint now;
    bit     b_open [0:NPC-1][0:31]; int b_row [0:NPC-1][0:31];
    longint b_act [0:NPC-1][0:31], b_pre [0:NPC-1][0:31], b_rd [0:NPC-1][0:31], b_wr [0:NPC-1][0:31], b_ref_end [0:NPC-1][0:31];
    longint p_ref0 [0:NPC-1], p_nref [0:NPC-1];
    longint p_last_act [0:NPC-1], p_last_rd [0:NPC-1], p_last_wr [0:NPC-1], p_last_col [0:NPC-1], p_last_ref [0:NPC-1], p_last_refpb_any [0:NPC-1];
    int     p_wr_bg [0:NPC-1];
    longint p_act_bg [0:NPC-1][0:3], p_col_bg [0:NPC-1][0:3], p_faw [0:NPC-1][0:3];
    bit [31:0] p_round [0:NPC-1];
    longint viol /*verilator public_flat_rw*/, n_act /*verilator public_flat_rw*/, n_rd /*verilator public_flat_rw*/,
            n_wr /*verilator public_flat_rw*/, n_ref /*verilator public_flat_rw*/, n_pre, max_land /*verilator public_flat_rw*/;
    longint rq_due [0:NPC-1][0:LR-1]; reg [255:0] rq_dat [0:NPC-1][0:LR-1]; reg [16:0] rq_sec [0:NPC-1][0:LR-1];
    reg [7:0] rq_row [0:NPC-1][0:LR-1];
    integer rq_w [0:NPC-1], rq_r [0:NPC-1];
    longint aq_due [0:NPC-1][0:LR-1]; reg [TAGW-1:0] aq_tag [0:NPC-1][0:LR-1];
    integer aq_w [0:NPC-1], aq_r [0:NPC-1];
    longint lpend [0:NPC-1];                         // landing entries pushed and not yet credited back
    // a WR column command of the previous edge: its captured queue entry arrives now (h_cv)
    reg [NPC-1:0] wc_pend; longint wc_addr [0:NPC-1], wc_now [0:NPC-1]; int wc_bank [0:NPC-1];
    task automatic v(input string what, input integer pc, input integer bk);
        if (viol < 20) $display("HBM_STREAM VIOLATION t=%0d ps pc=%0d bank=%0d %s", now, pc, bk, what);
        viol++;
        h_fault <= 1'b1; h_code[8] <= 1'b1;
    endtask

    integer q, b, gg, k;
    bit trace = 1'b0;
    initial trace = $test$plusargs("hbm_trace");
    always @(posedge hclk or negedge h_rst_n) begin
        if (!h_rst_n) begin
            hcyc = 0;
            h_fault <= 0; h_code <= 0; lp_v <= 0; ap_v <= 0; wc_pend = 0;
            viol = 0; n_act = 0; n_rd = 0; n_wr = 0; n_ref = 0; n_pre = 0; max_land = 0;
            for (q = 0; q < NPC; q = q + 1) begin
                rq_w[q] = 0; rq_r[q] = 0; aq_w[q] = 0; aq_r[q] = 0; lpend[q] = 0;
                p_last_act[q] = -1000000; p_last_rd[q] = -1000000; p_last_wr[q] = -1000000; p_last_col[q] = -1000000;
                p_last_refpb_any[q] = -1000000; p_round[q] = 0; p_wr_bg[q] = 0;
                begin : ph
                    automatic int P = 118;
                    automatic int base = (PHASE + ((q % 32) * P) / 32) % P;
                    p_last_ref[q] = longint'(base + ((base + P + (q % 32)) % 2)) * CYC;
                    p_ref0[q] = p_last_ref[q]; p_nref[q] = 0;
                end
                for (gg = 0; gg < 4; gg = gg + 1) begin p_act_bg[q][gg] = -1000000; p_col_bg[q][gg] = -1000000; p_faw[q][gg] = -1000000; end
                for (b = 0; b < 32; b = b + 1) begin
                    b_open[q][b] = 0; b_act[q][b] = -1000000; b_pre[q][b] = -1000000; b_rd[q][b] = -1000000;
                    b_wr[q][b] = -1000000; b_ref_end[q][b] = 0; b_row[q][b] = 0;
                end
            end
        end else begin
            now = hcyc * CYC;
            // the WR commands of the previous edge: write the captured entry to the array
            for (q = 0; q < NPC; q = q + 1) if (wc_pend[q]) begin
                if (!h_cv[q] || h_csec[q*24 +: 24] != 24'(wc_addr[q]) || wc_addr[q] < 0 || wc_addr[q] >= MEM_WORDS || aq_w[q]-aq_r[q] >= LR) begin
                    now = wc_now[q]; v("WR does not match the oldest queued write", q, wc_bank[q]); now = hcyc * CYC;
                end else begin
                    mem[wc_addr[q]] = h_cdata[q*256 +: 256];
                    gg = aq_w[q] % LR;
                    aq_due[q][gg] = (wc_now[q] + CWL + BURST + RSP + CYC - 1) / CYC;
                    aq_tag[q][gg] = h_ctag[q*TAGW +: TAGW];
                    aq_w[q] = aq_w[q] + 1;
                end
            end
            wc_pend = 0;
            for (q = 0; q < NPC; q = q + 1) begin
                if (row_v[q]) begin
                    automatic int op = row_op[q*3 +: 3], bk = row_bank[q*5 +: 5], rw = row_row[q*19 +: 19], g = bk & 3;
                    case (op)
                        1: begin // ACT
                            n_act++;
                            if (trace) $display("HBMTRACE ACT h=%0d pc=%0d bank=%0d", hcyc, q, bk);
                            if (b_open[q][bk]) v("ACT to open bank", q, bk);
                            if (now < b_pre[q][bk] + RP) v("tRP", q, bk);
                            if (now < b_act[q][bk] + RAS + RP) v("tRC", q, bk);
                            if (now < p_last_act[q] + RRDS) v("tRRD_S", q, bk);
                            if (now < p_act_bg[q][g] + RRDL) v("tRRD_L", q, bk);
                            if (now < p_faw[q][0] + FAW) v("tFAW", q, bk);
                            if (now < b_ref_end[q][bk]) v("ACT during refresh", q, bk);
                            if (now < p_last_refpb_any[q] + RREFD) v("tRREFD", q, bk);
                            b_open[q][bk] = 1; b_row[q][bk] = rw; b_act[q][bk] = now;
                            p_last_act[q] = now; p_act_bg[q][g] = now;
                            p_faw[q][0] = p_faw[q][1]; p_faw[q][1] = p_faw[q][2]; p_faw[q][2] = p_faw[q][3]; p_faw[q][3] = now;
                        end
                        0: begin // PRE
                            n_pre++;
                            if (!b_open[q][bk]) v("PRE closed bank", q, bk);
                            if (now < b_act[q][bk] + RAS) v("tRAS", q, bk);
                            if (now < b_rd[q][bk] + RTP) v("tRTP", q, bk);
                            if (now < b_wr[q][bk] + CWL + BURST + WR) v("tWR", q, bk);
                            b_open[q][bk] = 0; b_pre[q][bk] = now;
                        end
                        6: begin // REFpb
                            n_ref++;
                            if (trace) $display("HBMTRACE REF h=%0d pc=%0d bank=%0d", hcyc, q, bk);
                            if (b_open[q][bk]) v("REFpb to open bank", q, bk);
                            if (now < b_pre[q][bk] + RP) v("tRP (REFpb)", q, bk);
                            if (now < b_act[q][bk] + RAS + RP) v("tRC (REFpb)", q, bk);
                            if (now < b_ref_end[q][bk]) v("REFpb during refresh", q, bk);
                            if (now < p_last_act[q] + RREFD) v("tRREFD (REFpb after ACT)", q, bk);
                            if (now < p_last_refpb_any[q] + RREFD) v("tRREFD (REFpb after REFpb)", q, bk);
                            if (p_round[q][bk]) v("REFpb bank twice in one round", q, bk);
                            p_round[q][bk] = 1; if (&p_round[q]) p_round[q] = 0;
                            if (PULLIN == 0) begin
                                if (now - p_last_ref[q] > REFI / 32) v("REFpb late", q, bk);
                                p_last_ref[q] = now;
                            end else begin
                                //: pull-in: the k-th REFpb is due by origin + k * tREFI/32 and may come at most PULLIN
                                //: controller periods (118 cycles) before the controller's own schedule
                                p_nref[q]++;
                                if (now > p_ref0[q] + p_nref[q] * (REFI / 32)) v("REFpb late", q, bk);
                                if (now < p_ref0[q] + (p_nref[q] - PULLIN) * 118 * CYC - 2 * CYC) v("REFpb pulled in too far", q, bk);
                            end
                            p_last_refpb_any[q] = now;
                            b_ref_end[q][bk] = now + RFCPB;
                        end
                        default: v("row op not used by this controller", q, bk);
                    endcase
                end
                if (PULLIN == 0 && now - p_last_ref[q] > REFI / 32) begin v("refresh overdue", q, 0); p_last_ref[q] = now; end
                if (PULLIN != 0 && now > p_ref0[q] + (p_nref[q] + 1) * (REFI / 32)) begin v("refresh overdue", q, 0); p_nref[q]++; end
                if (col_v[q]) begin
                    automatic int bk = col_bank[q*5 +: 5], cl = col_col[q*5 +: 5], g = bk & 3;
                    automatic logic [16:0] ls = p2l(q, 5'(bk), 5'(cl));
                    automatic longint a = longint'(b_row[q][bk]) * 131072 + ls;
                    if (!b_open[q][bk]) v(col_we[q] ? "WR closed bank" : "RD closed bank", q, bk);
                    if (now < b_act[q][bk] + (col_we[q] ? RCDW : RCD)) v("tRCD", q, bk);
                    if (now < p_last_col[q] + BURST) v("tCCD_S", q, bk);
                    if (now < p_col_bg[q][g] + TCCDL) v("tCCD_L", q, bk);
                    if (now < b_ref_end[q][bk]) v("column command during refresh", q, bk);
                    if (b_row[q][bk] * 131072 >= MEM_WORDS) v("row beyond the backing store", q, bk);
                    p_last_col[q] = now; p_col_bg[q][g] = now;
                    if (!col_we[q]) begin
                        if (now < p_last_wr[q] + CWL + BURST + ((p_wr_bg[q] == g) ? WTRL : WTRS)) v("tWTR", q, bk);
                        n_rd++;
                        p_last_rd[q] = now; b_rd[q][bk] = now;
                        if (a < 0 || a >= MEM_WORDS || rq_w[q]-rq_r[q] >= LR)
                            $fatal(1,"numerical provider read bounds/finite return queue pc=%0d address=%0d",q,a);
                        k = rq_w[q] % LR;
                        rq_due[q][k] = (now + CL + BURST + RSP + CYC - 1) / CYC;
                        rq_dat[q][k] = mem[a];
                        rq_sec[q][k] = ls; rq_row[q][k] = 8'(b_row[q][bk]);
                        rq_w[q] = rq_w[q] + 1;
                    end else begin
                        if (now < p_last_rd[q] + RTW) v("tRTW", q, bk);
                        n_wr++;
                        p_last_wr[q] = now; p_wr_bg[q] = g; b_wr[q][bk] = now;
                        if (trace) $display("HBMTRACE WR h=%0d pc=%0d bank=%0d sec=%0d", hcyc, q, bk, a);
                        wc_pend[q] = 1'b1; wc_addr[q] = a; wc_now[q] = now; wc_bank[q] = bk;
                    end
                end
            end
            for (gg = 0; gg < NPC / 2; gg = gg + 1) if (row_v[2*gg] && row_v[2*gg+1]) v("two row commands on one channel slot", 2*gg, 0);
            // returns: the beat due at the NEXT edge is presented now and pushed into the landing FIFO at that edge
            for (q = 0; q < NPC; q = q + 1) begin
                lpend[q] = lpend[q] - longint'(cred_ret[q*3 +: 3]);
                if (lpend[q] < 0) v("credit without a returned landing",q,0);
                if (rq_r[q] != rq_w[q] && rq_due[q][rq_r[q] % LR] <= hcyc + 1) begin
                    k = rq_r[q] % LR;
                    lp_v[q] <= 1'b1; lp_dat[q] <= rq_dat[q][k]; lp_sec[q] <= rq_sec[q][k]; lp_row[q] <= rq_row[q][k];
                    rq_r[q] = rq_r[q] + 1; lpend[q] = lpend[q] + 1;
                    if (lpend[q] > CRED) v("finite landing credit overflow",q,0);
                    if (lpend[q] > max_land) max_land = lpend[q];
                end else lp_v[q] <= 1'b0;
                if (aq_r[q] != aq_w[q] && aq_due[q][aq_r[q] % LR] <= hcyc + 1) begin
                    k = aq_r[q] % LR;
                    ap_v[q] <= 1'b1; ap_tag[q] <= aq_tag[q][k];
                    aq_r[q] = aq_r[q] + 1;
                end else ap_v[q] <= 1'b0;
            end
            hcyc = hcyc + 1;
        end
    end
endmodule
