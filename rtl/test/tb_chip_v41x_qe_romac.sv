`timescale 1ns/1ps
// Exactness of the hardened QE ROM/MAC neighborhood (ot_chip_v41x_qe_romac, RL = 3,
// captures beside 16 ot_rom_8192x274_m8 behavioural macros, activation SRAMs) against the
// reference composition: the routed qtile (ot_hdc_v41x_wgt_qtile, RL = 2) fed by the
// source-pinned ot_chip_v41x_qtile_pair_bank over an ideal bank array holding the same
// checkpoint images.  Same descriptors, same activations; every result
// {rg, tag, mask, y, bf, f} must match in order.  The DUT runs the ops back to back
// (mixed FP8 / FP4 in flight); the reference drains between formats (its pair bank
// takes one format for all lanes).
module tb_chip_v41x_qe_romac;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    string dir;
    localparam integer NOPS = 3;
    // op table: {fp4, nrows, tag}
    reg        op_fp4   [0:NOPS-1];
    reg [15:0] op_nrows [0:NOPS-1];
    reg [3:0]  op_tag   [0:NOPS-1];
    initial begin
        op_fp4[0] = 0; op_nrows[0] = 320; op_tag[0] = 4'd1;   // wq_a, FP8
        op_fp4[1] = 1; op_nrows[1] = 576; op_tag[1] = 4'd2;   // exp110.w1, paired FP4
        op_fp4[2] = 0; op_nrows[2] = 320; op_tag[2] = 4'd3;   // wq_a again, behind an FP4 op
    end
    reg [273:0] mem [0:16*8192-1];
    reg [263:0] xw [0:8*20-1];         // activation word of position c, beat q at c*20+q

    // ------------------------------------------------------------------ DUT
    reg          s_d_v = 0;
    wire         s_d_rdy;
    reg          s_d_fp4 = 0;
    reg  [15:0]  s_d_nrows = 0;
    reg  [3:0]   s_d_tag = 0;
    reg          s_o_cr = 0;
    reg          s_x_we = 0;
    reg  [2:0]   s_x_pos = 0;
    reg  [5:0]   s_x_addr = 0;
    reg  [263:0] s_x_data = 0;
    wire r_v, r_mask, r_f, f_conflict, f_address, f_reserved, idle;
    wire [15:0] r_rg, r_bf;
    wire [3:0]  r_tag;
    wire [31:0] r_y;
    ot_chip_v41x_qe_romac #(.NP(2)) dut (
        .clk(clk), .rst_n(rst_n), .s_d_v(s_d_v), .s_d_rdy(s_d_rdy), .s_d_plg(4'd0), .s_d_nb(10'd160),
        .s_d_nrows(s_d_nrows), .s_d_wbase(20'd0), .s_d_ind(1'b0), .s_d_eid(9'd0), .s_d_estride(20'd0),
        .s_d_fp4(s_d_fp4), .s_d_tag(s_d_tag), .s_o_cr(s_o_cr),
        .s_x_we(s_x_we), .s_x_pos(s_x_pos), .s_x_addr(s_x_addr), .s_x_data(s_x_data),
        .r_v(r_v), .r_rg(r_rg), .r_tag(r_tag), .r_mask(r_mask), .r_y(r_y), .r_bf(r_bf), .r_f(r_f),
        .f_conflict(f_conflict), .f_address(f_address), .f_reserved(f_reserved), .idle(idle));
    always @(posedge clk) s_o_cr <= r_v;

    // ------------------------------------------------------------------ reference
    reg          q_d_v = 0;
    wire         q_d_rdy;
    reg          q_fp4 = 0;
    reg  [15:0]  q_nrows = 0;
    reg  [3:0]   q_tag = 0;
    reg          q_o_cr = 0;
    wire [7:0]   q_rq_v;
    wire [8*20-1:0] q_rq_a;
    wire [8*10-1:0] q_rq_q;
    wire [8*264-1:0] q_rd_w;
    reg  [8*264-1:0] q_x1, q_rd_x;
    wire q_o_v, q_o_mask, q_o_f, q_idle;
    wire [15:0] q_o_rg, q_o_bf;
    wire [3:0]  q_o_tag;
    wire [31:0] q_o_y;
    ot_hdc_v41x_wgt_qtile u_ref (
        .clk(clk), .rst_n(rst_n), .d_v(q_d_v), .d_rdy(q_d_rdy), .d_plg(4'd0), .d_nb(10'd160), .d_nrows(q_nrows),
        .d_wbase(20'd0), .d_ind(1'b0), .d_eid(9'd0), .d_estride(20'd0), .d_fp4(q_fp4), .d_tag(q_tag),
        .rq_v(q_rq_v), .rq_a(q_rq_a), .rq_q(q_rq_q), .rq_plg(), .rq_tag(), .rd_w(q_rd_w), .rd_x(q_rd_x),
        .o_cr(q_o_cr), .o_v(q_o_v), .o_rg(q_o_rg), .o_tag(q_o_tag), .o_mask(q_o_mask), .o_y(q_o_y),
        .o_bf(q_o_bf), .o_f(q_o_f), .idle(q_idle));
    always @(posedge clk) q_o_cr <= q_o_v;
    wire [15:0] bank_re;
    wire [16*13-1:0] bank_addr;
    reg  [16*274-1:0] bank_q = 0;
    wire [7:0] pb_v;
    wire pb_conflict, pb_address, pb_reserved;
    ot_chip_v41x_qtile_pair_bank u_pb (
        .clk(clk), .rst_n(rst_n), .fp4(q_fp4), .req_v(q_rq_v), .req_beat(q_rq_a), .bank_re(bank_re),
        .bank_addr(bank_addr), .bank_q(bank_q), .rd_v(pb_v), .rd_w(q_rd_w), .conflict(pb_conflict),
        .address_fault(pb_address), .reserved_fault(pb_reserved));
    integer bi;
    always @(posedge clk)
        for (bi = 0; bi < 16; bi = bi + 1)
            if (bank_re[bi]) bank_q[bi*274 +: 274] <= mem[bi*8192 + bank_addr[bi*13 +: 13]];
    integer ci;
    always @(posedge clk)
        for (ci = 0; ci < 8; ci = ci + 1) begin
            if (q_rq_v[ci]) q_x1[ci*264 +: 264] <= xw[ci*20 + q_rq_q[ci*10 +: 10]];
            q_rd_x[ci*264 +: 264] <= q_x1[ci*264 +: 264];
        end

    // ------------------------------------------------------------------ result logs
    localparam integer EW = 16 + 4 + 1 + 32 + 16 + 1;
    reg [EW-1:0] dlog [0:4095];
    reg [EW-1:0] rlog [0:4095];
    integer nd = 0, nr = 0;
    integer d_first [0:NOPS-1];
    integer r_first [0:NOPS-1];
    integer d_acc [0:NOPS-1];
    integer r_acc [0:NOPS-1];
    integer d_last = 0, r_last = 0;
    always @(posedge clk) if (rst_n && r_v) begin
        dlog[nd] <= {r_rg, r_tag, r_mask, r_y, r_bf, r_f}; nd <= nd + 1; d_last <= cyc;
        if (r_rg == 0 && d_first[r_tag - 1] < 0) d_first[r_tag - 1] <= cyc;
    end
    always @(posedge clk) if (rst_n && q_o_v) begin
        rlog[nr] <= {q_o_rg, q_o_tag, q_o_mask, q_o_y, q_o_bf, q_o_f}; nr <= nr + 1; r_last <= cyc;
        if (q_o_rg == 0 && r_first[q_o_tag - 1] < 0) r_first[q_o_tag - 1] <= cyc;
    end
    integer mref_conf = 0;
    always @(posedge clk) if (rst_n && (pb_conflict || pb_address || pb_reserved)) mref_conf = mref_conf + 1;

    integer i, k, errors = 0, total_rows = 0, nfault = 0;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "DIR required");
        for (i = 0; i < NOPS; i = i + 1) begin d_first[i] = -1; r_first[i] = -1; end
        $readmemh($sformatf("%s/banks.hex", dir), mem);
        $readmemh($sformatf("%s/act.hex", dir), xw);
        #1;
        $readmemh($sformatf("%s/via00.hex", dir), dut.g_rom[0].u_rom.arr);
        $readmemh($sformatf("%s/via01.hex", dir), dut.g_rom[1].u_rom.arr);
        $readmemh($sformatf("%s/via02.hex", dir), dut.g_rom[2].u_rom.arr);
        $readmemh($sformatf("%s/via03.hex", dir), dut.g_rom[3].u_rom.arr);
        $readmemh($sformatf("%s/via04.hex", dir), dut.g_rom[4].u_rom.arr);
        $readmemh($sformatf("%s/via05.hex", dir), dut.g_rom[5].u_rom.arr);
        $readmemh($sformatf("%s/via06.hex", dir), dut.g_rom[6].u_rom.arr);
        $readmemh($sformatf("%s/via07.hex", dir), dut.g_rom[7].u_rom.arr);
        $readmemh($sformatf("%s/via08.hex", dir), dut.g_rom[8].u_rom.arr);
        $readmemh($sformatf("%s/via09.hex", dir), dut.g_rom[9].u_rom.arr);
        $readmemh($sformatf("%s/via10.hex", dir), dut.g_rom[10].u_rom.arr);
        $readmemh($sformatf("%s/via11.hex", dir), dut.g_rom[11].u_rom.arr);
        $readmemh($sformatf("%s/via12.hex", dir), dut.g_rom[12].u_rom.arr);
        $readmemh($sformatf("%s/via13.hex", dir), dut.g_rom[13].u_rom.arr);
        $readmemh($sformatf("%s/via14.hex", dir), dut.g_rom[14].u_rom.arr);
        $readmemh($sformatf("%s/via15.hex", dir), dut.g_rom[15].u_rom.arr);
        repeat (4) @(negedge clk);
        rst_n = 1;
        repeat (4) @(negedge clk);
        // activations into the DUT's SRAMs through the spine edge
        for (i = 0; i < 160; i = i + 1) begin
            s_x_we = 1; s_x_pos = 3'(i / 20); s_x_addr = 6'(i % 20); s_x_data = xw[i];
            @(negedge clk);
        end
        s_x_we = 0;
        repeat (4) @(negedge clk);
        fork
            begin : drive_dut
                for (k = 0; k < NOPS; k = k + 1) begin
                    s_d_v = 1; s_d_fp4 = op_fp4[k]; s_d_nrows = op_nrows[k]; s_d_tag = op_tag[k];
                    @(posedge clk);
                    while (!s_d_rdy) @(posedge clk);
                    d_acc[k] = cyc;
                    @(negedge clk);
                    s_d_v = 0;
                end
            end
            begin : drive_ref
                integer j;
                for (j = 0; j < NOPS; j = j + 1) begin
                    if (j > 0 && op_fp4[j] != op_fp4[j-1]) begin
                        @(negedge clk);
                        while (!q_idle) @(negedge clk);
                        repeat (40) @(negedge clk);   // idle can precede the last beats' read pipe
                    end
                    q_d_v = 1; q_fp4 = op_fp4[j]; q_nrows = op_nrows[j]; q_tag = op_tag[j];
                    @(posedge clk);
                    while (!q_d_rdy) @(posedge clk);
                    r_acc[j] = cyc;
                    @(negedge clk);
                    q_d_v = 0;
                end
            end
        join
        for (k = 0; k < NOPS; k = k + 1) total_rows = total_rows + op_nrows[k];
        while ((nd < total_rows || nr < total_rows) && cyc < 400000) @(negedge clk);
        repeat (50) @(negedge clk);
        if (nd != total_rows || nr != total_rows) $fatal(1, "row count dut=%0d ref=%0d want=%0d", nd, nr, total_rows);
        for (i = 0; i < total_rows; i = i + 1) begin
            if (dlog[i] !== rlog[i]) begin
                errors = errors + 1;
                if (errors < 5) $display("MISMATCH row %0d dut=%h ref=%h", i, dlog[i], rlog[i]);
            end
            if (dlog[i][0]) nfault = nfault + 1;
        end
        if (f_conflict || f_address || f_reserved) $fatal(1, "DUT fault conflict=%0d address=%0d reserved=%0d",
                                                          f_conflict, f_address, f_reserved);
        if (mref_conf) $fatal(1, "reference pair bank fault");
        if (errors) $fatal(1, "errors=%0d", errors);
        $display("QE_ROMAC_PASS rows=%0d faults=%0d", total_rows, nfault);
        for (k = 0; k < NOPS; k = k + 1)
            $display("QE_ROMAC_LAT op=%0d fp4=%0d dut_accept=%0d dut_first=%0d ref_accept=%0d ref_first=%0d",
                     k, op_fp4[k], d_acc[k], d_first[k], r_acc[k], r_first[k]);
        $display("QE_ROMAC_END dut_last=%0d ref_last=%0d", d_last, r_last);
        $finish;
    end
endmodule
