`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hep_rx_store (H-LKEP 2026-10-15, route-2 structural fix): the endpoint's copy of H-COLL's off-die elastic RX
// pingpong (ot_hgi_coll_offdie_rx_pingpong / _rx_block, 6a31444da) with the SAME cycle contract (slot S -> bank pin
// S+3 -> merged pin S+4, fill / seal / ready / drain / flush, the same faults and MUT plumbing), restructured for timing:
//
//  * route 1 (hep_static_ref_1015-ep1-b58969306) EARLY_FAIL_HOLD stuck at FF -79 ps on u_block.pin_flit[484]/D for 4,800
//    hold iterations: the block's pin_flit D pin is a 2:1 enable mux whose select vp[2] is ONE flop fanning out to 612
//    flops across the macro channel (SS setup slack at that D pin +62 ps in the gate), while its data leg dout -> pin_flit
//    is a short hop that needs >= +109 ps FF delay (skew + 30 ps margin) -> every hold buffer breaks setup.  Same shape
//    at the pingpong merge (pv select fanning out 612) and at the SRAM leaf (6-bit address compare selecting a bypass for
//    306 dout bits).
//  * fix: every wide-register select is a REPLICATED register per 64-bit slice (keep), loaded one edge early from the
//    same next-state, so a select drives <= 64 loads and the data leg has hundreds of ps of setup slack for hold
//    buffers; the leaf drops the write->read bypass (it can never fire here: a block is read only after FILL -> SEAL (two
//    edges, the write capture + macro commit) -> READY -> release, and refilled only after FLUSH), so dout <= rd_out is
//    a plain macro -> flop hop; data registers carry no reset.
// The H-COLL module files are untouched (their jobs keep their source binding).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hep_rx_leaf #(parameter integer W = 306, parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          we,
    input  wire [5:0]    wa,
    input  wire [5:0]    ra,
    input  wire [W-1:0]  din,
    output reg  [W-1:0]  dout
);
    reg wq; reg [5:0] aq; reg [W-1:0] dq;
    wire [511:0] mr;
    always @(posedge ck) begin wq <= we; aq <= wa; dq <= din; end
    ot_sram_1r1w_64x512_m1_r2c2 u_sram (
        .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr),
        .w_ce_in(wq), .w_addr_in(aq), .wd_in({{(512-W){1'b0}}, dq}),
        .w_mask_in({{(512-W){1'b0}}, {W{1'b1}}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(18'd0));
    always @(posedge ck) dout <= mr[W-1:0] ^ (MUT != 0 ? {{(W-1){1'b0}}, 1'b1} : {W{1'b0}});
endmodule

module ot_hep_rx_block #(parameter integer MUT = 0) (
    input  wire          clk, rst_n,
    input  wire          arm_v,
    input  wire [6:0]    block_words,
    input  wire          phy_v,
    input  wire [611:0]  phy_flit,
    output wire          phy_ready,
    output wire          block_ready,
    input  wire          release_v,
    input  wire          slot_v,
    input  wire [5:0]    slot_index,
    output reg           pin_v,
    output wire [9:0]    pin_vr,        // replicated copies of pin_v, one per 64-b slice (the pingpong merge selects)
    output reg  [611:0]  pin_flit,
    output reg           fault,
    output reg  [4:0]    fault_cause
);
    localparam integer SL = 64, NSL = 10;
    localparam [2:0] EMPTY = 0, FILL = 1, SEAL = 2, READY = 3, DRAIN = 4, FLUSH = 5;
    reg [2:0] state;
    reg [6:0] count, words, issued;
    reg seal_age;
    reg [1:0] flush_age;
    reg [5:0] ra;
    reg [1:0] vp;                       // issue -> +1 -> +2 (vp2r is the +3 select, pvr / pin_v the +4 valid)
    (* keep *) reg [NSL-1:0] vp2r;
    (* keep *) reg [NSL-1:0] pvr;
    wire accept = phy_v && phy_ready;
    wire [611:0] mem_data;
    wire issue = slot_v && state == DRAIN && issued < words && slot_index == issued[5:0];
    assign phy_ready = state == FILL && count < words && !fault;
    assign block_ready = (state == READY) || (MUT == 2 && state == FILL && count != 0);
    assign pin_vr = pvr;
    for (genvar b = 0; b < 2; b = b + 1) begin : g_mem
        ot_hep_rx_leaf #(.W(306), .MUT((MUT == 1 && b == 0) ? 1 : 0)) u_mem (
            .ck(clk), .we(accept), .wa(count[5:0]), .ra(ra),
            .din(phy_flit[b*306 +: 306]), .dout(mem_data[b*306 +: 306]));
    end
    integer j;
    always @(posedge clk)
        for (j = 0; j < 612; j = j + 1) if (vp2r[j / SL]) pin_flit[j] <= mem_data[j];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= EMPTY; count <= 0; words <= 0; issued <= 0; seal_age <= 0; flush_age <= 0;
            ra <= 0; vp <= 0; vp2r <= 0; pvr <= 0; pin_v <= 0; fault <= 0; fault_cause <= 0;
        end else begin
            vp <= {vp[0], issue};
            vp2r <= {NSL{vp[1]}};
            pvr <= vp2r; pin_v <= vp2r[0];
            if (issue) ra <= slot_index;
            if (arm_v && (state != EMPTY || block_words == 0 || block_words > 64)) begin fault <= 1; fault_cause[0] <= 1; end
            if (release_v && !block_ready) begin fault <= 1; fault_cause[1] <= 1; end
            if (slot_v && !issue) begin fault <= 1; fault_cause[2] <= 1; end
            if (arm_v && state == EMPTY && block_words >= 1 && block_words <= 64) begin
                state <= FILL; count <= 0; words <= block_words; issued <= 0;
            end
            if (accept) begin
                count <= count + 1'b1;
                if (count + 1'b1 == words) begin state <= SEAL; seal_age <= 0; end
            end
            if (state == SEAL) begin
                seal_age <= 1;
                if (seal_age) state <= READY;
            end
            if (release_v && block_ready) begin state <= DRAIN; issued <= 0; end
            if (issue) begin
                issued <= issued + 1'b1;
                if (issued + 1'b1 == words) begin state <= FLUSH; flush_age <= 0; end
            end
            if (state == FLUSH) begin
                flush_age <= flush_age + 1'b1;
                if (flush_age == 3) state <= EMPTY;
            end
        end
    end
endmodule

module ot_hep_rx_pingpong #(parameter integer MUT = 0) (
    input  wire          clk, rst_n,
    input  wire          arm_v, arm_bank,
    input  wire [6:0]    block_words,
    input  wire          phy_v,
    input  wire [611:0]  phy_flit,
    output wire          phy_ready,
    output wire [1:0]    block_ready,
    input  wire          release_v, release_bank,
    input  wire          slot_v, slot_bank,
    input  wire [5:0]    slot_index,
    output reg           pin_v,
    output reg  [611:0]  pin_flit,
    output wire          fault,
    output wire [6:0]    fault_cause
);
    localparam integer SL = 64;
    reg fill_bank, drain_bank, drain_active, flushing;
    reg [6:0] words [0:1];
    reg [6:0] drain_words;
    reg [2:0] flush_age;
    reg [1:0] ctl_fault;
    wire [1:0] ready, pv, bfault;
    wire [19:0] pvr;
    wire [9:0] bcause;
    wire [1223:0] pd;
    wire arm_ok = arm_v && !phy_ready;
    wire release_ok = release_v && !drain_active && block_ready[release_bank];
    wire slot_ok = slot_v && drain_active && !flushing && slot_bank == drain_bank;
    assign phy_ready = ready[fill_bank] && !fault;
    assign fault = (|bfault) || (|ctl_fault);
    assign fault_cause = {ctl_fault, bcause[4:0] | bcause[9:5]};
    for (genvar b = 0; b < 2; b = b + 1) begin : g_block
        ot_hep_rx_block #(.MUT((MUT == 1 && b == 0) ? 1 : 0)) u_block (
            .clk(clk), .rst_n(rst_n), .arm_v(arm_ok && arm_bank == b), .block_words(block_words),
            .phy_v(phy_v && ((MUT == 3 && drain_active) ? !fill_bank : fill_bank) == b && !fault), .phy_flit(phy_flit),
            .phy_ready(ready[b]), .block_ready(block_ready[b]), .release_v(release_ok && release_bank == b),
            .slot_v(slot_ok && ((MUT == 2 ? !drain_bank : drain_bank) == b)), .slot_index(slot_index),
            .pin_v(pv[b]), .pin_vr(pvr[b*10 +: 10]), .pin_flit(pd[b*612 +: 612]), .fault(bfault[b]),
            .fault_cause(bcause[b*5 +: 5]));
    end
    // final registered merge: slot -> bank pin +3 -> merged pin +4; each 64-b slice selects with its own valid copies
    integer j;
    always @(posedge clk)
        for (j = 0; j < 612; j = j + 1)
            if (pvr[j / SL] | pvr[10 + j / SL])
                pin_flit[j] <= (pvr[j / SL] & pd[j]) | (pvr[10 + j / SL] & pd[612 + j]);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fill_bank <= 0; drain_bank <= 0; drain_active <= 0; flushing <= 0;
            words[0] <= 0; words[1] <= 0; drain_words <= 0; flush_age <= 0; ctl_fault <= 0; pin_v <= 0;
        end else begin
            pin_v <= |pv;
            if (arm_v && !arm_ok) ctl_fault[0] <= 1;
            if (release_v && !release_ok) ctl_fault[1] <= 1;
            if (slot_v && !slot_ok) ctl_fault[1] <= 1;
            if (arm_ok) begin fill_bank <= arm_bank; words[arm_bank] <= block_words; end
            if (release_ok) begin
                drain_bank <= release_bank; drain_active <= 1; flushing <= 0; drain_words <= words[release_bank];
            end
            if (slot_ok && {1'b0, slot_index} + 1'b1 == drain_words) begin flushing <= 1; flush_age <= 0; end
            if (flushing) begin
                flush_age <= flush_age + 1'b1;
                if (flush_age == 4) begin drain_active <= 0; flushing <= 0; end
            end
        end
    end
endmodule
`default_nettype wire
