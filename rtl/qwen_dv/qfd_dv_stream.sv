`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_stream -- the Q-DV slice's bidirectional neighbour stream face: pass-through relay W->E and E->W, the slice's
// own broadcast words (BF16 x segments of the consumer-side norm, SiLU*up, ...), and the table-write tap.
//
// Stream word (1,088 b): [1023:0] payload, [1087] v, [1086:1084] kind, [1083:1080] dst slice (15 = all), [1079:1076]
// src slice, [1075:1052] eaddr, [1051:1024] tag.
//   kind 0 X     : 64 BF16, element eaddr + i in payload[16 i +: 16] (eaddr 64-aligned, all 64 valid)
//   kind 1 CROM  : 16 (lo, hi) FP32 pairs for constant word eaddr      kind 2 BTAB : 64 BF16 for BF16-table words
//   kind 3 PROG  : 2 SU instructions (457 b each, 512-b slots) for program pair eaddr                (eaddr .. +3)
// Pass-through: every valid word moves one slice per edge (registered).  Own X words go out in the directions armed
// by the STREAM command; a pass word and an own word for the same direction on one edge is a sticky fault (the
// compiler owns the slots), as is a partial x beat abandoned for another beat.
// BF16 conversion (the consumer's operand, hdc_golden.to_bf16 and the tile's RNE16): (b + 0x7FFF + b[16]) >> 16.
// MUT 2 (bench negative control): truncation instead of RNE (must FAIL).
// =====================================================================================================================
module qfd_dv_stream #(
    parameter integer MUT = 0
) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [3:0]     sid,
    input  wire           cfg_v,
    input  wire [1:0]     cfg_dir,       // bit 0: east, bit 1: west
    input  wire [27:0]    cfg_tag,
    input  wire [1087:0]  sw_i,          // arriving from the west neighbour (travelling east); pin-registered
    input  wire [1087:0]  se_i,          // arriving from the east neighbour (travelling west); pin-registered
    output reg  [1087:0]  so_e,
    output reg  [1087:0]  so_w,
    // own x writes (SU lanes, window 01: element = addr[21:0])
    input  wire [7:0]     xw_we,
    input  wire [8*24-1:0] xw_addr,
    input  wire [8*32-1:0] xw_data,
    // table-write tap
    output reg            tw_we,
    output reg  [1:0]     tw_kind,
    output reg  [23:0]    tw_addr,
    output reg  [1023:0]  tw_data,
    output reg            fault
);
    reg [1:0]  dir; reg [27:0] tag;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin dir <= 2'b00; tag <= 28'd0; end
        else if (cfg_v) begin dir <= cfg_dir; tag <= cfg_tag; end
    function automatic [15:0] bf16(input [31:0] b);
        reg [32:0] r;
        begin
            r = {1'b0, b} + 33'h7FFF + {32'd0, b[16]};
            bf16 = (MUT == 2) ? b[31:16] : r[31:16];
        end
    endfunction
    // -------------------------------------------------------------- x packer (one 64-element beat in flight)
    reg [1023:0] xb;
    reg [63:0]   xm;
    reg [15:0]   xbeat;
    reg          xopen;
    reg          emit;
    reg [1023:0] eword;
    reg [15:0]   ebeat;
    integer l;
    reg [63:0]   nm;
    reg [1023:0] nb;
    reg          pbad;
    always @(*) begin
        nm = xopen ? xm : 64'd0; nb = xb; pbad = 1'b0;
        for (l = 0; l < 8; l = l + 1)
            if (xw_we[l]) begin
                if (xw_addr[24*l + 6 +: 16] != xw_addr[6 +: 16] || !xw_we[0]) pbad = 1'b1;
                nb[16*xw_addr[24*l +: 6] +: 16] = bf16(xw_data[32*l +: 32]);
                if (nm[xw_addr[24*l +: 6]]) pbad = 1'b1;
                nm[xw_addr[24*l +: 6]] = 1'b1;
            end
        if (xw_we[0] && xopen && xw_addr[6 +: 16] != xbeat) pbad = 1'b1;   // previous beat abandoned partial
    end
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin xopen <= 1'b0; xm <= 64'd0; emit <= 1'b0; end
        else begin
            emit <= 1'b0;
            if (xw_we != 8'd0) begin
                if (&nm) begin xopen <= 1'b0; xm <= 64'd0; emit <= 1'b1; end
                else begin xopen <= 1'b1; xm <= nm; end
            end
        end
    end
    always @(posedge ck) begin
        if (xw_we != 8'd0) begin xb <= nb; xbeat <= xw_addr[6 +: 16]; end
        if (xw_we != 8'd0 && &nm) begin eword <= nb; ebeat <= xw_addr[6 +: 16]; end
    end
    wire [63:0] own_ctl = {1'b1, 3'd0, 4'hF, sid, {2'b00, ebeat, 6'd0}, tag};
    // -------------------------------------------------------------- relay + insertion
    wire pe = sw_i[1087], pw = se_i[1087];
    wire ie = emit && dir[0], iw = emit && dir[1];
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin so_e <= 1088'd0; so_w <= 1088'd0; end
        else begin
            so_e <= pe ? sw_i : ie ? {own_ctl, eword} : 1088'd0;
            so_w <= pw ? se_i : iw ? {own_ctl, eword} : 1088'd0;
        end
    // -------------------------------------------------------------- table-write tap
    wire te = pe && sw_i[1086:1084] != 3'd0 && (sw_i[1083:1080] == sid || sw_i[1083:1080] == 4'hF);
    wire tw_ = pw && se_i[1086:1084] != 3'd0 && (se_i[1083:1080] == sid || se_i[1083:1080] == 4'hF);
    wire [1087:0] tsrc = te ? sw_i : se_i;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) tw_we <= 1'b0;
        else tw_we <= te || tw_;
    always @(posedge ck) begin
        tw_kind <= tsrc[1085:1084]; tw_addr <= tsrc[1075:1052]; tw_data <= tsrc[1023:0];
    end
    wire bad = pbad || (pe && ie) || (pw && iw) || (te && tw_) ||
               (pe && sw_i[1086]) || (pw && se_i[1086]);                 // kinds 4..7 are not defined
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else fault <= fault | bad;
endmodule
