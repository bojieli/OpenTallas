`timescale 1ns/1ps
// KV-CTL10 2026-10-20 (K.STA.CTL exact successor of the GEN9 / boot-ages control tile): qkd_kv_die_cfg_a_c32 = the native
// census form (no driver > 32 mapped loads) of rtl/qwen_sys/kv_bootage_20261019/qkd_kv_die_cfg_a.sv (AGES = 1), the die
// configuration block the boot-ages die tile (qkd_kvs_tiles_hroot_ff_k_mu_ba.sv qkd_kvs_ctl u_dcfg) binds.  Same ports,
// same word map, same fault rules and the same outputs on every edge (lockstep rtl/test/mu_qwen_1018/tb_kv_dcfg_a_c32.sv):
//   * ECTL / reset-region fields: the S32-B form of qkd_kv_die_cfg_s32 (qkd_kv_ctl_s32_misc.sv): explicit KEPT POR copies
//     (async clear, D = ps[0], release on the ps[1] edge), KEPT predecode, 4 KEPT copies of the data pin flops, one kept
//     qkd_kv_die_cfg_c32_fld hierarchy leaf per field;
//   * AGE words (19: attention 32 b, 2 PV pair 8 b, 16 V port 16 b = 304 bits): one kept field leaf per <= 16 bits, written
//     by KEPT predecode (ahi = {wr, is_age, g_ix[4:3]}, alo = g_ix[2:0] one-hot) from a KEPT copy of the data pin flop.
//     The age registers are NOT reset: every age output is ANDed with sealed (POR 0), and sealed rises only after every
//     age word was written exactly once in order, so an age register's power-up value is never observable (same outputs
//     as the POR-cleared original on every edge; owner 10-20 09:05: datapath unreset).  The 304 output gates read 19
//     KEPT copies of the sealed flop (same set / POR clear), 16 bits each.
// MUT (bench negative controls) as qkd_kv_die_cfg_a: 1-5 ECTL / reset / capability, 6 = age words one word off,
// 7 = age outputs not gated by the seal.  No handshake, credit or ready: configuration nets, POR-held.
module qkd_kv_die_cfg_a_c32 #(parameter integer NRST = 43, parameter integer CAP = 0, parameter integer AGES = 1, parameter integer MUT = 0) (
    input  wire               ck, por_n,
    input  wire               cfg_we, input wire [7:0] cfg_addr, input wire [63:0] cfg_data,
    output reg  [32*5-1:0]    ectl_a_cfg, ectl_b_cfg, ectl_c_cfg,
    output reg  [NRST*8-1:0]  rst_dly,
    output wire               fused_program_capability,
    output wire [31:0]        age_attn,         // {D_RL, D_QK, F_DLY, PV_LEAD}
    output wire [15:0]        age_pv,           // {pair 1, pair 0} FIRST_INPUT_AGE
    output wire [255:0]       age_vport,        // port i: [16 i +: 16] = {DQ, RT}
    output reg                sealed, fault
);
    localparam integer NA = (AGES != 0) ? 19 : 0;
    localparam integer A0 = 32 + NRST + ((CAP != 0) ? 1 : 0);   // first age word
    localparam integer NW = A0 + NA;                              // data words before the seal
    localparam [63:0] SEAL = 64'h514b5644_43464731;
    localparam integer KE = 16, KR = (NRST + 3) / 4, KS = 19;
    generate if (NRST < 1 || NW + 1 > 256 || AGES == 0) begin : g_bad
        initial $fatal(1, "qkd_kv_die_cfg_a_c32: NRST %0d CAP %0d AGES %0d (AGES 1 only)", NRST, CAP, AGES);
    end endgenerate
    // POR: two-flop synchronised release (async assert), as qkd_rst_region; kept (else opt_merge folds ps[1] into rcp[0])
    (* keep *) reg [1:0] ps;
    always @(posedge ck or negedge por_n) if (!por_n) ps <= 2'b00; else ps <= {ps[0], 1'b1};
    wire pr_n = ps[1];
    (* keep *) reg [KE+KR-1:0] rcp;     // field POR copies: release on the ps[1] edge
    always @(posedge ck or negedge por_n) if (!por_n) rcp <= {(KE+KR){1'b0}}; else rcp <= {(KE+KR){ps[0]}};
    // write port pin registers
    reg we_q; reg [7:0] a_q; reg [63:0] d_q;
    always @(posedge ck or negedge pr_n) if (!pr_n) we_q <= 1'b0; else we_q <= cfg_we;
    // KEPT second copy of the write-enable pin flop (same D / clock / clear): the age / seal write terms read it, so the
    // accept term wr is not one net into every ECTL, reset, age and seal decode (gate 2 census: 44 loads)
    (* keep *) reg we_q2;
    always @(posedge ck or negedge pr_n) if (!pr_n) we_q2 <= 1'b0; else we_q2 <= cfg_we;
    always @(posedge ck) begin a_q <= cfg_addr; d_q <= cfg_data; end
    (* keep *) reg [14:0] dqc0, dqc1, dqc2, dqc3;
    (* keep *) reg [31:0] dqa;
    always @(posedge ck) begin
        dqc0 <= cfg_data[14:0]; dqc1 <= cfg_data[14:0]; dqc2 <= cfg_data[14:0]; dqc3 <= cfg_data[14:0];
        dqa <= cfg_data[31:0];
    end
    reg [8:0] next;
    wire is_ectl = a_q < 8'd32;
    wire is_rst  = !is_ectl && a_q < 8'(32 + NRST);
    wire is_cap  = (CAP != 0) && a_q == 8'(32 + NRST);
    wire is_age  = a_q >= 8'(A0) && a_q < 8'(A0 + NA);
    wire [7:0] g_ix = a_q - 8'(A0) + ((MUT == 6) ? 8'd1 : 8'd0);
    wire is_seal = a_q == NW[7:0];
    wire age_pad = (g_ix == 8'd0) ? (d_q[63:32] != 0) : (g_ix == 8'd1 || g_ix == 8'd2) ? (d_q[63:8] != 0) : (d_q[63:16] != 0);
    reg  cap_q;
    wire [7:0] r_ix = a_q - 8'd32 + ((MUT == 3) ? 8'd1 : 8'd0);
    wire bad = sealed || ({1'b0, a_q} != next) ||
               (MUT != 2 && ((is_ectl && d_q[63:15] != 0) || (is_rst && d_q[63:8] != 0) || (is_cap && d_q[63:1] != 0) || (is_age && age_pad))) ||
               (is_seal && (d_q != SEAL || next != NW[8:0])) || (!is_ectl && !is_rst && !is_cap && !is_age && !is_seal);
    wire wr = we_q && !(bad || fault);
    wire wr2 = we_q2 && !(bad || fault);
    always @(posedge ck or negedge pr_n) begin
        if (!pr_n) begin
            cap_q <= 1'b0; sealed <= 1'b0; fault <= 1'b0; next <= 9'd0;
        end else if (we_q) begin
            if (bad || fault) fault <= 1'b1;
            else begin
                next <= next + 9'd1;
                if (is_cap) cap_q <= (MUT == 4) ? d_q[1] : d_q[0];
                if (is_seal) sealed <= 1'b1;
            end
        end
    end
    // KEPT copies of sealed (one per <= 16 gated age bits), same set / clear as sealed; cleared from 2 KEPT POR copies
    // (D = ps[0], release on the ps[1] edge) so pr_n keeps <= 32 loads
    (* keep *) reg [1:0] rcs;
    always @(posedge ck or negedge por_n) if (!por_n) rcs <= 2'b00; else rcs <= {2{ps[0]}};
    (* keep *) wire sl_set = wr2 && is_seal;
    (* keep *) reg [KS-1:0] sl_c;
    genvar gs;
    generate for (gs = 0; gs < KS; gs = gs + 1) begin : g_sl
        always @(posedge ck or negedge rcs[gs / 10]) if (!rcs[gs / 10]) sl_c[gs] <= 1'b0; else if (sl_set) sl_c[gs] <= 1'b1;
    end endgenerate
    // ---- ECTL / reset-region fields (S32-B form of qkd_kv_die_cfg_s32) ----
    (* keep *) wire [3:0] phi; (* keep *) wire [7:0] plo, rlo; (* keep *) wire [5:0] rhi;
    (* keep *) wire [31:0] fe; (* keep *) wire [NRST-1:0] fr;
    genvar q, f, r;
    generate
        for (q = 0; q < 4; q = q + 1) begin : g_phi
            assign phi[q] = wr && is_ectl && a_q[4:3] == q;
        end
        for (q = 0; q < 8; q = q + 1) begin : g_plo
            assign plo[q] = a_q[2:0] == q;
            assign rlo[q] = r_ix[2:0] == q;
        end
        for (q = 0; q < 6; q = q + 1) begin : g_rhi
            assign rhi[q] = wr && is_rst && r_ix[5:3] == q && r_ix[7:6] == 2'd0;
        end
        for (q = 0; q < 32; q = q + 1) begin : g_fe
            assign fe[q] = phi[q/8] && plo[q%8];
        end
        for (q = 0; q < NRST; q = q + 1) begin : g_fr
            assign fr[q] = rhi[q/8] && rlo[q%8];
        end
        for (f = 0; f < 32; f = f + 1) begin : g_ef
            wire [14:0] dq = (f < 16) ? dqc0 : dqc1;
            wire [14:0] qf;
            qkd_kv_die_cfg_c32_fld #(.W(15)) u_f (.ck(ck), .rn(rcp[f/2]), .en(fe[f]),
                .d({(MUT == 1) ? dq[9:5] : dq[14:10], (MUT == 1) ? dq[14:10] : dq[9:5], dq[4:0]}), .q(qf));
            always @* begin ectl_a_cfg[5*f +: 5] = qf[4:0]; ectl_b_cfg[5*f +: 5] = qf[9:5]; ectl_c_cfg[5*f +: 5] = qf[14:10]; end
        end
        for (r = 0; r < NRST; r = r + 1) begin : g_rf
            wire [7:0] qr;
            qkd_kv_die_cfg_c32_fld #(.W(8)) u_r (.ck(ck), .rn(rcp[KE + r/4]), .en(fr[r]), .d((r < 22) ? dqc2[7:0] : dqc3[7:0]), .q(qr));
            always @* rst_dly[8*r +: 8] = qr;
        end
    endgenerate
    // ---- AGE words: g = 0 attention (2 x 16 b), 1..2 PV pair (8 b), 3..18 V port (16 b); unreset, seal-gated ----
    (* keep *) wire [2:0] ahi; (* keep *) wire [7:0] alo; (* keep *) wire [18:0] fa;
    // the attention word's high half gets its own (structurally different, same function) enable: 2 x 16 bits on one
    // enable = 64 mapped loads
    (* keep *) wire fa0h = wr2 && is_age && a_q == 8'(A0 - ((MUT == 6) ? 1 : 0));
    wire [31:0] ag_attn; wire [15:0] ag_pv; wire [255:0] ag_vp;
    genvar ga;
    generate
        for (ga = 0; ga < 3; ga = ga + 1) begin : g_ahi
            assign ahi[ga] = wr2 && is_age && g_ix[4:3] == ga && g_ix[7:5] == 3'd0;
        end
        for (ga = 0; ga < 8; ga = ga + 1) begin : g_alo
            assign alo[ga] = g_ix[2:0] == ga;
        end
        for (ga = 0; ga < 19; ga = ga + 1) begin : g_fa
            assign fa[ga] = ahi[ga/8] && alo[ga%8];
        end
        qkd_kv_die_cfg_c32_age #(.W(16)) u_at0 (.ck(ck), .en(fa[0]), .d(dqa[15:0]), .q(ag_attn[15:0]));
        qkd_kv_die_cfg_c32_age #(.W(16)) u_at1 (.ck(ck), .en(fa0h), .d(dqa[31:16]), .q(ag_attn[31:16]));
        for (ga = 0; ga < 2; ga = ga + 1) begin : g_pv
            qkd_kv_die_cfg_c32_age #(.W(8)) u_p (.ck(ck), .en(fa[1 + ga]), .d(dqa[7:0]), .q(ag_pv[8*ga +: 8]));
        end
        for (ga = 0; ga < 16; ga = ga + 1) begin : g_vp
            qkd_kv_die_cfg_c32_age #(.W(16)) u_v (.ck(ck), .en(fa[3 + ga]), .d(dqa[15:0]), .q(ag_vp[16*ga +: 16]));
        end
    endgenerate
    // seal gating (16 bits a sealed copy): sl_c[0] / [1] attention low / high, sl_c[2] PV pairs, sl_c[3 + k] V port k
    assign age_attn[15:0] = ((MUT == 7) || sl_c[0]) ? ag_attn[15:0] : 16'd0;
    assign age_attn[31:16] = ((MUT == 7) || sl_c[1]) ? ag_attn[31:16] : 16'd0;
    assign age_pv = ((MUT == 7) || sl_c[2]) ? ag_pv : 16'd0;
    genvar gv;
    generate for (gv = 0; gv < 16; gv = gv + 1) begin : g_vg
        assign age_vport[16*gv +: 16] = ((MUT == 7) || sl_c[3 + gv]) ? ag_vp[16*gv +: 16] : 16'd0;
    end endgenerate
    assign fused_program_capability = cap_q && ((MUT == 5) || sealed);
endmodule

// KV-CTL10 10-20: one AGE field of qkd_kv_die_cfg_a_c32 (hold register, no reset: read only through the seal gate).  A kept
// hierarchy leaf so synthesis cannot fold the word's write decode into every bit's hold mux.
(* keep_hierarchy *)
module qkd_kv_die_cfg_c32_age #(parameter integer W = 16) (
    input wire ck, en, input wire [W-1:0] d, output reg [W-1:0] q
);
    always @(posedge ck) if (en) q <= d;
endmodule
