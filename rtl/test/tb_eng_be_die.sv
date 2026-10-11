`timescale 1ns/1ps
// s81-svceng-1011: one Engram home DIE of the BE gate = dsfd_engram_c #(BE 1) (eng_SE: core + SE half) + the SW half
// ot_s81_eng_half #(STACK 0) (svc_SW) on relay-delayed narrow pairs (t_hq / f_hr / t_eb / f_eb, D cycles each way)
// + 2 x 32 PC models (tb_eng_pc: per-PC sparse memory, fixed latency + jitter, writes acknowledged by wd)
// + a host driver (hw / hc: 8 sector credits) that programs the aperture by CSR words and boots EXPECT sectors.
// RUNTIME CONTENT: the read side's rows are loaded lazily into the PC models when the lookup issues the row request
// (snooped at the core's router input), at the PC / global sector addresses the rowstripe canonical map assigns
// (row = atom / 9: stack row % 2, PC (row / 2) % 32, local (row / 64) * 9 + base, global = inverse(PC, local + k));
// the content is the golden row (codes, scale, CRC-32/MPEG-2, padding) of the tables the lookup addresses.  A wrong
// route, merge, PC or address returns another row's atoms or none: the consumer compares against the golden.
module tb_eng_pc #(parameter integer LAT = 240, JIT = 0, LATW = 30) (
    input wire clk, rst_n, input wire [340:0] rq, output reg wd, output reg rv, output reg [255:0] r_data,
    output reg [16:0] r_tag, output reg [3:0] r_beat,
    input wire [8:0] ld_v, input wire [9*30-1:0] ld_a, input wire [9*256-1:0] ld_d);
    reg [255:0] mem [int unsigned];
    int unsigned qa [$]; int qd [$]; int ql [$]; int qt [$]; int wq [$];
    integer cyc = 0, b = 0, k; reg [31:0] js = 32'h1357;
    always @(posedge clk) begin
        cyc <= cyc + 1; rv <= 1'b0; wd <= 1'b0;
        for (k = 0; k < 9; k = k + 1) if (ld_v[k]) mem[ld_a[30*k +: 30]] = ld_d[256*k +: 256];
        if (rst_n && rq[0]) begin
            if (rq[1]) begin mem[rq[31:2]] = rq[340:85]; wq.push_back(cyc + LATW); end
            else begin js = js ^ (js << 13); js = js ^ (js >> 17); js = js ^ (js << 5);
                       qa.push_back(rq[31:2]); ql.push_back(rq[35:32]); qt.push_back(rq[52:36]);
                       qd.push_back(cyc + LAT + (JIT > 0 ? js % (JIT + 1) : 0)); end
        end
        if (wq.size() > 0 && wq[0] <= cyc) begin wd <= 1'b1; void'(wq.pop_front()); end
        if (qa.size() > 0 && qd[0] <= cyc) begin
            rv <= 1'b1; r_tag <= qt[0]; r_beat <= b;
            r_data <= mem.exists(qa[0] + b) ? mem[qa[0] + b] : {8{32'hDEAD0000 | (qa[0] + b) & 16'hffff}};
            if (b + 1 == ql[0]) begin b = 0; void'(qa.pop_front()); void'(ql.pop_front()); void'(qt.pop_front()); void'(qd.pop_front()); end
            else b = b + 1;
        end
    end
endmodule

module tb_eng_be_die #(parameter integer L = 0, R = 0, EXPECT = 18, D = 12, BASE = 4, LIMIT = 16777216, LAT = 240,
                       JIT = 0, CMUT = 0, EPMUT = 0, PIPE = 0, HMUT = 0) (
    input  wire clk, rst_n,
    input  wire [84:0] c_cmd, output wire [8:0] c_done, output wire [1:0] c_st,
    input  wire [72:0] f_win, output wire [0:0] t_collective, output wire [281:0] t_ag, input wire [0:0] f_agc,
    input  wire [1123:0] f_ai, output wire [3:0] t_air, output wire [531:0] t_vm, input wire [15:0] f_vm,
    output reg  [31:0] acks, output reg [31:0] host_sent, output wire booted, output wire sw_fault
);
    import ot_hdc_engram_tables_shipped_pkg::*;
    localparam integer QW = ENG_RES_W, RW = ENG_ROW_W;
    // ---- relay-delayed narrow pairs
    wire [34:0] t_hq; wire [264:0] f_hr; wire [290:0] t_eb; wire [3:0] f_eb;
    reg [34:0] hq_p [0:D-1]; reg [264:0] hr_p [0:D-1]; reg [290:0] eb_p [0:D-1]; reg [3:0] ed_p [0:D-1];
    integer i;
    always @(posedge clk) begin
        hq_p[0] <= t_hq; hr_p[0] <= hr_src; eb_p[0] <= t_eb; ed_p[0] <= ed_src;
        for (i = 1; i < D; i = i + 1) begin hq_p[i] <= hq_p[i-1]; hr_p[i] <= hr_p[i-1]; eb_p[i] <= eb_p[i-1]; ed_p[i] <= ed_p[i-1]; end
    end
    assign f_hr = hr_p[D-1]; assign f_eb = ed_p[D-1];
    // ---- host driver
    reg [291:0] hw; wire [8:0] hc; integer cred = 8, seq = 0; reg [31:0] fp = 0; reg [255:0] hd; reg [31:0] ha;
    localparam integer NCSR = 2 + 64 + 1;
    function automatic [255:0] csr(input integer n);
        reg [255:0] d; begin
            d = 256'd0; d[255] = 1'b1; d[65:64] = 2'd3;
            if (n < 2) begin d[254:253] = 2'd1; d[66] = n[0]; d[96:67] = 30'd1073741696; d[126:97] = 30'd128;
                             d[156:127] = 30'd536870912; d[186:157] = 30'd805306368; d[216:187] = 30'd134217728; end
            else if (n < 66) begin d[254:253] = 2'd2; d[72:67] = n - 2; d[102:73] = BASE; d[132:103] = LIMIT; end
            else d[254:253] = 2'd3;
            csr = d; end
    endfunction
    function automatic [255:0] sect(input integer n);
        integer w; reg [255:0] d; begin for (w = 0; w < 8; w = w + 1) d[32*w +: 32] = n * 32'h9E3779B1 ^ (w * 32'h85EBCA77) ^ (L << 20) ^ (R << 24); sect = d; end
    endfunction
    integer w8; reg [255:0] hs;
    always @(posedge clk) begin
        hw <= 292'd0;
        if (!rst_n) begin cred = 8; seq = 0; fp = 0; acks <= 0; host_sent <= 0; end
        else begin
            cred = cred + hc[0];
            acks <= acks + hc[8:1];
            if (cred > 0 && seq <= NCSR + EXPECT) begin
                if (seq < NCSR) begin ha = 32'hffffffff; hd = csr(seq); end
                else if (seq < NCSR + EXPECT) begin
                    ha = {2'b11, 30'(seq - NCSR)}; hd = sect(seq - NCSR);
                    if (HMUT == 1 && seq - NCSR == 5) hd[7] = ~hd[7];          // MUT: a sector corrupted after the fingerprint
                    fp = fp ^ {2'b0, ha[29:0]}; hs = sect(seq - NCSR); for (w8 = 0; w8 < 8; w8 = w8 + 1) fp = fp ^ hs[32*w8 +: 32];
                end else begin ha = 32'hffffffff; hd = 256'd0; hd[65:64] = 2'd3; hd[63:32] = fp; hd[31:0] = EXPECT; end
                hw <= {2'd2, 1'b1, ha, hd, 1'b1}; cred = cred - 1; seq = seq + 1; host_sent <= host_sent + 1;
            end
        end
    end
    // ---- PCs: stack 0 (SW half) and stack 1 (core's SE half)
    wire [32*341-1:0] rq_sw, rq_se; wire [31:0] wd_sw, wd_se; wire [8895:0] rd_sw, rd_se;
    reg [8:0] ldv [0:63]; reg [9*30-1:0] lda [0:63]; reg [9*256-1:0] ldd [0:63];
    genvar gp;
    generate for (gp = 0; gp < 64; gp = gp + 1) begin : g_pc
        localparam integer S = gp / 32, P = gp % 32;
        wire rv_; wire [255:0] rdd; wire [16:0] rt; wire [3:0] rb; wire wd_;
        tb_eng_pc #(.LAT(LAT), .JIT(JIT)) u (.clk(clk), .rst_n(rst_n), .rq(S ? rq_se[341*P +: 341] : rq_sw[341*P +: 341]),
            .wd(wd_), .rv(rv_), .r_data(rdd), .r_tag(rt), .r_beat(rb), .ld_v(ldv[gp]), .ld_a(lda[gp]), .ld_d(ldd[gp]));
        if (S) begin : g1
            assign wd_se[P] = wd_; assign rd_se[256*P +: 256] = rdd; assign rd_se[8192 + 17*P +: 17] = rt;
            assign rd_se[8736 + 4*P +: 4] = rb; assign rd_se[8864 + P] = rv_;
        end else begin : g0
            assign wd_sw[P] = wd_; assign rd_sw[256*P +: 256] = rdd; assign rd_sw[8192 + 17*P +: 17] = rt;
            assign rd_sw[8736 + 4*P +: 4] = rb; assign rd_sw[8864 + P] = rv_;
        end
    end endgenerate
    // ---- eng_SE master
    dsfd_engram_c #(.MUT(CMUT), .EPMUT(EPMUT), .PIPE(PIPE), .BE(1), .EXPECT_SECTORS(EXPECT)) u_e (
        .ck(clk), .rst(rst_n), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st), .f_cfg({R[1:0], L[0]}), .f_win(f_win),
        .t_collective(t_collective), .t_ag(t_ag), .f_agc(f_agc), .f_ai(f_ai), .t_air(t_air), .t_vm(t_vm), .f_vm(f_vm),
        .t_hq(t_hq), .f_hr(f_hr), .t_eb(t_eb), .f_eb(f_eb), .hw(hw), .hc(hc), .rq(rq_se), .wd(wd_se), .rd(rd_se));
    // ---- svc_SW's half
    wire [264:0] hr_src; wire [3:0] ed_src; wire sw_rdy;
    wire [290:0] eb = eb_p[D-1]; wire [34:0] hq = hq_p[D-1];
    ot_s81_eng_half #(.STACK(0)) u_sw (.ck(clk), .rst_n(rst_n), .b_v(eb[0]), .b_type(eb[2:1]), .b_atom(eb[31:3]),
        .b_tag(eb[34:32]), .b_d(eb[290:35]), .bd_v(ed_src[0]), .bd_tag(ed_src[3:1]),
        .hq_v(hq[0]), .hq_atom(hq[31:1]), .hq_tag(hq[34:32]), .hq_cred(hr_src[0]), .hr_v(hr_src[1]), .hr_tag(hr_src[4:2]),
        .hr_idx(hr_src[8:5]), .hr_d(hr_src[264:9]), .rq(rq_sw), .wd(wd_sw), .rd(rd_sw), .ready(sw_rdy), .fault(sw_fault));
    assign booted = sw_rdy && u_e.be_rdy;
    // ---- lazy golden content at the router input (row requests of the lookup)
    function automatic [63:0] smix(input [63:0] x); reg [63:0] z; begin
        z = x + 64'h9E3779B97F4A7C15; z = (z ^ (z >> 30)) * 64'hBF58476D1CE4E5B9; z = (z ^ (z >> 27)) * 64'h94D049BB133111EB;
        smix = z ^ (z >> 31); end endfunction
    function automatic [31:0] crcb(input [31:0] c, input [7:0] b); integer q; reg [31:0] x; begin
        x = c; for (q = 7; q >= 0; q = q - 1) x = {x[30:0], 1'b0} ^ ((x[31] ^ b[q]) ? 32'h04C11DB7 : 32'd0); crcb = x; end endfunction
    function automatic [7:0] scale_of(input [63:0] key); reg [63:0] w; begin
        w = smix(key | 64'd32); scale_of = w[8] ? w[7:0] : 8'd107 + (w[7:0] % 41); end endfunction
    function automatic [34:0] inverse(input [4:0] p, input [30:0] a); reg [30:0] t; reg [4:0] bank; begin
        t = a >> 2; bank = (p ^ t ^ (t >> 5)) & 31; inverse = ({4'b0, t} << 7) | ({30'b0, bank} << 2) | (a & 3); end endfunction
    reg [63:0] cba [0:6];                 // column bases in atoms (rowstripe: 9 atoms a row)
    initial begin : cb
        integer j; cba[0] = 0;
        for (j = 0; j < 6; j = j + 1) cba[j+1] = cba[j] + 64'(ENG_PRIME[QW*(L*ENG_COLS + R*6 + j) +: QW]) * 9;
    end
    reg [7:0] rowb [0:287];
    task automatic fill_row(input [63:0] A);
        integer j, c, q; reg [63:0] res, grow, key, w; reg [31:0] cr;
        begin
            j = 0; for (q = 0; q < 6; q = q + 1) if (A >= cba[q]) j = q;
            c = L * ENG_COLS + R * 6 + j; res = (A - cba[j]) / 9;
            grow = res + ENG_OFFSET[RW*c +: RW]; key = ({56'd0, 8'(L)} << 40) | (grow << 6);
            for (q = 0; q < 256; q = q + 1) begin w = smix(key | (q >> 3)); rowb[q] = w[8*(q % 8) +: 8]; end
            rowb[256] = scale_of(key); cr = 32'hFFFFFFFF; for (q = 0; q < 257; q = q + 1) cr = crcb(cr, rowb[q]);
            for (q = 0; q < 4; q = q + 1) rowb[257 + q] = cr[8*q +: 8];
            for (q = 261; q < 288; q = q + 1) rowb[q] = 8'd0;
        end
    endtask
    integer k, q, pc, st; reg [30:0] lo; reg [34:0] g; reg [63:0] row;
    always @(posedge clk) begin
        for (k = 0; k < 64; k = k + 1) ldv[k] <= 9'd0;
        if (u_e.lk_hqv) begin
            row = u_e.lk_hqa / 9; st = row % 2; pc = (row / 2) % 32; lo = (row / 64) * 9 + BASE;
            fill_row(u_e.lk_hqa);
            for (k = 0; k < 9; k = k + 1) begin
                g = inverse(pc[4:0], lo + k);
                lda[st*32 + pc][30*k +: 30] <= g[29:0];
                for (q = 0; q < 32; q = q + 1) ldd[st*32 + pc][256*k + 8*q +: 8] <= rowb[32*k + q];
            end
            ldv[st*32 + pc] <= 9'h1ff;
        end
    end
endmodule
