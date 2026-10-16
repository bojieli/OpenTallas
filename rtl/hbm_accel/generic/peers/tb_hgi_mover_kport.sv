`timescale 1ps/1ps
// ---------------------------------------------------------------------------------------------------------------------
// tb_hgi_mover_kport (hgi-1010/c 2026-10-10): RATE + exactness bench of the DMA mover's HBM load path on the REAL loader
// kport (ot_hfd_loader_kport ND 5: lane 0 = the mover's lane 2 role (writes / serial engine), lanes 1..4 = the mover's
// read lanes for stacks 0..3; NO 16, RB 64, NQ 4) and four behavioural svc stacks (ot_hbm_svc_core_native NATIVE_NO NO +
// the refresh-aware PHY model ot_hdc_v41x_idx_hbm, MEM_MODE 1: a sector's data is a pattern of its stack-local sector
// address), through CH register stages each way on the die's lq / lr chains (as tb_hfd_loader_kport).  The bench XORs
// each stack's response data with a stack mask, so a sector read from the wrong stack is visible.
// The VM destination is the mover's wide write port, captured word by word (wl_done one edge later).
// Cases: LOAD moves driven on the mover's move port; every destination word is checked against the pattern decoded in
// the source format; B/cycle = source bytes / (move accepted -> done).  A STRIPE4 move with an unaligned row start must
// fault.  XLAT: extra PHY request + response latency (ps; 39,000 ~ RTT 104 cycles, 76,000 ~ RTT 160).
// STOREs (hgi-1010/c, WR_G protocol with [svc]): the VM source is a packet-client model (4 outstanding, VLAT, data a
// hash of the word address); the svc WRITE side is modelled here per stack (the PS native endpoint contract): a WNO-deep
// wq taking one packet a cycle, popping one a cycle (stalled on a random 1/WSTALL of the cycles) into the stack memory,
// WR_G = the Gray count of pops on lr[291:284].  Every destination word is checked; STORE B/cycle likewise.
// Prints MOVER-KPORT PASS / FAIL and, per case, RATE <case> <B/cycle>.
// ---------------------------------------------------------------------------------------------------------------------
module tb_hgi_mover_kport;
    parameter integer MUT = 0;
    parameter integer KMUT = 0;                         // kport mutant (5: a write acknowledged at send)
    parameter integer NO = 16;
    parameter integer RB = 64;
    parameter integer XLAT = 76000;
    parameter integer CH = 12;
    parameter integer NQ = 4;
    parameter integer HC_MIN = 23800;                   // B/cycle x 1000 gate for the HC row (STRIPE4 FP32 4 x 5,120)
    parameter integer WNO = 16;                         // svc wq depth = kport write credits a stack
    parameter integer WSTALL = 8;                       // the svc wq pop stalls on 1 / WSTALL of the cycles
    parameter integer VLAT = 8;                         // VM packet client response latency
    parameter integer ST_MIN = 0;                       // B/cycle x 1000 gate for the STRIPE4 swapout store (0: report only)
    parameter integer VR2 = 0;                          // 1: VM-source sectors on the DMA wide read group model (b's contract)
    parameter integer GLAT = 12;                        // read group: request -> response edges (die hops + the VM core)
    reg clk = 0; always #416 clk = ~clk; reg rst_n = 0;
    // ---- mover
    reg mv_v = 0; reg [226:0] mv = 0; wire mv_rdy, mv_done, mv_fault, mv_src;
    wire k_req_v, k_req_we, k_rsp_rdy; wire [36:0] k_addr; wire [255:0] k_wd; wire [31:0] k_ws; wire [15:0] k_tag;
    wire [3:0] r_req_v, r_req_rdy, r_rsp_v, r_rsp_rdy, r_rsp_last; wire [4*37-1:0] r_req_addr; wire [15:0] r_req_len;
    wire [63:0] r_req_tag, r_rsp_tag; wire [1023:0] r_rsp_data, r_req_wdata; wire [3:0] r_req_we, r_rsp_we; wire [127:0] r_req_wstrb;
    wire [337:0] vmq; wire [279:0] wl; reg wl_done = 0; reg [273:0] vmr = 0;
    wire [4:0] kp_rdy, kp_rsp_v, kp_rsp_we, kp_last; wire [79:0] kp_rtag; wire [5*256-1:0] kp_rdata; wire kp_fault;
    wire [512:0] vr2q; reg [8256:0] vr2r = '0;
    ot_hgi_dma_mover #(.MUT(MUT), .VR2(VR2)) u_m (.clk(clk), .rst_n(rst_n), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done),
        .mv_fault(mv_fault), .mv_src(mv_src), .fence_v(1'b0), .fence_rdy(), .fence_done(),
        .k_req_v(k_req_v), .k_req_rdy(kp_rdy[0]), .k_req_we(k_req_we), .k_req_addr(k_addr), .k_req_wdata(k_wd),
        .k_req_wstrb(k_ws), .k_req_tag(k_tag), .k_rsp_v(kp_rsp_v[0]), .k_rsp_rdy(k_rsp_rdy), .k_rsp_we(kp_rsp_we[0]),
        .k_rsp_data(kp_rdata[255:0]), .k_fault(kp_fault),
        .r_req_v(r_req_v), .r_req_rdy(r_req_rdy), .r_req_addr(r_req_addr), .r_req_len(r_req_len), .r_req_tag(r_req_tag), .r_req_we(r_req_we), .r_req_wdata(r_req_wdata), .r_req_wstrb(r_req_wstrb),
        .r_rsp_v(r_rsp_v), .r_rsp_we(r_rsp_we), .r_rsp_rdy(r_rsp_rdy), .r_rsp_tag(r_rsp_tag), .r_rsp_last(r_rsp_last), .r_rsp_data(r_rsp_data), .vr2q(vr2q), .vr2r(vr2r),
        .vmq(vmq), .vmr(vmr), .wl(wl), .wl_done(wl_done));
    assign r_req_rdy = kp_rdy[4:1]; assign r_rsp_v = kp_rsp_v[4:1]; assign r_rsp_tag = kp_rtag[79:16];
    assign r_rsp_last = kp_last[4:1]; assign r_rsp_data = kp_rdata[5*256-1:256]; assign r_rsp_we = kp_rsp_we[4:1];
    wire [4*350-1:0] lq; wire [4*293-1:0] lr;
    ot_hfd_loader_kport #(.ENABLE(1), .ND(5), .STACK_BYTES(36'h800000000), .NO(NO), .NQ(NQ), .RB(RB), .WNO(WNO), .MUT(KMUT)) u_kp (.clk(clk), .rst_n(rst_n),
        .req_v({r_req_v, k_req_v}), .req_rdy(kp_rdy), .req_we({r_req_we, k_req_we}), .req_addr({r_req_addr, k_addr}),
        .req_wdata({r_req_wdata, k_wd}), .req_wstrb({r_req_wstrb, k_ws}), .req_tag({r_req_tag, k_tag}), .req_len({r_req_len, 4'd1}),
        .rsp_v(kp_rsp_v), .rsp_rdy({r_rsp_rdy, k_rsp_rdy}), .rsp_we(kp_rsp_we), .rsp_tag(kp_rtag), .rsp_data(kp_rdata),
        .rsp_last(kp_last), .lq(lq), .lr(lr), .fault(kp_fault));
    function automatic [255:0] smask(input integer s);
        smask = {8{32'h1F2E3D4C * (s + 1)}};
    endfunction
    function automatic [255:0] pat(input [29:0] s);            // = ot_hdc_v41x_idx_hbm MEM_MODE 1
        for (integer w = 0; w < 8; w = w + 1) pat[32*w +: 32] = (s * 32'd8 + w) * 32'h9E3779B1 ^ 32'h5bd1e995;
    endfunction
    reg [255:0] hm [bit [31:0]];                            // written sectors {stack, local sector}
    integer errs = 0;
    function automatic [31:0] vmw(input [31:0] a); vmw = (a * 32'h2545F491) ^ (a >> 7) ^ 32'hA5A50F0F; endfunction
    // ---- VM packet client model: reads in order, VLAT edges later (data vmw(word))
    reg [26:0] vq [0:15]; longint vd [0:15]; integer vh = 0, vn = 0; longint vt = 0;
    always @(posedge clk) begin
        vt <= vt + 1; vmr[273] <= 1'b0;
        if (vn > 0 && vd[vh % 16] <= vt) begin
            for (integer w = 0; w < 8; w = w + 1) vmr[32*w +: 32] <= vmw({vq[vh % 16], 3'(w)});
            vmr[273] <= 1'b1; vh = vh + 1; vn = vn - 1;
        end
        if (rst_n && vmq[337]) begin
            if (vmq[336]) begin $display("FATAL unexpected VM write packet"); errs = errs + 1; end
            vq[(vh + vn) % 16] = vmq[335:309]; vd[(vh + vn) % 16] = vt + VLAT; vn = vn + 1;
            if (vn > 4) begin $display("FATAL VM client > 4 outstanding"); errs = errs + 1; end
        end
    end
    // ---- VM DMA wide read group model (VR2): grant follows c_req, a lane's request is answered in order GLAT edges later,
    //      its credit returns 2 edges after the request (it reached the bank); a request without a credit or a grant is fatal
    reg [14:0] gq [0:31][0:63]; longint gd [0:31][0:63]; integer gh [0:31], gn [0:31]; integer gcr [0:31];
    initial for (integer b = 0; b < 32; b = b + 1) begin gh[b] = 0; gn[b] = 0; gcr[b] = 32; end
    reg [31:0] gcr_d1, gcr_d2;
    always @(posedge clk) begin
        vr2r[8256] <= vr2q[512];
        gcr_d2 <= gcr_d1; gcr_d1 <= 32'd0; vr2r[8255:8224] <= gcr_d2;
        for (integer b = 0; b < 32; b = b + 1) begin
            vr2r[b*257 + 256] <= 1'b0;
            if (gn[b] > 0 && gd[b][gh[b] % 64] <= vt) begin
                for (integer w = 0; w < 8; w = w + 1) vr2r[b*257 + 32*w +: 32] <= vmw({17'd0, gq[b][gh[b] % 64], 3'(w)});
                vr2r[b*257 + 256] <= 1'b1; gh[b] = gh[b] + 1; gn[b] = gn[b] - 1;
            end
            if (rst_n && vr2q[b*16 + 15]) begin
                if (!vr2r[8256]) begin $display("FATAL read group request without the grant"); errs = errs + 1; end
                if (vr2q[b*16 +: 5] != 5'(b)) begin $display("FATAL read group lane %0d got sector %h", b, vr2q[b*16 +: 15]); errs = errs + 1; end
                gq[b][(gh[b] + gn[b]) % 64] = vr2q[b*16 +: 15]; gd[b][(gh[b] + gn[b]) % 64] = vt + GLAT; gn[b] = gn[b] + 1;
                gcr_d1[b] <= 1'b1;
            end
        end
    end
    // ---- four svc stacks (as tb_hfd_loader_kport)
    genvar s, gp;
    for (s = 0; s < 4; s = s + 1) begin : g_st
        reg [349:0] qp [0:CH]; reg [292:0] rp [0:CH]; wire [292:0] r_svc;
        reg [7:0] popc = 0;                                  // svc write model: pops (WR_G = Gray(popc))
        always @* begin qp[0] = lq[s*350 +: 350]; rp[0] = {r_svc[292], popc ^ (popc >> 1), r_svc[283:0] ^ {1'd0, smask(s), 27'd0}}; end
        for (gp = 0; gp < CH; gp = gp + 1) begin : g_ch
            always @(posedge clk or negedge rst_n) if (!rst_n) begin qp[gp+1] <= '0; rp[gp+1] <= '0; end
                                                   else begin qp[gp+1] <= qp[gp]; rp[gp+1] <= rp[gp]; end
        end
        wire [349:0] q = qp[CH];
        assign lr[s*293 +: 293] = rp[CH];
        reg [290:0] wq [0:63]; integer wh = 0, wn = 0;
        always @(posedge clk) if (!rst_n) begin wh = 0; wn = 0; popc <= 8'd0; end else begin
            if (wn > 0 && ($urandom % WSTALL) != 0) begin                       // pop into the PC queue = visible
                hm[{2'(s), wq[wh % 64][34:5]}] = wq[wh % 64][290:35]; wh = wh + 1; wn = wn - 1; popc <= popc + 8'd1;
            end
            if (q[0]) begin
                if (wn >= WNO) begin $display("FATAL svc wq overflow on stack %0d", s); errs = errs + 1; end
                wq[(wh + wn) % 64] = q[291:1]; wn = wn + 1;
            end
        end
        wire [31:0] k_v, k_rdy, k_we, kr_v, kr_rdy, k_wr_done; wire [959:0] k_addr; wire [127:0] k_len, kr_beat; wire [543:0] k_tag, kr_tag;
        wire [8191:0] k_wdata, kr_data; wire [1023:0] k_wstrb; wire [31:0] wq_source_g, wq_source_busy;
        wire wq_source_fault, wq_pending, native_fault, phy_rst_n;
        wire n_rdy, n_rsp_v; wire [4:0] n_rsp_pc; wire [15:0] n_rsp_tag; wire [3:0] n_rsp_beat; wire [255:0] n_rsp_data;
        assign r_svc = {wq_source_fault, wq_source_g[31:24], native_fault, n_rsp_data, n_rsp_beat, n_rsp_tag, n_rsp_pc, n_rsp_v, n_rdy};
        ot_hbm_svc_core_native #(.NATIVE(1), .WB(1), .WB_SOURCE_ACK(1), .KVS(1), .XST(0), .WQ_ST(1), .NATIVE_NO(NO), .NATIVE_NQ(NQ),
            .NATIVE_CHAIN(1)) service (
            .ck(clk), .rst(rst_n), .q_d(336'b0), .q_v(8'b0), .q_fclk(8'b0), .e_d(128'b0), .e_fclk(1'b0),
            .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .k_we(k_we), .k_wdata(k_wdata), .k_wstrb(k_wstrb),
            .kr_v(kr_v), .kr_rdy(kr_rdy), .kr_tag(kr_tag), .kr_beat(kr_beat), .kr_data(kr_data),
            .w_rdy(1'b1), .w_room(8'hff), .wr_v(8'b0), .wr_tag(80'b0), .wr_beat(40'b0), .wr_data(2048'b0),
            .wq_d(292'd0), .wq_fclk(clk), .wq_source(2'd2), .wq_source_g(wq_source_g), .wq_source_fault(wq_source_fault),
            .wq_source_busy(wq_source_busy), .wq_pending(wq_pending), .k_wr_done(k_wr_done), .phy_rst_n(phy_rst_n),
            .outer_write_pending(q[345]),
            .native_v(q[292]), .native_rdy(n_rdy), .native_pc(q[297:293]), .native_addr(q[327:298]), .native_tag(q[343:328]),
            .native_len(q[349:346]),
            .native_rsp_v(n_rsp_v), .native_rsp_rdy(q[344]), .native_rsp_pc(n_rsp_pc), .native_rsp_tag(n_rsp_tag),
            .native_rsp_beat(n_rsp_beat), .native_rsp_data(n_rsp_data), .native_fault(native_fault));
        ot_hdc_v41x_idx_hbm #(.NPC(32), .AW(30), .DW(256), .MEM_WORDS(64), .TAGW(17), .LENW(4), .BEATW(4), .QD(64), .REFPB(3),
            .MEM_MODE(1), .REQ_PS(10000 + XLAT / 2), .RSP_PS(10000 + XLAT - XLAT / 2)) phy (
            .clk(clk), .rst_n(phy_rst_n), .req_v(k_v), .req_rdy(k_rdy), .req_addr(k_addr), .req_len(k_len), .req_tag(k_tag),
            .req_we(k_we), .req_wdata(k_wdata), .req_wstrb(k_wstrb), .wr_done(k_wr_done), .rsp_v(kr_v), .rsp_rdy(kr_rdy),
            .rsp_tag(kr_tag), .rsp_beat(kr_beat), .rsp_data(kr_data));
    end
    // ---- VM wide port capture
    reg [31:0] vm [int];
    always @(posedge clk) begin
        wl_done <= rst_n && wl[279];
        if (rst_n && wl[279]) for (integer q = 0; q < 8; q = q + 1) if (wl[q]) vm[{wl[278:264], 3'(q)}] = wl[8 + 32*q +: 32];
    end
    // ---- expected source element -> VM word
    function automatic [31:0] i8_f(input [7:0] c);
        reg [7:0] a; reg [2:0] p;
        begin
            a = c[7] ? (~c + 8'd1) : c; p = 3'd0;
            for (integer k = 0; k < 8; k = k + 1) if (a[k]) p = 3'(k);
            i8_f = (a == 8'd0) ? 32'd0 : {c[7], 8'd127 + {5'd0, p}, ({15'd0, a} << (5'd23 - {2'd0, p})) & 23'h7FFFFF};
        end
    endfunction
    function automatic [31:0] e4m3_f(input [7:0] c);
        reg [3:0] e; reg [2:0] m; reg [1:0] p;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 4'hF && m == 3'h7) e4m3_f = 32'h7FC00000;
            else if (e == 4'd0) begin
                if (m == 3'd0) e4m3_f = {c[7], 31'd0};
                else begin p = m[2] ? 2'd2 : m[1] ? 2'd1 : 2'd0;
                    e4m3_f = {c[7], 8'd127 - 8'd9 + {6'd0, p}, ({20'd0, m} << (5'd23 - {3'd0, p})) & 23'h7FFFFF}; end
            end else e4m3_f = {c[7], 8'd120 + {4'd0, e}, m, 20'd0};
        end
    endfunction
    function automatic [7:0] hbyte(input [36:0] a);            // the byte at HBM address a (stack a[36:35])
        reg [255:0] d; d = pat(a[34:5]) ^ smask(a[36:35]); hbyte = d[8*a[4:0] +: 8];
    endfunction
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    integer ncase = 0, nwords = 0;
    // run one LOAD: src fmt f, HBM base (40 b incl. the stripe code), stride (bytes), dst VM base / stride (words), m, n
    task automatic load(input [127:0] name, input integer f, input [39:0] hb, input [31:0] hst, input [39:0] vb, input [31:0] vst,
                        input integer m, input integer n, input integer expect_fault);
        integer t0, t1, es, o, i, k, bad; reg [36:0] ra; reg [31:0] raw, want, got; reg strp; real bpc;
        begin
            es = (f == 0 || f == 5) ? 4 : (f == 1) ? 2 : 1; strp = hb[39:37] == 3'd1;
            vm.delete();
            @(negedge clk);
            mv = {21'(n), 20'(m), 16'd1, vst, vb, (f == 5) ? 3'd5 : 3'd0, 2'd1, 16'd1, hst, hb, 3'(f), 2'd0};
            mv_v = 1; while (!mv_rdy) @(negedge clk); t0 = cyc; @(negedge clk); mv_v = 0;
            while (!mv_done && !mv_fault && cyc - t0 < 2000000) @(negedge clk);
            t1 = cyc;
            if (expect_fault) begin
                if (!mv_fault) begin $display("FAIL %0s: expected a fault", name); errs = errs + 1; end
                else $display("ok %0s: faulted as expected", name);
                rst_n = 0; repeat (4) @(posedge clk); rst_n = 1; repeat (20) @(posedge clk);
            end else begin
                if (!mv_done || mv_fault) begin $display("FAIL %0s: done %0d fault %0d after %0d cycles", name, mv_done, mv_fault, t1 - t0); errs = errs + 1; end
                repeat (4) @(posedge clk);
                bad = 0;
                for (o = 0; o < m; o = o + 1) for (i = 0; i < n; i = i + 1) begin
                    ra = strp ? {2'(hb[36:35] + 2'(o)), 35'(hb[34:0] + 35'(o) * hst + 35'(i * es))} : 37'(hb + 40'(o) * hst + 40'(i * es));
                    raw = 32'd0; for (k = 0; k < es; k = k + 1) raw[8*k +: 8] = hbyte(ra + 37'(k));
                    want = (f == 0 || f == 5) ? raw : (f == 1) ? {raw[15:0], 16'd0} : (f == 2) ? e4m3_f(raw[7:0]) : i8_f(raw[7:0]);
                    got = vm.exists(int'(vb + o * vst + i)) ? vm[int'(vb + o * vst + i)] : 32'hDEADDEAD;
                    if (got !== want) begin if (bad < 4) $display("FAIL %0s row %0d elem %0d: %h want %h", name, o, i, got, want); bad = bad + 1; end
                    nwords = nwords + 1;
                end
                errs = errs + bad;
                bpc = (1.0 * m * n * es) / (t1 - t0);
                $display("RATE %0s %0.2f B/cycle (%0d B in %0d cycles)%0s", name, bpc, m * n * es, t1 - t0, bad ? " DATA BAD" : "");
                if (name == "hc_row" && bpc * 1000 < HC_MIN) begin $display("FAIL hc_row rate %0.2f < %0.2f", bpc, HC_MIN / 1000.0); errs = errs + 1; end
            end
            ncase = ncase + 1;
        end
    endtask
    // STORE: VM FP32 / U32 words (vmw) -> HBM rows (FP32 / U32), whole sectors; STRIPE4 destination when hb[39:37] = 1
    task automatic store(input [127:0] name, input integer f, input [39:0] vb, input [31:0] vst, input [39:0] hb, input [31:0] hst,
                         input integer m, input integer n, input integer expect_fault);
        integer t0, t1, ts, o, i, bad; reg [36:0] ra; reg [31:0] want, got; reg strp; real bpc; reg [255:0] sec;
        begin
            strp = hb[39:37] == 3'd1;
            hm.delete();
            @(negedge clk);
            mv = {21'(n), 20'(m), 16'd1, hst, hb, 3'(f), 2'd0, 16'd1, vst, vb, (f == 5) ? 3'd5 : 3'd0, 2'd1};
            mv_v = 1; while (!mv_rdy) @(negedge clk); t0 = cyc; ts = -1; @(negedge clk); mv_v = 0;
            while (!mv_done && !mv_fault && cyc - t0 < 2000000) begin if (mv_src && ts < 0) ts = cyc; @(negedge clk); end
            if (mv_src && ts < 0) ts = cyc;
            t1 = cyc;
            // hgi-1010/tput1: the posted retire point (every source sector read and landed) = mv_src
            $display("SRC %0s source consumed %0d cycles after accept (done %0d)", name, ts - t0, t1 - t0);
            if (expect_fault) begin
                if (!mv_fault) begin $display("FAIL %0s: expected a fault", name); errs = errs + 1; end
                else $display("ok %0s: faulted as expected", name);
                rst_n = 0; repeat (4) @(posedge clk); rst_n = 1; repeat (20) @(posedge clk);
            end else begin
                if (!mv_done || mv_fault) begin $display("FAIL %0s: done %0d fault %0d after %0d cycles", name, mv_done, mv_fault, t1 - t0); errs = errs + 1; end
                repeat (4) @(posedge clk);
                bad = 0;
                for (o = 0; o < m; o = o + 1) for (i = 0; i < n; i = i + 1) begin
                    ra = strp ? {2'(hb[36:35] + 2'(o)), 35'(hb[34:0] + 35'(o) * hst + 35'(i * 4))} : 37'(hb + 40'(o) * hst + 40'(i * 4));
                    want = vmw(32'(vb + o * vst + i));
                    sec = hm.exists({ra[36:35], ra[34:5]}) ? hm[{ra[36:35], ra[34:5]}] : {8{32'hDEADDEAD}};
                    got = sec[32 * ra[4:2] +: 32];
                    if (got !== want) begin if (bad < 4) $display("FAIL %0s row %0d elem %0d: %h want %h", name, o, i, got, want); bad = bad + 1; end
                    nwords = nwords + 1;
                end
                if (hm.num() != (m * n * 4) / 32) begin $display("FAIL %0s: %0d sectors written, %0d expected", name, hm.num(), (m * n * 4) / 32); bad = bad + 1; end
                errs = errs + bad;
                bpc = (1.0 * m * n * 4) / (t1 - t0);
                $display("RATE %0s %0.2f B/cycle (%0d B in %0d cycles)%0s", name, bpc, m * n * 4, t1 - t0, bad ? " DATA BAD" : "");
                if (name == "swap_stripe" && bpc * 1000 < ST_MIN) begin $display("FAIL swap_stripe rate %0.2f < %0.2f", bpc, ST_MIN / 1000.0); errs = errs + 1; end
            end
            ncase = ncase + 1;
        end
    endtask
    initial begin
        repeat (4) @(posedge clk); rst_n = 1; repeat (40) @(posedge clk);
        load("hc_row",       0, {3'd1, 2'd1, 35'h0040000}, 0,    40'd4096,  5120, 4, 5120, 0);   // HC weight row, STRIPE4
        load("one_stack",    0, {3'd0, 2'd2, 35'h0100000}, 0,    40'd4096,  5120, 1, 5120, 0);   // linear, one stack
        load("bf16_stripe",  1, {3'd1, 2'd3, 35'h0200000}, 4096, 40'd0,     1008, 9, 1000, 0);
        load("fp8_unalign",  2, {3'd0, 2'd0, 35'h0300003}, 1001, 40'd7,     400,  5, 333,  0);
        load("i8_stripe",    4, {3'd1, 2'd0, 35'h0400000}, 32,   40'd800,   64,   6, 64,   0);
        load("u32_rows",     5, {3'd0, 2'd1, 35'h0500020}, 2080, 40'd16000, 520,  7, 500,  0);
        load("fp32_stripe2", 0, {3'd1, 2'd2, 35'h0600000}, 640,  40'd20000, 168,  13, 161, 0);
        load("stripe_unal",  0, {3'd1, 2'd0, 35'h0700004}, 0,    40'd0,     64,   4, 64,   1);   // must fault
        store("swap_stripe", 0, 40'd1024,  6784, {3'd1, 2'd2, 35'h0800000}, 0,     4, 6784, 0);  // ~106 KB, STRIPE4 destination
        store("swap_linear", 0, 40'd1024,  6784, {3'd0, 2'd1, 35'h0900000}, 27136, 4, 6784, 0);  // the same, one stack
        // hgi-1010/tput1: DS DMA.KVWB_DS production shape (ds_native window_row_append): one 512-word FP32 VM row ->
        // its WIN ring slot (2,048 B, one stack), alone on the mover
        store("kvwb_row",    0, 40'd2048,  512,  {3'd0, 2'd1, 35'h0c00800}, 2048,  1, 512,  0);
        store("u32_rows",    5, 40'd96,    104,  {3'd0, 2'd3, 35'h0a00000}, 4096,  9, 96,   0);
        store("partial_row", 0, 40'd0,     64,   {3'd0, 2'd0, 35'h0b00000}, 256,   2, 60,   1);  // 240 B rows: must fault
        store("unal_base",   0, 40'd0,     64,   {3'd0, 2'd0, 35'h0b00010}, 256,   2, 64,   1);  // must fault
        if (kp_fault) begin $display("FAIL kport fault"); errs = errs + 1; end
        if (errs == 0) $display("MOVER-KPORT PASS %0d cases, %0d words (NO %0d RB %0d XLAT %0d)", ncase, nwords, NO, RB, XLAT);
        else $display("MOVER-KPORT FAIL %0d errors", errs);
        $finish;
    end
endmodule
