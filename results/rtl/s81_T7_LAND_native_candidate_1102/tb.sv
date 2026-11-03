`timescale 1ps/1ps
// T7 LAND native gate: unchanged native 4c805 helper + verbatim rowword/kc_w + ekv_w capture (reference) versus the
// 12-SRAM + LVT candidate, all 1060 raw bits compared on EVERY edge (valid or not), 833 ps clock.
module tb;
reg clk = 0; always begin #416 clk = 1; #417 clk = 0; end
reg  [223:0]  WR_ADDR = 0; reg [1791:0] WR_DATA = 0, WR_EN = 0;
reg  [9:0]    rc = 0, tjob = 0; reg [7:0] wcount = 0; reg [20:0] wfirst = 0; reg [1023:0] wsc = 0;
reg  [511:0]  sel_held = 0; reg [3:0] tile = 0; reg [1:0] st_r = 0; reg [639:0] pres = 0; reg [3:0] spres = 0;
wire [127:0]  RD_ADDR; wire [1023:0] RD_DATA; wire [1059:0] gold; wire [3:0] gold_m;
ot_bind_native_4c805a5536bda0930879099e mem (.RD_ADDR(RD_ADDR), .RD_DATA(RD_DATA), .WR_ADDR(WR_ADDR),
    .WR_CLK({7{clk}}), .WR_DATA(WR_DATA), .WR_EN(WR_EN));
land_reference ref0 (.clk(clk), .rc(rc), .tjob(tjob), .wcount(wcount), .wfirst(wfirst), .wsc(wsc), .sel_held(sel_held),
    .tile(tile), .st_r(st_r), .pres(pres), .spres(spres), .RD_DATA(RD_DATA), .RD_ADDR(RD_ADDR), .ekv_w(gold), .ekv_m(gold_m));
// need per lane: the parent's unchanged expression (dsdv_svc_att.sv:476), fed to the cut
// valid/window/scale per lane: the parent's unchanged compares/shifter (dsdv_svc_att.sv:471, 437-439)
reg [3:0] need, valid, win; reg [31:0] scale; integer jn; reg [31:0] rown; reg [6:0] sln;
always @(*) begin
    need = 0; valid = 0; win = 0; scale = 0;
    for (jn = 0; jn < 4; jn = jn + 1) begin
        rown = 4 * (32'(rc) - 1) + jn;
        need[jn] = (rown < 32'(wcount)) || sel_held[rown - 32'(wcount)] || tile[3:2] == st_r;
        valid[jn] = rown < 32'(tjob);
        win[jn] = rown < 32'(wcount);
        sln = 7'(wfirst[6:0] + 7'(rown));
        scale[8*jn +: 8] = wsc[8*sln +: 8];
    end
end
wire [1059:0] cq [0:5];
land_sram_candidate #(.MUT(0)) c0 (clk, WR_ADDR, WR_DATA, WR_EN, rc, valid, win, need, scale, cq[0]);
land_sram_candidate #(.MUT(1)) c1 (clk, WR_ADDR, WR_DATA, WR_EN, rc, valid, win, need, scale, cq[1]);
land_sram_candidate #(.MUT(2)) c2 (clk, WR_ADDR, WR_DATA, WR_EN, rc, valid, win, need, scale, cq[2]);
land_sram_candidate #(.MUT(3)) c3 (clk, WR_ADDR, WR_DATA, WR_EN, rc, valid, win, need, scale, cq[3]);
land_sram_candidate #(.MUT(4)) c4 (clk, WR_ADDR, WR_DATA, WR_EN, rc, valid, win, need, scale, cq[4]);
land_sram_candidate #(.MUT(5)) c5 (clk, WR_ADDR, WR_DATA, WR_EN, rc, valid, win, need, scale, cq[5]);
integer mutant = 0;
wire [1059:0] observed = cq[mutant];

reg [31:0] rng = 32'h5a17c0de;
function automatic [31:0] nx(input [31:0] v); nx = v ^ (v << 13); nx = nx ^ (nx >> 17); nx = nx ^ (nx << 5); endfunction
task automatic rnd(output [31:0] v); begin rng = nx(rng); v = rng; end endtask
// one write on channel ch (0 PC0, 1 PC1, 2 ROWS) to row r; kind 0 window/type0 (PCs, r<256), 1 beat0, 2 beat1
task automatic put(input integer ch, input integer kind, input [9:0] r);
    integer s, k; reg [31:0] v; reg [255:0] d;
    begin
        for (k = 0; k < 8; k = k + 1) begin rnd(v); d[32*k +: 32] = v; end
        if (ch == 2) s = 6; else s = 3 * ch + kind;
        if (s != 0 && s != 3) d[255:144] = 0;                   // compressed / ROWS: literal zero112 + 144 bits
        WR_EN[256*s +: 256] = {256{1'b1}};
        WR_DATA[256*s +: 256] = d;
        if (s == 0 || s == 3) WR_ADDR[32*s +: 32] = {24'd0, r[7:0]};
        else if (s == 6)      WR_ADDR[32*s +: 32] = {22'd0, r};
        else begin            WR_ADDR[32*(3*ch+1) +: 32] = {22'd0, r}; WR_ADDR[32*(3*ch+2) +: 32] = {22'd0, r}; end
    end
endtask
// contract monitor: replicated masks, within-PC exclusion
integer cs; reg [2:0] pc0, pc1;
always @(negedge clk) #300 begin
    for (cs = 0; cs < 7; cs = cs + 1)
        if (WR_EN[256*cs +: 256] != 0 && WR_EN[256*cs +: 256] != {256{1'b1}}) begin $display("LAND_CONTRACT_FAIL mask slot %0d", cs); $fatal(1); end
    pc0 = {WR_EN[512], WR_EN[256], WR_EN[0]}; pc1 = {WR_EN[1280], WR_EN[1024], WR_EN[768]};
    if ((pc0 & (pc0 - 1)) != 0 || (pc1 & (pc1 - 1)) != 0) begin $display("LAND_CONTRACT_FAIL pc exclusion"); $fatal(1); end
end

integer i, j, k, ch, kind, pat; reg [31:0] v, w; reg [9:0] base, r3 [0:2];
integer n_wr [0:2]; integer seeded_rows = 0, samebank3 = 0, samebank2 = 0, sameaddr = 0, rdwr_coll = 0, oor_wr = 0,
        big_tjob = 0, lane_win = 0, lane_need = 0, lane_ign = 0, lane_inv = 0, hist_mix = 0, wsc_live = 0, rc0 = 0;
reg [1:0] wr_of [0:639]; reg written [0:639];
reg [9:0] rr; reg [9:0] rows [0:2]; reg en3 [0:2];
initial begin
    void'($value$plusargs("mutant=%d", mutant));
    n_wr[0] = 0; n_wr[1] = 0; n_wr[2] = 0;
    for (k = 0; k < 640; k = k + 1) begin written[k] = 0; wr_of[k] = 0; end
    for (i = 0; i < 4096; i = i + 1) begin
        @(negedge clk);
        WR_EN = 0; WR_ADDR = 0; WR_DATA = 0;
        for (k = 0; k < 3; k = k + 1) en3[k] = 0;
        if (i < 214) begin
            // seeding: every logical row through the real write channels, all three writers, both slot kinds
            for (ch = 0; ch < 3; ch = ch + 1) begin
                rr = 10'(3 * i + ch);
                if (3 * i + ch < 640) begin
                    kind = (ch == 2) ? 0 : (rr < 256 && (i % 3) == 0) ? 0 : 1 + (i % 2);
                    put(ch, kind, rr); en3[ch] = 1; rows[ch] = rr;
                end
            end
            rc = 0; tjob = 0;
        end else begin
            // program-like read cursor with restarts, live job/window facts
            rnd(v);
            if (v % 97 == 0) rc = 0; else if (v % 89 == 1) rc = 10'(v % 200); else rc = rc + 10'd1;
            if (rc > 175 && v % 5 == 0) rc = 0;
            rnd(v); if (v % 13 == 0) tjob = 10'(641 + v % 383); else if (v % 7 == 0) tjob = 10'(v % 641); else if (tjob > 640) tjob = 640;
            rnd(v); if (v % 5 == 0) wcount = v[15:8];
            rnd(v); if (v % 6 == 0) wfirst = v[20:0];
            rnd(v); if (v % 2 == 0) begin for (k = 0; k < 32; k = k + 1) begin rnd(w); wsc[32*k +: 32] = w; end wsc_live++; end
            rnd(v); if (v % 3 == 0) for (k = 0; k < 16; k = k + 1) begin rnd(w); sel_held[32*k +: 32] = w; end
            rnd(v); tile = v[3:0]; st_r = v[5:4];
            rnd(v); pat = v % 8; rnd(w); base = 10'(w % 640);
            for (ch = 0; ch < 3; ch = ch + 1) begin
                rnd(v);
                case (pat)
                    0: rows[ch] = 10'((base & 10'h3fc) + 4 * ch + base[1:0]);                 // same bank, different rows
                    1: rows[ch] = base;                                                     // same row, all writers
                    2: rows[ch] = 10'(4 * (32'(rc) - 0) + v % 4);                           // rows read next edge
                    3: rows[ch] = 10'(4 * (32'(rc) - 1) + v % 4);                           // rows read THIS edge
                    4: rows[ch] = 10'(v % 1024);                                            // incl. out of range
                    default: rows[ch] = 10'(v % 640);
                endcase
                rnd(w);
                en3[ch] = (pat <= 1) ? (w % 8 != 0) : (w % 3 != 0);
                if (en3[ch]) begin
                    rnd(w);
                    kind = (ch == 2) ? 0 : (rows[ch] < 256 && w % 3 == 0) ? 0 : 1 + w % 2;
                    put(ch, kind, rows[ch]);
                end
            end
        end
        // statistics (pre-edge)
        for (ch = 0; ch < 3; ch = ch + 1) if (en3[ch]) begin n_wr[ch]++; if (rows[ch] >= 640) oor_wr++; end
        if (en3[0] && en3[1] && en3[2] && rows[0][1:0] == rows[1][1:0] && rows[1][1:0] == rows[2][1:0] &&
            rows[0] != rows[1] && rows[1] != rows[2] && rows[0] != rows[2]) samebank3++;
        for (ch = 0; ch < 3; ch = ch + 1) for (k = ch + 1; k < 3; k = k + 1)
            if (en3[ch] && en3[k] && rows[ch] != rows[k] && rows[ch][1:0] == rows[k][1:0]) samebank2++;
        for (ch = 0; ch < 3; ch = ch + 1) for (k = ch + 1; k < 3; k = k + 1) if (en3[ch] && en3[k] && rows[ch] == rows[k]) sameaddr++;
        if (tjob > 640) big_tjob++;
        if (rc == 0) rc0++;
        for (j = 0; j < 4; j = j + 1) begin
            rown = 4 * (32'(rc) - 1) + j;
            for (ch = 0; ch < 3; ch = ch + 1) if (en3[ch] && 32'(rows[ch]) == rown && rown < 32'(tjob)) rdwr_coll++;
            if (!(rown < 32'(tjob))) lane_inv++;
            else if (rown < 32'(wcount)) lane_win++;
            else if (need[j]) lane_need++;
            else lane_ign++;
            if (rown < 640 && rown < 32'(tjob) && written[rown] && wr_of[rown] != 0) hist_mix++;
        end
        for (ch = 0; ch < 3; ch = ch + 1) if (en3[ch] && rows[ch] < 640) begin
            if (!written[rows[ch]]) seeded_rows++;
            written[rows[ch]] = 1; wr_of[rows[ch]] = 2'(ch);
        end
        @(posedge clk); #2;
        if (gold !== observed) begin
            $display("LAND_NATIVE_FAIL mutant=%0d edge=%0d rc=%0d tjob=%0d wcount=%0d", mutant, i, rc, tjob, wcount);
            for (j = 0; j < 4; j = j + 1) if (gold[265*j +: 265] !== observed[265*j +: 265])
                $display("  lane%0d gold=%h obs=%h", j, gold[265*j +: 265], observed[265*j +: 265]);
            $fatal(1);
        end
    end
    $display("LAND_NATIVE_PASS edges=4096 rows_seeded=%0d writes_pc0=%0d writes_pc1=%0d writes_rows=%0d samebank3=%0d samebank2=%0d sameaddr=%0d rdwr_collisions=%0d oor_writes=%0d tjob_gt640_edges=%0d rc0_edges=%0d lanes_window=%0d lanes_need=%0d lanes_ignored=%0d lanes_invalid=%0d lanes_nonzero_writer=%0d wsc_changes=%0d",
        seeded_rows, n_wr[0], n_wr[1], n_wr[2], samebank3, samebank2, sameaddr, rdwr_coll, oor_wr, big_tjob, rc0,
        lane_win, lane_need, lane_ign, lane_inv, hist_mix, wsc_live);
    $finish;
end
endmodule
