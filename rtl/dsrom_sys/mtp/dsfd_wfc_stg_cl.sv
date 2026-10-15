`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// dsfd_wfc_stg_cl: the S81 sp_wfc slot as a hardened cluster (el1013-s81-wfcstg, 2026-10-13) at the PRICED kit
// configuration of dsfd_wfc_stg (VM_LINK 1, POSTED 1, RD2 1, VMRQ 64, WOUTW 8, HEP 1): a wires-only parent over
//   u_wfc  ot_dsrom_wfc_tokpipe_stg   the stage WFC (module defaults = physical/dsrom_wfc_tokpipe/stg_basis.json)
//   u_lnk  dsfd_wfc_lnk               the link bridge
//   u_vp   dsfd_wfc_vmx_p             NEW: the VM / stage-core port tile = the three blocks below, one hard tile
//            dsfd_wfc_vmx_w           the WFC -> VM write / START transport (fast -> slow)
//            dsfd_wfc_vmx_r           the VM -> WFC outbound prefetch / DONE transport (slow -> fast)
//            dsfd_wfc_hep_t           the issue-epoch table (one SRAM macro), dsfd_wfc_kit.sv
// Why: the one-tile dsfd_wfc_vmx at these parameters is ~66k flops on two roots (the default-set closure had 63k in
// one tile, clock insertion 341 ps; the priced routes rq64w8 / rd2s stalled on hold / setup).  Its two bindings share
// nothing but the stage core's done pulse, so they are written as two blocks with every port at a register:
//   vmx_w  pin flops, pre-queue, fast -> slow ratio FIFO, write issue + START doorbell, write skid + grant link
//          (VM_LINK), write-credit return, the kit's fault register, the HEP start register.
//   vmx_r  response pin flops, prefetch, the 64 x 1032 response queue (5 x ot_sram_1r1w_128x256), slow -> fast ratio
//          FIFO, the staging buffer as two 1R1W macros (even / odd words) behind a registered look-ahead (was 32.8k
//          flops and a 64:1 x 512 mux), the predicted read register, DONE.
// The cluster is the one-tile kit CYCLE FOR CYCLE on every die port (bench tools/dsrom_wfc_cl_bench.py: lockstep
// against dsfd_wfc_stg at the priced parameters + the kit's own system cases on the cluster): 0 cycles added.
//
// Staging buffer in macros (was 64 x 512 flops, read by a 64:1 x 512 mux into vm_rq).  The WFC reads the outbound
// words in staging order, one read per word per job (the RQFREE 2 contract: pred is a counter, the pin address is
// only checked), so the next words are known before they are asked for:
//   vm_rq (flops at the pin) always holds word pred; the bank of the other parity holds word pred + 1 on its output
//   register and this bank is re-read for pred + 2 one edge after vm_rq took its word.  A read (vm_re) only steps
//   pred and a 1-bit flag; nothing between the pin and the 512-bit data path.
//   A job's words 0 / 1 / 2 are written first, long before DONE: word 0 is copied into vm_rq as it is written, words
//   1 and 2 are read into the two bank output registers the cycle after their write.
// vm_rq at the WFC's sampling edge (one edge after vm_re) is the flop table's value; in cycles the WFC does not
// sample (VM_REG contract) it may differ.
// Mutants: OT_WFCVMX_MUT_RD2_SWAP, OT_WFCVMX_MUT_PREDOFF, OT_WFCVMX_MUT_NOPCHK, OT_WFCVMX_MUT_DONEEARLY (as the
// one-tile vmx), OT_WFCVMXR_MUT_NOADV (a bank is not re-read after its word was taken: stale outbound words),
// OT_WFCVMXW_MUT_DOORBELL (the START doorbell written to a data row: the VM endpoint never starts the core).
// ---------------------------------------------------------------------------
module dsfd_wfc_vmx_w #(
    parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10, parameter integer VWA = 15,
    parameter integer DEPTH = 8, parameter integer PRE = 4, parameter integer LAG = 0, parameter integer WOUTW = 8,
    parameter integer POSTED = 1, parameter bit VM_LINK = 1
) (
    input  wire [0:0]        ck, ckv, rst, rsv,
    input  wire [VWA+FLIT:0] f_vw,           // {we, waddr, wdata} from the WFC (flops there)
    input  wire [USER_W+2*NW:0] f_cs,        // {start, user, token, pos} from the WFC
    output wire [0:0]        t_vc,           // VM write credit return (to dsfd_wfc_lnk)
    output wire [0:0]        t_swv, output wire [VWA+FLIT-1:0] t_swd, input wire [0:0] f_swr,   // VM write {addr, data}
    input  wire [0:0]        f_swa,          // VM write ACK (POSTED: sticky error level)
    input  wire [0:0]        f_kdv,          // the stage core's done pulse (f_kd[NW+32], shared with dsfd_wfc_vmx_r)
    output wire [USER_W+2*NW:0] t_ks,        // {start, user, token, pos} (dead under POSTED)
    output wire [USER_W+NW:0] t_hks,         // {start, user, pos} per stage start, from a flop (to dsfd_wfc_hep_t)
    input  wire [0:0]        f_pf, f_lf, f_rf,   // faults of the WFC, dsfd_wfc_lnk and dsfd_wfc_vmx_r (from flops)
    output wire [3:0]        t_ft            // the kit's {proto, lnk, 0, vmx}
);
    localparam integer SP = USER_W + 2 * NW;
    localparam integer PW = 1 + ((VWA + FLIT > SP) ? VWA + FLIT : SP);
    localparam integer PB = $clog2(PRE);
    wire fclk = ck[0], sclk = ckv[0];
    wire frst_n, srst_n;
    ot_dsrom_mtp_rstsync u_rf (.clk(fclk), .rst_n_async(rst[0]), .rst_n(frst_n));
    ot_dsrom_mtp_rstsync u_rsl (.clk(sclk), .rst_n_async(rsv[0]), .rst_n(srst_n));
    wire vm_we = f_vw[VWA+FLIT]; wire [VWA-1:0] vm_waddr = f_vw[FLIT +: VWA]; wire [FLIT-1:0] vm_wdata = f_vw[FLIT-1:0];
    wire core_start = f_cs[SP];
    // slow-side pin flops
    reg sw_ack, k_done;
    always @(posedge sclk) begin sw_ack <= f_swa[0] && srst_n; k_done <= f_kdv[0] && srst_n; end
    // =========================================================== fast domain
    reg pw_v, ps_v; reg [VWA-1:0] pw_a; reg [FLIT-1:0] pw_d; reg [SP-1:0] ps_d;
    always @(posedge fclk) begin
        pw_v <= vm_we && frst_n; pw_a <= vm_waddr; pw_d <= vm_wdata;
        ps_v <= core_start && frst_n; ps_d <= f_cs[SP-1:0];
    end
    reg [PW-1:0] pq [0:PRE-1]; reg [PB:0] pq_n; reg [PB-1:0] pq_r, pq_w;
    wire f_wv, f_wr; wire [PW-1:0] f_wd = pq[pq_r];
    assign f_wv = pq_n != 0;
    wire pq_pop = f_wv && f_wr;
    wire [1:0] npush = {1'b0, pw_v} + {1'b0, ps_v};
    reg fault_f;
    always @(posedge fclk) begin
        if (!frst_n) begin pq_n <= 0; pq_r <= 0; pq_w <= 0; fault_f <= 1'b0; end
        else begin
            if (pw_v) pq[pq_w] <= PW'({pw_a, pw_d});                          // kind 0 (MSB) = write
            if (ps_v) pq[pw_v ? pq_w + 1'b1 : pq_w] <= PW'(ps_d) | (PW'(1) << (PW - 1));   // kind 1 = start
            pq_w <= pq_w + npush;
            if (pq_pop) pq_r <= pq_r + 1'b1;
            pq_n <= pq_n + npush - (pq_pop ? 1'b1 : 1'b0);
            if (pq_n == PRE[PB:0] && npush != 0) fault_f <= 1'b1;      // credit / capacity violated
        end
    end
    // credit return: the slow side's issued-write count, sampled flop -> flop
    reg [3:0] wcnt_s, wcnt_f, wcnt_seen; reg vc_ret;
    always @(posedge fclk) begin
        wcnt_f <= wcnt_s;
        if (!frst_n) begin wcnt_seen <= 0; vc_ret <= 1'b0; end
        else begin
            vc_ret <= wcnt_f != wcnt_seen;
            if (wcnt_f != wcnt_seen) wcnt_seen <= wcnt_seen + 1'b1;
        end
    end
    assign t_vc = vc_ret;
    // =========================================================== the crossing
    wire s_v; wire [PW-1:0] s_d; wire s_rdy;
    ot_ratio_cdc_fifo #(.W(PW), .DEPTH(DEPTH), .LAG(LAG)) u_f2s (.wclk(fclk), .wrst_n(frst_n), .w_v(f_wv), .w_rdy(f_wr), .w_d(f_wd),
        .rclk(sclk), .rrst_n(srst_n), .r_v(s_v), .r_rdy(s_rdy), .r_d(s_d), .w_live(), .r_live());
    // =========================================================== slow domain
    reg [WOUTW-1:0] wout; reg busy, k_start; reg [USER_W-1:0] k_user; reg [NW-1:0] k_token, k_pos; reg fault_s;
    wire sw_valid, sw_ready;
    wire s_is_w = s_v && !s_d[PW-1];
    wire s_is_s = s_v && s_d[PW-1];
`ifdef OT_WFCVMX_MUT_STARTEARLY
    wire s_go = s_is_s && !busy && !k_start;
`else
    wire s_go = POSTED ? (s_is_s && !busy && !k_start && sw_ready)
                       : (s_is_s && !busy && !k_start && wout == 0 && !sw_ack);
`endif
    wire s_mark = POSTED && s_is_s && !busy && !k_start;     // the START doorbell rides the write channel
    assign sw_valid = s_is_w || s_mark;
`ifdef OT_WFCVMXW_MUT_DOORBELL
    wire [VWA-1:0] sw_addr = s_mark ? {{(VWA-1){1'b1}}, 1'b0} : s_d[FLIT +: VWA];   // MUTANT: START on a data row
`else
    wire [VWA-1:0] sw_addr = s_mark ? {VWA{1'b1}} : s_d[FLIT +: VWA];
`endif
    wire [FLIT-1:0] sw_data = s_mark ? FLIT'(s_d[SP-1:0]) : s_d[FLIT-1:0];
    wire sw_fire = sw_valid && sw_ready;
    assign s_rdy = POSTED ? sw_fire : (sw_fire || s_go);
    always @(posedge sclk) begin
        k_start <= 1'b0;
        if (!srst_n) begin wout <= 0; busy <= 1'b0; wcnt_s <= 0; fault_s <= 1'b0; end
        else begin
            if (!POSTED) begin
                wout <= wout + (sw_fire ? 1'b1 : 1'b0) - (sw_ack ? 1'b1 : 1'b0);
                if (sw_ack && wout == 0) fault_s <= 1'b1;
                if (WOUTW != 5 && sw_fire && !sw_ack && &wout) fault_s <= 1'b1;
            end
            if (sw_fire && !(POSTED && s_mark)) wcnt_s <= wcnt_s + 1'b1;
            if (s_go) begin
                k_start <= !POSTED; busy <= 1'b1;                 // POSTED: the VM endpoint starts the core
                {k_user, k_token, k_pos} <= s_d[SP-1:0];
            end
            if (k_done) begin
                if (!busy) fault_s <= 1'b1;
                if (POSTED && sw_ack) fault_s <= 1'b1;            // sticky VM status checked at the transaction end
                busy <= 1'b0;
            end
        end
    end
    assign t_ks = {k_start, k_user, k_token, k_pos};
    // write skid, then (VM_LINK) the registered grant link to the VM
    wire x_swv, x_swr; wire [VWA+FLIT-1:0] x_swd;
    ot_dsrom_mtp_skid #(.W(VWA + FLIT)) u_sw (.clk(sclk), .rst_n(srst_n), .in_valid(sw_valid), .in_ready(sw_ready),
        .in_data({sw_addr, sw_data}), .out_valid(x_swv), .out_ready(x_swr), .out_data(x_swd));
    generate if (VM_LINK) begin : g_vm_link
        ot_dsrom_mtp_ltx #(.W(VWA + FLIT)) u_swl (.clk(sclk), .rst_n(rsv[0]), .c_valid(x_swv), .c_ready(x_swr),
            .c_data(x_swd), .l_valid(t_swv[0]), .l_ready(f_swr[0]), .l_data(t_swd));
    end else begin : g_vm_direct
        assign t_swv = x_swv; assign t_swd = x_swd; assign x_swr = f_swr;
    end endgenerate
    // the stage start HEP counts (POSTED: the accepted START doorbell; else k_start), registered for the HEP tile
    reg [USER_W+NW:0] hq;
    generate if (POSTED) begin : g_hpost
        always @(posedge sclk) hq <= {x_swv && x_swr && (&x_swd[FLIT +: VWA]), x_swd[2*NW +: USER_W], x_swd[NW-1:0]};
    end else begin : g_hks
        always @(posedge sclk) hq <= {k_start, k_user, k_pos};
    end endgenerate
    assign t_hks = hq;
    // faults: this leaf's and dsfd_wfc_vmx_r's make the one-tile vmx fault; then the kit's fault register
    reg fs_f, fa; reg [3:0] ft_q;
    always @(posedge fclk) begin
        fs_f <= fault_s; fa <= fault_f || fs_f;
        ft_q <= {f_pf[0], f_lf[0], 1'b0, fa || f_rf[0]};
    end
    assign t_ft = ft_q;
endmodule

module dsfd_wfc_vmx_r #(
    parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10, parameter integer VWA = 15,
    parameter integer TXB = 0, parameter integer XWORDS = 46, parameter integer RQ = 64, parameter integer RDEPTH = 8,
    parameter integer LAG = 0, parameter integer RD2 = 1, parameter bit VM_LINK = 1
) (
    input  wire [0:0]        ck, ckv, rst, rsv,
    input  wire [VWA:0]      f_vr,           // {re, raddr} from the WFC (fixed one-edge read)
    output wire [FLIT-1:0]   t_vq,
    input  wire [0:0]        f_cst,          // the WFC's core_start (drops the done level)
    output wire [NW+32:0]    t_cd,           // {done, next_token, next_val}
    output wire [0:0]        t_srv, output wire [(RD2 ? 2*VWA+1 : VWA)-1:0] t_srd, input wire [0:0] f_srr,   // VM read request
    input  wire [(RD2 ? 2*FLIT+2 : FLIT+1)-1:0] f_srq,                                       // {[rv1, rq1,] rv, rq}
    input  wire [NW+32:0]    f_kd,           // {done, next_token, next_val} from the stage core
    output wire [0:0]        t_rf            // this leaf's fault (to dsfd_wfc_vmx_w's fault register)
);
    localparam integer SD = XWORDS;
    localparam integer IB = $clog2(SD + 1);
    localparam integer RW = 1 + ((IB + FLIT > NW + 32) ? IB + FLIT : NW + 32);
    localparam integer RWE = RD2 ? RW + 1 + FLIT : RW;   // RD2: {marker, v1, d1, idx0 / d0 or DONE payload}
    localparam integer SDP = 1 << IB;
    initial if (RQ < 2 || (RQ & (RQ - 1)) != 0 || RQ * RWE <= 32768 || SD < 4 || IB > 7 || FLIT != 512)
        $fatal(1, "dsfd_wfc_vmx_r: RQ a power of two with RQ x RWE > 32768 (SRAM queue), 4 <= XWORDS <= 126, FLIT 512");
    wire fclk = ck[0], sclk = ckv[0];
    wire frst_n, srst_n;
    ot_dsrom_mtp_rstsync u_rf (.clk(fclk), .rst_n_async(rst[0]), .rst_n(frst_n));
    ot_dsrom_mtp_rstsync u_rsl (.clk(sclk), .rst_n_async(rsv[0]), .rst_n(srst_n));
    wire vm_re = f_vr[VWA]; wire [VWA-1:0] vm_raddr = f_vr[VWA-1:0]; wire core_start = f_cst[0];
    // slow-side pin flops
    reg sr_rv, k_done; reg [FLIT-1:0] sr_rq; reg [NW+31:0] kd_q; reg sr1_rv; reg [FLIT-1:0] sr1_rq;
    always @(posedge sclk) begin
        sr_rv <= f_srq[FLIT] && srst_n; sr_rq <= f_srq[FLIT-1:0];
        sr1_rv <= RD2 && f_srq[(RD2 ? 2*FLIT+1 : FLIT)] && srst_n; sr1_rq <= f_srq[(RD2 ? FLIT+1 : 0) +: FLIT];
        k_done <= f_kd[NW+32] && srst_n; kd_q <= f_kd[NW+31:0];
    end
    wire [NW-1:0] k_next_token = kd_q[NW+31:32]; wire [31:0] k_next_val = kd_q[31:0];
    // =========================================================== slow domain: outbound prefetch after k_done
    reg pf; reg [IB-1:0] pf_i, pf_n; reg [NW-1:0] pf_tok; reg [31:0] pf_val; reg pf_dn;
    reg [$clog2(RQ):0] rq_n, r_out;
    reg pf_all;                                     // every outbound word's read issued
    wire [VWA-1:0] pf_a = TXB[VWA-1:0] + pf_i;
    wire sr_valid, sr_ready, sr1_valid; wire [VWA-1:0] sr_addr, sr1_addr;
    wire rd_ok = pf && !pf_all && (rq_n + r_out) < RQ;
    wire pair = RD2 && (pf_i + 1'b1 < SD);
    assign sr_valid = rd_ok && sr_ready;            // one widened channel: sr1_ready = sr_ready
    assign sr1_valid = rd_ok && sr_ready && pair;
    assign sr_addr = pf_a;
    assign sr1_addr = pf_a + 1'b1;
    wire sr_fire = sr_valid && sr_ready;
    wire q_v; wire [RWE-1:0] q_d; wire q_rdy;
    wire q_pop = q_v && q_rdy;
    wire rq_push_d = sr_rv;
`ifdef OT_WFCVMX_MUT_DONEEARLY
    wire rq_push_m = pf && !pf_dn && !sr_rv;                         // DONE before the outbound words
`else
    wire rq_push_m = pf && !pf_dn && pf_n == SD && !sr_rv;
`endif
    wire [RWE-1:0] rq_wd = sr_rv ? (RD2 ? {1'b0, sr1_rv, sr1_rq, (RW-1)'({pf_n, sr_rq})} : RWE'({pf_n, sr_rq}))   // data (MSB 0)
                                 : (RWE'({pf_tok, pf_val}) | (RWE'(1) << (RWE - 1)));                        // DONE (MSB 1)
    wire rq_ovf;
    ot_fifo_sram_fwft #(.W(RWE), .DEPTH(RQ), .MACRO(2)) u_rq (.clk(sclk), .rst_n(srst_n),
        .push(rq_push_d || rq_push_m), .wdata(rq_wd), .pop(q_pop), .hv(q_v), .head(q_d), .ovf(rq_ovf));
    reg fault_s;
    always @(posedge sclk) begin
        if (!srst_n) begin
            pf <= 1'b0; rq_n <= 0; r_out <= 0; fault_s <= 1'b0; pf_dn <= 1'b0; pf_all <= 1'b1;
        end else begin
            if (k_done) begin
                if (pf) fault_s <= 1'b1;
                pf <= 1'b1; pf_i <= 0; pf_n <= 0; pf_tok <= k_next_token; pf_val <= k_next_val;
                pf_dn <= 1'b0; pf_all <= 1'b0;
            end
            if (sr_fire) begin
                pf_i <= pf_i + (pair ? 2'd2 : 2'd1);
                if (pair ? (pf_i + 2'd2 >= SD) : (pf_i == SD - 1)) pf_all <= 1'b1;
            end
            if (rq_ovf) fault_s <= 1'b1;
            if (sr_rv) pf_n <= pf_n + 1'b1 + (RD2 && sr1_rv ? 1'b1 : 1'b0);
            else if (rq_push_m) pf_dn <= 1'b1;
            if (pf && (pf_dn || rq_push_m) && (sr_rv ? pf_n + 1'b1 + (RD2 && sr1_rv ? 1'b1 : 1'b0) : pf_n) == SD) pf <= 1'b0;
            rq_n <= rq_n + ((rq_push_d || rq_push_m) ? 1'b1 : 1'b0) - (q_pop ? 1'b1 : 1'b0);
            r_out <= r_out + (sr_fire ? 1'b1 : 1'b0) - (sr_rv ? 1'b1 : 1'b0);
        end
    end
    // read-request skid, then (VM_LINK) the registered grant link to the VM
    localparam integer SRW = RD2 ? 2*VWA+1 : VWA;
    wire x_srv, x_srr; wire [SRW-1:0] x_srd;
    wire [SRW-1:0] sr_word = RD2 ? SRW'({sr1_valid, sr1_addr, sr_addr}) : SRW'(sr_addr);
    ot_dsrom_mtp_skid #(.W(SRW)) u_sr (.clk(sclk), .rst_n(srst_n), .in_valid(sr_valid), .in_ready(sr_ready),
        .in_data(sr_word), .out_valid(x_srv), .out_ready(x_srr), .out_data(x_srd));
    generate if (VM_LINK) begin : g_vm_link
        ot_dsrom_mtp_ltx #(.W(SRW)) u_srl (.clk(sclk), .rst_n(rsv[0]), .c_valid(x_srv), .c_ready(x_srr),
            .c_data(x_srd), .l_valid(t_srv[0]), .l_ready(f_srr[0]), .l_data(t_srd));
    end else begin : g_vm_direct
        assign t_srv = x_srv; assign t_srd = x_srd; assign x_srr = f_srr;
    end endgenerate
    // =========================================================== the crossing
    wire r_v; wire [RWE-1:0] r_d;
    ot_ratio_cdc_fifo #(.W(RWE), .DEPTH(RDEPTH), .LAG(LAG)) u_s2f (.wclk(sclk), .wrst_n(srst_n), .w_v(q_v), .w_rdy(q_rdy), .w_d(q_d),
        .rclk(fclk), .rrst_n(frst_n), .r_v(r_v), .r_rdy(1'b1), .r_d(r_d), .w_live(), .r_live());
    // =========================================================== fast domain
    wire r_done = r_v && r_d[RWE-1];
    wire wr = r_v && !r_d[RWE-1];
    wire [IB-1:0] wi = r_d[FLIT +: IB];
    wire [IB-1:0] wi1 = wi + 1'b1;
    wire wp = RD2 && r_d[RW - 1 + FLIT];                 // a pair: the word of index wi + 1 rides along
`ifdef OT_WFCVMX_MUT_RD2_SWAP
    wire [FLIT-1:0] wd0 = wp ? r_d[RW - 1 +: FLIT] : r_d[FLIT-1:0];      // MUTANT: the pair's words swapped
    wire [FLIT-1:0] wd1 = r_d[FLIT-1:0];
`else
    wire [FLIT-1:0] wd0 = r_d[FLIT-1:0];
    wire [FLIT-1:0] wd1 = r_d[RW - 1 +: FLIT];
`endif
    reg core_done; reg [NW-1:0] core_next_token; reg [31:0] core_next_val;
    reg [SDP-1:0] got; reg fault_f;
    always @(posedge fclk) begin
        if (!frst_n) begin core_done <= 1'b0; got <= 0; fault_f <= 1'b0; end
        else begin
            if (core_start) begin core_done <= 1'b0; got <= 0; end
            if (wr) begin
                got[wi] <= 1'b1;
                if (wp) got[wi1] <= 1'b1;
            end
            if (r_done) begin
                core_done <= 1'b1;
                core_next_token <= r_d[32 +: NW]; core_next_val <= r_d[31:0];
`ifndef OT_WFCVMX_MUT_DONEEARLY
                if (got[SD-1:0] != {SD{1'b1}}) fault_f <= 1'b1;
`endif
            end
        end
    end
    assign t_cd = {core_done, core_next_token, core_next_val};
    // staging: even words in bank E, odd words in bank O (a pair is one write to each)
    wire we_e = wr && (!wi[0] || wp), we_o = wr && (wi[0] || wp);
    wire [IB-2:0] wa_e = wi[0] ? wi1[IB-1:1] : wi[IB-1:1];
    wire [IB-2:0] wa_o = wi[IB-1:1];
    wire [FLIT-1:0] wd_e = wi[0] ? wd1 : wd0, wd_o = wi[0] ? wd0 : wd1;
    // the predicted read: pred = the staging index of the next read; the pin address is checked one edge later
    reg [IB-1:0] pred; reg pchk_v; reg [VWA-1:0] pchk_a; reg [IB-1:0] pchk_p; reg pfault;
    wire [VWA-1:0] ra = vm_raddr - TXB[VWA-1:0];
    reg adv_q, rd_go, rd_bk, pr_e, pr_o; reg [IB-1:0] rd_ix;
    reg [FLIT-1:0] vm_rq;
    wire [FLIT-1:0] rq_e, rq_o;
    wire [IB:0] p2 = {1'b0, pred} + 2'd2;
    always @(posedge fclk) begin
        if (!frst_n) begin
            pred <= `ifdef OT_WFCVMX_MUT_PREDOFF 1 `else 0 `endif; pchk_v <= 1'b0; pfault <= 1'b0;
            adv_q <= 1'b0; rd_go <= 1'b0; pr_e <= 1'b0; pr_o <= 1'b0;
        end else begin
            if (vm_re) pred <= (pred == SD - 1) ? {IB{1'b0}} : pred + 1'b1;
            pchk_v <= vm_re; pchk_a <= ra; pchk_p <= pred;
`ifndef OT_WFCVMX_MUT_NOPCHK
            if (pchk_v && pchk_a != {{(VWA-IB){1'b0}}, pchk_p}) pfault <= 1'b1;
`endif
            adv_q <= vm_re;                                  // vm_rq takes word pred from the other bank next edge
`ifdef OT_WFCVMXR_MUT_NOADV
            rd_go <= 1'b0;                                   // MUTANT: the bank whose word was taken is not re-read
`else
            rd_go <= adv_q;                                  // ... and that bank is re-read for pred + 2 the edge after
`endif
            pr_o <= we_o && wa_o == 0;                       // word 1 written: onto bank O's output register
            pr_e <= we_e && wa_e == 1;                       // word 2 written: onto bank E's output register
        end
        rd_bk <= pred[0];
        rd_ix <= (p2 >= SD) ? IB'(p2 - SD) : p2[IB-1:0];
        if (adv_q) vm_rq <= pred[0] ? rq_o : rq_e;
        if (we_e && wa_e == 0) vm_rq <= wd_e;                // word 0 as it is written
    end
    assign t_vq = vm_rq;
    wire re_e = pr_e || (rd_go && !rd_bk), re_o = pr_o || (rd_go && rd_bk);
    wire [5:0] ra_e = pr_e ? 6'd1 : 6'(rd_ix[IB-1:1]), ra_o = pr_o ? 6'd0 : 6'(rd_ix[IB-1:1]);
    ot_sram_1r1w_64x512_m1_r2c2 u_se (.clk(fclk), .r_ce_in(re_e), .r_addr_in(ra_e), .rd_out(rq_e),
        .w_ce_in(we_e), .w_addr_in(6'(wa_e)), .wd_in(wd_e), .w_mask_in({FLIT{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    ot_sram_1r1w_64x512_m1_r2c2 u_so (.clk(fclk), .r_ce_in(re_o), .r_addr_in(ra_o), .rd_out(rq_o),
        .w_ce_in(we_o), .w_addr_in(6'(wa_o)), .wd_in(wd_o), .w_mask_in({FLIT{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    reg fs_f, fb;
    always @(posedge fclk) begin fs_f <= fault_s; fb <= fault_f || fs_f || pfault; end
    assign t_rf = fb;
endmodule

// dsfd_wfc_vmx_p: the VM / stage-core port tile of the sp_wfc slot = dsfd_wfc_vmx_w + dsfd_wfc_vmx_r + dsfd_wfc_hep_t in ONE
// hard tile (flattened in synthesis).  Why one tile and not three (floorplan, el1013-s81-wfcstg 2026-10-13): every die
// pin of the slot is on its E face (328 um) and hard children sit on a 43.2 um origin lattice, so only TWO tiles can
// own that face: the link bridge (151.2 um) and one VM-port tile (>= 147 um: two rows of response-queue macros).  All
// VM / core pins (write link, read link, responses, done, HEP epochs) therefore leave from this tile.  The clock rule is
// met by structure instead of by tile count: staging buffer in macros, and the slow -> fast ratio FIFO at RDEPTH 4.
//   RDEPTH 4 is cycle-exact with the kit's 8: its reader pops on every fast edge (r_rdy = 1) and its writer pushes at
//   most once a serial cycle, so at most 3 entries are outstanding (written, not yet seen retired by the writer: read
//   <= 1.5 T_s after the write, pointer back <= 1 T_s later) and w_rdy never drops at depth 4 either (lockstep bench).
//   Sinks: ck ~11.9k (pin flops 0.6k, pre-queue 2.1k, f2s 4.2k, s2f shadow 4.1k, read register / staging control 0.9k),
//   ckv ~14.6k (f2s shadow 4.2k, write skid + link 1.6k, response pin flops 1.1k, queue output buffer 2.1k, s2f 4.1k,
//   HEP 1.2k, control 0.3k); 8 macros.
module dsfd_wfc_vmx_p (
    input  wire [0:0]    ck, ckv, rst, rsv,
    input  wire [527:0]  f_vw,           // {we, waddr, wdata} from the WFC
    input  wire [52:0]   f_cs,           // {start, user, token, pos} from the WFC
    input  wire [15:0]   f_vr,           // {re, raddr} from the WFC
    output wire [511:0]  t_vq,           // the WFC's read data (one edge after re)
    output wire [53:0]   t_cd,           // {done, next_token, next_val} to the WFC
    output wire [0:0]    t_vc,           // VM write credit return (to dsfd_wfc_lnk)
    input  wire [0:0]    f_pf, f_lf,     // faults of the WFC and dsfd_wfc_lnk
    output wire [0:0]    t_swv, output wire [526:0] t_swd, input wire [0:0] f_swr, input wire [0:0] f_swa,
    output wire [0:0]    t_srv, output wire [30:0] t_srd, input wire [0:0] f_srr,
    input  wire [1025:0] f_srq,
    output wire [52:0]   t_ks, input wire [53:0] f_kd,
    output wire [35:0]   t_hep,
    output wire [3:0]    t_ft
);
    wire [31:0] hks; wire [0:0] vr_ft;
    dsfd_wfc_vmx_w u_vw (.ck(ck), .ckv(ckv), .rst(rst), .rsv(rsv),
        .f_vw(f_vw), .f_cs(f_cs), .t_vc(t_vc),
        .t_swv(t_swv), .t_swd(t_swd), .f_swr(f_swr), .f_swa(f_swa), .f_kdv(f_kd[53]), .t_ks(t_ks), .t_hks(hks),
        .f_pf(f_pf), .f_lf(f_lf), .f_rf(vr_ft), .t_ft(t_ft));
    dsfd_wfc_vmx_r #(.RDEPTH(4)) u_vr (.ck(ck), .ckv(ckv), .rst(rst), .rsv(rsv),
        .f_vr(f_vr), .t_vq(t_vq), .f_cst(f_cs[52]), .t_cd(t_cd),
        .t_srv(t_srv), .t_srd(t_srd), .f_srr(f_srr), .f_srq(f_srq), .f_kd(f_kd), .t_rf(vr_ft));
    dsfd_wfc_hep_t u_hep (.ckv(ckv), .rsv(rsv), .f_hks(hks), .t_hep(t_hep));
endmodule

// the cluster parent: wires and five constant ties (the WFC's unused SOURCE inputs); every net child pin -> child pin
// or child pin -> cluster pin, driven and captured by registers inside the children
// s81-die-rtl-bind 2026-10-14 (F4 hop): the die binds this cluster under the die master name dsfd_wfc_stg
// (+define+DSFD_WFC_STG_CL_DIE: physical/s81_die_rtl/layer1.f) and the cluster carries the stage hand-off engine's
// endpoint (engine 7 hop, ADAPTER_CONTRACT_1011 pins c_cmd / c_done / c_st): child dsfd_wfc_hop_ep below.
`ifdef DSFD_WFC_STG_CL_DIE
module dsfd_wfc_stg (
`else
module dsfd_wfc_stg_cl (
`endif
    input  wire [0:0] ck, ckv, rst, rsv,
    input  wire [84:0] c_cmd, output wire [8:0] c_done, output wire [1:0] c_st,   // engine 7 (hop) endpoint
    input  wire [0:0] f_liv, input  wire [512:0] f_lid, output wire [0:0] t_lir,
    output wire [0:0] t_lov, output wire [512:0] t_lod, input  wire [0:0] f_lor,
    output wire [0:0] t_swv, output wire [526:0] t_swd, input wire [0:0] f_swr, input wire [0:0] f_swa,
    output wire [0:0] t_srv, output wire [30:0] t_srd, input wire [0:0] f_srr,
    input  wire [1025:0] f_srq,
    output wire [52:0] t_ks, input wire [53:0] f_kd,
    output wire [35:0] t_hep,
    output wire [3:0] t_ft
);
    wire w_in_valid, w_in_ready, w_in_last, w_out_valid, w_out_ready, w_out_last;
    wire [511:0] w_in_data, w_out_data;
    wire core_start; wire [20:0] core_token, core_pos; wire [9:0] core_user;
    wire vm_we, vm_re; wire [14:0] vm_waddr, vm_raddr; wire [511:0] vm_wdata, vm_rq;
    wire [53:0] cd; wire proto_fault, lnk_ft; wire [0:0] vc_ret;
    wire [29:0] kv_base_nc; wire pr_re_nc; wire [9:0] pr_user_nc; wire [20:0] pr_pos_nc; wire [3:0] pr_blk_nc;
    wire core_busy_nc, tok_valid_nc, wf_issue_nc, wf_reject_nc, wf_squash_nc;
    wire [9:0] tok_user_nc, users_done_nc; wire [20:0] tok_pos_nc, tok_id_nc; wire [512:0] dw_nc;
    wire clk = ck[0];
    ot_dsrom_wfc_tokpipe_stg u_wfc (
        .clk(clk), .rst_n(rst[0]), .cfg_users(10'd0), .cfg_prompt_len(21'd0), .cfg_gen_len(21'd0),
        .in_valid(w_in_valid), .in_ready(w_in_ready), .in_data(w_in_data), .in_last(w_in_last),
        .out_valid(w_out_valid), .out_ready(w_out_ready), .out_data(w_out_data), .out_last(w_out_last),
        .core_start(core_start), .core_token(core_token), .core_pos(core_pos), .core_user(core_user),
        .core_done(cd[53]), .core_next_token(cd[52:32]), .core_next_val(cd[31:0]), .kv_base(kv_base_nc),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .vm_re(vm_re), .vm_raddr(vm_raddr), .vm_rq(vm_rq),
        .pr_re(pr_re_nc), .pr_user(pr_user_nc), .pr_pos(pr_pos_nc), .pr_q(21'd0), .pr_blk(pr_blk_nc), .pr_qk(1'b0),
        .core_busy(core_busy_nc), .tok_valid(tok_valid_nc), .tok_user(tok_user_nc), .tok_pos(tok_pos_nc), .tok_id(tok_id_nc),
        .users_done(users_done_nc), .proto_fault(proto_fault), .wf_issue(wf_issue_nc), .wf_reject(wf_reject_nc),
        .wf_squash(wf_squash_nc));
    dsfd_wfc_lnk u_lnk (.ck(ck), .rst(rst), .f_liv(f_liv), .f_lid(f_lid), .t_lir(t_lir),
        .t_wiv(w_in_valid), .t_wid({w_in_last, w_in_data}), .f_wig(w_in_ready),
        .f_wov(w_out_valid), .f_wod({w_out_last, w_out_data}), .t_wog(w_out_ready),
        .t_lov(t_lov), .t_lod(t_lod), .f_lor(f_lor), .t_dw(dw_nc), .f_vc(vc_ret), .t_ft(lnk_ft));
    dsfd_wfc_vmx_p u_vp (.ck(ck), .ckv(ckv), .rst(rst), .rsv(rsv),
        .f_vw({vm_we, vm_waddr, vm_wdata}), .f_cs({core_start, core_user, core_token, core_pos}),
        .f_vr({vm_re, vm_raddr}), .t_vq(vm_rq), .t_cd(cd), .t_vc(vc_ret), .f_pf(proto_fault), .f_lf(lnk_ft),
        .t_swv(t_swv), .t_swd(t_swd), .f_swr(f_swr), .f_swa(f_swa), .t_srv(t_srv), .t_srd(t_srd), .f_srr(f_srr),
        .f_srq(f_srq), .t_ks(t_ks), .f_kd(f_kd), .t_hep(t_hep), .t_ft(t_ft));
    dsfd_wfc_hop_ep #(.MUT(`ifdef DSFD_WFC_HOP_MUT `DSFD_WFC_HOP_MUT `else 0 `endif)) u_hop (.ck(ck), .rst(rst),
        .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st), .f_lov(t_lov), .f_lol(t_lod[512]));
endmodule

// dsfd_wfc_hop_ep (s81-die-rtl-bind 2026-10-14, die item F4): the stage hand-off engine (port 7, hop) of a layer die =
// the WFC stage kit.  The stage program's last op (L<n>.substage_hop0) is the HIDDEN hand-off; the kit starts it at its
// done (the sequencer's kit done t_kd excludes engine 7: dsfd_stage_seq_c8 KDX 7), so a hop job completes when the
// kit's link out has transferred the LAST flit of its next message (t_lov && last: the grant-protocol sender moves one
// flit every cycle its valid is high).  Messages that end before their descriptor is queued are counted (in order), so
// a fast hand-off never loses its completion.  The descriptor is accepted ahead (dataflow start: inputs present 1).
// MUT 6 (negative control): the job completes at its descriptor, not at the message end.
module dsfd_wfc_hop_ep #(parameter integer MUT = 0) (
    input  wire [0:0]  ck, rst,
    input  wire [84:0] c_cmd,
    output wire [8:0]  c_done,
    output wire [1:0]  c_st,
    input  wire [0:0]  f_lov, f_lol            // the kit's link out: valid, last
);
    wire clk = ck[0];
    reg [1:0] rs_q;
    always @(posedge clk or negedge rst[0]) if (!rst[0]) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];
    reg mend; always @(posedge clk or negedge rn) if (!rn) mend <= 1'b0; else mend <= f_lov[0] && f_lol[0];
    reg [7:0] mcnt;                            // message ends not yet matched to a hop job
    wire j_v; wire [83:0] j_d, jn_d; wire j_new, ep_f;
    wire j_done = j_v && ((MUT == 6) ? 1'b1 : (mcnt != 0 || mend));
    reg f_ov;
    always @(posedge clk or negedge rn)
        if (!rn) begin mcnt <= 0; f_ov <= 1'b0; end
        else begin
            mcnt <= mcnt + mend - ((j_done && MUT != 6) ? 8'd1 : 8'd0);   // one message end per hop job, in order
            if (mcnt == 8'hFF && mend) f_ov <= 1'b1;
        end
    ot_s81_slab_ep #(.QD(8), .JQ(2), .MUT((MUT == 6) ? 0 : MUT)) u_ep (.c_clk(clk), .c_rst_n(rst[0]), .c_cmd(c_cmd),
        .c_done(c_done), .c_st(c_st), .e_clk(clk), .e_rst_n(rst[0]), .j_v(j_v), .j_d(j_d), .j_new(j_new),
        .j_new_d(jn_d), .j_present(1'b1), .j_done(j_done), .slab_fault(f_ov), .ep_fault(ep_f));
endmodule
