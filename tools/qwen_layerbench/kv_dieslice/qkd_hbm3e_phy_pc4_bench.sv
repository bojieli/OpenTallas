`timescale 1ns/1ps
// KV-P7 10-23: BENCH MODEL of one 4-PC HBM3E PHY slice (the off-chip boundary; owner rule 10-14: only PHY / off-chip
// signals are modelled).  Same ports as the as-built port model qkd_hbm3e_phy_pc4 (bind/models/kv_phy_slices.sv), so a
// bench compiles it INSTEAD of the black box (Verilator: list this file, do not list kv_phy_slices.sv).
// Command word po<k> (qkd_ctrl_pc_host_static_core po_r, fixed RL calendar, ELASTIC 0):
//   [0] row_v  [3:1] row_op (1 = ACT)  [8:4] row_bank  [27:9] row_row  [28] col_v  [29] col_we  [34:30] col_bank
//   [39:35] col_col  [327:40] wd (288 b = 4 x SECDED(72,64) of the 256-b sector, encoded by ot_qfd_emb_pcport)
// Read return pi<k> = {data 288, valid 1} exactly RL hck edges after the RD column (RL 23 = the compiled calendar; the
// same law as rtl/test/mu_qwen_1018/tb_mu_kv_pc_path_rows.sv's PHY model).  A WR column stores the wd that the
// controller drives WL hck edges after it (KV-TOK B 10-24: WL 5 = the as-built write latency on po: column at po edge t,
// sched dv[1] t+1 -> port child pin t+2 -> ot_qfd_emb_pcport_nkw st1_wd t+3 / s2_wd t+4 -> po t+5; the same alignment
// the controller's own write observer checks (qkd_static_kv_write_observer valid[4]); the model previously stored the
// po wd of the column edge itself, i.e. stale data) at (bank, open row, col); a RD column returns the stored word (or,
// if never written, the PRELOAD image, else ECC(0)).
// Preload (history KV rows, layout CONTRACT map v2 + MU row bits): the bench calls preload(pc, bank, row, col, word288)
// by hierarchy, or +HBM_PRELOAD=<file> with lines "<slice> <pc> <bank> <row> <col> <288-b hex>" (slice = PRELOAD_ID).
// fh/rh = the PHY's forwarded front/return HBM clocks (4 per slice) = hck.  Write/read counters for the bench report.
module qkd_hbm3e_phy_pc4 #(parameter integer RL = 23, parameter integer PRELOAD_ID = -1, parameter integer WL = 5) (
    input  wire         clk,
    input  wire         rst_n,
    output reg  [288:0] pi0, output reg  [288:0] pi1, output reg  [288:0] pi2, output reg  [288:0] pi3,
    input  wire [327:0] po0, input  wire [327:0] po1, input  wire [327:0] po2, input  wire [327:0] po3,
    output wire [3:0]   fh0, output wire [3:0]   fh1, output wire [3:0]   fh2, output wire [3:0]   fh3,
    output wire [3:0]   rh0, output wire [3:0]   rh1, output wire [3:0]   rh2, output wire [3:0]   rh3
);
    assign fh0 = {4{clk}}; assign fh1 = {4{clk}}; assign fh2 = {4{clk}}; assign fh3 = {4{clk}};
    assign rh0 = {4{clk}}; assign rh1 = {4{clk}}; assign rh2 = {4{clk}}; assign rh3 = {4{clk}};
    function automatic [71:0] ecc(input [63:0] d);
        reg [71:0] c; integer j; begin c = 0; j = 0;
        for (integer p = 1; p <= 71; p++) if ((p & (p - 1)) != 0) begin c[p-1] = d[j]; j++; end
        for (integer k = 0; k < 7; k++) for (integer p = 1; p <= 71; p++) if ((p & (1 << k)) != 0) c[(1<<k)-1] ^= c[p-1];
        c[71] = ^c[70:0]; ecc = c; end
    endfunction
    function automatic [287:0] encode(input [255:0] d);
        for (integer j = 0; j < 4; j++) encode[j*72 +: 72] = ecc(d[j*64 +: 64]);
    endfunction
    // storage: key = {pc 2, bank 5, row 19, col 5}
    reg [287:0] mem [bit [30:0]];
    integer openrow [0:3][0:31];
    longint unsigned edge_n = 0, n_rd = 0, n_wr = 0, n_rd_unwritten = 0;
    reg [288:0] due [0:3][0:63];          // RL ring (RL < 64)
    reg [31:0]  wdue [0:3][0:63];         // WL ring: {valid, key} of the WR column whose data lands on that edge
    task automatic preload(input integer pc, input integer bank, input integer row, input integer col, input [287:0] w);
        mem[{2'(pc), 5'(bank), 19'(row), 5'(col)}] = w;
    endtask
    task automatic preload_plain(input integer pc, input integer bank, input integer row, input integer col, input [255:0] d);
        preload(pc, bank, row, col, encode(d));
    endtask
    // KV-TOK 10-24: the instance names its own slice by its bound partition (phy_<S>_<j>, from %m), so no defparam is
    // needed: +HBM_PRELOAD=<file> lines "<partition> <pc> <bank> <row> <col> <256-b plain sector hex>" (SECDED-encoded
    // on load, as the write path's ot_qfd_emb_pcport does); PRELOAD_ID >= 0 keeps the numeric form (288-b words).
    // +HBM_LOG=<n>: print the first n RD / WR columns of this slice (pc bank row col edge) -- the address-map self-check.
    string part = "";
    integer hlog = 0, nlog = 0;
    initial begin : pl
        string f, m, ps; integer fd, s, pc, b, r, c, n; reg [287:0] w; reg [255:0] d;
        for (int k = 0; k < 4; k++) for (int j = 0; j < 64; j++) begin due[k][j] = '0; wdue[k][j] = '0; end
        m = $sformatf("%m");
        for (int i = 0; i + 4 <= m.len(); i++) if (m.substr(i, i + 3) == "phy_") begin
            int e; e = i; while (e < m.len() && m[e] != ".") e++; part = m.substr(i, e - 1); break; end
        void'($value$plusargs("HBM_LOG=%d", hlog));
        if ($value$plusargs("HBM_PRELOAD=%s", f)) begin
            fd = $fopen(f, "r"); n = 0;
            if (fd == 0) $fatal(1, "HBM_PRELOAD %s not readable", f);
            if (PRELOAD_ID >= 0) begin
                while ($fscanf(fd, "%d %d %d %d %d %h\n", s, pc, b, r, c, w) == 6)
                    if (s == PRELOAD_ID) begin preload(pc, b, r, c, w); n++; end
            end else begin
                while ($fscanf(fd, "%s %d %d %d %d %h\n", ps, pc, b, r, c, d) == 6)
                    if (ps == part) begin preload(pc, b, r, c, encode(d)); n++; end
            end
            $fclose(fd);
            if (n > 0) $display("HBM_PRELOAD %s words %0d", part, n);
        end
    end
    wire [327:0] po [0:3];
    assign po[0] = po0; assign po[1] = po1; assign po[2] = po2; assign po[3] = po3;
    reg [3:0] po_seen = 0;
    always @(posedge clk) begin
        edge_n <= edge_n + 1;
        for (int k = 0; k < 4; k++) if (!po_seen[k] && po[k] != 328'd0) begin
            po_seen[k] <= 1'b1;
            if (hlog > 0) $display("HBM_PO_FIRST %s pc %0d edge %0d row_v %0d op %0d col_v %0d we %0d", part, k, edge_n, po[k][0],
                                   po[k][3:1], po[k][28], po[k][29]);
        end
        for (int k = 0; k < 4; k++) begin
            if (wdue[k][edge_n % 64][31]) begin mem[wdue[k][edge_n % 64][30:0]] = po[k][327:40]; wdue[k][edge_n % 64] = '0; end
            if (po[k][0] && po[k][3:1] == 3'd1) openrow[k][po[k][8:4]] = po[k][27:9];
            if (po[k][28]) begin : col
                automatic bit [30:0] key = {2'(k), po[k][34:30], 19'(openrow[k][po[k][34:30]]), po[k][39:35]};
                if (nlog < hlog) begin
                    nlog++;
                    $display("HBM_%s %s pc %0d bank %0d row %0d col %0d edge %0d", po[k][29] ? "WR" : "RD", part, k, po[k][34:30],
                             openrow[k][po[k][34:30]], po[k][39:35], edge_n);
                end
                if (po[k][29]) begin wdue[k][(edge_n + WL) % 64] = {1'b1, key}; n_wr++; end
                else begin
                    n_rd++;
                    if (!mem.exists(key)) begin n_rd_unwritten++; due[k][(edge_n + RL) % 64] = {encode(256'd0), 1'b1}; end
                    else due[k][(edge_n + RL) % 64] = {mem[key], 1'b1};
                end
            end
        end
    end
    always @(negedge clk) begin   // drive the slot whose edge comes next (as the reference PHY model)
        pi0 <= due[0][(edge_n) % 64]; due[0][(edge_n) % 64] <= '0;
        pi1 <= due[1][(edge_n) % 64]; due[1][(edge_n) % 64] <= '0;
        pi2 <= due[2][(edge_n) % 64]; due[2][(edge_n) % 64] <= '0;
        pi3 <= due[3][(edge_n) % 64]; due[3][(edge_n) % 64] <= '0;
    end
    final $display("HBM_PHY %s reads %0d writes %0d unwritten_reads %0d", part, n_rd, n_wr, n_rd_unwritten);
endmodule
