`timescale 1ns/1ps
// QC RED source/parent event (DIE-QC-63/RED 2026-11-02, OWNER 11-02 "ADOPT the QC RED source event as an explicit plan
// event, gated on equivalence/simulation PASS; reach problems fixed with added pipeline stages; tok/s loss accepted").
//
// Plan variant of the as-built su_c leaf qfd_dv_s5_red2_leaf (asbuilt.substitute_inst, same ports).  The reducer itself
// becomes the hard core u_core = qfd_dv_s5_red2_leaf #(HARD_PINREG 1) (every one of its 352 data pins on a private
// register; Codex qc-suc-1101 proof 0 data cycles); this wrapper is parent glue (flattened into the su_c partition):
//   * IN_STAGES reset-less register stages on every reducer input (the lane landing flops sit on the E/W faces, the
//     core in the middle of the partition: worst face->core 1164 um = 3 hops <= 388 um with 2 stages);
//   * OUT_STAGES register stages on red_we/red_addr/red_data (core S pins at y 579 -> branch driver near (560, 1320):
//     lead <= 1101 um = 4 hops <= 367 um with 3 stages).  The one red_* net then fans out to the x_ctl_o (x~100) and x_sc_o
//     (x~1000) N-face station flops 900 um apart: that last branch is >= 450 um (~485 um) from one driver whatever the
//     stage count (a per-destination driver needs a second port on the leaf, not available through substitute_inst);
//     recorded as the event's reach residual, 1 repeater per branch (<= 450 um rule);
//   * rd_v (consumer: the su8 sequencer idle term only) is the EXACT original rd_v, registered here from the un-relayed
//     inputs with the leaf's own reset release (2-flop land + rc), so su8 sees rd_v on the original edge;
//   * busy = exact rd_v OR rd_v of the last IN_STAGES edges OR core busy OR every pending output write.  The original
//     busy = the reducer pipeline (it starts with rd_v and ends with o_we); the core sees each word IN_STAGES edges
//     late, so the rd_v delay line bridges the edges until the core busy takes over and the output stages extend it
//     to the last delayed write: busy covers the original busy on every edge (su8 idle only later, never earlier) and
//     rises no earlier than it (stretch <= IN_STAGES+OUT_STAGES);
//   * fault = core fault (IN_STAGES edges later; sticky in su8).
// red_we/red_addr/red_data are the original stream exactly IN_STAGES+OUT_STAGES edges later (proved by
// results/qc_die63_red_1102/tb_red_event.sv against the unmodified as-built leaf).
module qfd_dv_s5_red2p1_leaf #(parameter integer IN_STAGES = 2, parameter integer OUT_STAGES = 3) (
    input  wire            ck,
    input  wire            rst_n,
    input  wire [7:0]      l_ov,
    input  wire [8*32-1:0] l_out,
    input  wire [1:0]      l_red0,
    input  wire            l_redsq0,
    input  wire            l_last0,
    input  wire [23:0]     l_raddr0,
    output wire            red_we,
    output wire [23:0]     red_addr,
    output wire [31:0]     red_data,
    output wire            rd_v,
    output wire            busy,
    output wire            fault
);
    localparam integer IW = 8 + 256 + 2 + 1 + 1 + 24;
    localparam integer OW = 1 + 24 + 32;
    wire c_we, c_rd_v, c_busy, c_fault;
    // reset release of the original leaf (qfd_dv_s5_red: qfd_dv_s5_rst2 land + rc)
    reg rs1, rs2, rc;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin rs1 <= 1'b0; rs2 <= 1'b0; end
        else begin rs1 <= 1'b1; rs2 <= rs1; end
    always @(posedge ck or negedge rs2) if (!rs2) rc <= 1'b0; else rc <= 1'b1;
    // the reduction valid of an input word (original: rd_v <= l_ov[0] && l_red0 != 0 behind the leaf's input pin
    // register; as-built k79 netlist: l_ov[0] pin flop u_1833 (reset rc) + unreset l_red0 pin flops u_2097/u_2098 ->
    // u_2125 (reset rc) -> rd_v flop u_6060 (reset rc) = 3 edges, reproduced here flop for flop)
    reg  rv_ov, rv_s2, rd_v_e;
    reg  [1:0] rv_red;
    always @(posedge ck) rv_red <= l_red0;
    always @(posedge ck or negedge rc)
        if (!rc) begin rv_ov <= 1'b0; rv_s2 <= 1'b0; rd_v_e <= 1'b0; end
        else begin rv_ov <= l_ov[0]; rv_s2 <= rv_ov && (rv_red != 2'd0); rd_v_e <= rv_s2; end
`ifdef OT_RED_MUT_RDV
    assign rd_v = c_rd_v;               // bench mutant: the relayed core rd_v (IN_STAGES late) must fail P3
`else
    assign rd_v = rd_v_e;
`endif
    // input stages
    wire [IW-1:0] i0 = {l_ov, l_out, l_red0, l_redsq0, l_last0, l_raddr0};
    reg  [IW-1:0] ir [0:IN_STAGES-1];
    reg  [IN_STAGES-1:0] rdq;           // rd_v of the last IN_STAGES edges (bridges until the core busy rises)
    integer j;
    always @(posedge ck) begin
        ir[0] <= i0;
        for (j = 1; j < IN_STAGES; j = j + 1) ir[j] <= ir[j-1];
    end
    always @(posedge ck or negedge rc)
        if (!rc) rdq <= {IN_STAGES{1'b0}};
        else rdq <= {rdq, rd_v_e};
    wire [IW-1:0] ic = ir[IN_STAGES-1];
    wire [23:0] c_addr;
    wire [31:0] c_data;
    qfd_dv_s5_red2_leaf #(.HARD_PINREG(1)) u_core (
        .ck(ck), .rst_n(rst_n),
        .l_ov(ic[IW-1 -: 8]), .l_out(ic[IW-9 -: 256]), .l_red0(ic[27:26]), .l_redsq0(ic[25]), .l_last0(ic[24]),
        .l_raddr0(ic[23:0]),
        .red_we(c_we), .red_addr(c_addr), .red_data(c_data), .rd_v(c_rd_v), .busy(c_busy), .fault(c_fault));
    // output stages (write strobe reset like the leaf's o_we, address/data reset-less like o_addr/o_data)
    reg [OW-2:0] orr [0:OUT_STAGES-1];
    reg [OUT_STAGES-1:0] ow;
    always @(posedge ck) begin
        orr[0] <= {c_addr, c_data};
        for (j = 1; j < OUT_STAGES; j = j + 1) orr[j] <= orr[j-1];
    end
    always @(posedge ck or negedge rc)
        if (!rc) ow <= {OUT_STAGES{1'b0}};
        else ow <= {ow, c_we};
    assign red_we = ow[OUT_STAGES-1];
    assign {red_addr, red_data} = orr[OUT_STAGES-1];
`ifdef OT_RED_MUT_BUSY
    assign busy = c_busy;               // bench mutant: busy without the relay/pending-write cover must fail P4
`else
    assign busy = rd_v_e || (|rdq) || c_busy || (|ow);
`endif
    assign fault = c_fault;
endmodule
