`timescale 1ns/1ps
`default_nettype none
// hgi-1010/g3 (2026-10-11): the die's NATIVE IDX.INDEX path for the die-level e2e (tb_hgi_e2e IDX_NATIVE = 1), every
// block real RTL from the unit's selector ports down to the HBM controller:
//   ot_hgi_idx_unit (NGLOB 1, IKS 1; in the bench)  --fs / qb / kin / to / co / ev-->  hfd_idx_sel_native_qend (the
//   die's selector, SRAM line memories)  --q bus / score beats / credits over LEG-stage die nets-->  4 x
//   hfd_idx_score_native (one a stack, 16 keys a cycle, FA 6)  <--8 index-line ports + credits--  4 x
//   ot_hbm_svc_core_native IKS = 1 (the kind-2 stripe over the stack's 32 PCs, started by the unit's iks_e beat)
//   <--32 PC request / response lanes-->  DRAM controller MODEL (per PC: a 4-sector read a cycle, beats in order LAT
//   later, one a PC a cycle; tb_hgi_idx_iks's model) on the e2e HBM model (DPI e2e_hbm_sector).
// The controller model inverts the stripe's address map (ot_hbm_kport_map of (pc, bank {j[9:7], j[1:0]}, row0 +
// (j >> 10), col j[6:2]); row0 from the stack's e command) to the logical byte the export's key image sits at:
// (stack << 35) | (row0 << 20) + 32 (32 j + pc); a request the map cannot produce is FATAL.
module hgi_e2e_idxn #(
    parameter integer LEG = 24,          // relay stages per die net (q bus, score beats, score credits), each direction
    parameter integer LAT = 104          // DRAM first access (cycles), as the IKS unit bench
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [89:0]   fs,
    input  wire [1047:0] qb,
    output wire          qbr,
    input  wire [344:0]  kin,
    output wire [611:0]  to,
    input  wire          toc,
    output wire [71:0]   co,
    input  wire          coc,
    output wire [1:0]    ev,
    input  wire [511:0]  iks_e,
    output wire [3:0]    ik_fault_seen   // a stack's svc raised ik_fault (sticky; the bench fails on it)
);
    import "DPI-C" function void e2e_hbm_sector(input longint addr, input bit we, input bit [255:0] wd,
                                                input bit [31:0] strb, output bit [255:0] rd);
    wire [2283:0] qo; wire [2439:0] si; wire [3:0] sc; wire co_ql;
    hfd_idx_sel_native_qend u_sel (.ck(clk), .rst(rst_n), .fs(fs), .qb(qb), .qbr(qbr), .kin(kin), .qo(qo), .si(si), .sc(sc),
        .to(to), .toc(toc), .co(co), .coc(coc), .ev(ev), .co_quarter_last(co_ql));
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : gs
        // ---- svc stack g (IKS stripe only: no SM / KV / write traffic in this slot)
        wire [31:0] kv_, rrdy, kwe; wire [959:0] kaddr; wire [127:0] klen; wire [543:0] ktag;
        wire [8791:0] lines; wire ik_done, ik_fault; wire [7:0] ikc;
        reg  [31:0] respv; reg [127:0] respb; reg [543:0] respt; reg [8191:0] respd;
        ot_hbm_svc_core_native #(.NATIVE(1), .NATIVE_CHAIN(0), .IKS(1), .E_ST(2), .XST(0)) u_svc (.ck(clk), .rst(rst_n),
            .q_d(336'd0), .q_v(8'd0), .q_fclk(8'd0), .q_rdy(), .line(), .fclk(), .e_d(iks_e[g*128 +: 128]), .e_fclk(clk),
            .kv(), .ik(), .phy_clk(), .phy_rst_n(), .k_v(kv_), .k_rdy(32'hffff_ffff), .k_addr(kaddr), .k_len(klen),
            .k_tag(ktag), .k_we(kwe), .k_wdata(), .k_wstrb(), .kr_v(respv), .kr_rdy(rrdy), .kr_tag(respt), .kr_beat(respb),
            .kr_data(respd), .w_v(), .w_rdy(1'b0), .w_addr(), .w_len(), .w_tag(), .w_room(8'd0), .wr_v(8'd0), .wr_rdy(),
            .wr_tag(80'd0), .wr_beat(40'd0), .wr_data(2048'd0), .wq_d(292'd0), .wq_fclk(1'b0), .wq_g(), .k_wr_done(32'd0),
            .wq_source(2'd0), .wq_source_g(), .wq_source_fault(), .wq_source_busy(), .wq_pending(), .kvs(), .kvs_done(),
            .ik_credit(ikc), .ik_lines(lines), .ik_done(ik_done), .ik_fault(ik_fault), .outer_write_pending(1'b0),
            .native_v(1'b0), .native_rdy(), .native_pc(5'd0), .native_addr(30'd0), .native_tag(16'h0), .native_len(4'd1),
            .native_rsp_v(), .native_rsp_rdy(1'b1), .native_rsp_pc(), .native_rsp_tag(), .native_rsp_beat(),
            .native_rsp_data(), .native_fault());
        // ---- DRAM controller model of stack g on the e2e HBM model
        reg [14:0] row0; reg fseen = 1'b0;
        assign ik_fault_seen[g] = fseen;
        reg [16:0] qt [0:31][0:255]; reg [3:0] qbt [0:31][0:255]; reg [255:0] qd [0:31][0:255]; longint qr [0:31][0:255];
        integer head [0:31], tail [0:31], cnt [0:31];
        longint c = 0;
        initial begin for (int p = 0; p < 32; p++) begin head[p] = 0; tail[p] = 0; cnt[p] = 0; end row0 = 15'd0;
            respv = 0; respb = 0; respt = 0; respd = 0; end
        function automatic longint logical(input integer pc, input [29:0] a);
            integer row, bhi, col, blo, bank, j, hi5; reg [29:0] fw;
            begin
                row = int'(a >> 15); bhi = int'((a >> 12) & 7); col = int'((a >> 7) & 31); blo = int'(a & 3);
                bank = ((bhi ^ ((row >> 2) & 7)) << 2) | (blo ^ (row & 3));
                j = ((row - int'(row0)) << 10) | ((bank >> 2) << 7) | (col << 2) | (bank & 3);
                hi5 = ((row & 3) << 3) | bhi;
                fw = 30'((row << 15) | (bhi << 12) | (col << 7) | (((pc ^ col ^ hi5) & 31) << 2) | blo);
                if (row < int'(row0) || fw !== a)
                    $fatal(1, "E2E FAIL: IDXN stack %0d PC %0d: DRAM sector %h is not on the IKS stripe (row0 %0d)", g, pc, a, row0);
                logical = (longint'(g) << 35) | (longint'(row0) << 20) | (longint'(32) * (longint'(32) * j + pc));
            end
        endfunction
        always @(posedge clk) begin
            c <= c + 1;
            respv <= 32'd0;
            if (iks_e[g*128]) row0 <= iks_e[g*128 + 3 +: 15];      // payload bit i = e_d[i + 1]: row0 = payload [16:2]
            if (rst_n && ik_fault) fseen <= 1'b1;
            if (rst_n) for (int p = 0; p < 32; p++) begin
                if (cnt[p] > 0 && rrdy[p] && qr[p][head[p]] <= c) begin
                    respv[p] <= 1'b1; respt[p*17 +: 17] <= qt[p][head[p]]; respb[p*4 +: 4] <= qbt[p][head[p]];
                    respd[p*256 +: 256] <= qd[p][head[p]];
                    head[p] = (head[p] + 1) % 256; cnt[p] = cnt[p] - 1;
                end
                if (kv_[p]) begin
                    if (kwe[p]) $fatal(1, "E2E FAIL: IDXN stack %0d: write request on the key stream", g);
                    for (int b = 0; b < int'(klen[p*4 +: 4]); b++) begin : bt
                        bit [255:0] d;
                        e2e_hbm_sector(logical(p, kaddr[p*30 +: 30] + 30'(b)), 1'b0, 256'd0, 32'd0, d);
                        qt[p][tail[p]] = ktag[p*17 +: 17]; qbt[p][tail[p]] = 4'(b); qd[p][tail[p]] = d;
                        qr[p][tail[p]] = c + LAT; tail[p] = (tail[p] + 1) % 256; cnt[p] = cnt[p] + 1;
                    end
                    if (cnt[p] > 64) $fatal(1, "E2E FAIL: IDXN stack %0d PC %0d: controller overflow", g, p);
                end
            end
        end
        // ---- scorer of stack g: index lines straight from the svc (the stack-side slot), q bus / scores / credits
        // over the LEG-stage die nets to the selector
        wire [570:0] qi; wire [609:0] so; wire scr; wire [3:0] st_unused;
        hfd_idx_score_native u_s (.ck(clk), .rst(rst_n), .ik(lines), .ikc(ikc), .q(qi), .s(so), .sc(scr), .st(st_unused));
        wire qv_, sv_, cv_; wire [569:0] qd_; wire [608:0] sd_; wire [0:0] cd_unused;
        hfd_idx_pipe #(.W(570), .N(LEG)) u_pq (.ck(clk), .rst_n(rst_n), .v(qo[g*571]), .d(qo[g*571+1 +: 570]), .qv(qv_), .q(qd_));
        assign qi = {qd_, qv_};
        hfd_idx_pipe #(.W(609), .N(LEG)) u_ps (.ck(clk), .rst_n(rst_n), .v(so[0]), .d(so[609:1]), .qv(sv_), .q(sd_));
        assign si[g*610 +: 610] = {sd_, sv_};
        hfd_idx_pipe #(.W(1), .N(LEG)) u_pc (.ck(clk), .rst_n(rst_n), .v(sc[g]), .d(1'b0), .qv(cv_), .q(cd_unused));
        assign scr = cv_;
    end endgenerate
endmodule
`default_nettype wire
