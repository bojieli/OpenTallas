`timescale 1ns/1ps
// el1013-hbm-hc: tb_hgi_hc_eng for the B2 engine ot_hgi_hc_eng_b2: FOUR local VM slices (ot_hgi_vm_unit RP 8 / W2 8 each;
// bench lane 8 q + b = bank b of slice q), vectors hc_eng_bench.py --b2 (the same golden, operands partitioned by quarter).
// -DRLQV / -DCDV: centre <-> quarter relay flops and chunk-slot credits.  Original header:
// hgi-1010/b-hc (2026-10-10): standalone bench of ot_hgi_hc_eng on the REAL wide VM lanes (ot_hgi_vm_unit RP 32 / W2 32,
// LQ credits).  Vectors tools/hgi_adapters/hc_eng_bench.py (DS d 5,120 HC_POST / HC_PRE_NORM, hdc_golden_v41 chunk8):
// the bench preloads VM through the write lanes, runs one job a case (cycles = job accept -> done), reads every output
// sector (and the guard sectors around it) back through the read lanes.  Prints HGI_HC_ENG PASS / FAIL.
// +GDLY=n: g_rdy rises n cycles after the job (the gain mover's landing; default 0 = gain already in VM).
module tb_hgi_hc_eng_b2;
    `include "hc_sizes.svh"
`ifndef LQV
`ifdef HC_NATIVE
 `define LQV 10
`else
 `define LQV 32
`endif
`endif
`ifndef HMUT
 `define HMUT 0
`endif
`ifndef RLQV
 `define RLQV 6
`endif
`ifndef CDV
 `define CDV 16
`endif
    localparam integer LQ = `LQV;
    reg clk = 0; always #1 clk = ~clk;
    reg [279:0] casem [0:NCASE-1]; reg [275:0] initm [0:NINIT-1]; reg [275:0] expm [0:NEXP-1];
    reg [8*256-1:0] dir;
    integer gdly = 0;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("GDLY=%d", gdly)) gdly = 0;
        $readmemh({dir, "/hc_case.mem"}, casem); $readmemh({dir, "/hc_init.mem"}, initm); $readmemh({dir, "/hc_exp.mem"}, expm);
    end
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0;
    // engine
    reg job_v = 0; reg [148:0] jw = 0; reg g_rdy = 0; wire job_rdy, e_done, e_fault, e_idle;
    wire [32*16-1:0] e_rq; wire [32*280-1:0] e_wq; wire e_rg, e_wg;
    // VM lanes
    wire [31:0] rq_cr, w2_cr, w2_done; wire [32*257-1:0] rr;
    reg own = 0;                                     // 1: the engine drives the lanes; 0: the bench
    reg [32*16-1:0] t_rq = 0; reg [32*280-1:0] t_wq = 0;
    wire [32*16-1:0] rq = own ? e_rq : t_rq; wire [32*280-1:0] w2q = own ? e_wq : t_wq;
`ifdef HC_CLOCKED
    localparam integer BCLOCKED=1;
`else
    localparam integer BCLOCKED=0;
`endif
`ifdef HC_STORELEAF
    localparam integer BSTORE=1;
`else
    localparam integer BSTORE=0;
`endif
`ifdef HC_COEFFLEAF
    localparam integer BCOEFF=1;
