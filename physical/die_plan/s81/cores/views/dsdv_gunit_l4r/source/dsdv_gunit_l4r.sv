`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT3 (2026-10-17): dsdv_gunit_l4r -- G-unit side leaf L4r (E of L4): the HC norm's r chain, split out of L4
// (the one-leaf L4 was 21,174 sinks on one root, TT insertion 436 ps: clock-rule FAIL).
//     ss -> ot_dsrom_divc (/ 20,480) -> + eps (ot_dsrom_qadd) -> ot_dsrom_rsqrt -> r        (unchanged units, unchanged
// association: tools/hdc_golden_v41.Model.hc_mixes).  W face only (L4): ss_v / ss / eps_c land in input flops (eps_c
// is the job's set's eps, static during the job), r leaves from an output flop with its valid; fault (sticky) = a
// divider / adder / rsqrt fault.  +2 edges against the one-leaf chain (+1 more in L4's input flop).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l4r #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ss_v, input wire [31:0] ss, input wire [31:0] eps_c,
    output reg           r_v, output reg [31:0] r_y, output reg r_f
);
    localparam integer LA = 4, LM = 5;
    // reset relay (S81U-GUNIT4): the rst_n port drives only ot_rst_relay; 3 kept region copies (each <= ~256
    // reset loads, no port net spans the leaf).  Release is 3 edges after the port (transaction-level exact).
    wire [2:0] rq;
    ot_rst_relay #(.REGIONS(3)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    reg sv; reg [31:0] sx, ep;
    always @(posedge clk or negedge rq[0]) if (!rq[0]) sv <= 1'b0; else sv <= ss_v;
    always @(posedge clk) begin sx <= ss; ep <= eps_c; end
    wire [31:0] mq, me, rr; wire mq_v, me_v, rr_v, f_div, f_eps, f_rsq; wire [LA:0] ve;
    ot_dsrom_divc #(.F(5), .K(12)) u_div (.clk(clk), .rst_n(rq[0]), .v(sv), .x(sx), .y(mq), .vo(mq_v), .fault(f_div));
    ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rq[1]), .v(mq_v), .vd(ve));
    ot_dsrom_qadd #(.LAT(LA)) u_eps (clk, rq[1], mq_v, mq, ep, me, f_eps);
    assign me_v = ve[LA];
    ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rq[2]), .v(me_v), .x(me), .y(rr), .vo(rr_v), .fault(f_rsq));
    // S81-KITS-RTLB 10-24 (owner: register every pin, in RTL): the sticky r_f flop fed its own D and the
    // port (face_guard 'shared').  r_fs (kept) holds the sticky state; r_f is a pin-only flop loaded with r_fs's next
    // value, so r_f == r_fs every cycle (0 cycles).
    (* keep *) reg r_fs;
    wire r_fn = r_fs | f_div | f_eps | f_rsq;
    always @(posedge clk or negedge rq[2])
        if (!rq[2]) begin r_v <= 1'b0; r_f <= 1'b0; r_fs <= 1'b0; end
        else begin
            r_v <= rr_v; r_fs <= r_fn;
`ifdef OT_RTLB_PINFLOP_MUT
            r_f <= f_div | f_eps | f_rsq;                  // mutant: pin flop not sticky
`else
            r_f <= r_fn;
`endif
        end
    always @(posedge clk) r_y <= rr;
endmodule
