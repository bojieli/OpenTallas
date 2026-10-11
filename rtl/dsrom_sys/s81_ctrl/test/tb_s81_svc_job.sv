`timescale 1ns/1ps
// s81-svceng-1011: engine-4 gate bench.  NS scan-service slabs, each = ot_s81_svc_job in front of the closed IO hub
// ot_s81ph_svc_io (NQ 4) with 4 behavioural quadrants and one behavioural index reader obeying SVC FRAME PROTOCOL v1.1;
// one dsfd_svc_join (the single engine-4 adapter) driven by a credit-counting issuer (dsfd_sp_ctrl's role).  The VM
// model sends each job's q frames to every slab >= LEAD cycles after the job's descriptor.  Golden = the sources'
// deterministic result frames (a function of the q words each source RECEIVED is checked against the words SENT).
// Checks: every result frame leaves the slab pins exactly once, in per-source order, with golden content; every job's
// done arrives at the controller in order with its tag, AFTER the last END of the job on every slab; no slab fault.
// TBMUT: 1 drop the descriptor of job 3 (dropped start), 2 job 3's descriptor misses source 0 in its END set (wrong
// descriptor), 3 job 3's descriptor names one q frame too many.  JMUT -> ot_s81_svc_job MUT, JNMUT -> dsfd_svc_join MUT.
module tb_s81_svc_job #(parameter integer TILE = 0, NS = 2, NJ = 40, TBMUT = 0, JMUT = 0, JNMUT = 0, LEAD = 16, SEED = 1);
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst = 0; integer cyc = 0;
    always @(posedge clk) begin cyc <= cyc + 1; if (cyc == 5) rst <= 1; end
    function automatic [31:0] xs(input [31:0] s); reg [31:0] t; begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end endfunction
    function automatic [511:0] hw(input [31:0] a, input [31:0] b, input [31:0] c);
        integer i; reg [31:0] x; begin x = a * 32'h9E3779B1 ^ b * 32'h85EBCA77 ^ c; for (i = 0; i < 16; i = i + 1) begin x = xs(x + i); hw[32*i +: 32] = x; end end
    endfunction
    // ---------------- job plan (same for every slab; contents differ per slab)
    reg [3:0] jm [0:NJ-1]; reg ji [0:NJ-1]; reg [7:0] jnq [0:NJ-1]; reg [7:0] jtag [0:NJ-1];
    integer jr [0:NJ-1][0:4]; integer jl [0:NJ-1][0:4]; reg [1:0] jst [0:NJ-1][0:4];   // results: frames, len, stream
    integer i, j, k, s; reg [31:0] sd;
    initial begin
        sd = SEED * 7919 + 17;
        for (j = 0; j < NJ; j = j + 1) begin
            sd = xs(sd); jm[j] = (sd % 15) + 1; ji[j] = (sd >> 8) % 3 == 0; jnq[j] = 1 + (sd >> 12) % 3; jtag[j] = j % 128;
            for (k = 0; k < 5; k = k + 1) begin sd = xs(sd); jr[j][k] = 1 + sd % 3; jl[j][k] = (sd >> 4) % 12; jst[j][k] = (k < 4) ? ((sd >> 9) % 4 == 0 ? 3 : 0) : ((sd >> 9) % 2 ? 1 : 2); end
        end
    end
    // ---------------- engine 4: issuer -> join -> slabs
    reg [84:0] c_cmd = 0; wire [8:0] c_done; wire [1:0] c_st;
    wire [33*NS-1:0] j_cmd; wire [2*NS-1:0] j_dn;
    dsfd_svc_join #(.NS(NS), .MUT(JNMUT)) u_join (.ck(clk), .rst(rst), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st), .j_cmd(j_cmd), .j_dn(j_dn));
    integer issued = 0, done_n = 0, tagerr = 0, dlate = 0; integer t_issue [0:NJ-1]; integer last_end [0:NJ-1];
    reg [23:0] arg;
    initial for (j = 0; j < NJ; j = j + 1) begin t_issue[j] = -1; last_end[j] = 0; end
    always @(posedge clk) begin
        c_cmd <= 0;
        if (c_done[8]) begin
            if (c_done[7:0] !== jtag[done_n]) tagerr = tagerr + 1;
            if (cyc < last_end[done_n]) begin dlate = dlate + 1; $display("EARLY DONE job %0d at %0d < last END %0d", done_n, cyc, last_end[done_n]); end
            done_n = done_n + 1;
        end
        if (rst && cyc > 30 && issued < NJ && issued - done_n < 8 && (cyc % 7) == 0) begin
            arg = {9'd0, jnq[issued] + ((TBMUT == 3 && issued == 3) ? 8'd1 : 8'd0), 2'd0, ji[issued], jm[issued] & ((TBMUT == 2 && issued == 3) ? 4'b1110 : 4'b1111)};
            if (!(TBMUT == 1 && issued == 3)) c_cmd <= {1'b1, 1'b0, 10'd0, 21'd0, 21'd0, arg, jtag[issued][6:0]};
            t_issue[issued] = cyc; issued = issued + 1;
        end
    end
    // ---------------- slabs
    integer fault_n = 0, frames_ok = 0, frames_bad = 0, frames_exp = 0;
    genvar gs;
    generate for (gs = 0; gs < NS; gs = gs + 1) begin : g_s
        reg [514:0] q = 0; wire [514:0] core_q;
        wire [513:0] od, xd; wire [1025:0] ad; wire hf; wire [2059:0] q_q;
        wire [3:0] od_r, a0_r; wire a1_r, x_r;
        reg [3:0] od_v = 0, a0_v = 0; reg [2047:0] od_d = 0, a0_d = 0; reg a1_v = 0, x_v = 0; reg [511:0] a1_d = 0, x_d = 0;
        if (TILE == 0) begin : g_flat
            ot_s81_svc_job #(.MUT(JMUT)) u_job (.ck(clk), .rs_n(rst), .j_cmd(j_cmd[33*gs +: 33]), .j_dn(j_dn[2*gs +: 2]),
                .q(q), .core_q(core_q), .ad(ad), .xd(xd), .od(od));
            ot_s81ph_svc_io #(.NQ(4), .SYNC(1)) u_io (.ck(clk), .rst(rst), .q(core_q), .od(od), .xd(xd), .ad(ad), .fault(hf), .q_q(q_q),
                .od_v(od_v), .od_d(od_d), .od_r(od_r), .a0_v(a0_v), .a0_d(a0_d), .a0_r(a0_r), .a1_v(a1_v), .a1_d(a1_d), .a1_r(a1_r),
                .x_v(x_v), .x_d(x_d), .x_r(x_r));
        end else begin : g_tile   // the slab composition: job tile + the closed hub tiles (as dsfd_svc_c)
            wire of_, xf_, af_;
            dsfd_svcio_job #(.MUT(JMUT)) u_job (.ck(clk), .rst(rst), .j(j_cmd[33*gs +: 33]), .jd(j_dn[2*gs +: 2]), .q(q), .q_o(core_q),
                .t_a0({ad[492:481], ad[508:496], ad[0]}), .t_a1({ad[1005:994], ad[1021:1009], ad[513]}),
                .t_x({xd[493:482], xd[509:497], xd[1]}), .t_od({od[493:482], od[509:497], od[1]}));
            ot_s81ph_svc_io_t u_io (.ck(clk), .rst(rst), .q(core_q), .od(od), .xd(xd), .ad(ad), .fault(hf), .q_q(q_q),
                .od_v(od_v), .od_d(od_d), .od_r(od_r), .a0_v(a0_v), .a0_d(a0_d), .a0_r(a0_r), .a1_v(a1_v), .a1_d(a1_d), .a1_r(a1_r),
                .x_v(x_v), .x_d(x_d), .x_r(x_r), .of(of_), .xf(xf_), .af(af_));
        end
        // VM: job j's q frames after its descriptor + LEAD (one word a cycle, no ready)
        integer vj = 0, vf = 0, vw = 0, vlen; reg [511:0] hdr;
        always @(posedge clk) begin
            q <= 0;
            if (vj < NJ && t_issue[vj] >= 0 && cyc >= t_issue[vj] + LEAD) begin
                vlen = 1 + (vj + vf) % 3;
                if (vw == 0) begin
                    hdr = hw(gs, vj, vf); hdr[511:508] = (ji[vj] && vf == jnq[vj] - 1) ? 4'd4 : 4'd1; hdr[507] = (vf == jnq[vj] - 1);
                    hdr[506:503] = jm[vj]; hdr[502:495] = jtag[vj]; hdr[494:492] = 0; hdr[491:480] = vlen;
                    q <= {2'b01, hdr, 1'b1}; vw = 1;
                end else begin
                    q <= {2'b01, hw(gs + 100, vj, vf * 16 + vw), 1'b1};
                    if (vw == vlen) begin vw = 0; vf = vf + 1; if (vf == jnq[vj]) begin vf = 0; vj = vj + 1; end end else vw = vw + 1;
                end
            end
        end
        // sources 0..3 (quadrants on q_q[q], results on a0 / od) and 4 (index reader: sees quadrant 0's copy of every
        // frame, acts on IDX_Q frames; results on a1 / x).  Each keeps a running hash of the words it RECEIVED for the job.
        genvar gq;
        for (gq = 0; gq < 5; gq = gq + 1) begin : g_q
            wire [514:0] qi = q_q[515*(gq == 4 ? 0 : gq) +: 515];
            reg in_f = 0, mine = 0; integer rem = 0; reg [31:0] acc = 0; reg trig = 0; reg [7:0] ttag; reg [31:0] tacc;
            integer pend [0:NJ-1]; reg [31:0] pacc [0:NJ-1]; integer ph = 0, pt = 0;
            reg lastf = 0; reg [7:0] ftag;
            always @(posedge clk) begin
                if (qi[0]) begin
                    acc = acc ^ qi[32:1] ^ qi[480:449];
                    if (!in_f) begin
                        mine = (gq < 4) ? qi[504 + gq] : (qi[512:509] == 4'd4);
                        rem = qi[492:481]; in_f = (rem != 0); lastf = qi[508]; ftag = qi[503:496];
                    end else begin rem = rem - 1; if (rem == 0) in_f = 0; end
                    if (!in_f && lastf) begin
                        if (mine) begin pacc[pt] = acc; pend[pt] = ftag; pt = pt + 1; end
                        acc = 0; lastf = 0;
                    end
                end
            end
            // emitter
            integer ej = 0, ef = 0, ew = 0, edl = 0; reg [31:0] sdq; reg [511:0] eh; reg [1:0] estr; reg busy = 0;
            reg ev = 0; reg [511:0] ed = 0; reg evn; reg [511:0] edn; wire er = (gq < 4) ? ((estr == 3) ? od_r[gq] : a0_r[gq]) : ((estr == 1) ? a1_r : x_r);
            initial sdq = SEED * 31 + gq * 1013 + gs * 7;
            always @(posedge clk) begin
                evn = ev; edn = ed;
                if (evn && er) evn = 0;
                if (!evn && ph < pt) begin
                    // job of the head pending entry: find it by tag order (sources receive jobs in order)
                    while (ej < NJ && !((gq < 4) ? jm[ej][gq] : ji[ej])) ej = ej + 1;
                    sdq = xs(sdq);
                    if (edl > 0) edl = edl - 1;
                    else if (ej < NJ) begin
                        estr = jst[ej][gq];
                        if (ew == 0) begin
                            eh = hw(pacc[ph], ej * 8 + ef, gs * 5 + gq);
                            eh[511:508] = (gq < 4) ? ((estr == 3) ? 4'd11 : 4'd8) : ((estr == 1) ? 4'd9 : 4'd10);
                            eh[507] = (ef == jr[ej][gq] - 1); eh[506:503] = gq; eh[502:495] = pend[ph]; eh[494:492] = 0; eh[491:480] = jl[ej][gq];
                            edn = eh; evn = 1;
                            if (jl[ej][gq] == 0) begin ef = ef + 1; edl = sdq % 40; end else ew = 1;
                        end else begin
                            edn = hw(pacc[ph] + ew, ej * 8 + ef, gs * 5 + gq + 64); evn = 1;
                            if (ew == jl[ej][gq]) begin ew = 0; ef = ef + 1; edl = sdq % 40; end else ew = ew + 1;
                        end
                        if (ef == jr[ej][gq]) begin ef = 0; ej = ej + 1; ph = ph + 1; edl = sdq % 200; end
                    end
                end
                ev <= evn; ed <= edn;
            end
            always @* begin
                if (gq < 4) begin
                    od_v[gq] = ev && estr == 3; a0_v[gq] = ev && estr != 3;
                    od_d[512*gq +: 512] = ed; a0_d[512*gq +: 512] = ed;
                end else begin
                    a1_v = ev && estr == 1; x_v = ev && estr != 1; a1_d = ed; x_d = ed;
                end
            end
        end
        // pin scoreboard: per source, frames in order with golden content (recomputed from what the VM SENT)
        integer sj [0:19], sf [0:19], sw [0:19]; reg [31:0] sacc [0:19];   // per (source, stream)
        integer kk;
        initial for (kk = 0; kk < 20; kk = kk + 1) begin sj[kk] = 0; sf[kk] = 0; sw[kk] = 0; end
        function automatic [31:0] sent_acc(input integer src, input integer jj);
            integer f, w, ln; reg [31:0] a; reg [511:0] h, d;
            begin a = 0;
                for (f = 0; f < jnq[jj]; f = f + 1) begin
                    ln = 1 + (jj + f) % 3;
                    h = hw(gs, jj, f); h[511:508] = (ji[jj] && f == jnq[jj] - 1) ? 4'd4 : 4'd1; h[507] = (f == jnq[jj] - 1);
                    h[506:503] = jm[jj]; h[502:495] = jtag[jj]; h[494:492] = 0; h[491:480] = ln;
                    a = a ^ h[31:0] ^ h[479:448];
                    for (w = 1; w <= ln; w = w + 1) begin d = hw(gs + 100, jj, f * 16 + w); a = a ^ d[31:0] ^ d[479:448]; end
                end
                sent_acc = a; end
        endfunction
        reg [3:0] oin = 0; integer orem [0:3]; integer osrc [0:3];
        task automatic chk(input integer st, input [511:0] w);
            integer src, jj, ky; reg [511:0] e;
            begin
                if (!oin[st]) begin
                    src = w[506:503]; osrc[st] = src;
                    if (src > 4) begin frames_bad = frames_bad + 1; end
                    else begin
                        ky = src * 4 + st;
                        while (sj[ky] < NJ && !(((src < 4) ? jm[sj[ky]][src] : ji[sj[ky]]) && jst[sj[ky]][src] == st)) sj[ky] = sj[ky] + 1;
                        jj = sj[ky];
                        if (jj >= NJ) frames_bad = frames_bad + 1;
                        else begin
                            if (sw[ky] == 0 && sf[ky] == 0) sacc[ky] = sent_acc(src, jj);
                            e = hw(sacc[ky], jj * 8 + sf[ky], gs * 5 + src);
                            e[511:508] = w[511:508]; e[507] = (sf[ky] == jr[jj][src] - 1); e[506:503] = src; e[502:495] = jtag[jj]; e[494:492] = 0; e[491:480] = jl[jj][src];
                            if (w !== e) begin frames_bad = frames_bad + 1; if (frames_bad < 4) $display("BAD HDR slab %0d src %0d job %0d", gs, src, jj); end
                            else begin frames_ok = frames_ok + 1; if (frames_ok > 300 && frames_ok < 306) $display("OKX st %0d src %0d jj %0d sf %0d jr %0d len %0d ky %0d", st, src, jj, sf[ky], jr[jj][src], w[491:480], ky); end
                            if (w[507] && cyc > last_end[jj]) last_end[jj] = cyc;
                            orem[st] = w[491:480]; oin[st] = (w[491:480] != 0);
                            sw[ky] = 1;
                            if (w[491:480] == 0) begin sw[ky] = 0; sf[ky] = sf[ky] + 1; if (sf[ky] == jr[jj][src]) begin sf[ky] = 0; sj[ky] = sj[ky] + 1; end end
                        end
                    end
                end else begin
                    src = osrc[st]; ky = src * 4 + st; jj = sj[ky];
                    e = hw(sacc[ky] + sw[ky], jj * 8 + sf[ky], gs * 5 + src + 64);
                    if (w !== e) begin frames_bad = frames_bad + 1; if (frames_bad < 4) $display("BAD WORD slab %0d src %0d job %0d", gs, src, jj); end
                    orem[st] = orem[st] - 1; if (orem[st] == 0) oin[st] = 0;
                    if (sw[ky] == jl[jj][src]) begin sw[ky] = 0; sf[ky] = sf[ky] + 1; if (sf[ky] == jr[jj][src]) begin sf[ky] = 0; sj[ky] = sj[ky] + 1; end end
                    else sw[ky] = sw[ky] + 1;
                end
            end
        endtask
        integer dbg = 0;
        always @(posedge clk) begin
            if ((ad[0] || ad[513] || xd[1] || od[1]) && dbg < 0) begin dbg = dbg + 1;
                $display("DBG %0d s%0d a0 %b %h a1 %b %h x %b %h od %b %h", cyc, gs, ad[0], ad[512:449], ad[513], ad[1025:962], xd[1], xd[513:450], od[1], od[513:450]); end
            if (ad[0]) chk(0, ad[512:1]);
            if (ad[513]) chk(1, ad[1025:514]);
            if (xd[1]) chk(2, xd[513:2]);
            if (od[1]) chk(3, od[513:2]);
        end
    end endgenerate
    // expected frames
    initial begin
        #1; frames_exp = 0;
        for (s = 0; s < NS; s = s + 1) for (j = 0; j < NJ; j = j + 1) for (k = 0; k < 5; k = k + 1)
            if ((k < 4) ? jm[j][k] : ji[j]) frames_exp = frames_exp + jr[j][k];
    end
    integer idle = 0, fl;
    always @(posedge clk) begin
        fl = (c_st[0] === 1'b1);
        idle = (done_n == NJ || fl) ? idle + 1 : 0;
        if (idle > 400 || cyc > 400000) begin
            $display("SVCJOB jobs=%0d issued=%0d dones=%0d tag_errors=%0d early_dones=%0d frames_ok=%0d frames_exp=%0d frames_bad=%0d fault=%0d cycles=%0d",
                     NJ, issued, done_n, tagerr, dlate, frames_ok, frames_exp, frames_bad, fl, cyc);
            if (done_n == NJ && tagerr == 0 && dlate == 0 && frames_ok == frames_exp && frames_bad == 0 && !fl) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule
