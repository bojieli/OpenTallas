`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// KV-CTL3 S32-A 2026-10-20 (SAFE checklist item 3 / PRE-GATE NATIVE CENSUS "no driver > 32 loads"): the writer role and
// the writer programme of the KV control tile (qkd_kvs_ctl u_wrn / u_wprg) rebuilt so every driver stays <= 32 loads in
// the ASAP7 mapped netlist (counted through BUF/INV; a hold / 2:1 select costs 2 loads per bit -> <= 14 bits a copy).
// mu6c census (results/arch/kv_ctl3_1020/cls.txt): writer hi_slot 2,357 loads, lo-slot 1,027, half / cohort enables
// 112 / 110, reset relay sync stage 132; wprg ld 325, start-accept select 145 (kvi pins + cycle), sh0..3 enables 33-90.
//
// NEW modules (the shared sources qkd_kv_static_writer.sv / ot_qkd_kv_static_writer_native.sv / qkd_kv_native_programme.sv
// / qkd_kv_static_writer_native_mu.sv are bound by closed and in-flight views and stay byte-identical):
//   qkd_kv_static_writer_s32          = qkd_kv_static_writer RST_RELAY 1 (MUT 0 only) with KEPT select copies
//   qkd_kv_static_writer_native_mu_s32= qkd_kv_static_writer_native_mu around it (+ copy ports)
//   qkd_kv_native_programme_s32       = qkd_kv_native_programme (SRAM 0/1, CTLSRAM) with KEPT copies + copy outputs
// Same function, cycle for cycle and bit for bit, on every output (tb_kv_ctl_s32_a lockstep); 0 added edges.
//
// Structure: a high-fanout select that was a gate of pin flops (hi_slot = slot & ix[0]) becomes a family of KEPT flops
// hs*[k] <= compiled_word_slot & compiled_word_index[0] registered on the SAME edge as slot / ix (identical value every
// cycle; reset like slot).  The D side stays <= 32: the programme exports NC KEPT copies of its word_slot / word_index
// flops (compiled_word_slot_c / compiled_word_index_c, identical D / reset); copy j's AND feeds every NC-th family flop
// (distinct inputs, so neither opt_merge nor ABC can fold them back).  Each family flop selects one <= 14-bit slice.
// Reset: the relay sync stage 2 is NC_SQ KEPT copies; the region relay is a STRIDED kept family (* ot_rst_split = 12 *)
// rcv[c*12 + r] (region r's copies share one D = sq1[r % SQ]), split by physical/common_flow/ot_rst_copies.py.  Release
// = 3 edges after rst_n, exactly ot_rst_relay #(12, 2, 1, COPIES).
// ---------------------------------------------------------------------------------------------------------------------
module qkd_kv_static_writer_s32 #(parameter integer MUT = 0, parameter integer VMAP = 0, parameter integer NC = 4,
    parameter integer RST_COPIES = 12, parameter integer SQ = 6) (
    input wire ck, rst_n,
    input wire word_valid, input wire [10:0] word_tag,
    input wire [511:0] word_data,
    input wire [58:0] word_identity, input wire [1:0] word_generation,
    input wire compiled_word_slot, input wire [1:0] compiled_word_index,
    input wire [NC-1:0] compiled_word_slot_c, input wire [2*NC-1:0] compiled_word_index_c,
    input wire [58:0] compiled_identity, input wire [1:0] compiled_generation,
    output wire [4*288-1:0] es,
    output wire [4*5-1:0] dest_pc, output wire [1:0] dest_stack,
    output wire [58:0] identity, output wire [1:0] generation,
    output reg [3:0] expected_valid,
    output wire [4*5-1:0] expected_pc, output wire [1:0] expected_stack,
    output wire [58:0] expected_identity, output wire [1:0] expected_generation,
    output wire [28:0] expected_address,
    output reg fault, output reg [7:0] fault_code
);
    localparam integer SW = 14;               // bits per select copy (2 loads a bit -> <= 28 loads)
    localparam integer RG = 12;               // reset regions (as qkd_kv_static_writer)
    // ---- reset relay (ot_rst_relay REGIONS 12, SYNC 2, TREE 1, COPIES RST_COPIES; release 3 edges) ----
    (* async_reg = "true" *) reg sync0;
    always @(posedge ck or negedge rst_n) if (!rst_n) sync0 <= 1'b0; else sync0 <= 1'b1;
    (* keep = "true", dont_touch = "true" *) reg [SQ-1:0] sq1;
    always @(posedge ck or negedge rst_n) if (!rst_n) sq1 <= {SQ{1'b0}}; else sq1 <= {SQ{sync0}};
    wire [RG*RST_COPIES-1:0] rcv_d;
    genvar gi;
    generate for (gi = 0; gi < RG*RST_COPIES; gi = gi + 1) begin : g_rd
        assign rcv_d[gi] = sq1[(gi % RG) % SQ];
    end endgenerate
    (* keep = "true", dont_touch = "true", ot_rst_split = 12 *) reg [RG*RST_COPIES-1:0] rcv;
    always @(posedge ck or negedge rst_n) if (!rst_n) rcv <= {(RG*RST_COPIES){1'b0}}; else rcv <= rcv_d;
    wire [RG-1:0] rr = rcv[RG-1:0];

    function automatic [2:0] group_of(input [2:0] e);
        case(e) 0:group_of=2;1:group_of=3;2:group_of=4;3:group_of=5;
                4:group_of=0;5:group_of=1;6:group_of=6;7:group_of=7;endcase
    endfunction
    // ---- face capture flops (as the original) ----
    (* keep *) reg wv, slot;
    (* keep *) reg [10:0] wt;
    (* keep *) reg [511:0] wd;
    (* keep *) reg [58:0] wi, ci;
    (* keep *) reg [1:0] wg, cg, ix;
    always @(posedge ck) begin
        wt <= word_tag; wd <= word_data; wi <= word_identity;
        wg <= word_generation; ci <= compiled_identity;
        cg <= compiled_generation; ix <= compiled_word_index;
    end
    // ---- select-copy D terms: copy group j = AND of the programme's kept copy j ----
    wire [NC-1:0] i0c, i1c;
    generate for (gi = 0; gi < NC; gi = gi + 1) begin : g_ic
        assign i0c[gi] = compiled_word_index_c[2*gi]; assign i1c[gi] = compiled_word_index_c[2*gi+1];
    end endgenerate
    wire [NC-1:0] hsD = compiled_word_slot_c & i0c;           // next hi_slot  (slot & ix[0])
    wire [NC-1:0] lsD = compiled_word_slot_c & ~i0c;          // next lo slot  (slot & !ix[0])
    wire [NC-1:0] chD = compiled_word_slot_c & ~i0c & ~i1c;   // next cohort   (slot & ix == 0)

    reg [1:0] next_index;
    reg half_live;
    wire [12:0] pos = wi[18:6];
    wire [5:0] stage = wi[42:37];
    wire [5:0] layer = stage - 6'd1;
    wire kind = wt[2];
    wire [18:0] row = 19'd64 + {13'd0, layer};
    wire vm = (VMAP != 0) && kind;
    wire [2:0] low3 = vm ? pos[3:1] : pos[5:3];
    wire [2:0] grp = vm ? {pos[5:4], pos[0]} : pos[2:0];
    wire [4:0] bank = {kind, 1'b0, pos[6], low3[1:0]};
    wire [4:0] column = {pos[12:9], low3[2]};
    reg [511:0] half_data;
    wire [1023:0] assembled_row = {wd, half_data};
    wire [2:0] expected_word_kind = {ix[1], 1'b0, ix[0]};
    // registered state vectors (field maps below)
    localparam integer WC0 = 61, WL0 = 63, WR0 = 83, WR1 = 142;
    reg [WC0-1:0] c0;      // {cohort_identity 59, cohort_generation 2}
    reg [WL0-1:0] l0;      // {half_identity 59, half_generation 2, half_index 2}
    reg [WR0-1:0] r0;      // {dest_pc 20, dest_stack 2, identity 59, generation 2}
    reg [WR1-1:0] r1;      // {expected_stack 2, expected_identity 59, expected_generation 2, expected_address 29,
                           //  expected_pc 20, es_sv 1, es_addr 29}
    wire [58:0] cohort_identity = c0[60:2]; wire [1:0] cohort_generation = c0[1:0];
    wire [58:0] half_identity = l0[62:4]; wire [1:0] half_generation = l0[3:2], half_index = l0[1:0];
    assign dest_pc = r0[82:63]; assign dest_stack = r0[62:61]; assign identity = r0[60:2]; assign generation = r0[1:0];
    assign expected_stack = r1[141:140]; assign expected_identity = r1[139:81]; assign expected_generation = r1[80:79];
    assign expected_address = r1[78:50]; assign expected_pc = r1[49:30];
    wire es_sv = r1[29]; wire [28:0] es_addr = r1[28:0];

    wire identity_ok = wi == ci && wg == cg && stage >= 1 && stage <= 36 && wi[5:0] == 0;
    wire header_ok = wt[10:8] == 3'b010 && wt[7:3] == 0 && wt[2:0] == expected_word_kind;
    wire pair_ok = !ix[0] ? !half_live : half_live && half_index == (ix - 2'd1) &&
                   half_identity == wi && half_generation == wg;
    wire program_ok = ix == next_index && (ix == 0 || (ci == cohort_identity && cg == cohort_generation));
    wire good = slot && wv && identity_ok && header_ok && pair_ok && program_ok;
    wire cvm = (VMAP != 0) && ix[1];
    wire [2:0] cgrp = cvm ? {ci[11:10], ci[6]} : ci[8:6];
    wire [2:0] gg = group_of(grp), cgg = group_of(cgrp);
    wire [WR0-1:0] r0_d = {gg, 2'd3, gg, 2'd2, gg, 2'd1, gg, 2'd0, pos[8:7], wi, wg};
    wire [WR1-1:0] r1_d = {ci[14:13], ci, cg,
                           19'd64 + {13'd0,(ci[42:37]-6'd1)}, ix[1], 1'b0, ci[12], cvm ? ci[8:7] : ci[10:9], ci[18:15],
                           cvm ? ci[9] : ci[11],
                           cgg, 2'd3, cgg, 2'd2, cgg, 2'd1, cgg, 2'd0, 1'b1, bank, column, row};
    wire [WL0-1:0] l0_d = {wi, wg, ix};
    wire [WC0-1:0] c0_d = {ci, cg};

    // ---- region 0: capture valids, programme / pairing state, write identity ----
    localparam integer NR0 = (WR0 + SW - 1) / SW, NL0 = (WL0 + SW - 1) / SW, NC0 = (WC0 + SW - 1) / SW;
    (* keep *) reg [NR0:0] hs_r0;       // [NR0] = half_live clear
    (* keep *) reg [NL0-1:0] lsg;
    (* keep *) reg [NC0-1:0] ch;
    generate
        for (gi = 0; gi <= NR0; gi = gi + 1) begin : g_hs0
            always @(posedge ck or negedge rr[0]) if (!rr[0]) hs_r0[gi] <= 1'b0; else hs_r0[gi] <= hsD[gi % NC];
        end
        for (gi = 0; gi < NL0; gi = gi + 1) begin : g_ls0
            always @(posedge ck or negedge rr[0]) if (!rr[0]) lsg[gi] <= 1'b0; else lsg[gi] <= lsD[gi % NC];
        end
        for (gi = 0; gi < NC0; gi = gi + 1) begin : g_ch0
            always @(posedge ck or negedge rr[0]) if (!rr[0]) ch[gi] <= 1'b0; else ch[gi] <= chD[gi % NC];
        end
    endgenerate
    always @(posedge ck or negedge rr[0]) begin
        if (!rr[0]) begin
            wv <= 0; slot <= 0; next_index <= 0; half_live <= 0;
        end else begin
            wv <= word_valid; slot <= compiled_word_slot;
            if (slot) next_index <= next_index + 2'd1;
            if (lsg[0] && good) half_live <= 1;
            if (hs_r0[NR0]) half_live <= 0;
        end
    end
    generate
        for (gi = 0; gi < NC0; gi = gi + 1) begin : g_c0
            localparam integer LO = gi * SW, W = (WC0 - LO < SW) ? WC0 - LO : SW;
            always @(posedge ck or negedge rr[0]) if (!rr[0]) c0[LO +: W] <= 0; else if (ch[gi]) c0[LO +: W] <= c0_d[LO +: W];
        end
        for (gi = 0; gi < NL0; gi = gi + 1) begin : g_l0
            localparam integer LO = gi * SW, W = (WL0 - LO < SW) ? WL0 - LO : SW;
            always @(posedge ck or negedge rr[0]) if (!rr[0]) l0[LO +: W] <= 0; else if (lsg[gi] && good) l0[LO +: W] <= l0_d[LO +: W];
        end
        for (gi = 0; gi < NR0; gi = gi + 1) begin : g_r0
            localparam integer LO = gi * SW, W = (WR0 - LO < SW) ? WR0 - LO : SW;
            always @(posedge ck or negedge rr[0]) if (!rr[0]) r0[LO +: W] <= 0; else if (hs_r0[gi]) r0[LO +: W] <= r0_d[LO +: W];
        end
    endgenerate

    // ---- region 1: faults, expected descriptor, shared es address / constant fields ----
    localparam integer NR1 = (WR1 + SW - 1) / SW;
    (* keep *) reg [NR1:0] hs_r1;       // [NR1] = expected_valid
    generate
        for (gi = 0; gi <= NR1; gi = gi + 1) begin : g_hs1
            always @(posedge ck or negedge rr[1]) if (!rr[1]) hs_r1[gi] <= 1'b0; else hs_r1[gi] <= hsD[gi % NC];
        end
        for (gi = 0; gi < NR1; gi = gi + 1) begin : g_r1
            localparam integer LO = gi * SW, W = (WR1 - LO < SW) ? WR1 - LO : SW;
            always @(posedge ck or negedge rr[1]) if (!rr[1]) r1[LO +: W] <= 0; else if (hs_r1[gi]) r1[LO +: W] <= r1_d[LO +: W];
        end
    endgenerate
    always @(posedge ck or negedge rr[1]) begin
        if (!rr[1]) begin
            expected_valid <= 0; fault <= 0; fault_code <= 0;
        end else begin
            expected_valid <= {4{hs_r1[NR1]}};
            if (slot && !program_ok) begin fault <= 1; fault_code[4] <= 1; end
            if (wv != slot) begin fault <= 1; fault_code[0] <= 1; end
            if (slot && !identity_ok) begin fault <= 1; fault_code[1] <= 1; end
            if (slot && wv && !header_ok) begin fault <= 1; fault_code[2] <= 1; end
            if (slot && !pair_ok) begin fault <= 1; fault_code[3] <= 1; end
        end
    end

    // ---- regions 2/3: low-half payload, captured on the compiled lo slot ----
    localparam integer NHD = (256 + SW - 1) / SW;
    genvar h, k;
    generate
        for (h = 0; h < 2; h = h + 1) begin : g_half
            (* keep *) reg [NHD-1:0] ls_h;
            for (k = 0; k < NHD; k = k + 1) begin : g_s
                localparam integer LO = k * SW, W = (256 - LO < SW) ? 256 - LO : SW;
                always @(posedge ck or negedge rr[2+h]) if (!rr[2+h]) ls_h[k] <= 1'b0; else ls_h[k] <= lsD[(h * NHD + k) % NC];
                always @(posedge ck or negedge rr[2+h])
                    if (!rr[2+h]) half_data[256*h + LO +: W] <= 0;
                    else if (ls_h[k]) half_data[256*h + LO +: W] <= wd[256*h + LO +: W];
            end
        end
    endgenerate

    // ---- regions 4..11: es lane q, rr[4+2q] = data[127:0] + w_v, rr[5+2q] = data[255:128] ----
    localparam integer NES = (128 + SW - 1) / SW;
    genvar q;
    generate
        for (q = 0; q < 4; q = q + 1) begin : g_lane
            reg [255:0] es_data;
            reg es_wv;
            (* keep *) reg [NES-1:0] hs_lo, hs_hi;
            for (k = 0; k < NES; k = k + 1) begin : g_s
                localparam integer LO = k * SW, W = (128 - LO < SW) ? 128 - LO : SW;
                always @(posedge ck or negedge rr[4+2*q]) if (!rr[4+2*q]) hs_lo[k] <= 1'b0; else hs_lo[k] <= hsD[k % NC];
                always @(posedge ck or negedge rr[5+2*q]) if (!rr[5+2*q]) hs_hi[k] <= 1'b0; else hs_hi[k] <= hsD[(k + 1) % NC];
                always @(posedge ck or negedge rr[4+2*q])
                    if (!rr[4+2*q]) es_data[LO +: W] <= 0;
                    else if (hs_lo[k]) es_data[LO +: W] <= assembled_row[256*q + LO +: W];
                always @(posedge ck or negedge rr[5+2*q])
                    if (!rr[5+2*q]) es_data[128 + LO +: W] <= 0;
                    else if (hs_hi[k]) es_data[128 + LO +: W] <= assembled_row[256*q + 128 + LO +: W];
            end
            always @(posedge ck or negedge rr[4+2*q]) if (!rr[4+2*q]) es_wv <= 0; else es_wv <= hs_lo[0] && good;
            assign es[288*q +: 288] = {es_sv, es_sv, es_addr, es_data, es_wv};
        end
    endgenerate

`ifndef SYNTHESIS
    initial begin
        if (MUT != 0) $error("qkd_kv_static_writer_s32: MUT 0 only (mutants live in the S32 lockstep runner)");
        if (NC < 1 || SQ < 1 || RST_COPIES < 1) $error("qkd_kv_static_writer_s32: NC / SQ / RST_COPIES >= 1");
    end
