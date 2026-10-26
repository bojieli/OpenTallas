`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// tb_mtp_wave die harnesses (el1011-ds-mtp wave bench, 2026-10-11).  Every MTP / WFC block is the closed element RTL;
// the stage compute is a cycle-accurate stub at the measured busy time with exact content checks.
//
// wv_stg  S81 stage die as bound for the WFC verify wave:
//   link faces   dsfd_wfc_crp (OSKID 1: the routed credit-boundary tile) <-> the die's credit link pins
//   WFC          dsfd_wfc_stg (ot_dsrom_wfc_tokpipe_stg + dsfd_wfc_lnk + dsfd_wfc_vmx) at the priced VM configuration:
//                VM_LINK 1, POSTED 1, RD2 1, VMRQ 64, WOUTW 8 (results/rtl/dsrom_wfc_integration_20261010/vm_station.json
//                rd2_vmnat = the 29.03-cycle VM hub-station term of the price)
//   VM           13 / 13 registered hub stations -> dsfd_vm_wfc_ep (RD2, PIPE 2, RL 6) -> VM port model (ops at the pins
//                in order, fixed-latency reads); the endpoint's START doorbell -> 1 station -> dsfd_stage_seq
//   stage seq    dsfd_stage_seq (main decision A) with the kit bench's 3-op program (eng1 3 cycles, eng0 = the stage
//                core, eng2 5 cycles): the 18.5-cycle stage-sequencer term of the price
//   core stub    at its engine command: every received word in the VM must equal wv_word(D, p, t, w) (41 words);
//                after T_BUSY slow cycles writes the 46 outbound words wv_word(100 + D, p, t, w), engine done
//   hrow (HP>=0) the die is layer 37 / 38 / 39's (part HP): at every stage START the issue epoch (the kit's dsfd_wfc_hep on the
//                endpoint START: under POSTED the kit's own t_ks never pulses, so the kit's t_hep is dead) and the
//                main-hidden row {header, 80 beats wv_beat(HP, p, t, b)} leave through ot_dsrom_mtp_hrow_tx
// wv_s0   S0 (SOURCE) die: dsfd_wfc_src TOKIN (token returns from the collective MTP lane far end) + the same VM
//         endpoint; link out through a dsfd_wfc_crp tile (link-out faces); S0 core stub writes wv_word(1, p, t, w).
// Event logs (fast-cycle stamps, wv_fc): per job the core-op command (js_t), the core done (jd_t), position / token.
// ---------------------------------------------------------------------------------------------------------------
module wv_relay #(parameter integer W = 1, parameter integer N = 0) (input wire clk, rst_n, input wire [W-1:0] d,
    output wire [W-1:0] q);
    generate if (N == 0) begin : g0
        assign q = d;
    end else begin : gp
        reg [W-1:0] s [0:N-1]; integer i;
        always @(posedge clk)
            if (!rst_n) for (i = 0; i < N; i = i + 1) s[i] <= {W{1'b0}};
            else begin s[0] <= d; for (i = 1; i < N; i = i + 1) s[i] <= s[i-1]; end
        assign q = s[N-1];
    end endgenerate
endmodule

// VM side of one die: 13 / 13 hub stations, dsfd_vm_wfc_ep (RD2), VM port model; vmem is read / written by the core stub
module wv_vm #(parameter integer VF = 13, parameter integer VR = 13, parameter integer KS = 1, parameter integer RL = 6) (
    input  wire sclk, rst_n,
    input  wire k_swv, input wire [526:0] k_swd, output wire k_swg, output wire k_err,
    input  wire k_srv, input wire [30:0] k_srd, output wire k_srg, output wire [1025:0] k_srq,
    output wire [52:0] ks
);
    localparam integer FLIT = 512, VWA = 15;
    wire r_swv, r_swg, r_srv, r_srg, e_err; wire [526:0] r_swd; wire [30:0] r_srd; wire [1025:0] e_srq; wire [52:0] e_ks;
    wv_relay #(.W(528), .N(VF)) y_swf (.clk(sclk), .rst_n(rst_n), .d({k_swv, k_swd}), .q({r_swv, r_swd}));
    wv_relay #(.W(1), .N(VR)) y_swr (.clk(sclk), .rst_n(rst_n), .d(r_swg), .q(k_swg));
    wv_relay #(.W(32), .N(VF)) y_srf (.clk(sclk), .rst_n(rst_n), .d({k_srv, k_srd}), .q({r_srv, r_srd}));
    wv_relay #(.W(1), .N(VR)) y_srr (.clk(sclk), .rst_n(rst_n), .d(r_srg), .q(k_srg));
    wv_relay #(.W(1), .N(VR)) y_err (.clk(sclk), .rst_n(rst_n), .d(e_err), .q(k_err));
    wv_relay #(.W(1026), .N(VR)) y_srq (.clk(sclk), .rst_n(rst_n), .d(e_srq), .q(k_srq));
    wv_relay #(.W(53), .N(KS)) y_ks (.clk(sclk), .rst_n(rst_n), .d(e_ks), .q(ks));
    wire e_mv, e_mwe, e_m1v; wire [VWA-1:0] e_mrow, e_m1row; wire [FLIT-1:0] e_md;
    reg e_mov = 0, e_m1ov = 0; reg [FLIT-1:0] e_mod = 0, e_m1od = 0;
    dsfd_vm_wfc_ep #(.VF(VF), .VR(VR), .RL(RL), .RD2(1)) u_ep (.ck(sclk), .rst(rst_n), .f_swv(r_swv), .f_swd(r_swd),
        .t_swg(r_swg), .f_srv(r_srv), .f_srd(r_srd), .t_srg(r_srg), .t_srq(e_srq), .t_err(e_err), .t_ks(e_ks),
        .m_v(e_mv), .m_we(e_mwe), .m_row(e_mrow), .m_d(e_md), .m_ov(e_mov), .m_od(e_mod), .m_fault(1'b0),
        .m1_v(e_m1v), .m1_row(e_m1row), .m1_ov(e_m1ov), .m1_od(e_m1od));
    reg [FLIT-1:0] vmem [0:63];
    reg [RL-1:0] e_rv = 0, e_rv1 = 0; reg [VWA-1:0] e_rr [0:RL-1]; reg [VWA-1:0] e_rr1 [0:RL-1]; integer e_i;
    always @(posedge sclk) begin
        if (e_mv === 1'b1 && e_mwe === 1'b1) begin
            if (e_mrow >= 64) begin $display("WAVE FAIL: VM write address %0d", e_mrow); $finish; end
            vmem[e_mrow] = e_md;
        end
        e_rv <= rst_n ? {e_rv[RL-2:0], e_mv === 1'b1 && e_mwe === 1'b0} : '0; e_rr[0] <= e_mrow;
        for (e_i = 1; e_i < RL; e_i = e_i + 1) e_rr[e_i] <= e_rr[e_i-1];
        e_mov <= rst_n && e_rv[RL-1]; e_mod <= vmem[e_rr[RL-1] % 64];
        e_rv1 <= rst_n ? {e_rv1[RL-2:0], e_m1v === 1'b1} : '0; e_rr1[0] <= e_m1row;
        for (e_i = 1; e_i < RL; e_i = e_i + 1) e_rr1[e_i] <= e_rr1[e_i-1];
        e_m1ov <= rst_n && e_rv1[RL-1]; e_m1od <= vmem[e_rr1[RL-1] % 64];
    end
endmodule

module wv_stg #(parameter integer D = 1, parameter integer HP = -1, parameter integer T_BUSY = 300) (
    input  wire fclk, sclk, rst_n,
    input  wire f_liv, input wire [512:0] f_lid, output wire t_lic,
    output wire t_lov, output wire [512:0] t_lod, input wire f_loc,
    output wire h_lv, output wire [513:0] h_ld, input wire h_lg,      // main-hidden row part (grant protocol)
    output wire fault
);
    `include "tb_mtp_wave_fn.svh"
    localparam integer FLIT = 512, NW = 21, USER_W = 10, VWA = 15, RXW = 41, TXW = 46;
    // ---- credit link faces
    wire liv, lir, lov, lor, krst, krsv, crp_ft; wire [512:0] lid, lod;
    dsfd_wfc_crp #(.OSKID(1)) u_crp (.ck(fclk), .ckv(sclk), .rst(rst_n), .rsv(rst_n),
        .f_liv(f_liv), .f_lid(f_lid), .t_lic(t_lic), .t_lov(t_lov), .t_lod(t_lod), .f_loc(f_loc),
        .t_swv(), .t_swd(), .f_swc(1'b0), .f_swa(1'b0), .t_srv(), .t_srd(), .f_src(1'b0),
        .t_kliv(liv), .t_klid(lid), .f_klir(lir), .f_klov(lov), .f_klod(lod), .t_klor(lor),
        .f_kswv(1'b0), .f_kswd(527'd0), .t_kswr(), .t_kswa(), .f_ksrv(1'b0), .f_ksrd(15'd0), .t_ksrr(),
        .t_krst(krst), .t_krsv(krsv), .t_ft(crp_ft));
    // ---- the WFC kit (STAGE)
    wire k_swv, k_swg, k_err, k_srv, k_srg; wire [526:0] k_swd; wire [30:0] k_srd; wire [1025:0] k_srq;
    wire [52:0] k_ks_unused, ks; wire [53:0] s_kd; wire [3:0] k_ft;
    wire [35:0] k_hep;
    dsfd_wfc_stg #(.VM_LINK(1), .VMRQ(64), .WOUTW(8), .POSTED(1), .RD2(1), .HEP(HP >= 0)) u_kit (.ck(fclk), .ckv(sclk), .rst(krst), .rsv(krsv),
        .f_liv(liv), .f_lid(lid), .t_lir(lir), .t_lov(lov), .t_lod(lod), .f_lor(lor),
        .t_swv(k_swv), .t_swd(k_swd), .f_swr(k_swg), .f_swa(k_err), .t_srv(k_srv), .t_srd(k_srd), .f_srr(k_srg),
        .f_srq(k_srq), .t_ks(k_ks_unused), .f_kd(s_kd), .t_hep(k_hep), .t_ft(k_ft));
    wv_vm u_vm (.sclk(sclk), .rst_n(rst_n), .k_swv(k_swv), .k_swd(k_swd), .k_swg(k_swg), .k_err(k_err),
        .k_srv(k_srv), .k_srd(k_srd), .k_srg(k_srg), .k_srq(k_srq), .ks(ks));
    // ---- stage sequencer + engines (port 0 = the stage core stub, ports 1 / 2 fixed-latency responders)
    localparam integer S_NENG = 3, S_OPW = 7, S_PEW = 28, S_CMDW = 1 + USER_W + 2*NW + 24 + 7, S_TAGW = 8;
    wire [S_NENG-1:0] s_cv; wire [S_NENG*S_CMDW-1:0] s_cd; wire [5:0] s_st;
    reg [S_NENG-1:0] s_dv = 0; reg [S_NENG*S_TAGW-1:0] s_dt = 0; reg [S_OPW+S_PEW:0] s_pw = 0; reg [S_OPW:0] s_plen = 0;
    dsfd_stage_seq #(.NOPS(128), .NENG(S_NENG)) u_sseq (.ckv(sclk), .rsv(rst_n), .f_ks(ks), .t_kd(s_kd), .f_pw(s_pw),
        .f_plen(s_plen), .t_cmdv(s_cv), .t_cmdd(s_cd), .f_dnv(s_dv), .f_dntag(s_dt), .t_st(s_st));
    integer scyc = 0, s_pi = 0, s_l1 = -1, s_l2 = -1, core_t = -1, cp, ct, k;
    reg [S_TAGW-1:0] s_t0, s_t1, s_t2;
    // job log
    integer n_job = 0, n_done = 0; integer js_t [0:4095]; integer jd_t [0:4095]; integer jpos [0:4095]; integer jtok [0:4095];
    reg bad = 0;
    always @(posedge sclk) begin
        scyc <= scyc + 1;
        s_pw <= 0; s_dv <= 0;
        if (rst_n && scyc > 20 && s_pi < 3) begin
            s_pw <= {1'b1, 7'(s_pi), 4'(s_pi == 0 ? 1 : s_pi == 1 ? 0 : 2), 24'(s_pi)}; s_pi = s_pi + 1;
            if (s_pi == 3) s_plen <= 8'd3;
        end
        if (s_cv[0]) begin
            if (core_t >= 0) begin $display("WAVE FAIL: die %0d core command while busy", D); bad <= 1; end
            s_t0 = {s_cd[S_CMDW-1], s_cd[S_OPW-1:0]};
            ct = s_cd[S_CMDW-2-USER_W-NW -: NW]; cp = s_cd[S_CMDW-2-USER_W -: NW];
            for (k = 0; k < RXW; k = k + 1)
                if (u_vm.vmem[k] !== wv_word(D, cp, ct, k)) begin
                    $display("WAVE FAIL: die %0d RX word %0d of (p%0d, t%0d) not in the VM at the core command", D, k, cp, ct);
                    bad <= 1;
                end
            js_t[n_job % 4096] = wv_fc(0); jpos[n_job % 4096] = cp; jtok[n_job % 4096] = ct; n_job = n_job + 1;
            core_t = scyc + T_BUSY;
        end else if (core_t >= 0 && scyc >= core_t) begin
            for (k = 0; k < TXW; k = k + 1) u_vm.vmem[k] = wv_word(100 + D, cp, ct, k);
            s_dv[0] <= 1'b1; s_dt[0 +: S_TAGW] <= s_t0;
            jd_t[n_done % 4096] = wv_fc(0); n_done = n_done + 1;
            core_t = -1;
        end
        if (s_cv[1]) begin s_t1 = {s_cd[S_CMDW + S_CMDW-1], s_cd[S_CMDW +: S_OPW]}; s_l1 = 3; end
        if (s_cv[2]) begin s_t2 = {s_cd[2*S_CMDW + S_CMDW-1], s_cd[2*S_CMDW +: S_OPW]}; s_l2 = 5; end
        if (s_l1 == 0) begin s_dv[1] <= 1'b1; s_dt[S_TAGW +: S_TAGW] <= s_t1; end
        if (s_l2 == 0) begin s_dv[2] <= 1'b1; s_dt[2*S_TAGW +: S_TAGW] <= s_t2; end
        if (s_l1 >= 0) s_l1 = s_l1 - 1;
        if (s_l2 >= 0) s_l2 = s_l2 - 1;
    end
    // ---- main-hidden row part (layers 37 / 38 / 39): issue epoch of every START + the row through ot_dsrom_mtp_hrow_tx
    generate if (HP >= 0) begin : g_hrow
        wire [35:0] hep;
        assign hep = k_hep;   // the kit's own issue epochs (posted START doorbell; el1011-ds-mtp fix cfe25038d)
        integer hq_u [0:255], hq_p [0:255], hq_e [0:255]; integer hq_w = 0, hq_r = 0;
        // the row model needs the stage's token, which only the VM endpoint START (ks) carries; the kit's HEP fires at
        // the doorbell issue, earlier. Starts are 1:1 and in order, so START i's token belongs to HEP i; a row is sent
        // only once its START has reached the VM (the row exists there: the stub's stand-in for the VM row-completion wait)
        integer kq_t [0:255]; integer kq_w = 0;
        always @(posedge sclk) begin
            if (ks[52]) begin kq_t[kq_w % 256] = ks[NW +: NW]; kq_w = kq_w + 1; end
            if (hep[35]) begin
                hq_u[hq_w % 256] = hep[4 + NW +: USER_W]; hq_p[hq_w % 256] = hep[4 +: NW]; hq_e[hq_w % 256] = hep[3:0];
                hq_w = hq_w + 1;
            end
        end
        reg hv = 0, bv = 0; wire hr, br; reg [36:0] hd = 0; reg [1023:0] bd = 0; integer nb = 0, cur = -1;
        ot_dsrom_mtp_hrow_tx #(.NW(NW), .USER_W(USER_W)) u_tx (.clk(fclk), .rst_n(rst_n), .h_v(hv), .h_r(hr), .h_d(hd),
            .b_v(bv), .b_r(br), .b_d(bd), .l_valid(h_lv), .l_ready(h_lg), .l_data(h_ld));
        integer rows_sent = 0;
        integer tx_t [0:4095];
        always @(posedge fclk) if (rst_n) begin
            if (hv && hr) begin hv <= 1'b0; bv <= 1'b1; nb = 0; bd <= wv_beat(HP, hq_p[cur % 256], kq_t[cur % 256], 0); end
            else if (bv && br) begin
                nb = nb + 1;
                if (nb == 80) begin bv <= 1'b0; cur = -1; rows_sent = rows_sent + 1; hq_r = hq_r + 1; end
                else bd <= wv_beat(HP, hq_p[cur % 256], kq_t[cur % 256], nb);
            end
            if (cur < 0 && !hv && !bv && hq_r < hq_w && hq_r < kq_w) begin
                cur = hq_r;
                hd <= {USER_W'(hq_u[cur % 256]), NW'(hq_p[cur % 256]), 4'(hq_e[cur % 256]), 2'(HP)}; hv <= 1'b1;
                tx_t[rows_sent % 4096] = wv_fc(0);
            end
        end
    end else begin : g_nohrow
        assign h_lv = 1'b0; assign h_ld = '0;
    end endgenerate
    assign fault = bad | (|k_ft) | crp_ft | s_st[5];
