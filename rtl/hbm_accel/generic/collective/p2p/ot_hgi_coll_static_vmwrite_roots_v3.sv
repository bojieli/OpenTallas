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
// PREPARATORY v3: fourteen independently delivered same-phase clock roots.
// All logical edges must align after each entry's own phi-R compensation.
// No clock is forwarded or generated here. Data/calendar/fault timing equal v2.
// Physical/native qualification and typed entry grants remain separate gates.
module ot_hgi_coll_static_vmwrite_roots_v3 #(
    parameter integer MUT = 0
) (
    input wire [4:0] clk_ingress,
    input wire [7:0] clk_bank,
    input wire clk_meta, rst_n,
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
    output wire [8*281-1:0] kq,
    output reg [4:0] launch_done,
    output reg fault
);
    wire [4:0] iv = {tkw_v,rgx_v};
    wire [199:0] ia = {tkw_d[567:528],rgx_addr};
    wire [2559:0] id = {tkw_d[511:0],rgx_data};
    wire [79:0] im = {tkw_d[527:512],64'hffffffffffffffff};
    wire [4:0] v0, v1;
    wire [199:0] a0, a1;
    wire [2559:0] d0, d1;
    wire [79:0] m0, m1;
    reg [8*281-1:0] next_kq;
    reg [7:0] used;
    reg schedule_bad;
    integer l, h, b;
    reg [15:0] sector;
    reg [255:0] payload;
    reg [7:0] mask;
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
    wire [7:0] used_q, multi_q;
    wire [31:0] bown_q;
    reg addr_bad, sched_bad_q, addr_bad_q;
    always @* begin
        next_kq = '0; used = '0; schedule_bad = 1'b0; bank_owner = '0; bank_multi = '0;
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
                    if (used[b]) bank_multi[b] = 1'b1;
                    bank_owner[b*4 +: 4] = bank_owner[b*4 +: 4] | owner;
                    used[b] = 1'b1;
                    next_kq[b*281 +: 281] = next_kq[b*281 +: 281] | {1'b1,sector,payload,mask};
                end
            end
          end
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
    // Five physical input groups. Each high-half staging register stays with
    // its producer capture root; no new data register or logical edge.
    for (genvar g = 0; g < 5; g = g + 1) begin : g_ingress
        reg [39:0] a0_l, a1_l;
        reg [511:0] d0_l, d1_l;
        reg [15:0] m0_l, m1_l;
        reg v0_l, v1_l;
        assign a0[g*40 +: 40] = a0_l;
        assign a1[g*40 +: 40] = a1_l;
        assign d0[g*512 +: 512] = d0_l;
        assign d1[g*512 +: 512] = d1_l;
        assign m0[g*16 +: 16] = m0_l;
        assign m1[g*16 +: 16] = m1_l;
        assign v0[g] = v0_l;
        assign v1[g] = v1_l;
        always @(posedge clk_ingress[g]) begin
            a0_l <= ia[g*40 +: 40]; a1_l <= a0_l;
            d0_l <= id[g*512 +: 512]; d1_l <= d0_l;
            m0_l <= im[g*16 +: 16]; m1_l <= m0_l;
        end
        always @(posedge clk_ingress[g] or negedge rst_n) begin
            if (!rst_n) begin v0_l <= 0; v1_l <= 0; end
            else begin v0_l <= iv[g]; v1_l <= v0_l; end
        end
    end
    // rgx_vm is a W-face input beside RGX3, rather than a remote N capture.
    always @(posedge clk_ingress[3]) vm_q <= rgx_vm;
    // Each bank's output and delayed check decode share a local E-face root.
    for (genvar g = 0; g < 8; g = g + 1) begin : g_bank
        reg [280:0] kq_l;
        reg [3:0] bown_l;
        reg used_l, multi_l;
        assign kq[g*281 +: 281] = kq_l;
        assign bown_q[g*4 +: 4] = bown_l;
        assign used_q[g] = used_l;
        assign multi_q[g] = multi_l;
        always @(posedge clk_bank[g]) begin
            kq_l <= next_kq[g*281 +: 281];
            bown_l <= bank_owner[g*4 +: 4];
            if (MUT == 1 && g == 0) kq_l[8] <= ~next_kq[8];
        end
        always @(posedge clk_bank[g] or negedge rst_n) begin
            if (!rst_n) begin used_l <= 0; multi_l <= 0; end
            else begin used_l <= used[g]; multi_l <= bank_multi[g]; end
        end
    end
    // The six diagnostic/completion outputs live beside their E-face pins.
    always @(posedge clk_bank[7] or negedge rst_n) begin
        if (!rst_n) begin launch_done <= 0; fault <= 0; end
        else begin
            launch_done <= v1;
            if (MUT == 3) begin
                if (sched_bad_q || addr_bad_q) fault <= 1;
            end else if ((schedule_bad && MUT != 2) || addr_bad) fault <= 1;
        end
    end
    // Forty-seven production flops capture the N-face reservation metadata.
    always @(posedge clk_meta) begin sid_q <= sid; so_q <= slot_owner; end
    always @(posedge clk_meta or negedge rst_n) begin
        if (!rst_n) begin
            islot_q <= 0; sv_q <= 0; sched_bad_q <= 0; addr_bad_q <= 0;
        end else begin
            islot_q <= ingress_slot; sv_q <= slot_valid;
            sched_bad_q <= schedule_bad; addr_bad_q <= addr_bad;
        end
    end
endmodule
`default_nettype wire
