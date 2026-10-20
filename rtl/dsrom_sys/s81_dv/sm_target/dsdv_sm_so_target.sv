`timescale 1ns/1ps
// Per-head SO receiver. See tools/s81_dv/sm_target/MODEL.md.
// S81-SMWIRE (10-19): instantiated inside every dsdv_svc_rs_c (16 on the die). HEAD < 0 (the die build) takes the head
// from the head strap pin (the slice's role tile, static from reset, captured in a pin flop); HEAD >= 0 keeps the
// original bench parameter. No END/destination acknowledgment is synthesized here: the booked retire joins the
// slice done (dsdv_svc_rs_c) and the fault joins the slice fault. Config authority is independent of the returned rows.
module dsdv_sm_so_target #(
    parameter integer HEAD = 0,
    parameter integer MUT = 0
) (
    input wire clk, rst_n,
    input wire [3:0] head,
    input wire cfg_v,
    input wire [19:0] cfg_owner,
    input wire [7:0] cfg_se_jid, cfg_so_jid,
    input wire [13:0] cfg_obase,
    input wire [15:0] cfg_first, cfg_last, cfg_read, cfg_retire,
    input wire op_st,
    input wire [3:0] op_kind,
    input wire [7:0] op_jid,
    input wire w_v,
    input wire [13:0] w_a,
    input wire [15:0] w_m,
    input wire [511:0] w_d,
    input wire [11:0] w_st,
    output reg g_v,
    output reg [6:0] g_idx,
    output reg [1023:0] g_d,
    output reg [19:0] g_owner,
    output reg g_group,
    output reg retired,
    output reg retire_error,
    output reg [19:0] retire_owner,
    output wire fault,
    output reg [11:0] fault_code
);
    reg [1:0] reset_landing;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) reset_landing <= 0;
        else reset_landing <= {reset_landing[0],1'b1};
    wire rn = reset_landing[1];
    reg [3:0] head_q;
    always @(posedge clk) head_q <= head;
    wire [3:0] hd = (HEAD >= 0) ? 4'(HEAD) : head_q;
    // All input pins land, including all unused bits of the returned row.
    reg cp_v, wp_v, op_v;
    reg [113:0] cp;
    reg [13:0] wp_a;
    reg [15:0] wp_m;
    reg [511:0] wp_d;
    reg [11:0] wp_st;
    reg [3:0] op_k;
    reg [7:0] op_j;
    always @(posedge clk) begin
        cp <= {cfg_owner,cfg_se_jid,cfg_so_jid,cfg_obase,
               cfg_first,cfg_last,cfg_read,cfg_retire};
        wp_a <= w_a; wp_m <= w_m; wp_d <= w_d; wp_st <= w_st;
        op_k <= op_kind; op_j <= op_jid;
    end
    always @(posedge clk or negedge rn)
        if (!rn) begin cp_v <= 0; wp_v <= 0; op_v <= 0; end
        else begin cp_v <= cfg_v; wp_v <= w_v; op_v <= op_st; end

    reg [19:0] owner;
    reg [7:0] se_jid, so_jid;
    reg [13:0] obase;
    reg [15:0] first_edge, last_edge, read_edge, retire_edge;
    reg active, den_seen;
    reg [1:0] phase; // 0 configured, 1 actual SE, 2 actual SO
    reg [15:0] cyc;
    reg [31:0] seen;
    reg [5:0] nw;
    reg reading;
    reg [4:0] ra;
    reg rd_v, rd_ok;
    reg [4:0] rd_row;
    reg [3:0] nb;
    reg [767:0] pack;

    wire [13:0] expected_a = obase + 14'(8*nw) + {11'd0, hd[3:1]};
    wire [15:0] expected_m = hd[0] ? 16'hff00 : 16'h00ff;
    wire [255:0] payload = hd[0] ? wp_d[511:256] : wp_d[255:0];
    reg [11:0] bad;
    always @* begin
        bad = 0;
        if (cp_v) begin
            if (active) bad[0] = 1;
            if (cp[63:48] > cp[47:32] ||
                {1'b0,cp[31:16]} <= {1'b0,cp[47:32]}+17'd1 ||
                {1'b0,cp[15:0]} <= {1'b0,cp[31:16]}+17'd34)
                bad[1] = 1;
        end
        if (op_v && active) begin
            if (op_k == 4'd4) begin
                if (phase != 0 || op_j != se_jid) bad[2] = 1;
            end else if (op_k == 4'd5) begin
                if (phase != 1 || op_j != so_jid || !den_seen) bad[3] = 1;
            end else bad[2] = 1;
        end
        if (wp_v) begin
            if (!active || phase == 0) bad[4] = 1;
            if (phase == 1) begin
                if (wp_m != 16'hffff || wp_st[11:4] != se_jid) bad[5] = 1;
            end else if (phase == 2) begin
                if (nw >= 32 || wp_a != expected_a) bad[6] = 1;
                if (wp_m != expected_m && MUT != 1) bad[7] = 1;
                if (wp_st[11:4] != so_jid || !wp_st[2] || |wp_st[1:0]) bad[8] = 1;
                if (cyc < first_edge || cyc > last_edge) bad[9] = 1;
                if (nw < 32 && seen[nw[4:0]]) bad[6] = 1;
            end
        end
        if (reading && !seen[ra] && MUT != 2) bad[10] = 1;
        if (active && cyc == read_edge && (nw != 32 || phase != 2)) bad[10] = 1;
        if (active && cyc == retire_edge && (nw != 32 || nb != 8 || reading || rd_v)) bad[11] = 1;
    end
    wire bad_now = |bad;
    assign fault = |fault_code;
    wire write_ok = wp_v && active && phase == 2 && !fault && !bad_now;
    wire rce = reading && active;
    wire [63:0] rq [0:3];
    genvar b;
    generate for (b=0;b<4;b=b+1) begin: g_bank
        ot_sram_1r1w_32x64_m1 u_mem (
            .clk(clk), .r_ce_in(rce), .r_addr_in(ra), .rd_out(rq[b]),
            .w_ce_in(write_ok), .w_addr_in(nw[4:0]),
            .wd_in(payload[64*b+:64]), .w_mask_in(64'hffffffffffffffff));
    end endgenerate
    wire [255:0] row_data = {rq[3],rq[2],rq[1],rq[0]};

    always @(posedge clk) begin
        if (cp_v && !active) begin
            {owner,se_jid,so_jid,obase,first_edge,last_edge,read_edge,retire_edge} <= cp;
        end
        // Three fixed assembly fields, not an indexed flop payload array.
        if (rd_v) begin
            case (rd_row[1:0])
                0: pack[255:0] <= row_data;
                1: pack[511:256] <= row_data;
                2: pack[767:512] <= row_data;
                default: ;
            endcase
        end
        // Unconditional output capture avoids a 1024-load output enable.
        g_d <= {row_data,pack};
        g_idx <= {1'b0, hd[2:0], rd_row[4:2]};
        g_owner <= owner; g_group <= hd[3];
        retire_owner <= owner;
    end
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            active <= 0; den_seen <= 0; phase <= 0; cyc <= 0;
            seen <= 0; nw <= 0; reading <= 0; ra <= 0;
            rd_v <= 0; rd_ok <= 0; rd_row <= 0; nb <= 0;
            g_v <= 0; retired <= 0; retire_error <= 0; fault_code <= 0;
        end else begin
            fault_code <= fault_code | bad;
            g_v <= rd_v && rd_row[1:0] == 3 && rd_ok && !fault && !bad_now;
            retired <= active && cyc == retire_edge;
            retire_error <= fault || bad_now;
            rd_v <= rce; rd_row <= ra; rd_ok <= rce && seen[ra] && !fault && !bad_now;
            if (active) cyc <= cyc + 1'b1;
            if (cp_v && !active) begin
                active <= 1; cyc <= 0; phase <= 0; den_seen <= 0;
                seen <= 0; nw <= 0; nb <= 0; reading <= 0; rd_v <= 0;
            end
            if (active && op_v && op_k == 4'd4 && phase == 0) begin phase <= 1; den_seen <= 0; end
            if (active && phase == 1 && wp_st[3] && wp_st[11:4] == se_jid) den_seen <= 1;
            if (active && op_v && op_k == 4'd5 && phase == 1) phase <= 2;
            if (write_ok) begin seen[nw[4:0]] <= 1; nw <= nw+1'b1; end
            if (active && cyc == read_edge) begin reading <= 1; ra <= 0; end
            else if (reading) begin
                ra <= ra+1'b1;
                if (ra == 31) reading <= 0;
            end
            if (rd_v && rd_row[1:0] == 3 && rd_ok && !fault && !bad_now) nb <= nb+1'b1;
            if (active && cyc == retire_edge) active <= 0;
        end
    end
endmodule
