`timescale 1ns/1ps
// DIE-S81-85 form A (3): dsdv_svc_mem_ar vs the flop arrays it replaces, random traffic with dense same-address
// write / read collisions, every cycle compared.  Four instances: AR 32 deep (sw / wq / pvq form), AR 40 of 160 with
// out-of-range pointers (pbuf form), SYNC 16 of 32 with out-of-range writes and reads (qmem form).
// + LA 32 x 512 (sw scanner form, dsdv_svc_mem_la).  MUT 1 = no write bypass, 2 = read one cycle late / LA bank by
// the previous pointer: both must be CAUGHT.
module tb_svc_mem_ar;
    parameter integer MUT = 0;
    parameter integer NCYC = 200000;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0, err = 0, chk = 0, coll = 0;
    reg [31:0] rng = 32'h1234_5678;
    function automatic [31:0] rnd(); rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5); rnd = rng; endfunction

    // ---- A: AR, W 300, DEPTH 32, pointer ring (sw / wq / pvq form)
    reg [299:0] a_mem [0:31]; reg [4:0] a_rp, a_wp; reg a_adv, a_we; reg [299:0] a_wd;
    wire [4:0] a_rpn = !rst_n ? 5'd0 : a_adv ? a_rp + 1'b1 : a_rp;
    wire [299:0] a_rd;
    dsdv_svc_mem_ar #(.W(300), .DEPTH(32), .AW(5), .MACRO(0), .SYNC(0), .MUT(MUT)) u_a (
        .clk(clk), .ra_n(a_rpn), .we(a_we), .wa(a_wp), .wd(a_wd), .rd(a_rd));
    // ---- B: AR on the 160 macro, DEPTH 40, 6-bit pointer that runs past 39 (pbuf form)
    reg [255:0] b_mem [0:39]; reg [5:0] b_rp, b_wp; reg b_adv, b_go, b_we; reg [255:0] b_wd;
    wire [5:0] b_rpn = !rst_n ? 6'd0 : b_go ? 6'd0 : b_adv ? b_rp + 1'b1 : b_rp;
    wire [255:0] b_rd;
    dsdv_svc_mem_ar #(.W(256), .DEPTH(40), .AW(6), .MACRO(1), .SYNC(0), .MUT(MUT)) u_b (
        .clk(clk), .ra_n(b_rpn), .we(b_we), .wa(b_wp), .wd(b_wd), .rd(b_rd));
    // ---- C: SYNC, DEPTH 8 of a 4-bit address (qmem form, H 8)
    reg [511:0] c_mem [0:7]; reg [3:0] c_ra, c_wa; reg c_we; reg [511:0] c_wd, c_q;
    wire [511:0] c_rd;
    dsdv_svc_mem_ar #(.W(512), .DEPTH(8), .AW(4), .MACRO(0), .SYNC(1), .MUT(MUT == 2 ? 0 : MUT)) u_c (
        .clk(clk), .ra_n(c_ra), .we(c_we), .wa(c_wa), .wd(c_wd), .rd(c_rd));

    // ---- D: LA two-bank lookahead, W 512, 32 entries, pointer steps 0 / 1 (sw scanner form)
    reg [511:0] d_mem [0:31]; reg [4:0] d_rp, d_wp; reg d_adv, d_we; reg [511:0] d_wd;
    wire [511:0] d_rd;
    dsdv_svc_mem_la #(.W(512), .AW(5), .MUT(MUT)) u_d (.clk(clk), .rp(d_rp), .we(d_we), .wa(d_wp), .wd(d_wd), .rd(d_rd));

    integer i;
    initial begin
        for (i = 0; i < 32; i++) d_mem[i] = 0; d_rp = 0; d_wp = 0;
        for (i = 0; i < 32; i++) a_mem[i] = 0;
        for (i = 0; i < 40; i++) b_mem[i] = 0;
        for (i = 0; i < 8; i++) c_mem[i] = 0;
        a_rp = 0; a_wp = 0; b_rp = 0; b_wp = 0; c_q = 0;
    end
    // stimulus (blocking, before the edge)
    always @(negedge clk) begin
        a_adv = rnd() % 3 == 0; a_we = rnd() % 2 == 0;
        a_wp = (rnd() % 4 == 0) ? (a_adv ? a_rp + 1'b1 : a_rp) : 5'(rnd());      // dense collisions with the next read
        a_wd = {rnd(), rnd(), rnd(), rnd(), rnd(), rnd(), rnd(), rnd(), rnd(), rnd()};
        b_go = rnd() % 97 == 0; b_adv = rnd() % 2 == 0; b_we = rnd() % 2 == 0;
        b_wp = (rnd() % 4 == 0) ? (b_go ? 6'd0 : b_adv ? b_rp + 1'b1 : b_rp) : 6'(rnd() % 40);
        b_wd = {8{rnd()}} ^ {rnd(), rnd(), rnd(), rnd(), rnd(), rnd(), rnd(), rnd()};
        c_ra = 4'(rnd()); c_we = rnd() % 2 == 0; c_wa = (rnd() % 3 == 0) ? c_ra : 4'(rnd());
        c_wd = {16{rnd()}};
        d_adv = rnd() % 2 == 0; d_we = rnd() % 3 != 0;
        d_wp = (rnd() % 2 == 0) ? d_rp + 5'(rnd() % 3) : 5'(rnd());              // the held rows rp / rp + 1 / rp + 2
        d_wd = {16{rnd()}};
        if (a_we && a_wp == (a_adv ? a_rp + 1'b1 : a_rp)) coll = coll + 1;
    end
    // reference: flop arrays + pointers
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin a_rp <= 0; b_rp <= 0; d_rp <= 0; end
        else begin
            if (a_adv) a_rp <= a_rp + 1'b1;
            if (d_adv) d_rp <= d_rp + 1'b1;
            if (b_go) b_rp <= 0; else if (b_adv) b_rp <= b_rp + 1'b1;
        end
    always @(posedge clk) begin
        if (a_we) a_mem[a_wp] <= a_wd;
        if (d_we) d_mem[d_wp] <= d_wd;
        if (b_we && b_wp < 40) b_mem[b_wp] <= b_wd;
        if (c_we && c_wa < 8) c_mem[c_wa[2:0]] <= c_wd;
        c_q <= (c_ra < 8) ? c_mem[c_ra[2:0]] : 512'd0;
    end
    wire [299:0] a_ref = a_mem[a_rp];
    wire [255:0] b_ref = (b_rp < 40) ? b_mem[b_rp] : 256'd0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1;
        if (cyc > 8) begin
            chk = chk + 1;
            if (a_rd !== a_ref) err = err + 1;
            if (b_rd !== b_ref) err = err + 1;
            if (c_rd !== c_q) err = err + 1;
            if (d_rd !== d_mem[d_rp]) err = err + 1;
        end
        if (cyc == NCYC) begin
            if (MUT == 0) $display("%s tb_svc_mem_ar MUT=0 checks=%0d errors=%0d same-address collisions=%0d", err == 0 ? "PASS" : "FAIL", chk, err, coll);
            else $display("%s tb_svc_mem_ar MUT=%0d checks=%0d errors=%0d", err != 0 ? "CAUGHT" : "MISSED", MUT, chk, err);
            $finish;
        end
    end
endmodule
