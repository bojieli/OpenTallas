`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// tb_s81_die_fld (s81-ctl-1011, 2026-10-11): die bench of the S81 control plane driving a REAL slab pair, on the
// smallest vehicle that holds the mechanism (ADAPTER_CONTRACT_1011 v2 rule "bench"):
//   dsfd_sp_ctrl_e (the layer-die master, hop_tx retired: program memory, guard, package controller, stage sequencer)
//     c0 / d0  <->  dsfd_sp_gather_c (fld endpoint: ot_s81_slab_ep + phase stage) -> dsfd_sp_capture_c (drained -> done)
//     c<e> / d<e> (e = 1..7, 10) <-> behavioural engines behind REAL ot_s81_slab_ep endpoints (su / hc on the 0.9 GHz
//     serial clock, the rest on the 1.2 GHz stream clock); an engine starts its head job when the job's in-stage
//     predecessors have ended (dataflow) and ends after the job's golden duration.
// Driver (no host stand-in): the stage program (tools/s81_ctrl/die_bench_stim.py: a real S81 stage program, default
// S001 = L0 ffn + L1 attn, 60 jobs, 8 field phases) is loaded through pw_*; each job's HIDDEN message (header + 640
// payload flits) enters through i_*; the package controller writes the payload through vwe into the bench VM and
// hands the job to the sequencer.  The bench VM posts each field phase's control word (f_vm) when the fld job's
// predecessors have ended (or, without predecessors, when the job's payload has landed); the field model drives the
// phase's golden root partials into the gather lanes when the gather releases the phase (t_xgo) -- the x broadcast.
// Checks: (1) every capture VM write equals the reference (128 ot_v41_ret_root + ot_dsrom_rd64_vm_capture, the
// tb_s81ph_gather_capture reference) per root as a multiset (UNORD; the tiled capture's transaction-level contract);
// (2) every done reaching dsfd_sp_ctrl_e is the next op of its port in program order for its job slot, each op done
// exactly once; (3) every job starts at or after all its predecessors ended; (4) the sequencer's stage done fires once
// per job; (5) no fault anywhere (controller, every endpoint, gather phase stage).
// MUT (gather endpoint): 2 wrong done tag, 3 early start (ignores e_inputs_present), 4 dropped done -> must FAIL.
// Plusargs: +PROG=<prog.txt> +STIM=<stim.txt>.  ck : ckv = 4 : 3 (1.2 / 0.9 GHz).
// ---------------------------------------------------------------------------------------------------------------
module tb_s81_die_fld;
    parameter integer MUT = 0, JOBS = 2;
    localparam integer NR = 128, XW = 640, MAXC = 16384, TMAX = 600000;
    reg ck = 0, ckv = 0;
    always #3 ck = ~ck;
    always #4 ckv = ~ckv;
    reg rst = 0, rsv = 0;
    integer cyc = 0;
    always @(posedge ck) cyc <= cyc + 1;
    // ---------------- program + stimulus tables
    integer nop = 0, nph = 0, ncl = 0;
    integer o_port [0:127], o_arg [0:127], o_dur [0:127], o_np [0:127], o_p [0:127][0:3], o_ph [0:127];
    reg [63:0] ph_par [0:15][0:9]; integer ph_c0 [0:15], ph_cn [0:15];
    integer c_gap [0:MAXC-1], c_root [0:MAXC-1], c_e [0:MAXC-1]; reg [31:0] c_t [0:MAXC-1], c_d [0:MAXC-1];
    // ---------------- DUT: control plane
    reg pw_v = 0; reg [6:0] pw_a = 0; reg [27:0] pw_d = 0; reg [7:0] plen = 0;
    reg i_v = 0; wire i_r; reg [511:0] i_d = 0; reg i_l = 0;
    wire [84:0] c [0:11]; wire [8:0] d [0:11]; wire [1:0] est [0:11];
    wire vwe; wire [13:0] vwa; wire [511:0] vwd; wire flt, stk; wire [15:0] fvec, snap;
    dsfd_sp_ctrl_e #(.MY_ID(2), .SRC_LO(1), .SRC_HI(1)) u_ctl (.ck(ck), .rs(rst), .pw_v(pw_v), .pw_a(pw_a), .pw_d(pw_d),
        .prog_len(plen), .cfg_users(12'd4), .i_v(i_v), .i_r(i_r), .i_d(i_d), .i_l(i_l),
        .c0(c[0]), .c1(c[1]), .c2(c[2]), .c3(c[3]), .c4(c[4]), .c5(c[5]), .c6(c[6]), .c7(c[7]), .c8(c[8]), .c9(c[9]),
        .c10(c[10]), .c11(c[11]),
        .d0(d[0]), .d1(d[1]), .d2(d[2]), .d3(d[3]), .d4(d[4]), .d5(d[5]), .d6(d[6]), .d7(d[7]), .d8(d[8]), .d9(d[9]),
        .d10(d[10]), .d11(d[11]),
        .vwe(vwe), .vwa(vwa), .vwd(vwd), .flt(flt), .fvec(fvec), .stk(stk), .snap(snap));
    // ---------------- DUT: gather + capture (fld)
    reg [511:0] f_vm = 0;
    wire [6946:0] tcap; wire [13375:0] tvm; wire [11:0] tcd; wire [10:0] xgo;
    reg [760:0] tp [0:11];
    dsfd_sp_gather_c #(.MUT(MUT)) u_g (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_vm(f_vm), .t_capture(tcap),
        .rW0(tp[0][691:0]), .rW1(tp[1][760:0]), .rW2(tp[2][760:0]), .rW3(tp[3][760:0]), .rW4(tp[4][760:0]), .rW5(tp[5][691:0]),
        .rE0(tp[6][691:0]), .rE1(tp[7][760:0]), .rE2(tp[8][760:0]), .rE3(tp[9][760:0]), .rE4(tp[10][760:0]), .rE5(tp[11][691:0]),
        .c_cmd(c[0]), .c_done(d[0]), .c_st(est[0]), .f_cd(tcd), .t_xgo(xgo));
    dsfd_sp_capture_c u_c (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_gather(tcap), .t_vm(tvm), .t_cd(tcd));
    wire [63:0] dst = tvm[13312 +: 64];
    // ---------------- reference (as tb_s81ph_gather_capture)
    reg [NR-1:0] s_v; reg [31:0] s_t [0:NR-1]; reg [31:0] s_d [0:NR-1]; reg [NR-1:0] s_e, s_b;
    wire [NR-1:0] rr_v, rr_e, rr_f;
    wire [NR*16-1:0] rr_row, rr_bf; wire [NR*3-1:0] rr_pos; wire [NR*32-1:0] rr_fp;
    reg rst_n_ref = 0;
    genvar g;
    generate for (g = 0; g < NR; g = g + 1) begin : g_ref
        ot_v41_ret_root #(.D(128), .QD(128)) u_root (.clk(ck), .rst_n(rst_n_ref), .i_v(s_v[g]), .i_t(s_t[g]), .i_d(s_d[g]),
            .i_e(s_e[g]), .r_v(rr_v[g]), .r_row(rr_row[16*g +: 16]), .r_pos(rr_pos[3*g +: 3]), .r_fp32(rr_fp[32*g +: 32]),
            .r_bf16(rr_bf[16*g +: 16]), .r_e(rr_e[g]), .fault(rr_f[g]));
    end endgenerate
    reg p_v = 0;
    reg [46:0] p_id = 0; reg [9:0] p_ph = 0; reg [29:0] p_ob = 0, p_ops = 0; reg [2:0] p_np = 0; reg [1:0] p_fmt = 0;
    reg [15:0] p_rs = 0, p_rows = 0; reg p_lo = 0, p_hi = 0;
    wire [128*19-1:0] quota;
    ot_dsrom_s81_phase_capture_profile #(.ENABLE(1)) u_prof (.phase_rows(p_rows), .phase_np(p_np), .root_returns(quota));
    wire [NR-1:0] rv_valid; wire [NR*30-1:0] rv_addr; wire [NR*32-1:0] rv_data;
    wire r_ready, r_live, r_idle, r_drained, r_fault;
    ot_dsrom_rd64_vm_capture #(.ENABLE(1), .ROOTS(NR), .CAPACITY(1), .VM_AW(19), .VM_ALWAYS_ACCEPT(1)) u_rc (
        .clk(ck), .rst_n(rst_n_ref), .reset_request(1'b0), .phase_valid(p_v), .phase_ready(r_ready),
        .phase_identity(p_id), .phase_id(p_ph), .phase_root_rows(quota), .phase_obase(p_ob), .phase_ops(p_ops),
        .phase_np(p_np), .phase_fmt(p_fmt), .phase_rsplit(p_rs), .phase_fp32_low(p_lo), .phase_fp32_high(p_hi),
        .r_valid(rr_v), .r_error(rr_e), .r_row(rr_row), .r_bf16(rr_bf), .r_pos(rr_pos), .r_fp32(rr_fp),
        .vm_valid(rv_valid), .vm_accept(rv_valid), .vm_addr(rv_addr), .vm_data(rv_data), .vm_row(), .vm_pos(),
        .held_identity(), .held_phase(), .phase_live(r_live), .phase_idle(r_idle), .phase_drained(r_drained),
        .fault(r_fault));
    wire ref_fault = r_fault | (|rr_f);
    localparam integer NC [0:5] = '{10, 11, 11, 11, 11, 10};
    function automatic integer port_of(input integer r);
        integer h, t, b;
        begin h = r / 64; b = h * 64; port_of = -1;
            for (t = 0; t < 6; t = t + 1) begin if (port_of < 0 && r < b + NC[t]) port_of = 6 * h + t; b = b + NC[t]; end end
    endfunction
    function automatic integer lane_of(input integer r);
        integer h, t, b;
        begin h = r / 64; b = h * 64; lane_of = -1;
            for (t = 0; t < 6; t = t + 1) begin if (lane_of < 0 && r < b + NC[t]) lane_of = NC[t] - 1 - (r - b); b = b + NC[t]; end end
    endfunction
    integer pi, li, rr;
    always @* begin
        for (pi = 0; pi < 12; pi = pi + 1) begin
            tp[pi] = 761'd0;
            tp[pi][69 * NC[pi % 6] +: 2] = 2'b01;           // {fault 0, live 1}
        end
        for (rr = 0; rr < NR; rr = rr + 1) begin
            pi = port_of(rr); li = lane_of(rr);
            tp[pi][69 * li] = s_v[rr];
            tp[pi][69 * li + 1 +: 68] = {1'b0, s_b[rr], s_e[rr], s_d[rr], s_t[rr], s_v[rr]};
        end
    end
    // ---------------- write collection
    reg [50:0] refq [0:NR-1][$];
    reg [50:0] dutq [0:NR-1][$];
    integer k;
    always @(posedge ck) for (k = 0; k < NR; k = k + 1) if (rv_valid[k]) refq[k].push_back({rv_data[32*k +: 32], rv_addr[30*k +: 19]});
    always @(posedge ckv) for (k = 0; k < NR; k = k + 1) begin
        if (tvm[104*k]) dutq[k].push_back(tvm[104*k + 1 +: 51]);
        if (tvm[104*k + 52]) dutq[k].push_back(tvm[104*k + 53 +: 51]);
    end
    // ---------------- bench VM: payload writes
    integer nwr = 0;
    always @(posedge ck) if (vwe) nwr <= nwr + 1;
    // ---------------- job bookkeeping (slot bit of the tag = job index; JOBS <= 2)
    integer endt [0:1][0:127], stt [0:1][0:127];
    integer errors = 0;
    function automatic integer ready_op(input integer jb, input integer op);
        integer i, r;
        begin
            r = 1;
            if (o_np[op] == 0) r = (nwr >= XW * (jb + 1));
            for (i = 0; i < o_np[op]; i = i + 1) if (endt[jb][o_p[op][i]] < 0) r = 0;
            ready_op = r;
        end
    endfunction
    // ---------------- behavioural engines (ports 1..11) behind real slab endpoints
    genvar ge;
    generate for (ge = 1; ge < 12; ge = ge + 1) begin : g_eng
        wire eclk;
        if (ge == 1 || ge == 2) begin : g_s assign eclk = ckv; end else begin : g_f assign eclk = ck; end
        wire jv, jnew, epf; wire [83:0] jd, jnd;
        reg jdone = 1'b0, busy = 1'b0; integer rem = 0;
        ot_s81_slab_ep #(.QD(8), .JQ(2)) u_ep (.c_clk(ck), .c_rst_n(rst), .c_cmd(c[ge]), .c_done(d[ge]), .c_st(est[ge]),
            .e_clk(eclk), .e_rst_n(rst), .j_v(jv), .j_d(jd), .j_new(jnew), .j_new_d(jnd), .j_present(1'b1),
            .j_done(jdone), .slab_fault(1'b0), .ep_fault(epf));
        always @(posedge eclk) begin
            jdone <= 1'b0;
            if (jv && !jdone) begin
                if (!busy) begin
                    if (ready_op(jd[83], jd[6:0])) begin
                        busy <= 1'b1; rem <= (o_dur[jd[6:0]] > 0) ? o_dur[jd[6:0]] : 1; stt[jd[83]][jd[6:0]] = cyc;
                        if (o_port[jd[6:0]] != ge) begin errors = errors + 1; $display("ERR engine %0d got op %0d of port %0d", ge, jd[6:0], o_port[jd[6:0]]); end
                    end
                end else if (rem <= 1) begin
                    jdone <= 1'b1; busy <= 1'b0; endt[jd[83]][jd[6:0]] = cyc;
                end else rem <= rem - 1;
            end
        end
    end endgenerate
    // fld: start = phase release (t_xgo), end = the gather endpoint's real done (capture drained)
    always @(posedge ck) begin
        if (u_g.jnew) stt[u_g.jnd[83]][u_g.jnd[6:0]] = cyc;
        if (u_g.dn) endt[u_g.jd[83]][u_g.jd[6:0]] = cyc;
    end
    // ---------------- done order at the controller pins
    integer nxt [0:11][0:1];                        // next op index to scan per (port, slot)
    integer ndone = 0, maxlat = 0;
    integer e2, s2, t2;
    always @(posedge ck) if (rst) for (e2 = 0; e2 < 12; e2 = e2 + 1) if (d[e2][8]) begin
        s2 = d[e2][7]; t2 = d[e2][6:0];
        while (nxt[e2][s2] < nop && o_port[nxt[e2][s2]] != e2) nxt[e2][s2] = nxt[e2][s2] + 1;
        if (nxt[e2][s2] != t2) begin
            errors = errors + 1;
            if (errors < 10) $display("ERR done order: port %0d slot %0d got op %0d expected %0d", e2, s2, t2, nxt[e2][s2]);
        end else nxt[e2][s2] = nxt[e2][s2] + 1;
        if (endt[s2][t2] < 0) begin errors = errors + 1; $display("ERR done before engine end: port %0d op %0d", e2, t2); end
        else if (cyc - endt[s2][t2] > maxlat) maxlat = cyc - endt[s2][t2];
        ndone = ndone + 1;
    end
    integer jdn = 0;
    always @(posedge ck) if (u_ctl.u.u.u_seq.job_done) jdn <= jdn + 1;
    // ---------------- bench VM: post the field phase words in fld order when the job's inputs are present
    integer pj = 0, pk = 0, posted = 0, released = 0;
    always @(posedge ck) if (xgo[10]) released <= released + 1;
    function automatic integer next_fld(input integer from);
        integer q; begin next_fld = nop; for (q = nop - 1; q >= from; q = q - 1) if (o_ph[q] >= 0) next_fld = q; end
    endfunction
    initial begin : vm_post
        integer ph;
        wait (rst && plen != 0);
        pk = next_fld(0);
        while (pj < JOBS) begin
            @(negedge ckv);
            if (pk >= nop) begin pj = pj + 1; pk = next_fld(0); end
            else if (posted - released < 3 && ready_op(pj, pk)) begin
                ph = o_ph[pk];
                f_vm = 0; f_vm[0] = 1;
                f_vm[159:1] = {1'b0, ph_par[ph][0][15:0], ph_par[ph][7][0], ph_par[ph][6][0], ph_par[ph][5][15:0],
                               ph_par[ph][4][1:0], ph_par[ph][1][2:0], ph_par[ph][3][29:0], ph_par[ph][2][29:0],
                               ph_par[ph][9][9:0], ph_par[ph][8][46:0], 2'b00};
                @(negedge ckv); f_vm[0] = 0;
                posted = posted + 1;
                pk = next_fld(pk + 1);
            end
        end
    end
    // ---------------- field model: the x broadcast of a released phase -> its golden partials
    integer nfp = 0;
    initial begin : field
        integer ph, ci, j;
        s_v = 0; s_e = 0; s_b = 0;
        for (j = 0; j < NR; j = j + 1) begin s_t[j] = 0; s_d[j] = 0; end
        forever begin
            @(posedge ck); #0.5;
            if (xgo[10]) begin
                ph = xgo[9:0];
                @(negedge ck);
                p_rows = ph_par[ph][0]; p_np = ph_par[ph][1]; p_ob = ph_par[ph][2]; p_ops = ph_par[ph][3]; p_fmt = ph_par[ph][4];
                p_rs = ph_par[ph][5]; p_lo = ph_par[ph][6]; p_hi = ph_par[ph][7]; p_id = ph_par[ph][8]; p_ph = ph_par[ph][9];
                // the reference rd64 capture leaves reset / its previous phase on its own schedule: wait (bounded) for it
                for (j = 0; j < 256 && !r_ready; j = j + 1) @(negedge ck);
                if (!r_ready) begin errors = errors + 1; $display("ERR reference not ready at phase %0d", ph); end
                p_v = 1; @(negedge ck); p_v = 0;
                for (j = 0; j < 30; j = j + 1) @(negedge ck);          // x broadcast + field latency
                begin : drive
                    reg [NR-1:0] n_v, n_e; reg [31:0] n_t [0:NR-1]; reg [31:0] n_d [0:NR-1];
                    n_v = 0; n_e = 0;
                    for (ci = ph_c0[ph]; ci < ph_c0[ph] + ph_cn[ph]; ci = ci + 1) begin
                        if (c_gap[ci] != 0) begin
                            for (j = 0; j < NR; j = j + 1) begin s_v[j] = n_v[j]; s_t[j] = n_t[j]; s_d[j] = n_d[j]; s_e[j] = n_e[j]; s_b[j] = $random; end
                            n_v = 0; n_e = 0;
                            @(negedge ck); s_v = 0;
                            for (j = 1; j < c_gap[ci]; j = j + 1) @(negedge ck);
                        end
                        n_v[c_root[ci]] = 1; n_t[c_root[ci]] = c_t[ci]; n_d[c_root[ci]] = c_d[ci]; n_e[c_root[ci]] = c_e[ci];
                    end
                    for (j = 0; j < NR; j = j + 1) begin s_v[j] = n_v[j]; s_t[j] = n_t[j]; s_d[j] = n_d[j]; s_e[j] = n_e[j]; s_b[j] = $random; end
                    @(negedge ck); s_v = 0;
                end
                nfp = nfp + 1;
            end
        end
    end
    // ---------------- main: load, reset, program, messages, wait, compare
    task automatic send_flit(input [511:0] dd, input ll);
        begin
            i_v = 1; i_d = dd; i_l = ll;
            while (!i_r) @(negedge ck);
            @(negedge ck);
        end
    endtask
    initial begin : main
        integer fd, rc, w, jb, e, s, bad, tot, tr, td, gst_f;
        reg [8*8-1:0] cmd; reg [63:0] a [0:9];
        string prog, stim;
        reg [511:0] hdr;
        for (jb = 0; jb < 2; jb = jb + 1) for (w = 0; w < 128; w = w + 1) begin endt[jb][w] = -1; stt[jb][w] = -1; end
        for (e = 0; e < 12; e = e + 1) begin nxt[e][0] = 0; nxt[e][1] = 0; end
        if (!$value$plusargs("PROG=%s", prog)) $fatal(1, "+PROG");
        if (!$value$plusargs("STIM=%s", stim)) $fatal(1, "+STIM");
        fd = $fopen(prog, "r");
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%d %d %d %d %d %d %d %d %d\n", o_port[nop], o_arg[nop], o_dur[nop], o_np[nop],
                         o_p[nop][0], o_p[nop][1], o_p[nop][2], o_p[nop][3], o_ph[nop]);
            if (rc == 9) nop = nop + 1;
        end
        $fclose(fd);
        fd = $fopen(stim, "r");
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%s", cmd);
            if (rc != 1) break;
            if (cmd == "P") begin
                rc = $fscanf(fd, "%h %h %h %h %h %h %h %h %h %h", a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], a[8], a[9]);
                for (w = 0; w < 10; w = w + 1) ph_par[nph][w] = a[w];
                ph_c0[nph] = ncl; ph_cn[nph] = 0; nph = nph + 1;
            end else if (cmd == "C") begin
                rc = $fscanf(fd, "%h %h %h %h %h", a[0], a[1], a[2], a[3], a[4]);
                c_gap[ncl] = a[0]; c_root[ncl] = a[1]; c_t[ncl] = a[2]; c_d[ncl] = a[3]; c_e[ncl] = a[4];
                ncl = ncl + 1; ph_cn[nph - 1] = ph_cn[nph - 1] + 1;
            end
        end
        $fclose(fd);
        $display("TB_S81_DIE_FLD program %0d ops, %0d field phases, %0d partials, JOBS %0d, MUT %0d", nop, nph, ncl, JOBS, MUT);
        repeat (10) @(negedge ck);
        rst = 1; rsv = 1; rst_n_ref = 1;
        repeat (60) @(negedge ck);
        // program through pw_*
        for (w = 0; w < nop; w = w + 1) begin
            pw_v = 1; pw_a = w; pw_d = {o_port[w][3:0], o_arg[w][23:0]}; @(negedge ck);
        end
        pw_v = 0; plen = nop;
        repeat (20) @(negedge ck);
        // stage messages through i_*: HIDDEN header + 640 payload flits per job
        for (jb = 0; jb < JOBS; jb = jb + 1) begin
            hdr = 0; hdr[11:0] = 2; hdr[23:12] = 1; hdr[27:24] = 1; hdr[39:28] = XW; hdr[51:40] = jb; hdr[72:52] = 0;
            hdr[146:126] = 1000 + jb;
            send_flit(hdr, 1'b0);
            for (w = 0; w < XW; w = w + 1) send_flit({16{32'(jb * 1000003 + w * 7919 + 17)}}, w == XW - 1);
            i_v = 0; i_l = 0;
        end
        // wait for every job's stage done (or a timeout)
        while (jdn < JOBS && cyc < TMAX) @(negedge ck);
        repeat (400) @(negedge ck);
        // ---- compare
        bad = 0; tot = 0;
        for (k = 0; k < NR; k = k + 1) begin
            tr = refq[k].size(); td = dutq[k].size(); tot = tot + tr;
            if (tr != td) begin bad = bad + 1; if (bad < 6) $display("MISMATCH root %0d: ref %0d writes, dut %0d", k, tr, td); end
            else begin
                refq[k].sort(); dutq[k].sort();
                for (rr = 0; rr < tr; rr = rr + 1) if (refq[k][rr] != dutq[k][rr]) begin
                    bad = bad + 1; if (bad < 6) $display("MISMATCH root %0d sorted write %0d: ref %h dut %h", k, rr, refq[k][rr], dutq[k][rr]); break; end
            end
        end
        // every op ended once per job, after its predecessors
        for (jb = 0; jb < JOBS; jb = jb + 1) for (w = 0; w < nop; w = w + 1) begin
            if (endt[jb][w] < 0) begin errors = errors + 1; if (errors < 20) $display("ERR job %0d op %0d never ended (port %0d)", jb, w, o_port[w]); end
            for (s = 0; s < o_np[w]; s = s + 1) if (stt[jb][w] >= 0 && stt[jb][w] < endt[jb][o_p[w][s]]) begin
                errors = errors + 1; $display("ERR job %0d op %0d started %0d before pred %0d ended %0d", jb, w, stt[jb][w], o_p[w][s], endt[jb][o_p[w][s]]); end
        end
        gst_f = 0; for (e = 0; e < 12; e = e + 1) if (est[e][0]) begin gst_f = gst_f + 1; $display("ERR endpoint %0d fault", e); end
        $display("SUMMARY cycles=%0d jobs_done=%0d/%0d dones=%0d/%0d phases_released=%0d field_phases=%0d writes=%0d mismatching_roots=%0d ref_fault=%0d dut_fault=%0d ctrl_flt=%0d fvec=%h stuck=%0d ep_faults=%0d gather_stage_fault=%0d max_done_latency=%0d errors=%0d",
                 cyc, jdn, JOBS, ndone, JOBS * nop, released, nfp, tot, bad, ref_fault, dst[3], flt, fvec, stk, gst_f, u_g.sf, maxlat, errors);
        if (bad == 0 && errors == 0 && jdn == JOBS && ndone == JOBS * nop && !ref_fault && !dst[3] && !flt && gst_f == 0 && !u_g.sf && tot > 0)
            $display("TB_S81_DIE_FLD PASS");
        else $display("TB_S81_DIE_FLD FAIL");
        $finish;
    end
endmodule
