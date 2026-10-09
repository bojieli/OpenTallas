`timescale 1ns/1ps
// Exact gate of ot_s81_cfg7_seq (CLAUDE S81-DIE, 2026-10-06): cycle lockstep against the reference loader
// ot_v41_pair_pq_ld_frontend (PHW 10, PQ 0, combinational payload read) with the sequencer driving SEVEN functional
// ot_rom_4096x72_m8 models (via-array content = the reference payload, linear word g -> macro g/4096, row g%4096).
// Every one of the 1,024 phases is loaded and checked (25,600 words), then 4,000 pseudo-random cycles of broadcasts,
// go, overlapping loads and resets.  Any mismatch is $fatal (nonzero exit).  Negative controls:
// +define+OT_S81_CFG7_MUT_BANK (unregistered bank select) and +define+OT_S81_CFG7_MUT_STRIDE (wrong phase stride) must FAIL.
// PQ = 1 (s81-die-2 2026-10-08): the same lockstep against the frontend at PQ 1 with the element's ef = {bank_free,
// sh_free} driven: 256 held loads (ef low 1..40 cycles after the broadcast) and random ef in the random section; go_tag
// checked at every broadcast go against the PQ spine's tag (ot_v41_spine_pq_w17w10 bt_tag = ist: +1 per go broadcast
// from 0 at reset).  Extra negative controls at PQ 1: OT_S81_CFG7_MUT_TAG, OT_S81_CFG7_MUT_NOFAULT, OT_S81_CFG7_MUT_NOHOLD.
module tb_ot_s81_cfg7_seq;
    parameter integer PQ = 0;
    localparam integer PHW = 10, CW = 25, NW = CW << PHW;
    reg clk = 0;
    always #0.416667 clk = ~clk;
    reg rst_n = 0, cfg_go = 0, go = 0;
    reg [PHW-1:0] phase = 0;
    reg [2:0] np = 0;
    reg [1:0] ef = 2'b11;
    reg [47:0] payload [0:NW-1];
    function automatic [47:0] word_at(input integer g);
        reg [47:0] w;
        begin
            w = {16'(g ^ 16'hb51d), 16'(g * 37 + 19), 16'(g * 73 + 7)};
            if (g % 25 >= 8 && g % 25 < 16) w[0] = (g / 25) % 3 != 0;   // class-valid bits: some phases inactive
            word_at = w;
        end
    endfunction
    // reference
    wire [14:0] cm_a;
    wire rv, rge, rbusy, rfault;
    wire [4:0] ra;
    wire [47:0] rd;
    ot_v41_pair_pq_ld_frontend #(.PHW(PHW), .PQ(PQ)) ref_ld (
        .clk(clk), .rst_n(rst_n), .cfg_go(cfg_go), .cfg_ph(phase), .cfg_np(np), .go(go), .e_sh_free(ef[0]),
        .e_bank_free(ef[1]), .cm_a(cm_a), .cm_q(payload[cm_a]), .c_v(rv), .c_a(ra), .c_d(rd), .go_e(rge),
        .ld_busy(rbusy), .fault(rfault));
    // DUT + seven real-macro functional models
    wire [11:0] a;
    wire [6:0] ce;
    wire [71:0] q [0:6];
    wire [53:0] cfg;
    wire ge;
    wire [1:0] st, gtag;
    ot_s81_cfg7_seq #(.PQ(PQ)) dut (.clk(clk), .rst_n(rst_n), .lc({np, phase, cfg_go, go}), .a(a),
        .ce0(ce[0]), .ce1(ce[1]), .ce2(ce[2]), .ce3(ce[3]), .ce4(ce[4]), .ce5(ce[5]), .ce6(ce[6]),
        .q0(q[0][47:0]), .q1(q[1][47:0]), .q2(q[2][47:0]), .q3(q[3][47:0]), .q4(q[4][47:0]), .q5(q[5][47:0]),
        .q6(q[6][47:0]), .cfg(cfg), .go_e(ge), .st(st), .ef(ef), .go_tag(gtag));
    // the PQ spine's op tag (bt_tag = ist): +1 per go broadcast, 0 at reset
    reg [1:0] stag = 0;
    integer tags = 0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) stag <= 2'd0;
        else if (go) begin
            if (gtag !== (PQ != 0 ? stag : 2'd0)) $fatal(1, "go_tag %0d, spine tag %0d", gtag, stag);
            tags++;
            stag <= stag + 2'd1;
        end
    genvar j;
    generate for (j = 0; j < 7; j = j + 1) begin : g_rom
        ot_rom_4096x72_m8 u_rom (.clk(clk), .ce_in(ce[j]), .addr_in(a), .rd_out(q[j]));
    end endgenerate
    integer checks = 0, words = 0, reads = 0, admits = 0, multi_ce = 0;
    always @(posedge clk) begin
        if (rst_n && |ce) begin
            reads++;
            if ((ce & (ce - 7'd1)) != 0) multi_ce++;
        end
        #0.001;
        if (rst_n) begin
            checks++;
            if ({cfg[53], ge, st[0], st[1]} !== {rv, rge, rbusy, rfault})
                $fatal(1, "control mismatch check %0d: dut v/go/busy/fault %b%b%b%b ref %b%b%b%b", checks, cfg[53], ge,
                       st[0], st[1], rv, rge, rbusy, rfault);
            if (rv) begin
                if ({cfg[4:0], cfg[52:5]} !== {ra, rd})
                    $fatal(1, "word mismatch check %0d: dut a%0d %h ref a%0d %h", checks, cfg[4:0], cfg[52:5], ra, rd);
                words++;
            end
            if (rge) admits++;
        end else if (cfg[53] || ge || st != 0)
            $fatal(1, "reset mismatch");
    end
    task automatic tick;
        @(negedge clk);
    endtask
    reg [31:0] rng = 32'h725ace19;
    integer g, b, oldr;
    initial begin
        for (g = 0; g < NW; g++) payload[g] = word_at(g);
        #0.001;
        for (g = 0; g < NW; g++)
            for (b = 0; b < 48; b++)
                case (g / 4096)
                    0: g_rom[0].u_rom.arr[(g % 4096) / 8][b * 8 + g % 8] = (payload[g] >> b) & 1;
                    1: g_rom[1].u_rom.arr[(g % 4096) / 8][b * 8 + g % 8] = (payload[g] >> b) & 1;
                    2: g_rom[2].u_rom.arr[(g % 4096) / 8][b * 8 + g % 8] = (payload[g] >> b) & 1;
                    3: g_rom[3].u_rom.arr[(g % 4096) / 8][b * 8 + g % 8] = (payload[g] >> b) & 1;
                    4: g_rom[4].u_rom.arr[(g % 4096) / 8][b * 8 + g % 8] = (payload[g] >> b) & 1;
                    5: g_rom[5].u_rom.arr[(g % 4096) / 8][b * 8 + g % 8] = (payload[g] >> b) & 1;
                    default: g_rom[6].u_rom.arr[(g % 4096) / 8][b * 8 + g % 8] = (payload[g] >> b) & 1;
                endcase
        repeat (3) tick(); rst_n = 1;
        for (int ph = 0; ph < (1 << PHW); ph++) begin
            oldr = reads;
            phase = PHW'(ph); np = 3'(ph); cfg_go = 1; tick(); cfg_go = 0;
            repeat (29) tick();
            if (reads - oldr != CW) $fatal(1, "phase %0d: %0d macro reads, expected %0d", ph, reads - oldr, CW);
            go = 1; tick(); go = 0; tick();
        end
        if (words != NW) $fatal(1, "full extent not consumed: %0d words", words);
        if (PQ != 0)
            for (int h = 0; h < 256; h++) begin       // held loads: ef low 1..40 cycles after the broadcast
                oldr = reads;
                phase = PHW'(h * 5 + 3); np = 3'(h); ef = 2'(h % 3); cfg_go = 1; tick(); cfg_go = 0;
                repeat (1 + (h * 7) % 40) tick();
                ef = 2'b11;
                repeat (30) tick();
                if (reads - oldr != CW) $fatal(1, "held load %0d: %0d macro reads, expected %0d", h, reads - oldr, CW);
                go = 1; tick(); go = 0; tick();
            end
        for (int n = 0; n < 4000; n++) begin
            rng = {rng[30:0], rng[31] ^ rng[21] ^ rng[1] ^ rng[0]};
            rst_n = (n % 311 != 0); phase = rng[PHW-1:0]; np = rng[12:10];
            cfg_go = (n == 4 || n == 7 || rng[16:13] == 0);
            go = (n == 11 || rng[19:17] == 0);
            ef = (PQ != 0) ? {rng[22:21] != 0, rng[24:23] != 0} : 2'b11;
            tick();
        end
        rst_n = 1; cfg_go = 0; go = 0; ef = 2'b11; repeat (35) tick();
        if (multi_ce != 0) $fatal(1, "%0d cycles with more than one macro enabled", multi_ce);
        if (admits == 0) $fatal(1, "go_e never admitted");
        $display("PASS ot_s81_cfg7_seq lockstep vs ot_v41_pair_pq_ld_frontend PHW10 PQ%0d: checks=%0d words=%0d reads=%0d go_e=%0d tags=%0d phases=%0d x %0d words, 7 real-macro models",
                 PQ, checks, words, reads, admits, tags, 1 << PHW, CW);
        $finish;
    end
endmodule
