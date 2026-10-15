`timescale 1ns/1ps
// tb_dsfd_coll_xc (s81-die-rtl-bind 2026-10-14): exact bench of the collective die-client adapter dsfd_coll_xc.
// A behavioural CORE drives c_tvm beats in the contract's t_vm format (reduce beats of 1..4 words with message lasts on
// 16-word boundaries, gather beats, pass-through flits on every channel, status beats) and returns pass-through queue
// credits for the flits it receives on c_fvm; it sees c_ts with a DTS-cycle delay (in-flight beats after the adapter
// closes ts).  A behavioural VM sends f_vm words (engine records, pass-through on its own channels, the config word)
// and checks t_vm.  The HC takes y beats with a random ready; the WFC kit is the real grant-protocol pair
// (ot_dsrom_mtp_lrx receiving t_wfc, ot_dsrom_mtp_ltx sending f_wfc); the host model drives f_host.
// CHECKS (scoreboards, in order): y beats = the reduce words in order, 16 a beat; kit link in = the hop-in flits;
// core injected flits on hop-out = the kit's flits, on the host channel = the host's credits (sum), completions (in
// order) and final status; c_fvm VM words = f_vm words (in order, unchanged); t_vm = the core beats with diverted
// pass-through beats turned into status beats (credits per queue summed equal); no adapter fault; every queue drained.
// MUT 1 (y word order), 2 (hop-in drop), 3 (host credits lost) must FAIL.
module tb_dsfd_coll_xc;
    parameter integer MUT = 0, NB = 6000, DTS = 6, SEED = 1, HCSLOW = 0;
    reg ck = 0, rst = 0; always #1 ck = ~ck;
    integer cyc = 0; always @(posedge ck) cyc <= cyc + 1;
    reg [63:0] rs = 64'h9E3779B97F4A7C15 ^ SEED;
    function [31:0] rnd(input integer d); begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 7); rs = rs ^ (rs << 17); rnd = rs[31:0]; end endfunction
    function [511:0] r512(input integer d); integer j; begin for (j = 0; j < 16; j = j + 1) r512[32 * j +: 32] = rnd(0); end endfunction
    // ---------------- DUT
    reg [591:0] f_vm = 0; reg [2:0] ts = 3'b011; wire [2099:0] t_vm;
    wire [591:0] c_fvm; wire [2:0] c_ts; reg [2099:0] c_tvm = 0;
    wire [8191:0] t_hc_y; wire t_hc_yv; reg f_hc_yr = 0;
    wire [513:0] t_wfc; wire f_wfcg; wire [513:0] f_wfc; wire t_wfcg;
    wire [515:0] t_host; reg [80:0] f_host = 0;
    dsfd_coll_xc #(.MUT(MUT)) dut (.ck(ck), .rst(rst), .f_vm(f_vm), .ts(ts), .t_vm(t_vm), .c_fvm(c_fvm), .c_ts(c_ts),
        .c_tvm(c_tvm), .t_hc_y(t_hc_y), .t_hc_yv(t_hc_yv), .f_hc_yr(f_hc_yr), .t_wfc(t_wfc), .f_wfcg(f_wfcg),
        .f_wfc(f_wfc), .t_wfcg(t_wfcg), .t_host(t_host), .f_host(f_host));
    localparam [2:0] HIN = 3'd1, HOUT = 3'd2, HOST = 3'd4;     // channel assignment (config word)
    // ---------------- WFC kit: real grant-protocol ends
    wire kv; reg kr = 0; wire [512:0] kd;
    ot_dsrom_mtp_lrx #(.W(513), .D(4)) u_kin (.clk(ck), .rst_n(rst), .l_valid(t_wfc[0]), .l_ready(f_wfcg),
        .l_data(t_wfc[513:1]), .c_valid(kv), .c_ready(kr), .c_data(kd));
    reg ksv = 0; wire ksr; reg [512:0] ksd = 0;
    wire [512:0] kld; wire klv;
    ot_dsrom_mtp_ltx #(.W(513)) u_kout (.clk(ck), .rst_n(rst), .c_valid(ksv), .c_ready(ksr), .c_data(ksd),
        .l_valid(klv), .l_ready(t_wfcg), .l_data(kld));
    assign f_wfc = {kld, klv};
    // ---------------- scoreboards
    reg [511:0] yexp [0:65535]; integer ywr = 0, yrd = 0;
    reg [512:0] kin_exp [0:8191]; integer kiw = 0, kir = 0;
    reg [512:0] kout_exp [0:8191]; integer kow = 0, kor = 0;
    reg [514:0] hin_exp [0:8191]; integer hiw = 0, hir = 0;
    reg [63:0] hc_exp [0:8191]; integer hcw = 0, hcr = 0;
    reg [591:0] vm_exp [0:65535]; integer vw = 0, vr = 0;
    reg [2099:0] tv_exp [0:65535]; integer tw = 0, tr = 0;
    integer errors = 0, crn_sent = 0, crn_got = 0, ybeats = 0, hops = 0, outs = 0, hosts = 0;
    reg [10:0] st_last = 0, st_got = 0;
    // ---------------- reset + config
    initial begin
        #10 rst = 1;
    end
    // ---------------- behavioural VM: config, then records / pass-through on channels 0 and 3 (not owned)
    integer vm_cfg = 0;
    always @(posedge ck) begin
        f_vm <= 0;
        if (rst && cyc > 12) begin
            if (vm_cfg == 0) begin
                f_vm <= {537'd0, HOST, 1'b1, HOUT, HIN, 1'b1, 1'b1, 3'b101, 32'd0, 1'b0, 1'b0, 3'd0, 2'd3, 1'b1};
                vm_exp[vw] = {537'd0, HOST, 1'b1, HOUT, HIN, 1'b1, 1'b1, 3'b101, 32'd0, 1'b0, 1'b0, 3'd0, 2'd3, 1'b1};
                vw = vw + 1; vm_cfg = 1;
            end else if ((rnd(0) % 4) == 0 && vw < 60000) begin
                reg [591:0] w_;
                w_ = {rnd(0), rnd(0), rnd(0), rnd(0), rnd(0), rnd(0), rnd(0), rnd(0), rnd(0), rnd(0), rnd(0), rnd(0),
                      rnd(0), rnd(0), rnd(0), rnd(0), rnd(0), rnd(0), 16'd0};
                w_[0] = 1'b1; w_[2:1] = (rnd(0) % 2) ? 2'd1 : 2'd2; w_[5:3] = (rnd(0) % 2) ? 3'd0 : 3'd3;
                f_vm <= w_; vm_exp[vw] = w_; vw = vw + 1;
            end
        end
    end
    // ---------------- behavioural core
    reg [DTS:0] tsd = 0;
    always @(posedge ck) tsd <= {tsd[DTS-1:0], c_ts[0]};
    integer pend_hop = 0, pend_hst = 0, nbeat = 0, ywpos = 0, cfg_seen = 0;
    reg [4:0] q2 [0:5];
    always @(posedge ck) begin
        c_tvm <= 0;
        // the core's view of c_fvm: VM words in order, injected flits on HOUT / HOST (credits returned later)
        if (c_fvm[0]) begin
            if (c_fvm[2:1] == 2'd2 && c_fvm[5:3] == HOUT) begin
                if (kor >= kow || c_fvm[40 +: 512] !== kout_exp[kor][511:0] || c_fvm[6] !== kout_exp[kor][512]) begin
                    errors = errors + 1; if (errors < 10) $display("ERR hop-out flit %0d", kor); end
                kor = kor + 1; pend_hop = pend_hop + 1; outs = outs + 1;
            end else if (c_fvm[2:1] == 2'd2 && c_fvm[5:3] == HOST) begin
                crn_got = crn_got + c_fvm[40 + 65 +: 5];
                st_got = c_fvm[40 + 70 +: 11];
                if (c_fvm[40 + 64]) begin
                    if (hcr >= hcw || c_fvm[40 +: 64] !== hc_exp[hcr]) begin errors = errors + 1; if (errors < 10) $display("ERR host completion %0d", hcr); end
                    hcr = hcr + 1;
                end
                pend_hst = pend_hst + 1;
            end else begin
                if (vr >= vw || c_fvm !== vm_exp[vr]) begin errors = errors + 1; if (errors < 10) $display("ERR VM word %0d to core", vr); end
                vr = vr + 1;
            end
        end
        if (rst && cyc > 20 && nbeat >= NB && tsd[DTS] && (pend_hop != 0 || pend_hst != 0)) begin : g_cr
            // after the traffic: status beats return the remaining pass-through credits (as the core's st_need)
            reg [2099:0] b;
            b = 0; b[0] = 1'b1; b[2:1] = 2'd3;
            b[17 + 4 * (1 + HOUT) +: 4] = (pend_hop > 15) ? 15 : pend_hop; pend_hop = pend_hop - b[17 + 4 * (1 + HOUT) +: 4];
            b[17 + 4 * (1 + HOST) +: 4] = (pend_hst > 15) ? 15 : pend_hst; pend_hst = pend_hst - b[17 + 4 * (1 + HOST) +: 4];
            c_tvm <= b; tv_exp[tw] = b; tw = tw + 1;
        end
        if (rst && cyc > 20 && nbeat < NB && tsd[DTS] && (rnd(0) % 3) != 0) begin : g_beat
            reg [2099:0] b; integer t_, nw, k;
            b = 0; b[0] = 1'b1;
            // credits: return pending pass-through credits in random chunks (q2 = hop-out queue, q5 = host queue)
            k = (pend_hop > 3) ? (rnd(0) % 4) : ((rnd(0) % 2) ? pend_hop : 0); if (k > pend_hop) k = pend_hop;
            b[17 + 4 * (1 + HOUT) +: 4] = k; pend_hop = pend_hop - k;
            k = (pend_hst > 3) ? (rnd(0) % 4) : ((rnd(0) % 2) ? pend_hst : 0); if (k > pend_hst) k = pend_hst;
            b[17 + 4 * (1 + HOST) +: 4] = k; pend_hst = pend_hst - k;
            b[17 +: 4] = rnd(0) % 4;                                        // engine queue credits (VM's)
            t_ = rnd(0) % 10;
            if (t_ < 4) begin                                              // reduce beat
                b[2:1] = 2'd1; nw = 1 + rnd(0) % 4;
                for (k = 0; k < 4; k = k + 1) if (k < nw) begin
                    b[6 + k] = 1'b1; b[52 + 512 * k +: 512] = r512(0);
                    yexp[ywr] = b[52 + 512 * k +: 512]; ywr = ywr + 1;
                    ywpos = ywpos + 1; if (ywpos % 16 == 0 && (rnd(0) % 2)) begin b[10 + k] = 1'b1; ywpos = 0; end
                end
            end else if (t_ == 4) begin                                    // gather beat
                b[2:1] = 2'd1; b[15] = 1'b1; b[9:6] = 4'hF; b[13] = rnd(0) % 2; b[52 +: 32] = rnd(0);
            end else if (t_ < 9) begin                                     // pass-through flit
                b[2:1] = 2'd2; b[5:3] = (t_ == 5) ? 3'd0 : (t_ == 6) ? HIN : (t_ == 7) ? HOST : 3'd3;
                b[14] = rnd(0) % 2; b[52 +: 512] = r512(0); b[52 + 512 +: 3] = rnd(0);
                if (b[5:3] == HIN) begin kin_exp[kiw] = {b[14], b[52 +: 512]}; kiw = kiw + 1; hops = hops + 1; end
                if (b[5:3] == HOST) begin hin_exp[hiw] = b[52 +: 515]; hiw = hiw + 1; hosts = hosts + 1; end
            end else b[2:1] = 2'd3;                                        // status
            c_tvm <= b;
            tv_exp[tw] = (b[2:1] == 2'd2 && (b[5:3] == HIN || b[5:3] == HOST)) ?
                         {2048'd0, b[51:42], b[41], b[40:17], 14'd0, 2'd3, 1'b1} : b;
            tw = tw + 1; nbeat = nbeat + 1;
        end
    end
    // y message ends must sit on beat boundaries: re-mark lasts at 16-word boundaries only (above: ywpos multiple of 16)
    // ---------------- HC
    always @(posedge ck) begin : g_hc
        integer k;
        f_hc_yr <= HCSLOW ? ((rnd(0) % 12) == 0) : ((rnd(0) % 4) != 0);   // HCSLOW: y back-pressure
        if (t_hc_yv && f_hc_yr) begin
            for (k = 0; k < 16; k = k + 1) begin
                if (yrd >= ywr || t_hc_y[512 * k +: 512] !== yexp[yrd]) begin errors = errors + 1; if (errors < 10) $display("ERR y word %0d", yrd); end
                yrd = yrd + 1;
            end
            ybeats = ybeats + 1;
        end
    end
    // ---------------- kit: receive (random ready), send random flits
    always @(posedge ck) begin
        kr <= (rnd(0) % 3) != 0;
        if (kv && kr) begin
            if (kir >= kiw || kd !== kin_exp[kir]) begin errors = errors + 1; if (errors < 10) $display("ERR kit in flit %0d", kir); end
            kir = kir + 1;
        end
        if (ksv && ksr) begin ksv <= 1'b0; end
        if ((!ksv || ksr) && rst && cyc > 30 && kow < 3000 && (rnd(0) % 3) == 0) begin
            ksv <= 1'b1; ksd <= {rnd(0) % 2 == 0, {16{rnd(0)}}};
        end
    end
    always @(posedge ck) if (ksv && ksr) begin kout_exp[kow] = ksd; kow = kow + 1; end
    // ---------------- host model
    always @(posedge ck) begin
        f_host <= 0;
        if (rst && cyc > 30 && cyc < 20000) begin
            // rates of a credit-limited ingest: a credit pulse / a completion every ~20 / ~40 cycles
            f_host[69:65] <= (rnd(0) % 20 == 0) ? rnd(0) % 32 : 0;
            if ((rnd(0) % 97) == 0) f_host[80:70] <= rnd(0);
            else f_host[80:70] <= st_last;
            if ((rnd(0) % 40) == 0) f_host[64] <= 1'b1;
            f_host[63:0] <= {rnd(0), rnd(0)};
        end else f_host[80:70] <= st_last;
    end
    reg [80:0] fh1 = 0;
    always @(posedge ck) begin
        fh1 <= f_host;
        crn_sent = crn_sent + f_host[69:65];
        st_last = f_host[80:70];
        if (f_host[64]) begin hc_exp[hcw] = f_host[63:0]; hcw = hcw + 1; end
    end
    // ---------------- VM: t_vm and t_host
    always @(posedge ck) begin
        if (t_vm[0]) begin
            if (tr >= tw || t_vm !== tv_exp[tr]) begin errors = errors + 1; if (errors < 10) $display("ERR t_vm beat %0d", tr); end
            tr = tr + 1;
        end
        if (t_host[0]) begin
            if (hir >= hiw || t_host[515:1] !== hin_exp[hir]) begin errors = errors + 1; if (errors < 10) $display("ERR host word %0d", hir); end
            hir = hir + 1;
        end
    end
    initial begin
        #(2 * (NB * 4 + 40000));
        if (yrd != (ywr / 16) * 16) begin errors = errors + 1; $display("ERR y words %0d of %0d", yrd, ywr); end
        if (kir != kiw) begin errors = errors + 1; $display("ERR kit in %0d of %0d", kir, kiw); end
        if (kor != kow) begin errors = errors + 1; $display("ERR hop out %0d of %0d", kor, kow); end
        if (hir != hiw) begin errors = errors + 1; $display("ERR host in %0d of %0d", hir, hiw); end
        if (hcr != hcw) begin errors = errors + 1; $display("ERR host completions %0d of %0d", hcr, hcw); end
        if (crn_got != crn_sent) begin errors = errors + 1; $display("ERR host credits %0d of %0d", crn_got, crn_sent); end
        if (st_got != st_last) begin errors = errors + 1; $display("ERR host status %h vs %h", st_got, st_last); end
        if (vr != vw) begin errors = errors + 1; $display("ERR VM words %0d of %0d", vr, vw); end
        if (tr != tw) begin errors = errors + 1; $display("ERR t_vm beats %0d of %0d", tr, tw); end
        if (dut.f_y || dut.f_kin || dut.f_own || dut.f_cmp) begin errors = errors + 1; $display("ERR adapter fault %b%b%b%b", dut.f_y, dut.f_kin, dut.f_own, dut.f_cmp); end
        $display("TB_DSFD_COLL_XC MUT=%0d beats=%0d ybeats=%0d hop_in=%0d hop_out=%0d host_in=%0d host_cpl=%0d crn=%0d errors=%0d %s",
                 MUT, tw, ybeats, kir, kor, hir, hcr, crn_got, errors, errors == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
