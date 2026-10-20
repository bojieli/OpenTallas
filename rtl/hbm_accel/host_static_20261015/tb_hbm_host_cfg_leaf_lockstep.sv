`timescale 1ns/1ps
`default_nettype none
// HBM-B-RTL1 2026-10-17: lockstep of the d4g host configuration path against d4f.
//   REF (d4f): host AXI -> ot_hbm_host_static_ingress -> 20 targets directly -> ot_hbm_status_join_fa (GUARD G).
//   DUT (d4g): same host AXI -> ingress -> 4 x ot_hbm_host_cfg_leaf (NCP 2) -> the same 20 targets -> leaf status
//              -> join (GUARD G + CFG_LAT + ST_LAT).
// Targets (tb_cfg_tgt): deterministic, pin-registered, re-validate after every config row / descriptor (ready low
// INST edges), run LEN edges at launch, sticky fault on a poisoned address or a launch reaching a not-ready target.
// Checks, every edge:
//   C1 ingress outputs + AXI responses identical REF/DUT (the host program is unchanged, launches accepted on the same edge)
//   C2 every target input bundle (all 317 payload + 3 valid bits) of DUT at t == REF at t - CFG_LAT
//   C3 the join's t_ready/t_active/t_fault of DUT at t == REF at t - (CFG_LAT + ST_LAT)
//   C4 program_active / program_fault and the irq RISING edge of DUT at t == REF at t - (CFG_LAT + ST_LAT)
//      (irq clears at the next launch_v, which the join sees on the same edge in both: the irq pulse is RT edges shorter)
//   C5 no target ever sees a launch while armed and not ready (both paths; fault[1] stays 0 until the poison round)
// MUT: passed to every leaf, or only to leaf MUTQ (1 dropped bit, 2 copy one stage short, 3 ready swap, 4 fault drop).
// D4G 0: 4 x ot_hbm_host_cfg_leaf2 NT5/NF10 (fault bit 2j+b = target j fault[b]).
// D4G 2 (HBM-RTL5 10-18): SE / NE = the re-hardened ot_hbm_host_cfg_leaf_{se,ne}2 at NT21/NF30 and NT17/NF27 (SW / NW
//   unchanged): 75 targets / 115 fault bits = the d4g GEN1 host_status widths with the six new E targets through the
//   leaves.  PLAST 1: the poison round poisons the LAST target of the quadrant (its fault[0] = leaf t_fault bit NT-1, a
//   new slot in SE / NE; the ingress refuses writes after the first program fault, so one poison per run), so a dropped
//   new fault bit (MUT 7) is observed.  MUT 5 / 6 invert the top s_ready / s_fault bit.
// D4G 1 (HBM-B-RTL1b): the d4g per-quadrant masters ot_hbm_host_cfg_leaf_{sw,se,nw,ne} at their exact NT/NF
//   (18/29, 18/26, 19/29, 14/23): NT bench targets per leaf (one per ready/active bit); leaf fault bit j < NT = target
//   j fault[0], j >= NT = target j-NT fault[1] (NF < 2 NT in every quadrant), so every leaf input is driven.
module tb_hbm_host_cfg_leaf_lockstep;
    parameter integer MUT = 0;
    parameter integer ROUNDS = 40;
    parameter integer SEED = 7;
    parameter integer D4G = 0;
    parameter integer MUTQ = -1;
    parameter integer PLAST = 0;
    localparam integer NQ = 4;
    function integer ntq(input integer q); ntq = D4G == 2 ? (q == 0 ? 18 : q == 1 ? 21 : q == 2 ? 19 : 17)
                                                : D4G ? (q == 0 ? 18 : q == 1 ? 18 : q == 2 ? 19 : 14) : 5; endfunction
    function integer nfq(input integer q); nfq = D4G == 2 ? (q == 0 ? 29 : q == 1 ? 30 : q == 2 ? 29 : 27)
                                                : D4G ? (q == 0 ? 29 : q == 1 ? 26 : q == 2 ? 29 : 23) : 10; endfunction
    function integer toff(input integer q); integer i; begin toff = 0; for (i = 0; i < q; i = i + 1) toff = toff + ntq(i); end endfunction
    function integer foff(input integer q); integer i; begin foff = 0; for (i = 0; i < q; i = i + 1) foff = foff + nfq(i); end endfunction
    localparam integer NTG = toff(NQ), NF = foff(NQ);
    localparam integer CFG_LAT = 2, ST_LAT = 2, RT = CFG_LAT + ST_LAT, G = 8;
    function [NTG*8-1:0] mk_tgts(input integer dummy); integer i; begin
        for (i = 0; i < NTG; i = i + 1) mk_tgts[i*8 +: 8] = 16 + i; end endfunction
    localparam [NTG*8-1:0] TGTS = mk_tgts(0);
    localparam [255:0] TMASK = (((256'd1 << NTG) - 1) << 16) | (256'd1 << 125);
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // ---------------- host AXI master (one stimulus, both ingresses)
    reg awvalid = 0, wvalid = 0, bready = 0, arvalid = 0, rready = 0;
    reg [11:0] awaddr = 0, araddr = 0; reg [31:0] wdata = 0; reg [3:0] wstrb = 4'hf;
    wire r_awready, r_wready, r_bvalid, r_arready, r_rvalid; wire [1:0] r_bresp; wire [31:0] r_rdata;
    wire d_awready, d_wready, d_bvalid, d_arready, d_rvalid; wire [1:0] d_bresp; wire [31:0] d_rdata;
    // ingress outputs
    wire r_cv, r_dv, r_lv, r_fault, d_cv, d_dv, d_lv, d_fault;
    wire [7:0] r_ct, d_ct; wire [11:0] r_ca, d_ca, r_db, d_db; wire [255:0] r_cd, d_cd;
    wire [12:0] r_dl, d_dl; wire [15:0] r_dp, d_dp;
    wire r_br, r_pa, r_pf, r_irq, r_df, d_br, d_pa, d_pf, d_irq, d_df;
    wire [0:0] r_ac, d_ac;

    ot_hbm_host_static_ingress #(.TARGET_MASK(TMASK)) ing_r (.clk(clk), .rst_n(rst_n),
        .s_awvalid(awvalid), .s_awready(r_awready), .s_awaddr(awaddr), .s_wvalid(wvalid), .s_wready(r_wready),
        .s_wdata(wdata), .s_wstrb(wstrb), .s_bvalid(r_bvalid), .s_bready(bready), .s_bresp(r_bresp),
        .s_arvalid(arvalid), .s_arready(r_arready), .s_araddr(araddr), .s_rvalid(r_rvalid), .s_rready(rready),
        .s_rdata(r_rdata), .block_ready(r_br), .program_active(r_pa), .program_fault(r_pf),
        .cfg_v(r_cv), .cfg_target(r_ct), .cfg_addr(r_ca), .cfg_data(r_cd), .desc_v(r_dv), .desc_base(r_db),
        .desc_limit(r_dl), .desc_loops(r_dp), .launch_v(r_lv), .fault(r_fault));
    ot_hbm_host_static_ingress #(.TARGET_MASK(TMASK)) ing_d (.clk(clk), .rst_n(rst_n),
        .s_awvalid(awvalid), .s_awready(d_awready), .s_awaddr(awaddr), .s_wvalid(wvalid), .s_wready(d_wready),
        .s_wdata(wdata), .s_wstrb(wstrb), .s_bvalid(d_bvalid), .s_bready(bready), .s_bresp(d_bresp),
        .s_arvalid(arvalid), .s_arready(d_arready), .s_araddr(araddr), .s_rvalid(d_rvalid), .s_rready(rready),
        .s_rdata(d_rdata), .block_ready(d_br), .program_active(d_pa), .program_fault(d_pf),
        .cfg_v(d_cv), .cfg_target(d_ct), .cfg_addr(d_ca), .cfg_data(d_cd), .desc_v(d_dv), .desc_base(d_db),
        .desc_limit(d_dl), .desc_loops(d_dp), .launch_v(d_lv), .fault(d_fault));

    // ---------------- REF: targets straight off the ingress
    wire [NTG-1:0] r_rdy, r_act; wire [NF-1:0] r_flt; wire [2*NTG-1:0] r_tf;
    wire [NTG-1:0] d_rdy, d_act, j_rdy, j_act; wire [NF-1:0] d_flt, j_flt; wire [2*NTG-1:0] d_tf;
    wire [NTG*320-1:0] r_tin;   // per-target input bundle {lv,dv,cv,payload317} as seen at the target pins
    genvar k;
    generate for (k = 0; k < NTG; k = k + 1) begin : g_rt
        assign r_tin[k*320 +: 320] = {r_lv, r_dv, r_cv, r_dp, r_dl, r_db, r_cd, r_ca, r_ct};
        tb_cfg_tgt #(.ID(16 + k)) t (.clk(clk), .rst_n(rst_n), .cfg_v(r_cv), .cfg_target(r_ct), .cfg_addr(r_ca),
            .desc_v(r_dv), .launch_v(r_lv), .ready(r_rdy[k]), .active(r_act[k]), .fault(r_tf[2*k +: 2]));
    end endgenerate
    // per-leaf fault bit order (the same selection on both paths)
    genvar fq, fj;
    generate for (fq = 0; fq < NQ; fq = fq + 1) begin : g_fs
        for (fj = 0; fj < nfq(fq); fj = fj + 1) begin : g_b
            localparam integer TI = toff(fq) + (D4G ? (fj < ntq(fq) ? fj : fj - ntq(fq)) : fj / 2);
            localparam integer FB = D4G ? (fj < ntq(fq) ? 0 : 1) : fj % 2;
            assign r_flt[foff(fq) + fj] = r_tf[2*TI + FB];
            assign d_flt[foff(fq) + fj] = d_tf[2*TI + FB];
        end
    end endgenerate
    ot_hbm_status_join_fa #(.NT(NTG), .NF(NF), .NH(1), .TGTS(TGTS), .GUARD(G), .NA(1), .FCLR(8'd125), .RRELAY(1)) join_r (
        .clk(clk), .rst_n(rst_n), .cfg_v(r_cv), .desc_v(r_dv), .launch_v(r_lv), .cfg_target(r_ct),
        .t_ready(r_rdy), .t_active(r_act), .t_fault(r_flt), .h_fault(r_fault), .a_fault(1'b0),
        .block_ready(r_br), .program_active(r_pa), .program_fault(r_pf), .irq(r_irq), .die_fault(r_df), .a_cause(r_ac));

    // ---------------- DUT: 4 leaves, NCP 2 (targets 0-2 of a quadrant on copy 0, 3-4 on copy 1)
    wire [NTG*320-1:0] d_tin;
    genvar q, j;
    generate for (q = 0; q < NQ; q = q + 1) begin : g_q
        localparam integer NTQ = ntq(q), NFQ = nfq(q), TO = toff(q), FO = foff(q);
        localparam integer LM = (MUTQ < 0 || MUTQ == q) ? MUT : 0;
        wire [1:0] ocv, odv, olv; wire [15:0] oct; wire [23:0] oca, odb; wire [511:0] ocd; wire [25:0] odl; wire [31:0] odp;
        // the hardened master: copy A = ocv[0].., copy B = ocv[1]..
        if (D4G == 0) begin : g_l2
        ot_hbm_host_cfg_leaf2 #(.NT(NTQ), .NF(NFQ), .MUT(LM)) leaf (.clk(clk), .rst_n(rst_n),
            .cfg_v(d_cv), .cfg_target(d_ct), .cfg_addr(d_ca), .cfg_data(d_cd), .desc_v(d_dv), .desc_base(d_db),
            .desc_limit(d_dl), .desc_loops(d_dp), .launch_v(d_lv),
            .a_cfg_v(ocv[0]), .a_cfg_target(oct[7:0]), .a_cfg_addr(oca[11:0]), .a_cfg_data(ocd[255:0]), .a_desc_v(odv[0]),
            .a_desc_base(odb[11:0]), .a_desc_limit(odl[12:0]), .a_desc_loops(odp[15:0]), .a_launch_v(olv[0]),
            .b_cfg_v(ocv[1]), .b_cfg_target(oct[15:8]), .b_cfg_addr(oca[23:12]), .b_cfg_data(ocd[511:256]), .b_desc_v(odv[1]),
            .b_desc_base(odb[23:12]), .b_desc_limit(odl[25:13]), .b_desc_loops(odp[31:16]), .b_launch_v(olv[1]),
            .t_ready(d_rdy[TO +: NTQ]), .t_active(d_act[TO +: NTQ]), .t_fault(d_flt[FO +: NFQ]),
            .s_ready(j_rdy[TO +: NTQ]), .s_active(j_act[TO +: NTQ]), .s_fault(j_flt[FO +: NFQ]));
        end else if (q == 0) begin : g_sw
        ot_hbm_host_cfg_leaf_sw #(.MUT(LM)) leaf (.clk(clk), .rst_n(rst_n),
            .cfg_v(d_cv), .cfg_target(d_ct), .cfg_addr(d_ca), .cfg_data(d_cd), .desc_v(d_dv), .desc_base(d_db),
            .desc_limit(d_dl), .desc_loops(d_dp), .launch_v(d_lv),
            .a_cfg_v(ocv[0]), .a_cfg_target(oct[7:0]), .a_cfg_addr(oca[11:0]), .a_cfg_data(ocd[255:0]), .a_desc_v(odv[0]),
            .a_desc_base(odb[11:0]), .a_desc_limit(odl[12:0]), .a_desc_loops(odp[15:0]), .a_launch_v(olv[0]),
            .b_cfg_v(ocv[1]), .b_cfg_target(oct[15:8]), .b_cfg_addr(oca[23:12]), .b_cfg_data(ocd[511:256]), .b_desc_v(odv[1]),
            .b_desc_base(odb[23:12]), .b_desc_limit(odl[25:13]), .b_desc_loops(odp[31:16]), .b_launch_v(olv[1]),
            .t_ready(d_rdy[TO +: NTQ]), .t_active(d_act[TO +: NTQ]), .t_fault(d_flt[FO +: NFQ]),
            .s_ready(j_rdy[TO +: NTQ]), .s_active(j_act[TO +: NTQ]), .s_fault(j_flt[FO +: NFQ]));
        end else if (q == 1 && D4G == 2) begin : g_se2
        ot_hbm_host_cfg_leaf_se2 #(.MUT(LM)) leaf (.clk(clk), .rst_n(rst_n),
            .cfg_v(d_cv), .cfg_target(d_ct), .cfg_addr(d_ca), .cfg_data(d_cd), .desc_v(d_dv), .desc_base(d_db),
            .desc_limit(d_dl), .desc_loops(d_dp), .launch_v(d_lv),
            .a_cfg_v(ocv[0]), .a_cfg_target(oct[7:0]), .a_cfg_addr(oca[11:0]), .a_cfg_data(ocd[255:0]), .a_desc_v(odv[0]),
            .a_desc_base(odb[11:0]), .a_desc_limit(odl[12:0]), .a_desc_loops(odp[15:0]), .a_launch_v(olv[0]),
            .b_cfg_v(ocv[1]), .b_cfg_target(oct[15:8]), .b_cfg_addr(oca[23:12]), .b_cfg_data(ocd[511:256]), .b_desc_v(odv[1]),
            .b_desc_base(odb[23:12]), .b_desc_limit(odl[25:13]), .b_desc_loops(odp[31:16]), .b_launch_v(olv[1]),
            .t_ready(d_rdy[TO +: NTQ]), .t_active(d_act[TO +: NTQ]), .t_fault(d_flt[FO +: NFQ]),
            .s_ready(j_rdy[TO +: NTQ]), .s_active(j_act[TO +: NTQ]), .s_fault(j_flt[FO +: NFQ]));
        end else if (q == 1) begin : g_se
        ot_hbm_host_cfg_leaf_se #(.MUT(LM)) leaf (.clk(clk), .rst_n(rst_n),
            .cfg_v(d_cv), .cfg_target(d_ct), .cfg_addr(d_ca), .cfg_data(d_cd), .desc_v(d_dv), .desc_base(d_db),
            .desc_limit(d_dl), .desc_loops(d_dp), .launch_v(d_lv),
            .a_cfg_v(ocv[0]), .a_cfg_target(oct[7:0]), .a_cfg_addr(oca[11:0]), .a_cfg_data(ocd[255:0]), .a_desc_v(odv[0]),
            .a_desc_base(odb[11:0]), .a_desc_limit(odl[12:0]), .a_desc_loops(odp[15:0]), .a_launch_v(olv[0]),
            .b_cfg_v(ocv[1]), .b_cfg_target(oct[15:8]), .b_cfg_addr(oca[23:12]), .b_cfg_data(ocd[511:256]), .b_desc_v(odv[1]),
            .b_desc_base(odb[23:12]), .b_desc_limit(odl[25:13]), .b_desc_loops(odp[31:16]), .b_launch_v(olv[1]),
            .t_ready(d_rdy[TO +: NTQ]), .t_active(d_act[TO +: NTQ]), .t_fault(d_flt[FO +: NFQ]),
            .s_ready(j_rdy[TO +: NTQ]), .s_active(j_act[TO +: NTQ]), .s_fault(j_flt[FO +: NFQ]));
        end else if (q == 2) begin : g_nw
        ot_hbm_host_cfg_leaf_nw #(.MUT(LM)) leaf (.clk(clk), .rst_n(rst_n),
            .cfg_v(d_cv), .cfg_target(d_ct), .cfg_addr(d_ca), .cfg_data(d_cd), .desc_v(d_dv), .desc_base(d_db),
            .desc_limit(d_dl), .desc_loops(d_dp), .launch_v(d_lv),
            .a_cfg_v(ocv[0]), .a_cfg_target(oct[7:0]), .a_cfg_addr(oca[11:0]), .a_cfg_data(ocd[255:0]), .a_desc_v(odv[0]),
            .a_desc_base(odb[11:0]), .a_desc_limit(odl[12:0]), .a_desc_loops(odp[15:0]), .a_launch_v(olv[0]),
            .b_cfg_v(ocv[1]), .b_cfg_target(oct[15:8]), .b_cfg_addr(oca[23:12]), .b_cfg_data(ocd[511:256]), .b_desc_v(odv[1]),
            .b_desc_base(odb[23:12]), .b_desc_limit(odl[25:13]), .b_desc_loops(odp[31:16]), .b_launch_v(olv[1]),
            .t_ready(d_rdy[TO +: NTQ]), .t_active(d_act[TO +: NTQ]), .t_fault(d_flt[FO +: NFQ]),
            .s_ready(j_rdy[TO +: NTQ]), .s_active(j_act[TO +: NTQ]), .s_fault(j_flt[FO +: NFQ]));
        end else if (q == 3 && D4G == 2) begin : g_ne2
        ot_hbm_host_cfg_leaf_ne2 #(.MUT(LM)) leaf (.clk(clk), .rst_n(rst_n),
            .cfg_v(d_cv), .cfg_target(d_ct), .cfg_addr(d_ca), .cfg_data(d_cd), .desc_v(d_dv), .desc_base(d_db),
            .desc_limit(d_dl), .desc_loops(d_dp), .launch_v(d_lv),
            .a_cfg_v(ocv[0]), .a_cfg_target(oct[7:0]), .a_cfg_addr(oca[11:0]), .a_cfg_data(ocd[255:0]), .a_desc_v(odv[0]),
            .a_desc_base(odb[11:0]), .a_desc_limit(odl[12:0]), .a_desc_loops(odp[15:0]), .a_launch_v(olv[0]),
            .b_cfg_v(ocv[1]), .b_cfg_target(oct[15:8]), .b_cfg_addr(oca[23:12]), .b_cfg_data(ocd[511:256]), .b_desc_v(odv[1]),
            .b_desc_base(odb[23:12]), .b_desc_limit(odl[25:13]), .b_desc_loops(odp[31:16]), .b_launch_v(olv[1]),
            .t_ready(d_rdy[TO +: NTQ]), .t_active(d_act[TO +: NTQ]), .t_fault(d_flt[FO +: NFQ]),
            .s_ready(j_rdy[TO +: NTQ]), .s_active(j_act[TO +: NTQ]), .s_fault(j_flt[FO +: NFQ]));
        end else if (q == 3) begin : g_ne
        ot_hbm_host_cfg_leaf_ne #(.MUT(LM)) leaf (.clk(clk), .rst_n(rst_n),
            .cfg_v(d_cv), .cfg_target(d_ct), .cfg_addr(d_ca), .cfg_data(d_cd), .desc_v(d_dv), .desc_base(d_db),
            .desc_limit(d_dl), .desc_loops(d_dp), .launch_v(d_lv),
            .a_cfg_v(ocv[0]), .a_cfg_target(oct[7:0]), .a_cfg_addr(oca[11:0]), .a_cfg_data(ocd[255:0]), .a_desc_v(odv[0]),
            .a_desc_base(odb[11:0]), .a_desc_limit(odl[12:0]), .a_desc_loops(odp[15:0]), .a_launch_v(olv[0]),
            .b_cfg_v(ocv[1]), .b_cfg_target(oct[15:8]), .b_cfg_addr(oca[23:12]), .b_cfg_data(ocd[511:256]), .b_desc_v(odv[1]),
            .b_desc_base(odb[23:12]), .b_desc_limit(odl[25:13]), .b_desc_loops(odp[31:16]), .b_launch_v(olv[1]),
            .t_ready(d_rdy[TO +: NTQ]), .t_active(d_act[TO +: NTQ]), .t_fault(d_flt[FO +: NFQ]),
            .s_ready(j_rdy[TO +: NTQ]), .s_active(j_act[TO +: NTQ]), .s_fault(j_flt[FO +: NFQ]));
        end
        for (j = 0; j < NTQ; j = j + 1) begin : g_t
            localparam integer C = (j < (NTQ + 1) / 2) ? 0 : 1;
            localparam integer T = TO + j;
            assign d_tin[T*320 +: 320] = {olv[C], odv[C], ocv[C], odp[C*16 +: 16], odl[C*13 +: 13], odb[C*12 +: 12],
                                          ocd[C*256 +: 256], oca[C*12 +: 12], oct[C*8 +: 8]};
            tb_cfg_tgt #(.ID(16 + T)) t (.clk(clk), .rst_n(rst_n), .cfg_v(ocv[C]), .cfg_target(oct[C*8 +: 8]),
                .cfg_addr(oca[C*12 +: 12]), .desc_v(odv[C]), .launch_v(olv[C]),
                .ready(d_rdy[T]), .active(d_act[T]), .fault(d_tf[2*T +: 2]));
        end
    end endgenerate
    ot_hbm_status_join_fa #(.NT(NTG), .NF(NF), .NH(1), .TGTS(TGTS), .GUARD(G + RT), .NA(1), .FCLR(8'd125), .RRELAY(1)) join_d (
        .clk(clk), .rst_n(rst_n), .cfg_v(d_cv), .desc_v(d_dv), .launch_v(d_lv), .cfg_target(d_ct),
        .t_ready(j_rdy), .t_active(j_act), .t_fault(j_flt), .h_fault(d_fault), .a_fault(1'b0),
        .block_ready(d_br), .program_active(d_pa), .program_fault(d_pf), .irq(d_irq), .die_fault(d_df), .a_cause(d_ac));

    // ---------------- history + checks
    reg d_irq_q = 0, r_irq_q = 0;
    localparam integer HD = 8;
    reg [NTG*320-1:0] h_tin [0:HD-1];
    reg [NTG-1:0] h_rdy [0:HD-1], h_act [0:HD-1]; reg [NF-1:0] h_flt [0:HD-1];
    reg [2:0] h_prog [0:HD-1];
    integer i, m1 = 0, m2 = 0, m3 = 0, m4 = 0, m5 = 0, nlaunch_r = 0, nlaunch_d = 0, nirq_r = 0, nirq_d = 0, ncfg = 0, ndesc = 0;
    reg poison = 0;
    always @(posedge clk) begin
        for (i = HD - 1; i > 0; i = i - 1) begin
            h_tin[i] <= h_tin[i-1]; h_rdy[i] <= h_rdy[i-1]; h_act[i] <= h_act[i-1]; h_flt[i] <= h_flt[i-1]; h_prog[i] <= h_prog[i-1];
        end
        h_tin[0] <= r_tin; h_rdy[0] <= r_rdy; h_act[0] <= r_act; h_flt[0] <= r_flt; h_prog[0] <= {r_pa, r_pf, r_irq && !r_irq_q};
        if (rst_n && cyc > 4) begin
            if ({r_awready, r_wready, r_bvalid, r_bresp, r_arready, r_rvalid, r_rdata, r_cv, r_dv, r_lv, r_fault, r_ct, r_ca, r_cd, r_db, r_dl, r_dp}
                !== {d_awready, d_wready, d_bvalid, d_bresp, d_arready, d_rvalid, d_rdata, d_cv, d_dv, d_lv, d_fault, d_ct, d_ca, d_cd, d_db, d_dl, d_dp}) begin
                m1 = m1 + 1; if (m1 < 4) $display("C1 cyc %0d ingress/AXI REF != DUT", cyc);
            end
        end
        if (cyc > 16) begin
            // h_tin[k] holds the REF value of k+1 edges ago (sampled before this edge's update)
            if (d_tin !== h_tin[CFG_LAT-1]) begin m2 = m2 + 1; if (m2 < 4) $display("C2 cyc %0d target inputs != REF@-%0d", cyc, CFG_LAT); end
            if ({j_rdy, j_act, j_flt} !== {h_rdy[RT-1], h_act[RT-1], h_flt[RT-1]}) begin
                m3 = m3 + 1; if (m3 < 4) $display("C3 cyc %0d join status inputs != REF@-%0d", cyc, RT); end
            if ({d_pa, d_pf, d_irq && !d_irq_q} !== h_prog[RT-1]) begin m4 = m4 + 1; if (m4 < 4) $display("C4 cyc %0d join outputs != REF@-%0d", cyc, RT); end
            if (!poison && ((|(r_tf & {NTG{2'b10}})) || (|(d_tf & {NTG{2'b10}})))) begin
                m5 = m5 + 1; if (m5 < 4) $display("C5 cyc %0d launch reached a not-ready target", cyc); end
        end
        if (r_lv) nlaunch_r = nlaunch_r + 1; if (d_lv) nlaunch_d = nlaunch_d + 1;
        if (r_cv) ncfg = ncfg + 1; if (r_dv) ndesc = ndesc + 1;
    end
    always @(posedge clk) begin d_irq_q <= d_irq; r_irq_q <= r_irq; if (d_irq && !d_irq_q) nirq_d = nirq_d + 1; if (r_irq && !r_irq_q) nirq_r = nirq_r + 1; end

    // ---------------- host programme
    task automatic tick; begin @(posedge clk); #0.1; end endtask
    task automatic wr(input [11:0] a, input [31:0] d);
        reg aw_done, w_done; begin
        awaddr = a; wdata = d; awvalid = 1; wvalid = 1; aw_done = 0; w_done = 0;
        while (!(aw_done && w_done)) begin
            @(posedge clk); if (awvalid && r_awready) aw_done = 1; if (wvalid && r_wready) w_done = 1; #0.1;
            if (aw_done) awvalid = 0; if (w_done) wvalid = 0;
        end
        bready = 1; @(posedge clk); while (!r_bvalid) @(posedge clk); #0.1;
        bready = 0; tick;
    end endtask
    task automatic idle(input integer n); integer z; begin for (z = 0; z < n; z = z + 1) tick; end endtask
    integer rnd, r, nt, t, w, base, lim, tgt;
    initial begin
        rnd = SEED;
        idle(4); rst_n = 1; idle(12);
        for (r = 0; r < ROUNDS; r = r + 1) begin
            nt = 1 + ($urandom(rnd) % 3); rnd = rnd + 1;
            for (t = 0; t < nt; t = t + 1) begin
                tgt = 16 + ($urandom % NTG);
                wr(12'hf20, {12'd0, 12'($urandom % 2700), 8'(tgt)});
                for (w = 0; w < 8; w = w + 1) wr(12'hf24, $urandom);
                base = $urandom % 2000; lim = base + 1 + ($urandom % 2000);
                wr(12'hf20, {12'd0, 12'd0, 8'(tgt)});
                wr(12'hf28, {7'd0, 13'(lim), 12'(base)});
                wr(12'hf2c, {16'd0, 16'(1 + $urandom % 3)});
            end
            idle(40 + $urandom % 8);
            wr(12'hf30, 32'd1);
            idle(60 + $urandom % 8);
        end
        // poison round: a config row at the fault address of one target (t_fault path through the leaf)
        poison = 1; tgt = 16 + toff((MUTQ >= 0) ? MUTQ : $urandom % NQ);   // target 0 of a quadrant: its fault[0] is leaf t_fault bit 0
        if (PLAST) tgt = tgt + ntq(tgt - 16 >= toff(3) ? 3 : tgt - 16 >= toff(2) ? 2 : tgt - 16 >= toff(1) ? 1 : 0) - 1;
                   // PLAST: the LAST target of the quadrant instead (fault[0] = leaf t_fault bit NT-1: a new SE/NE slot at D4G 2)
        wr(12'hf20, {12'd0, 12'habc, 8'(tgt)});
        for (w = 0; w < 8; w = w + 1) wr(12'hf24, $urandom);
        idle(40);
        if (!r_pf || !d_pf) begin m4 = m4 + 1; $display("poison fault not seen r=%0d d=%0d", r_pf, d_pf); end
        if (m1 == 0 && m2 == 0 && m3 == 0 && m4 == 0 && m5 == 0 && nlaunch_r == ROUNDS && nirq_d == nirq_r && ncfg > 0)
            $display("HOST_CFG_LEAF_LOCKSTEP_PASS plast=%0d d4g=%0d mutq=%0d nt=%0d nf=%0d rounds=%0d cfg=%0d desc=%0d launches=%0d irq=%0d cyc=%0d", PLAST, D4G, MUTQ, NTG, NF, ROUNDS, ncfg, ndesc, nlaunch_r, nirq_r, cyc);
        else
            $display("HOST_CFG_LEAF_LOCKSTEP_FAIL mism=%0d c1=%0d c2=%0d c3=%0d c4=%0d c5=%0d launches=%0d/%0d irq=%0d/%0d",
                     m1 + m2 + m3 + m4 + m5 + (nlaunch_r != ROUNDS) + (nirq_d != nirq_r), m1, m2, m3, m4, m5, nlaunch_r, nlaunch_d, nirq_r, nirq_d);
        $finish;
    end
endmodule

// deterministic bench target: pin flops in, flop outputs, F20-addressed
module tb_cfg_tgt #(parameter integer ID = 16, parameter integer INST = 3) (
    input wire clk, rst_n, cfg_v, desc_v, launch_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr,
    output reg ready, active, output reg [1:0] fault);
    reg cv, dv, lv; reg [7:0] ct; reg [11:0] ca;
    reg armed; reg [3:0] inst; reg [5:0] run;
    always @(posedge clk) begin ct <= cfg_target; ca <= cfg_addr; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cv <= 0; dv <= 0; lv <= 0; armed <= 0; inst <= 0; run <= 0; ready <= 0; active <= 0; fault <= 0; end
        else begin
            cv <= cfg_v; dv <= desc_v; lv <= launch_v;
            if (inst != 0) inst <= inst - 1'b1;
            if ((cv || dv) && ct == ID[7:0]) begin inst <= INST[3:0]; ready <= 1'b0; end
            else if (inst == 1) ready <= 1'b1;
            if (dv && ct == ID[7:0]) armed <= 1'b1;
            if (cv && ct == ID[7:0] && ca == 12'habc) fault[0] <= 1'b1;
            if (lv && armed) begin
                if (!ready || inst != 0) fault[1] <= 1'b1;
                armed <= 1'b0; run <= 6'd10 + 6'(ID % 7);
            end else if (run != 0) run <= run - 1'b1;
            active <= (run > 1) || (lv && armed);
        end
endmodule
`default_nettype wire
