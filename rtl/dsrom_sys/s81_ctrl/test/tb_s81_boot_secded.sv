`timescale 1ns/1ps
// tb_s81_boot_secded (stream ds-control, 2026-10-08): (c) the RoPE boot load and (d) the HBM / SRAM SECDED of the S81
// die.  The die-face stream is exactly what dsfd_host (ot_rom_host_ingest, RAW descriptors + the BOOT_END CSR) emits
// on its die face: RAW sectors {o_we 1, o_addr = 1<<31 | E, o_d} in E order, then the marker {o_addr all ones,
// o_d[63:0] = {checksum, expected}} (that block's own bench, rtl/test/tb_rom_host_ingest.sv, proves the RAW -> die face
// path); credits as its OCRED.  Image: tools/s81_ctrl/rope_boot_image.py (the golden's cos/sin, both tables, the top
// MAX_POS positions of the 1M context), interleaved with KV-ingest sectors (o_addr[31] = 0) that must pass through.
//   phase 1 BOOT: boot_seq -> 4 x ot_s81_hbm_secded_wr -> HBM model {data, ECC side-band}; boot_ok must rise.
//   phase 2 READ: every table sector read back through ot_s81_hbm_secded_rd at the ot_chip_v41x_rope_hbm_cache
//           address (stack s, base + 2*pos + j) and compared bit-exact with the golden image; NFLIP1 sectors carry an
//           injected single-bit error (must be corrected, data exact, ce), NFLIP2 a double-bit error in one 72-bit
//           word (ue, fault latched).
//   phase 3 SRAM: ot_s81_sram_secded (512 b x 64): every single-bit position of a row (576) corrected, every
//           double-bit pair of one 72-bit word (2,556) detected, clean rows clean.
//   +badsum: the marker carries a wrong checksum -> fault 2, boot_ok stays 0 (PASS means that);
//   +short:  one table sector is missing -> fault 2 (count), boot_ok 0.
// MUT=1 (decoder never corrects) / MUT=2 (encoder drops the overall parity): must FAIL.
module tb_s81_boot_secded;
    parameter integer MAX_POS = 64, MUT = 0, NFLIP1 = 40, NFLIP2 = 6;
    localparam integer HAW = 20, NS = 16 * MAX_POS;
    reg ck = 0, rst_n = 0;
    always #0.4166 ck = ~ck;
    reg [255:0] img [0:NS-1];
    reg  i_v = 0, i_we = 0; reg [31:0] i_addr = 0; reg [255:0] i_d = 0; wire i_cr;
    wire kv_v, kv_we; wire [30:0] kv_a; wire [255:0] kv_d;
    reg [4*HAW-1:0] plain_base, yarn_base;
    wire [3:0] w_v; wire [4*HAW-1:0] w_a; wire [4*256-1:0] w_d; wire [1:0] tp; wire boot_ok, bfault; wire [3:0] bfc;
    wire [31:0] st_sec, st_mk;
    ot_s81_boot_seq #(.HAW(HAW), .MAX_POS(MAX_POS), .E0(0), .NEED(2'b11), .OCRED(8)) u_boot (
        .ck(ck), .rst_n(rst_n), .i_v(i_v), .i_we(i_we), .i_addr(i_addr), .i_d(i_d), .i_cr(i_cr),
        .kv_v(kv_v), .kv_we(kv_we), .kv_a(kv_a), .kv_d(kv_d), .kv_rdy(1'b1),
        .plain_base(plain_base), .yarn_base(yarn_base), .w_v(w_v), .w_a(w_a), .w_d(w_d), .w_rdy(4'hF),
        .table_present(tp), .boot_ok(boot_ok), .fault(bfault), .fault_code(bfc), .st_sectors(st_sec), .st_markers(st_mk));
    // per-stack write encoders and the HBM model (associative)
    wire [3:0] e_v; wire [4*HAW-1:0] e_a; wire [4*256-1:0] e_d; wire [4*32-1:0] e_e;
    reg [287:0] hbm [0:3][int];
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_s
        ot_s81_hbm_secded_wr #(.AW(HAW), .MUT(MUT)) u_w (.clk(ck), .rst_n(rst_n), .i_v(w_v[g]), .i_a(w_a[g*HAW +: HAW]),
            .i_d(w_d[g*256 +: 256]), .o_v(e_v[g]), .o_a(e_a[g*HAW +: HAW]), .o_d(e_d[g*256 +: 256]), .o_e(e_e[g*32 +: 32]));
        always @(posedge ck) if (e_v[g]) hbm[g][int'(e_a[g*HAW +: HAW])] = {e_e[g*32 +: 32], e_d[g*256 +: 256]};
    end endgenerate
    // read decoder (one, shared by the bench)
    reg  r_v = 0; reg [19:0] r_t = 0; reg [255:0] r_d = 0; reg [31:0] r_e = 0;
    wire o_v, o_ce, o_ue, r_fault; wire [19:0] o_t; wire [255:0] o_d; wire [31:0] st_ce, st_ue;
    ot_s81_hbm_secded_rd #(.TW(20), .MUT(MUT)) u_r (.clk(ck), .rst_n(rst_n), .i_v(r_v), .i_t(r_t), .i_d(r_d), .i_e(r_e),
        .o_v(o_v), .o_t(o_t), .o_d(o_d), .o_ce(o_ce), .o_ue(o_ue), .fault(r_fault), .st_ce(st_ce), .st_ue(st_ue));
    // SRAM wrapper
    reg s_we = 0, s_re = 0, inj_v = 0; reg [5:0] s_wa = 0, s_ra = 0, inj_a = 0; reg [511:0] s_wd = 0; reg [575:0] inj_m = 0;
    wire s_rv, s_ce, s_ue, s_f; wire [511:0] s_rd; wire [31:0] s_cec, s_uec;
    ot_s81_sram_secded #(.W(512), .DEPTH(64), .MUT(MUT)) u_sram (.clk(ck), .rst_n(rst_n), .we(s_we), .wa(s_wa), .wd(s_wd),
        .re(s_re), .ra(s_ra), .rv(s_rv), .rd(s_rd), .ce(s_ce), .ue(s_ue), .fault(s_f), .st_ce(s_cec), .st_ue(s_uec),
        .inj_v(inj_v), .inj_a(inj_a), .inj_m(inj_m));

    integer n, i, j, k, s, pos, kind, cred, err = 0, kvn = 0, kvbad = 0, flip1 = 0, flip2 = 0, ce_n = 0, ue_n = 0, ok_n = 0;
    integer sram_err = 0, sram_ce = 0, sram_ue = 0, badsum = 0, shrt = 0;
    reg [31:0] csum; integer nsec, top;
    string imgf, metaf;
    integer fd;
    always @(posedge ck) if (kv_v) begin kvn = kvn + 1; if (kv_a != 31'(1000 + kvn - 1) || kv_d != {8{32'(kvn - 1)}}) kvbad = kvbad + 1; end
    task automatic send(input we, input [31:0] a, input [255:0] d);
        begin
            while (cred == 0) @(negedge ck);
            i_v = 1; i_we = we; i_addr = a; i_d = d; cred = cred - 1;
            @(negedge ck); i_v = 0;
        end
    endtask
    always @(negedge ck) if (i_cr) cred = cred + 1;
    function automatic [HAW-1:0] haddr(input integer kd, input integer st, input integer p, input integer jj);
        haddr = (kd ? yarn_base[st*HAW +: HAW] : plain_base[st*HAW +: HAW]) + 2 * p + jj;
    endfunction
    initial begin
        if (!$value$plusargs("img=%s", imgf)) $fatal(1, "+img");
        if (!$value$plusargs("meta=%s", metaf)) $fatal(1, "+meta");
        $readmemh(imgf, img);
        fd = $fopen(metaf, "r"); void'($fscanf(fd, "%d %h %d", nsec, csum, top)); $fclose(fd);
        if (nsec != NS) $fatal(1, "image size");
        if ($test$plusargs("badsum")) badsum = 1;
        if ($test$plusargs("short")) shrt = 1;
        for (s = 0; s < 4; s = s + 1) begin plain_base[s*HAW +: HAW] = 20'h01000 + s * 20'h40; yarn_base[s*HAW +: HAW] = 20'h08000 + s * 20'h40; end
        cred = 8;
        repeat (4) @(posedge ck); rst_n = 1; @(negedge ck);
        // phase 1: boot stream, KV-ingest sectors interleaved every 37 sectors
        for (i = 0; i < NS; i = i + 1) begin
            if (i % 37 == 5) send(1, 32'(1000 + i / 37), {8{32'(i / 37)}});
            if (!(shrt && i == 77)) send(1, {1'b1, 31'(i)}, img[i]);
        end
        send(1, 32'hFFFF_FFFF, {192'd0, badsum ? csum ^ 32'h1 : csum, 32'(shrt ? NS - 1 : NS)});
        repeat (20) @(posedge ck);
        if (badsum || shrt) begin
            $display("TB_S81_BOOT_SECDED neg=%s boot_ok=%0d fault=%0d code=%0d %s", badsum ? "badsum" : "short", boot_ok, bfault, bfc,
                     (!boot_ok && bfault && bfc == (shrt ? 1 : 2) && tp == 0) ? "PASS" : "FAIL");
            $finish;
        end
        // phase 2: inject errors into the stored copy, read every table sector back through the decoder
        for (i = 0; i < NS; i = i + 1) begin : rd
            reg [287:0] c; integer st2, jj, p2, kd;
            kd = i / (8 * MAX_POS); p2 = (i / 8) % MAX_POS; st2 = (i / 2) % 4; jj = i % 2;
            c = hbm[st2][int'(haddr(kd, st2, p2, jj))];
            if (i % 23 == 3 && flip1 < NFLIP1) begin c[(i * 7) % 288] = ~c[(i * 7) % 288]; flip1 = flip1 + 1; end
            else if (i % 97 == 11 && flip2 < NFLIP2) begin
                // two data bits of one 72-bit word: word w = i % 4, data bits 64w + a, 64w + b
                c[64 * (i % 4) + 5] = ~c[64 * (i % 4) + 5]; c[64 * (i % 4) + 40] = ~c[64 * (i % 4) + 40]; flip2 = flip2 + 1;
            end
            @(negedge ck); r_v = 1; r_t = 20'(i); r_d = c[255:0]; r_e = c[287:256];
        end
        @(negedge ck); r_v = 0;
        repeat (5) @(posedge ck);
        // phase 3: SRAM wrapper
        for (i = 0; i < 64; i = i + 1) begin @(negedge ck); s_we = 1; s_wa = i; s_wd = {16{32'(i * 2654435761)}}; end
        @(negedge ck); s_we = 0;
        for (k = 0; k < 576; k = k + 1) begin            // every single-bit position of row 7
            @(negedge ck); inj_v = 1; inj_a = 7; inj_m = 576'd1 << k;
            @(negedge ck); inj_v = 0; s_re = 1; s_ra = 7;
            @(negedge ck); s_re = 0; @(posedge ck); #0.1;
            if (!s_rv || s_rd != {16{32'(7 * 2654435761)}} || !s_ce || s_ue) sram_err = sram_err + 1; else sram_ce = sram_ce + 1;
            @(negedge ck); inj_v = 1; inj_a = 7; inj_m = 576'd1 << k;          // restore
            @(negedge ck); inj_v = 0;
        end
        for (j = 0; j < 72; j = j + 1) for (k = j + 1; k < 72; k = k + 1) begin   // every double-bit pair of word 0, row 9
            @(negedge ck); inj_v = 1; inj_a = 9; inj_m = (576'd1 << j) | (576'd1 << k);
            @(negedge ck); inj_v = 0; s_re = 1; s_ra = 9;
            @(negedge ck); s_re = 0; @(posedge ck); #0.1;
            if (!s_rv || !s_ue) sram_err = sram_err + 1; else sram_ue = sram_ue + 1;
            @(negedge ck); inj_v = 1; inj_a = 9; inj_m = (576'd1 << j) | (576'd1 << k);
            @(negedge ck); inj_v = 0;
        end
        for (i = 0; i < 64; i = i + 1) begin            // clean rows
            @(negedge ck); s_re = 1; s_ra = i;
            @(negedge ck); s_re = 0; @(posedge ck); #0.1;
            if (s_rd != {16{32'(i * 2654435761)}} || s_ce || s_ue) sram_err = sram_err + 1;
        end
        begin : verdict
            integer pass;
            pass = boot_ok && tp == 2'b11 && !bfault && err == 0 && ok_n == NS && ce_n == NFLIP1 && ue_n == NFLIP2 &&
                   kvbad == 0 && kvn == (NS + 31) / 37 && sram_err == 0 && sram_ce == 576 && sram_ue == 2556;
            $display("TB_S81_BOOT_SECDED mut=%0d max_pos=%0d top_pos=%0d sectors=%0d boot_ok=%0d present=%b boot_fault=%0d kv=%0d/%0d kv_bad=%0d read_ok=%0d/%0d mismatch=%0d ce=%0d/%0d ue=%0d/%0d hbm_fault=%0d sram_single=%0d/576 sram_double=%0d/2556 sram_err=%0d %s",
                MUT, MAX_POS, top, st_sec, boot_ok, tp, bfault, kvn, (NS + 31) / 37, kvbad, ok_n, NS, err, ce_n, NFLIP1, ue_n, NFLIP2, r_fault,
                sram_ce, sram_ue, sram_err, pass ? "PASS" : "FAIL");
            $finish;
        end
    end
    // decoder outputs vs golden
    always @(posedge ck) if (o_v) begin
        if (o_ue) ue_n = ue_n + 1;
        else begin
            if (o_ce) ce_n = ce_n + 1;
            if (o_d != img[o_t]) err = err + 1; else ok_n = ok_n + 1;
        end
        if (o_ue) ok_n = ok_n + 1;          // a detected sector counts as handled (the consumer fails closed)
    end
endmodule
