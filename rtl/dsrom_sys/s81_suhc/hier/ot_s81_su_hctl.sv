`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_su_hctl (s81-suhc-hier-1011, 2026-10-11): the control tile of the hierarchical SU slab master dsfd_sp_su_h.
// It holds the job state of ot_s81_su_core WITHOUT the engines, the operand beat assembly or the result row FIFO:
//   - takes the adapter's command (e_cmd_*), fetches the descriptor + parameter rows, issues the operand row reads;
//   - counts the VM responses (the pin owners forward each slot's valid and descriptor fields; the rows themselves go
//     from the pin owners straight onto the down spine, the tiles numbering them from the job announce);
//   - counts the write slots the pin owners issue and pulses e_done_v once the job's last result row write has been
//     issued (the done contract: the count reaches it after the write), the SE job also waiting for every softmax
//     tile's den.
// Job start is announced on the down chain (dn_st with kind / gain set / FP4 / job id) ahead of its parameter rows.
// QN / KV jobs: operand reads wait for the norm tile's ready (gain vectors loaded, go issued) for this job id.
// Result writes: QB / SW exponent rows are written by each lane tile under its word mask (nw counts writes).
// MUT (bench negative controls): 1 done before the result writes (once the operand rows are in: the done contract
// ignored; done ONE write early, the flat core's m1, is behaviour-equivalent here: this tile counts the writes 2 + NRL
// cycles after the pin owners issue them); 2 done tag flipped (the tile MUTs: 3, 4, 5).
// RA / RB / QR (s81-functional-token 2026-10-14, die item F1; tile ot_s81_su_rxt): ONE operand row read a cycle (RA one
// every 16 / RAL cycles), RB interleaved score row r / bias row r (the bias rows follow the cnt score rows), QR the 4 rope
// rows of each head (in_base + 32 h + 28 .. 31); result writes RA / RB cnt rows, QR 4 cnt rows (one write slot).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_hctl #(
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16,
    parameter integer S_RD = 16, S_WR = 16, NSW = 4, NQB = 2, NQN = 1, NKV = 1,
    parameter integer MUT = 0,
    parameter integer RAL = 16,
    parameter integer QRW = 2           // QR rope rows read a cycle (2: rows j, j + 1 of a head on slots 0 / 1; the rxt
                                        // tile takes the pair and writes two result rows on write slots 0 / 1)
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   e_cmd_v,
    input  wire [83:0]            e_cmd_d,
    output wire                   e_cmd_ready,
    output reg                    e_done_v,
    output reg  [7:0]             e_done_tag,
    output reg  [S_RD-1:0]        rq_v,
    output reg  [S_RD*14-1:0]     rq_row,
    input  wire [S_RD-1:0]        rs_v,           // the VM responses (the pin owners' copy)
    input  wire [S_RD*30-1:0]     rs_f,           // each slot's descriptor fields {cnt 16, ibase 14}
    output wire                   busy,
    output reg                    fault,
    output reg  [3:0]             fault_code,
    output reg  [31:0]            st_jobs,
    // down chain head
    output reg                    dn_st,
    output reg  [3:0]             dn_kind,
    output reg  [1:0]             dn_gsel,
    output reg                    dn_fp4,
    output reg  [7:0]             dn_jid,
    // up spine: the write slots issued (the pin owners' copy) and the tiles' status
    input  wire [S_WR-1:0]        up_v,
    input  wire                   up_fu,          // a tile's unit faulted (sticky)
    input  wire                   up_fo,          // a tile's result staging overflowed (sticky)
    input  wire                   up_alive,       // every tile out of reset
    input  wire                   up_den,         // every softmax tile holds this SE job's den
    input  wire                   up_rdy,         // a norm tile's go issued for job up_rjid
    input  wire [7:0]             up_rjid,
    input wire up_cp_done
);
    localparam integer DQ = 1280, DK = 512, NVQ = DQ / QN_N;
    localparam integer SMW = SM_H * SM_LPH;
    localparam integer RQN = QN_N / 16, RKV = KV_N / 16, RQB = 2 * QB_NB, RSW = SW_W / 16, RSM = SMW / 16;
    localparam integer NPV = 512 / SM_LPH;
    localparam [3:0] K_QN = 0, K_KV = 1, K_QB = 2, K_SW = 3, K_SE = 4, K_SO = 5, K_GQ = 6, K_GK = 7;
    localparam [3:0] K_RA = 8, K_RB = 9, K_QR = 10, K_RW = 11, K_CN = 12, K_IK = 13, K_CP = 14;   // RW: s81-ftok r3 die item F11 (ffn.weights)
    localparam integer XSUB = 16 / RAL;

    reg         run;
    reg  [3:0]  kind;
    reg         jslot;
    reg  [7:0]  jtag, jid;
    reg  [13:0] dbase;
    reg  [1:0]  ph;
    reg  [29:0] p0;                                  // the descriptor row's {cnt, ibase}
    reg  [15:0] ri, rr, np, nrow, nw, cw;
    reg         sm_owner_v, sm_owner;
    reg         rdy_ok, alive_q;
    reg  [1:0]  xs;                                  // RA read pacing (RAL < 16)
    assign e_cmd_ready = !run && !fault && alive_q;
    assign busy = run;
    wire take = e_cmd_v && e_cmd_ready;
    wire [23:0] c_arg = e_cmd_d[30:7];
    wire [13:0] ibase = p0[13:0];

    function automatic [15:0] nparams(input [3:0] k);
        nparams = (k == K_KV || k == K_CN || k == K_IK || k == K_SO || k == K_QR) ? 5 : (k == K_SE) ? 1 + (SM_H + 15) / 16 : 1;
    endfunction
    function automatic [15:0] rows_out(input [3:0] k, input [15:0] c);     // result row WRITES of the job
        case (k)
            K_QN: rows_out = NVQ * (QN_N / 64 + NQN);             // the exps row: one masked write a lane tile
            K_KV: rows_out = KV_N / 64 + NKV + KV_N / 32;
            K_CN: rows_out = 48; K_IK: rows_out = 8;
            K_QB: rows_out = c * (QB_NB / 2 + NQB + QB_NB);        // the exps row: one masked write a lane tile
            K_SW: rows_out = c * (SW_W / 64 + NSW + SW_W / 32);
            K_SE: rows_out = c * RSM;
            K_SO: rows_out = NPV * (SMW / 32);
            K_RA, K_RB: rows_out = c;
            K_QR: rows_out = 4 * c;
            K_RW: rows_out = 1;                                   // one word-masked write (the SW descriptor's weights)
            default: rows_out = 0;
        endcase
    endfunction
    function automatic [15:0] rows_in(input [3:0] k, input [15:0] c);
        case (k)
            K_QN: rows_in = NVQ * RQN;  K_KV, K_CN, K_IK: rows_in = RKV;  K_QB: rows_in = c * RQB;  K_SW: rows_in = c * 2 * RSW;
            K_SE: rows_in = c * RSM;    K_SO: rows_in = NPV * RSM; K_GQ: rows_in = DQ / 16; K_GK: rows_in = DK / 16;
            K_RA: rows_in = c;          K_RB: rows_in = 2 * c;     K_QR: rows_in = 4 * c;
            K_RW: rows_in = c;                                     // the ids row + the score rows, contiguous
            default: rows_in = 0;
        endcase
    endfunction

    integer s;
    // synchronous reset from a local relay flop: the reset is a registered full-cycle path into the D logic (no
    // async recovery check over a ~600-flop reset net from the slab reset synchroniser)
    reg rst_q;
    always @(posedge clk) rst_q <= rst_n;
    // response / write-slot accounting rung: the 16-slot popcounts and the first-response descriptor select are
    // trees registered one cycle ahead of the job counters (was one 16-deep ripple count -> select -> compare ->
    // rows_in / rows_out multiply -> nw chain in a single cycle, ~1.34 ns)
    reg  [4:0]  rs_n, up_n;
    reg         rs_any;
    reg  [29:0] rs_pn;
    // first-response descriptor select as a balanced binary tree (lower slot wins at every node): log2(S_RD) 2:1
    // mux levels on the data and an OR tree on the selects.  Was a 16-deep priority ripple (rs_v[14] -> 13 AO/OA
    // levels -> rs_pn, TT -57 ps in route dsfd_su_t_ctl_rt-rt-77e72f74a).  Same function: lowest set slot, 0 if none.
    localparam integer SRP = (S_RD <= 1) ? 1 : (1 << $clog2(S_RD));
    always @(posedge clk) begin : acct
        integer i, w;
        reg [4:0] a, b;
        reg [29:0] f;
        reg any;
        reg [29:0] tf [0:SRP-1];
        reg        ta [0:SRP-1];
        a = 0; b = 0;
        for (i = 0; i < S_RD; i = i + 1) a = a + rs_v[i];
        for (i = 0; i < S_WR; i = i + 1) b = b + up_v[i];
        for (i = 0; i < SRP; i = i + 1) begin
            tf[i] = (i < S_RD) ? rs_f[30 * i +: 30] : 30'd0;
            ta[i] = (i < S_RD) ? rs_v[i] : 1'b0;
        end
        for (w = SRP; w > 1; w = w / 2)
            for (i = 0; i < w / 2; i = i + 1) begin
                tf[i] = ta[2 * i] ? tf[2 * i] : tf[2 * i + 1];
                ta[i] = ta[2 * i] | ta[2 * i + 1];
            end
        any = ta[0];
        f = any ? tf[0] : 30'd0;
        if (!rst_n || !rst_q) begin rs_n <= 0; up_n <= 0; rs_any <= 0; end
        else begin rs_n <= a; up_n <= b; rs_any <= any; end
        rs_pn <= f;
    end
    always @(posedge clk) begin
        if (!rst_n || !rst_q) begin
            run <= 0; kind <= 0; jslot <= 0; jtag <= 0; jid <= 0; dbase <= 0; ph <= 0; p0 <= 0;
            ri <= 0; rr <= 0; np <= 0; nrow <= 0; nw <= 0; cw <= 0; sm_owner_v <= 0; sm_owner <= 0;
            rdy_ok <= 0; alive_q <= 0; xs <= 0;
            e_done_v <= 0; e_done_tag <= 0; fault <= 0; fault_code <= 0; st_jobs <= 0; rq_v <= 0; rq_row <= 0;
            dn_st <= 0; dn_kind <= 0; dn_gsel <= 0; dn_fp4 <= 0; dn_jid <= 0;
        end else begin
            e_done_v <= 0; rq_v <= 0; dn_st <= 0;
            alive_q <= up_alive;
            if (up_rdy && up_rjid == jid) rdy_ok <= 1'b1;
            if (up_fu && !fault) begin fault <= 1; fault_code <= 1; end
            if (up_fo) begin fault <= 1; fault_code <= 5; end
            if (take) begin
                run <= 1; kind <= c_arg[23:20]; jslot <= e_cmd_d[83]; jtag <= {e_cmd_d[83], e_cmd_d[6:0]};
                dbase <= c_arg[13:0]; ph <= 0; ri <= 0; rr <= 0; np <= nparams(c_arg[23:20]); cw <= 0;
                rdy_ok <= 1'b0; jid <= jid + 8'd1;
                dn_st <= 1'b1; dn_kind <= c_arg[23:20]; dn_gsel <= c_arg[19:18]; dn_fp4 <= c_arg[14]; dn_jid <= jid + 8'd1;
                if (c_arg[23:20] > K_CP) begin fault <= 1; fault_code <= 3; end
                if (c_arg[23:20] == K_SO && !(sm_owner_v && sm_owner == e_cmd_d[83])) begin fault <= 1; fault_code <= 6; end
            end
            if (run && !fault) begin
                if (ph == 0) begin
                    for (s = 0; s < S_RD; s = s + 1)
                        if (ri + s < np) begin rq_v[s] <= 1; rq_row[14 * s +: 14] <= dbase + ri + s; end
                    if (ri + S_RD >= np) ph <= 1;
                    ri <= ri + S_RD;
                end
                if (ph == 0 || ph == 1) begin
                    begin : prsp
                        reg [15:0] c;
                        reg [29:0] pn;
                        c = rr + rs_n;
                        pn = (rr == 0 && rs_any) ? rs_pn : p0;
                        p0 <= pn; rr <= c;
                        if (c == np) begin                     // parameters in: size the job next cycle (ph 3)
                            ph <= 3; ri <= 0; rr <= 0;
                            if (kind == K_SE) begin sm_owner_v <= 1; sm_owner <= jslot; end
                        end
                    end
                end
                if (ph == 3) begin                             // rows_in / rows_out from the registered descriptor
                    nrow <= rows_in(kind, p0[14 +: 16]);
                    nw <= rows_out(kind, p0[14 +: 16]);
                    ph <= 2;
                end
                if (ph == 2 && (kind == K_RA || kind == K_RB || kind == K_QR || kind == K_RW)) begin
                    // one operand row a cycle (RA: one every XSUB cycles) on slot 0
                    if (kind == K_RB && ri < nrow) begin
                        // RB pair issue (s81-romB2 2026-10-14): score row r on slot 0 and its bias row r on slot 1 in the
                        // SAME cycle (the rows land together at the tile, which adds them at once): 2 rows a cycle
                        rq_v[0] <= 1; rq_v[1] <= 1;
                        rq_row[13:0] <= ibase + {1'b0, ri[13:1]};
                        rq_row[27:14] <= ibase + {1'b0, ri[13:1]} + p0[14 +: 14];
                        ri <= ri + 2;
                    end else if (kind == K_QR && QRW > 1 && ri < nrow) begin
                        // QR pair issue (s81-romB3 2026-10-14): rope rows j, j + 1 (j even) of head h on slots 0 / 1
                        rq_v[0] <= 1; rq_v[1] <= 1;
                        rq_row[13:0] <= ibase + {ri[13:2], 5'd0} + 14'd28 + {12'd0, ri[1:0]};
                        rq_row[27:14] <= ibase + {ri[13:2], 5'd0} + 14'd29 + {12'd0, ri[1:0]};
                        ri <= ri + 2;
                    end else if (kind != K_RB && ri < nrow && (kind != K_RA || xs == 0)) begin
                        rq_v[0] <= 1;
                        rq_row[13:0] <= (kind == K_QR) ? ibase + {ri[13:2], 5'd0} + 14'd28 + {12'd0, ri[1:0]} : ibase + ri[13:0];
                        ri <= ri + 1;
                    end
                    xs <= (kind == K_RA && XSUB > 1) ? ((xs == XSUB - 1) ? 2'd0 : xs + 2'd1) : 2'd0;
                    begin : xrsp
                        reg [15:0] c;
                        c = rr + rs_n;
                        rr <= c;
                    end
                end
                if(ph==2 && kind==K_CP && up_cp_done)begin
                    run<=0;e_done_v<=1;e_done_tag<=jtag;st_jobs<=st_jobs+1;
                end
                if (ph == 2 && !(kind == K_RA || kind == K_RB || kind == K_QR || kind == K_RW || kind==K_CP)) begin
                    if ((kind != K_QN && kind != K_KV) || rdy_ok) begin
                        for (s = 0; s < S_RD; s = s + 1)
                            if (ri + s < nrow) begin rq_v[s] <= 1; rq_row[14 * s +: 14] <= ibase + ri + s; end
                        ri <= ri + S_RD;
                    end
                    begin : orsp
                        reg [15:0] c;
                        c = rr + rs_n;
                        rr <= c;
                    end
                    if (MUT == 1 && nw != 0 && rr == nrow && nrow != 0) begin
                        run <= 0; e_done_v <= 1; e_done_tag <= jtag; st_jobs <= st_jobs + 1;
                    end
                    if ((kind == K_GQ || kind == K_GK) && rr == nrow && nrow != 0) begin
                        run <= 0; e_done_v <= 1; e_done_tag <= (MUT == 2) ? (jtag ^ 8'h01) : jtag; st_jobs <= st_jobs + 1;
                    end
                end
            end
            // ------------------------------------------------------------- write slots issued -> completion
            begin : outp
                reg [15:0] n_out;
                n_out = {11'd0, up_n};
                if (run && ph == 2 && nw != 0) begin
                    cw <= cw + n_out;
                    if (MUT != 1 && cw + n_out >= nw && (kind != K_SE || up_den)) begin
                        run <= 0; e_done_v <= 1; e_done_tag <= (MUT == 2) ? (jtag ^ 8'h01) : jtag;
                        st_jobs <= st_jobs + 1;
                    end
                end
            end
        end
    end
`ifdef SU_RX_TRACE
    // cycle trace of the RA / RB / QR job phases (bench only)
    reg [31:0] tr_cyc;
    always @(posedge clk) begin
        tr_cyc <= (!rst_n) ? 32'd0 : tr_cyc + 32'd1;
        if (take && c_arg[23:20] >= K_RA) $display("RXTR hctl %0d take kind %0d", tr_cyc, c_arg[23:20]);
        if (run && kind >= K_RA && ph == 3) $display("RXTR hctl %0d params_in", tr_cyc);
        if (run && kind >= K_RA && ph == 2 && rq_v[0] && ri == 1) $display("RXTR hctl %0d first_operand_issued", tr_cyc);
        if (run && kind >= K_RA && ph == 2 && rq_v[0] && ri >= nrow) $display("RXTR hctl %0d last_operand_issued nrow %0d", tr_cyc, nrow);
        if (run && kind >= K_RA && ph == 2 && rs_n != 0 && rr == 0) $display("RXTR hctl %0d first_operand_back", tr_cyc);
        if (run && kind >= K_RA && up_n != 0 && cw == 0) $display("RXTR hctl %0d first_write_seen", tr_cyc);
        if (e_done_v && kind >= K_RA) $display("RXTR hctl %0d done nw %0d", tr_cyc, nw);
    end
`endif
endmodule