`else
    localparam integer BCOEFF=0;
`endif
    ot_hgi_hc_eng_b2 #(.COEFFLEAF(BCOEFF),.STORELEAF(BSTORE),.CLOCKED(BCLOCKED),.D(HD), .LQ(LQ), .RLQ(`RLQV), .CD(`CDV), .MUT(`HMUT)) u_e (.clk(clk), .rst_n(rst_n), .job_v(job_v),
        .clk_quarter_link({4{clk}}),.clk_ctl(clk),.clk_coll(clk),.clk_qst({4{clk}}),.clk_cat({4{clk}}),.clk_lane({32{clk}}),.clk_coeff({32{clk}}),.clk_store({20{clk}}),.clk_scan({32{clk}}),.clk_block_add({31{clk}}),.clk_heap_add({31{clk}}),.clk_sl({256{clk}}), .clk_chunk({224{clk}}), .job_rdy(job_rdy), .job(jw),
        .g_rdy(g_rdy), .done(e_done), .fault(e_fault), .idle(e_idle), .wrq(e_rq), .wrq_cr(own ? rq_cr : 32'd0),
        .wrr(own ? rr : '0), .wwq(e_wq), .wwq_cr(own ? w2_cr : 32'd0), .wwq_done(own ? w2_done : 32'd0),
        .rg_req(e_rg), .rg_gnt(1'b1), .wg_req(e_wg), .wg_gnt(1'b1));
`ifdef HC_NATIVE
    // Full native four-slice endpoints, production RG2/WG2 bank parameters,
    // independent slice straps and closed-loop ring connections. Group1 and
    // packet/DMA/COLL sources are idle in this isolated HC transaction gate.
    wire [2223:0] cw_in[0:3], cw_out[0:3], ccw_in[0:3], ccw_out[0:3];
    wire [1:0] cw_ic[0:3], cw_oc[0:3], ccw_ic[0:3], ccw_oc[0:3];
    genvar nq, nb, nr;
    generate for(nq=0;nq<4;nq=nq+1) begin:g_native_vm
        wire [271:0] native_rq; wire [4495:0] native_wq;
        wire [15:0] native_rc,native_wc,native_wd;wire[4111:0]native_rr;
        wire [143:0] bank_status;wire[2:0]hub_status;wire[1:0]mirror_busy;
        for(nb=0;nb<8;nb=nb+1)begin:g_lane
            wire[15:0]lr=rq[(nq*8+nb)*16+:16];wire[279:0]lw=w2q[(nq*8+nb)*280+:280];
            wire[16:0]rp[0:3];wire[280:0]wp[0:3];wire rc[0:3],wc[0:3];
            wire[256:0]rs[0:3];wire wd[0:3];
            assign rp[0]={lr[15],1'b0,2'(nq),lr[12:0]};
            assign wp[0]={lw[279],1'b0,2'(nq),lw[276:264],lw[263:0]};
            assign native_rq[nb*17+:17]=rp[3];assign rc[3]=native_rc[nb];
            assign native_wq[nb*281+:281]=wp[3];assign wc[3]=native_wc[nb];
            assign rs[0]=native_rr[nb*257+:257];assign wd[0]=native_wd[nb];
            assign rq_cr[nq*8+nb]=rc[0];assign w2_cr[nq*8+nb]=wc[0];
            assign rr[(nq*8+nb)*257+:257]=rs[3];assign w2_done[nq*8+nb]=wd[3];
            for(nr=0;nr<3;nr=nr+1)begin:g_relay
                ot_vms_relay #(.W(17),.C(1)) u_read(.clk(clk),.rst_n(rst_n),.f_in(rp[nr]),.f_out(rp[nr+1]),.cr_in(rc[nr+1]),.cr_out(rc[nr]));
                ot_vms_relay #(.W(281),.C(1)) u_write(.clk(clk),.rst_n(rst_n),.f_in(wp[nr]),.f_out(wp[nr+1]),.cr_in(wc[nr+1]),.cr_out(wc[nr]));
                ot_hdc_delay #(.W(257),.D(1),.RESET(1)) u_rsp(.clk(clk),.rst_n(rst_n),.d(rs[nr]),.q(rs[nr+1]));
                ot_hdc_delay #(.W(1),.D(1),.RESET(1)) u_done(.clk(clk),.rst_n(rst_n),.d(wd[nr]),.q(wd[nr+1]));
            end
            always @(posedge clk)if(rst_n)begin
                if(lr[15]&&(lr[14:13]!=0||lr[2:0]!=nb))$fatal(1,"HC native local read address invalid");
                if(lw[279]&&(lw[278:277]!=0||lw[266:264]!=nb))$fatal(1,"HC native local write address invalid");
            end
        end
        assign native_rq[271:136]='0;assign native_wq[4495:2248]='0;
        ot_vms_slice #(.NC(4),.RG(2),.WG(2),.RRS(8'h33),.WRS(8'h33)) u_vm(
            .clk(clk),.rst_n(rst_n),.sid(2'(nq)),.cq(1352'd0),.cr(),
            .rq(native_rq),.rq_cr(native_rc),.rr(native_rr),.wq(native_wq),.wq_cr(native_wc),.wq_done(native_wd),
            .dq(2248'd0),.dq_done(),.vcb(2130'd0),.vcb_cr(),.kq_done(),
            .cw_in(cw_in[nq]),.cw_in_cr(cw_ic[nq]),.cw_out(cw_out[nq]),.cw_out_cr(cw_oc[nq]),
            .ccw_in(ccw_in[nq]),.ccw_in_cr(ccw_ic[nq]),.ccw_out(ccw_out[nq]),.ccw_out_cr(ccw_oc[nq]),
            .bank_status(bank_status),.hub_status(hub_status),.mirror_busy(mirror_busy));
        ot_vms_relay #(.W(2224),.C(2)) u_cw(.clk(clk),.rst_n(rst_n),.f_in(cw_out[nq]),.f_out(cw_in[(nq+1)%4]),.cr_in(cw_ic[(nq+1)%4]),.cr_out(cw_oc[nq]));
        ot_vms_relay #(.W(2224),.C(2)) u_ccw(.clk(clk),.rst_n(rst_n),.f_in(ccw_out[nq]),.f_out(ccw_in[(nq+3)%4]),.cr_in(ccw_ic[(nq+3)%4]),.cr_out(ccw_oc[nq]));
        always @(posedge clk)if(rst_n && (hub_status != 0 || mirror_busy != 0))$fatal(1,"HC native slice unexpected fault or mirror traffic");
        for(nb=0;nb<8;nb=nb+1)begin:g_status
            always @(posedge clk)if(rst_n && bank_status[nb*18+17])$fatal(1,"HC native bank fault");
        end
    end endgenerate
    initial if(LQ!=10)$fatal(1,"HC native relay3 uses actual 10-credit queues");
`else
    // The golden VM core implements complete 32-bank lane groups. RP=8/W2=8 produces
    // zero groups (RP/32), so the original backing model never accepted a request.
    // Embed each local eight-bank slice in banks 0..7 of that unchanged core:
    // local sector = {row[9:0], bank[2:0]}, native sector = {row, 2'b00, bank}.
    // The other 24 banks stay idle. Reject addresses beyond the real eight-bank
    // capacity rather than truncating them. This is a test backing-store adapter;
    // native VM8 integration and timing remain separate qualification gates.
    genvar gq, bl;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_vm
        wire [32*16-1:0] nrq;
        wire [32*280-1:0] nwq;
        wire [31:0] nrcr, nwcr, nwdn;
        wire [32*257-1:0] nrr;
        for (bl = 0; bl < 32; bl = bl + 1) begin : g_bank
            if (bl < 8) begin : g_live
                wire [15:0] r = rq[(gq*8+bl)*16 +: 16];
                wire [279:0] w = w2q[(gq*8+bl)*280 +: 280];
                assign nrq[bl*16 +: 16] = {r[15], r[12:3], 2'b00, r[2:0]};
                assign nwq[bl*280 +: 280] = {w[279], w[276:267], 2'b00, w[266:264], w[263:0]};
                assign rq_cr[gq*8+bl] = nrcr[bl];
                assign w2_cr[gq*8+bl] = nwcr[bl];
                assign w2_done[gq*8+bl] = nwdn[bl];
                assign rr[(gq*8+bl)*257 +: 257] = nrr[bl*257 +: 257];
                always @(posedge clk) if (rst_n) begin
                    if (r[15] && (r[14:13] != 0 || r[2:0] != bl))
                        $fatal(1, "B2 VM read outside local capacity or wrong lane");
                    if (w[279] && (w[278:277] != 0 || w[266:264] != bl))
                        $fatal(1, "B2 VM write outside local capacity or wrong lane");
                end
            end else begin : g_unused
                assign nrq[bl*16 +: 16] = 16'd0;
                assign nwq[bl*280 +: 280] = 280'd0;
            end
        end
        ot_hgi_vm_unit #(.NC(1), .WP(1), .RP(32), .W2(32), .LQ(LQ)) u_vm (.clk(clk), .rst_n(rst_n), .cq(338'd0), .cr(),
            .status(), .wq(280'd0), .wq_done(), .rq(nrq), .rq_cr(nrcr), .rr(nrr),
            .w2q(nwq), .w2q_cr(nwcr), .w2q_done(nwdn));
    end endgenerate

`endif

    // ---- bench lane traffic: per-lane sector queues, LQ credits
    reg [270:0] wq_l [0:31][$]; reg [270:0] rq_l [0:31][$];     // writes {sec, data}; reads {sec, expected}
    integer wcr [0:31], rcr [0:31], wpd [0:31], wout = 0, errors = 0, checked = 0;
    reg [270:0] rexp [0:31][$];
    task automatic lanes_run();                      // drain every queue (writes first, then reads), wait for the landings
        integer b, busy, tw;
        begin
            for (b = 0; b < 32; b = b + 1) begin wcr[b] = LQ; rcr[b] = LQ; wpd[b] = 0; end
            busy = 1; tw = 0;
            while (busy && tw < 200000) begin
                @(negedge clk);
                t_rq = 0; t_wq = 0; busy = 0;
                for (b = 0; b < 32; b = b + 1) begin
                    if (w2_cr[b]) wcr[b] = wcr[b] + 1;
                    if (rq_cr[b]) rcr[b] = rcr[b] + 1;
                    if (w2_done[b]) wpd[b] = wpd[b] - 1;     // a preload write landed (dones trail the credits)
                    if (rr[b*257 + 256]) begin : rsp
                        reg [270:0] e; e = rexp[b].pop_front();
                        if (rr[b*257 +: 256] !== e[255:0]) begin
                            if (errors < 12) $display("ERR sector %0d lane %0d: got %h expected %h", e[270:256], b,
                                                      rr[b*257 +: 256], e[255:0]);
                            errors = errors + 1;
                        end
                        checked = checked + 1;
                    end
                    if (wq_l[b].size() > 0 && wcr[b] > 0) begin : wr
                        reg [270:0] x; x = wq_l[b].pop_front();
                        t_wq[b*280 +: 280] = {1'b1, x[270:256], x[255:0], 8'hFF}; wcr[b] = wcr[b] - 1; wpd[b] = wpd[b] + 1;
                    end else if (wq_l[b].size() == 0 && rq_l[b].size() > 0 && rcr[b] > 0 && wcr[b] == LQ) begin : rd
                        reg [270:0] x; x = rq_l[b].pop_front();
                        t_rq[b*16 +: 16] = {1'b1, x[270:256]}; rcr[b] = rcr[b] - 1; rexp[b].push_back(x);
                    end
                    if (wq_l[b].size() > 0 || rq_l[b].size() > 0 || rexp[b].size() > 0 || wcr[b] != LQ || rcr[b] != LQ || wpd[b] != 0) busy = 1;
                end
                tw = tw + 1;
            end
            @(negedge clk); t_rq = 0; t_wq = 0;
            if (busy) begin $display("ERR bench lane traffic hung"); errors = errors + 1; end
        end
    endtask

    integer c, j, t, i0, ni, e0, ne, t0, tot = 0;
    // the engine retires only after its last write is in the macro: count the VM write dones while it owns the lanes
    integer wdn = 0;
    always @(posedge clk) if (own) for (integer b = 0; b < 32; b = b + 1) if (w2_done[b]) wdn = wdn + 1;
    // Gain-ready is a real producer/consumer permission. The memory fixture is
    // preloaded, so output equality alone would miss a premature gain read.
    integer early_gain_reads = 0;
    always @(posedge clk) if (own && jw[148:147] == 0 && !g_rdy) begin
        for (integer bl = 0; bl < 32; bl = bl + 1) begin
            if (e_rq[bl*16+15] && e_rq[bl*16+:15] >= (jw[35:18] >> 3) &&
                e_rq[bl*16+:15] < ((jw[35:18] >> 3) + HD/32)) begin
                early_gain_reads = early_gain_reads + 1;
                errors = errors + 1;
                if (early_gain_reads < 3) $display("ERR gain read before producer ready lane %0d", bl);
            end
        end
    end
    integer cyc_case [0:15];
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            i0 = casem[c][127:96]; ni = casem[c][95:64]; e0 = casem[c][63:32]; ne = casem[c][31:0];
            own = 0; rst_n = 0; repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
            for (j = 0; j < ni; j = j + 1) wq_l[8 * initm[i0 + j][273:272] + initm[i0 + j][258:256]].push_back({initm[i0 + j][270:256], initm[i0 + j][255:0]});
            lanes_run();
            @(negedge clk); own = 1; wdn = 0; jw = casem[c][276:128]; job_v = 1; t0 = cyc;
            t = 0; while (!job_rdy && t < 1000) begin @(negedge clk); t = t + 1; end
            @(negedge clk); job_v = 0;
            fork
                begin repeat (gdly) @(posedge clk); #0.1 g_rdy = 1; end
            join_none
`ifndef WDOG
 `define WDOG 200000
`endif
            t = 0; while (!e_done && !e_fault && t < `WDOG) begin @(posedge clk); t = t + 1; end
            if (!e_done && !e_fault)
                $display("HANG st %0d ndone %0d nexp %0d fin %0d scl %0d nsc %0d", u_e.u_ctl.st, u_e.u_ctl.ndone, u_e.u_ctl.nexp,
                         u_e.u_ctl.fin_all, u_e.u_ctl.scl, u_e.u_ctl.nsc);
            cyc_case[c] = cyc - t0;
            begin : landed
                integer want; want = (jw[148:147] == 2'd1) ? HD / 2 : HD / 8;     // output sectors (HC_POST 4 x D / 8)
                if (e_done && wdn != want) begin
                    $display("ERR case %0d: retired with %0d of %0d output writes landed", c, wdn, want); errors = errors + 1;
                end
            end
            if (!e_done) begin $display("ERR case %0d: %s after %0d cycles", c, e_fault ? "FAULT" : "HANG", cyc - t0); errors = errors + 1; end
            $display("case %0d: %s d %0d %s%0d cycles", c, jw[148:147] == 2'd1 ? "HC_POST" : "HC_PRE_NORM", HD,
                     (jw[148:147] == 2'd0 && jw[36]) ? "packed gain " : "", cyc - t0); $fflush;
            repeat (2) @(negedge clk); own = 0; g_rdy = 0;
            for (j = 0; j < ne; j = j + 1) rq_l[8 * expm[e0 + j][273:272] + expm[e0 + j][258:256]].push_back({expm[e0 + j][270:256], expm[e0 + j][255:0]});
            lanes_run();
            tot = tot + 1;
        end
        $display("protocol: early_gain_reads %0d", early_gain_reads);
        $display("summary: %0d HC B2 engine cases, %0d sectors checked, %0d sector errors, stale chunks %0d", tot, checked, errors, u_e.u_ctl.c_stale);
        if (errors == 0 && tot == NCASE) $display("HGI_HC_ENG_B2 PASS"); else $display("HGI_HC_ENG_B2 FAIL errors=%0d", errors);
        $finish;
    end
endmodule
