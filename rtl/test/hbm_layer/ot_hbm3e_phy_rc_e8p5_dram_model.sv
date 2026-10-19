`timescale 1ps/1fs
// LAYERBENCH-HBM (10-18): OFF-CHIP MODEL of the HBM3E PHY + DRAM stack behind one d4g quadrant controller set
// (32 pseudo-channels).  Replaces the (* blackbox *) macro abstract
// physical/asap7_memory_macros/ot_hbm3e_phy_rc_e8p5/ot_hbm3e_phy_rc_e8p5_bb.v (same module name and port list) in the
// slice bench ONLY: the PHY and the DRAM are the off-chip edge of the die, every controller in front of it is the
// die's real RTL.  Command timing checks + read latency (23 HBM edges = CL 12.5 ns + burst 1.024 ns + return 10 ns)
// and the sector map are those of the native-command fixture of record
// rtl/hbm_accel/loader/service_native/tb_hbm_svc_command_dram_pipeline_fixture.sv; the storage is a sparse
// associative array over the whole 30-bit sector space (the fixture's bounded K window is a unit-bench limit).
// Preload: +HBM_IMG_DIR=<dir> reads <dir>/<instance leaf name>.hex if present, lines "<sector hex> <256-b data hex>"
// (the compiler's d4g address -> PC placement map writes them).  Unwritten sectors read 0.
// Final report: HBM_MODEL <inst> reads=<n> writes=<n> refreshes=<n> first_cmd=<cyc> last_cmd=<cyc>.
module ot_hbm3e_phy_rc_e8p5 (
    input wire clk,
    input wire rst_n,
    input wire [31:0] row_v,
    input wire [95:0] row_op,
    input wire [159:0] row_bank,
    input wire [607:0] row_row,
    input wire [31:0] col_v,
    input wire [31:0] col_we,
    input wire [159:0] col_bank,
    input wire [159:0] col_col,
    input wire [8191:0] col_data,
    input wire [1023:0] col_strb,
    output reg [31:0] dram_rvalid = 0,
    output reg [8191:0] dram_rdata = 0
);
    reg [255:0] mem [bit [29:0]];
    reg opened [0:31][0:31];
    integer current_row [0:31][0:31];
    integer act_at [0:31][0:31], pre_at [0:31][0:31], refresh_until [0:31][0:31], write_at [0:31][0:31], read_at [0:31][0:31];
    integer last_act [0:31], last_act_bg [0:31][0:3], last_col_bg [0:31][0:3], last_rd [0:31], last_wr [0:31];
    integer faw [0:31][0:3], ref_at [0:31];
    integer writes = 0, reads = 0, refreshes = 0, cyc = 0, first_cmd = -1, last_cmd = -1;
    reg [22:0] due_v [0:31];
    reg [255:0] due_data [0:31][0:22];
    string leaf;
    function automatic [29:0] sector(input integer pc, bank, row, col);
        reg [29:0] s;
        begin
            s = 30'(row) << 15; s[11:7] = 5'(col); s[14:12] = 3'(bank >> 2) ^ 3'(row >> 2); s[1:0] = 2'(bank) ^ 2'(row);
            s[6:2] = 5'(pc) ^ s[11:7] ^ s[16:12]; sector = s;
        end
    endfunction
    initial begin : INIT
        string dir, path, full;
        integer fd, n, k;
        reg [29:0] sa;
        reg [255:0] dv;
        for (integer p = 0; p < 32; p = p + 1) begin
            due_v[p] = 0; for (integer d = 0; d < 23; d = d + 1) due_data[p][d] = 0;
            last_act[p] = -1000; last_rd[p] = -1000; last_wr[p] = -1000; ref_at[p] = -1000;
            for (integer b = 0; b < 32; b = b + 1) begin
                opened[p][b] = 0; current_row[p][b] = 0; act_at[p][b] = -1000; pre_at[p][b] = -1000;
                refresh_until[p][b] = -1000; write_at[p][b] = -1000; read_at[p][b] = -1000;
            end
            for (integer g = 0; g < 4; g = g + 1) begin last_act_bg[p][g] = -1000; last_col_bg[p][g] = -1000; faw[p][g] = -1000; end
        end
        full = $sformatf("%m");
        leaf = full;
        for (k = full.len() - 1; k >= 0; k = k - 1) if (full[k] == ".") begin leaf = full.substr(k + 1, full.len() - 1); break; end
        if ($value$plusargs("HBM_IMG_DIR=%s", dir)) begin
            path = {dir, "/", leaf, ".hex"};
            fd = $fopen(path, "r");
            n = 0;
            if (fd != 0) begin
                while ($fscanf(fd, "%h %h\n", sa, dv) == 2) begin mem[sa] = dv; n = n + 1; end
                $fclose(fd);
            end
            $display("HBM_MODEL_PRELOAD %s sectors=%0d file=%s", leaf, n, path);
        end
    end
    always @(posedge clk) begin : COMMANDS
        integer b, kind, bg;
        reg [29:0] s;
        cyc = cyc + 1; dram_rvalid <= 0;
        if (rst_n) for (integer p = 0; p < 32; p = p + 1) begin
            due_v[p] <= {due_v[p][21:0], col_v[p] && !col_we[p]};
            for (integer d = 1; d < 23; d = d + 1) due_data[p][d] <= due_data[p][d - 1];
            if (due_v[p][22]) begin dram_rvalid[p] <= 1; dram_rdata[p * 256 +: 256] <= due_data[p][22]; end
            if (row_v[p] || col_v[p]) begin if (first_cmd < 0) first_cmd = cyc; last_cmd = cyc; end
            if (row_v[p]) begin
                b = row_bank[p * 5 +: 5]; bg = b & 3; kind = row_op[p * 3 +: 3];
                if (kind == 1) begin
                    if (opened[p][b] || cyc - pre_at[p][b] < 16 || cyc < refresh_until[p][b] || cyc - last_act[p] < 3 ||
                        cyc - last_act_bg[p][bg] < 4 || cyc - faw[p][0] < 15 || cyc - ref_at[p] < 8)
                        $fatal(1, "HBM_MODEL_FAIL %s illegal ACT p%0d b%0d cyc%0d", leaf, p, b, cyc);
                    opened[p][b] = 1; current_row[p][b] = row_row[p * 19 +: 19]; act_at[p][b] = cyc; last_act[p] = cyc;
                    last_act_bg[p][bg] = cyc;
                    for (integer g = 0; g < 3; g = g + 1) faw[p][g] = faw[p][g + 1]; faw[p][3] = cyc;
                end else if (kind == 0) begin
                    if (opened[p][b] && (cyc - act_at[p][b] < 28 || cyc - write_at[p][b] < 28 || cyc - read_at[p][b] < 6))
                        $fatal(1, "HBM_MODEL_FAIL %s early PRE p%0d b%0d", leaf, p, b);
                    opened[p][b] = 0; pre_at[p][b] = cyc;
                end else if (kind == 6) begin
                    if (opened[p][b] || cyc - pre_at[p][b] < 16 || cyc < refresh_until[p][b] || cyc - last_act[p] < 8 || cyc - ref_at[p] < 8)
                        $fatal(1, "HBM_MODEL_FAIL %s illegal REFpb p%0d b%0d", leaf, p, b);
                    refresh_until[p][b] = cyc + 196; refreshes = refreshes + 1; ref_at[p] = cyc;
                end else if (kind == 5) begin
                    for (integer bb = 0; bb < 32; bb = bb + 1) begin
                        if (opened[p][bb] && (cyc - act_at[p][bb] < 28 || cyc - write_at[p][bb] < 28 || cyc - read_at[p][bb] < 6))
                            $fatal(1, "HBM_MODEL_FAIL %s early PREab", leaf);
                        opened[p][bb] = 0; pre_at[p][bb] = cyc;
                    end
                end else $fatal(1, "HBM_MODEL_FAIL %s unsupported row op%0d", leaf, kind);
            end
            if (col_v[p]) begin
                b = col_bank[p * 5 +: 5]; bg = b & 3;
                if (!opened[p][b] || cyc - act_at[p][b] < (col_we[p] ? 10 : 19) || cyc < refresh_until[p][b] || cyc - last_col_bg[p][bg] < 3)
                    $fatal(1, "HBM_MODEL_FAIL %s column timing p%0d b%0d", leaf, p, b);
                if (col_we[p] && cyc - last_rd[p] < 10 || !col_we[p] && cyc - last_wr[p] < 14)
                    $fatal(1, "HBM_MODEL_FAIL %s RD/WR turnaround", leaf);
                s = sector(p, b, current_row[p][b], col_col[p * 5 +: 5]);
                last_col_bg[p][bg] = cyc;
                if (col_we[p]) begin
                    reg [255:0] w;
                    w = mem.exists(s) ? mem[s] : 256'd0;
                    for (integer by = 0; by < 32; by = by + 1) if (col_strb[p * 32 + by]) w[8 * by +: 8] = col_data[p * 256 + 8 * by +: 8];
                    mem[s] = w;
                    writes = writes + 1; write_at[p][b] = cyc; last_wr[p] = cyc;
                end else begin
                    due_data[p][0] <= mem.exists(s) ? mem[s] : 256'd0; reads = reads + 1; read_at[p][b] = cyc; last_rd[p] = cyc;
                end
            end
        end
    end
    final $display("HBM_MODEL %s reads=%0d writes=%0d refreshes=%0d first_cmd=%0d last_cmd=%0d", leaf, reads, writes,
                   refreshes, first_cmd, last_cmd);
endmodule
