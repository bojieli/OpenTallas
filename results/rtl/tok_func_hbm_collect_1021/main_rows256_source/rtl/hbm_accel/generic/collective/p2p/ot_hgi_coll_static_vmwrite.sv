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
// Pin-captured fault (2026-10-15, structural fix of the CTS gate's TT
// input->fault -210.1 ps over 19 paths, worst slot_owner->fault 8 levels):
// every port that feeds a check (sid, ingress_slot, slot_valid, slot_owner,
// rgx_vm) is captured in a pin flop and every check is evaluated one edge
// later from registers only (the per-bank decode of this edge's launch is
// registered alongside). The sticky fault therefore rises at edge C+1 for a
// violation presented at edge C (was C). Data path, kq, launch_done and the
// compiler calendar are unchanged; fault is a diagnostic/exception output that
// never steers execution. MUT=3 delays the fault one more edge (bench rejects).
// MUT=4 drops the high-sector +1 bank rotation, MUT=5 skews the low relay.
// Two-stage launch (v4, 2026-10-15 17:30, structural fix of the v2 route:
// TT reg->reg -26.49 ps on 12 kq endpoints = a0 sector decode -> 281-bit
// fanout -> 10-way AND-OR across the 103.68 x 388.8 pin-limited slot, and
// native capture 328.3 ps > 190 on rst_n = async reset net from the pin).
// (1) Relay edge: every bank select is decoded once into a registered
// one-hot (sel_lo/sel_hi, 80 FF) together with a registered copy of the
// operand sector/payload/mask; kq is an AND-OR of registers only. Launch
// moves one edge later: low sector at C+2, high at C+3, launch_done at C+3
// (compiler write-visibility +1 edge). The checks, their pin capture and
// fault timing (C+1) are unchanged.
// (2) rst_n reaches exactly one pin flop (async assert, sync deassert);
// every other reset flop is reset from that register.
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
    // Relay edge registers (launch stage inputs).
    reg [39:0] sel_lo, sel_hi;          // [l*8+b] one-hot bank selects
    reg [79:0] sec_lo, sec_hi;          // [l*16] sectors (high = +1)
    reg [1279:0] pay_lo, pay_hi;        // [l*256]
    reg [39:0] msk_lo, msk_hi;          // [l*8]
    reg [4:0] v2r;                      // high-half valid for launch_done
    reg [39:0] dsel_lo, dsel_hi;
    reg [8*281-1:0] launch_kq;
    reg rst_q;
    reg [7:0] used;
    reg schedule_bad;
    integer l, h, b;
    reg [15:0] sector;
    reg present;
    reg [3:0] owner;
    // Per-bank launch decode of this edge (registered for the C+1 check).
    reg [31:0] bank_owner; // owner id launched in each bank (OR on conflict)
    reg [7:0] bank_multi;  // two contributors in one bank
    // Pin-captured check inputs (0 logic levels from the port).
    reg [1:0] sid_q;
    reg [4:0] islot_q;
    reg [7:0] sv_q;
    reg [31:0] so_q;
    reg vm_q;
    reg [7:0] used_q, multi_q;
    reg [31:0] bown_q;
    reg addr_bad, sched_bad_q, addr_bad_q;
    always @* begin
        used = '0; schedule_bad = 1'b0; bank_owner = '0; bank_multi = '0;
        // Constant destination slices avoid a 2,248-bit dynamic scatter
        // network. Each physical bank has ten decoded contributors; valid
        // programmes select at most one. Conflicts remain visible as OR data
        // plus the same sticky schedule fault, without changing the calendar.
        for (b = 0; b < 8; b = b + 1) begin
          for (h = 0; h < 2; h = h + 1) begin
            for (l = 0; l < 5; l = l + 1) begin
                present = h == 0 ? v0[l] : v1[l];
                sector = h == 0 ? a0[l*40+3 +: 16] : a1[l*40+3 +: 16] + 16'd1;
                owner = 4'(l + 5*h);
                if (present && sector[2:0] == 3'(b)) begin
                    if (used[b]) bank_multi[b] = 1'b1;
                    bank_owner[b*4 +: 4] = bank_owner[b*4 +: 4] | owner;
                    used[b] = 1'b1;
                end
            end
          end
        end
        dsel_lo = '0; dsel_hi = '0;
        for (l = 0; l < 5; l = l + 1)
            for (b = 0; b < 8; b = b + 1) begin
                if (v0[l] && a0[l*40+3 +: 3] == 3'(b)) dsel_lo[l*8+b] = 1'b1;
                if (v1[l] && 3'(a1[l*40+3 +: 3] + (MUT == 4 ? 3'd0 : 3'd1)) == 3'(b)) dsel_hi[l*8+b] = 1'b1;
            end
        launch_kq = '0;
        for (b = 0; b < 8; b = b + 1)
            for (l = 0; l < 5; l = l + 1) begin
                if (sel_lo[l*8+b]) launch_kq[b*281 +: 281] = launch_kq[b*281 +: 281] |
                    {1'b1,sec_lo[l*16 +: 16],pay_lo[l*256 +: 256],msk_lo[l*8 +: 8]};
                if (sel_hi[l*8+b]) launch_kq[b*281 +: 281] = launch_kq[b*281 +: 281] |
                    {1'b1,sec_hi[l*16 +: 16],pay_hi[l*256 +: 256],msk_hi[l*8 +: 8]};
            end
        // Checks from registers only: this edge's decode vs the captured
        // reservation of the previous edge (both describe the same launch).
        schedule_bad = (|multi_q) || (used_q != sv_q);
        for (b = 0; b < 8; b = b + 1)
            if (used_q[b] && bown_q[b*4 +: 4] != so_q[b*4 +: 4]) schedule_bad = 1'b1;
        // v0/a0 are the existing ingress capture registers (iv/ia at C).
        addr_bad = (v0 != islot_q) || ((|v0[3:0]) && !vm_q);
        for (l = 0; l < 5; l = l + 1)
            // Local main/mirror sector address space.
            // Existing COLL ABI encodes sector at address[18:3], not >>5.
            // Preserve that ABI exactly; high bits and low 3 must be zero.
            if (v0[l] && (a0[l*40 +: 3] != 0 || |a0[l*40+19 +: 21] ||
                (a0[l*40+18] ? a0[l*40+16 +: 2] != 0 : a0[l*40+16 +: 2] != sid_q) || &a0[l*40+3 +: 13]))
                addr_bad = 1'b1;
    end
    always @(posedge clk) begin
        a0 <= ia; a1 <= a0; d0 <= id; d1 <= d0; m0 <= im; m1 <= m0;
        // Pin capture: data-only flops, no reset (checks are gated by the
        // reset-cleared valid copies below).
        sid_q <= sid; so_q <= slot_owner; vm_q <= rgx_vm; bown_q <= bank_owner;
        for (l = 0; l < 5; l = l + 1) begin
            sec_lo[l*16 +: 16] <= a0[l*40+3 +: 16];
            sec_hi[l*16 +: 16] <= a1[l*40+3 +: 16] + 16'd1;
            // MUT=5: relay-stage skew (low payload taken one edge late).
            pay_lo[l*256 +: 256] <= MUT == 5 ? d1[l*512 +: 256] : d0[l*512 +: 256];
            pay_hi[l*256 +: 256] <= d1[l*512+256 +: 256];
            msk_lo[l*8 +: 8] <= m0[l*16 +: 8];
            msk_hi[l*8 +: 8] <= m1[l*16+8 +: 8];
        end
        kq <= launch_kq;
        // Test-only corruption demonstrates that the data scoreboard is live.
        if (MUT == 1) kq[8] <= ~launch_kq[8];
    end
    // The only flop on the rst_n pin: async assert, sync deassert.
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rst_q <= 1'b0; else rst_q <= 1'b1;
    always @(posedge clk or negedge rst_q) begin
        if (!rst_q) begin
            v0 <= 0; v1 <= 0; v2r <= 0; launch_done <= 0; fault <= 0;
            sel_lo <= 0; sel_hi <= 0;
            islot_q <= 0; sv_q <= 0; used_q <= 0; multi_q <= 0; sched_bad_q <= 0; addr_bad_q <= 0;
        end else begin
            v0 <= iv; v1 <= v0; v2r <= v1; launch_done <= v2r;
            sel_lo <= dsel_lo; sel_hi <= dsel_hi;
            // Reservation/launch check state is reset so no check fires from
            // pre-reset values; so_q/sid_q/vm_q are only read under a reset-
            // cleared valid (used_q, v0).
            islot_q <= ingress_slot; sv_q <= slot_valid;
            used_q <= used; multi_q <= bank_multi;
            sched_bad_q <= schedule_bad; addr_bad_q <= addr_bad;
            if (MUT == 3) begin
                if (sched_bad_q || addr_bad_q) fault <= 1;
            end else if ((schedule_bad && MUT != 2) || addr_bad) fault <= 1;
        end
    end
endmodule
`default_nettype wire
