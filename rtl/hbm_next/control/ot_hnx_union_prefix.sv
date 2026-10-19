`timescale 1ns/1ps
`default_nettype none
// HBM-NEXT LH-P3UNITS/UNIONVAR 10-19: factored ordered-cardinality union dispatcher (COORD 07:26 + HNEXT-FACTORED-NEXT).
// Sits beside the IDX.UNION engine (ot_hnx_idx_union_static) and passively TAPS its registered VM packet-write bus cq.
// IDX.UNION's write timeline is data-independent (T = N k table slots in ascending slot order, then O sectors, then D),
// so the tap sees every union expert's row-table word 0 (= c_u, the expert's position cardinality) at a compiled edge.
//
// PREFIX (during the IDX write phase, no extra VM traffic):
//   slot i (ascending union order, word-0 byte mask 0xf = valid expert) -> c_i, then two exclusive prefix accumulators
//   P1[i] = sum_{j<i} D1[c_j] (loop 1: w1/w3), P2[i] = sum_{j<i} D2[c_j] (loop 2: w2) and one masked metadata write
//   {c_i[3:0], P2[i][31:0], P1[i][31:0]} into an existing 1R1W 1024x256 SRAM macro (>2 kb: safe-design item 5).
//   Pipeline: E0 pin capture of the tap fields, E1 registered one-hot select D1/D2[c] (static index, 16 entries),
//   E2 accumulate + SRAM write.  The D sector write (d_base) closes the table: ready 2 edges after its tap capture.
// DISPATCH (after the real IDX union_v; never waits on ready/credits; any late/illegal case FAULTS, never stalls):
//   S = the edge sampling union_v (requires ready and tap U == union_count, else fault).  Event times relative to S:
//     loop 1 slot i : B1 + P1[i]
//     loop 2 slot i : B1 + T1 + G + P2[i]          (T1 = P1[U], registered at S)
//     tail          : B1 + T1 + G + T2             (T2 = P2[U]; the fixed post-loop suffix starts here)
//   launch = {loop, slot, c, kref = KB[loop] + c - 1}: kref indexes the PREINSTALLED per-cardinality kernel descriptor
//   (c = 1..N) in the unit programme targets; no runtime code generation.  Port schedule (explicit, 1R1W):
//   write port only in the tap phase, read port only in the dispatch phase (busy), one read / event:
//   READ (r_ce) -> macro rd_out -> CAP (capture rung beside the macro) -> WAIT (compare, launch registered).
//   READ, CAP and FORM (evt = base + captured start) are registered stages, so an event is >= 4 edges after the previous
//   launch (or after S): cfg legality requires B1 >= 4 and every D1[c], D2[c] >= 4 (kernel spans are hundreds of edges).
//   c is 5 bits (c_u <= N <= 16).
// MUT (bench mutants): 1 = selects the neighbouring cardinality kernel (c-1) and its duration (wrong variant);
//   2 = inclusive prefix (start includes own duration); 3 = U-only reservation (every expert uses the c = n_rows kernel).
module ot_hnx_union_prefix #(
    parameter integer MUT = 0
)(
    input  wire          clk,
    input  wire          rst_n,
    // configuration (idle only): addr 0..15 D1[c=addr+1], 16..31 D2[c=addr-15], 32 B1, 33 G, 34 KB1, 35 KB2, 36 KBT
    input  wire          cfg_we,
    input  wire [5:0]    cfg_addr,
    input  wire [31:0]   cfg_data,
    // IDX descriptor (sampled with go, the same bus as the IDX engine)
    input  wire          go,
    input  wire [4:0]    n_rows,
    input  wire [3:0]    k,
    input  wire [17:0]   d_base,
    input  wire [17:0]   r_base,
    // passive tap of the IDX packet-write bus (ot_hnx_idx_union_static.cq) + its completion
    input  wire [337:0]  cq,
    input  wire          union_v,
    input  wire [9:0]    union_count,
    input  wire          union_fault,
    output reg           ready,
    output reg           busy,
    output reg           fault,
    output reg           done,
    output reg           launch_v,
    output reg  [1:0]    launch_loop,      // 1 loop 1, 2 loop 2, 3 tail
    output reg  [6:0]    launch_slot,
    output reg  [4:0]    launch_c,
    output reg  [11:0]   launch_kref
);
    // ---------------------------------------------------------------- configuration (flops: 2 x 16 x 24 b + 5 x 32 b)
    reg [23:0] d1 [0:15];
    reg [23:0] d2 [0:15];
    reg [31:0] b1_q, g_q;
    reg [11:0] kb1_q, kb2_q, kbt_q;
    reg cfg_bad;
    reg tap_on;
    always @(posedge clk) if (cfg_we && !busy && !tap_on) begin
        if (cfg_addr < 6'd16) d1[cfg_addr[3:0]] <= cfg_data[23:0];
        else if (cfg_addr < 6'd32) d2[cfg_addr[3:0]] <= cfg_data[23:0];
        else case (cfg_addr)
            6'd32: b1_q <= cfg_data;
            6'd33: g_q <= cfg_data;
            6'd34: kb1_q <= cfg_data[11:0];
            6'd35: kb2_q <= cfg_data[11:0];
            6'd36: kbt_q <= cfg_data[11:0];
            default: ;
        endcase
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) cfg_bad <= 1'b0;
        else if (cfg_we && !busy && !tap_on)
            cfg_bad <= cfg_bad | ((cfg_addr < 6'd33) && cfg_data < 32'd4) | (cfg_addr < 6'd32 && cfg_data[31:24] != 8'd0);
    // ---------------------------------------------------------------- descriptor + tap pin registers
    reg [14:0] rsec_q, dsec_q; reg [7:0] tslots_q; reg [4:0] n_q;
    reg t0_v, t0_d, t0_m; reg [14:0] t0_off; reg [4:0] t0_c; reg t0_cbad;
    wire        cq_v    = cq[337];
    wire [14:0] cq_sec  = cq[323:309];
    wire [31:0] cq_w0   = cq[79:48];
    wire [3:0]  cq_m0   = cq[19:16];
    wire [14:0] off     = cq_sec - rsec_q;
    wire in_tab = tap_on && cq_v && off[1:0] == 2'd0 && off[14:2] < {5'd0, tslots_q};
    // ---------------------------------------------------------------- prefix pipeline
    reg [6:0] nslot;             // next expected table slot
    reg [6:0] ucnt;              // valid experts seen
    reg e1_v; reg [6:0] e1_slot; reg [4:0] e1_c; reg [23:0] e1_d1, e1_d2;
    reg [31:0] acc1, acc2;
    reg rdy_p0, rdy_p1;
    reg tfault;
    // one-hot select of D[c] (registered, static index)
    reg [15:0] oh;
    reg [23:0] sel1, sel2;
    integer q;
    wire [4:0] cmut = (MUT == 1 && t0_c > 5'd1) ? t0_c - 5'd1 : (MUT == 3) ? n_q : t0_c;
    wire [4:0] cidx = cmut - 5'd1;
    always @* begin
        oh = 16'd0; oh[cidx[3:0]] = 1'b1;
        sel1 = 24'd0; sel2 = 24'd0;
        for (q = 0; q < 16; q = q + 1) begin
            sel1 = sel1 | (oh[q] ? d1[q] : 24'd0);
            sel2 = sel2 | (oh[q] ? d2[q] : 24'd0);
        end
    end
    // ---------------------------------------------------------------- metadata SRAM (1R1W, explicit port phases)
    reg         m_we; reg [9:0] m_waddr; reg [255:0] m_wd;
    reg         m_re; reg [9:0] m_raddr;
    wire [255:0] m_rd;
    ot_sram_1r1w_1024x256_m2_r2c2 u_meta (
        .clk(clk), .r_ce_in(m_re), .r_addr_in(m_raddr), .rd_out(m_rd),
        .w_ce_in(m_we), .w_addr_in(m_waddr), .wd_in(m_wd), .w_mask_in({{187{1'b0}}, {69{1'b1}}}),
        .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    reg [68:0] cap;
    always @(posedge clk) cap <= m_rd[68:0];      // capture rung beside the macro (its only load)
    // ---------------------------------------------------------------- dispatch state
    localparam [2:0] D_IDLE = 0, D_READ = 1, D_CAP = 2, D_FORM = 3, D_WAIT = 4, D_TAIL = 5;
    reg [2:0] dst;
    reg [1:0] loop_q;
    reg [6:0] di, u_q;
    reg [31:0] age, base2, t2_q, evt;
    reg [4:0] ev_c;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tap_on <= 1'b0; t0_v <= 1'b0; t0_d <= 1'b0; e1_v <= 1'b0; m_we <= 1'b0; m_re <= 1'b0;
            ready <= 1'b0; rdy_p0 <= 1'b0; rdy_p1 <= 1'b0; tfault <= 1'b0; nslot <= 7'd0; ucnt <= 7'd0;
            acc1 <= 32'd0; acc2 <= 32'd0; busy <= 1'b0; fault <= 1'b0; done <= 1'b0; launch_v <= 1'b0;
            dst <= D_IDLE; age <= 32'd0;
        end else begin
            fault <= 1'b0; done <= 1'b0; launch_v <= 1'b0; m_we <= 1'b0; m_re <= 1'b0;
            if (busy) age <= age + 32'd1;
            // -------- descriptor: a new union record arms the tap (never while dispatching: overrun faults)
            if (go) begin
                if (busy) begin busy <= 1'b0; fault <= 1'b1; dst <= D_IDLE; end
                tap_on <= 1'b1; ready <= 1'b0; tfault <= 1'b0; nslot <= 7'd0; ucnt <= 7'd0; acc1 <= 32'd0; acc2 <= 32'd0;
                rsec_q <= r_base[17:3]; dsec_q <= d_base[17:3]; tslots_q <= 8'(n_rows) * 8'(k); n_q <= n_rows;
            end
            // -------- E0: pin capture of the tap fields
            t0_v <= in_tab; t0_d <= tap_on && cq_v && cq_sec == dsec_q;
            t0_off <= off; t0_c <= cq_w0[4:0]; t0_m <= cq_m0 == 4'hf;
            t0_cbad <= cq_m0 == 4'hf && (cq_w0 == 32'd0 || cq_w0 > 32'(n_q)) || (cq_m0 != 4'hf && cq_m0 != 4'h0);
            // -------- E1: slot order check + registered one-hot duration select (only valid word-0 slots are experts)
            e1_v <= 1'b0;
            if (t0_v) begin
                if (t0_off[8:2] != nslot || t0_cbad) tfault <= 1'b1;
                nslot <= nslot + 7'd1;
                if (t0_m && !t0_cbad) begin
                    e1_v <= 1'b1; e1_slot <= t0_off[8:2]; e1_c <= cmut; e1_d1 <= sel1; e1_d2 <= sel2;
                end
            end
            // -------- E2: accumulate + one masked metadata write (write port, tap phase only)
            if (e1_v) begin
                if (e1_slot != ucnt) tfault <= 1'b1;       // valid experts are the leading U slots
                ucnt <= ucnt + 7'd1;
                m_we <= 1'b1; m_waddr <= {3'd0, e1_slot};
                m_wd <= {187'd0, e1_c, (MUT == 2) ? acc2 + 32'(e1_d2) : acc2, (MUT == 2) ? acc1 + 32'(e1_d1) : acc1};
                acc1 <= acc1 + 32'(e1_d1); acc2 <= acc2 + 32'(e1_d2);
            end
            rdy_p0 <= t0_d; rdy_p1 <= rdy_p0;
            if (rdy_p1) begin ready <= 1'b1; tap_on <= 1'b0; end
            // -------- IDX record ended in fault: discard, no launch
            if (union_fault) begin ready <= 1'b0; tap_on <= 1'b0; end
            // -------- dispatch
            case (dst)
                D_IDLE: if (union_v) begin
                    if (!ready || tfault || cfg_bad || union_count != {3'd0, ucnt} || ucnt == 7'd0) fault <= 1'b1;
                    else begin
                        busy <= 1'b1; age <= 32'd1; u_q <= ucnt; di <= 7'd0; loop_q <= 2'd1;
                        base2 <= b1_q + acc1 + g_q; t2_q <= acc2; ready <= 1'b0;
                        m_re <= 1'b1; m_raddr <= 10'd0; dst <= D_READ;
                    end
                end
                D_READ: dst <= D_CAP;                                 // macro reads on this edge (r_ce registered at the previous)
                D_CAP: dst <= D_FORM;                                 // capture rung samples rd_out on this edge
                D_FORM: begin                                         // event time from the captured word
                    ev_c <= cap[68:64];
                    evt <= (loop_q == 2'd1) ? b1_q + cap[31:0] : base2 + cap[63:32];
                    dst <= D_WAIT;
                end
                D_WAIT: if (evt < age) begin busy <= 1'b0; fault <= 1'b1; dst <= D_IDLE; end   // late: fail, never stall
                else if (evt == age) begin
                    launch_v <= 1'b1; launch_loop <= loop_q; launch_slot <= di; launch_c <= ev_c;
                    launch_kref <= ((loop_q == 2'd1) ? kb1_q : kb2_q) + 12'(ev_c) - 12'd1;
                    if (di + 7'd1 == u_q) begin
                        di <= 7'd0;
                        if (loop_q == 2'd1) begin loop_q <= 2'd2; m_re <= 1'b1; m_raddr <= 10'd0; dst <= D_READ; end
                        else begin evt <= base2 + t2_q; dst <= D_TAIL; end
                    end else begin
                        di <= di + 7'd1; m_re <= 1'b1; m_raddr <= {3'd0, di + 7'd1}; dst <= D_READ;
                    end
                end
                D_TAIL: if (evt < age) begin busy <= 1'b0; fault <= 1'b1; dst <= D_IDLE; end
                else if (evt == age) begin
                    launch_v <= 1'b1; launch_loop <= 2'd3; launch_slot <= u_q; launch_c <= 5'd0; launch_kref <= kbt_q;
                    busy <= 1'b0; done <= 1'b1; dst <= D_IDLE;
                end
                default: begin dst <= D_IDLE; busy <= 1'b0; fault <= 1'b1; end
            endcase
        end
    end
endmodule
`default_nettype wire
