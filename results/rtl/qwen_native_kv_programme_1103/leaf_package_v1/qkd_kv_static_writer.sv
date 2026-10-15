`timescale 1ns/1ps
// Actual native TP8 FP8 KV writer. New master: no legacy credit/queue/view alias.
// Input is the real SU formatter word and the identity captured with THAT word.
// Compiler word slots select time. Missing/early/late/order/context faults never
// defer or retry a slot. A high-half slot expects four physical sector writes
// independently of whether the required payload arrived.
// Reuses ot_qkvd_kv_wq::sec_of map v2 and qkd_ctrl_strip::wj bank/column mapping.
//
// r3 (10-15) reset structure: the state is partitioned into RST_REGIONS=12 reset
// regions (control/ident, faults/expected, two half_data halves, two per es lane),
// each <= 256 flops.  RST_RELAY=1 (the physical master) drives each region from
// its own ot_rst_relay copy (async assert, synchronous release after
// RST_RELEASE_CYCLES=3 edges), so the rst_n port loads only the relay flops
// instead of 1,812 async-clear pins.  The compiler's boot schedule places the
// first word slot >= RST_RELEASE_CYCLES edges after port release (initialization
// is an explicit exceptional mode; normal timing is unchanged).  The four es
// lanes' bank/column/row and s_v/s_we fields were identical copies: they are one
// shared register now (es is the same bit vector, cycle for cycle).
module qkd_kv_static_writer #(parameter integer MUT = 0, parameter integer RST_RELAY = 0) (
    input wire ck, rst_n,
    input wire word_valid, input wire [10:0] word_tag,
    input wire [511:0] word_data,
    input wire [58:0] word_identity, input wire [1:0] word_generation,
    input wire compiled_word_slot, input wire [1:0] compiled_word_index,
    input wire [58:0] compiled_identity, input wire [1:0] compiled_generation,
    output wire [4*288-1:0] es,
    output reg [4*5-1:0] dest_pc, output reg [1:0] dest_stack,
    output reg [58:0] identity, output reg [1:0] generation,
    output reg [4*256-1:0] write_mask,
    output reg [3:0] native_kv,
    output reg [3:0] expected_valid,
    output reg [4*5-1:0] expected_pc, output reg [1:0] expected_stack,
    output reg [58:0] expected_identity, output reg [1:0] expected_generation,
    output reg [28:0] expected_address,
    output wire [317:0] es_context, output wire [60:0] es_expected_identity,
    output reg fault, output reg [7:0] fault_code
);
    localparam integer RST_REGIONS = 12;
    localparam integer RST_RELEASE_CYCLES = (RST_RELAY != 0) ? 3 : 0;
    wire [RST_REGIONS-1:0] rr;
    generate
        if (RST_RELAY != 0) begin : g_rst
            ot_rst_relay #(.REGIONS(RST_REGIONS), .SYNC_STAGES(2), .TREE_STAGES(1))
                u_rst (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
        end else begin : g_rst_direct
            assign rr = {RST_REGIONS{rst_n}};
        end
    endgenerate

    assign es_context = {1'b1, identity, generation, write_mask[255:0]};
    assign es_expected_identity = {expected_identity, expected_generation};
    // Physical strap PCs use GROUP_ORDER={4,5,0,1,2,3,6,7}, quarter fastest.
    function automatic [2:0] group_of(input [2:0] e);
        case(e) 0:group_of=2;1:group_of=3;2:group_of=4;3:group_of=5;
                4:group_of=0;5:group_of=1;6:group_of=6;7:group_of=7;endcase
    endfunction
    // All incoming functional face bits end at capture flops.
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

    reg [1:0] next_index;
    reg [58:0] cohort_identity;
    reg [1:0] cohort_generation;
    reg half_live;
    reg [511:0] half_data;
    reg [58:0] half_identity;
    reg [1:0] half_generation, half_index;
    wire [12:0] pos = wi[18:6];
    wire [5:0] stage = wi[42:37];
    wire [5:0] layer = stage - 6'd1;
    wire kind = wt[2];                 // formatter {kind, head=0, half}
    wire [18:0] row = 19'd64 + {13'd0, layer};
    wire [4:0] bank = {kind, 1'b0, pos[6], pos[4:3]};
    wire [4:0] column = {pos[12:9], pos[5]};
    wire [1023:0] assembled_row = {wd, half_data};
    wire [2:0] expected_word_kind = {ix[1], 1'b0, ix[0]};
    wire identity_ok = wi == ci && wg == cg && stage >= 1 && stage <= 36 && wi[5:0] == 0;
    wire header_ok = wt[10:8] == 3'b010 && wt[7:3] == 0 && wt[2:0] == expected_word_kind;
    wire pair_ok = !ix[0] ? !half_live : half_live && half_index == (ix - 2'd1) &&
                   half_identity == wi && half_generation == wg;
    wire program_ok = ix == next_index && (ix == 0 || (ci == cohort_identity && cg == cohort_generation));
    wire good = slot && wv && identity_ok && header_ok && pair_ok && program_ok;
    wire hi_slot = slot && ix[0];
    // MUT: 1 data, 2 physical address, 3 mask, 4 actual identity,
    //      5 missing physical write, 6 one-edge-late physical descriptor.

    // ---- region 0: slot/valid capture, program and pairing state, write identity
    always @(posedge ck or negedge rr[0]) begin
        if (!rr[0]) begin
            wv <= 0; slot <= 0;
            next_index <= 0; cohort_identity <= 0; cohort_generation <= 0;
            half_live <= 0; half_identity <= 0; half_generation <= 0; half_index <= 0;
            dest_pc <= 0; dest_stack <= 0; identity <= 0; generation <= 0;
        end else begin
            wv <= word_valid; slot <= compiled_word_slot;
            if (slot) begin
                next_index <= next_index + 2'd1;
                if (ix == 0) begin cohort_identity <= ci; cohort_generation <= cg; end
            end
            if (slot && !ix[0] && good) begin
                half_live <= 1; half_identity <= wi;
                half_generation <= wg; half_index <= ix;
            end
            if (hi_slot) begin
                half_live <= 0;
                dest_stack <= pos[8:7];
                identity <= wi ^ ((MUT == 4) ? 59'd1 << 19 : 59'd0);
                generation <= wg;
                dest_pc <= {group_of(pos[2:0]), 2'd3, group_of(pos[2:0]), 2'd2,
                            group_of(pos[2:0]), 2'd1, group_of(pos[2:0]), 2'd0};
            end
        end
    end

    // ---- region 1: faults, expected descriptor, shared es address/constant fields
    reg es_sv;                        // es s_v and s_we (identical constant bits)
    reg [28:0] es_addr;               // {bank, column, row}, shared by the 4 lanes
    reg [28:0] late_addr;             // MUT6 only (removed by synthesis otherwise)
    reg late_live_c;
    always @(posedge ck or negedge rr[1]) begin
        if (!rr[1]) begin
            write_mask <= 0; native_kv <= 0;
            expected_valid <= 0; expected_pc <= 0; expected_stack <= 0;
            expected_identity <= 0; expected_generation <= 0; expected_address <= 0;
            fault <= 0; fault_code <= 0; es_sv <= 0; es_addr <= 0;
            late_addr <= 0; late_live_c <= 0;
        end else begin
            expected_valid <= 0; native_kv <= 0; late_live_c <= 0;
            if (slot && !program_ok) begin fault <= 1; fault_code[4] <= 1; end
            if (wv != slot) begin fault <= 1; fault_code[0] <= 1; end
            if (slot && !identity_ok) begin fault <= 1; fault_code[1] <= 1; end
            if (slot && wv && !header_ok) begin fault <= 1; fault_code[2] <= 1; end
            if (slot && !pair_ok) begin fault <= 1; fault_code[3] <= 1; end
            if (hi_slot) begin
                expected_valid <= 4'hf;
                expected_stack <= ci[14:13];
                expected_identity <= ci; expected_generation <= cg;
                expected_address <= {19'd64 + {13'd0,(ci[42:37]-6'd1)},
                                     ix[1],1'b0,ci[12],ci[10:9],ci[18:15],ci[11]};
                write_mask <= {1024{1'b1}};
                if (MUT == 3) write_mask[0] <= 0;
                native_kv <= 4'hf;
                expected_pc <= {group_of(ci[8:6]), 2'd3, group_of(ci[8:6]), 2'd2,
                                group_of(ci[8:6]), 2'd1, group_of(ci[8:6]), 2'd0};
                es_sv <= 1;
                es_addr <= {bank, column, row ^ ((MUT == 2) ? 19'd1 : 19'd0)};
                if (MUT == 6) begin late_addr <= {bank, column, row}; late_live_c <= 1; end
            end
            if (MUT == 6 && late_live_c) begin es_sv <= 1; es_addr <= late_addr; end
        end
    end

    // ---- regions 2/3: low-half payload, captured on the compiled slot alone
    // (2 registered bits), not on the 59-bit identity/pair/program compares
    // (r2 structure: a bad low half leaves half_live 0 -> !pair_ok -> w_v 0 + fault).
    genvar h;
    generate
        for (h = 0; h < 2; h = h + 1) begin : g_half
            always @(posedge ck or negedge rr[2+h])
                if (!rr[2+h]) half_data[256*h +: 256] <= 0;
                else if (slot && !ix[0]) half_data[256*h +: 256] <= wd[256*h +: 256];
        end
    endgenerate

    // ---- regions 4..11: two per es lane: rr[4+2q] = data[127:0] + w_v (129 flops),
    // rr[5+2q] = data[255:128] (128 flops).  The relay copy sits beside its half-lane.
    // es lane q, LSB first: w_v, data256, row19, col5, bank5, s_we, s_v.
    genvar q;
    generate
        for (q = 0; q < 4; q = q + 1) begin : g_lane
            reg [255:0] es_data, late_data;   // late_data: MUT6 only
            reg es_wv, late_wv, late_live;
            always @(posedge ck or negedge rr[4+2*q]) begin
                if (!rr[4+2*q]) begin
                    es_data[127:0] <= 0; late_data[127:0] <= 0;
                    es_wv <= 0; late_wv <= 0; late_live <= 0;
                end else begin
                    es_wv <= 0; late_live <= 0;
                    if (hi_slot) begin
                        es_data[127:0] <= assembled_row[256*q +: 128] ^ ((MUT == 1 && q == 0) ? 128'd1 : 128'd0);
                        es_wv <= good && !(MUT == 5 && q == 0) && MUT != 6;
                        if (MUT == 6) begin
                            late_wv <= good; late_live <= 1; late_data[127:0] <= assembled_row[256*q +: 128];
                        end
                    end
                    if (MUT == 6 && late_live) begin es_wv <= late_wv; es_data[127:0] <= late_data[127:0]; end
                end
            end
            always @(posedge ck or negedge rr[5+2*q]) begin
                if (!rr[5+2*q]) begin
                    es_data[255:128] <= 0; late_data[255:128] <= 0;
                end else begin
                    if (hi_slot) begin
                        es_data[255:128] <= assembled_row[256*q+128 +: 128];
                        if (MUT == 6) late_data[255:128] <= assembled_row[256*q+128 +: 128];
                    end
                    if (MUT == 6 && late_live) es_data[255:128] <= late_data[255:128];
                end
            end
            assign es[288*q +: 288] = {es_sv, es_sv, es_addr, es_data, es_wv};
        end
    endgenerate
endmodule
