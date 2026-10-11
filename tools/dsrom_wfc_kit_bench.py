#!/usr/bin/env python3
"""Exact gate of the WFC kit masters dsfd_wfc_src / dsfd_wfc_stg (rtl/dsrom_sys/mtp/dsfd_wfc_kit.sv).

The closed-element system benches (tb_mtp_rom_s0_tokpipe: SOURCE + lnk + tok + vmx + sequencer; tb_mtp_rom_stg_tokpipe:
STAGE + lnk + vmx) are regenerated with the four separately instantiated elements replaced by ONE kit instance on
the die-facing ports, so the bench drives exactly the ports the S81 die wires.  Observation-only internals (latency
statistics, issue counters) are bound hierarchically (u_kit.*); the committed-token stream, the configuration and
the faults come from the kit's own ports (t_tok, t_cfg, t_ft).  Cases mirror tools/dsrom_wfc_prompt_pipe_bench.py
(--hard-token pairing: SOURCE PROMPT_EXTRA 2 + dsfd_wfc_tok_hard) plus the vmx predicted-read negative.

  python3 tools/dsrom_wfc_kit_bench.py --out DIR [--case NAME]   -> DIR/summary.json, prints WFC_KIT_GATE PASS|FAIL
"""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
import dsrom_mtp_rom_bench as B

ROOT = Path(__file__).resolve().parents[1]
KIT = 'rtl/dsrom_sys/mtp/dsfd_wfc_kit.sv'
EXTRA = ['rtl/dsrom_sys/mtp/ot_dsrom_wfc_tok_r3.sv', 'rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc_tokpipe.sv',
         'rtl/dsrom_sys/mtp/ot_dsrom_wfc_tokpipe_src.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_wfc_tokpipe_stg.sv', KIT,
         'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv', 'rtl/dsrom_sys/mtp/tb_mtp_link_rtt.sv',
         'rtl/dsrom_sys/mtp/dsfd_vm_wfc_ep.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_stage_seq.sv',
         'rtl/dsrom_sys/mtp/dsfd_stage_seq.sv']
INTERNAL = ['w_in_valid', 'w_in_ready', 'w_in_last', 'w_out_valid', 'w_out_ready', 'w_out_last', 'w_in_data',
            'w_out_data', 'core_start', 'core_done_w', 'core_token', 'core_pos', 'cnt_tok', 'cnt_val', 'core_user',
            'kv_base', 'vm_we', 'vm_re', 'vm_waddr', 'vm_raddr', 'vm_wdata', 'vm_rq', 'pr_re', 'pr_user', 'pr_pos',
            'pr_blk', 'pr_q', 'pr_qk', 'core_busy', 'wf_issue', 'wf_reject', 'wf_squash', 'users_done', 'dw', 'vc_ret']
