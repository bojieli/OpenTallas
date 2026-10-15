`timescale 1ns/1ps
`default_nettype none
// Compiler-scheduled COLL -> VM fill-port transport. No queue, arbitration,
// credit, ready or retry exists here. Historical b2_vmport remains diagnostic.
// All clocks in this component share clk; physical relay stages must be added
// to the compiler calendar explicitly. Production shape: 4 x 512 RGX + 568 TKW.
// At rising edge C capture ingress. Registered kq low sector changes at C+1,
// high sector at C+2. A downstream synchronous bank samples those at C+2/C+3.
// launch_done denotes only the high-sector launch, NEVER SRAM commit.
// slot_valid/slot_owner describe the outputs to be launched at THIS edge:
// owners 0..4 = low sectors of lanes RGX0..3/TKW, 5..9 = high sectors.
// Fault checks do not alter launch timing. Invalid programs must be rejected;
// the OR payload in a conflicting bank is deliberately NOT priority selected.
module ot_hgi_coll_static_vmwrite #(
    parameter integer MUT = 0
) (
    input wire clk, rst_n,
    input wire [1:0] sid,
    input wire [3:0] rgx_v,
    input wire [159:0] rgx_addr,
    input wire [2047:0] rgx_data,
    input wire rgx_vm,
    input wire tkw_v,
    input wire [567:0] tkw_d,
    input wire [4:0] ingress_slot,
    input wire [7:0] slot_valid,
    input wire [31:0] slot_owner,
    output reg [8*281-1:0] kq,
    output reg [4:0] launch_done,
    output reg fault
);
    wire [4:0] iv = {tkw_v,rgx_v};
    wire [199:0] ia = {tkw_d[567:528],rgx_addr};
    wire [2559:0] id = {tkw_d[511:0],rgx_data};
    wire [79:0] im = {tkw_d[527:512],64'hffffffffffffffff};
    reg [4:0] v0, v1;
    reg [199:0] a0, a1;
    reg [2559:0] d0, d1;
    reg [79:0] m0, m1;
    reg [8*281-1:0] next_kq;
    reg [7:0] used;
    reg schedule_bad;
    integer l, h, b;
    reg [15:0] sector;
    reg [255:0] payload;
    reg [7:0] mask;
    reg present;
    reg [3:0] owner;
    always @* begin
        next_kq = '0; used = '0; schedule_bad = 1'b0;
        // Constant destination slices avoid a 2,248-bit dynamic scatter
        // network. Each physical bank has ten decoded contributors; valid
        // programmes select at most one. Conflicts remain visible as OR data
        // plus the same sticky schedule fault, without changing the calendar.
        for (b = 0; b < 8; b = b + 1) begin
          for (h = 0; h < 2; h = h + 1) begin
            for (l = 0; l < 5; l = l + 1) begin
                present = h == 0 ? v0[l] : v1[l];
                sector = h == 0 ? a0[l*40+3 +: 16] : a1[l*40+3 +: 16] + 16'd1;
                payload = h == 0 ? d0[l*512 +: 256] : d1[l*512+256 +: 256];
                mask = h == 0 ? m0[l*16 +: 8] : m1[l*16+8 +: 8];
                owner = 4'(l + 5*h);
                if (present && sector[2:0] == 3'(b)) begin
                    if (used[b] || !slot_valid[b] || slot_owner[b*4 +: 4] != owner) schedule_bad = 1'b1;
                    used[b] = 1'b1;
                    next_kq[b*281 +: 281] = next_kq[b*281 +: 281] | {1'b1,sector,payload,mask};
                end
            end
          end
        end
        if (used != slot_valid) schedule_bad = 1'b1;
    end
    always @(posedge clk) begin
        a0 <= ia; a1 <= a0; d0 <= id; d1 <= d0; m0 <= im; m1 <= m0;
        kq <= next_kq;
        // Test-only corruption demonstrates that the data scoreboard is live.
        if (MUT == 1) kq[8] <= ~next_kq[8];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin v0 <= 0; v1 <= 0; launch_done <= 0; fault <= 0; end
        else begin
            v0 <= iv; v1 <= v0; launch_done <= v1;
            if (iv != ingress_slot || (schedule_bad && MUT != 2) || ((|rgx_v) && !rgx_vm)) fault <= 1;
            for (integer j = 0; j < 5; j = j + 1) begin
                // Local main/mirror sector address space.
                // Existing COLL ABI encodes sector at address[18:3], not >>5.
                // Preserve that ABI exactly; high bits and low 3 must be zero.
                if (iv[j] && (ia[j*40 +: 3] != 0 || |ia[j*40+19 +: 21] ||
                    (ia[j*40+18] ? ia[j*40+16 +: 2] != 0 : ia[j*40+16 +: 2] != sid) || &ia[j*40+3 +: 13])) fault <= 1;
            end
        end
    end
endmodule
`default_nettype wire
