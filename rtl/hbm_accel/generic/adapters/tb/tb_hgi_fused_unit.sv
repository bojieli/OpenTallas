`timescale 1ns/1ps
// hgi-adapters (2026-10-09): D1 bench of the FUSED die body: ot_hgi_fused_record UNIT = 1 (micro-ops on an internal
// ot_hgi_su_unit: stage / real ot_hdc_v41x_vec / drain) + the gain DMA on the REAL ot_hgi_dma_mover, all on the REAL
// HGI VM (ot_hgi_vm_unit NC 3: 0 the FUSED unit, 1 the mover, 2 this bench) and a kport-lane HBM model.  Vectors:
// tools/hgi_adapters/fused_bench.py DATA cases (hbm-sim CF-NORM, Qwen ROW_NORM shapes, DS HC_PRE_NORM / HC_POST):
// VM out == expected.  Prints HGI_FUSED_UNIT PASS / FAIL.
module tb_hgi_fused_unit;
    `include "fu_sizes.svh"
`ifndef VLQ
 `ifdef HCE
  `define VLQ 32
 `else
  `define VLQ 8
 `endif
`endif
    reg clk = 0; always #1 clk = ~clk;
    reg [1214:0] recm [0:NREC-1]; reg [686:0] expm [0:NREC-1]; reg [287:0] casem [0:NCASE-1];
    reg [63:0] vmim [0:NVMI-1]; reg [63:0] vmem [0:NVME-1]; reg [71:0] hbmm [0:NHBM-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/fu_rec.mem"}, recm); $readmemh({dir, "/fu_exp.mem"}, expm); $readmemh({dir, "/fu_case.mem"}, casem);
        $readmemh({dir, "/fu_vmi.mem"}, vmim); $readmemh({dir, "/fu_vme.mem"}, vmem); $readmemh({dir, "/fu_hbm.mem"}, hbmm);
    end
    integer errors = 0, cyc = 0, seed = 3; always @(posedge clk) cyc <= cyc + 1;
    initial begin if (!$value$plusargs("SEED=%d", seed)) seed = 3; $display("SEED=%0d", seed); end  // runtime seed (+SEED=<n> overrides): Verilator 5.050 drops a declaration initialiser read only by $random (tools/seed_init_lint.py)
    reg rst_n = 0; reg [1214:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted, mv_v, mv_rdy, mv_done, mv_fault; wire [226:0] mv;
    wire [337:0] fq, mq; wire [273:0] fr, mr, tr; reg [337:0] tq = 0;
    wire [32*16-1:0] rq; wire [31:0] rq_cr, w2_cr, w2_done; wire [32*257-1:0] rr; wire [32*280-1:0] w2q;   // WIDE lanes
    ot_hgi_fused_record #(
`ifdef NO_PAYLOAD_RST
    .PAYLOAD_RESET(0),
