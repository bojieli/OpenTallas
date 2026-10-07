`timescale 1ns/1ps
// Smoke/equivalence bench for rtl/physical/ot_qwen_slab_port_group.sv (the M1-M5 slab element).
// The element must return, for each active request, o_data = the RTL post-scale ot_hdc_fmul (ot_hdc_fp32_mul_pipe,
// LAT 5) of res_in and the scale word its group reads, o_addr = oa + GID*ots, the RTL result mask, and the argmax
// subtree top over its 16 lanes.  A bench-local ot_rom_4096x266_m8 returns a word that depends on the bank (parsed
// from its own hierarchical name) and the address, so a mis-decoded bank or a mis-aligned capture fails.
// Build (iverilog -g2012): this file, the element, ot_hdc_delay, ot_hdc_fp32_mul_lat, ot_hdc_fp32_add_lat,
// ot_hdc_fastfp, ot_hdc_prefix, ot_hdc_fpu, ot_hdc_fp32_mul_pipe, rtl/proto/ot_fp32_add_rne_pipe (BW_FIFO = 0).
module ot_rom_4096x266_m8 (input wire clk, input wire ce_in, input wire [11:0] addr_in, output reg [265:0] rd_out);
    integer bank;
    initial begin : p_name
        string n;
        integer i, c, b;
        n = $sformatf("%m");
        bank = -1;
        for (c = 0; c < 4; c = c + 1)
            for (b = 0; b < 4; b = b + 1)
                if (n == $sformatf("tb_qwen_slab_port_group.dut.g_col[%0d].g_bank[%0d].u_rom.p_name", c, b)) bank = c * 4 + b;
        if (bank < 0) begin $display("FAIL: cannot parse bank from %s", n); $fatal(1, "EQUIVALENCE_TERMINAL_SETUP_FAIL"); end
    end
    function automatic [265:0] word(input integer bank, input [11:0] a);
        integer l;
        reg [31:0] h;
        begin
            word = 0;
            for (l = 0; l < 16; l = l + 1) begin
                h = (bank * 32'h9E3779B1) ^ (a * 32'h85EBCA77) ^ (l * 32'hC2B2AE3D);
                h = h ^ (h >> 13); h = h * 32'h27D4EB2F; h = h ^ (h >> 16);
                word[16*l +: 16] = {h[0], 8'd119 + {4'd0, h[11:8]}, h[18:12]};
            end
        end
    endfunction
    always @(posedge clk) if (ce_in) rd_out <= word(bank, addr_in);
endmodule

module tb_qwen_slab_port_group;
    parameter integer W = 16, IL = 8, AW = 24, NW = 16, GID = 95, MUL_LAT = 6, LEAD = 8;
    parameter integer IN_STAGE = 0, AM_SPLIT = 0, S5_CTL = 0, COVER_DPOS = 0, SCALE_PAIR = 0, OREG = 0;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = !clk;

    function automatic [265:0] word(input integer bank, input [11:0] a);
        integer l;
        reg [31:0] h;
        begin
            word = 0;
            for (l = 0; l < 16; l = l + 1) begin
                h = (bank * 32'h9E3779B1) ^ (a * 32'h85EBCA77) ^ (l * 32'hC2B2AE3D);
                h = h ^ (h >> 13); h = h * 32'h27D4EB2F; h = h ^ (h >> 16);
                // a BF16 scale in [2^-8, 2^8): sign, exponent 119..134, 7 mantissa bits
                word[16*l +: 16] = {h[0], 8'd119 + {4'd0, h[11:8]}, h[18:12]};
            end
        end
    endfunction

    reg p_v = 0, p_last = 0, p_oen = 0, p_amax = 0, p_rmax = 0, p_wsrc = 0, p_mmode = 0;
    reg [3:0] p_split = 0;
    reg [NW:0] p_nb = 0, p_lb = 0, p_nout = 0;
    reg [AW-1:0] p_sbase = 0, p_oa = 0, p_ots = 0;
    reg [W*32-1:0] res_in = 0;
    wire o_we, ov, am_tv, am_rmax, fault, wf, rf, wl, rl, bw_rdy, tw_v;
    wire [AW-1:0] o_addr;
    wire [W-1:0] o_mask;
    wire [W*32-1:0] o_data, tw_d;
    wire [1+32+NW-1:0] am_top;
    ot_qwen_slab_port_group #(.GID(GID), .MUL_LAT(MUL_LAT), .BW_FIFO(0), .IN_STAGE(IN_STAGE), .AM_SPLIT(AM_SPLIT),
        .S5_CTL(S5_CTL), .SCALE_PAIR(SCALE_PAIR), .OREG(OREG)) dut (
        .clk(clk), .rst_n(rst_n), .bw_clk(clk), .bw_rst_n(rst_n), .bw_v(1'b0), .bw_rdy(bw_rdy), .bw_d({W*32{1'b0}}),
        .tw_v(tw_v), .tw_rdy(1'b1), .tw_d(tw_d),
        .p_v(p_v), .p_last(p_last), .p_oen(p_oen), .p_amax(p_amax), .p_rmax(p_rmax), .p_wsrc(p_wsrc),
        .p_mmode(p_mmode), .p_split(p_split), .p_nb(p_nb), .p_lb(p_lb), .p_nout(p_nout),
        .p_sbase(p_sbase), .p_oa(p_oa), .p_ots(p_ots), .res_in(res_in),
        .o_we(o_we), .o_addr(o_addr), .o_mask(o_mask), .o_data(o_data), .ov(ov),
        .am_tv(am_tv), .am_top(am_top), .am_rmax(am_rmax), .fault(fault),
        .bw_w_fault(wf), .bw_r_fault(rf), .bw_w_live(wl), .bw_r_live(rl));

    // reference: the RTL's own post-scale multiplier, fed the same operands at the same time
    reg  [W*32-1:0] ra = 0, rb = 0;
    reg  rv = 0;
    wire [W*32-1:0] ry;
    wire [W-1:0] rvo;
    genvar gl;
    generate for (gl = 0; gl < W; gl = gl + 1) begin : g_ref
        wire [1:0] err;
        ot_hdc_fp32_mul_pipe u (.clk(clk), .rst_n(rst_n), .valid_in(rv), .a(ra[32*gl +: 32]), .b(rb[32*gl +: 32]),
                                .y(ry[32*gl +: 32]), .err(err), .valid_out(rvo[gl]));
    end endgenerate

    // expected-value queues
    reg [W*32-1:0] q_res [0:4095];
    reg [W*32-1:0] q_scl [0:4095];
    reg [AW-1:0]   q_addr [0:4095];
    reg [W-1:0]    q_mask [0:4095];
    reg [NW-1:0]   q_nb [0:4095];
    reg            q_wsrc [0:4095];
    reg            q_amax [0:4095];
    integer nq = 0, nd = 0, na = 0, errors = 0, nreq = 0;
    reg [W*32-1:0] pend_res [0:LEAD];   // res_in is driven LEAD cycles after the tag
    reg            pend_v [0:LEAD];
    reg [W*32-1:0] ref_y [0:4095];
    integer nr = 0;

    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction

    function automatic [31:0] rnd32(input integer s);
        reg [31:0] h;
        begin h = s * 32'h9E3779B1; h = h ^ (h >> 15); h = h * 32'h85EBCA77; h = h ^ (h >> 13); rnd32 = h; end
    endfunction

    integer cyc, k, l, seed;
    reg [AW-1:0] sa;
    reg [11:0] bank_a;
    integer bank;
    reg [265:0] sw;
    reg [W*32-1:0] rv_res, bvec;
    reg [W-1:0] mask;
    reg [31:0] lane;
    initial begin
        for (k = 0; k <= LEAD; k = k + 1) begin pend_v[k] = 0; pend_res[k] = 0; end
        repeat (4) @(posedge clk);
        rst_n <= 1;
        repeat (4) @(posedge clk);
        for (cyc = 0; cyc < 3000; cyc = cyc + 1) begin
            seed = cyc * 7 + 3;
            // tag at request time
            p_v <= (cyc < 2990) && ((rnd32(seed) % 4) != 0);
            p_last <= (rnd32(seed + 1) % 3) != 0;
            p_wsrc <= (rnd32(seed + 2) % 8) == 0;
            p_mmode <= rnd32(seed + 3) % 2;
            p_split <= 6;                                   // GT >> 6 = 96 ports: GID 95 is a port
            p_oen <= 1; p_amax <= (rnd32(seed + 4) % 2); p_rmax <= 0;
            p_nb <= (rnd32(seed + 5) % 64) * 16;
            p_lb <= rnd32(seed + 6) % 32;
            // partial masks near GID*W*IL = 12160 .. and lb + GID*W; with COVER_DPOS, one op in 8 has a small nout
            // (row-count difference d <= 0 and near 0 in both modes: no active request, all-zero masks)
            p_nout <= (COVER_DPOS != 0 && (rnd32(seed + 11) % 8) == 0) ? 1400 + (rnd32(seed + 7) % 12000)
                                                                    : 15000 + (rnd32(seed + 7) % 3000);
            p_sbase <= rnd32(seed + 8) % 60000;
            p_oa <= rnd32(seed + 9) % (1 << 20);
            p_ots <= rnd32(seed + 10) % 4096;
            @(negedge clk);
            if (p_v && p_last) begin
                nreq = nreq + 1;
                sa = (!p_wsrc && (p_mmode ? (p_lb + GID * W < p_nout) : (p_nb + GID * (W * IL) < p_nout))) ?
                     p_sbase + (p_nb >> 4) + GID * IL : p_sbase;
                bank = sa[AW-1:12];
                sw = word(bank, sa[11:0]);
                for (l = 0; l < W; l = l + 1) begin
                    lane = rnd32(seed * 31 + l);
                    // FP32 operands, normal range plus a few zeros
                    rv_res[32*l +: 32] = (lane % 23 == 0) ? 32'd0 : {lane[31], 8'd100 + {2'd0, lane[30:25]}, lane[22:0]};
                    bvec[32*l +: 32] = {p_wsrc ? 16'h3F80 : sw[16*l +: 16], 16'd0};
                    mask[l] = p_mmode ? (p_lb + GID * W + l < p_nout) : (p_nb + GID * (W * IL) + l < p_nout);
                end
                q_res[nq] = rv_res; q_scl[nq] = bvec; q_addr[nq] = p_oa + GID * p_ots; q_mask[nq] = mask;
                q_nb[nq] = p_nb[NW-1:0]; q_wsrc[nq] = p_wsrc; q_amax[nq] = p_amax;
                nq = nq + 1;
                pend_res[0] = rv_res; pend_v[0] = 1;
            end else begin
                pend_v[0] = 0; pend_res[0] = rnd32(seed + 99);
            end
            // res_in goes out LEAD cycles after its tag
            res_in <= pend_res[LEAD];
            for (k = LEAD; k > 0; k = k - 1) begin pend_res[k] = pend_res[k-1]; pend_v[k] = pend_v[k-1]; end
            @(posedge clk);
        end
        p_v <= 0;
        repeat (60) @(posedge clk);
        if (nd != nq) begin $display("FAIL: %0d results for %0d requests", nd, nq); errors = errors + 1; end
        if (errors == 0) $display("PASS: %0d requests, %0d results bit-exact vs ot_hdc_fmul; %0d argmax tops", nreq, nd, na);
        else $display("FAIL: %0d errors", errors);
        if (errors != 0) $fatal(1, "EQUIVALENCE_TERMINAL_FAIL");
        $finish;
    end

    // reference multiplier stream (order of requests), and comparison at the element's outputs
    integer ri = 0;
    always @(posedge clk) begin
        rv <= 0;
        if (ri < nq) begin
            ra <= q_res[ri]; rb <= q_scl[ri]; rv <= 1; ri <= ri + 1;
        end
    end
    // collect reference results in order (LAT 5)
    always @(posedge clk) if (rvo[0]) begin ref_y[nr] <= ry; nr <= nr + 1; end
    integer ai = 0;
    reg [1+32+NW-1:0] best;
    reg [NW-1:0] brow;
    integer bl;
    always @(posedge clk) if (ov) begin
        if (!o_we) begin $display("FAIL: ov without o_we at %0d", nd); errors = errors + 1; end
        if (nd >= nr) begin $display("FAIL: result %0d before its reference", nd); errors = errors + 1; end
        else begin
            for (bl = 0; bl < W; bl = bl + 1)
                if (q_mask[nd][bl] && o_data[32*bl +: 32] !== ref_y[nd][32*bl +: 32]) begin
                    $display("FAIL: result %0d lane %0d got %h want %h", nd, bl, o_data[32*bl +: 32], ref_y[nd][32*bl +: 32]);
                    errors = errors + 1;
                end
            if (o_addr !== q_addr[nd]) begin $display("FAIL: result %0d addr %h want %h", nd, o_addr, q_addr[nd]); errors = errors + 1; end
            if (o_mask !== q_mask[nd]) begin $display("FAIL: result %0d mask %h want %h", nd, o_mask, q_mask[nd]); errors = errors + 1; end
        end
        nd <= nd + 1;
    end
    // argmax subtree tops, in request order of amax requests
    integer am_i = 0;
    always @(posedge clk) if (am_tv) begin
        while (am_i < nq && !q_amax[am_i]) am_i = am_i + 1;
        best = 0;
        for (bl = 0; bl < W; bl = bl + 1)
            if (q_mask[am_i][bl] && (!best[1+32+NW-1] || okey(ref_y[am_i][32*bl +: 32]) > best[NW +: 32]))
            begin
                brow = q_nb[am_i] + GID * (W * IL) + bl;
                best = {1'b1, okey(ref_y[am_i][32*bl +: 32]), brow};
            end
        if (best[1+32+NW-1] && am_top !== best) begin
            $display("FAIL: argmax %0d got %h want %h", am_i, am_top, best); errors = errors + 1;
        end
        if (!best[1+32+NW-1] && am_top[1+32+NW-1]) begin $display("FAIL: argmax %0d spurious valid", am_i); errors = errors + 1; end
        am_i = am_i + 1; na = na + 1;
    end
    always @(posedge clk) if (fault) begin $display("FAIL: fault"); errors = errors + 1; end
endmodule
