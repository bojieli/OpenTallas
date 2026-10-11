`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_su_hctl (s81-suhc-hier-1011, 2026-10-11): the control tile of the hierarchical SU slab master dsfd_sp_su_h.
// It holds the job state of ot_s81_su_core WITHOUT the engines, the operand beat assembly or the result row FIFO:
//   - takes the adapter's command (e_cmd_*), fetches the descriptor + parameter rows, issues the operand row reads;
//   - forwards every VM response row, tagged {phase, row index}, onto the DOWN chain (a registered spine through the
//     engine tiles; each tile captures the parameter rows of its own jobs and the operand rows of its own lanes);
//   - registers the UP chain's write row slots onto the VM write port (wq_*) and pulses e_done_v when the job's last
//     result row write is issued (the done contract), the SE job also waiting for every softmax tile's den.
// Job start is announced on the down chain (dn_st with kind / gain set / FP4 / job id) ahead of its parameter rows.
// QN / KV jobs: operand reads wait for the norm tile's ready (gain vectors loaded, go issued) for this job id.
// Result writes: QB / SW exponent rows are written by each lane tile under its word mask (nw counts writes).
// MUT (bench negative controls): 1 done one write early; 2 done tag flipped (the tile MUTs: 3, 4, 5).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_hctl #(
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16,
    parameter integer S_RD = 16, S_WR = 16, NSW = 4, NQB = 2,
    parameter integer MUT = 0
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
    input  wire [S_RD-1:0]        rs_v,
    input  wire [S_RD*512-1:0]    rs_d,
    output reg  [S_WR-1:0]        wq_v,
    output reg  [S_WR*14-1:0]     wq_row,
    output reg  [S_WR*16-1:0]     wq_mask,
    output reg  [S_WR*512-1:0]    wq_d,
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
    output reg  [S_RD-1:0]        dn_v,
    output reg                    dn_ph,          // 0 parameter rows (index from the descriptor row), 1 operand rows
    output reg  [15:0]            dn_idx,         // row index of slot 0 within the phase
    output reg  [S_RD*512-1:0]    dn_d,
    // up chain tail (registered in the nearest tile)
    input  wire [S_WR-1:0]        up_v,
    input  wire [S_WR*14-1:0]     up_a,
    input  wire [S_WR*16-1:0]     up_m,
    input  wire [S_WR*512-1:0]    up_d,
    input  wire                   up_fu,          // a tile's unit faulted (sticky)
    input  wire                   up_fo,          // a tile's result staging overflowed (sticky)
    input  wire                   up_alive,       // every tile out of reset
    input  wire                   up_den,         // every softmax tile holds this SE job's den
    input  wire                   up_rdy,         // a norm tile's go issued for job up_rjid
    input  wire [7:0]             up_rjid
);
    localparam integer DQ = 1280, DK = 512, NVQ = DQ / QN_N;
    localparam integer SMW = SM_H * SM_LPH;
    localparam integer RQN = QN_N / 16, RKV = KV_N / 16, RQB = 2 * QB_NB, RSW = SW_W / 16, RSM = SMW / 16;
    localparam integer NPV = 512 / SM_LPH;
    localparam [3:0] K_QN = 0, K_KV = 1, K_QB = 2, K_SW = 3, K_SE = 4, K_SO = 5, K_GQ = 6, K_GK = 7;

    reg         run;
    reg  [3:0]  kind;
    reg         jslot;
    reg  [7:0]  jtag, jid;
    reg  [13:0] dbase;
    reg  [1:0]  ph;
    reg  [511:0] p0;                                 // the descriptor row
    reg  [15:0] ri, rr, np, nrow, nw, cw;
    reg         sm_owner_v, sm_owner;
    reg         rdy_ok, alive_q;
    assign e_cmd_ready = !run && !fault && alive_q;
    assign busy = run;
    wire take = e_cmd_v && e_cmd_ready;
    wire [23:0] c_arg = e_cmd_d[30:7];
    wire [13:0] ibase = p0[32 +: 14];

    function automatic [15:0] nparams(input [3:0] k);
        nparams = (k == K_KV || k == K_SO) ? 5 : (k == K_SE) ? 1 + (SM_H + 15) / 16 : 1;
    endfunction
    function automatic [15:0] rows_out(input [3:0] k, input [15:0] c);     // result row WRITES of the job
        case (k)
            K_QN: rows_out = NVQ * (QN_N / 64 + 1);
            K_KV: rows_out = KV_N / 64 + 1 + KV_N / 32;
            K_QB: rows_out = c * (QB_NB / 2 + NQB + QB_NB);        // the exps row: one masked write a lane tile
            K_SW: rows_out = c * (SW_W / 64 + NSW + SW_W / 32);
            K_SE: rows_out = c * RSM;
            K_SO: rows_out = NPV * (SMW / 32);
            default: rows_out = 0;
        endcase
    endfunction
    function automatic [15:0] rows_in(input [3:0] k, input [15:0] c);
        case (k)
            K_QN: rows_in = NVQ * RQN;  K_KV: rows_in = RKV;  K_QB: rows_in = c * RQB;  K_SW: rows_in = c * 2 * RSW;
            K_SE: rows_in = c * RSM;    K_SO: rows_in = NPV * RSM; K_GQ: rows_in = DQ / 16; K_GK: rows_in = DK / 16;
            default: rows_in = 0;
        endcase
    endfunction

    integer s;
    always @(posedge clk) begin                      // datapath registers: no reset
        dn_d <= rs_d;
        wq_row <= up_a; wq_mask <= up_m; wq_d <= up_d;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 0; kind <= 0; jslot <= 0; jtag <= 0; jid <= 0; dbase <= 0; ph <= 0; p0 <= 0;
            ri <= 0; rr <= 0; np <= 0; nrow <= 0; nw <= 0; cw <= 0; sm_owner_v <= 0; sm_owner <= 0;
            rdy_ok <= 0; alive_q <= 0;
            e_done_v <= 0; e_done_tag <= 0; fault <= 0; fault_code <= 0; st_jobs <= 0; rq_v <= 0; rq_row <= 0;
            wq_v <= 0; dn_st <= 0; dn_kind <= 0; dn_gsel <= 0; dn_fp4 <= 0; dn_jid <= 0; dn_v <= 0; dn_ph <= 0;
            dn_idx <= 0;
        end else begin
            e_done_v <= 0; rq_v <= 0; dn_st <= 0; dn_v <= 0;
            alive_q <= up_alive;
            if (up_rdy && up_rjid == jid) rdy_ok <= 1'b1;
            if (up_fu && !fault) begin fault <= 1; fault_code <= 1; end
            if (up_fo) begin fault <= 1; fault_code <= 5; end
            if (take) begin
                run <= 1; kind <= c_arg[23:20]; jslot <= e_cmd_d[83]; jtag <= {e_cmd_d[83], e_cmd_d[6:0]};
                dbase <= c_arg[13:0]; ph <= 0; ri <= 0; rr <= 0; np <= nparams(c_arg[23:20]); cw <= 0;
                rdy_ok <= 1'b0; jid <= jid + 8'd1;
                dn_st <= 1'b1; dn_kind <= c_arg[23:20]; dn_gsel <= c_arg[19:18]; dn_fp4 <= c_arg[14]; dn_jid <= jid + 8'd1;
                if (c_arg[23]) begin fault <= 1; fault_code <= 3; end
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
                        reg [511:0] pn;
                        c = rr; pn = p0;
                        for (s = 0; s < S_RD; s = s + 1)
                            if (rs_v[s]) begin if (c == 0) pn = rs_d[512 * s +: 512]; c = c + 1; end
                        p0 <= pn; rr <= c;
                        dn_v <= rs_v; dn_ph <= 1'b0; dn_idx <= rr;
                        if (c == np) begin
                            ph <= 2; ri <= 0; rr <= 0;
                            nrow <= rows_in(kind, pn[64 +: 16]);
                            nw <= rows_out(kind, pn[64 +: 16]);
                            if (kind == K_SE) begin sm_owner_v <= 1; sm_owner <= jslot; end
                        end
                    end
                end
                if (ph == 2) begin
                    if ((kind != K_QN && kind != K_KV) || rdy_ok) begin
                        for (s = 0; s < S_RD; s = s + 1)
                            if (ri + s < nrow) begin rq_v[s] <= 1; rq_row[14 * s +: 14] <= ibase + ri + s; end
                        ri <= ri + S_RD;
                    end
                    begin : orsp
                        reg [15:0] c;
                        c = rr;
                        for (s = 0; s < S_RD; s = s + 1) if (rs_v[s]) c = c + 1;
                        rr <= c;
                        dn_v <= rs_v; dn_ph <= 1'b1; dn_idx <= rr;
                    end
                    if ((kind == K_GQ || kind == K_GK) && rr == nrow && nrow != 0) begin
                        run <= 0; e_done_v <= 1; e_done_tag <= (MUT == 2) ? (jtag ^ 8'h01) : jtag; st_jobs <= st_jobs + 1;
                    end
                end
            end
            // ------------------------------------------------------------- up chain -> VM write port
            begin : outp
                reg [15:0] n_out;
                n_out = 0;
                for (s = 0; s < S_WR; s = s + 1) if (up_v[s]) n_out = n_out + 1;
                wq_v <= up_v;
                if (run && ph == 2 && nw != 0) begin
                    cw <= cw + n_out;
                    if (cw + n_out >= nw - ((MUT == 1) ? 1 : 0) && (kind != K_SE || up_den)) begin
                        run <= 0; e_done_v <= 1; e_done_tag <= (MUT == 2) ? (jtag ^ 8'h01) : jtag;
                        st_jobs <= st_jobs + 1;
                    end
                end
            end
        end
    end
endmodule