`endif
.UNIT(1)
`ifdef SCRW
    , .SCR_WORDS(`SCRW)
`endif
`ifdef WIDE
    , .UWIDE(1), .ULWB(18)
`endif
`ifdef UN
    , .UN(`UN), .UM(`UM)
`endif
`ifdef HCE
    , .HCE(1), .HMUT(`HCE), .ULQ(`VLQ)
`ifdef HLL
    , .HLL(1)
`endif
`endif
    ) u (.clk(clk), .rst_n(rst_n), .cfg_scratch(`ifdef HLL 18'd240640 `else 18'd240000 `endif), .rec_v(rec_v),
        .rec_rdy(rec_rdy), .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_c(cur[895:640]),
        .rec_o(cur[1151:896]), .rec_n_a(cur[1172:1152]), .rec_n_b(cur[1193:1173]), .rec_n_o(cur[1214:1194]),
        .rec_done(done), .rec_fault(fault), .halted(halted), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done),
        .mv_fault(mv_fault), .op_v(), .op_rdy(1'b0), .op_w(), .su_idle(1'b1), .su_fault(1'b0), .vmq(fq), .vmr(fr),
        .ne_v(), .ne_rdy(1'b1), .ne_job(), .ne_done(1'b0), .ne_fault(1'b0), .q_rec(), .q_done(1'b0), .q_fault(1'b0)
`ifdef WIDE
        , .wrq(f_rq), .wrq_cr(own ? rq_cr : 32'd0), .wrr(own ? rr : '0), .wwq(f_w2q), .wwq_cr(own ? w2_cr : 32'd0),
        .wwq_done(own ? w2_done : 32'd0), .rg_req(), .rg_gnt(1'b1), .wg_req(), .wg_gnt(1'b1)
`endif
        );
`ifdef WIDE
    // b-hc LANE_LOAD: the bench preloads / reads back VM through the wide lanes (32 sectors a cycle) while the unit is
    // idle (own = 0); otherwise the unit owns them
    wire [32*16-1:0] f_rq; wire [32*280-1:0] f_w2q;
    reg own = 1; reg [32*16-1:0] t_rq = 0; reg [32*280-1:0] t_wq = 0;
    assign rq = own ? f_rq : t_rq; assign w2q = own ? f_w2q : t_wq;
    reg [278:0] lw_q [0:31][$]; reg [278:0] lr_q [0:31][$]; reg [278:0] lr_e [0:31][$];   // {sec 15, mask 8, data 256}
    integer lwcr [0:31], lrcr [0:31], lerr = 0;
    task automatic lanes_run(input integer cs);
        integer b, busy, tw, q2;
        begin
            for (b = 0; b < 32; b = b + 1) begin lwcr[b] = `VLQ; lrcr[b] = `VLQ; end
            busy = 1; tw = 0;
            while (busy && tw < 400000) begin
                @(negedge clk);
                t_rq = 0; t_wq = 0; busy = 0;
                for (b = 0; b < 32; b = b + 1) begin
                    if (w2_cr[b]) lwcr[b] = lwcr[b] + 1;
                    if (rq_cr[b]) lrcr[b] = lrcr[b] + 1;
                    if (rr[b*257 + 256]) begin : rsp
                        reg [278:0] e; e = lr_e[b].pop_front();
                        for (q2 = 0; q2 < 8; q2 = q2 + 1)
                            if (e[256 + q2] && rr[b*257 + 32*q2 +: 32] !== e[32*q2 +: 32]) begin
                                if (errors < 20) $display("ERR case %0d VM[%0d] = %h expected %h", cs, {e[278:264], 3'(q2)},
                                                          rr[b*257 + 32*q2 +: 32], e[32*q2 +: 32]);
                                errors = errors + 1;
                            end
                    end
                    if (lw_q[b].size() > 0 && lwcr[b] > 0) begin : wr
                        reg [278:0] x; x = lw_q[b].pop_front();
                        t_wq[b*280 +: 280] = {1'b1, x[278:264], x[255:0], x[263:256]}; lwcr[b] = lwcr[b] - 1;
                    end else if (lw_q[b].size() == 0 && lr_q[b].size() > 0 && lrcr[b] > 0 && lwcr[b] == `VLQ) begin : rd
                        reg [278:0] x; x = lr_q[b].pop_front();
                        t_rq[b*16 +: 16] = {1'b1, x[278:264]}; lrcr[b] = lrcr[b] - 1; lr_e[b].push_back(x);
                    end
                    if (lw_q[b].size() > 0 || lr_q[b].size() > 0 || lr_e[b].size() > 0 || lwcr[b] != `VLQ || lrcr[b] != `VLQ) busy = 1;
                end
                tw = tw + 1;
            end
            @(negedge clk); t_rq = 0; t_wq = 0;
            if (busy) begin $display("ERR bench lane traffic hung"); errors = errors + 1; end
        end
    endtask
    // words {addr 32, value 32} sorted by address -> sector entries on the lane queues (wr = 1: writes, 0: checks)
    task automatic lanes_words(input integer first, input integer n, input integer wr);
        integer j2; reg [278:0] x; reg [31:0] a2; reg have;
        begin
            have = 0; x = 0;
            for (j2 = 0; j2 < n; j2 = j2 + 1) begin
                a2 = wr ? vmim[first + j2][63:32] : vmem[first + j2][63:32];
                if (have && x[278:264] != a2[17:3]) begin
                    if (wr) lw_q[x[268:264]].push_back(x); else lr_q[x[268:264]].push_back(x);
                    have = 0;
                end
                if (!have) begin x = 0; x[278:264] = a2[17:3]; have = 1; end
                x[256 + a2[2:0]] = 1'b1;
                x[32*a2[2:0] +: 32] = wr ? vmim[first + j2][31:0] : vmem[first + j2][31:0];
            end
            if (have) begin if (wr) lw_q[x[268:264]].push_back(x); else lr_q[x[268:264]].push_back(x); end
        end
    endtask
`endif
    wire k_req_v, k_req_we, k_rsp_rdy; reg k_req_rdy = 0, k_rsp_v = 0, k_rsp_we = 0; reg [255:0] k_rsp_data = 0;
    wire [36:0] k_addr; wire [255:0] k_wd; wire [31:0] k_ws; wire [15:0] k_tag;
    wire [279:0] wl; wire wl_done;   // the VM wide write port (hgi-takeover 2026-10-10)
    ot_hgi_dma_mover u_m (.clk(clk), .rst_n(rst_n), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done),
        .mv_fault(mv_fault), .fence_v(1'b0), .fence_rdy(), .fence_done(), .k_req_v(k_req_v), .k_req_rdy(k_req_rdy),
        .k_req_we(k_req_we), .k_req_addr(k_addr), .k_req_wdata(k_wd), .k_req_wstrb(k_ws), .k_req_tag(k_tag),
        .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_we(k_rsp_we), .k_rsp_data(k_rsp_data), .k_fault(1'b0),
.r_req_v(r_req_v), .r_req_rdy(r_req_rdy), .r_req_addr(r_req_addr), .r_req_len(r_req_len), .r_req_tag(r_req_tag), .r_req_we(r_req_we), .r_req_wdata(r_req_wdata), .r_req_wstrb(r_req_wstrb),
        .r_rsp_v(r_rsp_v), .r_rsp_we(r_rsp_we), .r_rsp_rdy(r_rsp_rdy), .r_rsp_tag(r_rsp_tag), .r_rsp_last(r_rsp_last), .r_rsp_data(r_rsp_data), .vr2q(), .vr2r(8257'd0),
        .vmq(mq), .vmr(mr), .wl(wl), .wl_done(wl_done));
`ifdef WIDE
    ot_hgi_vm_unit #(.NC(3), .WP(1), .RP(32), .W2(32), .LQ(`VLQ)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, mq, fq}), .cr({tr, mr, fr}), .status(),
        .wq(wl), .wq_done(wl_done), .rq(rq), .rq_cr(rq_cr), .rr(rr), .w2q(w2q), .w2q_cr(w2_cr), .w2q_done(w2_done));
`else
    ot_hgi_vm_unit #(.NC(3), .WP(1)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, mq, fq}), .cr({tr, mr, fr}), .status(), .wq(wl), .wq_done(wl_done));
`endif
    reg [31:0] hbm [longint];
    // hgi-1010/c: the mover's four HBM read lanes (bursts, in order a lane) on tb_hgi_rlanes over this bench's memory
    wire [3:0] r_req_v, r_req_rdy, r_rsp_v, r_rsp_rdy, r_rsp_last; wire [4*37-1:0] r_req_addr, la; wire [15:0] r_req_len;
    wire [63:0] r_req_tag, r_rsp_tag; wire [1023:0] r_rsp_data, r_req_wdata; wire [3:0] r_req_we, r_rsp_we; wire [127:0] r_req_wstrb; reg [1023:0] ld; integer hgen = 0; wire [3:0] wv; wire [4*37-1:0] wa; wire [1023:0] wd; wire [127:0] ws;
    always @(posedge clk) hgen <= hgen + 1;
    tb_hgi_rlanes #(.LAT(6)) u_rl (.clk(clk), .rst_n(rst_n), .r_req_v(r_req_v), .r_req_rdy(r_req_rdy), .r_req_addr(r_req_addr),
        .r_req_len(r_req_len), .r_req_tag(r_req_tag), .r_req_we(r_req_we), .r_req_wdata(r_req_wdata), .r_req_wstrb(r_req_wstrb), .r_rsp_v(r_rsp_v), .r_rsp_we(r_rsp_we), .r_rsp_rdy(r_rsp_rdy), .r_rsp_tag(r_rsp_tag),
        .r_rsp_last(r_rsp_last), .r_rsp_data(r_rsp_data), .la(la), .ld(ld), .wv(wv), .wa(wa), .wd(wd), .ws(ws));
    always @(posedge clk) for (integer l = 0; l < 4; l = l + 1) if (wv[l]) for (integer q = 0; q < 8; q = q + 1)
        hbm[(longint'(wa[l*37 +: 37]) >> 2) + q] = wd[l*256 + 32*q +: 32];      // full sectors (the lanes refuse partial ones)
    always @(la or hgen) for (integer l = 0; l < 4; l = l + 1) for (integer q = 0; q < 8; q = q + 1) begin
        longint wa; wa = (longint'(la[l*37 +: 37]) >> 2) + q;
        ld[l*256 + 32*q +: 32] = hbm.exists(wa) ? hbm[wa] : 32'd0;
    end
    integer klat = -1, q; reg pend = 0; reg [36:0] pa;
`ifdef KLAT
    // b-hc: the pipelined kport lane (as tb_hgi_e2e's hgi_e2e_kport): a request a cycle, answered IN ORDER KLAT cycles
    // later (reads only on this bench)
    reg [255:0] kq_d [0:255]; longint kq_t [0:255]; integer kq_h = 0, kq_n = 0; longint ktn = 0;
    always @(posedge clk) begin
        ktn <= ktn + 1;
        k_rsp_v <= 0;
        if (kq_n > 0 && kq_t[kq_h % 256] <= ktn) begin k_rsp_v <= 1; k_rsp_we <= 0; k_rsp_data <= kq_d[kq_h % 256]; kq_h = kq_h + 1; kq_n = kq_n - 1; end
        if (rst_n && k_req_v && k_req_rdy) begin : acc
            reg [255:0] rd;
            for (q = 0; q < 8; q = q + 1) rd[32*q +: 32] = hbm.exists((k_addr >> 2) + q) ? hbm[(k_addr >> 2) + q] : 32'd0;
            kq_d[(kq_h + kq_n) % 256] = rd; kq_t[(kq_h + kq_n) % 256] = ktn + `KLAT - 1; kq_n = kq_n + 1;
        end
        if (!rst_n) begin kq_h = 0; kq_n = 0; end
        k_req_rdy <= rst_n && (kq_n < 200);
    end
`else
    always @(posedge clk) begin
        k_rsp_v <= 0;
        if (rst_n && k_req_v && k_req_rdy && !pend) begin pend = 1; pa = k_addr; klat = 2 + ($random(seed) & 7); end
        else if (pend && klat > 0) klat = klat - 1;
        else if (pend) begin
            for (q = 0; q < 8; q = q + 1) k_rsp_data[32*q +: 32] <= hbm.exists((pa >> 2) + q) ? hbm[(pa >> 2) + q] : 32'd0;
            k_rsp_v <= 1; k_rsp_we <= 0; pend = 0;
        end
        k_req_rdy <= !pend && ($random(seed) & 1);     // hgi-takeover: ready from the state after this edge's accept
    end
`endif
    task automatic vm_req(input we, input [31:0] word, input [31:0] data, output [31:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, word[29:3], 5'd0, {8{data}}, (32'hF << (4 * word[2:0])), 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!tr[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            qd = tr[32 * word[2:0] +: 32];
        end
    endtask
    integer k, nf, hce_cyc = 0, mv_cyc = 0;
    always @(posedge clk) begin if (rst_n && u.st == 5'd9) hce_cyc <= hce_cyc + 1; if (rst_n && u.st == 5'd3) mv_cyc <= mv_cyc + 1; end
    always @(posedge clk) begin if (rst_n && done) k = k + 1; if (rst_n && fault) nf = nf + 1; end
`ifdef HTRACE
    // H-MTP2: engine event trace (HCE HLL build): record accept / job / lane 0 phase edges / top tail / retire
    always @(posedge clk) if (rst_n) begin
        if (rec_v && rec_rdy) $display("T %0d rec_accept", cyc);
        if (u.ne_v) $display("T %0d ne_job", cyc);
        if (u.mv_v && u.mv_rdy) $display("T %0d gain_move_issued", cyc);
        if (u.in_mvd) $display("T %0d gain_move_done", cyc);
        if (u.g_hce.u_hce.g_ll.u_ll.u_ctl.g_ln[0].u_l.c_go) $display("T %0d lane0 GO", cyc);
        if (u.g_hce.u_hce.g_ll.u_ll.u_ctl.g_ln[0].u_l.c_grdy) $display("T %0d lane0 GRDY", cyc);
        if (u.g_hce.u_hce.g_ll.u_ll.u_ctl.g_ln[0].u_l.c_rstd) $display("T %0d lane0 RSTD", cyc);
        if (u.g_hce.u_hce.g_ll.u_ll.u_ctl.g_ln[0].u_l.cs_v) $display("T %0d lane0 chunk_up", cyc);
        if (u.g_hce.u_hce.g_ll.u_ll.u_ctl.g_ln[0].u_l.y_v) $display("T %0d lane0 y", cyc);
        if (u.g_hce.u_hce.g_ll.u_ll.u_ctl.g_ln[0].u_l.iss) $display("T %0d lane0 read_issue ph_b=%0d", cyc, u.g_hce.u_hce.g_ll.u_ll.u_ctl.g_ln[0].u_l.ph_b);
        if (u.g_hce.u_hce.g_ll.u_ll.u_ctl.g_ln[0].u_l.fin) $display("T %0d lane0 fin", cyc);
        if (u.g_hce.u_hce.g_ll.u_ll.u_ctl.ss_v) $display("T %0d top ss", cyc);
        if (u.g_hce.u_hce.g_ll.u_ll.u_ctl.rr_v) $display("T %0d top rsqrt", cyc);
        if (u.g_hce.u_hce.g_ll.u_ll.u_ctl.st != $past(u.g_hce.u_hce.g_ll.u_ll.u_ctl.st)) $display("T %0d top st %0d", cyc, u.g_hce.u_hce.g_ll.u_ll.u_ctl.st);
        if (done) $display("T %0d rec_done", cyc);
    end
`endif
    integer c, j, t, kind, r0, nr, vi0, nvi, ve0, nve, h0, nh, words = 0, cases = 0, t0;
    reg [31:0] qd;
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            kind = casem[c][287:256]; r0 = casem[c][255:224]; nr = casem[c][223:192]; vi0 = casem[c][191:160];
            nvi = casem[c][159:128]; ve0 = casem[c][127:96]; nve = casem[c][95:64]; h0 = casem[c][63:32]; nh = casem[c][31:0];
            if (kind != 0) continue;
            rst_n = 0; hbm.delete(); repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
`ifdef LANE_LOAD
            own = 0; lanes_words(vi0, nvi, 1); lanes_run(c); own = 1;
`else
            for (j = 0; j < nvi; j = j + 1) vm_req(1'b1, vmim[vi0 + j][63:32], vmim[vi0 + j][31:0], qd);
`endif
            for (j = 0; j < nh; j = j + 1) hbm[hbmm[h0 + j][71:32]] = hbmm[h0 + j][31:0];
            k = 0; nf = 0; t0 = cyc; hce_cyc = 0; mv_cyc = 0;
            for (j = 0; j < nr; j = j + 1) begin
                @(negedge clk); cur = recm[r0 + j]; rec_v = 1;
                t = 0; while (!rec_rdy && t < 4000000) begin @(negedge clk); t = t + 1; end
                @(posedge clk); #0.1 rec_v = 0;
            end
            t = 0; while (k < nr && nf == 0 && t < 4000000) begin @(posedge clk); t = t + 1; end
            if (k != nr || nf != 0) begin $display("ERR case %0d: retired %0d of %0d, faults %0d", c, k, nr, nf); errors = errors + 1; end
            $display("case %0d: %0d records in %0d cycles (HC engine %0d, mover %0d)", c, k, cyc - t0, hce_cyc, mv_cyc); $fflush;
`ifdef DUMP_SCR
            for (j = 0; j < 4; j = j + 1) begin vm_req(1'b0, 240000 + `DUMP_SCR + j, 0, qd); $display("SCR %0d = %h", j, qd); end
`endif
`ifdef LANE_LOAD
            own = 0; lanes_words(ve0, nve, 0); lanes_run(c); own = 1;
            for (j = 0; j < 0; j = j + 1) begin
`else
            for (j = 0; j < nve; j = j + 1) begin
`endif
                vm_req(1'b0, vmem[ve0 + j][63:32], 0, qd);
                if (qd !== vmem[ve0 + j][31:0]) begin
                    if (errors < 20) $display("ERR case %0d VM[%0d] = %h expected %h", c, vmem[ve0 + j][63:32], qd, vmem[ve0 + j][31:0]);
                    errors = errors + 1; end
            end
            words = words + nve; cases = cases + 1;
        end
        $display("summary: %0d FUSED data cases through the D1 unit, %0d VM words exact", cases, words);
        if (errors == 0 && cases > 0) $display("HGI_FUSED_UNIT PASS"); else $display("HGI_FUSED_UNIT FAIL errors=%0d", errors);
        $finish;
    end
endmodule
