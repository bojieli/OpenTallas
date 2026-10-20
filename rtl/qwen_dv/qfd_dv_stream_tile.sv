`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_stream_tile -- the Q-DV slice stream face (qfd_dv_stream / static packer qfd_dv_stream_packer 9587da800) as a
// structurally safe hard tile (QW-CLUSTER3/STREAM 2026-10-19, owner safe-design checklist).
//
// Function: exactly qfd_dv_stream (sw_i = {sw_v, sw_hi, sw_lo}, tw_data = {tw_data_hi, tw_data_lo}, ...) with (a) every input registered once at its face and (b) the two tap outputs (table
// write tw_*, x tap xt_*) carried through one interior relay register.  Static schedule, no backpressure:
//   stream side  sw_i / se_i / sid : +1 edge (the face register; it REPLACES the slice's sw_q / se_q capture -> net 0)
//   SU side      cfg_*             : +1 edge (face register; the SU issues the STREAM cfg one edge earlier)
//   SU own x     xw_*              : +3 edges (face register + packer P1/P2 stages, QW-STREAM2 10-19): the SU issues own
//                                    x writes 3 edges earlier; II unchanged
//   relay        so_e / so_w       : unchanged (face reg -> relay mux -> output reg, one word per edge per direction)
//   taps         tw_* / xt_*       : +1 edge (interior relay: the tap mux sits between the W/E relay faces and the N/S
//                                    tap faces; without it a tap bit crosses ~490 um in one cycle)
//   reset                          : the kit lands rst_n in 2 registered stages (+2 edges assert/release, constant)
// Exactness: tb_stream_tile.sv compares every output against qfd_dv_stream with all inputs delayed one edge (xw_* three) and the tap
// outputs delayed one more edge, 10,000 edges, two resets, all lane subsets / duplicates / abandoned beats / conflicts.
//
// Fanout (safe item 3): every register that selects a wide word is a (* keep *) copy per 32-bit group, decoded at the face
// from the pins (te/xe/pe and E-side twins, write-any, config enable, emit, direction); ot_keep_regs.tcl keeps the copies.
// Reset is on control state only (valids, masks, config, faults); payload registers are overwritten every edge and carry
// no reset (no reset on the datapath).
// Storage (item 5): 1,024-bit assembly + 1,024-bit completed word + 64-bit mask, no runtime-indexed array > 2 kb, no
// delay line >= 3 deep.
// MUT (negative controls, must FAIL the bench): 2 BF16 truncation, 21 no lane priority, 22 no duplicate fault,
// 31 relay group 17 selects on the E valid copy, 32 table-tap group 5 ignores the SID match, 33 emit copy of relay group 9
// stuck 0, 34 face copy of write-any for xb group 3 stuck 0.
// =====================================================================================================================
module qfd_dv_stream_tile #(
    parameter integer MUT = 0
) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [3:0]     sid,
    input  wire           cfg_v,
    input  wire [1:0]     cfg_dir,
    input  wire [27:0]    cfg_tag,
    // incoming stream words, split only for the pin plan (word = {v, hi, lo}): the valid bit sits mid-face so its
    // kept select copies (anchored at the pin) reach every relay group within ~400 um
    input  wire [543:0]   sw_lo,
    input  wire           sw_v,
    input  wire [542:0]   sw_hi,
    input  wire [543:0]   se_lo,
    input  wire           se_v,
    input  wire [542:0]   se_hi,
    output reg  [1087:0]  so_e,
    output reg  [1087:0]  so_w,
    input  wire [7:0]     xw_we,
    input  wire [8*24-1:0] xw_addr,
    input  wire [8*32-1:0] xw_data,
    output reg            tw_we,
    output reg  [1:0]     tw_kind,
    output reg  [23:0]    tw_addr,
    output reg  [511:0]   tw_data_lo,
    output reg  [511:0]   tw_data_hi,
    output reg            xt_v,
    output reg  [23:0]    xt_a,
    output reg  [511:0]   xt_d_lo,
    output reg  [511:0]   xt_d_hi,
    output reg            xt_bad,
    output reg            fault
);
    localparam integer NR = 34;   // 1088-bit relay words: 34 groups of 32
    localparam integer NT = 33;   // 1050-bit table tap / 1048-bit x tap: 33 groups of 32
    localparam integer NB = 32;   // 1024-bit assembly / completed word: 32 groups of 32
    wire [1087:0] sw_i = {sw_v, sw_hi, sw_lo};
    wire [1087:0] se_i = {se_v, se_hi, se_lo};
    // ================================================================================================ face registers
    reg [1086:0] sw_q, se_q;                       // payload + header (bit 1087 = valid lives in the copies)
    reg [3:0]    sid_q;
    reg [1:0]    cdir_q;
    reg [27:0]   ctag_q;
    reg [7:0]    we_q;
    reg [191:0]  wa_q;
    reg [255:0]  wd_q;
    (* keep = "true" *) reg [NR-1:0] pe_c, pw_c;  // valid copies (relay select)
    (* keep = "true" *) reg [NT-1:0] te_c, tw_c;  // table-tap hit copies (valid, kind != 0, dst == sid or 15)
    (* keep = "true" *) reg [NT-1:0] xe_c, xw_c;  // x-tap hit copies (valid, kind == 0)
    (* keep = "true" *) reg [NB+3:0] wa_c;        // write-any copies: [31:0] xb/eword groups, [32] open+xbeat, [33]/[34] xm halves, [35] emit+ebeat
    (* keep = "true" *) reg [4:0]    cv_c;        // config-enable copies: [3:0] direction groups, [4] tag
    reg          ubad_q;                           // undefined kind 4..7 on a valid pass word
    wire te_i = sw_i[1087] && sw_i[1086:1084] != 3'd0 && (sw_i[1083:1080] == sid || sw_i[1083:1080] == 4'hF);
    wire tw_i = se_i[1087] && se_i[1086:1084] != 3'd0 && (se_i[1083:1080] == sid || se_i[1083:1080] == 4'hF);
    wire te_m = sw_i[1087] && sw_i[1086:1084] != 3'd0;            // MUT 32: SID match dropped in one group
    always @(posedge ck) begin
        sw_q <= sw_i[1086:0]; se_q <= se_i[1086:0]; sid_q <= sid;
        cdir_q <= cfg_dir; ctag_q <= cfg_tag; wa_q <= xw_addr; wd_q <= xw_data;
    end
    integer gi;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin
            pe_c <= 0; pw_c <= 0; te_c <= 0; tw_c <= 0; xe_c <= 0; xw_c <= 0; wa_c <= 0; cv_c <= 0; we_q <= 0; ubad_q <= 0;
        end else begin
            for (gi = 0; gi < NR; gi = gi + 1) begin
                pe_c[gi] <= (MUT == 31 && gi == 17) ? se_i[1087] : sw_i[1087];
                pw_c[gi] <= se_i[1087];
            end
            for (gi = 0; gi < NT; gi = gi + 1) begin
                te_c[gi] <= (MUT == 32 && gi == 5) ? te_m : te_i;
                tw_c[gi] <= tw_i;
                xe_c[gi] <= sw_i[1087] && sw_i[1086:1084] == 3'd0;
                xw_c[gi] <= se_i[1087] && se_i[1086:1084] == 3'd0;
            end
            for (gi = 0; gi < NB + 4; gi = gi + 1) wa_c[gi] <= (MUT == 34 && gi == 3) ? 1'b0 : (xw_we != 8'd0);
            cv_c <= {5{cfg_v}};
            we_q <= xw_we;
            ubad_q <= (sw_i[1087] && sw_i[1086]) || (se_i[1087] && se_i[1086]);
        end
    // ================================================================================================ configuration
    (* keep = "true" *) reg [NR-1:0] de_c, dw_c;  // direction copies (east / west armed)
    reg [27:0] tag;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin de_c <= 0; dw_c <= 0; tag <= 28'd0; end
        else begin
            for (gi = 0; gi < NR; gi = gi + 1)
                if (cv_c[gi % 4]) begin de_c[gi] <= cdir_q[0]; dw_c[gi] <= cdir_q[1]; end
            if (cv_c[4]) tag <= ctag_q;
        end
    // ================================================================================================ static x packer
    // qfd_dv_stream_packer STATIC_PACKER=1 equations: 64 independent BF16 slots, highest-lane priority, duplicate fault.
    // QW-STREAM2 10-19 (route s1-2c97be786 TT -47.5 ps: wa_q -> decode -> priority -> 8-way OR -> &nm -> 1,024-bit eword
    // enable in one edge, 17 levels + a ~1,100-load combinational enable) -- pipelined in three registered stages:
    //   P1 (edge after the face): BF16 RNE of the 8 lanes, the slot x lane one-hot select (decode + highest-lane priority)
    //      and the per-slot hit, the beat-consistency and duplicate partial faults -- all pure functions of the face regs;
    //   P2 (state edge): assembly xb / mask xm / open op / beat xbeat from the registered one-hot select (AND-OR 8 + mux),
    //      complete = &nm into KEPT copies cm_c (eword groups, emit groups, x tap, ebeat) and the beat fault pbad_r;
    //   P3 (emit edge): eword[g] <= xb[g] on its own kept copy cm_c[g]; emit copies em_c / emx_c; ebeat.
    // Net: the SU own-write path xw_* -> emitted beat / x tap / fault is +2 edges against the previous tile (+3 against
    // qfd_dv_stream).  Static: the SU issues own x writes 2 edges earlier; II unchanged (one 8-lane write per edge).
    function automatic [15:0] bf16(input [31:0] b);
        reg [32:0] r;
        begin
            r = {1'b0, b} + 33'h7FFF + {32'd0, b[16]};
            bf16 = (MUT == 2) ? b[31:16] : r[31:16];
        end
    endfunction
    genvar l, d, s, b;
    // ---------------------------------------------------------------------------------------------- P1
    wire [63:0]  lo_hit, hi_hit;
    wire [511:0] sel_n;                            // [8*s + l]: lane l writes slot s (highest lane wins)
    wire [63:0]  sh_n, dup_n;
    wire [7:0]   beat_bad;
    generate
        for (l = 0; l < 8; l = l + 1) begin: g_decode
            for (d = 0; d < 8; d = d + 1) begin: g_digit
                assign lo_hit[8*l+d] = (wa_q[24*l +: 3] == d);
                assign hi_hit[8*l+d] = we_q[l] && (wa_q[24*l+3 +: 3] == d);
            end
            assign beat_bad[l] = we_q[l] && (!we_q[0] || wa_q[24*l+6 +: 16] != wa_q[6 +: 16]);
        end
        for (s = 0; s < 64; s = s + 1) begin: g_slot1
            wire [7:0] hit;
            for (l = 0; l < 8; l = l + 1) begin: g_lane
                assign hit[l] = lo_hit[8*l + (s % 8)] && hi_hit[8*l + (s / 8)];
                if (l == 7) begin: g_top
                    assign sel_n[8*s+l] = hit[l];
                end else begin: g_low
                    assign sel_n[8*s+l] = hit[l] && ((MUT == 21) || !(|hit[7:l+1]));
                end
            end
            assign sh_n[s] = |hit;
            assign dup_n[s] = (hit[1] && hit[0]) || (hit[2] && |hit[1:0]) || (hit[3] && |hit[2:0]) ||
                              (hit[4] && |hit[3:0]) || (hit[5] && |hit[4:0]) || (hit[6] && |hit[5:0]) ||
                              (hit[7] && |hit[6:0]);
        end
    endgenerate
    reg [511:0] selq;                              // registered one-hot select (each bit -> 16 AND terms)
    reg [63:0]  shq;                               // registered slot hit (each -> 16 mux + nm + fault = 18 loads)
    (* keep = "true" *) reg [127:0] lane_c0;      // BF16 lane data, kept copy for slots 0..31 (32 loads per bit)
    (* keep = "true" *) reg [127:0] lane_c1;      // kept copy for slots 32..63
    (* keep = "true" *) reg [NB+3:0] wa1_c;       // write-any copies one edge on (same groups as wa_c)
    reg         dupq, bbq, w0q;
    reg [15:0]  abq;                               // beat address of lane 0
    integer li;
    always @(posedge ck) begin
        selq <= sel_n; shq <= sh_n; dupq <= |dup_n; bbq <= |beat_bad; w0q <= we_q[0]; abq <= wa_q[6 +: 16];
        for (li = 0; li < 8; li = li + 1) begin
            lane_c0[16*li +: 16] <= bf16(wd_q[32*li +: 32]);
            lane_c1[16*li +: 16] <= bf16(wd_q[32*li +: 32]);
        end
        wa1_c <= wa_c;                             // copy-to-copy, one load each (no fanout)
    end
    // ---------------------------------------------------------------------------------------------- P2
    reg [1023:0] xb;
    reg [63:0]   xm;
    reg [15:0]   xbeat;
    (* keep = "true" *) reg [3:0] op_c;           // open-beat copies, 16 slots each
    wire [63:0]  nm;
    wire [1023:0] nb;
    wire [63:0]  slot_bad;
    generate
        for (s = 0; s < 64; s = s + 1) begin: g_slot
            wire [127:0] lane = (s < 32) ? lane_c0 : lane_c1;
            wire [15:0] packed_slot;
            for (b = 0; b < 16; b = b + 1) begin: g_bit
                wire [7:0] terms;
                for (l = 0; l < 8; l = l + 1) begin: g_term
                    assign terms[l] = lane[16*l + b] && selq[8*s+l];
                end
                assign packed_slot[b] = |terms;
            end
            assign nb[16*s +: 16] = shq[s] ? packed_slot : xb[16*s +: 16];
            assign nm[s] = (op_c[s / 16] && xm[s]) || shq[s];
            assign slot_bad[s] = op_c[s / 16] && xm[s] && shq[s];
        end
    endgenerate
    wire wany1 = wa1_c[NB+3];
    wire complete = &nm;
    wire sbad = (MUT == 22) ? 1'b0 : ((|slot_bad) || dupq);   // MUT 22: no duplicate / overwrite fault
    wire pbad_n = sbad || bbq || (w0q && op_c[0] && abq != xbeat);
    localparam integer NC = NB + NR + 3;           // complete copies: [NB-1:0] eword groups, [NB+NR-1:NB] emit groups,
                                                   // [NB+NR] / [NB+NR+1] x tap, [NB+NR+2] ebeat
    (* keep = "true" *) reg [NC-1:0] cm_c;
    reg          pbad_r;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin op_c <= 4'd0; xm <= 64'd0; cm_c <= {NC{1'b0}}; pbad_r <= 1'b0; end
        else begin
            cm_c <= {NC{wany1 && complete}};
            pbad_r <= pbad_n;
            if (wa1_c[NB]) op_c <= {4{!complete}};
            if (wa1_c[NB+1]) xm[31:0] <= complete ? 32'd0 : nm[31:0];
            if (wa1_c[NB+2]) xm[63:32] <= complete ? 32'd0 : nm[63:32];
        end
    always @(posedge ck) begin
        for (gi = 0; gi < NB; gi = gi + 1)
            if (wa1_c[gi]) xb[32*gi +: 32] <= nb[32*gi +: 32];
        if (wa1_c[NB]) xbeat <= abq;
    end
    wire pbad = pbad_r;                            // the beat fault, on the emit edge (bench compares it per edge)
    // ---------------------------------------------------------------------------------------------- P3
    (* keep = "true" *) reg [NR-1:0] em_c;        // emit copies: relay groups
    (* keep = "true" *) reg [1:0]    emx_c;       // emit copies: x tap select / x tap valid + conflict
    reg [1023:0] eword;
    reg [15:0]   ebeat;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin em_c <= 0; emx_c <= 2'd0; end
        else begin
            for (gi = 0; gi < NR; gi = gi + 1) em_c[gi] <= (MUT == 33 && gi == 9) ? 1'b0 : cm_c[NB + gi];
            emx_c <= cm_c[NB+NR+1 -: 2];
        end
    always @(posedge ck) begin
        for (gi = 0; gi < NB; gi = gi + 1)
            if (cm_c[gi]) eword[32*gi +: 32] <= xb[32*gi +: 32];
        if (cm_c[NB+NR+2]) ebeat <= xbeat;
    end
    wire [63:0]   own_ctl = {1'b1, 3'd0, 4'hF, sid_q, {2'b00, ebeat, 6'd0}, tag};
    wire [1087:0] own = {own_ctl, eword};
    // ================================================================================================ relay + insertion
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin so_e[1087] <= 1'b0; so_w[1087] <= 1'b0; end
        else begin
            so_e[1087] <= pe_c[NR-1] || (em_c[NR-1] && de_c[NR-1]);
            so_w[1087] <= pw_c[NR-1] || (em_c[NR-1] && dw_c[NR-1]);
        end
    always @(posedge ck)
        for (gi = 0; gi < 1087; gi = gi + 1) begin
            so_e[gi] <= pe_c[gi / 32] ? sw_q[gi] : (em_c[gi / 32] && de_c[gi / 32]) ? own[gi] : 1'b0;
            so_w[gi] <= pw_c[gi / 32] ? se_q[gi] : (em_c[gi / 32] && dw_c[gi / 32]) ? own[gi] : 1'b0;
        end
    // ================================================================================================ taps (interior relay)
    // table tap: word bits {kind 1085:1084, eaddr 1075:1052, payload 1023:0} = 1,050 bits, select te ? sw : se
    reg          r_tw_we, r_xt_v, r_xt_bad;
    reg [1:0]    r_tw_kind;
    reg [23:0]   r_tw_addr, r_xt_a;
    reg [1023:0] r_tw_data, r_xt_d;
    always @(posedge ck) begin
        for (gi = 0; gi < 1024; gi = gi + 1) begin
            r_tw_data[gi] <= te_c[gi / 32] ? sw_q[gi] : se_q[gi];
            r_xt_d[gi] <= xe_c[gi / 32] ? sw_q[gi] : xw_c[gi / 32] ? se_q[gi] : eword[gi];
        end
        r_tw_addr <= te_c[NT-1] ? sw_q[1075:1052] : se_q[1075:1052];
        r_tw_kind <= te_c[NT-1] ? sw_q[1085:1084] : se_q[1085:1084];
        r_xt_a <= xe_c[NT-1] ? sw_q[1075:1052] : xw_c[NT-1] ? se_q[1075:1052] : {2'b00, ebeat, 6'd0};
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin r_tw_we <= 1'b0; r_xt_v <= 1'b0; r_xt_bad <= 1'b0; end
        else begin
            r_tw_we <= te_c[0] || tw_c[0];
            r_xt_v <= xe_c[0] || xw_c[0] || emx_c[0];
            r_xt_bad <= r_xt_bad | ((xe_c[0] ? 2'd1 : 2'd0) + (xw_c[0] ? 2'd1 : 2'd0) + (emx_c[1] ? 2'd1 : 2'd0) > 2'd1);
        end
    // output registers at the N / S tap faces
    always @(posedge ck) begin
        tw_kind <= r_tw_kind; tw_addr <= r_tw_addr; tw_data_lo <= r_tw_data[511:0]; tw_data_hi <= r_tw_data[1023:512];
        xt_a <= r_xt_a; xt_d_lo <= r_xt_d[511:0]; xt_d_hi <= r_xt_d[1023:512];
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin tw_we <= 1'b0; xt_v <= 1'b0; xt_bad <= 1'b0; end
        else begin tw_we <= r_tw_we; xt_v <= r_xt_v; xt_bad <= r_xt_bad; end
    // ================================================================================================ fault (sticky)
    wire bad = pbad || (pe_c[0] && em_c[0] && de_c[0]) || (pw_c[0] && em_c[0] && dw_c[0]) || (te_c[0] && tw_c[0]) || ubad_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else fault <= fault | bad;
endmodule