`endif
endmodule

// qkd_kv_static_writer_native_mu (MU-ADOPT-KV per-user KV row glue) around the S32 writer; + the copy ports.
module qkd_kv_static_writer_native_mu_s32 #(parameter integer MUT = 0, parameter integer VMAP = 0, parameter integer MU = 0,
    parameter integer NC = 4, parameter integer RST_COPIES = 12) (
    input wire ck, rst_n,
    input wire word_valid, input wire [10:0] word_tag,
    input wire [511:0] word_data,
    input wire [58:0] word_identity, input wire [1:0] word_generation,
    input wire compiled_word_slot, input wire [1:0] compiled_word_index,
    input wire [NC-1:0] compiled_word_slot_c, input wire [2*NC-1:0] compiled_word_index_c,
    input wire [58:0] compiled_identity, input wire [1:0] compiled_generation,
    output wire [4*288-1:0] es,
    output wire [4*5-1:0] dest_pc, output wire [1:0] dest_stack,
    output wire [58:0] identity, output wire [1:0] generation,
    output wire [3:0] expected_valid,
    output wire [4*5-1:0] expected_pc, output wire [1:0] expected_stack,
    output wire [58:0] expected_identity, output wire [1:0] expected_generation,
    output wire [28:0] expected_address,
    output wire fault, output wire [7:0] fault_code
);
    wire [4*288-1:0] es_w;
    wire [28:0] xa_w;
    wire f_w;
    wire [7:0] fc_w;
    qkd_kv_static_writer_s32 #(.MUT(MUT), .VMAP(VMAP), .NC(NC), .RST_COPIES(RST_COPIES)) u_writer (
        .ck(ck), .rst_n(rst_n), .word_valid(word_valid), .word_tag(word_tag), .word_data(word_data),
        .word_identity(word_identity), .word_generation(word_generation), .compiled_word_slot(compiled_word_slot),
        .compiled_word_index(compiled_word_index), .compiled_word_slot_c(compiled_word_slot_c),
        .compiled_word_index_c(compiled_word_index_c), .compiled_identity(compiled_identity),
        .compiled_generation(compiled_generation), .es(es_w), .dest_pc(dest_pc), .dest_stack(dest_stack),
        .identity(identity), .generation(generation), .expected_valid(expected_valid), .expected_pc(expected_pc),
        .expected_stack(expected_stack), .expected_identity(expected_identity),
        .expected_generation(expected_generation), .expected_address(xa_w), .fault(f_w), .fault_code(fc_w));
    wire rf_es, rf_xa;
    wire [4*288-1:0] es_unused;
    wire [28:0] xa_unused;
    qkd_kv_mu_wrow #(.MU(MU), .NL(4)) u_mu_es (.user(identity[44:43]), .es_i(es_w), .xa_i(xa_w),
        .es_o(es), .xa_o(xa_unused), .range_fault(rf_es));
    qkd_kv_mu_wrow #(.MU(MU), .NL(4)) u_mu_xa (.user(expected_identity[44:43]), .es_i(es_w), .xa_i(xa_w),
        .es_o(es_unused), .xa_o(expected_address), .range_fault(rf_xa));
    reg rf_q;
    always @(posedge ck or negedge rst_n) if (!rst_n) rf_q <= 1'b0; else if (rf_es) rf_q <= 1'b1;
    assign fault = f_w | rf_q;
    assign fault_code = {fc_w[7] | rf_q, fc_w[6:0]};
endmodule

// qkd_kv_native_programme (writer-only fixed programme, KV-GRP-CTL/MU5 SRAM / KV-SRAM-CTL CTLSRAM forms) with KEPT
// copies; every output equal on every edge.  S32 changes (see the header):
//   ld          -> NLD KEPT copies ldc (each loads one <= 14-bit slice of {stop_q, t3, t2, t1, t0} on the ld edge);
//   start accept (start_p && !bad, was one OAI driving identity_q / generation_q / stage_q / sel_q / cycle / active ->
//               kvi pins) -> KEPT start_p copies spc / spy / spl, one AND with nbad per slice;
//   active      -> NA KEPT copies (same next-state function) for the cycle slices and the word-copy enable;
//   sh0..sh3    -> 3 KEPT cfg_we_p copies, one boot-write enable per (word, <= 11-bit slice);
//   word_slot_q / word_index_q -> + NC KEPT copies exported as compiled_word_slot_c / compiled_word_index_c (the writer's
//               select families' D side).
module qkd_kv_native_programme_s32 #(parameter integer MUT=0,parameter integer VMAP=0,parameter integer RCOPIES=1,
 parameter integer SRAM=0,parameter integer CTLSRAM=0,parameter integer NC=4)(
 input wire ck,rst_n,
 input wire cfg_we,input wire[7:0]cfg_addr,input wire[63:0]cfg_data,
 input wire start,input wire[5:0]stage,input wire[15:0]epoch,input wire[17:0]token,
 input wire[12:0]position,input wire[1:0]generation,
 output wire compiled_word_slot,output wire[1:0]compiled_word_index,
 output wire[NC-1:0]compiled_word_slot_c,output wire[2*NC-1:0]compiled_word_index_c,
 output wire[58:0]compiled_identity,output wire[1:0]compiled_generation,
 output wire kvn_word_slot,
 output reg configured,active,done,fault,
 output wire[31:0]cycle,
 output reg[3:0]expected_valid,output reg[19:0]expected_pc,
 output reg[1:0]expected_stack,output reg[58:0]expected_identity,
 output reg[1:0]expected_generation,output reg[28:0]expected_address
);
 localparam integer SW=14;
 (* keep = "true" *) reg reset_pin_n;
 always @(posedge ck) reset_pin_n<=rst_n;
 generate if(RCOPIES>1)begin:g_rc
  (* keep = "true" *) reg[RCOPIES-2:0]rc_q;
  always @(posedge ck)rc_q<={(RCOPIES-1){rst_n}};
  (* keep = "true", ot_rst_split *) wire[RCOPIES-1:0]rpv={rc_q,reset_pin_n};
 end endgenerate
 (* keep = "true" *) reg cfg_we_p,start_p;
 (* keep = "true" *) reg[7:0]cfg_addr_p;
 (* keep = "true" *) reg[63:0]cfg_data_p;
 (* keep = "true" *) reg[5:0]stage_p;
 (* keep = "true" *) reg[15:0]epoch_p;
 (* keep = "true" *) reg[17:0]token_p;
 (* keep = "true" *) reg[12:0]position_p;
 (* keep = "true" *) reg[1:0]generation_p;
 always @(posedge ck)begin
  cfg_addr_p<=cfg_addr;cfg_data_p<=cfg_data;
  stage_p<=stage;epoch_p<=epoch;token_p<=token;
  position_p<=position;generation_p<=generation;
 end
 always @(posedge ck or negedge reset_pin_n)
  if(!reset_pin_n)begin cfg_we_p<=0;start_p<=0;end
  else begin cfg_we_p<=cfg_we;start_p<=start;end
 // S32: kept copies of the cfg_we / start pin flops (same D, reset)
 localparam integer NSS=(73+SW-1)/SW, NCY=4, NLD=(160+SW-1)/SW, NLG=3, NA=NCY+1;
 (* keep = "true" *) reg[2:0]cwe_c;
 (* keep = "true" *) reg[NSS-1:0]spc;
 (* keep = "true" *) reg[NCY-1:0]spy;
 (* keep = "true" *) reg[NLG-1:0]spl;
 always @(posedge ck or negedge reset_pin_n)
  if(!reset_pin_n)begin cwe_c<=0;spc<=0;spy<=0;spl<=0;end
  else begin cwe_c<={3{cfg_we}};spc<={NSS{start}};spy<={NCY{start}};spl<={NLG{start}};end
 reg[159:0]tv;                                   // {stop_q, t3, t2, t1, t0}
 wire[31:0]t0=tv[31:0],t1=tv[63:32],t2=tv[95:64],t3=tv[127:96],stop_q=tv[159:128];
 reg[7:0]next_cfg;
 reg[5:0]cfg_stage;reg[2:0]cfg_word;
 reg[31:0]table0[0:35],table1[0:35],table2[0:35],table3[0:35],table_stop[0:35];
 wire acc_rest=!active&&!configured&&!fault&&cfg_addr_p==next_cfg;
 wire accept_cfg=cfg_we_p&&acc_rest;
 reg wq_v;reg[35:0]wq_stage;reg[4:0]wq_word;reg[31:0]wq_data;
 always @(posedge ck or negedge reset_pin_n)
  if(!reset_pin_n)wq_v<=0;else wq_v<=accept_cfg&&cfg_addr_p<180;
 always @(posedge ck)begin
  wq_stage<=36'd1<<cfg_stage;wq_word<=5'd1<<cfg_word;wq_data<=cfg_data_p[31:0];
 end
 genvar g,k;
 generate if(SRAM==0)begin:g_ftw for(g=0;g<36;g=g+1)begin:g_stage
  always @(posedge ck)if(wq_v&&wq_stage[g])begin
   if(wq_word[0])table0[g]<=wq_data;
   if(wq_word[1])table1[g]<=wq_data;
   if(wq_word[2])table2[g]<=wq_data;
   if(wq_word[3])table3[g]<=wq_data;
   if(wq_word[4])table_stop[g]<=wq_data;
  end
 end end endgenerate
 // shadow words: enable (cfg_we_p copy h, word w) per <= 11-bit slice
 reg[127:0]shv;                                  // {sh3, sh2, sh1, sh0}
 wire[31:0]sh0=shv[31:0],sh1=shv[63:32],sh2=shv[95:64],sh3=shv[127:96];
 wire sh_rest=acc_rest&&cfg_addr_p<180;
 generate for(g=0;g<4;g=g+1)begin:g_shw for(k=0;k<3;k=k+1)begin:g_shs
  localparam integer LO=32*g+11*k, W=(k==2)?10:11;
  always @(posedge ck)if(cwe_c[k]&&sh_rest&&cfg_word==g)shv[LO+:W]<=cfg_data_p[11*k+:W];
 end end endgenerate
 wire[5:0]selected_stage=(MUT==5)?((stage_p==36)?6'd1:stage_p+6'd1):stage_p;
 reg ld;(* keep = "true" *) reg[NLD-1:0]ldc;
 reg[31:0]tm0,tm1,tm2,tm3;
 reg[72:0]sv;                                    // {identity_q 59, generation_q 2, stage_q 6, sel_q 6}
 wire[58:0]identity_q=sv[72:14];wire[1:0]generation_q=sv[13:12];wire[5:0]stage_q=sv[11:6],sel_q=sv[5:0];
 wire[31:0]rt0,rt1,rt2,rt3,rts;
 generate if(SRAM==0)begin:g_ft
  assign rt0=table0[sel_q];assign rt1=table1[sel_q];assign rt2=table2[sel_q];assign rt3=table3[sel_q];
  assign rts=table_stop[sel_q];
 end else begin:g_sr
  reg[5:0]wq_row;
  always @(posedge ck)wq_row<=cfg_stage;
  wire[255:0]rd;
  wire[5:0]r_row=selected_stage-6'd1;
  wire[255:0]w_d={96'd0,{5{wq_data}}};
  wire[255:0]w_m={96'd0,{32{wq_word[4]}},{32{wq_word[3]}},{32{wq_word[2]}},{32{wq_word[1]}},{32{wq_word[0]}}};
  if(CTLSRAM==0)begin:g_s0
  ot_sram_1r1w_128x256_m1_r2c2 u_rows(.clk(ck),.r_ce_in(start_p),.r_addr_in({1'b0,r_row}),.rd_out(rd),
   .w_ce_in(wq_v),.w_addr_in({1'b0,wq_row}),.wd_in(w_d),.w_mask_in(w_m),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  end else if(CTLSRAM==1)begin:g_s1
  ctl_sram_1r1w_64x64_p192 u_rows_b0(.clk(ck),.r_ce_in(start_p),.r_addr_in(r_row),.rd_out(rd[0+:64]),
   .w_ce_in(wq_v),.w_addr_in(wq_row),.wd_in(w_d[0+:64]),.w_mask_in(w_m[0+:64]));
  ctl_sram_1r1w_64x64_p192 u_rows_b1(.clk(ck),.r_ce_in(start_p),.r_addr_in(r_row),.rd_out(rd[64+:64]),
   .w_ce_in(wq_v),.w_addr_in(wq_row),.wd_in(w_d[64+:64]),.w_mask_in(w_m[64+:64]));
  ctl_sram_1r1w_64x64_p192 u_rows_b2(.clk(ck),.r_ce_in(start_p),.r_addr_in(r_row),.rd_out(rd[128+:64]),
   .w_ce_in(wq_v),.w_addr_in(wq_row),.wd_in(w_d[128+:64]),.w_mask_in(w_m[128+:64]));
  assign rd[255:192]=64'd0;
  end else begin:g_s2
  ctl_sram_1r1w_64x128_p192 u_rows_b0(.clk(ck),.r_ce_in(start_p),.r_addr_in(r_row),.rd_out(rd[0+:128]),
   .w_ce_in(wq_v),.w_addr_in(wq_row),.wd_in(w_d[0+:128]),.w_mask_in(w_m[0+:128]));
  ctl_sram_1r1w_64x128_p192 u_rows_b1(.clk(ck),.r_ce_in(start_p),.r_addr_in(r_row),.rd_out(rd[128+:128]),
   .w_ce_in(wq_v),.w_addr_in(wq_row),.wd_in(w_d[128+:128]),.w_mask_in(w_m[128+:128]));
  end
  assign rt0=rd[31:0];assign rt1=rd[63:32];assign rt2=rd[95:64];assign rt3=rd[127:96];assign rts=rd[159:128];
 end endgenerate
 always @(posedge ck or negedge reset_pin_n)
  if(!reset_pin_n)begin tm0<=~32'd0;tm1<=~32'd0;tm2<=~32'd0;tm3<=~32'd0;end
  else begin tm0<=t0-((MUT==2)?32'd2:32'd1);tm1<=t1-32'd1;tm2<=t2-32'd1;tm3<=t3-32'd1;end
 reg[31:0]cyc;assign cycle=cyc;
 wire n0=!ld&&cycle==tm0,n1=!ld&&cycle==tm1;
 wire n2=!ld&&cycle==tm2,n3=!ld&&cycle==tm3;
 wire next_slot=n0||n1||n2||n3;
 wire[1:0]next_index=n0?2'd0:n1?2'd1:n2?2'd2:2'd3;
 (* keep = "true" *) reg word_slot_q,kvn_slot_q;
 (* keep = "true" *) reg[1:0]word_index_q;
 (* keep = "true" *) reg[NC-1:0]wsc;
 (* keep = "true" *) reg[2*NC-1:0]wic;
 assign compiled_word_slot=word_slot_q;
 assign kvn_word_slot=kvn_slot_q;
 assign compiled_word_index=word_index_q;
 assign compiled_word_slot_c=wsc;
 assign compiled_word_index_c=wic;
 wire slot=word_slot_q;
 wire[1:0]index=word_index_q;
 assign compiled_identity=identity_q;
 assign compiled_generation=generation_q;
 reg pending;reg kind_q;
 function automatic[2:0]group_of(input[2:0]logical_group);
  case(logical_group)
   0:group_of=2;1:group_of=3;2:group_of=4;3:group_of=5;
   4:group_of=0;5:group_of=1;6:group_of=6;7:group_of=7;
  endcase
 endfunction
 wire[12:0]pos=identity_q[18:6];
 wire vm=(VMAP!=0)&&kind_q;
 wire[2:0]grp_q=vm?{pos[5:4],pos[0]^((MUT==7)?1'b1:1'b0)}:pos[2:0];
 wire[2:0]group_q=group_of(grp_q);
 // start accept: bad = the original rejection; acc_k = start copy k && nbad
 wire bad=!configured||active||fault||cfg_we_p||stage_p<1||stage_p>36;
 wire nbad=!bad;
 wire[72:0]sv_d={{epoch_p,stage_p,token_p,position_p,6'd0} ^ ((MUT==1)?(59'd1<<43):((MUT==6)?(59'd1<<37):59'd0)),
                 generation_p,stage_p,selected_stage-6'd1};
 generate for(k=0;k<NSS;k=k+1)begin:g_sv
  localparam integer LO=k*SW, W=(73-LO<SW)?73-LO:SW;
  always @(posedge ck or negedge reset_pin_n)
   if(!reset_pin_n)sv[LO+:W]<=0;else if(spc[k]&&nbad)sv[LO+:W]<=sv_d[LO+:W];
 end endgenerate
 // ld copies (D = start_p && !bad, as ld) and the root row slices they load
 wire[159:0]rt_all={rts,rt3,rt2,rt1,rt0};
 generate for(k=0;k<NLD;k=k+1)begin:g_ld
  localparam integer LO=k*SW, W=(160-LO<SW)?160-LO:SW;
  always @(posedge ck or negedge reset_pin_n)
   if(!reset_pin_n)ldc[k]<=0;else ldc[k]<=spl[k%NLG]&&nbad;
  always @(posedge ck or negedge reset_pin_n)
   if(!reset_pin_n)tv[LO+:W]<=0;else if(ldc[k])tv[LO+:W]<=rt_all[LO+:W];
 end endgenerate
 // active next state (the big block's), copied NA times: [NCY-1:0] cycle slices, [NCY] word copies
 wire active_nx=start_p?(bad?active:1'b1):(active?!((!ld&&cycle==stop_q)||(&cycle)):active);
 (* keep = "true" *) reg[NA-1:0]actc;
 always @(posedge ck or negedge reset_pin_n)
  if(!reset_pin_n)actc<=0;else actc<={NA{active_nx}};
 wire[31:0]cyc_inc=cyc+32'd1;
 generate for(k=0;k<NCY;k=k+1)begin:g_cy
  always @(posedge ck or negedge reset_pin_n)
   if(!reset_pin_n)cyc[8*k+:8]<=0;
   else if(spy[k])begin if(nbad)cyc[8*k+:8]<=8'd0;end
   else if(actc[k])cyc[8*k+:8]<=cyc_inc[8*k+:8];
 end endgenerate
 always @(posedge ck or negedge reset_pin_n)
  if(!reset_pin_n)begin wsc<=0;wic<=0;end
  else begin
   wsc<={NC{actc[NCY]&&next_slot}};
   if(actc[NCY])wic<={NC{next_index ^ ((MUT==3)?2'd1:2'd0)}};
  end
 always @(posedge ck or negedge reset_pin_n)begin
  if(!reset_pin_n)begin
   next_cfg<=0;cfg_stage<=0;cfg_word<=0;ld<=0;
   configured<=0;active<=0;done<=0;
   word_slot_q<=0;kvn_slot_q<=0;word_index_q<=0;fault<=0;pending<=0;kind_q<=0;expected_valid<=0;
   expected_pc<=0;expected_stack<=0;expected_identity<=0;
   expected_generation<=0;expected_address<=0;
  end else begin
   done<=0;expected_valid<=0;ld<=0;
   word_slot_q<=0;kvn_slot_q<=0;
   if(active)begin
    word_slot_q<=next_slot;kvn_slot_q<=next_slot;
    word_index_q<=next_index ^ ((MUT==3)?2'd1:2'd0);
   end
   pending<=slot&&word_index_q[0];
   if(slot&&index[0])kind_q<=index[1];
   if(pending)begin
    expected_valid<=4'hf;
    expected_identity<=identity_q;expected_generation<=generation_q;
    expected_stack<=pos[8:7];
    expected_pc<={group_q,2'd3,group_q,2'd2,group_q,2'd1,group_q,2'd0};
    expected_address<={19'd64+{13'd0,stage_q-6'd1},kind_q,1'b0,pos[6],vm?pos[2:1]:pos[4:3],pos[12:9],vm?pos[3]:pos[5]} ^ ((MUT==4)?29'd1:29'd0);
   end
   if(cfg_we_p)begin
    if(!accept_cfg)fault<=1;
    else if(cfg_addr_p<180)begin
     next_cfg<=next_cfg+1'b1;
     if(cfg_data_p[63:32]!=0)fault<=1;
     if(cfg_word==4)begin
      if(sh0<4||sh0>=sh1||sh1>=sh2||sh2>=sh3||
         cfg_data_p[31:0]<=sh3||cfg_data_p[31:0]-sh3<3)fault<=1;
      cfg_word<=0;cfg_stage<=cfg_stage+1'b1;
     end else cfg_word<=cfg_word+1'b1;
    end else if(cfg_addr_p==180&&cfg_data_p==64'h514b565052473336&&cfg_stage==36&&cfg_word==0)
     configured<=1;
    else fault<=1;
   end
   if(start_p)begin
    if(bad)fault<=1;
    else begin active<=1;ld<=1;end
   end else if(active)begin
    if(!ld&&cycle==stop_q)begin active<=0;done<=1;end
    if(&cycle)begin active<=0;fault<=1;done<=1;end
   end
  end
 end
endmodule