SRC_KIT = '''    wire [52:0] k_tok; wire [3:0] k_ft;
    dsfd_wfc_src u_kit (.ck(fclk), .ckv(sclk), .rst(rst_n), .rsv(rst_n),
        .f_liv(li_v), .f_lid(li_d), .t_lir(li_r), .t_lov(lo_v), .t_lod(lo_d), .f_lor(lo_r),
        .t_swv(swv), .t_swd(swd), .f_swr(swr), .f_swa(swa), .t_srv(srv), .t_srd(srd), .f_srr(srr), .f_srq(srq),
        .t_ks(ks), .f_kd(kd), .f_c(cfgw), .t_tok(k_tok), .t_cfg({cfg_users, cfg_plen, cfg_glen}), .t_ft(k_ft));
    assign {proto_fault, lnk_ft, tok_ft, vmx_ft} = k_ft;
    assign {tok_valid, tok_user, tok_pos, tok_id} = k_tok;
'''
STG_KIT = '''    wire [3:0] k_ft;
    dsfd_wfc_stg #(.LAG(LAG)) u_kit (.ck(fclk), .ckv(sclk), .rst(rst_n), .rsv(rst_n),
        .f_liv(li_v), .f_lid(li_d), .t_lir(li_r), .t_lov(lo_v), .t_lod(lo_d), .f_lor(lo_r),
        .t_swv(swv), .t_swd(swd), .f_swr(swr), .f_swa(swa), .t_srv(srv), .t_srd(srd), .f_srr(srr), .f_srq(srq),
        .t_ks(ks), .f_kd(kd), .t_ft(k_ft));
    assign proto_fault = k_ft[3]; assign lnk_ft = k_ft[2]; assign vmx_ft = k_ft[0];
    assign tok_valid = u_kit.tok_valid; assign tok_user = u_kit.tok_user; assign tok_pos = u_kit.tok_pos;
    assign tok_id = u_kit.tok_id;
'''
VMRLY = '''    // VM side behind VF / VR registered hub relay stations (serial clock): the kit launches requests on grants
    // (VM_LINK 1), the VM receives them with RTT-sized ot_dsrom_mtp_lrx_rtt; response / ACK pushed back through VR.
    localparam integer VF = 13, VR = 13;
    wire k_swv, k_swg, k_srv, k_srg, r_swv, r_swg, r_srv, r_srg, k_swa; wire [VWA+FLIT-1:0] k_swd, r_swd;
    wire [VWA-1:0] k_srd, r_srd; wire [FLIT:0] k_srq;
    mtp_test_relay #(.W(VWA+FLIT+1), .HOPS(VF)) y_swf (.clk(sclk), .rst_n(rst_n), .in_data({k_swv, k_swd}), .out_data({r_swv, r_swd}));
    mtp_test_relay #(.W(1), .HOPS(VR)) y_swr (.clk(sclk), .rst_n(rst_n), .in_data(r_swg), .out_data(k_swg));
    mtp_test_relay #(.W(VWA+1), .HOPS(VF)) y_srf (.clk(sclk), .rst_n(rst_n), .in_data({k_srv, k_srd}), .out_data({r_srv, r_srd}));
    mtp_test_relay #(.W(1), .HOPS(VR)) y_srr (.clk(sclk), .rst_n(rst_n), .in_data(r_srg), .out_data(k_srg));
    mtp_test_relay #(.W(1), .HOPS(VR)) y_swa (.clk(sclk), .rst_n(rst_n), .in_data(swa), .out_data(k_swa));
    mtp_test_relay #(.W(FLIT+1), .HOPS(VR)) y_srq (.clk(sclk), .rst_n(rst_n), .in_data(srq), .out_data(k_srq));
    ot_dsrom_mtp_lrx_rtt #(.W(VWA+FLIT), .D(VF+VR+4), .ENABLE_RTT(1), .FORWARD_HOPS(VF), .RETURN_HOPS(VR)) v_sw (
        .clk(sclk), .rst_n(rst_n), .l_valid(r_swv), .l_ready(r_swg), .l_data(r_swd), .c_valid(swv), .c_ready(swr), .c_data(swd));
    ot_dsrom_mtp_lrx_rtt #(.W(VWA), .D(VF+VR+4), .ENABLE_RTT(1), .FORWARD_HOPS(VF), .RETURN_HOPS(VR)) v_sr (
        .clk(sclk), .rst_n(rst_n), .l_valid(r_srv), .l_ready(r_srg), .l_data(r_srd), .c_valid(srv), .c_ready(srr), .c_data(srd));
'''
POSTED_VM = '''    // POSTED (main decision 10-10): the kit's VM channels behind VF / VR hub stations into the VM-side endpoint
    // dsfd_vm_wfc_ep (one in-order op pipe to a VM port); START reaches the core from the endpoint (KS stations);
    // the VM port model applies ops at the pins in order and returns reads RL cycles later; errors are a sticky level.
    localparam integer VF = 13, VR = 13, KS = 1, RL = 6;
    wire k_swv, k_swg, k_srv, k_srg, r_swv, r_swg, r_srv, r_srg, k_err, e_err; wire [VWA+FLIT-1:0] k_swd, r_swd;
    wire [VWA-1:0] k_srd, r_srd; wire [FLIT:0] k_srq, e_srq; wire [USER_W+2*NW:0] e_ks, k_ks_unused;
    wire e_mv, e_mwe; wire [VWA-1:0] e_mrow; wire [FLIT-1:0] e_md; reg e_mov = 0; reg [FLIT-1:0] e_mod = 0;
    mtp_test_relay #(.W(VWA+FLIT+1), .HOPS(VF)) y_swf (.clk(sclk), .rst_n(rst_n), .in_data({k_swv, k_swd}), .out_data({r_swv, r_swd}));
    mtp_test_relay #(.W(1), .HOPS(VR)) y_swr (.clk(sclk), .rst_n(rst_n), .in_data(r_swg), .out_data(k_swg));
    mtp_test_relay #(.W(VWA+1), .HOPS(VF)) y_srf (.clk(sclk), .rst_n(rst_n), .in_data({k_srv, k_srd}), .out_data({r_srv, r_srd}));
    mtp_test_relay #(.W(1), .HOPS(VR)) y_srr (.clk(sclk), .rst_n(rst_n), .in_data(r_srg), .out_data(k_srg));
    mtp_test_relay #(.W(1), .HOPS(VR)) y_err (.clk(sclk), .rst_n(rst_n), .in_data(e_err), .out_data(k_err));
    mtp_test_relay #(.W(FLIT+1), .HOPS(VR)) y_srq (.clk(sclk), .rst_n(rst_n), .in_data(e_srq), .out_data(k_srq));
    mtp_test_relay #(.W(USER_W+2*NW+1), .HOPS(KS)) y_ks (.clk(sclk), .rst_n(rst_n), .in_data(e_ks), .out_data(ks));
    dsfd_vm_wfc_ep #(.VF(VF), .VR(VR), .RL(RL)) u_ep (.ck(sclk), .rst(rst_n), .f_swv(r_swv), .f_swd(r_swd), .t_swg(r_swg),
        .f_srv(r_srv), .f_srd(r_srd), .t_srg(r_srg), .t_srq(e_srq), .t_err(e_err), .t_ks(e_ks),
        .m_v(e_mv), .m_we(e_mwe), .m_row(e_mrow), .m_d(e_md), .m_ov(e_mov), .m_od(e_mod), .m_fault(1'b0));
    reg [RL-1:0] e_rv = 0; reg [VWA-1:0] e_rr [0:RL-1]; integer e_i;
    always @(posedge sclk) begin             // VM port: ops take effect at the pins in issue order; fixed-latency reads
        if (e_mv === 1'b1 && e_mwe === 1'b1) begin
            if (e_mrow >= 64) begin $display("FAIL: VM write address"); $finish; end
            vmem[e_mrow] = e_md;
        end
        e_rv <= rst_n ? {e_rv[RL-2:0], e_mv === 1'b1 && e_mwe === 1'b0} : '0; e_rr[0] <= e_mrow;
        for (e_i = 1; e_i < RL; e_i = e_i + 1) e_rr[e_i] <= e_rr[e_i-1];
        e_mov <= rst_n && e_rv[RL-1]; e_mod <= vmem[e_rr[RL-1]];
    end
    assign swv = 1'b0; assign srv = 1'b0; assign swd = '0; assign srd = '0;   // the TB's own VM model stays idle
'''
SSEQ = '''    // main decision A: the kit's start / done through the stage sequencer dsfd_stage_seq (ot_s81_stage_seq) to the
    // engines; port 0 = this bench's stage-core model (cmd -> ks start, its done -> dn), ports 1 / 2 = fixed-latency
    // engine responders; program {eng1 op, eng0 core op, eng2 op} loaded at reset over f_pw
    localparam integer S_NENG = 3, S_OPW = 7, S_ARGW = 24, S_PEW = 28, S_CMDW = 1 + USER_W + 2*NW + 24 + 7, S_TAGW = 8;
    wire [USER_W+2*NW:0] k_ks; wire [NW+32:0] s_kd; wire [S_NENG-1:0] s_cv; wire [S_NENG*S_CMDW-1:0] s_cd; wire [5:0] s_st;
    reg [S_NENG-1:0] s_dv = 0; reg [S_NENG*S_TAGW-1:0] s_dt = 0; reg [S_OPW+S_PEW:0] s_pw = 0; reg [S_OPW:0] s_plen = 0;
    dsfd_stage_seq #(.NOPS(128), .NENG(S_NENG)) u_sseq (.ckv(sclk), .rsv(rst_n), .f_ks(k_ks), .t_kd(s_kd), .f_pw(s_pw),
        .f_plen(s_plen), .t_cmdv(s_cv), .t_cmdd(s_cd), .f_dnv(s_dv), .f_dntag(s_dt), .t_st(s_st));
    integer s_pi = 0, s_e, s_l1 = -1, s_l2 = -1; reg [S_TAGW-1:0] s_t0, s_t1, s_t2; reg s_core_wait = 0;
    reg [USER_W+2*NW:0] s_ks = 0;
    assign ks = s_ks;
    always @(posedge sclk) begin
        s_pw <= 0; s_dv <= 0; s_ks <= 0;
        if (rst_n && scyc > 20 && s_pi < 3) begin   // program (after the sequencer reset): 0 = eng1, 1 = eng0 (the core), 2 = eng2
            s_pw <= {1'b1, 7'(s_pi), 4'(s_pi == 0 ? 1 : s_pi == 1 ? 0 : 2), 24'(s_pi)}; s_pi = s_pi + 1;
            if (s_pi == 3) s_plen <= 8'd3;
        end
        if (s_cv[0]) begin             // the core op: start the bench's core model with the job context
            s_t0 = {s_cd[S_CMDW-1], s_cd[S_OPW-1:0]};
            s_ks <= {1'b1, s_cd[S_CMDW-2 -: USER_W], s_cd[S_CMDW-2-USER_W-NW -: NW], s_cd[S_CMDW-2-USER_W -: NW]};
            s_core_wait = 1;
        end
        if (s_cv[1]) begin s_t1 = {s_cd[S_CMDW + S_CMDW-1], s_cd[S_CMDW +: S_OPW]}; s_l1 = 3; end
        if (s_cv[2]) begin s_t2 = {s_cd[2*S_CMDW + S_CMDW-1], s_cd[2*S_CMDW +: S_OPW]}; s_l2 = 5; end
        if (s_l1 == 0) begin s_dv[1] <= 1'b1; s_dt[S_TAGW +: S_TAGW] <= s_t1; end
        if (s_l2 == 0) begin s_dv[2] <= 1'b1; s_dt[2*S_TAGW +: S_TAGW] <= s_t2; end
        if (s_l1 >= 0) s_l1 = s_l1 - 1; if (s_l2 >= 0) s_l2 = s_l2 - 1;
        if (s_core_wait && kd[NW+32]) begin s_dv[0] <= 1'b1; s_dt[0 +: S_TAGW] <= s_t0; s_core_wait = 0; end
        if (s_st[5]) begin $display("MTP_STG FAIL: stage sequencer fault code %h", s_st[4:1]); $finish; end
    end
'''
HEPCHK = '''    // HEP (DSpark hrow versioning): every stage start's issue epoch; a re-issued (user, pos) must carry a strictly higher
    // epoch than its previous issue (its old row can never be served), a user's epoch never decreases, and in total the
    // epochs advance exactly once per WFC rejection (checked before PASS)
    wire [USER_W+NW+4:0] k_hep;
    integer h_ep [0:1023]; integer h_pe [0:1023][0:255]; integer h_inc = 0, h_i, h_j;
    initial for (h_i = 0; h_i < 1024; h_i = h_i + 1) begin h_ep[h_i] = 0; for (h_j = 0; h_j < 256; h_j = h_j + 1) h_pe[h_i][h_j] = -1; end
    always @(posedge sclk) if (k_hep[USER_W+NW+4]) begin : hepchk
        integer hu, hp, he;
        hu = k_hep[NW+4 +: USER_W]; hp = k_hep[4 +: NW]; he = k_hep[3:0];
        if (he < h_ep[hu] && !(h_ep[hu] == 15 && he == 0)) begin TAGFAIL("epoch of u%0d decreased %0d -> %0d", hu, h_ep[hu], he); end
        if (he != h_ep[hu]) h_inc = h_inc + ((he - h_ep[hu] + 16) % 16);
        if (h_pe[hu][hp % 256] >= 0 && h_pe[hu][hp % 256] == he) begin TAGFAIL("u%0d pos %0d re-issued under the same epoch %0d (stale row)", hu, hp, he); end
        h_pe[hu][hp % 256] = he; h_ep[hu] = he;
    end
'''
CASES = {  # name -> (base case in dsrom_mtp_rom_bench.cases(), stage?, extra defines, expect)
    's0_tr_dspark': ('s0_tr_dspark', 0, [], 'pass'), 's0_tr_forced': ('s0_tr_forced', 0, [], 'pass'),
    's0_tr_forced_w16': ('s0_tr_forced_w16', 0, [], 'pass'), 's0_hash_u3': ('s0_hash_u3', 0, [], 'pass'),
    's0_hash_u1_fast': ('s0_hash_u1_fast', 0, [], 'pass'), 's0_hash_u4_ar1': ('s0_hash_u4_ar1', 0, [], 'pass'),
    'stg_r1': ('stg_r1', 1, [], 'pass'), 'stg_vmnat': ('stg_vmnat', 1, [], 'pass'), 'stg_lag1': ('stg_lag1', 1, [], 'pass'),
    'stg_r2_slowvm': ('stg_r2_slowvm', 1, [], 'pass'),
    's0_neg_noepoch': ('s0_neg_noepoch', 0, [], 'fail'), 's0_neg_nohold': ('s0_neg_nohold', 0, [], 'fail'),
    's0_neg_predoff': ('s0_tr_forced', 0, ['OT_WFCVMX_MUT_PREDOFF'], 'fail'),
    'stg_neg_nocred': ('stg_neg_nocred', 1, [], 'fail'),
    'stg_neg_predoff': ('stg_r1', 1, ['OT_WFCVMX_MUT_PREDOFF'], 'fail'),
    # VM behind 13/13 hub relay stations + grant links (VM_LINK 1); negative: the short-history receiver overflows
    'vmrly_s0_tr_forced': ('s0_tr_forced', 0, [], 'pass', 1), 'vmrly_s0_hash_u3': ('s0_hash_u3', 0, [], 'pass', 1),
    'vmrly_stg_r1': ('stg_r1', 1, [], 'pass', 1), 'vmrly_stg_r2_slowvm': ('stg_r2_slowvm', 1, [], 'pass', 1),
    'vmrly_stg_neg_nolink': ('stg_r1', 1, [], 'fail', 2),
    'vmrly_stg_vmnat': ('stg_vmnat', 1, [], 'pass', 1),
    # POSTED writes (no ACK fence): START as an in-order doorbell through dsfd_vm_wfc_ep; RAW checks are the benches'
    # own (every RX word in the VM at core start; the outbound prefetch reads what the core wrote)
    'post_stg_r1': ('stg_r1', 1, [], 'pass', 4), 'post_stg_vmnat': ('stg_vmnat', 1, [], 'pass', 4),
    'post_stg_r2_slowvm': ('stg_r2_slowvm', 1, [], 'pass', 4), 'post_s0_tr_forced': ('s0_tr_forced', 0, [], 'pass', 4),
    'post_s0_hash_u3': ('s0_hash_u3', 0, [], 'pass', 4),
    'post_stg_neg_early': ('stg_r1', 1, ['OT_VMWFC_MUT_EARLY_START'], 'fail', 5),
    # (the s0 bench checks no VM contents at core start, so its early-START mutant cannot discriminate: stg only)
    # RD2 (main GO 10-11): 2-port prefetch over the posted endpoint; mutant = the pair's words swapped
    'rd2_stg_r1': ('stg_r1', 1, [], 'pass', 7), 'rd2_stg_vmnat': ('stg_vmnat', 1, [], 'pass', 7),
    'rd2_stg_r2_slowvm': ('stg_r2_slowvm', 1, [], 'pass', 7), 'rd2_s0_tr_forced': ('s0_tr_forced', 0, [], 'pass', 7),
    'rd2_s0_hash_u3': ('s0_hash_u3', 0, [], 'pass', 7),
    'rd2_stg_neg_swap': ('stg_r1', 1, ['OT_WFCVMX_MUT_RD2_SWAP'], 'fail', 8),
    # main decision A: stage start / done through the stage sequencer (dsfd_stage_seq); mutants: dropped start, early done
    'sseq_stg_r1': ('stg_r1', 1, [], 'pass', 9), 'sseq_stg_vmnat': ('stg_vmnat', 1, [], 'pass', 9),
    'sseq_stg_r2_slowvm': ('stg_r2_slowvm', 1, [], 'pass', 9),
    'sseq_stg_neg_dropstart': ('stg_r1', 1, ['OT_SSEQ_MUT_DROP_START'], 'fail', 9),
    'sseq_stg_neg_earlydone': ('stg_r1', 1, ['OT_SSEQ_MUT_EARLY_DONE'], 'fail', 9),
    # HEP (DSpark hrow): issue epochs per stage start; mutant = the epoch never advances (stale rows)
    'hep_s0_tr_forced': ('s0_tr_forced', 0, [], 'pass', 10), 'hep_s0_hash_u3': ('s0_hash_u3', 0, [], 'pass', 10),
    'hep_stg_r1': ('stg_r1', 1, [], 'pass', 10),
    'hep_s0_neg_stale': ('s0_hash_u3', 0, ['OT_WFCHEP_MUT_STALE'], 'fail', 10),
    # TOKIN: the S0 kit's link-in from the collective MTP lane (t_mrt {data, valid} / f_mrt grant)
    'tokin_s0_tr_forced': ('s0_tr_forced', 0, [], 'pass', 6), 'tokin_s0_hash_u3': ('s0_hash_u3', 0, [], 'pass', 6),
    'vmrly_stg_neg_wout4': ('stg_r1', 1, [], 'fail', 3),   # s0 never exceeds 15 writes in flight: stg only 'vmrly_s0_neg_nolink': ('s0_tr_forced', 0, [], 'fail', 2),
}


