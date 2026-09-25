`timescale 1ns/1ps
// Stand-alone test of the weight streamer (rtl/hdc/hbm/ot_hdc_wstream.sv) on
// the timing-faithful HBM model (rtl/hdc/kv/ot_hdc_hbm_model.sv, per-channel
// ready).  The HBM holds a synthetic stream whose word n is a hash of n.  One
// op of +WORDS words is announced; the modelled engine then reads it:
//   +SET=0 (probe): a word as soon as the completion pointer passes it -- the
//           sustained supply of the streamer + HBM (words per cycle);
//   +SET=1 (unprovisioned): one word every cycle from the first w_ok with
//           +WRATE claiming more than the HBM delivers -- the underflow
//           detector must fire (fail closed);
//   +SET=2 (gated): one word every cycle from w_ok with the given +WLEAD and
//           +WRATE -- every word must arrive in time and match.
// Every delivered word is checked against the stream.
module tb_hdc_wstream #(
    parameter integer NPC = 4,
    parameter integer LWIN = 11,
    parameter integer CLK_PS = 1000
) (input wire clk);
    localparam integer AW = 24, NW = 16, WB = 1024, WS = 4, LENW = 5, BEATW = 4, TAGW = LWIN + 1;
    localparam integer HMEM = 1 << 20;
    reg rst_n = 1'b0, tok = 1'b0;
    reg wd_v = 1'b0;
    reg wrom_re = 1'b0;
    reg [AW-1:0] wrom_addr = 0;
    wire w_ok, emb_ok, fault;
    wire [3:0] why;
    wire [WB-1:0] wrom_q;
    localparam integer BF = 2, NB = BF * WS;
    wire [NB-1:0] we; wire [NB*LWIN-1:0] waddr; wire [BF*WB-1:0] wdata; wire [NB-1:0] re; wire [LWIN-1:0] raddr;
    reg  [BF*WB-1:0] q;
    reg  [255:0] win [0:NB-1][0:(1<<LWIN)/BF-1];
    wire hq_v, hq_rdy; wire [AW-1:0] hq_addr; wire [LENW-1:0] hq_len; wire [TAGW-1:0] hq_tag;
    wire [NPC-1:0] hr_v, hr_rdy, room; wire [NPC*TAGW-1:0] hr_tag; wire [NPC*BEATW-1:0] hr_beat;
    wire [NPC*256-1:0] hr_data;
    wire [31:0] fetched, consumed;
    reg [15:0] wrate, wlead;
    integer words, set;
    ot_hdc_wstream #(.WB(WB), .AW(AW), .HAW(AW), .NW(NW), .LWIN(LWIN), .NPC(NPC), .LENW(LENW), .BEATW(BEATW),
                     .EMBW(2)) u_ws (
        .clk(clk), .rst_n(rst_n), .cfg_base(24'd0), .cfg_ntot(words), .cfg_emb_base(24'd0), .cfg_emb_rom(24'd0),
        .cfg_lead(wlead), .cfg_rate(wrate), .tok_start(tok), .token(16'd0),
        .wd_v(wd_v), .wd_wbase(24'd0), .wd_tiles(words / (8 * 1024)), .wd_k(16'd1024), .w_ok(w_ok), .emb_ok(emb_ok),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_su(1'b0), .wrom_q(wrom_q),
        .win_we(we), .win_waddr(waddr), .win_wdata(wdata), .win_re(re), .win_raddr(raddr), .win_q(q),
        .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_addr(hq_addr), .hq_len(hq_len), .hq_tag(hq_tag), .hq_room(room),
        .hr_v(hr_v), .hr_rdy(hr_rdy), .hr_tag(hr_tag), .hr_beat(hr_beat), .hr_data(hr_data),
        .fault(fault), .fault_why(why), .st_fetched(fetched), .st_consumed(consumed));
    ot_hdc_hbm_model #(.NPC(NPC), .AW(AW), .DW(256), .MEM_WORDS(HMEM), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW),
                       .CLK_PS(CLK_PS), .PC_RDY(1), .PC_ROOM(2 * WS)) u_hbm (
        .clk(clk), .rst_n(rst_n), .req_v(hq_v), .req_rdy(hq_rdy), .pc_room(room), .req_we(1'b0), .req_addr(hq_addr),
        .req_len(hq_len), .req_tag(hq_tag), .req_wdata(256'd0),
        .rsp_v(hr_v), .rsp_rdy(hr_rdy), .rsp_tag(hr_tag), .rsp_beat(hr_beat), .rsp_data(hr_data));
    integer b;
    always @(posedge clk) begin
        for (b = 0; b < NB; b = b + 1) begin
            if (re[b]) q[b*256 +: 256] <= win[b][raddr / BF];
            if (we[b]) win[b][waddr[b*LWIN +: LWIN] / BF] <= wdata[b*256 +: 256];
        end
    end
    function automatic [255:0] sector(input integer s);
        sector = {8{s * 32'h9E3779B1 + 32'h7F4A7C15}};
    endfunction
    integer n_iss = 0, rsp_wait = 0, req_idle = 0, pc;
    integer i, cyc = 0, t_ok = 0, t_first = 0, bad = 0, got = 0;
    reg run = 1'b0, chk = 1'b0; reg [AW-1:0] chk_a;
    initial begin
        if (!$value$plusargs("SET=%d", set)) set = 0;
        if (!$value$plusargs("WORDS=%d", words)) words = 65536;
        if (!$value$plusargs("WRATE=%d", wrate)) wrate = 0;
        if (!$value$plusargs("WLEAD=%d", wlead)) wlead = 512;
        for (i = 0; i < words * WS && i < HMEM; i = i + 1) u_hbm.mem[i] = sector(i);
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1'b1;
        tok <= (cyc == 10);
        wd_v <= (cyc == 12);
        chk <= wrom_re; chk_a <= wrom_addr;
        for (pc = 0; pc < NPC; pc = pc + 1) if (hr_v[pc] && !hr_rdy[pc]) rsp_wait = rsp_wait + 1;
        if (run && !hq_v) req_idle = req_idle + 1;
        if (chk) begin
            got = got + 1;
            for (b = 0; b < WS; b = b + 1) if (wrom_q[b*256 +: 256] !== sector(chk_a * WS + b)) bad = bad + 1;
        end
        wrom_re <= 1'b0;
        if (cyc > 20 && !run && (set == 0 || w_ok)) begin run <= 1'b1; t_ok = cyc; end
        if (run && n_iss < words && !fault && (set == 0 ? (u_ws.cp > n_iss) : 1'b1)) begin
            wrom_re <= 1'b1; wrom_addr <= n_iss; n_iss = n_iss + 1;
            if (t_first == 0) t_first = cyc;
        end
        if ((got == words && got > 0) || fault || cyc > 50000000) begin
            $display("WSTREAM_UNIT set=%0d npc=%0d words=%0d delivered=%0d mismatches=%0d fault=%0d why=%0d start_wait=%0d cycles=%0d words_per_cycle_x1000=%0d refreshes=%0d",
                     set, NPC, words, got, bad, fault, why, t_ok - 12, cyc - t_first, (got * 1000) / (cyc - t_first + 1),
                     u_hbm.st_ref[0]);
            $display("WSTREAM_DIAG rsp_wait=%0d req_idle=%0d", rsp_wait, req_idle);
            if (set == 1) $display(fault && why[0] ? "FAULT_DETECTED" : "FAIL");
            else $display(!fault && bad == 0 && got == words ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