endmodule

module wv_s0 #(parameter integer T_BUSY = 300) (
    input  wire fclk, sclk, rst_n,
    input  wire [54:0] f_c, output wire [52:0] t_tok,
    input  wire [512:0] f_mrt, output wire t_mrg,                    // TOKIN: the MTP lane far end {data, valid} / grant
    output wire t_lov, output wire [512:0] t_lod, input wire f_loc,
    output wire fault
);
    `include "tb_mtp_wave_fn.svh"
    localparam integer FLIT = 512, NW = 21, USER_W = 10, XW = 41;
    wire lov, lor, krst, krsv, crp_ft; wire [512:0] lod;
    dsfd_wfc_crp #(.OSKID(1)) u_crp (.ck(fclk), .ckv(sclk), .rst(rst_n), .rsv(rst_n),
        .f_liv(1'b0), .f_lid(513'd0), .t_lic(), .t_lov(t_lov), .t_lod(t_lod), .f_loc(f_loc),
        .t_swv(), .t_swd(), .f_swc(1'b0), .f_swa(1'b0), .t_srv(), .t_srd(), .f_src(1'b0),
        .t_kliv(), .t_klid(), .f_klir(1'b0), .f_klov(lov), .f_klod(lod), .t_klor(lor),
        .f_kswv(1'b0), .f_kswd(527'd0), .t_kswr(), .t_kswa(), .f_ksrv(1'b0), .f_ksrd(15'd0), .t_ksrr(),
        .t_krst(krst), .t_krsv(krsv), .t_ft(crp_ft));
    wire k_swv, k_swg, k_err, k_srv, k_srg; wire [526:0] k_swd; wire [30:0] k_srd; wire [1025:0] k_srq;
    wire [52:0] k_ks_unused, ks; reg [53:0] kd = 0; wire [3:0] k_ft;
    dsfd_wfc_src #(.TOKIN(1), .VM_LINK(1), .VMRQ(64), .WOUTW(8), .POSTED(1), .RD2(1)) u_kit (.ck(fclk), .ckv(sclk),
        .rst(krst), .rsv(krsv),
        .f_liv(1'b0), .f_lid(513'd0), .t_lir(), .t_lov(lov), .t_lod(lod), .f_lor(lor),
        .t_swv(k_swv), .t_swd(k_swd), .f_swr(k_swg), .f_swa(k_err), .t_srv(k_srv), .t_srd(k_srd), .f_srr(k_srg),
        .f_srq(k_srq), .t_ks(k_ks_unused), .f_kd(kd), .t_hep(), .f_c(f_c), .f_mrt(f_mrt), .t_mrg(t_mrg),
        .t_tok(t_tok), .t_cfg(), .t_ft(k_ft));
    wv_vm u_vm (.sclk(sclk), .rst_n(rst_n), .k_swv(k_swv), .k_swd(k_swd), .k_swg(k_swg), .k_err(k_err),
        .k_srv(k_srv), .k_srd(k_srd), .k_srg(k_srg), .k_srq(k_srq), .ks(ks));
    integer scyc = 0, core_t = -1, cp, ct, k, n_job = 0;
    integer js_t [0:4095]; integer jpos [0:4095]; integer jtok [0:4095];
    reg bad = 0;
    always @(posedge sclk) begin
        scyc <= scyc + 1;
        kd[53] <= 1'b0;
        if (ks[52]) begin
            if (core_t >= 0) begin $display("WAVE FAIL: S0 start while the core is busy"); bad <= 1; end
            ct = ks[NW +: NW]; cp = ks[NW-1:0]; core_t = scyc + T_BUSY;
            js_t[n_job % 4096] = wv_fc(0); jpos[n_job % 4096] = cp; jtok[n_job % 4096] = ct; n_job = n_job + 1;
        end else if (core_t >= 0 && scyc >= core_t) begin
            for (k = 0; k < XW; k = k + 1) u_vm.vmem[k] = wv_word(1, cp, ct, k);
            kd <= {1'b1, NW'(ct ^ 21'h155), 32'h3f800000 ^ cp};
            core_t = -1;
        end
    end
    // wfc_tok.edges: every prompt-port read pr_re -> the HARD store's registered response (valid_pipe[2] + 1 edge)
    integer pr_n = 0, pr_sum = 0, pr_t = -1;
    always @(posedge fclk) if (rst_n) begin
        if (u_kit.pr_re) pr_t = wv_fc(0);
        if (u_kit.u_tok.tok.hard_read.valid_pipe[2] && pr_t >= 0) begin pr_sum = pr_sum + (wv_fc(0) + 1 - pr_t); pr_n = pr_n + 1; pr_t = -1; end
    end
    assign fault = bad | (|k_ft) | crp_ft;
endmodule