VMRQ_K = 64   # vmx read-response queue in the vmrly cases (set by --vmrq); 64 adopted (RQ 16 stalls s0 behind 13/13 stations)


def kit_tb(stage, vmrly=0):
    tb = 'tb_mtp_rom_stg_tokpipe' if stage else 'tb_mtp_rom_s0_tokpipe'
    body = (ROOT / f'rtl/dsrom_sys/mtp/tb/{tb}.sv').read_text()
    pats = [r'    ot_rom_pkg_ctrl_wfc_tokpipe #\(.*?wf_squash\)\);\n', r'    dsfd_wfc_lnk u_lnk \(.*?\);\n']
    if not stage:
        pats.append(r'    dsfd_wfc_tok_r3 u_tok \(.*?\);\n')
    for p in pats:
        body, n = re.subn(p, '', body, count=1, flags=re.S)
        assert n == 1, (tb, p)
    binds = ''.join(f'    assign {x} = u_kit.{x};\n' for x in INTERNAL if re.search(rf'\b{x}\b', body))
    kit = STG_KIT if stage else SRC_KIT
    if vmrly == 6:   # TOKIN: the token returns enter as the collective MTP lane's {data, valid} / grant
        kit = kit.replace('dsfd_wfc_src u_kit (', 'dsfd_wfc_src #(.TOKIN(1)) u_kit (')
        for a_, b_ in (('.f_liv(li_v), .f_lid(li_d), .t_lir(li_r),', '.f_liv(1\'b0), .f_lid(\'0), .t_lir(), .f_mrt({li_d[FLIT-1:0], li_v}), .t_mrg(li_r),'),):
            assert a_ in kit, a_
            kit = kit.replace(a_, b_)
        kit += '''    always @(posedge fclk) if (li_v && !li_d[FLIT]) begin $display("MTP_S0 FAIL: token-return flit without last"); $finish; end
'''
    elif vmrly == 10:   # HEP: issue epochs for the hidden-row senders
        kit = kit.replace('dsfd_wfc_stg #(.LAG(LAG)) u_kit (', 'dsfd_wfc_stg #(.LAG(LAG), .HEP(1)) u_kit (').replace(
            'dsfd_wfc_src u_kit (', 'dsfd_wfc_src #(.HEP(1)) u_kit (').replace('.t_ft(k_ft));', '.t_ft(k_ft), .t_hep(k_hep));')
        tag = 'MTP_STG' if stage else 'MTP_S0'
        kit = kit + HEPCHK.replace('TAGFAIL("', '$display("' + tag + ' FAIL: hep ').replace('); end', '); $finish; end')
    elif vmrly == 9:   # main decision A: kit start / done through dsfd_stage_seq (stage dies)
        for a_, b_ in (('.t_ks(ks)', '.t_ks(k_ks)'), ('.f_kd(kd)', '.f_kd(s_kd)')):
            assert a_ in kit, a_
            kit = kit.replace(a_, b_)
        kit = SSEQ + kit
    elif vmrly in (7, 8):   # posted + RD2 (2-port prefetch); 8 = mutant (define in the case)
        kit = kit.replace('u_kit (', '#(.VM_LINK(1), .VMRQ(64), .WOUTW(8), .POSTED(1), .RD2(1)) u_kit (').replace(
            'dsfd_wfc_stg #(.LAG(LAG)) #(.VM_LINK(1), .VMRQ(64), .WOUTW(8), .POSTED(1), .RD2(1))',
            'dsfd_wfc_stg #(.LAG(LAG), .VM_LINK(1), .VMRQ(64), .WOUTW(8), .POSTED(1), .RD2(1))')
        for a_, b_ in (('.t_swv(swv)', '.t_swv(k_swv)'), ('.t_swd(swd)', '.t_swd(k_swd)'), ('.f_swr(swr)', '.f_swr(k_swg)'),
                       ('.f_swa(swa)', '.f_swa(k_err)'), ('.t_srv(srv)', '.t_srv(k_srv)'), ('.t_srd(srd)', '.t_srd(k_srd)'),
                       ('.f_srr(srr)', '.f_srr(k_srg)'), ('.f_srq(srq)', '.f_srq(k_srq)'), ('.t_ks(ks)', '.t_ks(k_ks_unused)')):
            assert a_ in kit, a_
            kit = kit.replace(a_, b_)
        pv = (POSTED_VM.replace('wire [VWA-1:0] k_srd, r_srd; wire [FLIT:0] k_srq, e_srq;',
                                'wire [2*VWA:0] k_srd, r_srd; wire [2*FLIT+1:0] k_srq, e_srq;')
              .replace('mtp_test_relay #(.W(VWA+1), .HOPS(VF)) y_srf', 'mtp_test_relay #(.W(2*VWA+2), .HOPS(VF)) y_srf')
              .replace('mtp_test_relay #(.W(FLIT+1), .HOPS(VR)) y_srq', 'mtp_test_relay #(.W(2*FLIT+2), .HOPS(VR)) y_srq')
              .replace('dsfd_vm_wfc_ep #(.VF(VF), .VR(VR), .RL(RL))', 'dsfd_vm_wfc_ep #(.VF(VF), .VR(VR), .RL(RL), .RD2(1))')
              .replace(".m_fault(1'b0));", ".m_fault(1'b0), .m1_v(e_m1v), .m1_row(e_m1row), .m1_ov(e_m1ov), .m1_od(e_m1od));")
              .replace('reg [RL-1:0] e_rv = 0; reg [VWA-1:0] e_rr [0:RL-1]; integer e_i;',
                       'reg [RL-1:0] e_rv = 0; reg [VWA-1:0] e_rr [0:RL-1]; integer e_i;\n'
                       '    wire e_m1v; wire [VWA-1:0] e_m1row; reg e_m1ov = 0; reg [FLIT-1:0] e_m1od = 0;\n'
                       '    reg [RL-1:0] e_rv1 = 0; reg [VWA-1:0] e_rr1 [0:RL-1];')
              .replace("        e_mov <= rst_n && e_rv[RL-1]; e_mod <= vmem[e_rr[RL-1]];",
                       "        e_mov <= rst_n && e_rv[RL-1]; e_mod <= vmem[e_rr[RL-1]];\n"
                       "        e_rv1 <= rst_n ? {e_rv1[RL-2:0], e_m1v === 1'b1} : '0; e_rr1[0] <= e_m1row;\n"
                       "        for (e_i = 1; e_i < RL; e_i = e_i + 1) e_rr1[e_i] <= e_rr1[e_i-1];\n"
                       "        e_m1ov <= rst_n && e_rv1[RL-1]; e_m1od <= vmem[e_rr1[RL-1]];"))
        for chk in ('RD2(1)', 'e_m1od <= vmem', '2*FLIT+2', '2*VWA+2', 'wire [2*VWA:0] k_srd'):
            assert chk in pv, chk
        kit = pv + kit
    elif vmrly in (4, 5):   # posted: endpoint + VM port model; 5 = mutant (the define is in the case)
        kit = kit.replace('u_kit (', '#(.VM_LINK(1), .VMRQ(64), .WOUTW(8), .POSTED(1)) u_kit (').replace(
            'dsfd_wfc_stg #(.LAG(LAG)) #(.VM_LINK(1), .VMRQ(64), .WOUTW(8), .POSTED(1))',
            'dsfd_wfc_stg #(.LAG(LAG), .VM_LINK(1), .VMRQ(64), .WOUTW(8), .POSTED(1))')
        for a_, b_ in (('.t_swv(swv)', '.t_swv(k_swv)'), ('.t_swd(swd)', '.t_swd(k_swd)'), ('.f_swr(swr)', '.f_swr(k_swg)'),
                       ('.f_swa(swa)', '.f_swa(k_err)'), ('.t_srv(srv)', '.t_srv(k_srv)'), ('.t_srd(srd)', '.t_srd(k_srd)'),
                       ('.f_srr(srr)', '.f_srr(k_srg)'), ('.f_srq(srq)', '.f_srq(k_srq)'), ('.t_ks(ks)', '.t_ks(k_ks_unused)')):
            assert a_ in kit, a_
            kit = kit.replace(a_, b_)
        kit = POSTED_VM + kit
    elif vmrly:
        kit = VMRLY + (kit if vmrly == 2 else   # 2: negative, valid / ready skids (VM_LINK 0) behind the relays
                       kit.replace('u_kit (', '#(.VM_LINK(1), .WOUTW(WOUTW_K)) u_kit (').replace(
                           'dsfd_wfc_stg #(.LAG(LAG)) #(.VM_LINK(1), .WOUTW(WOUTW_K))', 'dsfd_wfc_stg #(.LAG(LAG), .VM_LINK(1), .WOUTW(WOUTW_K))'))
        kit = kit.replace('WOUTW_K', '4' if vmrly == 3 else '8').replace('.VM_LINK(1), .WOUTW(', f'.VM_LINK(1), .VMRQ({VMRQ_K}), .WOUTW(')
        for a_, b_ in (('.t_swv(swv)', '.t_swv(k_swv)'), ('.t_swd(swd)', '.t_swd(k_swd)'), ('.f_swr(swr)', '.f_swr(k_swg)'),
                       ('.f_swa(swa)', '.f_swa(k_swa)'), ('.t_srv(srv)', '.t_srv(k_srv)'), ('.t_srd(srd)', '.t_srd(k_srd)'),
                       ('.f_srr(srr)', '.f_srr(k_srg)'), ('.f_srq(srq)', '.f_srq(k_srq)')):
            assert a_ in kit, a_
            kit = kit.replace(a_, b_)
    body, n = re.subn(r'    dsfd_wfc_vmx #\(.*?\) u_vmx \(.*?\);\n', lambda m: kit + binds, body, count=1, flags=re.S)
    assert n == 1, tb
    if vmrly == 10 and not stage:   # HEP: the epochs advance exactly once per WFC rejection
        assert body.count('        $display("MTP_S0 PASS mode') == 1
        body = body.replace('        $display("MTP_S0 PASS mode', '        if (h_inc != rej) begin $display("MTP_S0 FAIL: hep epoch '
                            'advances %0d != WFC rejections %0d", h_inc, rej); $finish; end\n        $display("MTP_S0 PASS mode')
    return tb, body


