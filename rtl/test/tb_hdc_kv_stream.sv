`timescale 1ns/1ps
// Stand-alone test of ot_hdc_kv_stream against the HBM model, with a model of
// the matrix engine's KV reads in place of the core.  Covers what the reduced
// vehicle's decode does not reach: several rounds, both fetch modes (K-mode
// runs along k; G-mode runs across groups, the weighted sum of a head_dim-128
// model), every GQA share (jsh 0..3), partial valid tiles, and ops far longer
// than the window (steady streaming through refreshes).
//
// The "engine" announces each op (kvd_v), issues it on kv_ok (never in the
// announcing cycle), announces the next op a few cycles after issuing, and
// runs the element loop of tools/hdc_program.py's ISA model: round r, k, slot
// j; group g reads word wbase + (r*G + g)*ts + k*ks + (j >> jsh)*js, one cycle
// before it takes kv_q.  Every delivered word of a valid tile (t*W < nout) is
// compared with HBM; invalid tiles must read zero.
//
// +SET=0: the provisioned ops (demand <= supply), expected PASS with no fault.
// +SET=1: one op demanding 4 words per cycle from 2 pseudo-channels (~1.8
//         words per cycle): the start condition cannot cover it and the
//         streamer must report the underflow (fault) -- expected FAULT_DETECTED.
// +SET=2: bandwidth probe.  The same kind of op, but the engine model takes a
//         line only once the streamer has completed it (a dataflow consumer, not
//         the real engine), so the run measures the sustained HBM read rate.
module tb_hdc_kv_stream #(
    parameter integer G = 4,
    parameter integer LWIN = 8,
    parameter integer NPC = 2,
    parameter integer BK = 16,
    parameter integer CLK_PS = 1000
) (input wire clk);
    localparam integer W = 16, AW = 24, NW = 16, IL = 8;
    localparam integer MEM = 65536;
    localparam integer WIN = 1 << LWIN, LG = $clog2(G), TAGW = 1 + LWIN + LG + 3, LBK = $clog2(BK);
    localparam integer NOPS = 7;

    reg rst_n = 1'b0;
    reg [NW-1:0] lead;
    // op table: wbase ts ks js jsh tiles k nout
    reg [AW-1:0] o_wbase [0:NOPS-1], o_ts [0:NOPS-1], o_ks [0:NOPS-1], o_js [0:NOPS-1];
    reg [2:0]    o_jsh [0:NOPS-1];
    reg [NW-1:0] o_tiles [0:NOPS-1], o_k [0:NOPS-1], o_nout [0:NOPS-1];
    integer nops, set;

    reg kvd_v; wire kv_ok;
    reg [AW-1:0] kvd_wbase, kvd_ts, kvd_ks, kvd_js; reg [2:0] kvd_jsh; reg [NW-1:0] kvd_tiles, kvd_k, kvd_nout;
    reg kv_re; reg [G*AW-1:0] kv_raddr; wire [G*W*32-1:0] kv_q;
    wire [G-1:0] win_we; wire [G*LWIN-1:0] win_waddr; wire [G*W*16-1:0] win_wdata;
    wire win_re; wire [LWIN-1:0] win_raddr; reg [G*W*16-1:0] win_q;
    wire [1:0] tl_we, tl_re; wire [2*5-1:0] tl_waddr, tl_raddr; wire [2*W-1:0] tl_wmask; wire [2*W*16-1:0] tl_wdata;
    wire hq_v, hq_rdy, hq_we; wire [AW-1:0] hq_addr; wire [LBK:0] hq_len; wire [TAGW-1:0] hq_tag; wire [W*16-1:0] hq_wdata;
    wire [NPC-1:0] hr_v, hr_rdy; wire [NPC*TAGW-1:0] hr_tag; wire [NPC*LBK-1:0] hr_beat; wire [NPC*W*16-1:0] hr_data;
    wire fault;
    reg [W*16-1:0] win [0:G-1][0:WIN-1];

    ot_hdc_kv_stream #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .LWIN(LWIN), .NPC(NPC), .BK(BK),
                       .LOG_HD(4), .LOG_TW(2), .LLG(1), .V0_WORD(0)) u_kvs (
        .clk(clk), .rst_n(rst_n), .tok_start(1'b0), .tok_pos(16'd0), .cfg_lead(lead),
        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(kvd_ts), .kvd_ks(kvd_ks), .kvd_js(kvd_js),
        .kvd_jsh(kvd_jsh), .kvd_tiles(kvd_tiles), .kvd_k(kvd_k), .kvd_nout(kvd_nout),
        .kvd_kindk(1'b0), .kvd_pos(16'd0), .kv_ok(kv_ok),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q),
        .kv_we(1'b0), .kv_waddr({AW{1'b0}}), .kv_wdata(32'd0),
        .win_we(win_we), .win_waddr(win_waddr), .win_wdata(win_wdata), .win_re(win_re), .win_raddr(win_raddr),
        .win_q(win_q),
        .tl_we(tl_we), .tl_waddr(tl_waddr), .tl_wmask(tl_wmask), .tl_wdata(tl_wdata), .tl_re(tl_re),
        .tl_raddr(tl_raddr), .tl_q({(2*W*16){1'b0}}),
        .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_we(hq_we), .hq_addr(hq_addr), .hq_len(hq_len), .hq_tag(hq_tag),
        .hq_wdata(hq_wdata),
        .hr_v(hr_v), .hr_rdy(hr_rdy), .hr_tag(hr_tag), .hr_beat(hr_beat), .hr_data(hr_data), .fault(fault));
    ot_hdc_hbm_model #(.NPC(NPC), .AW(AW), .DW(W*16), .MEM_WORDS(MEM), .TAGW(TAGW), .LENW(LBK+1),
                       .BEATW(LBK), .CLK_PS(CLK_PS)) u_hbm (
        .clk(clk), .rst_n(rst_n), .req_v(hq_v), .req_rdy(hq_rdy), .req_we(hq_we), .req_addr(hq_addr),
        .req_len(hq_len), .req_tag(hq_tag), .req_wdata(hq_wdata),
        .rsp_v(hr_v), .rsp_rdy(hr_rdy), .rsp_tag(hr_tag), .rsp_beat(hr_beat), .rsp_data(hr_data));
    integer q;
    always @(posedge clk) begin
        for (q = 0; q < G; q = q + 1) begin
            if (win_re) win_q[q*W*16 +: W*16] <= win[q][win_raddr];
            if (win_we[q]) win[q][win_waddr[q*LWIN +: LWIN]] <= win_wdata[q*W*16 +: W*16];
        end
    end

    function automatic [W*16-1:0] pattern(input integer a);
        integer l;
        for (l = 0; l < W; l = l + 1) pattern[l*16 +: 16] = (a * 7 + l * 13 + 1) & 16'h7F7F;
    endfunction

    task automatic add_op(input [AW-1:0] wb, ts, ks, js, input [2:0] jsh, input [NW-1:0] tiles, kk, nout);
        begin
            o_wbase[nops] = wb; o_ts[nops] = ts; o_ks[nops] = ks; o_js[nops] = js; o_jsh[nops] = jsh;
            o_tiles[nops] = tiles; o_k[nops] = kk; o_nout[nops] = nout; nops = nops + 1;
        end
    endtask
    integer i;
    initial begin
        if (!$value$plusargs("LEAD=%d", lead)) lead = 512;
        if (!$value$plusargs("SET=%d", set)) set = 0;
        for (i = 0; i < MEM; i = i + 1) u_hbm.mem[i] = pattern(i);
        nops = 0;
        if (set == 0) begin
            // K-mode (scores-like): 3 rounds, partial last tile, 2 KV heads per op
            add_op(24'd1000, 24'd16, 24'd1, 24'd4096, 3'd2, 16'd3, 16'd16, 16'd170);
            // G-mode (weighted sum, head_dim 128: 8 words a row, 2 rounds of 4 tiles)
            add_op(24'd20000, 24'd1, 24'd8, 24'd8192, 3'd2, 16'd2, 16'd100, 16'd128);
            // G-mode, a partial second round (head_dim 96: 6 tiles)
            add_op(24'd30000, 24'd1, 24'd6, 24'd4000, 3'd2, 16'd2, 16'd50, 16'd96);
            // K-mode, one KV head per 8 slots (jsh 3) and per 2 slots (jsh 1)
            add_op(24'd2000, 24'd32, 24'd1, 24'd512, 3'd3, 16'd2, 16'd32, 16'd128);
            add_op(24'd6000, 24'd16, 24'd1, 24'd2048, 3'd1, 16'd1, 16'd16, 16'd64);
            // a long weighted-sum-like K-mode op: 3,000 positions, 6,000 lines (23x the window)
            add_op(24'd40000, 24'd1, 24'd1, 24'd3000, 3'd2, 16'd1, 16'd3000, 16'd16);
            // and a long G-mode op: 2,000 positions of head_dim 64
            add_op(24'd8000, 24'd1, 24'd4, 24'd9000, 3'd2, 16'd1, 16'd2000, 16'd64);
        end else begin
            // set 1: jsh 0, 8 KV heads per op, 4 words per cycle; set 2: jsh 2 (GQA 4:1 as Qwen3),
            // 1 word per cycle, run on one pseudo-channel to measure its sustained rate
            if (set == 1) add_op(24'd8000, 24'd1, 24'd4, 24'd9000, 3'd0, 16'd1, 16'd6000, 16'd64);
            else add_op(24'd8000, 24'd1, 24'd4, 24'd9000, 3'd2, 16'd1, 16'd6000, 16'd64);
        end
    end

    // the engine model
    integer cyc = 0, op = 0, nxt = 0, bad = 0, zbad = 0, checked = 0;
    integer r, k, j, g, t, gap;
    reg running = 1'b0, announced = 1'b0, finished = 1'b0;
    integer ann_cyc, wait_total = 0, probe_start = 0, probe_end = 0;
    reg pace_ok;
    longint rd_sum;
    reg chk_v; reg [G*AW-1:0] chk_addr; reg [G-1:0] chk_valid, el_valid;
    reg [W*16-1:0] e16; reg [W*32-1:0] e32;
    integer l;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1'b1;
        kvd_v <= 1'b0; kv_re <= 1'b0;
        // announce the next op (the core: when the sequencer reaches it)
        if (rst_n && cyc > 10 && !announced && nxt < nops && (!running || gap >= 6)) begin
            kvd_v <= 1'b1; announced <= 1'b1; ann_cyc = cyc;
            kvd_wbase <= o_wbase[nxt]; kvd_ts <= o_ts[nxt]; kvd_ks <= o_ks[nxt]; kvd_js <= o_js[nxt];
            kvd_jsh <= o_jsh[nxt]; kvd_tiles <= o_tiles[nxt]; kvd_k <= o_k[nxt]; kvd_nout <= o_nout[nxt];
        end
        pace_ok = (set != 2) || ($signed(u_kvs.cp_line - u_kvs.cons_line) >= 3) || !u_kvs.p_act;
        if (running && pace_ok) begin
            gap = gap + 1;
            kv_re <= 1'b1;
            for (g = 0; g < G; g = g + 1) begin
                kv_raddr[g*AW +: AW] <= o_wbase[op] + (r*G + g) * o_ts[op] + k * o_ks[op] + (j >> o_jsh[op]) * o_js[op];
                el_valid[g] <= ((r*G + g) * W < o_nout[op]);
            end
            if (j < IL - 1) j = j + 1;
            else begin
                j = 0;
                if (k < o_k[op] - 1) k = k + 1;
                else begin
                    k = 0;
                    if (r < o_tiles[op] - 1) r = r + 1;
                    else begin running <= 1'b0; op = op + 1; probe_end = cyc; end
                end
            end
        end else if (!running && announced && !kvd_v && kv_ok && op == nxt) begin
            // issue: the element loop starts next cycle
            wait_total = wait_total + (cyc - ann_cyc);
            $display("OP %0d issued after %0d cycles", nxt, cyc - ann_cyc);
            running <= 1'b1; r = 0; k = 0; j = 0; gap = 0; probe_start = cyc;
            announced <= 1'b0; nxt = nxt + 1;
        end
        if (!running && !announced && nxt == nops && op == nops && !finished && cyc > 20) finished <= 1'b1;
        // check what the engine takes this cycle (addresses of the previous one)
        chk_v <= kv_re; chk_addr <= kv_raddr; chk_valid <= el_valid;
        if ($test$plusargs("RSPTRACE") && hr_v[0] && hr_rdy[0] && cyc < 400)
            $display("RSP cyc=%0d tag=%h beat=%0d d=%h line=%0d grp=%0d", cyc, hr_tag[TAGW-1:0], hr_beat[LBK-1:0],
                     hr_data[15:0], u_kvs.rsp_line[LWIN-1:0], u_kvs.rsp_grp[LG-1:0]);
        if ($test$plusargs("RSPTRACE") && hq_v && hq_rdy && cyc < 400)
            $display("REQ cyc=%0d we=%0d addr=%0d len=%0d tag=%h", cyc, hq_we, hq_addr, hq_len, hq_tag);
        if (chk_v)
            for (g = 0; g < G; g = g + 1) begin
                e16 = chk_valid[g] ? pattern(chk_addr[g*AW +: AW] % MEM) : {(W*16){1'b0}};
                for (l = 0; l < W; l = l + 1) e32[l*32 +: 32] = {e16[l*16 +: 16], 16'h0};
                checked = checked + 1;
                if (kv_q[g*W*32 +: W*32] !== e32) begin
                    if (bad + zbad < 4)
                        $display("MISMATCH cyc=%0d op=%0d g=%0d valid=%0d addr=%0d got=%h", cyc, op, g, chk_valid[g],
                                 chk_addr[g*AW +: AW], kv_q[g*W*32 +: 64]);
                    if (chk_valid[g]) bad = bad + 1; else zbad = zbad + 1;
                end
            end
        if (fault || finished || cyc > 3000000) begin
            $display("KVSTREAM_UNIT set=%0d ops=%0d/%0d checked=%0d mismatches=%0d zero_mismatches=%0d fault=%0d wait_cycles=%0d cycles=%0d hbm_rd_lat_max_ps=%0d",
                     set, op, nops, checked, bad, zbad, fault, wait_total, cyc, u_hbm.st_rd_lat_max);
            for (g = 0; g < NPC; g = g + 1)
                $display("HBM_PC pc=%0d reads=%0d writes=%0d acts=%0d row_hits=%0d row_conflicts=%0d refreshes=%0d",
                         g, u_hbm.st_rd[g], u_hbm.st_wr[g], u_hbm.st_act[g], u_hbm.st_hit[g], u_hbm.st_conf[g],
                         u_hbm.st_ref[g]);
            $display("HBM req_backpressure_cycles=%0d rd_lat_avg_ps=%0d", u_hbm.st_bp_cycles,
                     u_hbm.st_rd_lat_sum / (u_hbm.st_rd[0] + 1) / NPC);
            if (set == 2)
            begin
                rd_sum = 0;
                for (g = 0; g < NPC; g = g + 1) rd_sum = rd_sum + u_hbm.st_rd[g];
                $display("PROBE npc=%0d hbm_words=%0d cycles=%0d", NPC, rd_sum, probe_end - probe_start);
            end
            if (fault) $display("FAULT_DETECTED cons_line=%0d cp_line=%0d fetch_line=%0d q_n=%0d/%0d r_n=%0d/%0d now=%0d next_ref=%0d/%0d",
                                u_kvs.cons_line, u_kvs.cp_line, u_kvs.fetch_line, u_hbm.q_n[0], u_hbm.q_n[NPC-1],
                                u_hbm.r_n[0], u_hbm.r_n[NPC-1], u_hbm.cyc * CLK_PS, u_hbm.next_ref[0], u_hbm.next_ref[NPC-1]);
            else if (finished && bad == 0 && zbad == 0) $display("PASS");
            else $display("FAIL");
            $finish;
        end
    end
endmodule
