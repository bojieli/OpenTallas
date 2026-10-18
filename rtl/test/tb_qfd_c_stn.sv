`timescale 1ns/1ps
// S-QSTN (2026-10-18): per-master behavioural bench for the qfd_c_b16_dv fabric station tiles (rtl/physical/qcluster/
// qfd_c_stn.sv).  One master per build (+define+M_STN516 / M_STN514 / M_XSTN / M_XSTNW); random inputs every cycle,
// every output bit compared every cycle against an INDEPENDENT cycle model written here (not a copy of the RTL):
//   stn516 / stn514 : q(t+1) = d(t)
//   xstn / xstnw    : a_d(t+1) = b_d(t); tap_d[379:0](t+1) = b_d[379:0](t); tap_d[507:380] = 4 x {hold[16i+:16], 16'h0}
//                     with hold loaded on the fixed deadline (XOFF = 3 edges after a go passed the corridor register,
//                     then every IL = 8 edges) from this station's own TDM line (tag[3] && tag[2:0] == sidx -> xl lo,
//                     tag[7] && tag[6:4] == sidx -> xl hi) or the capture register; go / tag / reset / sidx exercised.
// Prints "STN_BENCH PASS <master> 0 errors in N cycles ..." or "STN_BENCH FAIL <master> <errors> errors ...".
module tb;
    reg ck = 1'b0;
    always #0.5 ck = ~ck;
    integer N;
    integer cyc = 0, errs = 0, shown = 0;
`ifdef M_STN516
    localparam integer W = 516;
    localparam string  NAME = "qfd_c_stn516";
`elsif M_STN514
    localparam integer W = 514;
    localparam string  NAME = "qfd_c_stn514";
`endif
`ifdef M_XSTN
  `define XS 1
    localparam string NAME = "qfd_c_xstn";
`elsif M_XSTNW
  `define XS 1
    localparam string NAME = "qfd_c_xstnw";
