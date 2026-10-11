`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX index-key stream issuer (hgi-1010/g, 2026-10-10): at the start of an IDX.INDEX frame, one svc STREAM
// command per stack (quarter) so the index keys of this die arrive striped over all 32 PCs of each stack (svc IKS = 1,
// ot_hbm_svc_core kind-2 stripe; the rows land in ot_hbm_index_lines by (pc, j mod DEPTH) and leave on the 8 index-line
// ports to the stack's hfd_idx_score).  Replaces the legacy kind-2 read (4 sectors on IK_PC, ~1/32 of a stack).
//
//   keys of this die: n (imm_a of the record); blocks of 8 keys, nb = ceil(n / 8); quarter q owns die ordinals
//   [342 q, 342 q + 342) (the selector's quarter rule: quarter = ord div 342), so B_q = clamp(nb - 342 q, 0, 342).
//   A stack with B_q = 0 gets no command.
//   e command (one 128-bit beat {payload 127, valid} on the stack's e port, payload bit i = e_d[i + 1]):
//     [1:0] kind 2, [16:2] row0 (the key region's first DRAM row),
//     [69:61] B_q, [83:71] load tag (13 b), [125] no-credit, [126] STREAM; other bits zero.
//   Address map (writer = DMA.KVWB_DS index-key store, reader = this stream): logical byte g of the region (lines of
//   136 B, 4 lines a block): sector q = g / 32, pc = q mod 32, j = q div 32, DRAM sector =
//   ot_hbm_kport_map(pc, bank {j[9:7], j[1:0]}, row0 + (j >> 10), col j[6:2]); nsec per PC = ceil(17 B_q / 32).
//   row0 (lead decision 10-10): from the record's key-region descriptor base (HBM byte address, {stack 36:35,
//   sector 34:5, byte 4:0}): the region must start at logical sector 0 of a row, i.e. base[19:0] = 0 and the stack
//   field 0 (the descriptor names the set; quarter q's keys sit at the same row in stack q); row0 = base[34:20].
//   A misaligned base (base[19:0] != 0 or base[36:35] != 0) issues NOTHING and raises fault (sticky until rst_n).
//   go: one cycle; the commands leave on the next edge (registered, one beat per stack, all four in parallel).
//   MUT (bench): 1 = B_q from the previous quarter's split (off by one quarter) -> the stream must be refused / mismatch.
module ot_hgi_idx_iks_issue #(
    parameter integer QB = 342,             // blocks a quarter (2,736 keys / 8)
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go,
    input  wire [31:0]   n,                 // keys of this die
    input  wire [39:0]   ik_base,           // the record's key-region descriptor base (HBM byte address)
    input  wire [12:0]   tag,
    input  wire          no_credit,
    output reg  [511:0]  e_d,               // 4 x {payload 127, valid}
    output reg  [35:0]   blocks,            // 4 x 9: B_q issued (status / bench)
    output reg           fault              // misaligned key-region base (sticky)
);
    wire [28:0] nb = n[31:3] + {28'd0, |n[2:0]};
    function automatic [8:0] bq(input integer q);
        reg [29:0] lo;
        begin
            lo = q * QB;
            bq = (nb <= lo) ? 9'd0 : ((nb - lo) >= QB ? 9'(QB) : 9'(nb - lo));
        end
    endfunction
    integer q;
    wire misaligned = ik_base[19:0] != 20'd0 || ik_base[36:35] != 2'd0;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin e_d <= 512'd0; blocks <= 36'd0; fault <= 1'b0; end
        else begin
            for (q = 0; q < 4; q = q + 1) e_d[q * 128] <= 1'b0;
            if (go && misaligned) fault <= 1'b1;
            if (go && !misaligned) for (q = 0; q < 4; q = q + 1) begin : one
                reg [8:0] b; reg [126:0] p;
                b = bq((MUT == 1 && q > 0) ? q - 1 : q);
                p = 127'd0;
                p[1:0] = 2'd2; p[16:2] = ik_base[34:20]; p[69:61] = b; p[83:71] = tag; p[125] = no_credit; p[126] = 1'b1;
                e_d[q * 128 +: 128] <= {p, b != 9'd0};
                blocks[q * 9 +: 9] <= b;
            end
        end
    end
endmodule
`default_nettype wire
