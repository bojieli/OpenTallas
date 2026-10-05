`timescale 1ns/1ps
// RTL side of tools/v41_selection_global_ids.py: for every id in ids.hex (sorted, <= 512), the selected-CKV
// DMA of every die (remote_needed / remote_die, or the stack port and first sector address), the ID table's
// read ports (rd_die / rd_stack / rd_local) and the wide fetch's port choice must equal exp.hex
// {die[1:0], stack[1:0], local[20:0], port-in-stack[3:0] (P = 4)} computed by the tool.  +n=<count>.
module tb_v41_selection_global_ids;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg [31:0] ids [0:511];
    reg [31:0] exp_ [0:511];
    integer n = 0, i, d, errors = 0, checked = 0, t;
    localparam [4*30-1:0] BASE = {30'd4000003, 30'd3000003, 30'd2000003, 30'd1000003};
    localparam [4*30-1:0] CNT = {4{30'd200000000}};
    // DMAs of the four dies
    reg fetch_v = 0; reg [20:0] sid = 0;
    wire [3:0] rem; wire [7:0] rdie; wire [15:0] mv_all; wire [4*120-1:0] maddr_all;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_d
        wire fr, ok, pv, flt; wire [31:0] q, r1, r2; wire [7:0] q8; wire [2303:0] prow; wire [9:0] plr;
        wire [20:0] psid; wire [3:0] fc, mwe, srdy; wire [15:0] mlen; wire [63:0] mtag; wire [1023:0] mwd;
        wire [127:0] mws;
        ot_chip_v41x_ckv_selected_dma #(.DIE_ID(g)) u (
            .clk(clk), .rst_n(rst_n), .region_base_sector(BASE), .region_sector_count(CNT),
            .published_source_count(21'h1fffff), .fetch_v(fetch_v), .fetch_ready(fr), .local_row(10'd200),
            .window_count(8'd128), .source_id(sid), .remote_needed(rem[g]), .remote_die(rdie[g*2 +: 2]),
            .kv_ok(ok), .re(1'b0), .rrow(10'd0), .relem(9'd0), .q(q), .q_fp8(q8), .packed_row(prow),
            .packed_valid(pv), .packed_local_row(plr), .packed_source_id(psid), .fault(flt), .fault_code(fc),
            .st_rows_fetched(r1), .st_sectors_read(r2), .m_v(mv_all[g*4 +: 4]), .m_rdy(4'h0),
            .m_addr(maddr_all[g*120 +: 120]), .m_len(mlen), .m_tag(mtag), .m_we(mwe), .m_wdata(mwd), .m_wstrb(mws),
            .m_wr_done(4'h0), .s_v(4'h0), .s_rdy(srdy), .s_tag(64'd0), .s_beat(16'd0), .s_data(1024'd0));
    end endgenerate
    // ID table (one port carries every id)
    reg clr = 0; reg [3:0] s_valid = 0, s_last = 0; reg [63:0] s_lv = 0; reg [1279:0] s_idx = 0;
    wire [3:0] s_ready; wire [9:0] cnt; wire done; wire [31:0] dc; reg [9:0] rr = 0;
    wire [20:0] rg, rl, og; wire [1:0] rd, rs; wire flt; wire [3:0] fc; wire [39:0] oc, orank;
    ot_chip_v41x_ckv_sel_ids #(.NRD(1)) u_ids (
        .clk(clk), .rst_n(rst_n), .clr(clr), .exp_n(10'(n)), .s_valid(s_valid), .s_ready(s_ready), .s_last(s_last),
        .s_lv(s_lv), .s_idx(s_idx), .count(cnt), .done(done), .done_cycle_count(dc), .rd_rank(rr), .rd_gid(rg),
        .rd_die(rd), .rd_stack(rs), .rd_local(rl), .own_count(oc), .own_idx(40'd0), .own_rank(orank), .own_gid(),
        .fault(flt), .fault_code(fc));
    // wide fetch port choice (P = 4), die 0..3
    reg fjob = 0; reg [20:0] fgid = 0;
    wire [63:0] fmv;
    generate for (g = 0; g < 4; g = g + 1) begin : g_w
        wire jr, ov, dn, ft; wire [9:0] ix, ork; wire [20:0] ogid; wire [2303:0] orow; wire [2:0] fcw;
        wire [31:0] own; wire [16*30-1:0] ma; wire [16*8-1:0] mt;
        ot_chip_v41x_ckv_pc_fetch #(.DIE_ID(g), .P(4), .S(16)) u (
            .clk(clk), .rst_n(rst_n), .job_v(fjob), .job_ready(jr), .window_count(8'd128),
            .published_source_count(21'h1fffff), .region_base_sector(BASE), .region_sector_count(CNT),
            .id_count(10'd1), .id_done(1'b1), .id_idx(ix), .id_rank_in(10'd0), .id_gid(fgid),
            .o_v(ov), .o_ready(1'b1), .o_rank(ork), .o_gid(ogid), .o_row(orow), .done(dn), .fault(ft),
            .fault_code(fcw), .st_owned_rows(own), .m_v(fmv[g*16 +: 16]), .m_rdy(16'd0), .m_addr(ma), .m_tag(mt),
            .s_v(16'd0), .s_tag(128'd0), .s_beat(64'd0), .s_data(4096'd0));
    end endgenerate
    reg [1:0] ed, es; reg [20:0] el; reg [3:0] ep;
    initial begin
        if (!$value$plusargs("n=%d", n)) n = 0;
        $readmemh("ids.hex", ids, 0, n - 1);
        $readmemh("exp.hex", exp_, 0, n - 1);
        for (i = 0; i < n; i = i + 1) begin
            {ed, es, el, ep} = exp_[i][28:0];
            // DMA: one fetch per id from reset
            rst_n = 0; @(negedge clk); rst_n = 1; @(negedge clk);
            sid = ids[i][20:0]; fetch_v = 1; @(negedge clk); fetch_v = 0; @(negedge clk);
            for (d = 0; d < 4; d = d + 1) begin
                checked = checked + 1;
                if (d == ed) begin
                    if (rem[d] || mv_all[d*4 +: 4] != (4'b1 << es) ||
                        maddr_all[d*120 + es*30 +: 30] != 30'(BASE[es*30 +: 30] + 9 * el)) begin
                        errors = errors + 1;
                        if (errors < 5) $display("DMA MISMATCH id %0d die %0d", ids[i], d);
                    end
                end else if (mv_all[d*4 +: 4] != 0) begin
                    errors = errors + 1;
                    if (errors < 5) $display("DMA NONOWNER REQ id %0d die %0d", ids[i], d);
                end
            end
            // wide fetch: the owner die's port
            rst_n = 0; @(negedge clk); rst_n = 1; @(negedge clk);
            fgid = ids[i][20:0]; fjob = 1; @(negedge clk); fjob = 0;
            for (t = 0; t < 6; t = t + 1) @(negedge clk);
            checked = checked + 1;
            if (fmv != (64'd1 << (ed * 16 + es * 4 + ep))) begin
                errors = errors + 1;
                if (errors < 5) $display("PORT MISMATCH id %0d got %h", ids[i], fmv);
            end
        end
        // ID table: all ids through quarter-0 beats, other quarters empty
        rst_n = 0; @(negedge clk); rst_n = 1; @(negedge clk);
        clr = 1; @(negedge clk); clr = 0;
        i = 0;
        while (i < n || !s_last[0]) begin
            s_valid = 4'b0001; s_lv = 0;
            for (d = 0; d < 16; d = d + 1) if (i + d < n) begin s_lv[d] = 1; s_idx[d*20 +: 20] = ids[i + d][19:0]; end
            s_last = (i + 16 >= n) ? 4'b0001 : 4'b0000;
            @(negedge clk); i = i + 16;
            if (s_last[0]) begin
                s_valid = 4'b0010; s_lv = 0; s_last = 4'b0010; @(negedge clk);
                s_valid = 4'b0100; s_last = 4'b0100; @(negedge clk);
                s_valid = 4'b1000; s_last = 4'b1000; @(negedge clk);
                s_valid = 0; s_last = 4'b0001;
            end
        end
        s_last = 0;
        for (t = 0; t < 4; t = t + 1) @(negedge clk);
        if (!done || flt) begin errors = errors + 1; $display("TABLE not done fault=%0d cnt=%0d", flt, cnt); end
        for (i = 0; i < n; i = i + 1) begin
            {ed, es, el, ep} = exp_[i][28:0];
            rr = 10'(i); #0.1;
            checked = checked + 1;
            if (rg != ids[i][20:0] || rd != ed || rs != es || rl != el) begin
                errors = errors + 1;
                if (errors < 5) $display("TABLE MISMATCH rank %0d", i);
            end
        end
        $display("GLOBAL_IDS checked=%0d errors=%0d", checked, errors);
        $finish;
    end
endmodule
