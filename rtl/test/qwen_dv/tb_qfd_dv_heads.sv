`timescale 1ns/1ps
// Q-DV column-head bench (step 2, item 2): the slice's 8 corridor words, carried through the existing corridor
// stations (ot_qfd_xcst, as ot_qwen_me_array_dvm_w12 g_cor) to its 64 tiles, against the EXISTING x fabric
// ot_qfd_xdvm_fabric (NCOL 48, tap fed with the FP32 x values, NATIVE_AFFINE / STATIC_SCHEDULE 1) at the same tiles.
// The slice sees the x as stream words (64 BF16 RNE, 64-aligned beats) on sw_i and the arm descriptor / {ib, go} on
// hr_i; the fabric gets the FP32 writes (all 64 lanes) and the same xpf / go / ib on the same edges.  Every tile's
// {go, ib, xl} is compared on every edge at one constant offset (the slice path minus the fabric path), taken from the
// first go.  Ops: the production TP8 shapes (qkv k 8 S 512, o_proj k 2 S 256 x3, gate_up k 32 S 128, down k 6 S 256 x3)
// with random x images.  Prints PASS / FAIL.
// QW-DIEFIX-NFAR 10-19: corridor station model = the die clusters' physical sidx numbering (g_s below), matching the
// qfd_dv_heads corridor retag; the old model (sidx = logical station) passes only the pre-fix heads.
module tb_qfd_dv_heads;
    parameter integer MUT = 0, SID = 5, NOPS = 4, GAPC = 1500;
    localparam integer NW = 18, AW = 24, XCW = 12, NH = 8, TG = 4, IL = 8, NCOL = 48;
    localparam integer IBW = 3 * NW + 13 * AW + 13, CW = 1 + IBW + 128 + 8;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    function automatic [31:0] mix(input [31:0] a, input [31:0] b);
        reg [31:0] x;
        begin
            x = a * 32'h9E3779B1 ^ (b + 32'h7F4A7C15) * 32'h85EBCA77;
            x = x ^ (x >> 15); x = x * 32'h2C1B3C6D; x = x ^ (x >> 12); x = x * 32'h297A2D39; x = x ^ (x >> 15);
            mix = x;
        end
    endfunction
    function automatic [31:0] xv(input [31:0] addr, input integer n);
        reg [31:0] h;
        begin
            h = mix(addr + 32'd4099 * n, 32'h4444);
            xv = {h[31], 8'd124 + {5'd0, h[26:24] % 3'd6}, h[22:0]};
            if (h[30:28] == 3'd0) xv[15:0] = 16'h8000;        // RNE ties
        end
    endfunction
    function automatic [15:0] rne(input [31:0] b);
        reg [32:0] r;
        begin r = {1'b0, b} + 33'h7FFF + {32'd0, b[16]}; rne = r[31:16]; end
    endfunction
    // ---------------------------------------------------------------- stimulus registers
    reg              go, xpf_v, xpf_round, sw_v;
    reg [NW-1:0]     i_nout, i_tiles, i_k, xpf_k;
    reg [AW-1:0]     i_xbase, i_xcs, xpf_xbase, sw_a;
    reg [XCW-1:0]    xpf_xcs, xpf_xks;
    reg [3:0]        i_split, xpf_split;
    reg [64*32-1:0]  sw_d;
    reg [1023:0]     sw_bf;
    wire [IBW-1:0] ib = {i_nout, i_tiles, i_k, 1'b0, {AW{1'b0}}, AW'(i_k * IL), AW'(IL), AW'(1), i_xbase, AW'(1),
                         {AW{1'b0}}, i_xcs, 3'd0, i_split, {AW{1'b0}}, 1'b1, {AW{1'b0}}, AW'(IL), AW'(1), 1'b0, 1'b1,
                         1'b0, 1'b0, {AW{1'b0}}};
    wire [71:0]  xpf = {xpf_round, xpf_k, xpf_split, xpf_xks, xpf_xcs, xpf_xbase, xpf_v};
    // ---------------------------------------------------------------- reference: the existing fabric
    wire [NCOL*2*NH-1:0] r_go;
    wire [NCOL*2*NH*IBW-1:0] r_ib;
    wire [NCOL*2*NH*TG*32-1:0] r_xl;
    wire r_fault;
    ot_qfd_xdvm_fabric #(.AW(AW), .NW(NW), .XCW(XCW), .IL(IL), .NCOL(NCOL), .NH(NH), .TG(TG), .SMIN(7), .SMAX(11),
        .HB(1), .NATIVE_AFFINE(1), .STATIC_SCHEDULE(1)) u_ref (
        .clk(clk), .rst_n(rst_n), .go_acc(go), .ib(ib),
        .xpf_v(xpf_v), .xpf_xbase(xpf_xbase), .xpf_xcs(xpf_xcs), .xpf_xks(xpf_xks), .xpf_split(xpf_split),
        .xpf_k(xpf_k), .xpf_round(xpf_round), .sw_v(sw_v), .sw_a(sw_a), .sw_m({64{1'b1}}), .sw_d(sw_d),
        .aw_v(1'b0), .aw_a({AW{1'b0}}), .aw_m(16'd0), .aw_d(512'd0),
        .go_t(r_go), .ib_t(r_ib), .xl_t(r_xl), .x_fault(r_fault));
    // ---------------------------------------------------------------- DUT: the slice + the corridor stations
    wire [4*CW-1:0] n_d, s_d;
    wire [69:0] st;
    wire [1087:0] swi = sw_v ? {1'b1, 3'd0, 4'hF, 4'hE, sw_a, 28'd0, sw_bf} : 1088'd0;
    qfd_dv_slice #(.MUT(MUT)) u_dut (.ck(clk), .rst_n(rst_n), .sid(4'(SID)), .cmd(116'd0), .cw0(514'd0), .cw1(514'd0),
        .nb9_i(514'd0), .nb9_o(), .sw_i(swi), .so_e(), .se_i(1088'd0), .so_w(), .sc_i(96'd0), .sc_o(),
        .ar_o(), .ar_i(518'd0), .dd_o(), .dd_i(520'd0), .hr_i({go, ib, xpf}), .hr_o(), .n_d(n_d), .s_d(s_d), .st(st));
    function automatic integer tid(input integer c, input integer r);
        integer dr, bc, br, lbc, lbr, blk, z, p, i;
        begin
            dr = (r < NH) ? NH + r : NH - 1 - (r - NH);
            bc = 4; br = 4; lbc = 2; lbr = 2;
            blk = (c / bc) * (2 * NH / br) + dr / br;
            z = 0; p = 0;
            for (i = 0; i < 2; i = i + 1) begin
                z = z | (((c % bc) >> i) & 1) << p; p = p + 1;
                z = z | (((dr % br) >> i) & 1) << p; p = p + 1;
            end
            tid = bc * br * blk + z;
        end
    endfunction
    wire [64-1:0]        d_go;
    wire [64*IBW-1:0]    d_ib;
    wire [64*128-1:0]    d_xl;
    genvar c, h, s;
    generate for (c = 0; c < 4; c = c + 1) begin : g_c
        for (h = 0; h < 2; h = h + 1) begin : g_h
            wire [CW-1:0] chain [0:NH];
            assign chain[0] = h == 0 ? n_d[c*CW +: CW] : s_d[c*CW +: CW];
            // s = PHYSICAL station position along the side's chain from the slice (0..3 near cluster, 4..7 far).
            // Die cluster numbering (qfd_c_b16_dv: sidx {far, q} near / {far, ~q} far, q = position inside the
            // cluster from the slice): SIDX = s (near) / 11 - s (far).  The tile there is the heads' logical station
            // LS whose corridor tag (qfd_dv_heads retag, QW-XHEAD ea371ad83: tag = s ^ 3 for N s >= 4 and S s < 4)
            // equals SIDX: N LS = s; S LS = s ^ 3 (near) / 11 - s (far).  (Pre-fix model: SIDX = LS = s.)
            for (s = 0; s < NH; s = s + 1) begin : g_s
                localparam integer SIDX = (s < 4) ? s : 11 - s;
                localparam integer LS = (h == 0) ? s : ((s < 4) ? (s ^ 3) : 11 - s);
                wire [IBW+128:0] tap, tq;
                ot_qfd_xcst #(.AW(AW), .NW(NW), .IL(IL), .XOFF(3)) u_st (.ck(clk), .rst_n(rst_n), .sidx(3'(SIDX)),
                    .a_d(chain[s]), .a_r(), .b_d(chain[s+1]), .b_r(1'b1), .tap_d(tap));
                ot_hdc_delay #(.W(IBW + 129), .D(NH - 1 - s)) u_eq (.clk(clk), .rst_n(rst_n), .d(tap), .q(tq));
                localparam integer K = c * 16 + h * NH + LS;
                assign d_go[K] = tq[0];
                assign d_ib[K*IBW +: IBW] = tq[IBW:1];
                assign d_xl[K*128 +: 128] = tq[IBW+128 -: 128];
            end
        end
    end endgenerate
    // ---------------------------------------------------------------- traces and compare
    localparam integer NC = 8000;
    reg [IBW+128:0] rt [0:63][0:NC-1];
    reg [IBW+128:0] dt [0:63][0:NC-1];
    integer cyc = 0, k, t, rfirst = -1, dfirst = -1, errors = 0, checks = 0, gos = 0, faults = 0;
    always @(negedge clk) if (rst_n && cyc < NC) begin
        for (k = 0; k < 64; k = k + 1) begin
            t = tid(4 * SID + k / 16, k % 16);
            rt[k][cyc] = {r_xl[t*TG*32 +: 128], r_ib[t*IBW +: IBW], r_go[t]};
            dt[k][cyc] = {d_xl[k*128 +: 128], d_ib[k*IBW +: IBW], d_go[k]};
            if (r_go[t] && rfirst < 0) rfirst = cyc;
            if (d_go[k] && dfirst < 0) dfirst = cyc;
            if (r_go[t]) gos = gos + 1;
        end
        if (st[69] || r_fault) faults = faults + 1;
        cyc = cyc + 1;
    end
    // ---------------------------------------------------------------- stimulus
    integer op, a, lo, hi, l;
    task automatic issue(input integer kk, input integer split, input integer xbase, input integer rounds,
                         input integer nout);
        begin
            lo = xbase; hi = xbase + ((1 << split) - 1) * kk + kk;
            @(posedge clk); #0.1;
            xpf_v = 1; xpf_xbase = xbase; xpf_xcs = kk; xpf_xks = 1; xpf_split = split; xpf_k = kk; xpf_round = 1;
            @(posedge clk); #0.1; xpf_v = 0;
            repeat (2) @(posedge clk); #0.1;
            a = lo & ~63;                                  // stream beats are 64-aligned
            while (a < hi) begin
                sw_v = 1; sw_a = a;
                for (l = 0; l < 64; l = l + 1) begin
                    sw_d[32*l +: 32] = xv(a + l, op); sw_bf[16*l +: 16] = rne(xv(a + l, op));
                end
                a = a + 64;
                @(posedge clk); #0.1;
            end
            sw_v = 0;
            repeat (8) @(posedge clk); #0.1;
            i_k = kk; i_split = split; i_xbase = xbase; i_xcs = kk; i_tiles = rounds; i_nout = nout;
            go = 1; @(posedge clk); #0.1; go = 0;
            repeat (GAPC) @(posedge clk); #0.1;
            op = op + 1;
        end
    endtask
    integer off, e;
    initial begin
        go = 0; xpf_v = 0; sw_v = 0; op = 0; i_nout = 0; i_tiles = 0; i_k = 0; i_xbase = 0; i_xcs = 0; i_split = 0;
        xpf_round = 0; xpf_k = 0; xpf_split = 0; xpf_xks = 0; xpf_xcs = 0; xpf_xbase = 0; sw_a = 0; sw_d = 0; sw_bf = 0;
        repeat (4) @(posedge clk); rst_n = 1; repeat (8) @(posedge clk); #0.1;
        issue(8, 9, 4096, 1, 768);           // qkv
        issue(2, 8, 50672, 3, 4096);         // o_proj
        issue(32, 7, 4096, 1, 3072);         // gate_up
        issue(6, 8, 55280, 3, 4096);         // down
        repeat (100) @(posedge clk);
        off = dfirst - rfirst;
        if (rfirst < 0 || dfirst < 0) begin $display("FAIL no go reached the tiles (ref %0d, slice %0d)", rfirst, dfirst); $finish; end
        for (t = rfirst; t + off < cyc && t + off < NC; t = t + 1)
            for (k = 0; k < 64; k = k + 1) begin
                checks = checks + 1;
                if (rt[k][t] !== dt[k][t + off]) begin
                    if (errors < 10) $display("FAIL tile %0d ref cyc %0d: go %0d/%0d xl ref %h slice %h", k, t,
                        rt[k][t][0], dt[k][t + off][0], rt[k][t][IBW+128 -: 128], dt[k][t + off][IBW+128 -: 128]);
                    errors = errors + 1;
                end
            end
        if (errors == 0 && faults == 0 && gos > 0)
            $display("PASS heads SID=%0d ops=%0d tile-edges=%0d tile gos=%0d slice-minus-fabric offset=%0d edges",
                     SID, op, checks, gos, off);
        else $display("FAIL heads errors=%0d faults=%0d gos=%0d checks=%0d", errors, faults, gos, checks);
        $finish;
    end
endmodule
