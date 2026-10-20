`timescale 1ns/1ps
// KV-CTL3 10-20: native-census (<= 32 mapped loads a driver) successors of three qkd_kvs_ctl members, as NEW modules so
// the shared originals (listed by ~40 closed kit specs) stay byte-identical.  Each is the original module with an S32
// parameter (0 = the original logic, 1 = the census form); the tile binds S32 = 1.
//   qkd_kv_es_fan_root2_b_s32          <- qkd_kv_ctl_half_root_b.sv qkd_kv_es_fan_root2_b (fork S32-B)
//   qkd_kv_die_cfg_s32 (+ _s32_fld)    <- qkd_kv_die_cfg.sv qkd_kv_die_cfg (fork S32-B)
//   qkd_static_kv_ownership_calendar_mu_s32 <- qkd_static_kv_ownership_calendar_mu.sv (root banks sliced)
// Lockstep: rtl/test/mu_qwen_1018/run_kv_ctl_s32_b.sh (fanr, dcfg), run_kv_ctl_s32_d.sh (ownership).

// ===== fan root (S32-B) =====
// ---------------------------------------------------------------------------------------------------------------------
// Qwen KV die, RTL-BUILD-KV/BOOT 2026-10-18 (results/arch/qwen_kv_boot_path_1018/note.md): the static PC chain carries
// the EMBEDDING BOOT WORDS (the removed per-stack strips' BOOT_WR delivery) on its existing lane-0 pc / data / address
// fields, with one new valid bit:
//   qkd_kv_es_fan_root2_b = qkd_kv_es_fan_root2 + boot face bw (pin flop) + h[783] BV.  On a boot edge the word's
//                           stack / pc / data / address replace lane A's DST / PA / DA / AD (AV stays 0, so no writer
//                           lane hits); a writer or expected event (or the lanes-2/3 edge) on a boot edge latches fault.
//   qkd_kv_es_fan_stack_b = qkd_kv_es_fan_stack + chain bit F_BT = 779 (W 780): BV && DST == stack.
// Writer / expected / token-start / calendar fields and their edges are UNCHANGED (h[782:0] and d[778:0] equal the
// originals' bit for bit whenever bw is idle: tb_kv_boot_chain lockstep).  Boot word age root input -> station:
// as a writer lane 0 word (kvjc3_pc_chain writer_ages).  Boot is elastic (init phase): no compiled slot is added.
// MUT (bench only): root2_b 1 = a boot word overrides a writer edge with no fault.
// ---------------------------------------------------------------------------------------------------------------------
// KV-SRAM-CTL 10-19 (mu6, SAFE checklist item 3): PH1C = 1 replaces the phase register ph1 (mu5 census: 1,033 loads, the
// select of the two 256-bit lane-pair data muxes) by 17 KEPT identical copies (same D / clock / async clear): copy 0 drives
// the narrow selects (av, xv, pc fields, boot terms, fault), copies 1..16 drive one 32-bit slice of DB / DA each (<= ~32
// loads a copy), and the runtime part-selects es_p[288*hi + 1 +: 256] / es_p[288*lo + 1 +: 256] / [5*hi +: 5] become
// explicit constant-index 2:1 muxes (the gate's runtime_partselect warning).  Same function on every edge; 0 = mu5 form.
// KV-CTL3 10-20 (native32 census, SAFE checklist item 3): S32 = 1 rebuilds the two wide selects so every driver has <= 32
// mapped loads (a 2:1 mux bit = 2 loads, select + inverse) with NO added edge: ph1 -> 35 KEPT copies (DB / DA 16-bit
// slices 0..31, av/xv/boot/fault 32, QB/QA 33, PB/PA 34); use_b (bw_p[0] && !ev_now && !ph1, ~290 h bits) -> 19 KEPT flops
// ubc loaded one edge EARLY from the same-edge inputs (bw[0], expected_valid, es lane valids, ph1's D), 16 bits a copy;
// ev_now (the D of every ph1 / use_b copy) -> 3 groups of KEPT copies of ev_p and the 4 es lane valid pin flops.  Same
// function on every edge (tb_kv_fanr_mu6_lockstep S32 0 vs 1).  Use RCOPIES >= 32 with S32 (reset family ~860 flops).
// S32 = 0: unchanged (PH1C selects the mu5 / mu6 form).
module qkd_kv_es_fan_root2_b_s32 #(parameter integer MUT = 0, parameter integer RCOPIES = 1, parameter integer PH1C = 0,
                               parameter integer S32 = 0) (
    input  wire            ck,
    input  wire            rst_n,
    input  wire [4*288-1:0] es,
    input  wire [19:0]     dest_pc,
    input  wire [1:0]      dest_stack,
    input  wire [58:0]     identity,
    input  wire [1:0]      generation,
    input  wire [3:0]      expected_valid,
    input  wire [19:0]     expected_pc,
    input  wire [1:0]      expected_stack,
    input  wire [58:0]     expected_identity,
    input  wire [1:0]      expected_generation,
    input  wire [28:0]     expected_address,
    input  wire            emb_start,
    input  wire [17:0]     emb_token,
    input  wire [15:0]     emb_epoch,
    input  wire            cfg_we,
    input  wire [7:0]      cfg_addr,
    input  wire [63:0]     cfg_data,
    // BOOT (RTL-BUILD-KV/BOOT): the embedding boot word from qkd_embgw_boot_s
    //   bw = {data 256, address 29 = {bank, col, row}, pc 5, stack 2, v}
    input  wire [292:0]    bw,
    output reg  [783:0]    h,
    output reg             fault
);
    // ---- pin flops (identical to qkd_kv_es_fan_root) ----
    (* keep *) reg rs_q;
    always @(posedge ck) rs_q <= rst_n;
    // KV-GRP-CTL/MU5 10-19: RCOPIES > 1 = that many KEPT identical copies of rs_q (family wire g_rc.rsv, ot_rst_split)
    // for the synthesis reset-relay split (physical/common_flow/ot_rst_copies.py); default 1 = unchanged.
    generate if (RCOPIES > 1) begin : g_rc
        (* keep *) reg [RCOPIES-2:0] rc_q;
        always @(posedge ck) rc_q <= {(RCOPIES-1){rst_n}};
        (* keep, ot_rst_split *) wire [RCOPIES-1:0] rsv = {rc_q, rs_q};
    end endgenerate
    reg [4*288-1:0] es_p; reg [19:0] dpc_p, epc_p; reg [1:0] dst_p, gen_p, est_p, egen_p;
    reg [58:0] id_p, eid_p; reg [28:0] ea_p; reg [17:0] tok_p; reg [15:0] ep_p; reg [7:0] ca_p; reg [63:0] cd_p;
    reg [3:0] ev_p; reg ss_p, cw_p;
    always @(posedge ck) begin
        es_p <= es; dpc_p <= dest_pc; dst_p <= dest_stack; id_p <= identity; gen_p <= generation;
        epc_p <= expected_pc; est_p <= expected_stack; eid_p <= expected_identity; egen_p <= expected_generation;
        ea_p <= expected_address; tok_p <= emb_token; ep_p <= emb_epoch; ca_p <= cfg_addr; cd_p <= cfg_data;
        bw_p[292:1] <= bw[292:1];
    end
    reg [292:0] bw_p;
    always @(posedge ck or negedge rs_q) if (!rs_q) bw_p[0] <= 1'b0; else bw_p[0] <= bw[0];
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin ev_p <= 4'd0; ss_p <= 1'b0; cw_p <= 1'b0; end
        else begin ev_p <= expected_valid; ss_p <= emb_start; cw_p <= cfg_we; end
    wire [3:0] wv_p = {es_p[864], es_p[576], es_p[288], es_p[0]};
    wire ev_now = (|ev_p) | (|wv_p);
    reg  ph1; reg [1:0] wv23, ev23;
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin ph1 <= 1'b0; wv23 <= 2'd0; ev23 <= 2'd0; end
        else begin ph1 <= ev_now && MUT != 2; wv23 <= wv_p[3:2]; ev23 <= ev_p[3:2]; end
    wire [1:0]   av, xv;
    wire [1:0]   lo = ph1 ? 2'd2 : 2'd0;
    wire [1:0]   hi = lo | 2'd1;
    wire c_pc = cw_p && cd_p[63:62] == 2'd0;
    wire c_bad = cw_p && (cd_p[63] || (cd_p[63:62] == 2'd0 && cd_p[61:18] != 44'd0));
    // ---- boot word: rides lane A's pc / data / address fields with its own valid BV (bit 783).  Boot is the
    //      exceptional init phase: the writer is idle by construction; a writer / expected event or the lanes-2/3
    //      edge on a boot edge latches fault and the WRITER keeps its fields (the boot word is dropped).
    wire bt, bt_x, use_b, ev_ph1;
    // ---- the edge word (field map: qkd_kv_es_fan_half) ----
    wire [255:0] db_s, da_s; wire [4:0] qb_s, qa_s, pb_s, pa_s;
    wire [782:0] hn;
    generate if (S32 == 0) begin : g_s0
    assign av = ph1 ? wv23 : wv_p[1:0];
    assign xv = ph1 ? ev23 : ev_p[1:0];
    assign bt   = bw_p[0] && !ev_now && !ph1;
    assign bt_x = bw_p[0] && (ev_now || ph1);
    assign use_b = (MUT == 1) ? bw_p[0] : bt;
    assign ev_ph1 = ev_now && ph1;
    if (PH1C == 0) begin : g_ph0
        assign db_s = es_p[288*hi + 1 +: 256]; assign da_s = es_p[288*lo + 1 +: 256];
        assign qb_s = epc_p[5*hi +: 5]; assign qa_s = epc_p[5*lo +: 5];
        assign pb_s = dpc_p[5*hi +: 5]; assign pa_s = dpc_p[5*lo +: 5];
    end else begin : g_ph1
        // copies 1..16 of ph1: identical D, clock and async clear (kept flops, ot_keep_regs)
        (* keep *) reg [15:0] ph1c;
        always @(posedge ck or negedge rs_q)
            if (!rs_q) ph1c <= 16'd0; else ph1c <= {16{ev_now && MUT != 2}};
        genvar gs;
        for (gs = 0; gs < 8; gs = gs + 1) begin : g_sl
            // hi = ph1 ? 3 : 1, lo = ph1 ? 2 : 0
            assign db_s[32*gs +: 32] = ph1c[gs]     ? es_p[865 + 32*gs +: 32] : es_p[289 + 32*gs +: 32];
            assign da_s[32*gs +: 32] = ph1c[8 + gs] ? es_p[577 + 32*gs +: 32] : es_p[  1 + 32*gs +: 32];
        end
        assign qb_s = ph1 ? epc_p[15 +: 5] : epc_p[5 +: 5]; assign qa_s = ph1 ? epc_p[10 +: 5] : epc_p[0 +: 5];
        assign pb_s = ph1 ? dpc_p[15 +: 5] : dpc_p[5 +: 5]; assign pa_s = ph1 ? dpc_p[10 +: 5] : dpc_p[0 +: 5];
    end
    assign hn = {cd_p[15:0], ca_p[2:0], ca_p[7:3], cd_p[17:16], c_pc,                 // CVL CRG CPC CST CV
                       ep_p, tok_p, ss_p,                                                    // EP TOK SS
                       ea_p, {eid_p, egen_p}, {id_p, gen_p}, es_p[286],                      // EAD EID CTX SV
                       use_b ? bw_p[36:8] : es_p[257 +: 29],                                 // AD
                       db_s, use_b ? bw_p[292:37] : da_s,                                    // DB DA
                       qb_s, qa_s, pb_s,                                                     // QB QA PB
                       use_b ? bw_p[7:3] : pa_s,                                             // PA
                       est_p, use_b ? bw_p[2:1] : dst_p, xv, av};                            // EST DST XV AV
    end else begin : g_s32
        localparam integer NG = 3, NP = 35, NU = 19;
        // ev_now copies: group g = ev_p / es lane valid pin flops copy g (identical D / clock / reset as ev_p / es_p)
        (* keep *) reg [4*NG-1:0] evc;
        (* keep *) reg [4*NG-1:0] wvc;
        always @(posedge ck) wvc <= {NG{es[864], es[576], es[288], es[0]}};
        always @(posedge ck or negedge rs_q) if (!rs_q) evc <= {4*NG{1'b0}}; else evc <= {NG{expected_valid}};
        wire [NG-1:0] evn;
        genvar g, j, k;
        for (g = 0; g < NG; g = g + 1) begin : g_ev
            assign evn[g] = (|evc[4*g +: 4]) | (|wvc[4*g +: 4]);
        end
        // ph1 copies (D = ev_now && MUT != 2 from the copy's group): 0..11 group 0, 12..23 group 1, 24..34 group 2
        (* keep *) reg [NP-1:0] p1c;
        wire [NP-1:0] p1d;
        for (j = 0; j < NP; j = j + 1) begin : g_p1d
            assign p1d[j] = evn[(j < 12) ? 0 : (j < 24) ? 1 : 2] && MUT != 2;
        end
        always @(posedge ck or negedge rs_q) if (!rs_q) p1c <= {NP{1'b0}}; else p1c <= p1d;
        // use_b one edge early: use_b' = bw_p[0]' && !ev_now' && !ph1' with bw_p[0]' = bw[0], ev_now' = |expected_valid |
        // |es lane valids, ph1' = ev_now && MUT != 2 (MUT 1: use_b = bw_p[0]).  Copies 0..9 group 1, 10..18 group 2.
        wire ub_base = bw[0] && !(|expected_valid) && !(es[864] | es[576] | es[288] | es[0]);
        (* keep *) reg [NU-1:0] ubc;
        wire [NU-1:0] ubd;
        for (k = 0; k < NU; k = k + 1) begin : g_ubd
            assign ubd[k] = (MUT == 1) ? bw[0] : (ub_base && !(evn[(k < 10) ? 1 : 2] && MUT != 2));
        end
        always @(posedge ck or negedge rs_q) if (!rs_q) ubc <= {NU{1'b0}}; else ubc <= ubd;
        assign use_b = ubc[NU-1];
        assign av = p1c[32] ? wv23 : wv_p[1:0];
        assign xv = p1c[32] ? ev23 : ev_p[1:0];
        assign bt   = bw_p[0] && !evn[0] && !p1c[32];
        assign bt_x = bw_p[0] && (evn[0] || p1c[32]);
        assign ev_ph1 = evn[0] && p1c[32];
        for (j = 0; j < 16; j = j + 1) begin : g_sl
            // hi = ph1 ? 3 : 1, lo = ph1 ? 2 : 0
            assign db_s[16*j +: 16] = p1c[j]      ? es_p[865 + 16*j +: 16] : es_p[289 + 16*j +: 16];
            assign da_s[16*j +: 16] = p1c[16 + j] ? es_p[577 + 16*j +: 16] : es_p[  1 + 16*j +: 16];
        end
        assign qb_s = p1c[33] ? epc_p[15 +: 5] : epc_p[5 +: 5]; assign qa_s = p1c[33] ? epc_p[10 +: 5] : epc_p[0 +: 5];
        assign pb_s = p1c[34] ? dpc_p[15 +: 5] : dpc_p[5 +: 5]; assign pa_s = p1c[34] ? dpc_p[10 +: 5] : dpc_p[0 +: 5];
        // the use_b-selected fields as one 292-bit vector {DA, AD, PA, DST}, 16 bits a copy
        wire [291:0] u_a = {bw_p[292:37], bw_p[36:8], bw_p[7:3], bw_p[2:1]};
        wire [291:0] u_b = {da_s, es_p[257 +: 29], pa_s, dst_p};
        wire [291:0] u_s;
        for (k = 0; k < NU; k = k + 1) begin : g_us
            localparam integer W = (16*k + 16 > 292) ? 292 - 16*k : 16;
            assign u_s[16*k +: W] = ubc[k] ? u_a[16*k +: W] : u_b[16*k +: W];
        end
        assign hn = {cd_p[15:0], ca_p[2:0], ca_p[7:3], cd_p[17:16], c_pc,                 // CVL CRG CPC CST CV
                     ep_p, tok_p, ss_p,                                                    // EP TOK SS
                     ea_p, {eid_p, egen_p}, {id_p, gen_p}, es_p[286],                      // EAD EID CTX SV
                     u_s[35:7],                                                            // AD
                     db_s, u_s[291:36],                                                    // DB DA
                     qb_s, qa_s, pb_s,                                                     // QB QA PB
                     u_s[6:2],                                                             // PA
                     est_p, u_s[1:0], xv, av};                                             // EST DST XV AV
    end endgenerate
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin h <= 784'd0; fault <= 1'b0; end
        else begin
            h <= {use_b, hn};
            if (ev_ph1 || c_bad || (bt_x && MUT != 1)) fault <= 1'b1;
        end
endmodule

// ===== die cfg (S32-B) =====
// KV-CTL3 10-20 (native32 census): S32 = 1 resets the configuration fields from EXPLICIT kept POR copies (no reliance on
// the synthesis load split, which left copy c1 at 44 loads on one 35-bit cell): copy f/2 resets ectl fields 2f/2f+1 (a, b,
// c: 30 flops), copy 16 + r/4 resets rst_dly words 4r..4r+3 (32 flops); same D ps[0], clock and async clear as ps[1], so
// every field resets and releases on the same edges as before.  The control state (we_q, next, sealed, fault, cap_q) stays
// on pr_n.  Write decode via KEPT predecode wires and write data from 4 KEPT copies of the data pin flops (<= 32 loads
// each).  S32 = 0: unchanged.
module qkd_kv_die_cfg_s32 #(parameter integer NRST = 43, parameter integer CAP = 0, parameter integer MUT = 0, parameter integer PCOPIES = 1,
                        parameter integer S32 = 0) (
    input  wire               ck, por_n,
    input  wire               cfg_we, input wire [7:0] cfg_addr, input wire [63:0] cfg_data,
    output reg  [32*5-1:0]    ectl_a_cfg, ectl_b_cfg, ectl_c_cfg,
    output reg  [NRST*8-1:0]  rst_dly,
    output wire               fused_program_capability,
    output reg                sealed, fault
);
    localparam integer NW = 32 + NRST + ((CAP != 0) ? 1 : 0);   // data words before the seal
    localparam [63:0] SEAL = 64'h514b5644_43464731;
    generate if (NRST < 1 || NW + 1 > 256) begin : g_bad
        initial $fatal(1, "qkd_kv_die_cfg: NRST %0d CAP %0d", NRST, CAP);
    end endgenerate
    // POR: two-flop synchronised release (async assert), as qkd_rst_region
    reg [1:0] ps;
    always @(posedge ck or negedge por_n) if (!por_n) ps <= 2'b00; else ps <= {ps[0], 1'b1};
    wire pr_n = ps[1];
    generate if (PCOPIES > 1) begin : g_pc
        (* keep *) reg [PCOPIES-2:0] pc_q;
        always @(posedge ck or negedge por_n) if (!por_n) pc_q <= {(PCOPIES-1){1'b0}}; else pc_q <= {(PCOPIES-1){ps[0]}};
        (* keep, ot_rst_split *) wire [PCOPIES-1:0] prv = {pc_q, ps[1]};
    end endgenerate
    // write port pin registers
    reg we_q; reg [7:0] a_q; reg [63:0] d_q;
    always @(posedge ck or negedge pr_n) if (!pr_n) we_q <= 1'b0; else we_q <= cfg_we;
    always @(posedge ck) begin a_q <= cfg_addr; d_q <= cfg_data; end
    reg [8:0] next;
    wire is_ectl = a_q < 8'd32;
    wire is_rst  = !is_ectl && a_q < 8'(32 + NRST);
    wire is_cap  = (CAP != 0) && a_q == 8'(32 + NRST);
    wire is_seal = a_q == NW[7:0];
    reg  cap_q;
    wire [7:0] r_ix = a_q - 8'd32 + ((MUT == 3) ? 8'd1 : 8'd0);
    wire bad = sealed || ({1'b0, a_q} != next) ||
               (MUT != 2 && ((is_ectl && d_q[63:15] != 0) || (is_rst && d_q[63:8] != 0) || (is_cap && d_q[63:1] != 0))) ||
               (is_seal && (d_q != SEAL || next != NW[8:0])) || (!is_ectl && !is_rst && !is_cap && !is_seal);
    integer i;
    generate if (S32 == 0) begin : g_s0
    always @(posedge ck or negedge pr_n) begin
        if (!pr_n) begin
            ectl_a_cfg <= 0; ectl_b_cfg <= 0; ectl_c_cfg <= 0; rst_dly <= 0; cap_q <= 1'b0;
            sealed <= 1'b0; fault <= 1'b0; next <= 9'd0;
        end else if (we_q) begin
            if (bad || fault) fault <= 1'b1;
            else begin
                next <= next + 9'd1;
                if (is_ectl) begin
                    ectl_a_cfg[5*a_q[4:0] +: 5] <= d_q[4:0];
                    ectl_b_cfg[5*a_q[4:0] +: 5] <= (MUT == 1) ? d_q[14:10] : d_q[9:5];
                    ectl_c_cfg[5*a_q[4:0] +: 5] <= (MUT == 1) ? d_q[9:5] : d_q[14:10];
                end
                if (is_rst && r_ix < NRST) rst_dly[8*r_ix +: 8] <= d_q[7:0];
                if (is_cap) cap_q <= (MUT == 4) ? d_q[1] : d_q[0];
                if (is_seal) sealed <= 1'b1;
            end
        end
    end
    end else begin : g_s32
        localparam integer KE = 16, KR = (NRST + 3) / 4;
        (* keep *) reg [KE+KR-1:0] rcp;
        always @(posedge ck or negedge por_n) if (!por_n) rcp <= {(KE+KR){1'b0}}; else rcp <= {(KE+KR){ps[0]}};
        wire wr = we_q && !(bad || fault);
        // decode and data fan-out (ABC would fold a flat decode into every hold mux: 190+ loads on wr / a_q bits): KEPT
        // predecode wires (ABC boundaries) phi = {wr, is_ectl, a_q[4:3]}, plo = a_q[2:0] one-hot, fe = phi & plo (30
        // hold-mux loads each); rst rows likewise (rhi = {wr, is_rst, r_ix[5:3]}, rlo = r_ix[2:0]); write data from 4 KEPT
        // copies of d_q[14:0] (ectl fields 0..15 / 16..31, rst rows 0..21 / 22..)
        (* keep *) wire [3:0] phi; (* keep *) wire [7:0] plo, rlo; (* keep *) wire [5:0] rhi;
        (* keep *) wire [31:0] fe; (* keep *) wire [NRST-1:0] fr;
        (* keep *) reg [14:0] dqc0, dqc1, dqc2, dqc3;
        always @(posedge ck) begin dqc0 <= cfg_data[14:0]; dqc1 <= cfg_data[14:0]; dqc2 <= cfg_data[14:0]; dqc3 <= cfg_data[14:0]; end
        genvar q;
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
        genvar f, r;
        for (f = 0; f < 32; f = f + 1) begin : g_ef
            wire [14:0] dq = (f < 16) ? dqc0 : dqc1;
            wire [14:0] qf;
            qkd_kv_die_cfg_s32_fld #(.W(15)) u_f (.ck(ck), .rn(rcp[f/2]), .en(fe[f]),
                .d({(MUT == 1) ? dq[9:5] : dq[14:10], (MUT == 1) ? dq[14:10] : dq[9:5], dq[4:0]}), .q(qf));
            always @* begin ectl_a_cfg[5*f +: 5] = qf[4:0]; ectl_b_cfg[5*f +: 5] = qf[9:5]; ectl_c_cfg[5*f +: 5] = qf[14:10]; end
        end
        for (r = 0; r < NRST; r = r + 1) begin : g_rf
            wire [7:0] qr;
            qkd_kv_die_cfg_s32_fld #(.W(8)) u_r (.ck(ck), .rn(rcp[KE + r/4]), .en(fr[r]), .d((r < 22) ? dqc2[7:0] : dqc3[7:0]), .q(qr));
            always @* rst_dly[8*r +: 8] = qr;
        end
    end endgenerate
    assign fused_program_capability = cap_q && ((MUT == 5) || sealed);
endmodule

// KV-CTL3 10-20: one configuration field of qkd_kv_die_cfg S32 1 (hold register, async clear from its POR copy).  A kept
// hierarchy leaf so synthesis cannot fold the field's write decode into every bit's hold mux (en = <= 2 x W loads).
(* keep_hierarchy *)
module qkd_kv_die_cfg_s32_fld #(parameter integer W = 15) (
    input wire ck, rn, en, input wire [W-1:0] d, output reg [W-1:0] q
);
    always @(posedge ck or negedge rn) if (!rn) q <= {W{1'b0}}; else if (en) q <= d;
endmodule

// ===== ownership calendar =====
// KV-CTL3 10-20 (PRE-GATE NATIVE CENSUS, no driver > 32 mapped loads): S32 = 1 (MU only) writes the three root banks
// ({root, root - k, guard} = 96 / 96 / 64 held bits, one shared write enable each: mu6c census 181 / 148 / 119 loads) in
// 16-bit SLICES, each slice's enable ANDed with its own KEPT copy of the reset pin flop (rs_s, identical D = rst_n, not a
// split family), so no two slices share an enable gate; rs_s == rn on every edge (the banks reset on rn): same function,
// 0 added edges.  S32 = 0 = unchanged.
module qkd_static_kv_ownership_calendar_mu_s32 #(parameter integer MUT = 0, parameter integer MU = 0, parameter integer PIPE = 0, parameter integer SAFE = 0,
    parameter integer RCOPIES = 1, parameter integer S32 = 0) (
    input wire ck, rst_n,
    input wire cfg_we, input wire [1:0] cfg_addr, input wire [31:0] cfg_data,
    input wire go,
    input wire host_quiet, upstream_quiet,
    input wire [31:0] group_drained, group_fault,
    output wire native_mode, ownership_valid, native_reserved,
    output wire active, done, configured,
    output wire [31:0] cycle,
    output wire fault, output wire [7:0] fault_code
);
generate if (MU == 0) begin : g_plain
    qkd_static_kv_ownership_calendar #(.MUT(MUT), .PIPE(PIPE)) u_plain (.ck(ck), .rst_n(rst_n), .cfg_we(cfg_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .go(go), .host_quiet(host_quiet), .upstream_quiet(upstream_quiet),
        .group_drained(group_drained), .group_fault(group_fault), .native_mode(native_mode),
        .ownership_valid(ownership_valid), .native_reserved(native_reserved), .active(active), .done(done),
        .configured(configured), .cycle(cycle), .fault(fault), .fault_code(fault_code));
end else begin : g_mu
    (* keep *) reg rn;
    always @(posedge ck) rn <= rst_n;
    if (RCOPIES > 1) begin : g_rc
        (* keep *) reg [RCOPIES-2:0] rc_q;
        always @(posedge ck) rc_q <= {(RCOPIES-1){rst_n}};
        (* keep, ot_rst_split *) wire [RCOPIES-1:0] rnv = {rc_q, rn};
    end
    reg we_q, go_q, host_q, upstream_q;
    reg [1:0] addr_q; reg [31:0] data_q, drained_q, fault_q;
    always @(posedge ck) begin
        addr_q <= cfg_addr; data_q <= cfg_data;
        drained_q <= group_drained; fault_q <= group_fault;
    end
    always @(posedge ck or negedge rn) begin
        if (!rn) begin we_q <= 0; go_q <= 0; host_q <= 0; upstream_q <= 0; end
        else begin we_q <= cfg_we; go_q <= go; host_q <= host_quiet; upstream_q <= upstream_quiet; end
    end
    reg nm, ov, nr, ac, dn, cf, ft; reg [31:0] cy; reg [7:0] fc;
    reg [31:0] enter_root, leave_root, deadline_root;
    reg [2:0] written;
    reg [31:0] enter_m, leave_m, deadline_m;                   // PIPE: root - k, captured with the root word
    reg drained_all_q;                                         // PIPE: &drained_q, one edge later
    always @(posedge ck) drained_all_q <= &drained_q;
    wire drained_ok = (PIPE != 0) ? drained_all_q : (&drained_q);
    wire rearm = go_q && ac && MUT != 7;                       // a later user's token start re-arms the window
    wire enter_now = ac && !rearm && cy == ((PIPE != 0) ? enter_m : enter_root - ((MUT == 1) ? 32'd2 : 32'd1));
    wire enter_tr = enter_now && (!nm || MUT == 6);            // host -> native transition only
    wire leave_now = ac && !rearm && cy == ((PIPE != 0) ? leave_m : leave_root - 32'd1);
    wire deadline_now = cy == ((PIPE != 0) ? deadline_m : deadline_root - 32'd1);
    // SAFE guard forecast is sampled one edge before the ownership boundary.
    // Four KEPT registered stop copies isolate root banks and control enables.
    reg [31:0] enter_guard, leave_guard;
    wire guard_enter = SAFE ? (ac && !rearm && !nm && cy == enter_guard) : enter_tr;
    wire guard_leave = SAFE ? (ac && !rearm && cy == leave_guard) : leave_now;
    reg [7:0] bad;
    (* keep = 1 *) reg [7:0] bad_q;
    (* keep = 1, dont_touch = 1 *) reg [3:0] halt_q;
    wire [7:0] bad_use = SAFE ? bad_q : bad;
    wire stop_ctl = SAFE ? halt_q[3] : (ft || (|bad));
    wire [3:0] stop_bank = SAFE ? halt_q : {4{ft || (|bad)}};
    always @(posedge ck or negedge rn) begin
        if (!rn) begin bad_q <= 0; halt_q <= 0; end
        else begin
            bad_q <= bad;
            halt_q[0] <= ft || (|bad);
            halt_q[1] <= ft || (|bad);
            halt_q[2] <= ft || (|bad);
            halt_q[3] <= ft || (|bad);
        end
    end
    always @* begin
        bad = 0;
        if (we_q && (cf || ac || go_q)) bad[0] = 1;
        if (we_q && addr_q == 3 &&
            (written != 3'b111 || data_q != 32'h514b564d || enter_root < 3 ||
             leave_root <= enter_root || deadline_root <= leave_root)) bad[1] = 1;
        if (go_q && (!cf || we_q || (ac && MUT == 5))) bad[2] = 1;
        if (guard_enter && (!host_q || !upstream_q || !drained_ok)) bad[3] = 1;
        if (guard_leave && MUT != 2 && (!upstream_q || !drained_ok)) bad[4] = 1;
        if ((|fault_q) && MUT != 3) bad[5] = 1;
    end
    always @(posedge ck or negedge rn) begin
        if (!rn) begin
            nm <= 0; ov <= 0; nr <= 0; ac <= 0;
            dn <= 0; cf <= 0; cy <= 0; ft <= 0; fc <= 0;
            written <= 0;
        end else if (stop_ctl) begin
            ft <= 1; fc <= fc | bad_use;
            ov <= 0; nr <= 1; ac <= 0; dn <= 0;
        end else begin
            dn <= 0;
            if (we_q) case (addr_q)
                0: written[0] <= 1;
                1: written[1] <= 1;
                2: written[2] <= 1;
                3: begin cf <= 1; ov <= 1; end
            endcase
            if (ac) begin
                cy <= cy + 1;
                if (enter_now) nm <= 1;
                if (leave_now) nm <= 0;
                if (!rearm && deadline_now) begin ac <= 0; dn <= 1; nr <= 0; end
            end
            if (go_q && !(ac && MUT == 7)) begin
                cy <= 0; ac <= 1; nr <= 1;
                if (!ac) nm <= 0;                              // a fresh window starts in host mode (the original)
            end
        end
    end
    if (S32 == 0) begin : g_bank
        always @(posedge ck or negedge rn) begin
            if (!rn) begin enter_root <= 0; enter_m <= 0; enter_guard <= 0; end
            else if (!stop_bank[0] && we_q && addr_q == 0) begin
                enter_root <= data_q;
                enter_m <= data_q - ((MUT == 1) ? 32'd2 : 32'd1);
                enter_guard <= data_q - 32'd2;
            end
        end
        always @(posedge ck or negedge rn) begin
            if (!rn) begin leave_root <= 0; leave_m <= 0; leave_guard <= 0; end
            else if (!stop_bank[1] && we_q && addr_q == 1) begin
                leave_root <= data_q; leave_m <= data_q - 32'd1;
                leave_guard <= data_q - 32'd2;
            end
        end
        always @(posedge ck or negedge rn) begin
            if (!rn) begin deadline_root <= 0; deadline_m <= 0; end
            else if (!stop_bank[2] && we_q && addr_q == 2) begin
                deadline_root <= data_q; deadline_m <= data_q - 32'd1;
            end
        end
    end else begin : g_bank_s32
        (* keep *) reg [15:0] rs_s;
        always @(posedge ck) rs_s <= {16{rst_n}};
        wire en0 = !stop_bank[0] && we_q && addr_q == 0;
        wire en1 = !stop_bank[1] && we_q && addr_q == 1;
        wire en2 = !stop_bank[2] && we_q && addr_q == 2;
        wire [95:0] s0 = {data_q - 32'd2, data_q - ((MUT == 1) ? 32'd2 : 32'd1), data_q};
        wire [95:0] s1 = {data_q - 32'd2, data_q - 32'd1, data_q};
        wire [63:0] s2 = {data_q - 32'd1, data_q};
        reg [95:0] b0, b1; reg [63:0] b2; wire [95:0] n0, n1; wire [63:0] n2;
        genvar gs;
        // ot_s32_sel leaves (rtl/lib/ot_s32_cells.sv): kept hierarchy, so the bank enable cannot be folded into every bit
        for (gs = 0; gs < 6; gs = gs + 1) begin : g_s01
            ot_s32_sel #(.W(16)) u_0 (.s(en0 && rs_s[gs]), .a(s0[16*gs +: 16]), .b(b0[16*gs +: 16]), .y(n0[16*gs +: 16]));
            ot_s32_sel #(.W(16)) u_1 (.s(en1 && rs_s[6+gs]), .a(s1[16*gs +: 16]), .b(b1[16*gs +: 16]), .y(n1[16*gs +: 16]));
        end
        for (gs = 0; gs < 4; gs = gs + 1) begin : g_s2
            ot_s32_sel #(.W(16)) u_2 (.s(en2 && rs_s[12+gs]), .a(s2[16*gs +: 16]), .b(b2[16*gs +: 16]), .y(n2[16*gs +: 16]));
        end
        always @(posedge ck or negedge rn) if (!rn) begin b0 <= 0; b1 <= 0; b2 <= 0; end else begin b0 <= n0; b1 <= n1; b2 <= n2; end
        always @* begin
            enter_root = b0[31:0]; enter_m = b0[63:32]; enter_guard = b0[95:64];
            leave_root = b1[31:0]; leave_m = b1[63:32]; leave_guard = b1[95:64];
            deadline_root = b2[31:0]; deadline_m = b2[63:32];
        end
    end
    assign native_mode = nm; assign ownership_valid = ov; assign native_reserved = nr;
    assign active = ac; assign done = dn; assign configured = cf; assign cycle = cy;
    assign fault = ft; assign fault_code = fc;
end endgenerate
endmodule