def run(name, out):
    base, stage, defs, expect = CASES[name][:4]
    vmrly = CASES[name][4] if len(CASES[name]) > 4 else 0
    spec = B.cases()[base]
    tb, body = kit_tb(stage, vmrly)
    d = out / name; d.mkdir(parents=True, exist_ok=True)
    meta = B.trace_hex(ROOT / B.TRACES / f"{spec['trace']}.cfg.json", d / 'trace.hex') if 'trace' in spec else None
    (d / 'tb.sv').write_text(body)
    srcs = [str(ROOT / s) for s in list(B.COMMON) + EXTRA] + [str(d / 'tb.sv')]
    cmd = ['iverilog', '-g2012', '-s', tb, '-o', str(d / 'sim.vvp')] + \
          [f'-D{x}' for x in list(spec.get('defines', [])) + defs] + \
          [f'-P{tb}.{k}={v}' for k, v in spec.get('params', {}).items()] + srcs
    b = subprocess.run(cmd, capture_output=True, text=True); (d / 'build.log').write_text(b.stdout + b.stderr)
    if b.returncode:
        return dict(case=name, expect=expect, verdict='BUILD_ERROR', log=b.stderr[-1500:])
    r = subprocess.run(['vvp', '-n', str(d / 'sim.vvp')], capture_output=True, text=True, cwd=d)
    (d / 'run.log').write_text(r.stdout + r.stderr)
    tag = 'MTP_STG' if stage else 'MTP_S0'
    m = re.search(rf'^{tag} (PASS|FAIL).*$', r.stdout, re.M) or re.search(r'^LINK_REG (FAIL).*$', r.stdout, re.M)
    got = m.group(1).lower() if m else 'nolog'
    return dict(case=name, base=base, defines=list(spec.get('defines', [])) + defs, expect=expect, got=got,
                verdict='OK' if got == expect else 'UNEXPECTED', result=(m.group(0) if m else r.stdout[-400:]), trace=meta)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--out', type=Path, required=True); p.add_argument('--case'); p.add_argument('--jobs', type=int, default=8)
    p.add_argument('--raw-negative', action='store_true', help='one expected-FAIL case: exit 1 when it fails as required')
    p.add_argument('--vmrq', type=int, default=64, help='vmx RQ in the vmrly cases (power of two; >= stationed read RTT)')
    a = p.parse_args(); a.out = a.out.resolve(); a.out.mkdir(parents=True, exist_ok=True)
    global VMRQ_K; VMRQ_K = a.vmrq
    names = [a.case] if a.case else list(CASES)
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        recs = list(ex.map(lambda n: run(n, a.out), names))
    pins = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in list(B.COMMON) + EXTRA}
    ok = all(r['verdict'] == 'OK' for r in recs)
    (a.out / 'summary.json').write_text(json.dumps(dict(all_ok=ok, cases=recs, source_sha256=pins), indent=1) + '\n')
    for r in recs:
        print(f"{r['verdict']:10s} {r['case']:18s} expect={r['expect']} {str(r.get('result', r.get('log', '')))[:180]}")
    npos = sum(1 for r in recs if r['expect'] == 'pass' and r['verdict'] == 'OK')
    nneg = sum(1 for r in recs if r['expect'] == 'fail' and r['verdict'] == 'OK')
    if a.raw_negative:
        assert len(recs) == 1 and recs[0]['expect'] == 'fail', 'raw-negative needs one negative case'
        if recs[0]['verdict'] == 'OK':
            print('WFC_KIT_NEGATIVE FAIL_AS_REQUIRED ' + recs[0]['case']); return 1
        print('WFC_KIT_NEGATIVE UNEXPECTED_PASS ' + recs[0]['case']); return 0
    print(f"WFC_KIT_GATE {'PASS' if ok else 'FAIL'} positives={npos} negatives={nneg}")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
