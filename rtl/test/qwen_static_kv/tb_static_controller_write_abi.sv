`timescale 1ns/1fs
// Exact existing physical write/retirement ABI stimulus adapted to the new
// persistent controller PO stage. PROFILE is diagnostic only; random legacy
// credits are not a compiled native program and never qualify native release.
// Raw PHY23-cycle external model; actualKV handoff input register enabled.
module tb_static_controller_write_abi;
    parameter integer PCI = 0, MUT = 0, NL = 3, RL = 23, HAND_PIPE = 1;
`include "qkd_strip_map.vh"
    localparam integer ROW0 = 64, SROW = 24427, CVL = 2;
    reg hclk = 0, ck = 0;
    always #0.512 hclk = ~hclk;
    initial begin #0.137; forever #0.416667 ck = ~ck; end
    reg hrst = 0, rsi = 0;
    reg  [318:0] ci = 0;
    wire [293:0] co;
    reg  [287:0] es = 0;
    wire [260:0] er;
    wire [327:0] po;
    reg  [288:0] pi = 0;
    reg  [32:0]  ki = 0;
    wire [32:0]  ko;
    wire         fo;
    qkd_ctrl_pc_host_static #(.MUT(MUT),.PROFILE(1)) dut (.pll_hbm(hclk), .hrst(hrst), .ck(ck), .rsi(rsi), .pc(5'(PCI)), .ci(ci), .co(co),
        .es(es), .er(er), .po(po), .pi(pi), .ki(ki), .ko(ko), .fi(1'b0), .fo(fo),.static_cmd_owner(1'b0),.static_cmd(43'b0),.reserved_rd(1'b0),.reserved_static_col(1'b0),.reserved_write_col(1'b0),.static_epoch(16'd7),.expected_raw_valid(pi[0]),.corrected_epoch(),.completion_v(),.completion_we(),.completion_fault());

    wire        p_rv  = po[O_po_row_v];
    wire [2:0]  p_rop = po[O_po_row_op +: 3];
    wire [4:0]  p_rb  = po[O_po_row_bank +: 5];
    wire [18:0] p_rr  = po[O_po_row_row +: 19];
    wire        p_cv  = po[O_po_col_v], p_cwe = po[O_po_col_we];
    wire [4:0]  p_cb  = po[O_po_col_bank +: 5], p_cc = po[O_po_col_col +: 5];
    wire [287:0] p_wd = po[O_po_wd +: 288];
    longint kv_write_column_cycle[$];
    longint cyc = 0, n_cmp = 0, n_err = 0, n_rowc = 0, n_colc = 0;
    task automatic bad(input string what);
        if (n_err < 12) $display("MISMATCH hclk=%0d %s", cyc, what);
        n_err++;
    endtask
    always @(posedge hclk)if(hrst)begin n_cmp++;if(p_rv)n_rowc++;if(p_cv)n_colc++;end

    // ---------------- the bench's own SECDED(72,64) x 4 ----------------
    function automatic [71:0] enc64(input [63:0] data);
        reg [71:0] c; integer p, k, j;
        begin
            c = '0; j = 0;
            for (p = 1; p <= 71; p = p + 1) if ((p & (p - 1)) != 0) begin c[p-1] = data[j]; j = j + 1; end
            for (k = 0; k < 7; k = k + 1)
                for (p = 1; p <= 71; p = p + 1)
                    if ((p & (1 << k)) != 0 && p != (1 << k)) c[(1<<k)-1] = c[(1<<k)-1] ^ c[p-1];
            c[71] = ^c[70:0]; enc64 = c;
        end
    endfunction
    function automatic [287:0] enc256(input [255:0] d);
        enc256 = {enc64(d[255:192]), enc64(d[191:128]), enc64(d[127:64]), enc64(d[63:0])};
    endfunction
    function automatic [255:0] pat(input integer k);
        integer j;
        begin for (j = 0; j < 8; j = j + 1) pat[j*32 +: 32] = (32'h9e3779b9 * (k * 8 + j + 1)) ^ (k << j) ^ 32'h5bd1e995; end
    endfunction

    // ---------------- (b) behavioural HBM pseudo-channel on po / pi ----------------
    reg  [255:0] kvmem [0:64*1024-1];              // [layer * 1024 + j]
    reg  [255:0] stmem [0:1023];                   // the static row, [{bank, col}]
    bit          b_open [0:31]; int b_row [0:31];
    // RD returns in order
    longint      rq_due [$]; reg [287:0] rq_word [$];
    // expectations
    typedef struct { reg [16:0] sec; reg [7:0] row; reg [255:0] data; } land_t;
    land_t       exp_land [$];
    typedef struct { reg [255:0] data; bit ce; } st_t;
    st_t         exp_st [$];
    typedef struct { reg [23:0] sec; reg [255:0] data; reg [8:0] tag; } wr_t;
    wr_t         exp_wr [$];                       // handed-off KV writes awaiting their WR data
    typedef struct { reg [9:0] bc; reg [18:0] row; reg [255:0] data; } sw_t;
    sw_t         exp_sw [$];                       // posted static writes
    longint      wr_due [$]; int wr_b [$], wr_c [$], wr_row [$];
    longint n_rd = 0, n_kvw = 0, n_stw = 0, n_strd = 0, n_flip = 0, n_act = 0;
    integer ii;
    initial begin
        for (ii = 0; ii < 64 * 1024; ii = ii + 1) kvmem[ii] = pat(ii + 7);
        for (ii = 0; ii < 1024; ii = ii + 1) stmem[ii] = pat(ii + 900000);
        for (ii = 0; ii < 32; ii = ii + 1) begin b_open[ii] = 0; b_row[ii] = 0; end
    end
    always @(posedge hclk) begin
        cyc++;
        pi <= 289'd0;
        if (rq_due.size() != 0 && rq_due[0] <= cyc) begin
            pi <= {rq_word[0], 1'b1};
            void'(rq_due.pop_front()); void'(rq_word.pop_front());
        end
        if (hrst && p_rv) begin
            if (p_rop == 3'd1) begin n_act++; b_open[p_rb] = 1; b_row[p_rb] = p_rr; end
            else if (p_rop == 3'd0) b_open[p_rb] = 0;
        end
        if (hrst && p_cv && !p_cwe) begin : rd
            automatic reg [9:0] j = {p_cb[4:2], p_cc, p_cb[1:0]};
            automatic int row = b_row[p_cb];
            automatic reg [287:0] w;
            automatic land_t e; automatic st_t s;
            if (!b_open[p_cb]) bad("RD to a closed bank");
            n_rd++;
            if (row >= ROW0 && row < ROW0 + 64) begin
                e.sec = {6'(row - ROW0), j[9:7], 1'b0, j[6:0]}; e.row = 8'(row); e.data = kvmem[(row - ROW0) * 1024 + j];
                w = enc256(e.data);
                if (n_rd % 37 == 5) begin w[(n_rd * 13) % 288] = ~w[(n_rd * 13) % 288]; n_flip++; end
                exp_land.push_back(e);
            end else begin
                if (row != SROW) bad("RD on an unexpected row");
                s.data = stmem[{p_cb, p_cc}]; s.ce = (n_strd % 2) == 1;
                w = enc256(s.data);
                if (s.ce) w[(n_strd * 29 + 3) % 288] = ~w[(n_strd * 29 + 3) % 288];
                n_strd++;
                exp_st.push_back(s);
            end
            rq_due.push_back(cyc + RL); rq_word.push_back(w);
        end
        if (hrst && p_cv && p_cwe) begin
            if(b_row[p_cb]>=ROW0&&b_row[p_cb]<ROW0+64)kv_write_column_cycle.push_back(cyc);
            if (!b_open[p_cb]) bad("WR to a closed bank");
            wr_due.push_back(cyc + CVL + 3); wr_b.push_back(p_cb); wr_c.push_back(p_cc); wr_row.push_back(b_row[p_cb]);
        end
        if (wr_due.size() != 0 && wr_due[0] == cyc) begin : wr
            automatic int b = wr_b.pop_front(), c = wr_c.pop_front(), row = wr_row.pop_front();
            automatic reg [4:0] bb = 5'(b);
            automatic reg [4:0] cc = 5'(c);
            automatic reg [9:0] j = {bb[4:2], cc, bb[1:0]};
            void'(wr_due.pop_front());
            if (row >= ROW0 && row < ROW0 + 64) begin
                if (exp_wr.size() == 0) bad("KV WR column with no handed-off write");
                else begin
                    automatic wr_t x = exp_wr.pop_front();
                    if ({x.sec[10:8], x.sec[6:0]} !== j) bad("KV WR at the wrong bank / column");
                    if (int'(x.sec[16:11]) + ROW0 != row) bad($sformatf("KV WR on row %0d, posted for layer %0d", row, x.sec[16:11]));
                    if (p_wd !== enc256(x.data)) bad("PHY write data is not the bench's SECDED encoding of the posted sector");
                    kvmem[(row - ROW0) * 1024 + j] = x.data; n_kvw++;
                end
            end else begin
                if (exp_sw.size() == 0) bad("static WR column with no posted static write");
                else begin
                    automatic sw_t x = exp_sw.pop_front();
                    if (x.bc !== {bb, cc} || int'(x.row) != row) bad($sformatf("static WR at bank %0d col %0d row %0d, posted bank %0d col %0d row %0d", bb, cc, row, x.bc[9:5], x.bc[4:0], x.row));
                    if (p_wd !== enc256(x.data)) bad("static PHY write data mismatch");
                    stmem[{bb, cc}] = x.data; n_stw++;
                end
            end
        end
    end

    // ---------------- (b) behavioural CDC hclk side on ci / co ----------------
    wr_t   wq [0:255];
    reg [7:0] ww = 0, wh = 0, wc = 0;              // written / handed off / completed
    reg    wc_p = 0;
    wr_t   ack_q [$];
    longint n_land = 0, n_ack = 0, n_hand = 0, cred_pend = 0;
    reg [31:0] rnd = 32'h1234567;
    wire   o_lv = co[O_co_h_lv], o_hand = co[O_co_h_hand], o_wcon = co[O_co_h_wcon], o_av = co[O_co_h_av];
    reg hand_pin = 0;
    always @(posedge hclk) if (!hrst) hand_pin <= 1'b0; else hand_pin <= o_hand;
    wire hand_cdc = HAND_PIPE != 0 ? hand_pin : o_hand;
    always @(posedge hclk) begin : cdc
        automatic reg [7:0] whn = wh + 8'(hand_cdc);
        automatic int give;
        rnd = {rnd[30:0], rnd[31] ^ rnd[21] ^ rnd[1] ^ rnd[0]};
        if (hand_cdc) begin
            if (wh == ww) bad("h_hand with an empty write queue");
            else begin exp_wr.push_back(wq[wh]); n_hand++; end
        end
        wh <= whn;
        ci[O_ci_h_wv] <= hrst && (whn != ww);
        ci[O_ci_h_wsec +: 24] <= wq[whn].sec;
        wc_p <= o_wcon;
        ci[O_ci_h_cv] <= wc_p;
        if (wc_p) begin
            if (wc == wh) bad("h_wcon with nothing handed off");
            ci[O_ci_h_csec +: 24] <= wq[wc].sec; ci[O_ci_h_cdata +: 256] <= wq[wc].data; ci[O_ci_h_ctag +: 9] <= wq[wc].tag;
            ack_q.push_back(wq[wc]); wc <= wc + 8'd1;
        end
        if (o_lv) begin
            n_land++; cred_pend++;
            if (exp_land.size() == 0) bad("landing with no RD outstanding");
            else begin
                automatic land_t e = exp_land.pop_front();
                if (co[O_co_h_lsec +: 17] !== e.sec) bad($sformatf("landing sector %h, expected %h", co[O_co_h_lsec +: 17], e.sec));
                if (co[O_co_h_lrow +: 8] !== e.row) bad("landing row");
                if (co[O_co_h_ldata +: 256] !== e.data) bad("landing data");
            end
        end
        give = (rnd[3:0] < 4'd11) ? ((cred_pend > 3) ? 3 : int'(cred_pend)) : 0;
        ci[O_ci_h_cred +: 3] <= 3'(give); cred_pend -= give;
        if (o_av) begin
            if(kv_write_column_cycle.size()==0)bad("write-done without physical WR column");
            else begin
                automatic longint column_cycle=kv_write_column_cycle.pop_front();
                if(cyc-column_cycle!=17)bad($sformatf("physical WR-to-retirement %0d edges expected17",cyc-column_cycle));
            end
            if (ack_q.size() == 0) bad("write-done with no completed write");
            else begin
                automatic wr_t x = ack_q.pop_front();
                if (co[O_co_h_atag +: 9] !== x.tag) bad("write-done tag");
            end
            n_ack++;
        end
    end

    // ---------------- embedding static port (core clock) ----------------
    longint n_er = 0, n_scr = 0, n_sent = 0;
    always @(posedge ck) begin
        if (er[O_er_e_v]) begin
            n_er++;
            if (exp_st.size() == 0) bad("static beat with no static RD outstanding");
            else begin
                automatic st_t s = exp_st.pop_front();
                if (er[O_er_e_data +: 256] !== s.data) bad("static beat data");
                if (er[O_er_e_ce] !== s.ce || er[O_er_e_ue] !== 1'b0) bad("static beat CE / UE flags");
            end
        end
        if (er[O_er_s_credit]) n_scr++;
        if (er[O_er_fault_core]) bad("fault_core");
    end
    task automatic st_cmd(input bit we, input [4:0] bank, input [4:0] col, input [255:0] d);
        automatic sw_t x;
        @(negedge ck);
        while (n_sent - n_scr >= 4) @(negedge ck);
        if (we) begin x.bc = {bank, col}; x.row = 19'(SROW); x.data = d; exp_sw.push_back(x); end
        es[O_es_s_v] = 1'b1; es[O_es_w_v] = we; es[O_es_s_we] = we; es[O_es_s_bank +: 5] = bank; es[O_es_s_col +: 5] = col;
        es[O_es_s_row +: 19] = 19'(SROW); es[O_es_w_d +: 256] = d;
        n_sent++;
        @(negedge ck); es = 288'd0;
    endtask

    // ---------------- stimulus ----------------
    integer nw = 0;
    task automatic kc_word(input [31:0] w);
        @(negedge hclk); ki = {w, 1'b1};
        @(negedge hclk); ki = 33'd0;
    endtask
    task automatic kv_write(input integer layer, input integer j);
        // posted in the hclk domain model of the CDC write queue
        @(negedge hclk);
        wq[ww].sec = {7'd0, 6'(layer), 3'(j >> 7), 1'b0, 7'(j)}; wq[ww].data = pat(100000 + nw * 3 + layer); wq[ww].tag = 9'(nw * 5 + 1);
        ww = ww + 8'd1; nw++;
    endtask
    integer L, k;
    longint hand0;
    initial begin
        repeat (8) @(negedge hclk);
        hrst = 1; @(negedge ck); rsi = 1;
        repeat (150) @(negedge hclk);
        // embedding boot writes, then reads (every second read carries a single-bit upset)
        for (k = 0; k < 3; k++) st_cmd(1'b1, 5'(k * 5 + 1), 5'(k * 3 + 2), pat(500000 + k));
        for (k = 0; k < 6; k++) st_cmd(1'b0, 5'((k % 3) * 5 + 1), 5'((k % 3) * 3 + 2), 256'd0);
        wait (n_er == 6 && n_stw == 3);
        for (L = 0; L < NL; L++) begin
            kc_word({2'd0, 10'd0, 6'(L), 14'd8192});                       // DESC
            for (k = 0; k < 5; k++) kv_write(L, (L * 131 + k * 257 + 3) % 1024);   // before GO
            repeat (40) @(negedge hclk);
            kc_word({2'd1, 30'd0});                                        // GO
            repeat (200) @(negedge hclk);
            for (k = 0; k < 4; k++) kv_write(L, (L * 71 + k * 311 + 900) % 1024);  // during the stream
            if (L == 1) st_cmd(1'b0, 5'd1, 5'd2, 256'd0);                  // a static read inside a stream
            wait (n_land == 1024 * (L + 1) && n_ack == nw);
            repeat (20) @(negedge hclk);
        end
        // a write posted for a layer whose descriptor has not been sent is held
        hand0 = n_hand;
        kv_write(NL, 77);
        repeat (400) @(negedge hclk);
        if (n_hand != hand0) bad("a write of a layer with no descriptor was handed off");
        kc_word({2'd0, 10'd0, 6'(NL), 14'd8192});
        wait (n_ack == nw);
        repeat (40) @(negedge hclk);
        if (fo !== 1'b0) bad("fault chain set");
        if (exp_land.size() != 0 || exp_wr.size() != 0 || exp_st.size() != 0 || exp_sw.size() != 0) bad("expectations left over");
        if (n_kvw != nw || n_stw != 3 || n_er != 7 || n_flip < 20 || n_land != 1024 * NL) bad("coverage floor");
        if (n_err == 0)
            $display("PASS static_controller_write_ABI pc=%0d: %0d actual hclk (diagnostic PROFILE only, no static schedule qualification) (%0d row, %0d column commands, %0d ACT); %0d sectors landed exact (%0d single-bit upsets corrected), %0d KV writes + %0d static writes exact at the PHY, %0d physical-column+17 write-dones, %0d static beats, late-layer write held",
                     PCI, n_cmp, n_rowc, n_colc, n_act, n_land, n_flip, n_kvw, n_stw, n_ack, n_er);
        else $fatal(1,"FAIL static_controller_write_ABI pc=%0d mut=%0d: %0d mismatches", PCI, MUT, n_err);
        $finish;
    end
    initial begin
        #2000000;
        $fatal(1,"FAIL static_controller_write_ABI pc=%0d mut=%0d: watchdog (landed %0d, acks %0d of %0d, static beats %0d, static writes %0d, hand-offs %0d, mismatches %0d)",
                 PCI, MUT, n_land, n_ack, nw, n_er, n_stw, n_hand, n_err);
        $finish;
    end
endmodule
