`timescale 1ns/1ps
// DS-ROM 1M: one quantiser instance on one node's golden blocks, back to back (no bubbles), timed.
// Same file formats as rtl/test/tb_hdc_v41_quant.sv (tools/rtl_hdc_v41_blockdot_campaign.py aq_expect/q4_expect):
//   ot_hdc_actquant  aq_in.mem  {mode[3:0], x[1023:0]}   aq_exp.mem {fault[3:0], e[11:0], q[255:0], y[511:0]}
//   ot_hdc_fp4qdq    q4_in.mem  {x[1023:0]}              q4_exp.mem {fault[3:0], y[511:0]}
// +NAQ / +NQ4: block counts (one of them per run).  Prints the cycle of the first accepted input and of the last
// valid output (first block in -> last block out = last_out - first_in + 1).  tools/dsrom_1m_su.py quant drives it.
//
// WIRED variant (tools/dsrom_1m_su_cdcq.py qwired): the plus-hub network stages of the stream unit's 'wired' bench
// (rtl/hdc/v41x/ot_hdc_v41x_vec.sv BCAST_STAGES / RET_STAGES: control broadcast 6 + operand read 16 = 22 on the issue
// side, element write 15 on the return side) as RTL register stages around the quantiser: every input beat crosses
// BCAST register stages before the unit and every output beat RET register stages after it, so first block in ->
// last block out includes them (simulated, not added).
module tb_dsrom_1m_quant_wired #(parameter integer BCAST = 22, parameter integer RET = 15);
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg [1027:0] aq_in  [0:4095];
    reg [783:0]  aq_exp [0:4095];
    reg [1023:0] q4_in  [0:4095];
    reg [515:0]  q4_exp [0:4095];
    integer naq = 0, nq4 = 0;
    initial begin
        if (!$value$plusargs("NAQ=%d", naq)) naq = 0;
        if (!$value$plusargs("NQ4=%d", nq4)) nq4 = 0;
        if (naq > 0) $readmemh("aq_in.mem", aq_in, 0, naq - 1);
        if (naq > 0) $readmemh("aq_exp.mem", aq_exp, 0, naq - 1);
        if (nq4 > 0) $readmemh("q4_in.mem", q4_in, 0, nq4 - 1);
        if (nq4 > 0) $readmemh("q4_exp.mem", q4_exp, 0, nq4 - 1);
    end
    reg rst_n = 1'b0;
    reg          a_v = 1'b0, a_fp4 = 1'b0, b_v = 1'b0;
    reg [1023:0] a_x = 0, b_x = 0;
    wire         a_vo, a_fault, b_vo, b_fault;
    wire [255:0] a_q;
    wire signed [9:0] a_e;
    wire [511:0] a_y, b_y;
    // issue side: BCAST register stages (valid + operand beat) between the bench's issue register and the unit
    reg  [1025:0] ia_st [0:BCAST];
    reg  [1024:0] ib_st [0:BCAST];
    always @* begin ia_st[0] = {a_v, a_fp4, a_x}; ib_st[0] = {b_v, b_x}; end
    genvar gs;
    generate for (gs = 0; gs < BCAST; gs = gs + 1) begin : g_bc
        always @(posedge clk) begin
            if (!rst_n) begin ia_st[gs + 1] <= '0; ib_st[gs + 1] <= '0; end
            else begin ia_st[gs + 1] <= ia_st[gs]; ib_st[gs + 1] <= ib_st[gs]; end
        end
    end endgenerate
    wire         ua_v = ia_st[BCAST][1025], ua_fp4 = ia_st[BCAST][1024], ub_v = ib_st[BCAST][1024];
    wire [1023:0] ua_x = ia_st[BCAST][1023:0], ub_x = ib_st[BCAST][1023:0];
    wire         ua_vo, ua_fault, ub_vo, ub_fault;
    wire [255:0] ua_q;
    wire signed [9:0] ua_e;
    wire [511:0] ua_y, ub_y;
    ot_hdc_actquant dut_a (.clk(clk), .rst_n(rst_n), .v(ua_v), .fp4(ua_fp4), .x(ua_x),
                           .vo(ua_vo), .q(ua_q), .e(ua_e), .y(ua_y), .fault(ua_fault));
    ot_hdc_fp4qdq   dut_b (.clk(clk), .rst_n(rst_n), .v(ub_v), .x(ub_x), .vo(ub_vo), .y(ub_y), .fault(ub_fault));
    // return side: RET register stages (valid + result beat) between the unit and the vector-memory write
    reg  [779:0] oa_st [0:RET];
    reg  [513:0] ob_st [0:RET];
    always @* begin oa_st[0] = {ua_vo, ua_fault, ua_e, ua_q, ua_y}; ob_st[0] = {ub_vo, ub_fault, ub_y}; end
    generate for (gs = 0; gs < RET; gs = gs + 1) begin : g_rt
        always @(posedge clk) begin
            if (!rst_n) begin oa_st[gs + 1] <= '0; ob_st[gs + 1] <= '0; end
            else begin oa_st[gs + 1] <= oa_st[gs]; ob_st[gs + 1] <= ob_st[gs]; end
        end
    end endgenerate
    assign a_vo = oa_st[RET][779]; assign a_fault = oa_st[RET][778]; assign a_e = oa_st[RET][777:768];
    assign a_q = oa_st[RET][767:512]; assign a_y = oa_st[RET][511:0];
    assign b_vo = ob_st[RET][513]; assign b_fault = ob_st[RET][512]; assign b_y = ob_st[RET][511:0];
    integer cyc = 0, ia = 0, ib = 0, oa = 0, ob = 0, ea = 0, eb = 0, idle = 0;
    integer first_in = -1, last_out = -1;
    reg [783:0] ex;
    reg [515:0] ey;
    always @(posedge clk) begin
        cyc = cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        a_v <= 1'b0; b_v <= 1'b0;
        if (cyc > 5) begin
            if (ia < naq) begin
                a_v <= 1'b1; a_fp4 <= aq_in[ia][1024]; a_x <= aq_in[ia][1023:0]; ia = ia + 1;
                if (first_in < 0) first_in = cyc + 1;          // registered into the unit on the next edge
            end
            if (ib < nq4) begin
                b_v <= 1'b1; b_x <= q4_in[ib]; ib = ib + 1;
                if (first_in < 0) first_in = cyc + 1;
            end
        end
        if (rst_n && a_vo) begin
            ex = aq_exp[oa];
            if (a_fault !== ex[780] || (!ex[780] && ({a_e, a_q, a_y} !== {ex[777:768], ex[767:0]}))) ea = ea + 1;
            oa = oa + 1; last_out = cyc;
        end
        if (rst_n && b_vo) begin
            ey = q4_exp[ob];
            if (b_fault !== ey[512] || (!ey[512] && b_y !== ey[511:0])) eb = eb + 1;
            ob = ob + 1; last_out = cyc;
        end
        if (ia == naq && ib == nq4) idle = idle + 1;
        if (idle == 40 + BCAST + RET) begin
            $display("DSQ naq=%0d checked=%0d errors=%0d nq4=%0d checked=%0d errors=%0d first_in=%0d last_out=%0d",
                     naq, oa, ea, nq4, ob, eb, first_in, last_out);
            if (ea == 0 && eb == 0 && oa == naq && ob == nq4) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule
