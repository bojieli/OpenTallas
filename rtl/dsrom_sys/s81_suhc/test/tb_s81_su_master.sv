`timescale 1ns/1ps
// Bench of dsfd_sp_su (stream s81-suhc-1011): the S81 SU die master driven at its controller-side adapter pins
// exactly as dsfd_sp_ctrl's stage sequencer drives an engine port (one-cycle c_cmd_v pulses, QD 8 credits returned
// only by c_done_v, no ready), a behavioural VM (fixed read latency LVM on every read slot, writes in issue order) and
// no y bus (SU operands come through the wide VM read port).  Files (tools/s81_suhc/su_gate.py prep): vm.mem (initial
// VM image), prog.mem (84-bit commands in program order), expa.mem / expd.mem
// (expected VM rows), n.mem (counts), jexp.mem (per op: first index into expa / ed and row count of the job's result
// rows).  Done contract check: at the core's e_done_v (slab clock, after that cycle's writes) every result row of the
// job must already hold its expected value -- a consumer issued on done reads them; a done ahead of the job's last
// row write counts in early= and fails the run even when the row lands later.  Prints per job its engine start / done (slab cycles) and
// SUG jobs= done= err= rows= fault= code= cyc= bad_tag= early=  then SUG PASS / SUG FAIL.
`ifdef SU_HIER
`define CORE `SU_CTL.u_core
`else
`define CORE dut.u_core
`endif
// the control tile's scope: with -DSU_TILE_TOPS (gate s81su_tiles, tools/s81_suhc/su_tile_tops.py) the slab instantiates the
// routed top dsfd_su_t_ctl (core instance u_c) inside the generated block g_tt0_u_ctl
`ifdef SU_TILE_TOPS
`define SU_CTL dut.g_tt0_u_ctl.u_ctl.u_c
`else
`define SU_CTL dut.u_ctl
`endif
module tb_s81_su_master;
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16, SM_NVMAX = 40;
    parameter integer S_RD = 16, S_WR = 16, LVM = 10, MUT = 0, AMUT = 0;
    parameter integer MAXJ = 64, MAXE = 4096, MAXY = 2048, TMAX = 400000;
    reg cck = 0, sk = 0, crs = 0, srs = 0;
    always #0.4165 cck = ~cck;              // controller 1.2 GHz
    always #0.4255 sk = ~sk;                // slab clock (stream domain, independent source: exercises the CDC)
    reg          c_cmd_v = 0;
    reg  [83:0]  c_cmd_d = 0;
    wire         c_done_v;
    wire [7:0]   c_done_tag;
    reg          inp = 1;                   // operands of every program job are in the VM image before reset release
    wire [S_RD-1:0] rq_v;
    wire [S_RD*14-1:0] rq_row;
    reg  [S_RD-1:0] rs_v = 0;
    reg  [S_RD*512-1:0] rs_d = 0;
    wire [S_WR-1:0] wq_v;
    wire [S_WR*14-1:0] wq_row;
    wire [S_WR*16-1:0] wq_mask;
    wire [S_WR*512-1:0] wq_d;
    wire flt, online;
    wire [3:0] fcode;
`ifdef SU_HIER
    dsfd_sp_su_h #(.QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H), .SM_LPH(SM_LPH), .SM_NVMAX(SM_NVMAX),
        .S_RD(S_RD), .S_WR(S_WR), .MUT(MUT), .AMUT(AMUT)) dut (
        .cck(cck), .crs(crs), .sk(sk), .srs(srs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v),
        .c_done_tag(c_done_tag), .inp(inp), .rq_v(rq_v), .rq_row(rq_row),
        .rs_v(rs_v), .rs_d(rs_d), .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .flt(flt),
        .online(online), .fcode(fcode));
`else
    dsfd_sp_su #(.QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H), .SM_LPH(SM_LPH), .SM_NVMAX(SM_NVMAX),
        .S_RD(S_RD), .S_WR(S_WR), .MUT(MUT), .AMUT(AMUT)) dut (
        .cck(cck), .crs(crs), .sk(sk), .srs(srs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v),
        .c_done_tag(c_done_tag), .inp(inp), .rq_v(rq_v), .rq_row(rq_row),
        .rs_v(rs_v), .rs_d(rs_d), .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .flt(flt),
        .online(online), .fcode(fcode));
`endif

    reg [511:0]     vm [0:16383];
    reg [83:0]      prog [0:MAXJ-1];
    reg [13:0]      ea [0:MAXE-1];
    reg [511:0]     ed [0:MAXE-1];
    reg [31:0]      nm [0:2];
    reg [63:0]      jexp [0:MAXJ-1];
    integer early, k;
    integer fd;
    integer n_qn, n_qnq, n_kv, n_kvq, n_qb, n_qbo, n_sw, n_swo, n_ss, n_se, n_sp, n_so, n_beat;
    initial begin n_qn = 0; n_qnq = 0; n_kv = 0; n_kvq = 0; n_qb = 0; n_qbo = 0; n_sw = 0; n_swo = 0; n_ss = 0; n_se = 0;
                  n_sp = 0; n_so = 0; n_beat = 0; end
`ifndef SU_HIER
    always @(posedge sk) begin
        n_qn += `CORE.qn_in; n_qnq += `CORE.qn_qv; n_kv += `CORE.kv_in; n_kvq += `CORE.kv_qv;
        n_qb += `CORE.qb_v; n_qbo += `CORE.qb_vo; n_sw += `CORE.sw_v; n_swo += `CORE.sw_vo;
        n_ss += `CORE.sm_sv; n_se += `CORE.sm_ev; n_sp += `CORE.sm_pv; n_so += `CORE.sm_ov;
        n_beat += `CORE.beat_v;
    end
`endif
    integer nj, ne, ny, i, s, errs, credits, ip, ndone, yb, bad_tag, scyc, t;
    reg [MAXJ-1:0] pend;
    integer jstart [0:MAXJ-1];
    integer jdone  [0:MAXJ-1];
    initial begin
        for (i = 0; i < 16384; i = i + 1) vm[i] = 512'd0;
        $readmemh("vm.mem", vm);
        $readmemh("prog.mem", prog);
        $readmemh("expa.mem", ea);
        $readmemh("expd.mem", ed);
        $readmemh("n.mem", nm);
        for (i = 0; i < MAXJ; i = i + 1) jexp[i] = 64'd0;
        $readmemh("jexp.mem", jexp);
        early = 0;
        nj = nm[0]; ne = nm[1]; ny = nm[2];
        for (i = 0; i < MAXJ; i = i + 1) begin jstart[i] = -1; jdone[i] = -1; end
        credits = 8; ip = 0; ndone = 0; yb = 0; bad_tag = 0; pend = 0; scyc = 0;
        repeat (4) @(posedge cck);
        crs = 1; srs = 1;
    end

    // ---- controller side: decoupled issue under QD 8 credits, completions return credits
    always @(posedge cck) if (crs) begin
        c_cmd_v <= 1'b0;
        if (c_done_v) begin
            if (!pend[c_done_tag[6:0]] || prog[c_done_tag[6:0]][83] != c_done_tag[7]) bad_tag = bad_tag + 1;
            else begin pend[c_done_tag[6:0]] = 1'b0; jdone[c_done_tag[6:0]] = scyc; end
            ndone = ndone + 1;
            credits = credits + 1;
        end
        if (online && ip < nj && credits > 0) begin
            c_cmd_v <= 1'b1; c_cmd_d <= prog[ip]; pend[ip] = 1'b1; credits = credits - 1; ip = ip + 1;
        end
    end

    // ---- slab side: VM, y source, job start stamps
    reg [S_RD-1:0]     dl_v [0:63];
    reg [S_RD*14-1:0]  dl_a [0:63];
    always @(posedge sk) if (srs) begin
        scyc = scyc + 1;
        if (`CORE.e_cmd_v && `CORE.e_cmd_ready) jstart[`CORE.e_cmd_d[6:0]] = scyc;
        // writes take effect at issue (before reads of the same cycle: the core never mixes them in one job), under
        // the slot's 32-bit word mask
        for (s = 0; s < S_WR; s = s + 1)
            if (wq_v[s])
                for (i = 0; i < 16; i = i + 1)
                    if (wq_mask[16 * s + i]) vm[wq_row[14 * s +: 14]][32 * i +: 32] = wq_d[512 * s + 32 * i +: 32];
        // done contract: the job's rows are all in the VM, with their values, when the core pulses done
        if (`CORE.e_done_v)
            for (k = 0; k < jexp[`CORE.e_done_tag[6:0]][31:0]; k = k + 1)
                if (vm[ea[jexp[`CORE.e_done_tag[6:0]][63:32] + k]] !== ed[jexp[`CORE.e_done_tag[6:0]][63:32] + k]) begin
                    if (early < 5) $display("early done op=%0d row %0d", `CORE.e_done_tag[6:0],
                                            ea[jexp[`CORE.e_done_tag[6:0]][63:32] + k]);
                    early = early + 1;
                end
        // reads: fixed latency LVM
        for (i = 63; i > 0; i = i - 1) begin dl_v[i] = dl_v[i - 1]; dl_a[i] = dl_a[i - 1]; end
        dl_v[0] = rq_v; dl_a[0] = rq_row;
        rs_v <= dl_v[LVM - 1];
        for (s = 0; s < S_RD; s = s + 1) rs_d[512 * s +: 512] <= vm[dl_a[LVM - 1][14 * s +: 14]];
        // y: offered back to back in POST order
    end
    initial for (i = 0; i < 64; i = i + 1) begin dl_v[i] = 0; dl_a[i] = 0; end

    initial begin
        t = 0;
        wait (srs);
        while (t < TMAX && !(ndone >= nj && nj > 0) && !flt) begin @(posedge sk); t = t + 1; end
        repeat (200) @(posedge sk);
        errs = 0;
        fd = $fopen("got.mem", "w");
        for (i = 0; i < ne; i = i + 1) $fdisplay(fd, "%h", vm[ea[i]]);
        $fclose(fd);
        for (i = 0; i < ne; i = i + 1)
            if (vm[ea[i]] !== ed[i]) begin
                if (errs < 5) $display("mismatch row %0d got %h want %h", ea[i], vm[ea[i]][63:0], ed[i][63:0]);
                errs = errs + 1;
            end
        for (i = 0; i < nj; i = i + 1)
            $display("SUJ op=%0d kind=%0d start=%0d done=%0d", i, prog[i][30:27], jstart[i], jdone[i]);
        $display("SUC qn %0d/%0d kv %0d/%0d qb %0d/%0d sw %0d/%0d sm s %0d e %0d pv %0d o %0d beats %0d ph %0d rr %0d nrow %0d cw %0d nw %0d",
                 n_qn, n_qnq, n_kv, n_kvq, n_qb, n_qbo, n_sw, n_swo, n_ss, n_se, n_sp, n_so, n_beat, `CORE.ph,
                 `CORE.rr, `CORE.nrow, `CORE.cw, `CORE.nw);
        $display("SUG jobs=%0d done=%0d err=%0d rows=%0d fault=%0d code=%0d cyc=%0d bad_tag=%0d early=%0d", nj, ndone, errs, ne,
                 flt, fcode, scyc, bad_tag, early);
        if (errs == 0 && ndone == nj && !flt && bad_tag == 0 && early == 0 && pend == 0) $display("SUG PASS"); else $display("SUG FAIL");
        $finish;
    end
endmodule