`endif

`ifndef XS
    reg  [W-1:0] d = '0;
    wire [W-1:0] q;
    reg  [W-1:0] m_q;
    reg          m_def = 1'b0;
  `ifdef M_STN516
    qfd_c_stn516 dut (.ck(ck), .d(d), .q(q));
  `else
    qfd_c_stn514 dut (.ck(ck), .d(d), .q(q));
  `endif
    always @(posedge ck) begin m_q = d; m_def = 1'b1; end
    integer i;
    reg [543:0] rnd;
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 20000;
        repeat (N) begin
            @(negedge ck);
            if (m_def && q !== m_q) begin
                errs = errs + 1;
                if (shown < 8) begin shown = shown + 1; $display("MISMATCH cyc %0d q^exp %h", cyc, q ^ m_q); end
            end
            for (i = 0; i < 544; i = i + 32) rnd[i +: 32] = $urandom;
            d = rnd[W-1:0];
            cyc = cyc + 1;
        end
        if (errs == 0) $display("STN_BENCH PASS %s 0 errors in %0d cycles width=%0d", NAME, cyc, W);
        else           $display("STN_BENCH FAIL %s %0d errors in %0d cycles width=%0d", NAME, errs, cyc, W);
        $finish;
    end
`else
    localparam integer IBW = 3 * 18 + 13 * 24 + 13;      // 379
    localparam integer CW  = 1 + IBW + 128 + 8;           // 516
    localparam integer TW  = 1 + IBW + 128;               // 508
    localparam integer IL = 8, XOFF = 3;
    reg          rst_n = 1'b0;
    reg  [2:0]   sidx = 3'd0;
    reg  [CW-1:0] b_d = '0;
    wire [CW-1:0] a_d;
    wire [TW-1:0] tap_d;
  `ifdef M_XSTN
    qfd_c_xstn  dut (.ck(ck), .rst_n(rst_n), .sidx(sidx), .b_d(b_d), .a_d(a_d), .tap_d(tap_d));
  `else
    qfd_c_xstnw dut (.ck(ck), .rst_n(rst_n), .sidx(sidx), .b_d(b_d), .a_d(a_d), .tap_d(tap_d));
  `endif
    // independent cycle model
    reg [CW-1:0] m_bq;  reg m_bq_def = 0;
    reg [IBW:0]  m_tq;
    reg [2:0]    m_sx;
    reg [63:0]   m_cap = 0;  reg m_cap_def = 0;
    reg [63:0]   m_hold = 0; reg m_hold_def = 0;
    integer      m_cnt = 0;  reg m_run = 0;
    integer      n_go = 0, n_tag = 0, n_hold = 0, n_rst = 0, n_sidx = 0;
    reg [127:0]  xl;  reg [7:0] tag;  reg ta, tb_;  reg [63:0] sel;
    always @(posedge ck) begin
        if (m_bq_def) begin
            xl  = m_bq[1 + IBW +: 128];
            tag = m_bq[1 + IBW + 128 +: 8];
            ta  = tag[3] && (tag[2:0] == m_sx);
            tb_ = tag[7] && (tag[6:4] == m_sx);
            sel = ta ? xl[63:0] : xl[127:64];
            if (rst_n && m_run && m_cnt == 0) begin              // the fixed deadline
                if (ta || tb_) begin m_hold = sel; m_hold_def = 1; end
                else begin m_hold = m_cap; m_hold_def = m_cap_def; end
                n_hold = n_hold + 1;
            end
            if (ta || tb_) begin m_cap = sel; m_cap_def = 1; n_tag = n_tag + 1; end
            if (!rst_n) begin m_cnt = 0; m_run = 0; end
            else if (m_bq[0]) begin m_cnt = XOFF - 2; m_run = 1; n_go = n_go + 1; end
            else if (m_run) m_cnt = (m_cnt == 0) ? IL - 1 : m_cnt - 1;
        end else if (!rst_n) begin m_cnt = 0; m_run = 0; end
        m_bq = b_d; m_bq_def = 1;
        m_tq = b_d[IBW:0];
        m_sx = sidx;
    end
    function automatic [127:0] xo_of(input [63:0] h);
        integer k;
        for (k = 0; k < 4; k = k + 1) xo_of[32 * k +: 32] = {h[16 * k +: 16], 16'h0000};
    endfunction
    integer i, rst_left = 3;
    reg [543:0] rnd;
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 20000;
        repeat (N) begin
            @(negedge ck);
            if (cyc >= 2) begin
                if (a_d !== m_bq) begin
                    errs = errs + 1;
                    if (shown < 8) begin shown = shown + 1; $display("MISMATCH cyc %0d a_d^exp %h", cyc, a_d ^ m_bq); end
                end
                if (tap_d[IBW:0] !== m_tq) begin
                    errs = errs + 1;
                    if (shown < 8) begin shown = shown + 1; $display("MISMATCH cyc %0d tap_d[t]^exp %h", cyc, tap_d[IBW:0] ^ m_tq); end
                end
                if (m_hold_def && tap_d[TW-1:IBW+1] !== xo_of(m_hold)) begin
                    errs = errs + 1;
                    if (shown < 8) begin shown = shown + 1; $display("MISMATCH cyc %0d tap_d[x] %h exp %h", cyc, tap_d[TW-1:IBW+1], xo_of(m_hold)); end
                end
            end
            // next inputs (changed at the negedge; the async reset of cnt / run is mirrored in the model)
            for (i = 0; i < 544; i = i + 32) rnd[i +: 32] = $urandom;
            b_d = rnd[CW-1:0];
            b_d[0] = ($urandom % 12) == 0;                                  // go
            b_d[1 + IBW + 128 + 3] = ($urandom % 3) == 0;                   // tag[3]
            b_d[1 + IBW + 128 + 7] = ($urandom % 3) == 0;                   // tag[7]
            if (cyc % 1500 == 1499) begin sidx = sidx + 3'd3; n_sidx = n_sidx + 1; end
            if (rst_left > 0) begin rst_n = 1'b0; rst_left = rst_left - 1; end
            else begin
                rst_n = 1'b1;
                if (cyc % 4999 == 4998) begin rst_left = 2; rst_n = 1'b0; n_rst = n_rst + 1; end
            end
            if (!rst_n) begin m_cnt = 0; m_run = 0; end
            cyc = cyc + 1;
        end
        if (errs == 0 && n_hold > 0 && n_tag > 0)
            $display("STN_BENCH PASS %s 0 errors in %0d cycles go=%0d tag_hits=%0d hold_loads=%0d resets=%0d sidx_steps=%0d",
                     NAME, cyc, n_go, n_tag, n_hold, n_rst, n_sidx);
        else
            $display("STN_BENCH FAIL %s %0d errors in %0d cycles go=%0d tag_hits=%0d hold_loads=%0d resets=%0d sidx_steps=%0d",
                     NAME, errs, cyc, n_go, n_tag, n_hold, n_rst, n_sidx);
        $finish;
    end
`endif
endmodule
