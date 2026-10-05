`timescale 1ns/1ps
// Exactness of the hardened ME ROM/MAC neighborhood (ot_chip_v41x_me_romac: captures beside 8
// ot_rom_8192x274_m8 and 8 MP1 behavioural macros, combinational lane words into the ME lane P0)
// against the routed-parameter mtile fed by ideal RL = 2 bank arrays holding the same words.
module tb_chip_v41x_me_romac;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    string dir;
    localparam integer NOPS = 3;
    reg [3:0]  op_plg [0:NOPS-1];
    reg [13:0] op_nb [0:NOPS-1];
    reg [15:0] op_nrows [0:NOPS-1];
    reg [19:0] op_wbase [0:NOPS-1];
    reg [3:0]  op_tag [0:NOPS-1];
    initial begin
        op_plg[0] = 3; op_nb[0] = 512; op_nrows[0] = 64; op_wbase[0] = 0;    op_tag[0] = 1;
        op_plg[1] = 1; op_nb[1] = 64;  op_nrows[1] = 32; op_wbase[1] = 1024; op_tag[1] = 2;
        op_plg[2] = 2; op_nb[2] = 128; op_nrows[2] = 16; op_wbase[2] = 1536; op_tag[2] = 3;
    end
    reg [273:0] wmem [0:8*2048-1];     // chain position c, address a at c*2048 + a
    reg [127:0] xmem [0:8*128-1];      // chain position c, beat q at c*128 + q

    reg s_d_v = 0; wire s_d_rdy;
    reg [3:0] s_d_plg = 0, s_d_tag = 0; reg [13:0] s_d_nb = 0; reg [15:0] s_d_nrows = 0; reg [19:0] s_d_wbase = 0;
    reg s_o_cr = 0, s_x_we = 0; reg [2:0] s_x_pos = 0; reg [6:0] s_x_addr = 0; reg [127:0] s_x_data = 0;
    wire r_v, f_reserved, idle; wire [15:0] r_rg; wire [3:0] r_tag, r_mask, r_f; wire [127:0] r_y; wire [63:0] r_bf;
    ot_chip_v41x_me_romac #(.NP(2)) dut (
        .clk(clk), .rst_n(rst_n), .s_d_v(s_d_v), .s_d_rdy(s_d_rdy), .s_d_plg(s_d_plg), .s_d_nb(s_d_nb),
        .s_d_nrows(s_d_nrows), .s_d_wbase(s_d_wbase), .s_d_ind(1'b0), .s_d_eid(9'd0), .s_d_estride(20'd0),
        .s_d_tag(s_d_tag), .s_o_cr(s_o_cr), .s_x_we(s_x_we), .s_x_pos(s_x_pos), .s_x_addr(s_x_addr),
        .s_x_data(s_x_data), .r_v(r_v), .r_rg(r_rg), .r_tag(r_tag), .r_mask(r_mask), .r_y(r_y), .r_bf(r_bf),
        .r_f(r_f), .f_reserved(f_reserved), .idle(idle));
    always @(posedge clk) s_o_cr <= r_v;

    reg q_d_v = 0; wire q_d_rdy;
    reg [3:0] q_plg = 0, q_tag = 0; reg [13:0] q_nb = 0; reg [15:0] q_nrows = 0; reg [19:0] q_wbase = 0;
    reg q_o_cr = 0;
    wire [7:0] q_rq_v; wire [8*20-1:0] q_rq_a; wire [8*14-1:0] q_rq_q;
    reg [64*34-1:0] q_rd_w; reg [64*16-1:0] q_rd_x;
    reg [273:0] w1 [0:7]; reg [127:0] x1 [0:7];
    wire q_o_v, q_idle; wire [15:0] q_o_rg; wire [3:0] q_o_tag, q_o_mask, q_o_f; wire [127:0] q_o_y; wire [63:0] q_o_bf;
    ot_hdc_v41x_wgt_mtile u_ref (
        .clk(clk), .rst_n(rst_n), .d_v(q_d_v), .d_rdy(q_d_rdy), .d_plg(q_plg), .d_nb(q_nb), .d_nrows(q_nrows),
        .d_wbase(q_wbase), .d_ind(1'b0), .d_eid(9'd0), .d_estride(20'd0), .d_tag(q_tag),
        .rq_v(q_rq_v), .rq_a(q_rq_a), .rq_q(q_rq_q), .rq_plg(), .rq_tag(), .rd_w(q_rd_w), .rd_x(q_rd_x),
        .o_cr(q_o_cr), .o_v(q_o_v), .o_rg(q_o_rg), .o_tag(q_o_tag), .o_mask(q_o_mask), .o_y(q_o_y), .o_bf(q_o_bf),
        .o_f(q_o_f), .idle(q_idle));
    always @(posedge clk) q_o_cr <= q_o_v;
    integer ci, ui;
    always @(posedge clk) begin
        for (ci = 0; ci < 8; ci = ci + 1) begin
            if (q_rq_v[ci]) begin
                w1[ci] <= wmem[ci*2048 + q_rq_a[ci*20 +: 11]];
                x1[ci] <= xmem[ci*128 + q_rq_q[ci*14 +: 7]];
            end
            for (ui = 0; ui < 8; ui = ui + 1) begin
                q_rd_w[(8*ui + ci)*34 +: 34] <= w1[ci][ui*34 +: 34];
                q_rd_x[(8*ui + ci)*16 +: 16] <= x1[ci][ui*16 +: 16];
            end
        end
    end

    localparam integer EW = 16 + 4 + 4 + 128 + 64 + 4;
    reg [EW-1:0] dlog [0:1023];
    reg [EW-1:0] rlog [0:1023];
    integer nd = 0, nr = 0, d_first0 = -1, r_first0 = -1, d_acc0 = 0, r_acc0 = 0, d_last = 0, r_last = 0;
    always @(posedge clk) if (rst_n && r_v) begin
        dlog[nd] <= {r_rg, r_tag, r_mask, r_y, r_bf, r_f}; nd <= nd + 1; d_last <= cyc;
        if (d_first0 < 0) d_first0 <= cyc;
    end
    always @(posedge clk) if (rst_n && q_o_v) begin
        rlog[nr] <= {q_o_rg, q_o_tag, q_o_mask, q_o_y, q_o_bf, q_o_f}; nr <= nr + 1; r_last <= cyc;
        if (r_first0 < 0) r_first0 <= cyc;
    end
    integer i, k, errors = 0, total = 0, nfault = 0;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "DIR required");
        $readmemh($sformatf("%s/wmem.hex", dir), wmem);
        $readmemh($sformatf("%s/xmem.hex", dir), xmem);
        #1;
        $readmemh($sformatf("%s/via0.hex", dir), dut.g_mc[0].u_rom.arr);
        $readmemh($sformatf("%s/via1.hex", dir), dut.g_mc[1].u_rom.arr);
        $readmemh($sformatf("%s/via2.hex", dir), dut.g_mc[2].u_rom.arr);
        $readmemh($sformatf("%s/via3.hex", dir), dut.g_mc[3].u_rom.arr);
        $readmemh($sformatf("%s/via4.hex", dir), dut.g_mc[4].u_rom.arr);
        $readmemh($sformatf("%s/via5.hex", dir), dut.g_mc[5].u_rom.arr);
        $readmemh($sformatf("%s/via6.hex", dir), dut.g_mc[6].u_rom.arr);
        $readmemh($sformatf("%s/via7.hex", dir), dut.g_mc[7].u_rom.arr);
        repeat (4) @(negedge clk);
        rst_n = 1;
        repeat (4) @(negedge clk);
        for (i = 0; i < 8*8; i = i + 1) begin        // beats 0..7 of every chain position
            s_x_we = 1; s_x_pos = 3'(i / 8); s_x_addr = 7'(i % 8); s_x_data = xmem[(i / 8)*128 + (i % 8)];
            @(negedge clk);
        end
        s_x_we = 0;
        repeat (4) @(negedge clk);
        fork
            begin
                for (k = 0; k < NOPS; k = k + 1) begin
                    s_d_v = 1; s_d_plg = op_plg[k]; s_d_nb = op_nb[k]; s_d_nrows = op_nrows[k];
                    s_d_wbase = op_wbase[k]; s_d_tag = op_tag[k];
                    @(posedge clk); while (!s_d_rdy) @(posedge clk);
                    if (k == 0) d_acc0 = cyc;
                    @(negedge clk); s_d_v = 0;
                end
            end
            begin : ref_drive
                integer j;
                for (j = 0; j < NOPS; j = j + 1) begin
                    q_d_v = 1; q_plg = op_plg[j]; q_nb = op_nb[j]; q_nrows = op_nrows[j];
                    q_wbase = op_wbase[j]; q_tag = op_tag[j];
                    @(posedge clk); while (!q_d_rdy) @(posedge clk);
                    if (j == 0) r_acc0 = cyc;
                    @(negedge clk); q_d_v = 0;
                end
            end
        join
        while ((nd < nr || nr == 0 || !q_idle || !idle) && cyc < 200000) @(negedge clk);
        repeat (50) @(negedge clk);
        if (nd != nr || nd == 0) $fatal(1, "result count dut=%0d ref=%0d", nd, nr);
        for (i = 0; i < nd; i = i + 1) begin
            if (dlog[i] !== rlog[i]) begin
                errors = errors + 1;
                if (errors < 5) $display("MISMATCH %0d dut=%h ref=%h", i, dlog[i], rlog[i]);
            end
            if (dlog[i][3:0] != 0) nfault = nfault + 1;
        end
        if (f_reserved) $fatal(1, "DUT reserved fault");
        if (errors) $fatal(1, "errors=%0d", errors);
        $display("ME_ROMAC_PASS results=%0d fault_results=%0d", nd, nfault);
        $display("ME_ROMAC_LAT dut_accept=%0d dut_first=%0d ref_accept=%0d ref_first=%0d dut_last=%0d ref_last=%0d",
                 d_acc0, d_first0, r_acc0, r_first0, d_last, r_last);
        $finish;
    end
endmodule
